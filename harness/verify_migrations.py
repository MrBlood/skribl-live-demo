"""The Alembic migration chain.

Skribl created its schema with `db.create_all()`, which is fine for a demo and
unusable for a platform: it cannot alter an existing table, so every schema
change would mean losing the data. A host also cannot let a component's
migrations touch its own tables.

Self-contained: builds throwaway SQLite databases in a temp directory and never
touches the harness server or its database, so it can run alongside everything
else. PostgreSQL behaviour is covered by running the same chain in CI's postgres
job.

The assertions that matter:
  * The chain applies cleanly to an EMPTY database.
  * The chain applies cleanly to a POPULATED v131 database — the real case, and
    the one that fails if a NOT NULL column is added without a server default.
  * Existing rows are backfilled as 'unlisted', not 'public'. Getting this
    backwards would retroactively publish every Skribl ever made into the feed.
  * Migrations are scoped to Skribl: a host table in the same database is left
    strictly alone, and autogenerate does not propose dropping it.
  * The chain's end state matches the models, so nobody has to remember to write
    a migration after editing a column.
"""
import os
import re
import shutil
import subprocess
import sys
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  → {detail}" if detail else ""))


def alembic(db_path, *args):
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db_path}")
    return subprocess.run([sys.executable, "-m", "alembic", *args],
                          cwd=ROOT, env=env, capture_output=True, text=True)


if shutil.which("alembic") is None and \
        subprocess.run([sys.executable, "-c", "import alembic"],
                       capture_output=True).returncode != 0:
    print("SUITE-SKIPPED: alembic is not installed.")
    raise SystemExit(77)

tmp = tempfile.mkdtemp()
BASELINE = "6aa1de24dda3"

print("\nMIGRATIONS — the chain applies to an empty database")
db1 = os.path.join(tmp, "empty.db")
r = alembic(db1, "upgrade", "head")
check("upgrade head succeeds on a fresh database", r.returncode == 0,
      (r.stderr or "").strip().splitlines()[-1:] and (r.stderr).strip().splitlines()[-1] or "")
cols = {c[1] for c in sqlite3.connect(db1).execute("pragma table_info(skribl_posts)")}
check("skribl_posts exists with the expected columns",
      {"id", "public_id", "user_id", "title", "caption", "payload_json",
       "has_audio", "created_at", "visibility"} <= cols, str(sorted(cols)))
idx = {r[1] for r in sqlite3.connect(db1).execute("pragma index_list(skribl_posts)")}
check("the feed indexes exist",
      {"ix_skribl_posts_user_created", "ix_skribl_posts_visibility_created"} <= idx,
      str(sorted(idx)))

print("\nMIGRATIONS — the chain applies to a POPULATED v131 database")
db2 = os.path.join(tmp, "legacy.db")
r = alembic(db2, "upgrade", BASELINE)
check("a database can be brought to the v131 baseline", r.returncode == 0)
con = sqlite3.connect(db2)
con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,has_audio,created_at)"
            " values ('legacy1',1,'old post','{}',0,?)", (datetime.now().isoformat(),))
con.commit()
pre_cols = {c[1] for c in con.execute("pragma table_info(skribl_posts)")}
check("the v131 baseline has NO visibility column (it describes v131, not today)",
      "visibility" not in pre_cols,
      "the baseline folded v132 in — an existing deploy could not be stamped at it")

r = alembic(db2, "upgrade", "head")
check("upgrading a table that already has rows succeeds", r.returncode == 0,
      "a NOT NULL column with no server_default fails exactly here")
rows = list(sqlite3.connect(db2).execute("select public_id, visibility from skribl_posts"))
check("the pre-existing row survived the migration", len(rows) == 1, str(rows))
check("and it was backfilled as 'unlisted', NOT 'public'",
      rows and rows[0][1] == "unlisted",
      f"got {rows[0][1]!r} — 'public' would publish every legacy Skribl to the feed")

print("\nMIGRATIONS — pre-v135 local media is adopted, not orphaned")
# The legacy row above uses payload_json='{}', which is why this gap existed:
# the suite proved a populated table upgrades, but never a populated table
# holding MEDIA. SKRIBL_MEDIA_BACKEND=local has been supported since v132, so a
# real database can hold posts referencing /media/<key> objects. v135 authorises
# those objects through skribl_post_media and treats an object with no rows as
# orphaned — so without a data backfill, upgrading 404s the audio and images of
# every previously posted Skribl.
db5 = os.path.join(tmp, "legacymedia.db")
r = alembic(db5, "upgrade", "88f18e7f844d")
check("a database can be brought to the pre-v135 revision", r.returncode == 0)
_K1, _K2 = "a" * 64 + ".wav", "b" * 64 + ".png"
_con = sqlite3.connect(db5)
_payload = json.dumps({"frames": [{"music": {"data": f"/media/{_K1}"},
                                   "photo": {"data": f"/media/{_K2}"}}]})
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('legacy-media',1,'pre-v135 media',?,1,?,'public')",
             (_payload, datetime.now().isoformat()))
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('no-media',1,'none','{}',0,?,'public')",
             (datetime.now().isoformat(),))
_con.commit()
check("the pre-v135 revision has no association table yet",
      not list(_con.execute("select name from sqlite_master where"
                            " name='skribl_post_media'")))

r = alembic(db5, "upgrade", "head")
check("upgrading a database that already holds local media succeeds",
      r.returncode == 0, (r.stderr or "").strip().splitlines()[-1:] and
      (r.stderr).strip().splitlines()[-1] or "")
_con = sqlite3.connect(db5)
_assoc = list(_con.execute(
    "select p.public_id, m.media_key from skribl_post_media m"
    " join skribl_posts p on p.id = m.post_id order by m.media_key"))
check("both referenced objects were adopted", len(_assoc) == 2,
      f"{len(_assoc)} rows — pre-v135 media would 404 as orphaned")
check("they are attached to the post that actually referenced them",
      all(pid == "legacy-media" for pid, _ in _assoc), str(_assoc))
check("the exact keys were extracted, not a mangled substring",
      {k for _, k in _assoc} == {_K1, _K2},
      str(sorted(k[:10] for _, k in _assoc)))
check("a post with no media gains no association rows",
      not list(_con.execute(
          "select 1 from skribl_post_media m join skribl_posts p"
          " on p.id = m.post_id where p.public_id = 'no-media'")))

print("\nMIGRATIONS — a database already stamped at v135 still gets the backfill")
# The previous suite started at the PRE-v135 revision and upgraded to head,
# proving v132->v136 and saying nothing about v135->v136. That mattered: the
# backfill was first added by EDITING the already-released v135 revision, so a
# database actually stamped at 86171614cb85 saw itself as current and never ran
# it. The fix that mattered ran only where the problem did not exist.
V135 = "86171614cb85"
db6 = os.path.join(tmp, "v135stamped.db")
r = alembic(db6, "upgrade", V135)
check("a database can be brought to the released v135 revision", r.returncode == 0)
_con = sqlite3.connect(db6)
check("v135 creates the association table but leaves it EMPTY",
      list(_con.execute("select name from sqlite_master where name='skribl_post_media'"))
      and not list(_con.execute("select 1 from skribl_post_media")))

_REAL = "a" * 64 + ".wav"
_VICTIM = "c" * 64 + ".png"
_now = datetime.now().isoformat()
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('realmedia',1,'real',?,1,?,'public')",
             (json.dumps({"frames": [{"music": {"data": f"/media/{_REAL}"}}]}), _now))
# A post that merely NAMES someone else's key in fields the API preserves.
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('forger',2,'forger',?,0,?,'public')",
             (json.dumps({"notes": f"see /media/{_VICTIM}",
                          "stolen": f"/media/{_VICTIM}",
                          "frames": []}), _now))
# A NARROWER forgery: a per-frame "thumbnail". The application's walker has no
# such slot — captureCurrentFrame() never writes one and the share thumbnail is
# top-level only — but POST preserves unknown fields, so an attacker could
# persist it. A backfill that assumed the slot existed would promote it into a
# real association. Seeded here precisely because a draft of the migration did.
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('frameforger',3,'frame forger',?,0,?,'public')",
             (json.dumps({"frames": [{"thumbnail": f"/media/{_VICTIM}"}]}), _now))
# A PREFIXED deployment: the local store builds URLs with url_for, so a
# blueprint mounted at /skribl stores "/skribl/media/<key>". These must be
# adopted; the first backfill only matched a root-mounted path.
_PREFIXED = "d" * 64 + ".wav"
_con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
             "has_audio,created_at,visibility) values"
             " ('prefixed',4,'mounted at /skribl',?,1,?,'public')",
             (json.dumps({"frames": [{"music": {"data": f"/skribl/media/{_PREFIXED}"}}]}),
              _now))
_con.commit()

r = alembic(db6, "upgrade", "head")
check("upgrading FROM v135 runs a further revision", r.returncode == 0
      and "Running upgrade" in (r.stdout + r.stderr),
      "no revision after v135 — editing the released one would look like this")
_con = sqlite3.connect(db6)
_rows = list(_con.execute(
    "select p.public_id, m.media_key from skribl_post_media m"
    " join skribl_posts p on p.id = m.post_id"))
check("the genuine media reference was adopted",
      any(pid == "realmedia" and k == _REAL for pid, k in _rows), str(_rows))
check("the FORGER gained nothing by naming another post's key",
      not any(pid == "forger" for pid, _ in _rows),
      "a text scan of payload_json would have granted it — that is the v135 "
      "forgery, recreated in a migration")

r = alembic(db6, "upgrade", "head")
check("a per-frame 'thumbnail' grants NO association",
      not any(pid == "frameforger" for pid, _ in _rows),
      "the walker has no frames[i].thumbnail slot — inventing one is a hole")
check("a PREFIXED media URL is adopted (/skribl/media/<key>)",
      any(pid == "prefixed" and k == _PREFIXED for pid, k in _rows),
      "a deployment mounted under url_prefix would keep 404ing its own media")

check("re-running the backfill is idempotent", r.returncode == 0)
_after = len(list(sqlite3.connect(db6).execute("select 1 from skribl_post_media")))
check("and does not duplicate associations", _after == len(_rows),
      f"{_after} rows vs {len(_rows)}")

print("\nMIGRATIONS — released revisions are immutable")
# The guard for the mistake this project made twice. Editing a released revision
# is invisible to Alembic: a database stamped at it sees current == head and runs
# nothing, so the fix reaches only the databases that never needed it.
import hashlib
_released = ROOT / "skribl" / "migrations" / "RELEASED.txt"
check("the released-revision manifest exists", _released.is_file())
if _released.is_file():
    _frozen = {}
    for _line in _released.read_text(encoding="utf-8").splitlines():
        if _line.startswith("#") or not _line.strip():
            continue
        _d, _rev = _line.split()
        _frozen[_rev] = _d
    _changed, _unlisted = [], []
    for _f in sorted((ROOT / "skribl" / "migrations" / "versions").glob("*.py")):
        _rev = _f.name.split("_")[0]
        _actual = hashlib.sha256(_f.read_bytes()).hexdigest()
        if _rev not in _frozen:
            _unlisted.append(_rev)
        elif _frozen[_rev] != _actual:
            _changed.append(_rev)
    check("no released migration has been edited", not _changed,
          f"{_changed} — add a revision instead; editing one is a silent no-op "
          f"for every database already stamped at it")
    check("every revision on disk is listed as released", not _unlisted,
          f"{_unlisted} — append its digest to RELEASED.txt")

print("\nMIGRATIONS — a database at the RELEASED v137 head is repaired")
# The upgrade the previous suite could not see. It started at v135 and ran to
# head, which proves v135->current and says nothing about v137->v138 — and
# v137->v138 is exactly where "edited in place" shows up as zero revisions run.
V137 = "e4b7c9a15d2f"
db7 = os.path.join(tmp, "v137head.db")
r = alembic(db7, "upgrade", "86171614cb85")
check("a database can be brought to the pre-v137 revision", r.returncode == 0)
_PREF = "d" * 64 + ".wav"
_VIC = "c" * 64 + ".png"
_GOOD = "a" * 64 + ".wav"
_con = sqlite3.connect(db7)
_now2 = datetime.now().isoformat()
for _pid, _uid, _payload in [
        ("prefixed", 4, {"frames": [{"music": {"data": f"/skribl/media/{_PREF}"}}]}),
        ("frameforger", 3, {"frames": [{"thumbnail": f"/media/{_VIC}"}]}),
        ("realmedia", 1, {"frames": [{"music": {"data": f"/media/{_GOOD}"}}]})]:
    _con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
                 "has_audio,created_at,visibility) values (?,?,?,?,0,?,'public')",
                 (_pid, _uid, _pid, json.dumps(_payload), _now2))
_con.commit()

r = alembic(db7, "upgrade", V137)
check("the released v137 migration runs", r.returncode == 0)
_before = {(a, b) for a, b in sqlite3.connect(db7).execute(
    "select p.public_id, m.media_key from skribl_post_media m"
    " join skribl_posts p on p.id = m.post_id")}
check("v137 left the prefixed deployment with NO association",
      not any(a == "prefixed" for a, _ in _before),
      "if this passes, the bug being repaired is reproduced")
check("and invented one for the per-frame thumbnail",
      any(a == "frameforger" for a, _ in _before),
      "the false row this revision must clean up")

r = alembic(db7, "upgrade", "head")
check("upgrading FROM the released v137 head runs a NEW revision",
      r.returncode == 0 and "Running upgrade" in (r.stdout + r.stderr),
      "zero revisions ran — a released migration was edited in place again")
_after = {(a, b) for a, b in sqlite3.connect(db7).execute(
    "select p.public_id, m.media_key from skribl_post_media m"
    " join skribl_posts p on p.id = m.post_id")}
check("the prefixed deployment's media is adopted",
      any(a == "prefixed" and k == _PREF for a, k in _after), str(sorted(_after)))
check("the false per-frame-thumbnail association is REMOVED",
      not any(a == "frameforger" for a, _ in _after),
      "correcting the code does not delete rows the old code already wrote")
check("the genuine association is preserved",
      any(a == "realmedia" and k == _GOOD for a, k in _after))

r = alembic(db7, "upgrade", "head")
_again = len(list(sqlite3.connect(db7).execute("select 1 from skribl_post_media")))
check("the repair is idempotent", r.returncode == 0 and _again == len(_after),
      f"{_again} vs {len(_after)}")

print("\nMIGRATIONS — the repair never deletes a valid association")
# The v139 repair decided legitimacy by reverse-parsing the stored URL, so any
# presentation form its pattern did not recognise — a presigned S3 URL, a mount
# prefix containing characters outside [A-Za-z0-9._~%-] — computed as "not a
# legitimate reference" and the valid association was DELETED. With the local
# backend that turns working media into a 404. Storage returns the key precisely
# so nothing has to parse one back out of a URL; the cleanup parsed one anyway.
db8 = os.path.join(tmp, "urlforms.db")
r = alembic(db8, "upgrade", "86171614cb85")
check("a database can be brought to the pre-v137 revision", r.returncode == 0)
_S3 = "e" * 64 + ".wav"
_TEN = "f" * 64 + ".wav"
_VIC2 = "c" * 64 + ".png"
_OK = "a" * 64 + ".wav"
_con = sqlite3.connect(db8)
_n = datetime.now().isoformat()
for _pid, _payload in [
        # legitimate media, presented as a presigned S3 URL
        ("s3post", {"frames": [{"music": {"data": f"https://bucket/objects/{_S3}?X-Amz-Signature=abc"},
                                "thumbnail": f"/media/{_S3}"}]}),
        # legitimate media behind a prefix with a '+' in it
        ("tenant", {"frames": [{"music": {"data": f"/tenant+blue/media/{_TEN}"},
                                "thumbnail": f"/media/{_TEN}"}]}),
        # a genuine forgery: the key appears ONLY in the invalid slot
        ("frameforger2", {"frames": [{"thumbnail": f"/media/{_VIC2}"}]}),
        ("plain", {"frames": [{"music": {"data": f"/media/{_OK}"}}]})]:
    _con.execute("insert into skribl_posts (public_id,user_id,title,payload_json,"
                 "has_audio,created_at,visibility) values (?,1,?,?,0,?,'public')",
                 (_pid, _pid, json.dumps(_payload), _n))
_con.commit()
for _pid, _k in (("s3post", _S3), ("tenant", _TEN)):
    _rid = _con.execute("select id from skribl_posts where public_id=?", (_pid,)).fetchone()[0]
    _con.execute("insert into skribl_post_media (post_id,media_key) values (?,?)", (_rid, _k))
_con.commit()

r = alembic(db8, "upgrade", "head")
check("the full chain applies to a database with varied URL forms",
      r.returncode == 0, (r.stderr or "").strip().splitlines()[-1:] and
      (r.stderr).strip().splitlines()[-1] or "")
_final = {(a, b) for a, b in sqlite3.connect(db8).execute(
    "select p.public_id, m.media_key from skribl_post_media m"
    " join skribl_posts p on p.id = m.post_id")}
check("a presigned S3 URL keeps its association",
      ("s3post", _S3) in _final,
      "deleted — legitimacy was inferred from the presentation URL")
check("a custom mount prefix keeps its association",
      ("tenant", _TEN) in _final, str(sorted(a for a, _ in _final)))
check("a plain /media/<key> reference is unaffected", ("plain", _OK) in _final)
check("and the genuine forgery is still NOT granted one",
      not any(a == "frameforger2" for a, _ in _final),
      "preserving valid rows must not resurrect invalid ones")

print("\nMIGRATIONS — the repair's batch size cannot change its result")
# f0a3d81b47e2 was edited after release to reduce BATCH from 500 to 25 (each row
# carries a payload of up to MAX_CONTENT_LENGTH, so 500 rows is up to 12.5 GB at
# once). Editing a released migration is otherwise forbidden here; the
# justification is that batch size affects only how much is held in memory,
# never which rows result. That justification is ASSERTED nowhere and PROVED
# here: same fixture, several batch sizes, identical output.
_mig = next((ROOT / "skribl" / "migrations" / "versions").glob("f0a3d81b47e2_*.py"), None)
check("the repair revision is present", _mig is not None)
if _mig:
    _src = _mig.read_text(encoding="utf-8")
    _declared = re.search(r"^BATCH = (\d+)", _src, re.M)
    check("the batch size is small enough to bound memory",
          _declared and int(_declared.group(1)) <= 50,
          f"BATCH={_declared.group(1) if _declared else '?'} — each row carries a "
          f"payload of up to MAX_CONTENT_LENGTH")

    _outputs = []
    for _b in (1, 7, 50):
        _db = os.path.join(tmp, f"batch{_b}.db")
        alembic(_db, "upgrade", "86171614cb85")
        _c = sqlite3.connect(_db)
        _t = datetime.now().isoformat()
        for _i in range(9):
            _k = format(_i, "x") + "0" * 63 + ".wav"
            _c.execute("insert into skribl_posts (public_id,user_id,title,"
                       "payload_json,has_audio,created_at,visibility) values"
                       " (?,1,?,?,0,?,'public')",
                       (f"b{_b}p{_i}", f"p{_i}",
                        json.dumps({"frames": [{"music": {"data": f"/media/{_k}"}}]}), _t))
        _c.commit()
        _patched = _src.replace(f"BATCH = {_declared.group(1)}", f"BATCH = {_b}", 1)
        _mig.write_text(_patched, encoding="utf-8")
        try:
            alembic(_db, "upgrade", "head")
        finally:
            _mig.write_text(_src, encoding="utf-8")
        _outputs.append(sorted(
            k for _, k in sqlite3.connect(_db).execute(
                "select post_id, media_key from skribl_post_media")))
    check("batch sizes 1, 7 and 50 produce identical associations",
          len({tuple(o) for o in _outputs}) == 1,
          f"row counts {[len(o) for o in _outputs]}")
    check("and the migration file was restored after the probe",
          _mig.read_text(encoding="utf-8") == _src)

print("\nMIGRATIONS — scoped to Skribl, never the host's tables")
db3 = os.path.join(tmp, "shared.db")
con = sqlite3.connect(db3)
con.execute("create table host_users (id integer primary key, email text)")
con.execute("insert into host_users (email) values ('someone@example.com')")
con.commit()
r = alembic(db3, "upgrade", "head")
check("Skribl's chain applies to a database it shares with a host",
      r.returncode == 0)
con = sqlite3.connect(db3)
survived = list(con.execute("select email from host_users"))
check("the host's table is untouched", survived == [("someone@example.com",)],
      str(survived))
tables = {t[0] for t in con.execute("select name from sqlite_master where type='table'")}
check("both Skribl's tables and the host's coexist",
      {"host_users", "skribl_posts", "skribl_rate_events"} <= tables,
      str(sorted(tables)))

r = alembic(db3, "revision", "--autogenerate", "-m", "scope probe")
out = (r.stdout or "") + (r.stderr or "")
check("autogenerate does NOT propose dropping the host's table",
      "host_users" not in out,
      "include_object is not filtering — a host would lose its tables")
# Clean up the probe revision so it cannot be committed by accident.
for line in out.splitlines():
    if "Generating" in line and ".py" in line:
        probe = line.split("Generating")[1].split("...")[0].strip()
        try:
            os.remove(probe)
        except OSError:
            pass

print("\nMIGRATIONS — the chain matches the models")
db4 = os.path.join(tmp, "drift.db")
alembic(db4, "upgrade", "head")
r = alembic(db4, "revision", "--autogenerate", "-m", "drift probe")
out = (r.stdout or "") + (r.stderr or "")
drift = [l for l in out.splitlines()
         if "Detected" in l and "host_users" not in l]
check("no schema drift between the migrations and the models", not drift,
      "; ".join(d.split("]")[-1].strip() for d in drift[:3]))
for line in out.splitlines():
    if "Generating" in line and ".py" in line:
        probe = line.split("Generating")[1].split("...")[0].strip()
        try:
            os.remove(probe)
        except OSError:
            pass

shutil.rmtree(tmp, ignore_errors=True)

# ---- v180: the invariants are enforced by the database, not only by Python --
# The package expects a host application to touch the same database and
# possibly construct models itself, so an invariant that authorisation depends
# on must not live only in application code.
try:
    import sqlite3 as _sq
    import tempfile as _tf

    _d = _tf.mkdtemp(prefix="skribl-v180-")
    _db = os.path.join(_d, "inv.db")
    alembic(_db, "upgrade", "head")
    _c = _sq.connect(_db)
    _c.execute("PRAGMA foreign_keys = ON")

    _fks = _c.execute("PRAGMA foreign_key_list(skribl_post_media)").fetchall()
    check("skribl_post_media has a foreign key to skribl_posts",
          any(r[2] == "skribl_posts" and r[3] == "post_id" for r in _fks),
          f"got {_fks}")
    check("and it cascades, so a deleted post takes its associations with it",
          any((r[6] or "").upper() == "CASCADE" for r in _fks),
          "otherwise the orphan sweep sees their media as still referenced")

    _c.execute("INSERT INTO skribl_posts "
               "(public_id, title, payload_json, has_audio, created_at, visibility) "
               "VALUES ('inv-1', 'inv', '{}', 0, '2026-01-01 00:00:00', 'public')")
    _pid = _c.execute("SELECT id FROM skribl_posts WHERE public_id='inv-1'").fetchone()[0]
    _c.execute("INSERT INTO skribl_post_media (post_id, media_key) VALUES (?, 'abc.png')",
               (_pid,))
    _c.commit()
    _refused = False
    try:
        _c.execute("INSERT INTO skribl_post_media (post_id, media_key) "
                   "VALUES (999999, 'ghost.png')")
        _c.commit()
    except Exception:       # noqa: BLE001
        _refused = True
        _c.rollback()
    check("an association for a post that does not exist is refused",
          _refused, "authorisation by a row nothing points at is not "
                    "authorisation")

    _c.execute("DELETE FROM skribl_posts WHERE id = ?", (_pid,))
    _c.commit()
    _left = _c.execute("SELECT COUNT(*) FROM skribl_post_media WHERE post_id = ?",
                       (_pid,)).fetchone()[0]
    check("deleting a post removes its associations", _left == 0, f"{_left} left")

    _bad = False
    try:
        _c.execute("INSERT INTO skribl_rate_events (bucket, key_hash, created_at, state) "
                   "VALUES ('posts', 'x', '2026-01-01', 'weird')")
        _c.commit()
    except Exception:       # noqa: BLE001
        _bad = True
        _c.rollback()
    check("a rate-event state outside pending/committed is refused",
          _bad, "a third value counts as neither and holds no quota slot")
    _c.close()
except Exception as _e5:    # noqa: BLE001
    check("the v180 invariants are testable", False, repr(_e5))

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
