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
"""
import os
import time

threads = int(os.environ.get("GUNICORN_THREADS") or 8)


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
