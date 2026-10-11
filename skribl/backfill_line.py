"""Fill in `drawn_ms` / `play_speed` on posts written before the in-post line.

    python -m skribl.backfill_line            # what it would do
    python -m skribl.backfill_line --write    # do it

The line under a post in a feed says "Drawn in 15 sec · watching at 1x" before
anybody presses play, from two columns the listing can read (the payload it
cannot). New posts carry both from the moment they are made (creation.py);
this is for the ones made before.

A COMMAND, NOT A MIGRATION, for the reason skribl/backfill_canvas.py gives at
length: v309 put its backfill in a revision and took the site down twice, and
what is computed here is as cosmetic as what was computed there. A null is a
supported state -- the line says what it can without one -- so nothing here
runs during a deploy. The shape is that file's, deliberately:

  * BOUNDED BATCHES, committed as it goes; interrupt it and what is written
    stays written. SMALLER batches than the canvas one (25, not 200), because
    what crosses the wire here is a drawing's whole stroke list, not a size.
  * PAGED BY id, with `drawn_ms IS NULL` as the queue across runs, so a row
    with nothing to write (no points) is stepped past rather than read for ever.
  * PAD POSTS ONLY, by the `kind` column: a Flip's line counts pages, and its
    drawn time is not a number anything shows.
  * THE DATABASE READS THE PAYLOAD ONCE AND SENDS ONLY WHAT IS NEEDED -- the
    first page's strokes (or the top level's, a Skribl from before pages) and
    `playSpeed` -- never the photo, the music, or anything else in it.
  * IT DECIDES IN PYTHON: validation._payload_drawn_ms and _payload_play_speed,
    the rules creation.py writes with, so there is one spelling of each.

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
from .validation import _payload_drawn_ms, _payload_play_speed

EXIT_OK = 0
EXIT_PARTIAL = 1

#: Rows per statement. A stroke list can be megabytes for a long drawing.
DEFAULT_BATCH = 25


def _extract_sql(dialect):
    """SELECT id, the strokes (first page, else top level) and playSpeed -- never the payload.

    Path operators answer NULL for a path that is not there rather than
    raising, on both engines this project deploys on, which is the trap that
    killed the v309 revision (an operator that RAISES on the wrong shape, in a
    WHERE clause the planner reorders). SQLite's json_extract does raise on a
    payload that is not JSON at all, so it sits inside CASE, which promises
    its order (backfill_canvas.py's note).
    """
    if dialect == "postgresql":
        return ("SELECT id, (payload_json #> '{frames,0,strokes}')::text, "
                "(payload_json #> '{strokes}')::text, (payload_json #> '{playSpeed}')::text "
                "FROM skribl_posts WHERE drawn_ms IS NULL AND kind = 'pad' AND id > :last "
                "ORDER BY id LIMIT :n")
    if dialect == "sqlite":
        return ("SELECT id, "
                "CASE WHEN json_valid(payload_json) THEN json_extract(payload_json, '$.frames[0].strokes') END, "
                "CASE WHEN json_valid(payload_json) THEN json_extract(payload_json, '$.strokes') END, "
                "CASE WHEN json_valid(payload_json) THEN json_quote(json_extract(payload_json, '$.playSpeed')) END "
                "FROM skribl_posts WHERE drawn_ms IS NULL AND kind = 'pad' AND id > :last "
                "ORDER BY id LIMIT :n")
    return ("SELECT id, payload_json, NULL, NULL FROM skribl_posts "
            "WHERE drawn_ms IS NULL AND kind = 'pad' AND id > :last ORDER BY id LIMIT :n")


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


def _line_from(first, top, speed):
    """(drawn_ms, play_speed) for one row, through the same two rules creation.py uses."""
    first, top, speed = _json(first), _json(top), _json(speed)
    if isinstance(first, dict) and top is None and speed is None:
        # The generic branch: the whole payload came back in the first slot.
        return _payload_drawn_ms(first), _payload_play_speed(first)
    pts = first if isinstance(first, list) and first else top
    return (_payload_drawn_ms({"strokes": pts}) if isinstance(pts, list) else None,
            _payload_play_speed({"playSpeed": speed}))


def run(session, batch=DEFAULT_BATCH, limit=None, write=False, out=sys.stdout):
    """Fill the columns in batches. Returns (looked_at, filled, failed_batches)."""
    dialect = session.get_bind().dialect.name
    select_sql = text(_extract_sql(dialect))
    update_sql = text("UPDATE skribl_posts SET drawn_ms = :d, play_speed = :s WHERE id = :id")
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
        for row_id, first, top, speed in rows:
            seen += 1
            last = max(last, row_id)
            drawn, play = _line_from(first, top, speed)
            if drawn is None:
                continue
            filled += 1
            if write:
                session.execute(update_sql, {"d": drawn, "s": play, "id": row_id})
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
        description="Fill drawn_ms/play_speed on Pad posts written before the in-post line.")
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
