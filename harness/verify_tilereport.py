"""Report on every gallery tile: a row in an operator's queue, never an action.

The gallery lists what people chose to show, and the owner's direction was
"opt-in, with Report on every tile". The claim this suite holds:

  1. THE SHEET IS THE API'S. It opens from a tile with that tile's id, offers
     exactly skribl.core.REPORT_REASONS (rendered from the tuple, read back
     from the DOM), and the request the browser sends carries the reason it
     showed. Driven through the page, with the request body read off the wire.
  2. ONE REPORTER, ONE POST, ONE ROW. A second report from the same client is
     answered like the first and writes nothing — counted in the table through
     the operator's own reader (takedown --reports), never inferred from the
     status code.
  3. NOTHING IS TAKEN DOWN. The post's visibility and its place in the listing
     are the same after a report as before. A flood of reports cannot hide a
     drawing; that is the operator's call.
  4. YOU CAN ONLY REPORT WHAT YOU COULD SEE. A malformed id, an unknown id and
     a post the reporter may not read all answer 404 — the same answer, so the
     endpoint confirms nothing GET would not.
  5. THE SHEET SAYS SO, AND HOLDS FOCUS. It declares itself a dialog, focus
     moves in, and the button it opened from is where focus lands on close —
     including after a send, when the button has become the record.

Fixtures are unique per run: run_harness.sh gives every suite one server.
The table is read through `python -m skribl.takedown --reports` against the
server's own database (DATABASE_URL), which is the reader an operator has.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence reporting works.")
    raise SystemExit(77)

from skribl.core import REPORT_REASONS                     # noqa: E402

results = []
check = make_check(results)
TAG = "rep" + os.urandom(4).hex()


def call(path, body=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def post_public(title, visibility="public"):
    pts = [{"x": 120 + i * 40, "y": 140 + (i % 3) * 30, "color": "#ff48b0",
            "size": 12, "t": i * 120} for i in range(12)]
    body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": visibility,
            "playbackMode": "replay", "frames": [{"strokes": pts, "strokeGroups": [len(pts)]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    st, res = call("/api/skribls", body)
    return res.get("id")


def listed_ids():
    out, cursor = [], None
    for _ in range(50):
        st, body = call(f"/api/skribls?limit=100" + (f"&cursor={cursor}" if cursor else ""))
        out += [i["id"] for i in body.get("items", [])]
        cursor = body.get("next_cursor")
        if not cursor:
            break
    return out


def queue():
    """What the operator sees: `takedown --reports` against the server's database."""
    env = dict(os.environ)
    if "DATABASE_URL" not in env:
        return None
    p = subprocess.run([sys.executable, "-m", "skribl.takedown", "--app", "app:create_app", "--reports"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    return p.stdout + p.stderr


def queue_count(out, pid):
    """The report count the queue prints for one post, or 0."""
    if not out:
        return 0
    m = re.search(re.escape(pid) + r"\s+\S+\s+(\d+) report", out)
    return int(m.group(1)) if m else 0


# ------------------------------------------------------------------ section 1
print("\nREPORT 1 — the endpoint: one row per reporter, nothing taken down")
target = post_public(TAG + " target")
other = post_public(TAG + " other")
check("fixtures posted public", bool(target) and bool(other), f"{target} {other}")
before = queue()
have_db = before is not None
if not have_db:
    print("  (DATABASE_URL not set: the table is not read directly; the duplicate and "
          "cascade pins fall back to the endpoint's own answer)")
st1, r1 = call(f"/api/skribls/{target}/report", {"reason": "spam", "note": "an advert"})
check("a first report is received", st1 == 202 and r1.get("status") == "received" and r1.get("new") is True,
      f"{st1} {r1}")
st2, r2 = call(f"/api/skribls/{target}/report", {"reason": "abuse"})
check("a second report from the same client is received the same way, and says it was not new",
      st2 == 202 and r2.get("status") == "received" and r2.get("new") is False, f"{st2} {r2}")
if have_db:
    after = queue()
    check("the operator's queue holds ONE report for the post", queue_count(after, target) == 1,
          f"queue says {queue_count(after, target)} — " + (after or "").strip().splitlines()[0])
    check("...with the first reason and its note", "spam x1" in after and "an advert" in after
          and "abuse" not in after.split(target, 1)[1].split("\n")[0], after[:400])
    check("the other post is not in the queue", other not in after)
st, one = call(f"/api/skribls/{target}")
ids = listed_ids()
check("the post is still readable after being reported", st == 200, str(st))
check("...and still listed: a report takes nothing down", target in ids, f"listed={target in ids}")

st, body = call(f"/api/skribls/{target}/report", {"reason": "not-a-reason"})
check("an unknown reason is refused with 400, naming the set",
      st == 400 and all(r in body.get("error", "") for r in REPORT_REASONS), f"{st} {body}")
st, body = call(f"/api/skribls/{target}/report", [1, 2])
check("a non-object body is refused with 400", st == 400, str(st))
st, body = call(f"/api/skribls/{target}/report", {"reason": "other", "note": 42})
check("a non-text note is refused with 400", st == 400, str(st))
st, body = call("/api/skribls/zzzzzzzzzzz/report", {"reason": "spam"})
check("an unknown id answers 404", st == 404, str(st))
st, body = call("/api/skribls/not%20an%20id!/report", {"reason": "spam"})
check("a malformed id answers 404, the same answer", st == 404, str(st))
# A post the reporter cannot read: an unlisted one IS readable by anybody
# with the link (and so reportable); a private one is not, and the standalone
# app cannot make one without an author. The rule is post.visible_to(), the
# same call GET makes; pin that the two agree on an unlisted post.
unl = post_public(TAG + " unlisted", visibility="unlisted")
st_get, _ = call(f"/api/skribls/{unl}")
st_rep, _ = call(f"/api/skribls/{unl}/report", {"reason": "other"})
check("an unlisted post — readable by its link — is reportable, as GET and report agree",
      st_get == 200 and st_rep == 202, f"GET {st_get}, report {st_rep}")

# ------------------------------------------------------------------ section 2
print("\nREPORT 2 — the sheet, through the page")
with sync_playwright() as sp:
    b = sp.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    sent = {}

    def on_req(r):
        if r.method == "POST" and r.url.split("?")[0].endswith("/report"):
            sent["url"] = r.url
            try:
                sent["body"] = json.loads(r.post_data or "{}")
            except Exception:
                sent["body"] = None
    pg.on("request", on_req)
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(600)

    per_tile = pg.evaluate("""() => {
        const tiles = [...document.querySelectorAll('#galleryList .tile')];
        return { tiles: tiles.length,
                 buttons: tiles.filter(t => t.querySelector('button.report[data-report]')).length,
                 ids: tiles.filter(t => t.querySelector('button.report').getAttribute('data-report') === t.getAttribute('data-id')).length }; }""")
    check("every tile carries a Report button naming its own post",
          per_tile["tiles"] > 0 and per_tile["buttons"] == per_tile["tiles"] and per_tile["ids"] == per_tile["tiles"],
          str(per_tile))
    sheet = pg.evaluate("""() => { const d = document.getElementById('reportSheet');
        return { role: d.getAttribute('role'), modal: d.getAttribute('aria-modal'), hidden: d.hidden,
                 reasons: [...d.querySelectorAll('input[name=reason]')].map(i => i.value) }; }""")
    check("the sheet is a dialog that says so, hidden until opened",
          sheet["role"] == "dialog" and sheet["modal"] == "true" and sheet["hidden"], str(sheet))
    check("its reasons are exactly the API's closed set, in order",
          tuple(sheet["reasons"]) == tuple(REPORT_REASONS), f"{sheet['reasons']} vs {list(REPORT_REASONS)}")
    words = pg.evaluate("() => document.querySelector('#reportSheet p').textContent")
    check("it says nothing is taken down automatically", "nothing is taken down automatically" in words.lower(), words)

    pg.click(f'button.report[data-report="{other}"]')
    pg.wait_for_timeout(450)
    check("opening moves focus into the sheet",
          pg.evaluate("() => document.getElementById('reportSheet').contains(document.activeElement)"))
    pg.click('#reportSheet input[value="copyright"]')
    pg.fill("#reportNote", "traced from a poster")
    pg.click("#reportSend")
    pg.wait_for_timeout(900)
    check("the request went to that tile's post, with the reason and note shown",
          sent.get("url", "").endswith(f"/api/skribls/{other}/report")
          and (sent.get("body") or {}).get("reason") == "copyright"
          and (sent.get("body") or {}).get("note") == "traced from a poster", str(sent))
    st_text = pg.evaluate("() => document.getElementById('reportStatus').textContent")
    btn = pg.evaluate(f"""() => {{ const b = document.querySelector('button.report[data-report="{other}"]');
        return {{ text: b.textContent.trim(), reported: b.getAttribute('data-reported'), disabled: b.disabled }}; }}""")
    check("the sheet thanks the reader", "thanks" in st_text.lower(), st_text)
    check("the tile's button becomes the record and stays pressable",
          btn["text"] == "Reported" and btn["reported"] == "1" and not btn["disabled"], str(btn))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    landed = pg.evaluate("() => { const a = document.activeElement; return a === document.body ? '(body)' : (a.getAttribute('data-report') || a.id || a.tagName); }")
    check("Escape closes it and focus returns to the button that opened it", landed == other, f"focus on {landed!r}")
    pg.click(f'button.report[data-report="{other}"]')
    pg.wait_for_timeout(400)
    again = pg.evaluate("""() => ({ open: !document.getElementById('reportSheet').hidden,
        send: document.getElementById('reportSend').disabled,
        status: document.getElementById('reportStatus').textContent })""")
    check("opening it again is the record, with nothing to send",
          again["open"] and again["send"] and "already" in again["status"].lower(), str(again))
    pg.keyboard.press("Escape")
    check("no page errors", not errs, "; ".join(errs[:2]))

    # A refused request is said in the sheet, and the sheet stays open to try again.
    pg.route(re.compile(r"/report$"), lambda route: route.fulfill(status=429, content_type="application/json",
                                                                   body=json.dumps({"error": "slow down"})))
    pg.click(f'button.report[data-report="{target}"]')
    pg.wait_for_timeout(300)
    pg.click("#reportSend")
    pg.wait_for_timeout(600)
    refused = pg.evaluate("""() => ({ open: !document.getElementById('reportSheet').hidden,
        status: document.getElementById('reportStatus').textContent,
        error: document.getElementById('reportStatus').classList.contains('error'),
        send: document.getElementById('reportSend').disabled })""")
    check("a 429 is said in the sheet as an error, and Send is offered again",
          refused["open"] and refused["error"] and "later" in refused["status"].lower() and not refused["send"],
          str(refused))
    pg.unroute(re.compile(r"/report$"))
    pg.close()
    b.close()

if have_db:
    final = queue()
    check("the report sent through the page is in the operator's queue with its reason",
          queue_count(final, other) == 1 and "copyright x1" in final and "traced from a poster" in final,
          (final or "")[:400])

passed = sum(1 for r in results if r[0])
print("\n" + "=" * 62 + f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
