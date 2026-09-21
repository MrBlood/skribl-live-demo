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
    # THE BOX SAYS WHAT IT SEARCHES (PRESEAL-006). It said "Search titles…"
    # while the server matches title AND caption, so the wider half of the
    # feature was invisible. Asserted with the copy AND a caption-only search
    # driven through the box, because the words are only true if the behaviour
    # is.
    _ph = pg.get_attribute("#galleryQ", "placeholder") or ""
    check("the box says it searches captions too", "caption" in _ph.lower(), repr(_ph))
    pg.fill("#galleryQ", "howls")          # lives only in alpha wolf's CAPTION
    pg.wait_for_timeout(1400)
    _cap = pg.evaluate("() => [...document.querySelectorAll('#galleryList .tile .tt')].map(t => t.textContent)")
    check("...and a word that is only in a caption finds its post",
          bool(_cap) and any("alpha wolf" in t for t in _cap),
          f"caption-only search returned {_cap}")
    pg.fill("#galleryQ", "")
    pg.wait_for_timeout(900)
    check("no page errors", not errs, "; ".join(errs[:2]))
    pg.close()

    # ---- THE LATEST INTENT WINS (PRESEAL-001) ---------------------------
    #
    # gallery.js used to begin load() with `if (loading) return`. Tapping Hot,
    # or typing, while a listing was still in flight set sort/query and then
    # threw the reload away, and nothing re-issued it when the first request
    # settled: the grid rendered the OLD answer under a bar saying Hot. On a
    # slow phone that is the ordinary case, not a rare one.
    #
    # DRIVEN AT THE RACE, not near it: the first listing is held open by the
    # route until the tab has been clicked, so the click lands while the
    # request really is pending. The suite's other gallery assertions wait
    # ~1.2s between actions and cannot reach this.
    print("\nHOT 5b — a tab or a search during an in-flight request is not dropped")
    for _what, _act, _wanted in (
            ("the Hot tab", lambda q: q.click('.tab[data-sort="hot"]'), "sort=hot"),
            ("a search", lambda q: q.fill("#galleryQ", "beta fish"), "q=beta")):
        rp = br.new_page(viewport={"width": 1280, "height": 900})
        seen, held = [], {"done": False}
        rp.on("request", lambda rq: seen.append(rq.url) if "/api/skribls?" in rq.url else None)

        def _hold(route):
            # Hold ONLY the first listing, and let it go after the click.
            if held["done"]:
                route.continue_()
                return
            held["done"] = True
            for _ in range(60):
                if held.get("release"):
                    break
                rp.wait_for_timeout(100)
            route.continue_()
        rp.route(re.compile(r"/api/skribls\?"), _hold)
        rp.goto(BASE + "/gallery", wait_until="commit")
        # The page is up but the listing is still open: act now.
        rp.wait_for_selector('.tab[data-sort="hot"]', timeout=15000)
        _act(rp)
        held["release"] = True
        rp.wait_for_timeout(2500)
        _sent = [u for u in seen if _wanted in u]
        check(f"{_what} during a pending request is actually sent",
              bool(_sent), f"requests: {seen}")
        _state = rp.evaluate("""() => ({
            hot: (document.querySelector('.tab[data-sort="hot"]') || {}).getAttribute
                 ? document.querySelector('.tab[data-sort="hot"]').getAttribute('aria-pressed') : null,
            q: (document.getElementById('galleryQ') || {}).value,
            titles: [...document.querySelectorAll('#galleryList .tile .tt')].map(t => t.textContent) })""")
        # AND THE GRID AGREES WITH THE BAR. Asserting only that the request
        # went would pass on a page that issued it and then rendered the
        # stale response over the top.
        if _wanted == "sort=hot":
            _st, _srv = listing(sort="hot", limit=3)
            check("...and the grid is the Hot answer, not the stale one",
                  _state["titles"][:1] == titles(_srv)[:1],
                  f"page {_state['titles'][:1]} vs server {titles(_srv)[:1]}")
        else:
            check("...and the grid holds only what the search asked for",
                  bool(_state["titles"]) and all("beta fish" in t.lower() for t in _state["titles"]),
                  f"q={_state['q']!r} -> {_state['titles']}")
        rp.close()
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

# ------------------------------------------------------------------ section 7
print("\nHOT 7 — a view row does not outlive the window it serves")
# PRESEAL-003 of the pre-v305 audit: skribl_views kept one pseudonymous row per
# (post, client hash, UTC day) for the life of the post, while the only thing
# that reads them is the last HOT_DAYS. views_total already carries the lifetime
# figure the UI shows, so the old rows served nothing. They are purged now.
#
# ASSERTED ON ALL THREE HALVES, because a purge that gets any one of them wrong
# is worse than no purge: the old rows must GO, the recent ones must STAY (or
# Hot silently starts ranking on a window it no longer has), and views_total
# must not move (or the lifetime count becomes a function of when a janitor
# last ran).
if have_db:
    from skribl.core import HOT_DAYS as _HOT_DAYS        # noqa: E402
    from skribl.views import purge_views, view_cutoff    # noqa: E402

    _pid = post(f"{TAG} retention")
    for _d in (40, 30, 20):
        plant_view(_pid, _d, f"ancient-{_d}")
    for _d in (1, 3):
        plant_view(_pid, _d, f"recent-{_d}")
    _before, _total_before = view_rows(_pid)
    check("the fixture has old and recent view rows", _before == 5, f"{_before} rows")
    _hot_before = titles(listing(sort="hot", limit=40)[1])

    with _app.app_context():
        _s = session()
        _gone = purge_views(_s)
        _s.commit()
    _after, _total_after = view_rows(_pid)
    check("the rows past the retention window are deleted",
          _after == 2 and _gone >= 3, f"{_before} -> {_after} rows, purge reported {_gone}")
    check("...the rows inside the window are kept",
          _after == 2, f"{_after} rows left, expected the two recent ones")
    check("...and views_total is untouched, so the lifetime count is not a "
          "function of when the janitor ran",
          _total_after == _total_before, f"{_total_before} -> {_total_after}")
    _hot_after = titles(listing(sort="hot", limit=40)[1])
    check("...and Hot still ranks the same posts in the same order",
          _hot_after == _hot_before, f"{_hot_before[:3]} -> {_hot_after[:3]}")

    # THE HOT WINDOW IS A FLOOR. A host asking for a retention shorter than the
    # window must get a shorter retention AND a correct Hot, not a ranking
    # reading rows that were deleted underneath it.
    _now = datetime.now(timezone.utc)
    check("a retention shorter than HOT_DAYS is clamped to HOT_DAYS",
          (_now - view_cutoff(1)).days == (_now - view_cutoff(_HOT_DAYS)).days
          and (_now - view_cutoff(1)).days >= _HOT_DAYS - 1,
          f"asked 1 day, cutoff is {(_now - view_cutoff(1)).days} days back")
    # ...and a longer one is honoured, or the clamp would just be a constant.
    check("...while a longer retention is honoured",
          (_now - view_cutoff(30)).days > (_now - view_cutoff(_HOT_DAYS)).days,
          f"30 -> {(_now - view_cutoff(30)).days} days back")

    # BOUNDED: one call cannot turn into an unbounded delete.
    for _d in (50, 51, 52):
        plant_view(_pid, _d, f"batch-{_d}")
    with _app.app_context():
        _s = session()
        _n = purge_views(_s, batch=2)
        _s.commit()
    check("the purge respects its batch size", _n == 2, f"deleted {_n} with batch=2")
    with _app.app_context():
        _s = session()
        purge_views(_s)
        _s.commit()

passed = sum(1 for r in results if r[0])
print("\n" + "=" * 62 + f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
