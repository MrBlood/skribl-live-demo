"""Fill in `canvas_w` / `canvas_h` on posts written before v309.

    python -m skribl.backfill --app app:app            # what it would do
    python -m skribl.backfill --app app:app --write    # do it

WHY THIS IS A COMMAND AND NOT A MIGRATION, which is the whole point of the
file. It WAS a migration, and it took the site down twice in one afternoon.

    1. `invalid input syntax for type numeric: "{"a":1}"`
       A cast ran before the guard written above it. PostgreSQL sorts WHERE
       quals by estimated cost, so a funnel written top to bottom is not one.

    2. `psycopg.OperationalError: consuming input failed:
        SSL error: unexpected eof while reading`
       The backend went away mid-statement. Every JSON operator on a `json`
       column detoasts and re-parses the WHOLE document, and that statement
       called five of them per row -- so a table of multi-megabyte drawings
       was parsed five times per row, in one statement, on a small instance.

`Procfile` is `alembic upgrade head && gunicorn app:app`, so both of those
exited the deploy before the server started and the host kept serving the
previous build. What they were computing is COSMETIC: a null canvas size is a
supported state, and a tile without one falls back to the crop it used before
v309 existed. Nothing here is worth an outage, so nothing here runs during one.

WHAT IT DOES DIFFERENTLY:

  * ONE PARSE PER ROW, not five. The database extracts `canvasSize` -- a small
    object -- and that is all that crosses the wire. The multi-megabyte payload
    is read once by the server and never sent anywhere.
  * BOUNDED BATCHES, committed as it goes. No statement is long enough to be
    killed and no transaction is large enough to matter. Interrupt it at any
    point and the rows already written stay written.
  * RESUMABLE ACROSS RUNS. The work queue is "rows where canvas_w IS NULL", so
    re-running skips everything already written and there is no state to keep
    between runs. Within one run an id cursor carries it past rows that have no
    size to write -- without that it cannot make progress past the first such
    row, which is a bug this file shipped with for about ten minutes.
  * IT DECIDES IN PYTHON. One rule, `validation._payload_canvas`, applied to
    the small object -- so there is no second spelling of it to drift, which is
    what the SQL version was always at risk of.

EXIT CODES, because this may be run from a scheduler:
    0  it ran (including "nothing to do", including a dry run)
    1  it ran and at least one batch failed; rows before that are committed
    2  it could not run at all -- bad --app, no session, bad flags
"""
import argparse
import importlib
import sys

from .models import session as resolve_session
from .validation import _payload_canvas

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_CANNOT_RUN = 2

#: Rows per statement. Small enough that one batch is quick even when every
#: payload in it is megabytes, which is the case that killed the migration.
DEFAULT_BATCH = 200


def _die(message):
    print(f"skribl.backfill: {message}", file=sys.stderr)
    raise SystemExit(EXIT_CANNOT_RUN)


def _load_app(spec):
    """Resolve `module:attribute` to a Flask application. Exits 2 on failure."""
    if ":" not in spec:
        _die(f"--app must be module:attribute (got {spec!r}).")
    module_name, attr = spec.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:                                    # noqa: BLE001
        _die(f"--app: could not import {module_name!r}: "
             f"{type(exc).__name__}: {exc}")
    try:
        target = getattr(module, attr)
    except AttributeError:
        _die(f"--app: {module_name!r} has no attribute {attr!r}.")
    if callable(target):
        try:
            target = target()
        except Exception as exc:                                # noqa: BLE001
            _die(f"--app: calling {spec} raised {type(exc).__name__}: {exc}")
    if not hasattr(target, "app_context"):
        _die(f"--app: {spec} is not a Flask application "
             f"(got {type(target).__name__}).")
    return target


def _extract_sql(dialect):
    """SELECT id and the canvasSize SUB-OBJECT, never the payload.

    The whole design of this command is in this one expression. `payload_json`
    is the multi-megabyte column the listing endpoint defers on purpose; the
    server has to read it to reach inside, but only the small object it finds
    there crosses the wire, and it is parsed once rather than five times.

    The engine-specific spellings are the two this project deploys on and
    tests. Anything else gets the payload itself -- correct everywhere, and
    only ever reached by a host running something exotic, who can pass a small
    --batch. verify_migrations drives the sqlite branch and verify_postgres the
    postgresql one, both against payload shapes chosen to be hostile.
    """
    if dialect == "postgresql":
        return ("SELECT id, (payload_json #> '{canvasSize}')::text "
                "FROM skribl_posts WHERE canvas_w IS NULL AND id > :last "
                "ORDER BY id LIMIT :n")
    if dialect == "sqlite":
        # CASE, NOT A GUARD IN THE WHERE CLAUSE. `json_extract` RAISES
        # ("malformed JSON") on a payload that is not valid JSON, and one such
        # row kills the whole batch -- taking the rows behind it with it, which
        # is how this was found: a fixture with a bad payload near the end and
        # fillable rows after it reported 12 of 15 looked at. Putting
        # `json_valid(...)` in the WHERE would be the same mistake that killed
        # the PostgreSQL version twice, since no engine promises to evaluate
        # AND in the order written. CASE does promise it.
        return ("SELECT id, CASE WHEN json_valid(payload_json) "
                "THEN json_extract(payload_json, '$.canvasSize') END "
                "FROM skribl_posts WHERE canvas_w IS NULL AND id > :last "
                "ORDER BY id LIMIT :n")
    return ("SELECT id, payload_json FROM skribl_posts "
            "WHERE canvas_w IS NULL AND id > :last ORDER BY id LIMIT :n")


def _sizes_from(raw):
    """(w, h) for whatever the SELECT above returned for one row.

    THE RULE IS validation._payload_canvas AND ONLY THAT. Whatever shape the
    driver hands back -- a JSON string, a dict a JSON column already decoded,
    a scalar, None -- it is wrapped back into the `{"canvasSize": ...}` the one
    reader expects, rather than re-deciding what a valid size is here. Two
    spellings of that rule is exactly what the SQL version kept getting wrong.
    """
    import json
    if raw is None:
        return (None, None)
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:                                       # noqa: BLE001
            return (None, None)
    return _payload_canvas({"canvasSize": raw})


def run(session, batch=DEFAULT_BATCH, limit=None, write=False, out=sys.stdout):
    """Fill the columns in batches. Returns (looked_at, filled, failed_batches)."""
    from sqlalchemy import text

    dialect = session.get_bind().dialect.name
    select_sql = text(_extract_sql(dialect))
    update_sql = text("UPDATE skribl_posts SET canvas_w = :w, canvas_h = :h "
                      "WHERE id = :id")
    # PAGED BY id, NOT BY "IS NULL". The queue looks like it could be "rows
    # where canvas_w IS NULL", and the first version used exactly that -- which
    # cannot make progress past a row that has no size to write, because that
    # row is still NULL on the next pass and comes back for ever. Guarding the
    # spin instead of fixing it just stopped the run early: seventeen rows, a
    # batch of five, and it quit after ten with the rest never looked at. A
    # test with hostile payloads in the middle is what showed it; a test with
    # tidy ones would have agreed with the bug.
    #
    # The cursor makes unfillable rows skippable while `IS NULL` keeps the work
    # queue honest across RUNS: interrupt it, run it again, and the rows it
    # already wrote are excluded from the start.
    seen = filled = failed = 0
    last = 0
    while True:
        want = batch if limit is None else min(batch, limit - seen)
        if want <= 0:
            break
        try:
            rows = session.execute(select_sql, {"n": want, "last": last}).fetchall()
        except Exception as exc:                                # noqa: BLE001
            print(f"  batch read failed: {type(exc).__name__}: {exc}", file=out)
            return seen, filled, failed + 1
        if not rows:
            break
        for row_id, raw in rows:
            seen += 1
            last = max(last, row_id)
            w, h = _sizes_from(raw)
            if w is None:
                continue
            filled += 1
            if write:
                session.execute(update_sql, {"w": w, "h": h, "id": row_id})
        # A DRY RUN STILL PAGES. It writes nothing, so the cursor is the only
        # thing carrying it forward -- and it must, or a preview would report
        # on the first batch and call that the answer.
        if not write:
            continue
        try:
            session.commit()
        except Exception as exc:                                # noqa: BLE001
            session.rollback()
            print(f"  batch commit failed: {type(exc).__name__}: {exc}", file=out)
            failed += 1
            break
        print(f"  {seen} looked at, {filled} filled", file=out)
    return seen, filled, failed


def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m skribl.backfill",
        description="Fill canvas_w/canvas_h on posts written before v309.")
    p.add_argument("--app", default="app:app",
                   help="module:attribute of the Flask app (default app:app)")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                   help=f"rows per statement (default {DEFAULT_BATCH})")
    p.add_argument("--limit", type=int, default=None,
                   help="stop after looking at this many rows")
    p.add_argument("--write", action="store_true",
                   help="actually write; without it this is a dry run")
    return p


def main(argv=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if args.batch < 1:
        _die("--batch must be at least 1.")
    if args.limit is not None and args.limit < 1:
        _die("--limit must be at least 1.")

    app = _load_app(args.app)
    with app.app_context():
        session = resolve_session()
        if session is None:
            _die("no database session is configured on this app.")
        seen, filled, failed = run(session, batch=args.batch, limit=args.limit,
                                   write=args.write, out=out)
    verb = "filled" if args.write else "would fill"
    print(f"{seen} looked at, {filled} {verb}"
          + ("" if args.write else "  (dry run — pass --write to do it)"),
          file=out)
    return EXIT_PARTIAL if failed else EXIT_OK


if __name__ == "__main__":                                      # pragma: no cover
    raise SystemExit(main())
