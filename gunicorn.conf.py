"""How gunicorn runs Skribl. `gunicorn app:app`, run from this folder (the
Procfile's command and Render's start command alike), reads this file by its
name, so neither command has to change.

THREADS: each worker answers several requests at once. One sync worker
answered one at a time, and an editor's first open asks for about 120 files:
on the live demo they came back 25 to 40 ms apart, 5 to 9 s in all (owner,
Nov 8: "it takes over 5 seconds to load on first time"). Threads cost nothing
on the same instance. The app already runs threaded in every harness run (the
dev server is threaded), its in-memory limiter takes a lock, and production's
limiter is the database. WEB_CONCURRENCY, where a host sets it, still decides
how many workers there are; this decides how much each one can hold.
verify_hostconfig asks gunicorn what it resolves.

WARM BEFORE THE FIRST VISITOR: each worker strips and compresses every Skribl
script and style before it takes a request (post_worker_init, below). That work
is done once per file and kept, but it used to fall on the first visitor after
each start: on the live demo, the Pad's files took 8.8 s of server work the
first time. A worker that is warming queues its first requests for those few
seconds instead, and every open after is quick.

THE SITE'S OWN TABLES, ONCE PER START, BEFORE ANY WORKER (on_starting). The
site at /social keeps its tables on a migration chain of its own
(social/alembic.ini). Render does not read the Procfile, and its start
command lives in its dashboard (`python -m alembic upgrade head && gunicorn
app:app`, Skribl's chain), so the site's chain is run from here, which both
that command and the Procfile reach: in gunicorn's master, once, before any
worker loads the app. CAREFULLY: a site chain that fails or hangs never
stops the demo. It is logged, loudly, with alembic's own last lines (any
database address in them blanked), the server starts anyway, and the site's
sign-in rests (a kind 503 on its pages) until the tables are there, while
the Pad, Flip and the rest of the demo serve as before. SKRIBL_SOCIAL=0, or a
package without social/, skips it.

THE STAND-IN BESIDE THE DEMO, AFTER IT AND IN THE BACKGROUND. app.py mounts
examples/host_app at /host: a second Flask app with a Skribl of its own, so
caches of its own that start empty, and the first open of its Pad paid what
the demo's used to. Each app mounted beside the demo is warmed on a thread of
its own once the demo's files are done, resting a moment after each file:
Python runs one thread at a time, and unrested the stand-in's 5 s of work held
the demo's own visitors (on the dev box the demo's Pad opened in 1.4-1.8 s
beside it unrested, 0.4 s rested, 0.2 s with nothing beside it; rested, the
stand-in is done in about 22 s). A request that arrives mid-warm-up does its
file itself, which is what every request did before there was a warm-up.
"""
import os
import re
import subprocess
import sys
import threading
import time

threads = int(os.environ.get("GUNICORN_THREADS") or 8)

#: The rest after each of the stand-in's files (the docstring's last paragraph).
#: Underscored, so gunicorn never reads it as one of its settings.
_BESIDE_REST = 0.1
#: How long the site's chain may take before the server starts without it.
_SITE_CHAIN_SECONDS = 120


def on_starting(server):
    """Bring the site's own tables up to date, once, before any worker (the
    docstring's last paragraph). Never raises: the demo starts whatever
    happens here."""
    try:
        _site_chain(server.log)
    except Exception:
        server.log.exception("social: the site's tables were not brought up to date; the demo "
                             "serves on, and the site's sign-in rests until they are")


def _site_chain(log):
    if os.environ.get("SKRIBL_SOCIAL", "1").strip() == "0":
        return
    here = os.path.dirname(os.path.abspath(__file__))
    ini = os.path.join(here, "social", "alembic.ini")
    if not os.path.isfile(ini):
        log.info("social: no site in this package (social/alembic.ini); nothing to migrate")
        return
    try:
        done = subprocess.run([sys.executable, "-m", "alembic", "-c", ini, "upgrade", "head"],
                              cwd=here, capture_output=True, text=True, timeout=_SITE_CHAIN_SECONDS)
    except subprocess.TimeoutExpired:
        log.error("social: the site's tables took over %d s to bring up to date and were left; "
                  "the demo serves on, and the site's sign-in rests until they are",
                  _SITE_CHAIN_SECONDS)
        return
    said = _blank_addresses((done.stderr or "") + (done.stdout or ""))
    if done.returncode == 0:
        log.info("social: the site's tables are up to date (social_alembic_version at head)")
    else:
        last = " | ".join(line.strip() for line in said.strip().splitlines()[-4:])
        log.error("social: the site's tables could not be brought up to date (alembic exited %d); "
                  "the demo serves on, and the site's sign-in rests until they are: %s",
                  done.returncode, last[-600:])


def _blank_addresses(text):
    """A database address can carry its password: none reaches the log."""
    return re.sub(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://\S+", "<database address>", text)


def post_worker_init(worker):
    """Run by gunicorn in each worker after the app loads and before the
    worker takes a request. worker.notify after each file keeps gunicorn's
    timeout from taking a long warm-up for a hung worker. A warm-up that
    fails is logged and the worker serves anyway: each file is then done on
    its first request, as before."""
    try:
        import skribl
        t0 = time.monotonic()
        n = skribl.warm_assets(worker.wsgi, tick=worker.notify)
        worker.log.info("skribl: %d files stripped and compressed before the "
                        "first visitor (%.1f s)", n, time.monotonic() - t0)
    except Exception:
        worker.log.exception("skribl: warming the files failed; each is done "
                             "on its first request instead")
    # What app.py mounted beside the demo (the stand-in at /host), each on a
    # thread of its own: see the module's last paragraph. A plain attribute
    # read, so a host whose app is not wrapped this way starts no thread.
    beside = getattr(getattr(worker.wsgi, "wsgi_app", None), "mounts", None)
    for prefix, other in (beside or {}).items():
        threading.Thread(target=_warm_beside, args=(worker, prefix, other),
                         name="skribl warm " + prefix, daemon=True).start()


def _warm_beside(worker, prefix, other):
    """Warm an app mounted beside the demo, off the worker's request path,
    resting after each file so the demo's visitors are not held for it. A
    failure is logged and changes nothing else: that app's files are then done
    on their first request, as before."""
    try:
        import skribl
        t0 = time.monotonic()
        n = skribl.warm_assets(other, tick=lambda: time.sleep(_BESIDE_REST))
        if n:
            worker.log.info("skribl: %d files stripped and compressed for %s, "
                            "beside the first visitors (%.1f s)",
                            n, prefix, time.monotonic() - t0)
    except Exception:
        worker.log.exception("skribl: warming %s's files failed; each is done "
                             "on its first request instead", prefix)
