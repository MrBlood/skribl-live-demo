"""Fill in `line_json` on posts written before the in-post line.

    python -m skribl.backfill_line            # what it would do
    python -m skribl.backfill_line --write    # do it

The line under a post in a feed says "Drawn in 15 sec · watching at 1x" over a
scrubber in the drawing's shape before anybody presses play, from a column the
listing can read (the payload it cannot). New posts carry it from the moment
they are made (creation.py); this is for the ones made before.

A COMMAND, NOT A MIGRATION, for the reason skribl/backfill_canvas.py gives at
length: v309 put its backfill in a revision and took the site down twice, and
what is computed here is as cosmetic as what was computed there. A null is a
supported state -- the line says what it can without one -- so nothing here
runs during a deploy. The shape is that file's, deliberately:

  * BOUNDED BATCHES, committed as it goes; interrupt it and what is written
    stays written. SMALLER batches than the canvas one (25, not 200), because
    what crosses the wire here is a drawing's whole stroke list, not a size.
  * PAGED BY id, with `line_json IS NULL` as the queue across runs, so a row
    with nothing to write (no points) is stepped past rather than read for ever.
  * PAD POSTS ONLY, by the `kind` column: a Flip's line counts pages, which
    `pages` already holds.
  * THE DATABASE READS THE PAYLOAD ONCE AND SENDS ONLY WHAT IS NEEDED -- the
    first page's strokes (or the top level's, a Skribl from before pages),
    `playSpeed` and `pauseMode` -- never the photo, the music, or anything
    else in it.
  * IT DECIDES IN PYTHON: validation._payload_line, the rule creation.py
    writes with, so there is one spelling of it.

EXIT CODES, as backfill_canvas: 0 it ran (including nothing to do, including a
dry run); 1 at least one batch failed, rows before it are committed; 2 it could
not run at all.
"""
import argparse
import json
import sys

from sqlalchemy import text

from .models import session as resolve_session
from .sweep import _die, _load_app
from .validation import _payload_line

EXIT_OK = 0
EXIT_PARTIAL = 1

#: Rows per statement. A stroke list can be megabytes for a long drawing.
DEFAULT_BATCH = 25


def _extract_sql(dialect):
    """SELECT id, the strokes (first page, else top level), playSpeed and pauseMode -- never the payload.

    Path operators answer NULL for a path that is not there rather than
    raising, on both engines this project deploys on, which is the trap that
    killed the v309 revision (an operator that RAISES on the wrong shape, in a
    WHERE clause the planner reorders). SQLite's json_extract does raise on a
    payload that is not JSON at all, so it sits inside CASE, which promises
    its order (backfill_canvas.py's note).
    """
    if dialect == "postgresql":
        return ("SELECT id, (payload_json #> '{frames,0,strokes}')::text, "
                "(payload_json #> '{strokes}')::text, (payload_json #> '{playSpeed}')::text, "
                "(payload_json #> '{pauseMode}')::text "
                "FROM skribl_posts WHERE line_json IS NULL AND kind = 'pad' AND id > :last "
                "ORDER BY id LIMIT :n")
    if dialect == "sqlite":
        return ("SELECT id, "
                "CASE WHEN json_valid(payload_json) THEN json_extract(payload_json, '$.frames[0].strokes') END, "
                "CASE WHEN json_valid(payload_json) THEN json_extract(payload_json, '$.strokes') END, "
                "CASE WHEN json_valid(payload_json) THEN json_quote(json_extract(payload_json, '$.playSpeed')) END, "
                "CASE WHEN json_valid(payload_json) THEN json_quote(json_extract(payload_json, '$.pauseMode')) END "
                "FROM skribl_posts WHERE line_json IS NULL AND kind = 'pad' AND id > :last "
                "ORDER BY id LIMIT :n")
    return ("SELECT id, payload_json, NULL, NULL, NULL FROM skribl_posts "
            "WHERE line_json IS NULL AND kind = 'pad' AND id > :last ORDER BY id LIMIT :n")


def _json(raw):
    """Whatever the driver hands back for one extracted value, decoded, or None."""
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:                                       # noqa: BLE001
            return None
    return raw


def _line_from(first, top, speed, pause):
    """line_json for one row, through the rule creation.py uses, or None."""
    first, top, speed, pause = _json(first), _json(top), _json(speed), _json(pause)
    if isinstance(first, dict) and top is None and speed is None and pause is None:
        # The generic branch: the whole payload came back in the first slot.
        line = _payload_line(first)
    else:
        pts = first if isinstance(first, list) and first else top
        payload = {"strokes": pts}
        if speed is not None:
            payload["playSpeed"] = speed
        if pause is not None:
            payload["pauseMode"] = pause
        line = _payload_line(payload) if isinstance(pts, list) else None
    return json.dumps(line, separators=(",", ":")) if line else None


def run(session, batch=DEFAULT_BATCH, limit=None, write=False, out=sys.stdout):
    """Fill the columns in batches. Returns (looked_at, filled, failed_batches)."""
    dialect = session.get_bind().dialect.name
    select_sql = text(_extract_sql(dialect))
    update_sql = text("UPDATE skribl_posts SET line_json = :line WHERE id = :id")
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
        for row_id, first, top, speed, pause in rows:
            seen += 1
            last = max(last, row_id)
            line = _line_from(first, top, speed, pause)
            if line is None:
                continue
            filled += 1
            if write:
                session.execute(update_sql, {"line": line, "id": row_id})
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
        prog="python -m skribl.backfill_line",
        description="Fill line_json on Pad posts written before the in-post line.")
    p.add_argument("--app", default="app:create_app",
                   help="module:attribute of the Flask app (default app:create_app)")
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
          + ("" if args.write else "  (dry run — pass --write to do it)")
          + (f"  — {failed} BATCH(ES) FAILED, exit 1" if failed else ""),
          file=out)
    return EXIT_PARTIAL if failed else EXIT_OK


if __name__ == "__main__":                                      # pragma: no cover
    raise SystemExit(main())
