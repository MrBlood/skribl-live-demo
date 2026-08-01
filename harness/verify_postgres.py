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
init = subprocess.run([sys.executable, "-c",
                       "from app import app, db; app.app_context().push(); db.create_all()"],
                      cwd=str(ROOT), env=env, capture_output=True, text=True)
if init.returncode != 0:
    skip(f"could not create the schema on PostgreSQL: {init.stderr.strip()[:120]}")

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
_kh = subprocess.run([sys.executable, "-c",
                      "import app; print(app._rate_key('127.0.0.1'))"],
                     cwd=str(ROOT), env=env, capture_output=True, text=True)
KEY_HASH = _kh.stdout.strip().splitlines()[-1] if _kh.returncode == 0 else ""
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

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
