"""Both editors build a share card, through one builder — Flip never did.

/s/<id>/card.png is a 1200x630 Open Graph card carrying the drawing. It is what
a shared link unfurls with, and since the in-post player landed it is also what
an idle post shows in a feed and what a tile shows on the profile's Skribls tab.

FLIP NEVER BUILT ONE. `buildShareCardDataURL()` lived in editor_post.js, which
is Pad-only; flip.js's `buildSharePayload()` set no `thumbnail` at all. Every
Flip post therefore fell through to the static branded og-card in all three
places — an advert where the drawing should be. Nothing revealed it, because the
person who posts a Skribl does not look at their own unfurl, and because the
fallback is a real image rather than a broken one.

Same shape as the defect verify_flipmeta.py records — "a whole control surface
that was never built on one of the two editors" — and found the same way: by
building something downstream that depended on it.

The fix is not "add a card to Flip". It is ONE builder in lib/sharecard.js, next
to the geometry the in-post player already crops by, with each editor supplying
only its own flat canvas — the part that genuinely differs between a recording
and an animation. This suite asserts the outcome (both editors' posts carry a
real card) and the arrangement (there is only one composite in the tree), because
the outcome alone would go green again the moment somebody copied the builder
back into one of them.
"""
import io
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    print("No assertions were executed. This is NOT evidence the cards are built.")
    raise SystemExit(77)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return r.read(), r.geturl()


GENERIC, _ = get(BASE + "/static/skribl/og-card.png")


def card_of(pid):
    """The bytes /s/<id>/card.png actually serves, and where it landed."""
    return get(BASE + "/s/" + pid + "/card.png")


# ---- source gates first: they cost no browser ------------------------------
lib = (ROOT / "skribl" / "static" / "lib" / "sharecard.js").read_text(encoding="utf-8")
post = (ROOT / "skribl" / "static" / "editor_post.js").read_text(encoding="utf-8")
flip = (ROOT / "skribl" / "static" / "flip.js").read_text(encoding="utf-8")

card = (ROOT / "skribl" / "static" / "lib" / "postedcard.js").read_text(encoding="utf-8")
check("lib/postedcard.js composites the card",
      "function build(" in card and "createRadialGradient" in card)
# GEOMETRY AND COMPOSITE ARE SEPARATE FILES ON PURPOSE, the same way
# lib/postedaudio.js is separate: a host embedding the in-post player needs
# band() to crop a poster and never composites anything, because it never
# posts. Merging them put 2 KB of canvas work on every feed page and blew
# verify_inline.py's embed ratchet, which is the job that ratchet has.
check("and lib/sharecard.js, which the feed DOES load, carries no compositor",
      "createRadialGradient" not in lib and "band" in lib)
# ONE COMPOSITE IN THE TREE. The accent wash is unique to the card and cheap to
# find, so it stands in for the whole composite: if it appears anywhere else,
# somebody has a second card builder and the two will drift the way the geometry
# did before this module existed.
_copies = sorted(p.name for p in (ROOT / "skribl" / "static").rglob("*.js")
                 if "createRadialGradient(" in p.read_text(encoding="utf-8")
                 and "gifenc" not in p.name and "muxer" not in p.name)
check("and it is the only file that composites one",
      _copies == ["postedcard.js"], ", ".join(_copies))
check("the Pad builds its card through the module",
      "SkriblPostedCard" in post and "PC.build(" in post)
check("FLIP BUILDS ONE AT ALL — it never used to",
      "thumbnail" in flip and "PC.build(" in flip,
      "flip.js set no payload.thumbnail before this, so every Flip post "
      "unfurled, postered and tiled as the generic branded card")

for tpl, label in (("skribl_editor.html", "Pad"), ("skribl_flip.html", "Flip")):
    body = (ROOT / "skribl" / "templates" / "skribl" / tpl).read_text(encoding="utf-8")
    for mod in ("lib/sharecard.js", "lib/postedcard.js"):
        check(f"{label} loads {mod}", mod in body,
              "reading a global nothing loads is a silent fallback")
inline_macro = (ROOT / "skribl" / "templates" / "skribl"
                / "_skribl_inline_player.html").read_text(encoding="utf-8")
check("the in-post embed loads the geometry but NOT the compositor",
      "lib/sharecard.js" in inline_macro and "lib/postedcard.js" not in inline_macro,
      "a feed page has no drawing to composite")

# ---- and now the round trip ------------------------------------------------
with sync_playwright() as sp:
    b = sp.chromium.launch()

    # PAD ---------------------------------------------------------------------
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/skribl-pad", wait_until="load")
    pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    box = pg.locator("#canvas").bounding_box()
    pg.mouse.move(box["x"] + 120, box["y"] + 120)
    pg.mouse.down()
    for i in range(24):
        pg.mouse.move(box["x"] + 120 + i * 14, box["y"] + 120 + (i % 6) * 22)
        pg.wait_for_timeout(30)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    pg.click("#recordBtn")
    pg.wait_for_timeout(400)
    pg.click("#postBtn")
    pg.wait_for_timeout(1000)
    pg.fill("#postTitleInput", "Pad card fixture")
    pg.click("#postSubmitBtn")
    pg.wait_for_timeout(7000)
    pad_url = pg.evaluate("""() => {
        const v = [...document.querySelectorAll('*')].map(e => e.value || e.href || '')
          .find(v => typeof v === 'string' && v.includes('/s/'));
        return v || null; }""")
    pg.close()
    pad_id = re.search(r"/s/([A-Za-z0-9_-]+)", pad_url).group(1) if pad_url else None
    check("a Pad Skribl was posted (fixture)", bool(pad_id), str(pad_url))

    # FLIP --------------------------------------------------------------------
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(1500)
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 70, box["y"] + 70)
    pg.mouse.down()
    for i in range(20):
        pg.mouse.move(box["x"] + 70 + i * 13, box["y"] + 70 + (i % 5) * 26, steps=2)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.click("#postBtn")
    pg.wait_for_timeout(600)
    pg.fill("#flipShareTitle", "Flip card fixture")
    pg.click("#flipShareSubmit")
    pg.wait_for_selector("#flipShareUrl", state="visible", timeout=25000)
    flip_url = pg.input_value("#flipShareUrl")
    pg.close()
    flip_id = re.search(r"/s/([A-Za-z0-9_-]+)", flip_url).group(1) if flip_url else None
    check("a Flip Skribl was posted (fixture)", bool(flip_id), str(flip_url))
    check("no page errors in either editor", not errs, "; ".join(errs[:2]))
    b.close()

if not (pad_id and flip_id):
    print("\n" + "=" * 62 + f"\n{sum(1 for ok, _ in results if ok)}/{len(results)} passed")
    sys.exit(1)

for pid, label in ((pad_id, "Pad"), (flip_id, "Flip")):
    body, landed = card_of(pid)
    # THE REGRESSION, stated as bluntly as it can be: a post whose card route
    # redirects to og-card.png has no card of its own, and its drawing appears
    # nowhere a reader looks first.
    check(f"a {label} post's card is its own drawing, not the branded fallback",
          body != GENERIC and "og-card" not in landed,
          f"served {len(body):,} B from {landed}")
    # 1200x630 is load-bearing, not decoration: inlineplayer.css crops the
    # poster by fractions of exactly that, so a card of another size would put
    # the wordmark back in frame on every feed post. Read through Pillow because
    # the format is no longer fixed — the builder encodes both ways and keeps
    # the smaller, so a card may be PNG or JPEG.
    try:
        from PIL import Image
        size = Image.open(io.BytesIO(body)).size
        fmt = Image.open(io.BytesIO(body)).format
    except Exception as exc:
        size, fmt = None, f"unreadable ({exc})"
    check(f"the {label} card is the 1200x630 the crop assumes",
          size == (1200, 630), f"{size} ({fmt})")

    # THE RATCHET THAT WOULD HAVE CAUGHT THIS. The card is the IDLE COST OF
    # EVERY POST IN A FEED — the in-post player's poster — so its weight is a
    # product constraint, not a detail. A line-art card was 451,824 B until the
    # builder stopped choosing PNG on a rule that had gone wrong (see the note
    # at the encoder); a screenful of twelve was over five megabytes to show
    # twelve thumbnails. Pinned well above what a real drawing costs and far
    # below what the old rule produced, so a return to it fails here.
    check(f"the {label} card is not enormous",
          len(body) <= 200_000,
          f"{len(body):,} B — the poster of every post in a feed")

# The two cards must not be the same image — the same drawing composited twice
# would mean one of the fixtures did not reach the builder.
pad_bytes, _ = card_of(pad_id)
flip_bytes, _ = card_of(flip_id)
check("the two cards carry different drawings",
      pad_bytes != flip_bytes,
      "identical bytes would mean one fixture's flat canvas never arrived")

passed = sum(1 for ok, _ in results if ok)
bad = [name for ok, name in results if not ok]
print("\n" + "=" * 62)
print(f"{passed}/{len(results)} passed" + ("" if not bad else "\nFAILURES:\n  - " + "\n  - ".join(bad)))
sys.exit(1 if bad else 0)
