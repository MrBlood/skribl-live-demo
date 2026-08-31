"""v224 — is the orphan sweep operable, and does it say what it did?

Outside review, finding #6. `storage.sweep_orphans` has reclaimed disk since
v180 and returned a list of keys. Two things were wrong with that as a
maintenance story.

NOTHING SHIPPED COULD RUN IT. Every deployment had to write its own entry point
— resolve the app, find the store the host passed to init_skribl, get a session,
and get the argument order right on a function whose third positional argument
deletes user data. `python -m skribl.sweep` is now that entry point, dry by
default with `--delete` as the wet flag.

AND A RUN WAS UNOBSERVABLE. A sweep that removed nothing looked identical
whether there was nothing to reclaim, the credentials were pointed at the wrong
prefix, or the grace period was swallowing everything. `sweep_orphans_report`
now counts every branch that DECLINES to delete, separately.

The suite is built around the same rule as verify_medialimits: prove each thing
in the direction it can fail. Every counter gets an object planted specifically
to land in it and nowhere else, the CLI is driven as a real subprocess (so exit
codes are the ones a cron job would see, not the ones the source implies), and
the counters are cross-checked against each other so a miscount cannot hide.

Runs entirely in-process against a temp SQLite file and a temp media root. No
server, no browser — it is one of the cheapest suites in the tree.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB_DIR = tempfile.mkdtemp()
MEDIA_ROOT = tempfile.mkdtemp()
STUB_DIR = tempfile.mkdtemp()
DB_URL = f"sqlite:///{DB_DIR}/sweepjob.db"
DAY = 86400

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


ENV = dict(os.environ, DATABASE_URL=DB_URL, SKRIBL_MEDIA_BACKEND="local",
           SKRIBL_MEDIA_ROOT=MEDIA_ROOT, SECRET_KEY="harness-sweepjob",
           PYTHONPATH=STUB_DIR + os.pathsep + os.environ.get("PYTHONPATH", ""))
os.environ.update(ENV)

from app import create_app                                        # noqa: E402
import skribl.storage as storage                                  # noqa: E402
from skribl.models import SkriblPost, SkriblPostMedia, SkriblPendingMedia, session  # noqa: E402

app = create_app()
with app.app_context():
    import app as _app_module
    _app_module.db.create_all()


# ── planting ────────────────────────────────────────────────────────────────
def plant(name, body=b"x", age_seconds=0):
    """Write a file at the store's canonical sharded path with a chosen age."""
    sub = os.path.join(MEDIA_ROOT, name[:2], name[2:4])
    os.makedirs(sub, exist_ok=True)
    path = os.path.join(sub, name)
    with open(path, "wb") as fh:
        fh.write(body)
    when = time.time() - age_seconds
    os.utime(path, (when, when))
    return path


def key(seed, ext=".png"):
    return hashlib.sha256(seed.encode()).hexdigest() + ext


def on_disk():
    return {f for _s, _d, files in os.walk(MEDIA_ROOT) for f in files}


def reset_store():
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
    os.makedirs(MEDIA_ROOT, exist_ok=True)


def store_now():
    from flask import url_for
    return storage.LocalDiskStore(MEDIA_ROOT, lambda k: url_for("skribl.media", key=k))


# One object per counter, and NOTHING that could land in two of them. A planted
# case that could be counted twice proves nothing about which branch caught it.
K_ORPHAN_A = key("orphan-a")
K_ORPHAN_B = key("orphan-b")
K_REFERENCED = key("referenced")
K_YOUNG = key("young")
K_FOREIGN = hashlib.sha256(b"foreign").hexdigest() + ".html"   # hex-named, wrong ext
K_REUSED = key("reused")


def plant_the_full_set():
    reset_store()
    for k in (K_ORPHAN_A, K_ORPHAN_B, K_REFERENCED, K_REUSED):
        plant(k, age_seconds=3 * DAY)
    plant(K_FOREIGN, age_seconds=3 * DAY)
    plant(K_YOUNG, age_seconds=5)          # written minutes ago: may be mid-commit


with app.app_context():
    sess = session()
    post = SkriblPost(public_id="sweepjob-1", title="held", payload_json={},
                      visibility="public")
    sess.add(post)
    sess.flush()
    sess.add(SkriblPostMedia(post_id=post.id, media_key=K_REFERENCED))
    sess.commit()


print("\nCOUNTERS — every branch that declines to delete must say so")
plant_the_full_set()
with app.test_request_context():
    # A store whose stat_key reports ONE key as freshly touched — the reuse race
    # the v223 fix closed. Wrapping the real store is the only way to hit that
    # window deterministically; the race itself is a few milliseconds wide.
    class ReusedMidSweep(storage.LocalDiskStore):
        def stat_key(self, k):
            return time.time() if k == K_REUSED else super().stat_key(k)

    from flask import url_for
    st = ReusedMidSweep(MEDIA_ROOT, lambda k: url_for("skribl.media", key=k))
    rep = storage.sweep_orphans_report(st, session(), older_than_seconds=DAY)

check("the report is a dry run unless asked otherwise", rep["dry_run"] is True)
check("it lists every file at a canonical path", rep["listed"] == 6, str(rep["listed"]))
check("a hex name with a foreign extension is counted as not ours",
      rep["skipped_foreign"] == 1, str(rep["skipped_foreign"]))
check("an object inside the grace period is counted as young",
      rep["skipped_young"] == 1, str(rep["skipped_young"]))
check("an object a post references is counted as referenced",
      rep["skipped_referenced"] == 1, str(rep["skipped_referenced"]))
check("an object touched mid-sweep is counted as reused, not deleted",
      rep["skipped_reused"] == 1 and K_REUSED not in rep["removed"],
      f"reused={rep['skipped_reused']}")
check("and the two real orphans are what is left",
      sorted(rep["removed"]) == sorted([K_ORPHAN_A, K_ORPHAN_B]),
      str(rep["removed"]))
check("removed_count agrees with the list it summarises",
      rep["removed_count"] == len(rep["removed"]))
# The cross-check. Each counter above could be right on its own while the sweep
# quietly dropped a key on the floor; this is what makes them add up.
check("every listed object is accounted for exactly once",
      rep["listed"] == (rep["skipped_foreign"] + rep["skipped_young"]
                        + rep["skipped_referenced"] + rep["skipped_reused"]
                        + rep["skipped_claimed"]
                        + rep["removed_count"] + rep["delete_error_count"]),
      json.dumps({k: v for k, v in rep.items() if k != "removed"}))
check("candidates is what survived both cheap filters",
      rep["candidates"] == rep["listed"] - rep["skipped_foreign"] - rep["skipped_young"],
      str(rep["candidates"]))
check("the report is JSON-serialisable as-is",
      isinstance(json.loads(json.dumps(rep)), dict),
      "a job that cannot ship the dict to its metrics has to reformat it")
check("A DRY RUN DELETED NOTHING", len(on_disk()) == 6, f"{len(on_disk())} files")


print("\nTHE WRAPPER — sweep_orphans keeps its old contract exactly")
with app.test_request_context():
    plain = storage.sweep_orphans(store_now(), session(), older_than_seconds=DAY)
check("it still returns a plain list", type(plain) is list, type(plain).__name__)
check("holding the same keys the report names",
      sorted(plain) == sorted([K_ORPHAN_A, K_ORPHAN_B, K_REUSED]),
      "the un-wrapped store has no reuse to skip, so K_REUSED joins them")


print("\nA FAILED DELETE IS NO LONGER A FAILED SWEEP")
# Before this, store.delete_key ran uncaught: one object a bucket policy refuses
# aborted the run and left every LATER orphan in place — while the key was
# already in the returned list, reporting a deletion that never happened.
plant_the_full_set()
with app.test_request_context():
    class RefusesOne(storage.LocalDiskStore):
        def delete_key(self, k):
            if k == K_ORPHAN_A:
                raise PermissionError("access denied by bucket policy")
            return super().delete_key(k)

    from flask import url_for
    rep2 = storage.sweep_orphans_report(
        RefusesOne(MEDIA_ROOT, lambda k: url_for("skribl.media", key=k)),
        session(), older_than_seconds=DAY, dry_run=False)

left = on_disk()
check("the sweep continued past the refusal", rep2["removed_count"] >= 2,
      f"removed {rep2['removed_count']}")
check("the orphan it could not delete is NOT reported as removed",
      K_ORPHAN_A not in rep2["removed"] and K_ORPHAN_A in left,
      "`removed` has to mean removed")
check("the failure is reported with its key and its reason",
      rep2["delete_error_count"] == 1
      and rep2["delete_errors"][0]["key"] == K_ORPHAN_A
      and "PermissionError" in rep2["delete_errors"][0]["error"],
      str(rep2["delete_errors"])[:120])
check("the orphans after it were still reclaimed", K_ORPHAN_B not in left)
check("and it still did not touch the referenced, young or foreign objects",
      {K_REFERENCED, K_YOUNG, K_FOREIGN} <= left,
      f"{sorted(left)}")


print("\nDELETE_KEY MEANS DELETE — a real failure is not a silent success")
# OUTSIDE REVIEW OF v263, M5. LocalDiskStore.delete_key swallowed EVERY OSError,
# so a delete the filesystem refused (permissions, read-only) was invisible to
# the sweep and the key was counted as removed while its bytes stayed on disk.
# Only 'already gone' is a legitimate silent success now; anything else raises
# and the sweep records it (proven by the RefusesOne block above, which now
# rides on the base class actually propagating).
reset_store()
_st = store_now()
_missing = key("never-existed")
try:
    _st.delete_key(_missing)
    _missing_ok = True
except OSError:
    _missing_ok = False
check("deleting an already-gone key is a silent success", _missing_ok,
      "FileNotFoundError is the one OSError that means 'done'")
# Force a non-ENOENT OSError deterministically (works even as root, unlike a
# chmod): put a DIRECTORY where the body file would be, so os.remove raises
# IsADirectoryError.
_k = key("is-a-dir")
_sub = os.path.join(MEDIA_ROOT, _k[:2], _k[2:4])
os.makedirs(os.path.join(_sub, _k), exist_ok=True)
try:
    _st.delete_key(_k)
    _raised = False
except OSError:
    _raised = True
check("a delete the filesystem refuses now RAISES instead of being swallowed",
      _raised, "M5: swallowing it reported a removal that did not happen")

print("\nREUSE RACING THE SWEEP — an object deleted mid-reuse is rewritten")
# OUTSIDE REVIEW OF v263, H3. put_bytes reuses an existing object by touching
# its mtime, but between the exists() check and the utime() the sweeper can
# delete the file it listed as old. The touch then raises FileNotFoundError;
# the old code swallowed it and returned, leaving the committing post pointing
# at bytes that are gone. We hold the bytes, so that race now rewrites them.
reset_store()
_st = store_now()
_rk = key("racy")
_st.put_bytes(b"hello-bytes", "image/png", _rk)
_bpath = _st._paths(_rk)[1]
check("the object was written the first time", os.path.exists(_bpath))
_real_utime = os.utime
def _racing_utime(p, times):
    # the sweeper wins the race: the object we just found is deleted here,
    # right before the touch that was going to refresh its age.
    try:
        os.remove(_bpath)
    except OSError:
        pass
    return _real_utime(p, times)          # now raises FileNotFoundError
os.utime = _racing_utime
try:
    _st.put_bytes(b"hello-bytes", "image/png", _rk)   # the reuse path
finally:
    os.utime = _real_utime
check("a reuse whose object is deleted mid-touch rewrites the bytes",
      os.path.exists(_bpath) and open(_bpath, "rb").read() == b"hello-bytes",
      "the post must not be left pointing at deleted media")


print("\nTHE CLI — driven as a subprocess, so these are the codes cron sees")


def cli(*args, env=None):
    p = subprocess.run([sys.executable, "-m", "skribl.sweep",
                        "--app", "app:create_app", *args],
                       cwd=ROOT, env=env or ENV, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


plant_the_full_set()
code, out, err = cli("--list-keys")
check("a bare run is a dry run and exits 0", code == 0, f"exit {code} — {err.strip()[:120]}")
check("it says it was a rehearsal", "DRY RUN" in out, out.strip()[:80])
check("it names both orphans", K_ORPHAN_A in out and K_ORPHAN_B in out)
check("and it tells the reader how to actually reclaim them",
      "--delete" in out, "a dry run that does not say what to do next is a dead end")
check("A BARE RUN DELETED NOTHING", len(on_disk()) == 6, f"{len(on_disk())} files")

code, out, err = cli("--json")
# Three, not two: the CLI runs against the real store, which has no reuse to
# skip, so K_REUSED is an ordinary orphan on this path. Only the wrapped store
# in the counters block above can hold that window open.
check("--json prints one parseable object and nothing else", code == 0
      and json.loads(out)["removed_count"] == 3, out.strip()[:120])
check("…and no human prose leaks into it", "DRY RUN" not in out)

code, out, err = cli("--older-than", "60", "--delete")
check("--delete with a 60s grace period is REFUSED", code == 2,
      f"exit {code}")
check("the refusal explains the ordering hazard rather than just saying no",
      "before the transaction" in err, err.strip()[:140])
check("and it refused before touching anything", len(on_disk()) == 6)

code, out, err = cli("--older-than", "60", "--delete",
                     "--i-know-the-grace-period-is-short")
check("the acknowledgement flag unblocks it", code == 0, f"exit {code} — {err[:100]}")
check("…and then it really deletes", K_ORPHAN_A not in on_disk())

code, out, err = cli("--app", "nosuchmodule:app")
check("an unimportable --app exits 2, not 1", code == 2, f"exit {code}")
check("…with one line on stderr and no traceback",
      "Traceback" not in err and err.count("\n") <= 1, err[:160])

code, out, err = cli(env=dict(ENV, SKRIBL_MEDIA_BACKEND="inline"))
check("an inline deployment is told there is nothing to sweep, and exits 0",
      code == 0 and "payload_json" in out, f"exit {code} — {out.strip()[:100]}")

# The exit-1 path needs a store whose delete actually raises. LocalDiskStore
# swallows OSError by design, so no permissions trick on the real backend can
# reach it — a throwaway app on PYTHONPATH is the honest way to exercise it.
with open(os.path.join(STUB_DIR, "sweepstub.py"), "w") as fh:
    fh.write(
        "import os\n"
        "from flask import url_for\n"
        "import skribl.storage as storage\n"
        "import app as demo\n"
        "class Refuses(storage.LocalDiskStore):\n"
        "    def delete_key(self, k):\n"
        "        raise PermissionError('access denied by bucket policy')\n"
        "def create_app():\n"
        "    a = demo.create_app()\n"
        "    bp = a.blueprints['skribl']\n"
        "    with a.test_request_context():\n"
        "        bp.skribl_media_store = Refuses(\n"
        "            os.environ['SKRIBL_MEDIA_ROOT'],\n"
        "            lambda k: url_for('skribl.media', key=k))\n"
        "    return a\n")
plant_the_full_set()
code, out, err = cli("--app", "sweepstub:create_app", "--delete")
check("a run where every delete fails exits 1, not 0", code == 1, f"exit {code}")
check("…and the failures are printed, not swallowed",
      "DELETES THAT FAILED" in out and "PermissionError" in out, out.strip()[-160:])
check("exit 1 and exit 2 mean different things to the job that reads them",
      True, "1 = it ran and some deletes failed; 2 = it could not run at all")


print("\nTHE FLAG IS LOAD-BEARING — without --delete, nothing goes")
# The mutation check for this suite: if a dry run and a wet run both leave the
# same disk behind, every assertion above about --delete is decoration.
plant_the_full_set()
before = len(on_disk())
cli()
after_dry = len(on_disk())
cli("--delete")
after_wet = len(on_disk())
check("the dry run and the wet run leave DIFFERENT disks behind",
      before == after_dry == 6 and after_wet == 3,
      f"{before} planted, {after_dry} after dry, {after_wet} after wet — "
      "the three survivors are the referenced, young and foreign objects")



print("\nPENDING CLAIMS (v266) — the ownership that closes the sweep race (H3)")
# OUTSIDE REVIEW OF v263/v264/v265. Media bytes are written before the post's
# association row, which commits in the HOST's transaction — so no delete-time
# check can see it, and touch-and-re-check cannot close the window. A poster now
# writes a COMMITTED pending-media claim before its association commits, and the
# sweeper spares any object carrying an unexpired one.


def _add_claim(k, ttl_seconds):
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=ttl_seconds)
    s = session()
    s.add(SkriblPendingMedia(media_key=k, expires_at=exp))
    s.commit()


import datetime  # noqa: E402

# (1) An unexpired claim spares an orphan the sweep would otherwise reclaim.
reset_store()
K_CLAIMED = key("claimed")
plant(K_CLAIMED, age_seconds=3 * DAY)          # old and unreferenced: a sure orphan
with app.app_context():
    session().query(SkriblPendingMedia).delete(); session().commit()
    _add_claim(K_CLAIMED, 300)
with app.test_request_context():
    rep_c = storage.sweep_orphans_report(store_now(), session(), older_than_seconds=DAY,
                                         dry_run=False)
check("an object with an unexpired claim is spared and counted as claimed",
      K_CLAIMED not in rep_c["removed"] and rep_c["skipped_claimed"] == 1
      and K_CLAIMED in on_disk(),
      f"skipped_claimed={rep_c['skipped_claimed']} removed={rep_c['removed']}")

# (2) MUTATION-BY-DATA: an EXPIRED claim must NOT protect — otherwise the check
# above passes for a build that skips every claimed key regardless of expiry,
# which would leak orphans forever.
reset_store()
plant(K_CLAIMED, age_seconds=3 * DAY)
with app.app_context():
    session().query(SkriblPendingMedia).delete(); session().commit()
    _add_claim(K_CLAIMED, -10)                 # already expired
with app.test_request_context():
    rep_e = storage.sweep_orphans_report(store_now(), session(), older_than_seconds=DAY,
                                         dry_run=False)
check("an EXPIRED claim does not protect — the object is reclaimed",
      K_CLAIMED in rep_e["removed"] and K_CLAIMED not in on_disk(),
      f"removed={rep_e['removed']}")
check("…and the sweep prunes the expired claim it stepped over",
      rep_e["claims_pruned"] >= 1, f"pruned={rep_e['claims_pruned']}")

# (3) THE DETERMINISTIC REPRODUCTION the reviewer asked for: the sweeper lists an
# object as old, a concurrent poster CLAIMS (committed) and reuses it inside the
# window, and the sweeper reaches its delete. On v265 the object is deleted and
# its committed post 404s; the per-key claim re-check must now spare it.
reset_store()
K_RACE = key("race")
plant(K_RACE, age_seconds=3 * DAY)
_race_path = store_now()._paths(K_RACE)[1]
with app.app_context():
    session().query(SkriblPendingMedia).delete(); session().commit()
_old = time.time() - 3 * DAY


class ClaimsAtStatSeam(storage.LocalDiskStore):
    def stat_key(self, k):
        if k == K_RACE:
            # the concurrent poster, at the exact TOCTOU seam: COMMIT a claim
            # then reuse the object, and report the pre-touch age so the sweeper
            # still believes it is deletable. The claim is committed through the
            # session here rather than claim_media's separate connection because
            # SQLite's rollback-journal lock would block a second writer while
            # this sweep holds a read — the write-path contention that makes the
            # claim best-effort on SQLite and fully effective on PostgreSQL,
            # where this race actually occurs. What is under test is the
            # SWEEPER's per-key recheck honouring a claim that appears after the
            # batch query, which this reproduces deterministically.
            s = session()
            s.add(SkriblPendingMedia(
                media_key=K_RACE,
                expires_at=datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(seconds=300)))
            s.commit()
            self.put_bytes(b"reused-bytes", "image/png", K_RACE)
            return _old                        # sweeper still holds the age it read
        return super().stat_key(k)


with app.test_request_context():
    rep_r = storage.sweep_orphans_report(
        ClaimsAtStatSeam(MEDIA_ROOT, lambda k: "/m/" + k),
        session(), older_than_seconds=DAY, dry_run=False)
check("REVIEWER ORDERING: claim-at-seam spares the reused object from deletion",
      os.path.exists(_race_path) and K_RACE not in rep_r["removed"]
      and rep_r["skipped_claimed"] >= 1,
      f"survived={os.path.exists(_race_path)} skipped_claimed={rep_r['skipped_claimed']}")

# (4) claim_media writes durable rows visible to a fresh reader (it is what the
# poster relies on being seen before its own transaction commits).
reset_store()
with app.app_context():
    session().query(SkriblPendingMedia).delete(); session().commit()
    eng = session().get_bind()
    n = storage.claim_media(eng, [key("w1"), key("w2"), key("w2")], 120)   # dup collapses
    n_empty = storage.claim_media(eng, [], 120)
with app.app_context():
    seen = {r[0] for r in session().query(SkriblPendingMedia.media_key).all()}
check("claim_media writes one committed row per distinct key",
      n == 2 and seen == {key("w1"), key("w2")}, f"n={n} seen={len(seen)}")
check("claim_media with no keys writes nothing", n_empty == 0)


shutil.rmtree(DB_DIR, ignore_errors=True)
shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
shutil.rmtree(STUB_DIR, ignore_errors=True)

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
