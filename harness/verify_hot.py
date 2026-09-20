"""The gallery's search and Hot: the listing's own q and sort, and a view that
cannot be gamed by holding refresh.

WHAT A VIEW IS. A play is the payload fetch every player makes (GET
/api/skribls/<id>): the in-post player on a tap, the /s/<id> page on load.
A view is one row per (post, client hash, UTC day), unique, so the same
client fetching the same post again today is the same view -- the count
moves once. No address is stored. Hot is the count of those rows in the last
seven days, most first, newest id breaking ties; it is computed from the
rows, never from the running total, so an old post with a big total does not
sit on top forever. New is the listing as it always was.

THE HARNESS IS ONE CLIENT, so one post can earn at most one view per day
from here. That is enough: A with one view above B with none is an ordering,
and the seven-day window is driven by planting rows in the past straight
into the server's database (DATABASE_URL), which is where an operator's
question about it would be answered too.

SEARCH is a substring of the title or caption, case-folded, with the
person's own % and _ escaped so they are letters, bounded at 80 characters,
paged by the same cursor as the listing. The gallery's box sends it and adds
no filtering of its own; the Hot tab sends sort=hot and adds no ranking.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence Hot works.")
    raise SystemExit(77)

results = []
check = make_check(results)
TAG = "hot" + os.urandom(4).hex()


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def post(title, caption=""):
    pts = [{"x": 120 + i * 40, "y": 140 + (i % 3) * 30, "color": "#ff48b0", "size": 12, "t": i * 120}
           for i in range(12)]
    body = {"title": title, "caption": caption, "version": 2, "schemaVersion": 2, "visibility": "public",
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [len(pts)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    return call("/api/skribls", body)[1].get("id")


def listing(**params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return call("/api/skribls?" + qs)


def titles(body):
    return [i["title"] for i in body.get("items", [])]


have_db = "DATABASE_URL" in os.environ
if have_db:
    from app import create_app                                  # noqa: E402
    from skribl.models import SkriblPost, SkriblView, session   # noqa: E402
    _app = create_app()

    def view_rows(pid):
        with _app.app_context():
            s = session()
            p = s.query(SkriblPost).filter(SkriblPost.public_id == pid).one()
            return s.query(SkriblView).filter(SkriblView.post_id == p.id).count(), int(p.views_total or 0)

    def plant_view(pid, days_ago, who):
        with _app.app_context():
            s = session()
            p = s.query(SkriblPost).filter(SkriblPost.public_id == pid).one()
            when = datetime.now(timezone.utc) - timedelta(days=days_ago)
            s.add(SkriblView(post_id=p.id, viewer_hash=who, day=when.strftime("%Y-%m-%d"), created_at=when))
            p.views_total = (p.views_total or 0) + 1
            s.commit()
else:
    print("  (DATABASE_URL not set: the window pins that plant old views are skipped)")

# ------------------------------------------------------------------ section 1
print("\nHOT 1 — a view is one per client per post per day, and the total follows")
a = post(TAG + " alpha wolf", "howls at night")
b = post(TAG + " beta fish", "swims at 100% and under_scores")
c = post(TAG + " gamma ray", "shines")
# THE DECOYS for the search's escaping (section 4). A wildcard matches the
# literal it stands for, so "100%" and "_scores" alone cannot tell an
# escaped LIKE from a raw one -- the first calibration stayed green. These
# match the RAW reading only: "%100%%" finds "100 percent" and "%_scores%"
# finds "underscores", and an escaped query finds neither.
d = post(TAG + " delta decoy", "100 percent, no sign, and underscores plain")
check("fixtures posted public", all((a, b, c, d)), f"{a} {b} {c} {d}")
st, before = listing(q=TAG, limit=10)
check("the listing carries a views count", all("views" in i for i in before.get("items", [])), str(before)[:200])
check("...zero before anybody fetched a payload", all(i["views"] == 0 for i in before.get("items", [])),
      str([(i["title"], i["views"]) for i in before.get("items", [])]))
st1, _ = call(f"/api/skribls/{a}")
st2, _ = call(f"/api/skribls/{a}")
st, after = listing(q=TAG, limit=10)
va = {i["id"]: i["views"] for i in after.get("items", [])}
check("two payload fetches from one client today count ONE view", st1 == 200 and st2 == 200 and va.get(a) == 1,
      f"views={va.get(a)}")
check("...and the others are untouched", va.get(b) == 0 and va.get(c) == 0, str(va))
if have_db:
    rows, total = view_rows(a)
    check("one row in skribl_views, total 1", rows == 1 and total == 1, f"rows={rows} total={total}")

# ------------------------------------------------------------------ section 2
print("\nHOT 2 — sort=hot ranks by plays in the last seven days, newest id breaking ties")
st, hot = listing(q=TAG, sort="hot", limit=10)
ht = titles(hot)
check("the played post is first under Hot", ht and ht[0].endswith("alpha wolf"), str(ht))
check("the unplayed ones follow, newest first", ht[1:] == [TAG + " delta decoy", TAG + " gamma ray", TAG + " beta fish"], str(ht))
check("Hot carries the seven-day count beside the total",
      all("views_recent" in i for i in hot.get("items", [])) and hot["items"][0]["views_recent"] == 1,
      str([(i["title"], i.get("views"), i.get("views_recent")) for i in hot.get("items", [])]))
st, new = listing(q=TAG, sort="new", limit=10)
check("sort=new is the listing as it always was: newest first regardless of plays",
      titles(new) == [TAG + " delta decoy", TAG + " gamma ray", TAG + " beta fish", TAG + " alpha wolf"], str(titles(new)))
st, bad = listing(sort="sideways")
check("an unknown sort is refused with 400", st == 400, str(st))
if have_db:
    # AN OLD POST WITH A BIG TOTAL: eight-day-old plays count for the total
    # and NOT for Hot. Planted, because the harness cannot wait a week.
    for k in range(3):
        plant_view(c, 8, f"old-client-{k}")
    st, hot2 = listing(q=TAG, sort="hot", limit=10)
    ht2 = [(i["title"], i["views"], i["views_recent"]) for i in hot2.get("items", [])]
    check("plays older than seven days raise the total but not Hot",
          ht2[0][0].endswith("alpha wolf") and any(t.endswith("gamma ray") and v == 3 and r == 0 for t, v, r in ht2),
          str(ht2))
    plant_view(c, 2, "recent-client-1")
    plant_view(c, 3, "recent-client-2")
    st, hot3 = listing(q=TAG, sort="hot", limit=10)
    check("...and two plays within the week put it on top", titles(hot3)[0].endswith("gamma ray"), str(titles(hot3)))

# ------------------------------------------------------------------ section 3
print("\nHOT 3 — Hot pages by its own cursor, and the two shapes do not mix")
st, p1 = listing(q=TAG, sort="hot", limit=1)
cur = p1.get("next_cursor")
check("a first Hot page of one comes back with a cursor", len(p1.get("items", [])) == 1 and bool(cur), str(cur))
st, p2 = listing(q=TAG, sort="hot", limit=5, cursor=cur)
check("the next Hot page continues without repeating",
      st == 200 and titles(p1)[0] not in titles(p2) and len(titles(p2)) == 3, f"{titles(p1)} then {titles(p2)}")
st, mixed = listing(q=TAG, sort="new", cursor=cur)
check("a Hot cursor handed to New is refused with 400", st == 400, str(st))
st, n1 = listing(q=TAG, limit=1)
st, mixed2 = listing(q=TAG, sort="hot", cursor=n1.get("next_cursor"))
check("...and a New cursor handed to Hot likewise", st == 400, str(st))

# ------------------------------------------------------------------ section 4
print("\nHOT 4 — search is the listing's, on title and caption, with the person's letters kept")
st, r = listing(q="beta FISH")
check("a title matches case-folded", [t for t in titles(r) if t.startswith(TAG)] == [TAG + " beta fish"], str(titles(r)))
st, r = listing(q="howls")
check("a caption matches too", [t for t in titles(r) if t.startswith(TAG)] == [TAG + " alpha wolf"], str(titles(r)))
st, r = listing(q="100%")
check("a % typed by a person is a percent sign, not a wildcard: the decoy with '100 percent' does not match",
      [t for t in titles(r) if t.startswith(TAG)] == [TAG + " beta fish"], str(titles(r)))
st, r = listing(q="_scores")
check("an _ typed by a person is an underscore, not a wildcard: the decoy with 'underscores' does not match",
      [t for t in titles(r) if t.startswith(TAG)] == [TAG + " beta fish"], str(titles(r)))
st, r = listing(q="x" * 81)
check("a query past 80 characters is refused with 400", st == 400, str(st))
st, r = listing(q="   ")
check("a blank query is the plain listing", st == 200 and len(r.get("items", [])) >= 4, str(st))

# ------------------------------------------------------------------ section 5
print("\nHOT 5 — the gallery: two tabs and a box, and nothing of its own")
with sync_playwright() as sp:
    br = sp.chromium.launch()
    pg = br.new_page(viewport={"width": 1280, "height": 900})
    errs, reqs = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda rq: reqs.append(rq.url) if "/api/skribls?" in rq.url else None)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(600)
    tabs = pg.evaluate("() => [...document.querySelectorAll('.tabs .tab')].map(t => [t.textContent.trim(), t.getAttribute('aria-pressed')])")
    check("New and Hot are the two tabs, New pressed", tabs == [["New", "true"], ["Hot", "false"]], str(tabs))
    check("the first request asked for sort=new and no q", any("sort=new" in u and "q=" not in u for u in reqs), str(reqs))
    pg.click('.tab[data-sort="hot"]')
    pg.wait_for_timeout(1200)
    check("the Hot tab asks the server for sort=hot", any("sort=hot" in u for u in reqs), str(reqs[-1:]))
    first = pg.evaluate("() => (document.querySelector('#galleryList .tile .tt') || {}).textContent")
    st, srv = listing(sort="hot", limit=1)
    check("...and shows the server's order, not one of its own", first == titles(srv)[0], f"page {first!r} vs server {titles(srv)[:1]}")
    plays = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile')].slice(0, 3).map(t => (t.querySelector('.plays') || {}).textContent || '')")
    check("a played tile says its plays; an unplayed one says nothing", any(re.match(r"\d+ plays?$", p) for p in plays), str(plays))
    pg.fill("#galleryQ", "beta fish")
    pg.wait_for_timeout(1200)
    shown = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile .tt')].map(t => t.textContent)")
    check("the box sends q and the page shows what came back",
          any("q=beta" in u for u in reqs) and all("beta fish" in t.lower() for t in shown) and shown, f"{reqs[-1:]} -> {shown}")
    pg.fill("#galleryQ", "zzzz-nothing-" + TAG)
    pg.wait_for_timeout(1200)
    none = pg.evaluate("() => ({ none: !document.getElementById('galleryNone').hidden, empty: !document.getElementById('galleryEmpty').hidden, tiles: document.querySelectorAll('#galleryList .tile').length })")
    check("no match shows 'nothing matches', not the empty gallery", none["none"] and not none["empty"] and none["tiles"] == 0, str(none))
    check("no page errors", not errs, "; ".join(errs[:2]))
    pg.close()
    br.close()

# ------------------------------------------------------------------ section 6
print("\nHOT 6 — a view stores no address")
if have_db:
    with _app.app_context():
        s = session()
        p = s.query(SkriblPost).filter(SkriblPost.public_id == a).one()
        row = s.query(SkriblView).filter(SkriblView.post_id == p.id).first()
        check("the viewer column is a 64-hex hash, not an address",
              bool(row) and re.fullmatch(r"[0-9a-f]{64}", row.viewer_hash or "") is not None
              and "127.0.0.1" not in (row.viewer_hash or ""), str(row.viewer_hash)[:20])
        check("the day is a UTC date", bool(row) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.day or "") is not None, str(row.day))

passed = sum(1 for r in results if r[0])
print("\n" + "=" * 62 + f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
