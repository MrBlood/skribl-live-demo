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
"""
import os

threads = int(os.environ.get("GUNICORN_THREADS") or 8)
