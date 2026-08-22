"""Harness-owned Flask host for the cross-worker failed-post regression.

NOT the demo app. app.py must not grow a test-only failure hook, so this
module mounts the same Skribl blueprint on a host whose after_request commit
can be made to fail by a request header — X-Skribl-Fail-Commit: 1 — the way
routes.py's own transaction-contract tests inject the failure. Run under
gunicorn with two or more workers so "worker A fails, worker B retries" is
two real processes on one real database.

Every response carries X-Skribl-Worker: <pid> so the test can prove the
retry really landed on a different process.
"""
import os

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

import skribl
import skribl.models

app = Flask("skribl-f3-host")
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.environ["DATABASE_URL"],
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get("SECRET_KEY", "f3-host"),
    SKRIBL_RATE_BACKEND=os.environ.get("SKRIBL_RATE_BACKEND", "db"),
    SKRIBL_RATE_MAX_POSTS=int(os.environ.get("SKRIBL_RATE_MAX_POSTS", "1")),
    SKRIBL_RATE_MAX_ATTEMPTS=int(os.environ.get("SKRIBL_RATE_MAX_ATTEMPTS", "500")),
)
db = SQLAlchemy()
db.init_app(app)
skribl.init_skribl(app, session=lambda: db.session)
skribl.models.attach_to_metadata(db.metadata)
with app.app_context():
    db.create_all()


@app.after_request
def _commit(resp):
    resp.headers["X-Skribl-Worker"] = str(os.getpid())
    if resp.status_code < 500:
        if request.headers.get("X-Skribl-Fail-Commit") == "1":
            raise RuntimeError("injected host commit failure")
        db.session.commit()
    return resp


@app.teardown_request
def _rollback(exc):
    db.session.rollback()
