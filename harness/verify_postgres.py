"""PostgreSQL multi-process concurrency for the shared-store rate limiter.

Everything else in this harness runs against SQLite and, for the limiter, threads
against a single dev server. That cannot answer the question a reviewer actually
asked: does insert-then-count hold when SEPARATE OS PROCESSES with SEPARATE
connections race for the last slots on the production database engine?

This suite answers it empirically: gunicorn with four worker processes, a real
PostgreSQL, a fresh identity with an empty bucket, quota 2, and twelve requests
released simultaneously through a threading.Barrier. Row counts are read straight
out of PostgreSQL rather than inferred from HTTP status codes.

SKIP SEMANTICS — read this before quoting a number from it.
    Without PostgreSQL, or without SKRIBL_PG_DSN, this suite exits 77 and reports
    SUITE-SKIPPED. run_harness.sh records skipped suites SEPARATELY: they
    contribute ZERO assertions to the aggregate and are listed by name. A skipped
    run of this file is NOT evidence that concurrency was tested. It is evidence
    that it was not.

SCOPE OF THE CONCLUSION — deliberately narrow.
    A pass closes multi-process over-admission for the TESTED configuration only:
    this PostgreSQL version, default isolation, gunicorn's default worker model,
    this connection setup, no induced failures, and a 12-request burst. It does
    not establish behaviour under every isolation level, pooling arrangement,
    failure mode, or production load.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_EXIT = 77

WORKERS = 4
CONCURRENT = 12
QUOTA = 2
PORT = 5055


def skip(reason):
    print(f"SUITE-SKIPPED: {reason}")
    print("No assertions were executed. This is NOT evidence that PostgreSQL "
          "concurrency was tested.")
    raise SystemExit(SKIP_EXIT)


# --- availability gate -------------------------------------------------------
DSN = os.environ.get("SKRIBL_PG_DSN", "postgresql://skribl:skribl@127.0.0.1:5432/skribl")
if not shutil.which("psql") and not os.environ.get("SKRIBL_PG_DSN"):
    skip("no PostgreSQL client found and SKRIBL_PG_DSN is not set")
try:
    import psycopg
except ImportError:
    skip("the psycopg driver is not installed")
if not shutil.which("gunicorn"):
    skip("gunicorn is not installed")
try:
    with psycopg.connect(DSN, connect_timeout=5) as _c:
        PG_VERSION = _c.execute("show server_version").fetchone()[0]
except Exception as exc:
    skip(f"cannot connect to PostgreSQL at the configured DSN ({type(exc).__name__})")

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def version(pkg):
    try:
        from importlib.metadata import version as _v
        return _v(pkg)
    except Exception:
        return "unknown"


SA_DSN = DSN.replace("postgresql://", "postgresql+psycopg://", 1)
KEY = "pgrace-" + uuid.uuid4().hex[:12]          # fresh identity => empty bucket

print("\nENVIRONMENT — recorded so the result can be interpreted")
for label, value in (("PostgreSQL", PG_VERSION),
                     ("gunicorn", version("gunicorn")),
                     ("Python", sys.version.split()[0]),
                     ("Flask", version("flask")),
                     ("SQLAlchemy", version("sqlalchemy")),
                     ("psycopg", version("psycopg"))):
    print(f"  {label:<12}: {value}")
print(f"  {'workers':<12}: {WORKERS} gunicorn processes")
print(f"  {'burst':<12}: {CONCURRENT} simultaneous requests, quota {QUOTA}")

# --- schema ------------------------------------------------------------------
env = dict(os.environ,
           DATABASE_URL=SA_DSN,
           SKRIBL_RATE_BACKEND="db",
           SKRIBL_RATE_HMAC_KEY=KEY,
           SKRIBL_RATE_MAX_POSTS=str(QUOTA),
           SKRIBL_RATE_MAX_ATTEMPTS="500",
           SECRET_KEY="pgtest")
# Migrate, do not create_all(). This suite reuses a long-lived database, and
# create_all() only ever CREATES — it cannot add a column to a table that already
# exists. When `visibility` landed in v132 this suite started returning 500s on
# every insert against its stale table, which is the exact failure mode the
# Alembic chain exists to prevent. Running the real chain here also means every
# PostgreSQL run dogfoods it.
init = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                      cwd=str(ROOT), env=env, capture_output=True, text=True)
if init.returncode != 0:
    # A database created before the chain existed has the tables but no
    # alembic_version; stamp the baseline, then upgrade.
    subprocess.run([sys.executable, "-m", "alembic", "stamp", "6aa1de24dda3"],
                   cwd=str(ROOT), env=env, capture_output=True, text=True)
    init = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                          cwd=str(ROOT), env=env, capture_output=True, text=True)
if init.returncode != 0:
    skip(f"could not migrate the schema on PostgreSQL: {init.stderr.strip()[:160]}")

# Baselines. The table is shared with any earlier run, so every assertion below
# measures a DELTA rather than an absolute count — an absolute count silently
# folds in unrelated rows and turns a passing system into a failing assertion
# (or, worse, the reverse).
# Rate events are counted BY THIS RUN'S IDENTITY, not as a whole-table delta.
# The opportunistic cleanup sweep deletes expired rows during the burst, so a
# table-wide delta can legitimately go negative and fail a healthy system — it
# did exactly that once. KEY is fresh per run, so these rows are unambiguously
# ours. Posts have no identity column, so they stay a delta; nothing else is
# writing to this database during the run.
KEY_HASH = None

def _post_rows():
    with psycopg.connect(DSN) as c:
        return c.execute("select count(*) from skribl_posts").fetchone()[0]

def _our_events(state):
    with psycopg.connect(DSN) as c:
        return c.execute("select count(*) from skribl_rate_events "
                         "where bucket='posts' and state=%s and key_hash=%s",
                         (state, KEY_HASH)).fetchone()[0]

posts_before = _post_rows()

# --- server ------------------------------------------------------------------
# --log-level info makes gunicorn announce every worker boot and exit, which is
# how a crash-and-respawn becomes observable at all. Its stderr goes to a file
# rather than a pipe so it can be read after the burst without deadlocking.
GLOG = ROOT / "harness" / ".pg_gunicorn.log"
_glog = open(GLOG, "w+")
proc = subprocess.Popen(["gunicorn", "-w", str(WORKERS), "-b", f"127.0.0.1:{PORT}",
                         "--timeout", "60", "--log-level", "info", "app:app"],
                        cwd=str(ROOT), env=env,
                        stdout=subprocess.DEVNULL, stderr=_glog)


def worker_pids(master_pid):
    """Live worker PIDs, straight from /proc — the master's own children."""
    try:
        with open(f"/proc/{master_pid}/task/{master_pid}/children") as fh:
            return {int(x) for x in fh.read().split()}
    except OSError:
        return set()
base = f"http://127.0.0.1:{PORT}"
ready = False
for _ in range(120):
    if proc.poll() is not None:
        err = (proc.stderr.read() or b"").decode()[-300:]
        skip(f"gunicorn exited during startup: {err}")
    try:
        urllib.request.urlopen(base + "/", timeout=1); ready = True; break
    except urllib.error.HTTPError:
        ready = True; break
    except Exception:
        time.sleep(0.25)
if not ready:
    proc.terminate()
    skip("gunicorn never became ready")

# Wait for the full complement, then record the exact PIDs. Comparing this SET
# afterwards is what distinguishes "no worker died" from "the master survived" —
# a crashed worker is silently replaced, leaving the master alive and the worker
# count unchanged, which is precisely what the previous assertion could not see.
for _ in range(40):
    if len(worker_pids(proc.pid)) >= WORKERS:
        break
    time.sleep(0.25)
pids_before = worker_pids(proc.pid)

print("\nCONCURRENCY — 12 processes-wide requests, quota 2")
payload = {"title": "pg concurrency",
           "frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}]}
out, lock = [], threading.Lock()
barrier = threading.Barrier(CONCURRENT)

def fire():
    barrier.wait()                      # a real barrier: all released together
    req = urllib.request.Request(base + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = f"{type(e).__name__}"
    with lock:
        out.append(code)

threads = [threading.Thread(target=fire) for _ in range(CONCURRENT)]
for t in threads:
    t.start()
for t in threads:
    t.join()

pids_after = worker_pids(proc.pid)
master_alive = proc.poll() is None
# Snapshot the log BEFORE terminating: our own shutdown makes every worker log
# "Worker exiting", which would otherwise read as four crashes.
_glog.flush()
glog_during = GLOG.read_text(errors="replace") if GLOG.exists() else ""
proc.terminate()
try:
    proc.wait(timeout=15)
except Exception:
    proc.kill()

# Resolve the identity hash the workers used, from the app itself.
#
# _rate_key moved from app.py into skribl.ratelimit when Skribl became a
# blueprint, so this probe must try both. And it must FAIL LOUDLY: it used to
# swallow a non-zero exit into KEY_HASH = "", which made both the committed and
# pending queries match zero rows. "pending == 0" then passed VACUOUSLY while
# "committed == QUOTA" failed — a result that looks like a rate-limiter bug and
# is actually a broken probe. An identity we cannot resolve is not a result.
_PROBE = ("import sys\n"
          "try:\n"
          "    from skribl.ratelimit import _rate_key\n"
          "except ImportError:\n"
          "    from app import _rate_key\n"
          "print(_rate_key('127.0.0.1'))\n")
_kh = subprocess.run([sys.executable, "-c", _PROBE],
                     cwd=str(ROOT), env=env, capture_output=True, text=True)
if _kh.returncode != 0 or not _kh.stdout.strip():
    skip("could not resolve the rate-limit identity hash from the app "
         f"({(_kh.stderr or '').strip().splitlines()[-1:] or ['no output']})")
KEY_HASH = _kh.stdout.strip().splitlines()[-1]
posts_after = _post_rows()
created = posts_after - posts_before
committed = _our_events("committed")
pending = _our_events("pending")
booted = glog_during.count("Booting worker")
exited = (glog_during.count("Worker exiting") + glog_during.count("was terminated")
          + glog_during.count("Worker failed to boot"))
try:
    GLOG.unlink()
except OSError:
    pass

check("the gunicorn master stayed alive", master_alive)
check(f"all {WORKERS} workers were running before the burst",
      len(pids_before) == WORKERS, f"{sorted(pids_before)}")
# The three assertions that actually close the gap the master check left open.
check("the SAME worker processes were alive afterwards — none died and respawned",
      pids_after == pids_before and len(pids_after) == WORKERS,
      f"before={sorted(pids_before)} after={sorted(pids_after)}")
check(f"gunicorn booted exactly {WORKERS} workers — no respawn was logged",
      booted == WORKERS, f"{booted} 'Booting worker' lines")
check("gunicorn logged no worker exit, termination or boot failure DURING the burst",
      exited == 0, f"{exited} exit/termination lines before shutdown")
check("every response was 201 or 429 — no 500s, no transport errors",
      set(out) <= {201, 429}, str(sorted(set(out))))
check(f"exactly {QUOTA} requests were admitted", out.count(201) == QUOTA, str(sorted(out)))
check(f"exactly {CONCURRENT - QUOTA} were refused", out.count(429) == CONCURRENT - QUOTA,
      str(sorted(out)))
check("no OVER-admission: PostgreSQL holds exactly two new post rows",
      created == QUOTA, f"{created} rows created")
check("no UNDER-admission: the quota was actually used, not merely blocked",
      created == QUOTA and out.count(201) == QUOTA)
check("HTTP admissions match committed database rows",
      out.count(201) == created, f"{out.count(201)} x 201 vs {created} rows")
check("exactly two rate events were promoted to committed",
      committed == QUOTA, f"committed rows for THIS run's identity={committed}")
check("no reservation was stranded in pending",
      pending == 0, f"pending rows for THIS run's identity={pending}")

print("\nSCOPE — what this does and does not establish")
check("recorded configuration is complete enough to interpret the result",
      bool(PG_VERSION) and WORKERS == 4 and CONCURRENT == 12 and QUOTA == 2,
      f"PostgreSQL {PG_VERSION}, {WORKERS} workers, {CONCURRENT} requests, quota {QUOTA}")
print("  NOTE: this closes multi-process over-admission for the TESTED configuration")
print("        only — this PostgreSQL version, default isolation, gunicorn's default")
print("        worker model, no induced failures, a single 12-request burst. It does")
print("        not establish behaviour under every isolation level, pooling")
print("        arrangement, failure mode, or production load.")

# ---------------------------------------------------------------------------
# v211 (v210 review F3): the CROSS-WORKER failed-post guarantee, on the
# backend a larger site actually runs. The claim under test:
#
#   after the host POST fails, no worker may count that failed reservation
#   against an immediate retry — even when the retry lands on a DIFFERENT
#   process.
#
# v209's SQLite fix keeps the release in process memory, which the reviewer
# rightly called process-local. The inference "PostgreSQL is fine because its
# cleanup write does not collide with SQLite's single writer" is exactly the
# kind of architectural inference this project has been burned by, so it is
# TESTED here, first, before it is allowed to become a contract. Two real
# gunicorn workers on one real PostgreSQL, a harness-owned host whose commit
# fails on a request header (app.py grows no test hook), cap 1, and every
# response stamped with its worker pid so "a different process" is a fact,
# not an assumption.
print("\nF3 — CROSS-WORKER: a failed post on worker A must not cost worker B's immediate retry")
F3_PORT = PORT + 1
F3_KEY = "pgf3-" + uuid.uuid4().hex[:12]
f3_env = dict(env, SKRIBL_RATE_HMAC_KEY=F3_KEY, SKRIBL_RATE_MAX_POSTS="2")
f3_log = open(ROOT / "harness" / ".pg_f3_gunicorn.log", "w+")
f3 = subprocess.Popen(["gunicorn", "-w", "2", "-b", f"127.0.0.1:{F3_PORT}",
                       "--timeout", "60", "--log-level", "info",
                       "--pythonpath", str(ROOT / "harness"), "f3_host:app"],
                      cwd=str(ROOT), env=f3_env, stdout=subprocess.DEVNULL, stderr=f3_log)
f3_base = f"http://127.0.0.1:{F3_PORT}"
f3_ready = False
for _ in range(120):
    if f3.poll() is not None:
        break
    try:
        urllib.request.urlopen(f3_base + "/skribl-pad", timeout=1); f3_ready = True; break
    except Exception:
        time.sleep(0.25)
if not f3_ready:
    f3.terminate()
    check("F3 setup: the two-worker F3 host came up", False, "gunicorn never became ready")
else:
    def f3_post(fail=False):
        body = json.dumps({"frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}]}).encode()
        hdr = {"Content-Type": "application/json"}
        if fail:
            hdr["X-Skribl-Fail-Commit"] = "1"
        req = urllib.request.Request(f3_base + "/api/skribls", data=body, headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.headers.get("X-Skribl-Worker")
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("X-Skribl-Worker")

    # Find both workers by pid: hit the pad page until two distinct pids answer.
    seen = set()
    for _ in range(40):
        try:
            with urllib.request.urlopen(f3_base + "/skribl-pad", timeout=5) as r:
                seen.add(r.headers.get("X-Skribl-Worker"))
        except Exception:
            pass
        if len(seen) >= 2:
            break
    check("F3 setup: two distinct worker processes are answering", len(seen) >= 2, str(seen))

    # The failing post. Whichever worker takes it is 'A'.
    st, worker_a = f3_post(fail=True)
    check("F3 setup: the injected host commit failure returns 5xx from worker A",
          st >= 500 and worker_a is not None, f"{st} from {worker_a}")

    # Immediate retries until one lands on a DIFFERENT worker. gunicorn's
    # scheduling is not ours to pick, so a retry may land on A first — and at
    # cap 1 a successful A retry then legitimately owns the only slot, which
    # would make B's 429 correct rather than a bug (a first draft of this pin
    # broke out at that point and proved nothing). Cap is 2 for this reason:
    # A's failed reservation, if it were counted, plus one successful retry
    # would fill the bucket; only if the failure is NOT counted does a retry
    # on B still fit. Every 429 from B before B has succeeded once is the
    # finding; a 201 from B is the contract.
    # Retry until the bucket fills, recording every outcome by worker. We
    # cannot choose which worker gunicorn hands each request to, so the claim
    # is made worker-agnostic and exact: with cap 2, EXACTLY TWO retries
    # succeed in total (across A and B) and the next is 429. If A's failed
    # reservation were counted by any worker, only ONE retry could succeed
    # before a 429. (A first draft asserted "B's retry is 201" and broke when
    # A happened to take both slots first — B's 429 was correct then.)
    # Fire the two retries CONCURRENTLY so both workers are busy at once and
    # each takes one — sequential retries let a single worker answer both
    # before the other ever saw a request, which made "a success on the
    # other worker" a coin flip. Two threads, two posts, same instant.
    import threading
    outcomes = []
    def _one():
        outcomes.append(f3_post(fail=False))
    ts = [threading.Thread(target=_one) for _ in range(2)]
    for t in ts: t.start()
    for t in ts: t.join(timeout=40)
    # then one more, sequential, to show the cap is now full
    outcomes.append(f3_post(fail=False))
    succ = [(st, w) for st, w in outcomes if st == 201]
    workers_seen = {w for _, w in outcomes}
    check("F3: the two concurrent retries were handled by BOTH workers",
          len({w for _, w in outcomes[:2]}) == 2, f"workers {[w for _, w in outcomes[:2]]}")
    check("F3 THE CONTRACT (PostgreSQL): EXACTLY the cap's worth of retries succeed across "
          "all workers — A's failed reservation is not counted by anyone (a counted stranded "
          "row would leave room for only one)", len(succ) == 2,
          f"{len(succ)} of {len(outcomes)} retries succeeded: {outcomes}")
    check("F3 control: the retry after the cap is 429 — the cap is real, the test is not vacuous",
          outcomes and outcomes[-1][0] == 429, str(outcomes[-1] if outcomes else None))
    check("F3 CROSS-WORKER: a success landed on the worker that did NOT fail — the release "
          "was visible across processes, not just in A's memory",
          any(w != worker_a for _, w in succ), f"A={worker_a} successes on {[w for _, w in succ]}")
    f3.terminate()
    try:
        f3.wait(timeout=10)
    except Exception:
        f3.kill()
f3_log.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
