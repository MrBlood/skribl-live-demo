"""Two saves of one account draft at once: one wins, one is a conflict, nothing is lost.

THE FINDING (the v328 audit's AUD-002). PUT /api/drafts/<id> with
baseUpdatedAt compared the stored draft with the copy the save was made from,
under with_for_update(). SQLite has no row lock, so on SQLite the comparison
locked nothing. Two saves made from one copy both passed it, and then either
the second waited out SQLite's write lock and answered 500 (the auditor: three
of three, with two requests held together after both had read the draft), or,
had it written after the first committed, replaced the first without a word.
The overwrite now carries the comparison itself, and a save the write lock
refuses is answered as the conflict it is (skribl/drafts.py save_draft).

DRIVEN THROUGH THE GUIDE'S OWN HOST (docs/INTEGRATION.md: a Flask app, its own
SQLAlchemy, a commit after each request under 500 and a rollback in teardown),
in-process with Flask's test client on two threads. Where two saves have to
meet at one moment, they are held at the comparison (drafts._instant, the
first call each makes), as the auditor's probe held them; the code under test
is not changed. On SQLite always, on a temporary file; on PostgreSQL too when
DATABASE_URL names one (CI's postgres jobs), as an author of its own whose rows
are deleted after. No server, no browser.
"""
import os
import secrets
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from assertions import make_check  # noqa: E402
from flask import Flask  # noqa: E402
from flask_sqlalchemy import SQLAlchemy  # noqa: E402
from sqlalchemy import event as sa_event  # noqa: E402

import skribl  # noqa: E402
import skribl.drafts as drafts  # noqa: E402
import skribl.models  # noqa: E402

results = []
check = make_check(results, with_detail=True)
TRIALS = 20
PAYLOAD = {"frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}]}


def host(url, author):
    """The smallest host docs/INTEGRATION.md gives, on `url`, signed in as `author`."""
    app = Flask(f"draftrace-{author}")
    app.config.update(SECRET_KEY="harness-draftrace", SQLALCHEMY_DATABASE_URI=url,
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db = SQLAlchemy()
    db.init_app(app)
    skribl.models.attach_to_metadata(db.metadata)
    skribl.init_skribl(app, session=lambda: db.session, current_user_id=lambda: author, csrf=False)

    @app.after_request
    def commit_request(response):
        if response.status_code < 500:
            db.session.commit()
        return response

    @app.teardown_request
    def rollback_request(exc):
        db.session.rollback()

    with app.app_context():
        db.create_all()
    return app, db


def body(title, base=None):
    b = {"kind": "pad", "title": title, "payload": PAYLOAD}
    if base is not None:
        b["baseUpdatedAt"] = base
    return b


def put(app, did, title, base):
    try:
        with app.test_client() as c:
            r = c.put(f"/api/drafts/{did}", json=body(title, base))
            j = r.get_json(silent=True) or {}
            return r.status_code, j
    except Exception as exc:          # a 500 the test client raised, said as one
        return 500, {"error": repr(exc)}


def held_at_compare(fn):
    """Run `fn` with drafts._instant wrapped: each thread's first call goes to
    `fn(thread_name)` before it compares. Put back afterwards whatever happens."""
    real, local = drafts._instant, threading.local()

    def hook(v):
        if not getattr(local, "seen", False):
            local.seen = True
            fn(threading.current_thread().name)
        return real(v)
    drafts._instant = hook
    return real


def run_on(name, url):
    author = "draftrace-" + secrets.token_hex(4)
    app, db = host(url, author)
    c = app.test_client()

    def fresh(title):
        r = c.post("/api/drafts", json=body(title))
        return r.get_json()["id"], r.get_json()["updatedAt"]

    def title_of(did):
        return c.get(f"/api/drafts/{did}").get_json().get("title")

    sqlite = url.startswith("sqlite")

    # 1. TOGETHER: both saves read the draft, then both go on at once. On
    # PostgreSQL the row lock queues them and the second meets the first's save:
    # a conflict. On SQLite one writes and the other is told the drafts are busy;
    # saving again, it meets the first's save and is the conflict it is.
    tally, odd = {}, []
    for k in range(TRIALS):
        did, base = fresh(f"race {k}")
        # On PostgreSQL the second save waits at the row lock before it can
        # reach the comparison, so the two never meet there: a short wait.
        gate = threading.Barrier(2, timeout=10 if sqlite else 0.3)

        def meet(_):
            try:
                gate.wait()
            except threading.BrokenBarrierError:
                pass
        real = held_at_compare(meet)
        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                got = list(ex.map(lambda n: put(app, did, f"device {n}", base), (1, 2)))
        finally:
            drafts._instant = real
        shape = tuple(sorted((s_, "busy" if j.get("busy") else "conflict" if j.get("conflict") else "")
                             for s_, j in got))
        tally[shape] = tally.get(shape, 0) + 1
        win = [j for s_, j in got if s_ == 200]
        lose = [j for s_, j in got if s_ != 200]
        final = title_of(did)
        again = put(app, did, "the other device, again", base) if lose else (None, {})
        want = (200, "") , (409, "busy" if sqlite else "conflict")
        if shape != tuple(sorted(want)) or final != (win[0].get("title") if win else None) \
                or again[0] != 409 or again[1].get("conflict") is not True \
                or (again[1].get("current") or {}).get("title") != final:
            odd.append((k, got, final, again))
    check(f"{name}: {TRIALS} pairs of saves made together from one copy: each time one is saved and "
          f"the other is {'told the drafts are busy' if sqlite else 'a conflict'}, never a 500; saving "
          "again, it meets the saved one as a conflict (so the editor keeps both)",
          not odd and sum(tally.values()) == TRIALS,
          f"outcomes {tally}; first odd one {odd[:1]}")

    # 2. A SAVE THAT MEETS SOMEBODY ELSE'S WRITE: on SQLite the lock is the whole
    # file's, so what a save meets may be any write. It is never answered as a
    # conflict (the editor would say this draft changed on another device and
    # save a copy), and saving again goes through.
    mine, base = fresh("mine")
    other, _ = fresh("another draft")
    paused, wrote = threading.Event(), threading.Event()

    def wait_for_other(who):
        if who == "mine":
            paused.set()
            wrote.wait(10)
    with app.app_context():
        engine = db.engine

    def saw(conn, cursor, statement, *a):
        if threading.current_thread().name == "other" and statement.lstrip().upper().startswith("UPDATE"):
            wrote.set()
    sa_event.listen(engine, "after_cursor_execute", saw)
    real = held_at_compare(wait_for_other)
    out = {}
    try:
        t1 = threading.Thread(name="mine", target=lambda: out.setdefault("mine", put(app, mine, "mine, saved", base)))
        t1.start()
        paused.wait(10)
        t2 = threading.Thread(name="other", target=lambda: out.setdefault("other", put(app, other, "the other, saved", None)))
        t2.start()
        wrote.wait(10)
        t1.join(20)
        t2.join(20)
    finally:
        drafts._instant = real
        sa_event.remove(engine, "after_cursor_execute", saw)
    m, o = out.get("mine", (None, {})), out.get("other", (None, {}))
    retry = put(app, mine, "mine, saved", base) if m[0] != 200 else m
    check(f"{name}: a save that meets a write to another draft is never a conflict and never a 500 "
          "(busy at most), and saving again goes through",
          o[0] == 200 and m[0] in (200, 409) and not m[1].get("conflict")
          and (m[0] == 200 or m[1].get("busy") is True) and retry[0] == 200
          and title_of(mine) == "mine, saved" and title_of(other) == "the other, saved",
          f"mine {m[0]} {m[1].get('error') or ''}, the other {o[0]}, mine again {retry[0]}, "
          f"stored {title_of(mine)!r} / {title_of(other)!r}")

    # 3. What was right stays right.
    did, base = fresh("one")
    r1 = put(app, did, "two", base)
    r2 = put(app, did, "three", r1[1].get("updatedAt"))
    r3 = put(app, did, "stale", base)
    check(f"{name}: one device saving again and again is never a conflict with itself, and a save "
          "from an older copy still is",
          r1[0] == 200 and r2[0] == 200 and r3[0] == 409 and title_of(did) == "three",
          f"{r1[0]}, {r2[0]}, stale {r3[0]}, stored {title_of(did)!r}")
    r4 = put(app, did, "an older client", None)
    check(f"{name}: a save with no baseUpdatedAt (an older client, a host's own code) still "
          "overwrites, as before",
          r4[0] == 200 and title_of(did) == "an older client", f"{r4[0]}, stored {title_of(did)!r}")

    with app.app_context():
        db.session.query(skribl.models.SkriblDraft).filter_by(user_id=author).delete()
        db.session.commit()


print("DRAFT RACE — two saves of one draft at once (the v328 audit's AUD-002)")
_tmp = tempfile.mkdtemp(prefix="skribl-draftrace-")
run_on("SQLite", f"sqlite:///{_tmp}/drafts.db")
_pg = os.environ.get("DATABASE_URL", "")
if _pg.startswith("postgres"):
    # Spelled for psycopg 3 as app.py spells it: a bare postgresql:// (CI's)
    # would ask SQLAlchemy for psycopg2, which the lock does not carry.
    for bare in ("postgresql://", "postgres://"):
        if _pg.startswith(bare):
            _pg = "postgresql+psycopg://" + _pg[len(bare):]
    run_on("PostgreSQL", _pg)
else:
    print("  (DATABASE_URL names no PostgreSQL here: CI's postgres jobs run that half)")

bad = [r for r in results if not r[0]]
print(f"\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
