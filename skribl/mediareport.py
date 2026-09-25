"""`python -m skribl.mediareport` — how much photo and music the database holds.

WHY THIS EXISTS. The owner asked where photo and music files should live, and
the honest answer was "that depends on numbers nobody has": how many bytes of
media the live database carries today, how fast that is growing, and how it
compares with the database's own size. This measures exactly those, once, and
exits. It is the evidence for choosing a backend, and the first step of moving
to one — `backfill_media` is what moves the bytes, and this is how you know
what it would be moving.

READ-ONLY, BY CONSTRUCTION. No `--delete`, no `--apply`, no flag that writes.
It reads posts in id order, a batch at a time, and rolls its session back at
the end. Safe to run against production from the Render Shell while the site is
serving.

WHAT IT COUNTS. Every media slot the validator walks (`_iter_media_items`:
photo and music, per frame, plus the pre-recording canvas snapshot and the
share-card thumbnail) — the same walk, so the report and the write path cannot
disagree about what counts as media. A slot holding a data URL is INLINE: its
bytes live inside `payload_json`, and the size reported is the decoded size. A
slot holding anything else was already externalised by a store; those are
counted, not sized, because their bytes are not in this database.

GROWTH IS IN THE SAME RUN. Media bytes are also bucketed by the month each post
was created, so one run shows the trend without waiting a fortnight for a
second reading.

USAGE

    python -m skribl.mediareport                     # a readable report
    python -m skribl.mediareport --json              # one JSON object
    python -m skribl.mediareport --app myhost:app    # a host's own app

`--app` takes `module:attribute` exactly as `python -m skribl.sweep` does.

EXIT CODES: 0 the report ran; 2 it could not run (bad --app, no database).
"""
import argparse
import json
import sys

from sqlalchemy import text

from .models import SkriblPost, session as resolve_session
from .storage import is_data_url
from .sweep import _find_store, _load_app
from .validation import _iter_media_items

EXIT_OK = 0
EXIT_CANNOT_RUN = 2

BATCH = 50
TOP_N = 5

#: The report's categories, in the order a person reading it cares about them.
KINDS = ("photo", "music", "baseSnapshot", "thumbnail")


def _kind(label):
    """`frames[3].music.data` -> 'music'; `thumbnail` -> 'thumbnail'."""
    tail = label.rsplit(".", 2)
    if label.endswith(".data"):
        return tail[-2]
    return tail[-1]


def decoded_len(data_url):
    """Bytes the data URL decodes to, without decoding it.

    base64 is 4 characters per 3 bytes, less the padding. Exact for well-formed
    input, which validation guarantees for anything that reached a row.
    """
    b64 = data_url.strip().split(",", 1)[1] if "," in data_url else ""
    b64 = b64.strip()
    return max(0, len(b64) * 3 // 4 - b64[-2:].count("="))


def _empty_bucket():
    return {"items": 0, "bytes": 0, "posts": 0}


def measure(sess):
    """Walk every post once. Returns the report dict; writes nothing."""
    inline = {k: _empty_bucket() for k in KINDS}
    external = {k: 0 for k in KINDS}
    by_month = {}
    top = []
    posts = 0
    payload_bytes = 0
    posts_with_media = 0
    last_id = 0
    while True:
        rows = (sess.query(SkriblPost.id, SkriblPost.public_id,
                           SkriblPost.created_at, SkriblPost.payload_json)
                .filter(SkriblPost.id > last_id)
                .order_by(SkriblPost.id).limit(BATCH).all())
        if not rows:
            break
        for pid, public_id, created, payload in rows:
            last_id = pid
            posts += 1
            payload = payload or {}
            payload_bytes += len(json.dumps(payload, separators=(",", ":")))
            this_post = 0
            seen_kinds = set()
            carries = False
            for value, _type, _cap, label in _iter_media_items(payload):
                kind = _kind(label)
                if kind not in inline or not isinstance(value, str):
                    continue
                carries = carries or kind in ("photo", "music")
                if is_data_url(value):
                    n = decoded_len(value)
                    inline[kind]["items"] += 1
                    inline[kind]["bytes"] += n
                    seen_kinds.add(kind)
                    this_post += n
                else:
                    external[kind] += 1
            for kind in seen_kinds:
                inline[kind]["posts"] += 1
            if carries:          # inline or already externalised, either way
                posts_with_media += 1
            month = created.strftime("%Y-%m") if created else "unknown"
            m = by_month.setdefault(month, {"posts": 0, "media_bytes": 0})
            m["posts"] += 1
            m["media_bytes"] += this_post
            if this_post:
                top.append((this_post, public_id))
        sess.expunge_all()
    top.sort(reverse=True)
    return {
        "posts": posts,
        "posts_with_photo_or_music": posts_with_media,
        "payload_json_bytes": payload_bytes,
        "inline_media_bytes": sum(b["bytes"] for b in inline.values()),
        "inline": inline,
        "externalised_items": external,
        "by_month": dict(sorted(by_month.items())),
        "largest": [{"public_id": p, "media_bytes": n} for n, p in top[:TOP_N]],
    }


def database_size(sess):
    """(total database bytes, skribl_posts bytes incl. indexes and TOAST), or
    Nones where the dialect cannot say."""
    dialect = sess.get_bind().dialect.name
    try:
        if dialect == "postgresql":
            db = sess.execute(text("SELECT pg_database_size(current_database())")).scalar()
            posts = sess.execute(text("SELECT pg_total_relation_size('skribl_posts')")).scalar()
            return dialect, int(db), int(posts)
        if dialect == "sqlite":
            pages = sess.execute(text("PRAGMA page_count")).scalar()
            size = sess.execute(text("PRAGMA page_size")).scalar()
            return dialect, int(pages) * int(size), None
    except Exception:
        pass
    return dialect, None, None


def mb(n):
    return "unknown" if n is None else f"{n / 1_000_000:,.2f} MB"


def _human(r, out):
    p = lambda *a: print(*a, file=out)
    p(f"media store         : {r['store']}")
    p(f"database            : {r['dialect']}, {mb(r['database_bytes'])} in total"
      + (f"; skribl_posts {mb(r['posts_table_bytes'])}"
         if r["posts_table_bytes"] is not None else ""))
    p(f"posts               : {r['posts']}"
      f" ({r['posts_with_photo_or_music']} carry a photo or music)")
    p(f"payload_json        : {mb(r['payload_json_bytes'])}, of which inline media"
      f" {mb(r['inline_media_bytes'])}")
    p("")
    p("inline media, by kind (decoded bytes):")
    for kind in KINDS:
        b = r["inline"][kind]
        p(f"  {kind:<13} {b['items']:>6} item(s) on {b['posts']:>6} post(s)"
          f"  {mb(b['bytes']):>14}")
    ext = sum(r["externalised_items"].values())
    if ext:
        p(f"  already externalised: {ext} item(s), stored outside this database")
    p("")
    p("by month (posts, inline media):")
    for month, m in r["by_month"].items():
        p(f"  {month}  {m['posts']:>6}  {mb(m['media_bytes']):>14}")
    if r["largest"]:
        p("")
        p(f"largest {len(r['largest'])} by inline media:")
        for row in r["largest"]:
            p(f"  /s/{row['public_id']:<16} {mb(row['media_bytes'])}")
    p("")
    p("Nothing was changed; this command only reads.")


def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m skribl.mediareport",
        description="Report how much photo and music media the database holds. "
                    "Read-only.")
    p.add_argument("--app", default="app:create_app",
                   help="module:attribute of the Flask app or app factory "
                        "(default: app:create_app)")
    p.add_argument("--json", action="store_true",
                   help="print the report as one JSON object and nothing else")
    return p


def main(argv=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    app = _load_app(args.app)
    store = _find_store(app)
    with app.app_context():
        try:
            sess = resolve_session()
        except RuntimeError as exc:
            print(f"skribl.mediareport: no database session: {exc}", file=sys.stderr)
            raise SystemExit(EXIT_CANNOT_RUN)
        try:
            report = measure(sess)
            dialect, db_bytes, posts_bytes = database_size(sess)
        except Exception as exc:
            print(f"skribl.mediareport: could not read the database: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            raise SystemExit(EXIT_CANNOT_RUN)
        finally:
            sess.rollback()
    report.update(store=type(store).__name__, dialect=dialect,
                  database_bytes=db_bytes, posts_table_bytes=posts_bytes)
    if args.json:
        print(json.dumps(report, sort_keys=True), file=out)
    else:
        _human(report, out)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
