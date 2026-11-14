"""Fill in `ground` and `on_photo` on posts written before them (after v330).

    python -m skribl.backfill_ground            # what it would do
    python -m skribl.backfill_ground --write    # do it

A host's tile lays the box around a drawing in the drawing's own ground, and
a drawing made on a picture (a photo, or the picture the Pad began on) keeps
that picture, blurred, at its sides (the owner's "Yes to both, build them",
Nov 14). describe_posts hands a host both from two small columns, which new
posts carry from the moment they are made (creation.py); a post from before
them has NULL, and describe_posts reads that one from its drawing, on every
page that shows it. On PostgreSQL the payload is plain `json` and every path
read re-parses the whole drawing (measured: 80-260 ms a page for the ground's
two reads, 310-425 ms with the picture's four). This fills them in once.

A COMMAND, NOT A MIGRATION, for the reason skribl/backfill_canvas.py gives at
length: v309 put its backfill in a revision and took the site down twice, and
nothing here is worth an outage. A NULL is a supported state -- the tile looks
the way it looked before the columns -- so nothing here runs during a deploy,
and nothing breaks if it is never run. The shape is that file's, deliberately:

  * BOUNDED BATCHES, committed as it goes; interrupt it and what is written
    stays written. Small ones (25, as backfill_line's), because the database
    reads every payload in a batch whole to reach inside it.
  * PAGED BY id, with "rows where ground or on_photo IS NULL" as the queue
    across runs, so a re-run starts where the last one stopped. Every row
    looked at has an answer ("" is no ground, False no picture), so every one
    is written; a column a host already wrote is left as it is (COALESCE).
  * THE DATABASE READS EACH PAYLOAD AND SENDS ONLY WHAT IS NEEDED: the two
    colours, whether the first page is there, and the first characters of
    each of the picture's four places (enough to tell a picture from nothing)
    -- never the photo, the snapshot, the strokes or the music.
  * IT DECIDES IN PYTHON: validation._payload_ground and _payload_on_photo,
    the rules creation.py writes with, applied to a stand-in payload built
    from those few values, so there is one spelling of each.

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
from .validation import _payload_ground, _payload_on_photo

EXIT_OK = 0
EXIT_PARTIAL = 1

#: Rows per statement. The database reads each payload in it whole, and a
#: drawing with an inline photo can be megabytes.
DEFAULT_BATCH = 25

#: How much of a picture's place crosses the wire: its JSON text's first
#: characters, which say whether there is a picture there and nothing more.
#: A colour as JSON text is nine ('"#0d0f14"'), so this never cuts one.
CUT = 24

_QUEUE = ("FROM skribl_posts WHERE (ground IS NULL OR on_photo IS NULL) AND id > :last "
          "ORDER BY id LIMIT :n")

# The places the player looks, in its order (inlineplayer.js adopt()): the
# first page's colour and the payload's own; the first page's photo and base
# snapshot, the payload's own photo (a payload from before pages) and base
# snapshot.
_PLACES = (("frames", 0, "background", "color"), ("background", "color"),
           ("frames", 0, "photo", "data"), ("frames", 0, "baseSnapshot"),
           ("photo", "data"), ("baseSnapshot",))


def _extract_sql(dialect):
    """SELECT id, the six places' JSON text cut short, and the first page's
    JSON type -- never the payload.

    Path operators answer NULL for a path that is not there rather than
    raising, on both engines this project deploys on (the trap that killed the
    v309 revision was an operator that RAISES on the wrong shape, in a WHERE
    clause the planner reorders). SQLite's json_extract does raise on a payload
    that is not JSON at all, so it sits inside CASE, which promises its order
    (backfill_canvas.py's note). The first page is "there" only when `frames`
    is a list with something in it, as the player's framesOf asks: PostgreSQL
    asks the type of `frames` first, in a CASE, since its path operator would
    read a key "0" of an object as a first page.
    """
    if dialect == "postgresql":
        cols = ", ".join(f"left((payload_json #> '{{{','.join(str(p) for p in path)}}}')::text, {CUT})"
                         for path in _PLACES)
        return (f"SELECT id, {cols}, CASE WHEN json_typeof(payload_json -> 'frames') = 'array' "
                f"THEN json_typeof(payload_json #> '{{frames,0}}') END " + _QUEUE)
    if dialect == "sqlite":
        def at(path):
            return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in path)
        cols = ", ".join(f"CASE WHEN json_valid(payload_json) THEN "
                         f"substr(json_quote(json_extract(payload_json, '{at(path)}')), 1, {CUT}) END"
                         for path in _PLACES)
        return (f"SELECT id, {cols}, CASE WHEN json_valid(payload_json) "
                f"THEN json_type(payload_json, '$.frames[0]') END " + _QUEUE)
    return "SELECT id, payload_json " + _QUEUE


def _value(raw):
    """What one place held, as far as the rules need it, from its JSON text cut
    to CUT characters (None when the place is not there).

    Short JSON is read whole: a colour, a number, true, false, null. A string
    that was cut is a long string, never a colour (a colour is nine
    characters), and true to the player; an object or array that was cut is
    true to it too."""
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except ValueError:
        return ("cut:" + raw) if raw.startswith('"') else {}


def _stand_in(first_color, own_color, photo, snapshot, own_photo, own_snapshot, first):
    """A payload carrying only what the rules read, in the places they read it:
    a first page when `frames` held one (`first`, its JSON type), else the top
    level alone, as a payload from before pages."""
    payload = {"background": {"color": _value(own_color)}, "photo": {"data": _value(own_photo)},
               "baseSnapshot": _value(own_snapshot)}
    if first is not None:
        page = None
        if first == "object":
            page = {"background": {"color": _value(first_color)}, "photo": {"data": _value(photo)},
                    "baseSnapshot": _value(snapshot)}
        payload["frames"] = [page]
    return payload


def _answer(row):
    """(ground, on_photo) for one row of the SELECT above, by the rules
    creation.py writes with."""
    if len(row) == 2:
        # The generic branch: the payload itself, as the driver hands it.
        raw = row[1]
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", "replace")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = None
        payload = raw
    else:
        payload = _stand_in(*row[1:])
    return _payload_ground(payload), _payload_on_photo(payload)


def run(session, batch=DEFAULT_BATCH, limit=None, write=False, out=sys.stdout):
    """Fill the columns in batches. Returns (looked_at, filled, failed_batches)."""
    dialect = session.get_bind().dialect.name
    select_sql = text(_extract_sql(dialect))
    # Only what is NULL: a column a host wrote itself is its answer.
    update_sql = text("UPDATE skribl_posts SET ground = COALESCE(ground, :ground), "
                      "on_photo = COALESCE(on_photo, :on_photo) WHERE id = :id")
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
        for row in rows:
            seen += 1
            last = max(last, row[0])
            ground, on_photo = _answer(tuple(row))
            filled += 1
            if write:
                session.execute(update_sql, {"ground": ground, "on_photo": on_photo, "id": row[0]})
        # A DRY RUN STILL PAGES, by the cursor, or a preview would report on
        # the first batch and call that the answer.
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
        prog="python -m skribl.backfill_ground",
        description="Fill ground/on_photo on posts written before them.")
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
