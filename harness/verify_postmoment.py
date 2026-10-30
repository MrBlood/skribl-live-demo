#!/usr/bin/env python3
"""Posted!, the moment: the Post sheet once a drawing has posted, and when it has not.

THE OWNER, of the old posted state: "the Posted! should be more visible, like
background of accents or something (you don't really notice the top changing
- it's subtle) maybe think about a way to make it more of a moment - and a
back to skribls.net post timeline button? ... it just kind of dead ends on the
Posted card"; "maybe an animated blooby jumping up with his hands in the
air?"; then, of the mock, "all yes": A, the band; Blooby's jump; where to go
next; the caption in full; the reason in a calm card above Try again; the
sheet's words at the menu's sizes; Flip's "animation".

WHAT IS ASKED, AND HOW IT IS READ
  * THE BAND: "Posted!" painted (elementFromPoint at its middle, never a
    rect), on the brand's purple (the band's own pixels), with the line each
    editor says; the form folded away (no box at all for the title, the
    fields or the button).
  * THE CARD: the posted title, the whole caption in its words with two
    lines of it shown and a "more", and whether it is in the gallery. It
    starts on the drawing's own ground and the drawing draws itself there,
    read on every frame: its finished picture is never shown first and then
    taken away (the picture is the card under Reduce Motion).
  * THE DRAWING IN ITS OWN SHAPE (the owner, of a long caption on the old
    200px band: "comment chokes out canvas"): tall, wide and square, Pad and
    Flip, phone and desk, the card's box is the shape of the canvas the suite
    gave the editor, centred and no wider than the words, as big as the sheet
    has room for up to half the screen, and all of the sheet on the screen
    with Watch painted; a window too short for it all keeps the drawing at
    160px and scrolls, and refits when it has its height back.
  * TWO LINES OF THE CAPTION: a painted "more", 44px, its state and its word
    in its name; it opens the rest in place, the sheet staying up and the
    drawing at its size, even when the window changes while it is open;
    "less" puts it back; the next post starts at two lines; a caption that
    fits has none; "more" 7:1, light and dark.
  * IT PLAYS: the card's drawing is the in-post player's, on the payload just
    sent. The Pad's plays once, about three seconds, and rests on the finished
    drawing (inked, at its end); a Flip of two pages goes round twice and
    rests on its first page, its passes counted on every frame.
  * BLOOBY JUMPS: the seven poses of his strip, each in turn, read on every
    frame, in about 0.8 s, and the one he stays in is the cheer badge's (his
    pixels against blooby-cheer.webp's, beside a pose that is not).
  * IT GLIDES: the sheet's height read on every frame from the old height to
    the new, no frame a jump, and the parts rise in rather than appear.
  * REDUCE MOTION: none of that moves. Nothing glides or rises, Blooby is
    cheering from the first frame, and the card is the picture.
  * WHERE TO GO NEXT: Make another closes the sheet and starts a new drawing
    with New Skribl's Undo, which brings this one back (both editors); Back to
    the site only when the site named it, and it goes there; the x closes;
    focus is on Watch once the button that posted has gone.
  * WATCH ON THE HOME SCREEN opens in place, not in a new tab, which there is
    Safari; in a browser tab, a new tab as before.
  * THE HOST NAMES ITS HOME once (create_blueprint(home_url, home_label)):
    rendered into both editors, null standalone, and anything but an http(s)
    address or a path on the site refused at startup.
  * THE REASON, when a post does not go: in a card in the sheet's own ink with
    the danger's mark, right above Try again, both on a phone's screen; while
    it sends, "Posting…" under the button. Flip says animation, and that it
    is saved on this device when the network or the server failed.
  * THE WORDS AT THE MENU'S SIZES: nothing painted in the sheet under 12px,
    and the sizes the mock named.
  * COMPOSE MODE renders none of the moment: nothing is posted there.
"""
import io
import json
import os
import re
import sys

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
    from PIL import Image
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the posted moment is a moment.")
    raise SystemExit(77)
import browsing  # noqa: E402

# For calibration: POSTMOMENT_PART=band,card,... runs only those parts.
PART = [p for p in (os.environ.get("POSTMOMENT_PART") or "").split(",") if p]


def part(name):
    return not PART or name in PART


PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=3, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
CAPTION = ("She sits there every morning and tells the birds what she thinks of them. "
           "Then she naps in the one square of sun, and nobody may move her.")

# Every frame from the moment the sheet is .is-posted: the sheet's box, its
# classes, the band's opacity and Blooby's pose. Installed before Post is
# pressed, so the first frame of the moment is in it. And every long task the
# page runs, so a frame the page itself held is told from one the box held.
SAMPLER = """() => {
  const sheet = document.getElementById('postSheet'), img = document.getElementById('postJump');
  window.__pm = []; let on = false, t0 = 0;
  window.__pmlt = []; window.__pm0 = null;
  try { new PerformanceObserver(l => l.getEntries().forEach(e => window.__pmlt.push([e.startTime, e.duration])))
          .observe({ type: 'longtask' }); } catch (e) {}
  const pose = () => { const m = /translateX\\((-?[\\d.]+)%\\)/.exec(img ? img.style.transform : '');
                       return m ? Math.round(-parseFloat(m[1]) * 7 / 100) : null; };
  function tick(t) {
    const band = sheet.querySelector('.post-band');
    const pic = document.getElementById('postCardPic');
    window.__pm.push({ t: t - t0, h: sheet.getBoundingClientRect().height, cls: sheet.className,
                       band: band ? +getComputedStyle(band).opacity : null, pose: pose(),
                       pic: !!pic && !!pic.getAttribute('src') && pic.getClientRects().length > 0 && getComputedStyle(pic).visibility === 'visible',
                       on: !!document.querySelector('#postCardPlayer.is-on') });
    if (window.__pm.length < 240) requestAnimationFrame(tick);
  }
  new MutationObserver(() => {
    if (on || !sheet.classList.contains('is-posted')) return;
    on = true; t0 = performance.now(); window.__pm0 = t0; requestAnimationFrame(tick);
  }).observe(sheet, { attributes: true, attributeFilter: ['class'] });
}"""


def goto(pg, path):
    browsing.goto(pg, BASE, path)
    pg.wait_for_timeout(900)
    pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide(); }")


def scribble(pg, sel, k=0):
    box = pg.locator(sel).bounding_box()
    x0, y0 = box["x"] + box["width"] * (0.25 + 0.1 * k), box["y"] + box["height"] * 0.35
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    for i in range(1, 25):
        pg.mouse.move(x0 + i * box["width"] * 0.018, y0 + (i % 6) * box["height"] * 0.03, steps=2)
        pg.wait_for_timeout(16)
    pg.mouse.up()
    pg.wait_for_timeout(200)


def drawn(pg, ed, pages=1):
    """A drawing on the Pad (its take ended) or a Flip of `pages` pages."""
    if ed == "pad":
        for k in range(3):
            scribble(pg, "#canvas", k)
            pg.wait_for_timeout(500)
        pg.evaluate("() => { if (typeof recording !== 'undefined' && recording) endRecordingTake(); }")
        pg.wait_for_timeout(300)
    else:
        scribble(pg, "#pad")
        for k in range(1, pages):
            pg.evaluate("() => addFrame(false)")
            pg.wait_for_timeout(200)
            scribble(pg, "#pad", k)


def post(pg, title="Window cat", caption=CAPTION, public=True, wait=True):
    pg.click("#postBtn")
    pg.wait_for_selector("#postSheet", state="visible")
    pg.wait_for_timeout(450)
    pg.fill("#postTitleInput", title)
    pg.fill("#postCaptionInput", caption)
    if public != pg.is_checked("#postPublicInput"):
        pg.locator("#postSheet .post-check").click()
    pg.click("#postSubmitBtn")
    if wait:
        pg.wait_for_selector("#postDone:not([hidden])", timeout=20000)


# The card's player, as the in-post player reports itself.
CARD = """() => { const p = window.SkriblInline && SkriblInline.players().find(x => x.el.id === 'postCardPlayer');
  return p ? Object.assign(p.state(), { rate: p.rate(), looping: p.looping() }) : null; }"""


def shot(pg, sel):
    return Image.open(io.BytesIO(pg.locator(sel).screenshot(animations="disabled"))).convert("RGB")


def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def worst(pg, sel, scale):
    """The word's ink against what is painted behind it, at nine points of its
    text's box, the words hidden for the photograph (verify_linkpage's)."""
    box = pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null;
      const r = document.createRange(); r.selectNodeContents(e); const b = r.getBoundingClientRect();
      const c = getComputedStyle(e).color.match(/[\\d.]+/g).map(Number);
      return { l: b.left, t: b.top, r: b.right, b: b.bottom, ink: c }; }""", sel)
    if not box:
        return None
    st = pg.add_style_tag(content="body * { color: transparent !important; }")
    pg.wait_for_timeout(80)
    im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    st.evaluate("s => s.remove()")
    a = box["ink"][3] if len(box["ink"]) > 3 else 1
    out = None
    for i in range(3):
        for j in range(3):
            x = int((box["l"] + (box["r"] - box["l"]) * (i + .5) / 3) * scale)
            y = int((box["t"] + (box["b"] - box["t"]) * (j + .5) / 3) * scale)
            g = im.getpixel((x, y))
            ink = [box["ink"][k] * a + g[k] * (1 - a) for k in range(3)]
            v = ratio(ink, g)
            out = v if out is None else min(out, v)
    return out


def mean_diff(a, b):
    b = b.resize(a.size)
    pa, pb = a.load(), b.load()
    n, tot = 0, 0
    for y in range(0, a.height, 2):
        for x in range(0, a.width, 2):
            p, q = pa[x, y], pb[x, y]
            tot += abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2])
            n += 3
    return tot / n


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------------------------------------------------------- the band
    if part("band") or part("card") or part("play") or part("jump") or part("glide") or part("focus"):
        print("\nTHE BAND, THE CARD, BLOOBY AND THE GLIDE (Pad, on a phone)")
        for theme in ("light", "dark"):
            ctx = b.new_context(color_scheme=theme, **PHONE)
            pg = ctx.new_page()
            goto(pg, "/")
            # A WIDE DRAWING, so the sheet has a new height to glide to: the
            # card's drawing takes the room the sheet has, so a tall one leaves
            # the posted sheet as full as the form was, and nothing glides.
            pg.evaluate("() => establishEditorCanvas(944, 531)")
            pg.wait_for_timeout(400)
            drawn(pg, "pad")
            pg.evaluate(SAMPLER)
            post(pg)
            pg.wait_for_timeout(250)
            if part("band"):
                r = pg.evaluate("""() => {
                  const h = document.getElementById('postDoneHead'), l = document.getElementById('postDoneLine');
                  const r = h.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  const gone = ['.post-top', '#postBody', '#postSubmitBtn'].map(s => document.querySelector('#postSheet ' + s))
                    .every(e => !e || !e.getClientRects().length);
                  return { head: h.textContent.trim(), painted: !!hit && h.contains(hit), line: l.textContent.trim(),
                           gone, status: document.getElementById('postStatus').hidden }; }""")
                check(f"Pad, {theme}: once posted, 'Posted!' is painted on the band, and the line says anyone with the link can watch it draw itself",
                      r["head"] == "Posted!" and r["painted"] and r["line"] == "Anyone with the link can watch it draw itself.", str(r))
                check(f"Pad, {theme}: ...the form folds away: no title, fields or Post button left on the sheet, and no status line",
                      r["gone"] and r["status"], str(r))
                pg.wait_for_timeout(500)
                band = shot(pg, "#postSheet .post-band")
                px = band.getpixel((max(2, band.width // 12), band.height - max(4, band.height // 10)))
                check(f"Pad, {theme}: ...on the brand's purple, the same in both themes",
                      px[2] > 150 and px[2] > px[0] + 30 and px[0] > px[1] and px[1] < 110, f"the band's foot is {px}")
            if part("card"):
                c = pg.evaluate("""() => { const t = document.getElementById('postCardTitle'), c = document.getElementById('postCardCaption'),
                  m = document.getElementById('postCardMeta'), pic = document.getElementById('postCardPic'), pv = document.getElementById('postPreviewImg'),
                  more = document.getElementById('postCardMore');
                  return { title: t.textContent, caption: c.hidden ? null : c.textContent,
                           lines: +(c.getBoundingClientRect().height / parseFloat(getComputedStyle(c).lineHeight)).toFixed(2),
                           more: !!more && !more.hidden, meta: m.textContent,
                           pic: !!pic.getAttribute('src') && pic.getAttribute('src') === pv.getAttribute('src') }; }""")
                check(f"Pad, {theme}: the card shows the posted title, its whole caption in its words with two lines of it shown and a 'more', and that it is in the gallery",
                      c["title"] == "Window cat" and c["caption"] == CAPTION and c["lines"] <= 2.05 and c["more"]
                      and c["meta"] == "In the public gallery", str(c))
                pg.wait_for_function("() => window.__pm.some(f => f.on) || window.__pm.length >= 240", timeout=15000)
                fr = pg.evaluate("() => window.__pm")
                first_on = next((i for i, f in enumerate(fr) if f["on"]), None)
                shown = [round(f["t"]) for f in fr[:first_on or len(fr)] if f["pic"]]
                check(f"Pad, {theme}: ...on the drawing's own ground the drawing draws itself, its finished picture never shown first",
                      first_on is not None and fr[first_on]["t"] < 2500 and not shown,
                      f"drawing from {first_on is not None and round(fr[first_on]['t'])} ms; the picture shown before it at {shown[:6]}")
            if part("focus"):
                a = pg.evaluate("() => document.activeElement && document.activeElement.id")
                check(f"Pad, {theme}: the button that posted is gone, and focus is on Watch, not on nothing",
                      a == "postWatchBtn", f"focus on {a!r}")
            if part("play"):
                pg.wait_for_timeout(300)
                s1 = pg.evaluate(CARD)
                pg.wait_for_timeout(600)
                s2 = pg.evaluate(CARD)
                want = max(1, (s1 or {}).get("totalMs", 0) / 3000)
                check(f"Pad, {theme}: the card is the in-post player on the drawing just posted, drawing itself, once, in about three seconds",
                      bool(s1 and s2) and s1["loaded"] and s1["kind"] == "replay" and s2["state"] == "playing" and want > 1
                      and s2["elapsedMs"] > s1["elapsedMs"] and not s1["looping"] and abs(s1["rate"] - want) < 0.01 * want,
                      f"{s1} then {s2}; rate wanted {want:.2f}")
                try:
                    pg.wait_for_function("""() => { const p = window.SkriblInline && SkriblInline.players().find(x => x.el.id === 'postCardPlayer');
                        return p && p.state().state !== 'playing'; }""", timeout=12000)
                except Exception:                                   # noqa: BLE001
                    pass
                e = pg.evaluate("""() => { const p = window.SkriblInline && SkriblInline.players().find(x => x.el.id === 'postCardPlayer');
                  if (!p) return null; const s = p.state();
                  const cv = p.el.querySelector('canvas'), x = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
                  let ink = 0; for (let i = 0; i < x.length; i += 16) if (x[i + 2] > x[i] + 40) ink++;
                  return { state: s.state, at: s.elapsedMs, total: s.totalMs, ink }; }""")
                check(f"Pad, {theme}: ...and rests on the finished drawing, inked, at its end",
                      bool(e) and e["state"] != "playing" and e["at"] >= e["total"] - 1 and e["ink"] > 30, str(e))
            if part("jump") or part("glide"):
                pg.wait_for_function("() => window.__pm.length && window.__pm[window.__pm.length - 1].t > 1300", timeout=15000)
            if part("jump"):
                fr = pg.evaluate("() => window.__pm")
                poses = [f["pose"] for f in fr if f["pose"] is not None]
                seq = [x for i, x in enumerate(poses) if i == 0 or x != poses[i - 1]]
                t6 = next((f["t"] for f in fr if f["pose"] == 6), None)
                img = pg.evaluate("() => { const i = document.getElementById('postJump'); return [i.naturalWidth, i.naturalHeight]; }")
                check(f"Pad, {theme}: Blooby jumps: each of his strip's seven poses in turn, read on every frame, in about 0.8 s, and he stays in the last",
                      img[0] == 7 * img[1] and seq == [0, 1, 2, 3, 4, 5, 6] and t6 is not None and 650 <= t6 <= 1500 and poses[-1] == 6,
                      f"strip {img}; poses {seq}; at the last after {t6 and round(t6)} ms")
                if theme == "light":
                    him = shot(pg, "#postSheet .post-jump")
                    pg.evaluate("() => { document.getElementById('postJump').style.transform = 'translateX(' + (-5 * 100 / 7) + '%)'; }")
                    land = shot(pg, "#postSheet .post-jump")
                    pg.evaluate("() => { document.getElementById('postJump').style.transform = 'translateX(' + (-6 * 100 / 7) + '%)'; }")
                    import pathlib
                    badge = Image.open(pathlib.Path(__file__).resolve().parent.parent / "skribl/static/brand/blooby-cheer.webp").convert("RGBA")
                    flat = Image.new("RGB", badge.size, him.getpixel((1, 1)))   # the band, at his box's corner
                    flat.paste(badge, (0, 0), badge)
                    d_rest, d_land = mean_diff(him, flat), mean_diff(land, flat)
                    check("Pad: ...the pose he stays in is the cheer badge's, his own drawn line (and the landing before it is not)",
                          d_rest < 9 and d_land > d_rest + 3, f"against blooby-cheer.webp: resting {d_rest:.1f}, landing {d_land:.1f}")
            if part("glide"):
                fr = pg.evaluate("() => window.__pm")
                hs, ts = [f["h"] for f in fr], [f["t"] for f in fr]
                h0, h1 = hs[0] if hs else 0, hs[-1] if hs else 0
                way = abs(h1 - h0)
                steps = [(ts[i] - ts[i - 1], abs(hs[i] - hs[i - 1]), i) for i in range(1, len(hs))]
                moving = [s for s in steps if s[1] > 0.5]
                back = any((hs[i] - hs[i - 1]) * (h1 - h0) < -1 for i in range(1, len(hs)))
                glide_ms = next((f["t"] for f in fr if "is-gliding" not in f["cls"] and f["t"] > 30), None)
                # A FRAME THE BOX HELD IS NOT A JUMP. The ease's fastest
                # stretch is about 16% of the way a frame, so a frame 45ms long
                # reads 40% of it at once. This box draws in software: two runs
                # in three here had a 33ms frame at the start, with nothing of
                # the page's running. A frame the PAGE held is the page's fault
                # (the height is laid out on the page's own thread), so a step
                # is set aside only across a frame of 30ms and more in which
                # the page ran no long task; one, the biggest, named in the
                # detail. Six frames moving still have to be read.
                t0 = pg.evaluate("() => window.__pm0") or 0
                tasks = [(a - t0, a - t0 + d) for a, d in pg.evaluate("() => window.__pmlt || []")]
                dts = sorted(s[0] for s in steps)
                usual = dts[len(dts) // 2] if dts else 16.7
                held = [s for s in steps if s[0] >= max(30, 1.5 * usual) and s[1] > 0.4 * way
                        and not any(a < ts[s[2]] and b_ > ts[s[2] - 1] for a, b_ in tasks)]
                aside = max(held, key=lambda s: s[1]) if held else None
                big = max((s[1] for s in steps if s is not aside), default=0)
                ours = [(round(a), round(b_ - a)) for a, b_ in tasks if b_ > 0 and a < (ts[-1] if ts else 0)]
                check(f"Pad, {theme}: the sheet glides to its new height: {len(moving)} frames between, none a jump, never back",
                      way > 20 and len(moving) >= 6 and big <= 0.4 * way and not back,
                      f"{round(h0)} -> {round(h1)} px; largest step {big:.1f}; frames moving {len(moving)}; glide done at {glide_ms}"
                      + (f"; set aside: {aside[1]:.1f}px across a {round(aside[0])}ms frame the box held" if aside else "")
                      + (f"; the page's long tasks meanwhile (at, ms) {ours}" if ours else ""))
                ops = [f["band"] for f in fr if f["band"] is not None]
                rising = [o for o in ops if 0.02 < o < 0.98]
                check(f"Pad, {theme}: ...and the band rises in over frames rather than appearing",
                      bool(ops) and ops[0] < 0.2 and ops[-1] > 0.99 and len(rising) >= 4, f"opacity {[round(o, 2) for o in ops[:14]]}")
            ctx.close()

    # ---------------------------------------------------------------- reduce motion
    if part("still"):
        print("\nREDUCE MOTION: none of it moves")
        ctx = b.new_context(reduced_motion="reduce", **PHONE)
        pg = ctx.new_page()
        goto(pg, "/")
        drawn(pg, "pad")
        pg.evaluate(SAMPLER)
        post(pg)
        pg.wait_for_timeout(900)
        fr = pg.evaluate("() => window.__pm")
        st = pg.evaluate(CARD)
        r = pg.evaluate("""() => { const pic = document.getElementById('postCardPic'), pv = document.getElementById('postPreviewImg');
          return { pic: !!pic.getAttribute('src') && pic.getAttribute('src') === pv.getAttribute('src') && pic.getClientRects().length > 0
                        && pic.naturalWidth > 0 && getComputedStyle(pic).visibility === 'visible',
                   head: document.getElementById('postDoneHead').textContent }; }""")
        check("Reduce Motion: nothing glides or rises, and Blooby is cheering from the first frame",
              bool(fr) and all("is-gliding" not in f["cls"] and "is-rising" not in f["cls"] for f in fr)
              and all(f["pose"] == 6 for f in fr if f["pose"] is not None) and fr[0]["band"] > 0.99,
              f"{len(fr)} frames; classes seen {sorted({c for f in fr for c in f['cls'].split()})}; poses {sorted({f['pose'] for f in fr})}")
        check("Reduce Motion: ...and the card is the picture the sheet showed: the drawing does not play itself",
              r["pic"] and (st is None or st["state"] != "playing") and r["head"] == "Posted!", f"{r}; player {st}")
        ctx.close()

    # ---------------------------------------------------------------- Flip
    if part("flip"):
        print("\nFLIP: its own line, and twice round, resting on its first page")
        ctx = b.new_context(**PHONE)
        pg = ctx.new_page()
        goto(pg, "/flip")
        drawn(pg, "flip", pages=5)
        pg.evaluate("""() => { window.__laps = []; let last = -1;
          (function t() { const p = window.SkriblInline && SkriblInline.players().find(x => x.el.id === 'postCardPlayer');
            if (p) { const s = p.state(); window.__laps.push([s.state, Math.round(s.elapsedMs), s.totalMs]); }
            if (window.__laps.length < 1200) requestAnimationFrame(t); })(); }""")
        post(pg, title="Bounce", caption="Two pages, one ball, no rush.", public=False)
        r = pg.evaluate("""() => ({ line: document.getElementById('postDoneLine').textContent.trim(),
            meta: document.getElementById('postCardMeta').textContent, caption: document.getElementById('postCardCaption').textContent })""")
        check("Flip: once posted, the band's line says anyone with the link can watch it play; unlisted, the card says it is shared by its link",
              r["line"] == "Anyone with the link can watch it play." and r["meta"] == "Shared by its link only"
              and r["caption"] == "Two pages, one ball, no rush.", str(r))
        try:
            pg.wait_for_function("""() => { const p = window.SkriblInline && SkriblInline.players().find(x => x.el.id === 'postCardPlayer');
                if (!p) return false; const s = p.state(); return window.__laps.some(l => l[0] === 'playing') && s.state !== 'playing'; }""", timeout=20000)
        except Exception:                                           # noqa: BLE001
            pass
        pg.wait_for_timeout(400)
        laps = pg.evaluate("() => window.__laps")
        play = [l for l in laps if l[0] == "playing"]
        wraps = sum(1 for i in range(1, len(play)) if play[i][1] < play[i - 1][1] - 20)
        end = pg.evaluate(CARD)
        check("Flip: the card plays the five pages just posted twice round, counted on every frame, and rests on its first page",
              bool(play) and bool(end) and end["kind"] == "flip" and wraps == 1 and end["state"] != "playing" and end["elapsedMs"] == 0,
              f"{len(play)} frames playing; turns {wraps}; at rest {end}")
        ctx.close()

    # ---------------------------------------------------------------- the card's drawing and words
    # THE DRAWING IN ITS OWN SHAPE, AND TWO LINES OF THE CAPTION (the owner, of
    # a long caption on the old 200px band: "comment chokes out canvas"; "all
    # yes, skip the mock and just build it"). The shape asked of the box is the
    # canvas size the suite gave the editor, not anything the sheet says.
    if part("shape") or part("words"):
        print("\nTHE CARD: THE DRAWING IN ITS OWN SHAPE, TWO LINES OF ITS CAPTION")
        SHAPES = {"tall": (531, 944), "wide": (944, 531), "square": (707, 707)}
        CARD_BOX = """() => {
          const sh = document.getElementById('postSheet'), m = document.getElementById('postCardMedia'),
                w = sh.querySelector('.post-card-words'), cap = document.getElementById('postCardCaption'),
                more = document.getElementById('postCardMore'), watch = document.getElementById('postWatchBtn');
          const hit = (el) => { const r = el.getBoundingClientRect(), e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                                return !!e && el.contains(e); };
          const mb = m.getBoundingClientRect(), cb = m.parentNode.getBoundingClientRect(), ws = getComputedStyle(w);
          const mr = more.hidden ? null : more.getBoundingClientRect(), ss = getComputedStyle(sh);
          return { w: mb.width, h: mb.height, left: mb.left - cb.left, right: cb.right - mb.right,
                   words: w.getBoundingClientRect().width - parseFloat(ws.paddingLeft) - parseFloat(ws.paddingRight),
                   vh: innerHeight, over: sh.scrollHeight - sh.clientHeight,
                   full: sh.getBoundingClientRect().height >= parseFloat(ss.maxHeight) - 2,
                   watch: watch.getBoundingClientRect().bottom <= innerHeight && hit(watch),
                   lines: cap.hidden ? 0 : cap.getBoundingClientRect().height / parseFloat(getComputedStyle(cap).lineHeight),
                   whole: cap.scrollHeight <= cap.clientHeight + 1,
                   more: mr && { h: mr.height, painted: hit(more), word: more.textContent.trim(), name: more.getAttribute('aria-label'),
                                 expanded: more.getAttribute('aria-expanded') },
                   posted: sh.classList.contains('is-posted') && !document.getElementById('postOverlay').hidden }; }"""

        # A desk window taller than the sheet needs, where half the screen is
        # what holds a tall drawing back rather than the sheet's room.
        TALLWIN = dict(viewport={"width": 1280, "height": 1300}, device_scale_factor=1)

        def shaped(ed, size, shape, theme="light", caption=CAPTION):
            ctx = b.new_context(color_scheme=theme, **{"phone": PHONE, "desk": DESK, "tall window": TALLWIN}[size])
            pg = ctx.new_page()
            goto(pg, "/" if ed == "Pad" else "/flip")
            w, h = SHAPES[shape]
            pg.evaluate(f"() => {'establishEditorCanvas' if ed == 'Pad' else 'applyCanvasSize'}({w}, {h})")
            pg.wait_for_timeout(500)
            drawn(pg, "pad" if ed == "Pad" else "flip")
            post(pg, caption=caption)
            pg.wait_for_timeout(1200)
            return ctx, pg, w / h

        def fits(ed, size, shape, pg, ar):
            r = pg.evaluate(CARD_BOX)
            k = r["w"] / r["h"]
            room = min(r["words"] / ar, r["vh"] / 2)
            check(f"{ed}, {size}, a {shape} drawing: the card's box is the drawing's own shape, centred, no wider than the words",
                  abs(k - ar) / ar < 0.012 and abs(r["left"] - r["right"]) <= 1 and r["w"] <= r["words"] + 0.5,
                  f"box {r['w']:.1f}x{r['h']:.1f} ({k:.4f}, the drawing {ar:.4f}), {r['left']:.1f} | {r['right']:.1f}, words {r['words']:.1f}")
            check(f"{ed}, {size}, a {shape} drawing: ...as big as the sheet has room for, up to half the screen, and all of the sheet on it, Watch painted",
                  r["h"] <= r["vh"] / 2 + 1 and (r["h"] >= room - 1.5 or r["full"]) and r["over"] <= 1 and r["watch"],
                  f"{r['h']:.1f}px of {r['vh']} (it could be {room:.1f}); the sheet {'full' if r['full'] else 'not full'}, "
                  f"{r['over']}px over; Watch {'painted on the screen' if r['watch'] else 'NOT on the screen'}")
            return r

        if part("shape"):
            for ed, size, shape in (("Pad", "phone", "tall"), ("Pad", "phone", "wide"), ("Pad", "phone", "square"),
                                    ("Pad", "desk", "tall"), ("Pad", "desk", "wide"), ("Pad", "tall window", "tall"),
                                    ("Flip", "phone", "tall"), ("Flip", "desk", "square")):
                ctx, pg, ar = shaped(ed, size, shape)
                fits(ed, size, shape, pg, ar)
                ctx.close()
            # A window too short for all of it: the drawing keeps its floor and
            # the sheet scrolls to the rest; back to its height, it refits.
            ctx, pg, ar = shaped("Pad", "desk", "tall")
            pg.set_viewport_size({"width": 1280, "height": 560})
            pg.wait_for_timeout(500)
            s = pg.evaluate(CARD_BOX)
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.wait_for_timeout(500)
            t = pg.evaluate(CARD_BOX)
            check("a window too short for all of it: the drawing keeps 160px and the sheet scrolls to the rest; given its height back, it refits",
                  abs(s["h"] - 160) <= 1 and s["over"] > 1 and t["over"] <= 1 and t["h"] > 250 and abs(t["w"] / t["h"] - ar) / ar < 0.012,
                  f"short: {s['h']:.1f}px, {s['over']}px to scroll; back: {t['h']:.1f}px, {t['over']}px over")
            ctx.close()

        if part("words"):
            ctx, pg, ar = shaped("Pad", "phone", "tall")
            r = pg.evaluate(CARD_BOX)
            m = r["more"] or {}
            check("the card's caption: two lines of it and a painted 'more', 44px, its state and its word in its name",
                  r["lines"] <= 2.05 and not r["whole"] and m.get("h", 0) >= 44 and m.get("painted") and m.get("word") == "more"
                  and m.get("expanded") == "false" and m.get("name") == "Read more of the caption", str(r))
            pg.click("#postCardMore")
            pg.wait_for_timeout(600)
            o = pg.evaluate(CARD_BOX)
            om = o["more"] or {}
            check("'more' opens the rest in place: the sheet stays up and the drawing keeps its size",
                  o["posted"] and o["lines"] > 2.5 and o["whole"] and abs(o["w"] - r["w"]) < 0.5 and abs(o["h"] - r["h"]) < 0.5
                  and om.get("word") == "less" and om.get("expanded") == "true", f"{o}; before {r['w']:.1f}x{r['h']:.1f}")
            pg.set_viewport_size({"width": 402, "height": 873})
            pg.wait_for_timeout(500)
            g = pg.evaluate(CARD_BOX)
            check("...and with it open, a window change does not give the caption the drawing's room",
                  abs(g["h"] - r["h"]) <= 1.5 and g["lines"] > 2.5, f"{g['h']:.1f}px, was {r['h']:.1f}")
            pg.click("#postCardMore")
            pg.wait_for_timeout(600)
            z = pg.evaluate(CARD_BOX)
            check("'less' puts it back to two lines", z["lines"] <= 2.05 and (z["more"] or {}).get("word") == "more", str(z))
            # Opened again, then another post: its caption starts at two lines.
            pg.click("#postCardMore")
            pg.wait_for_timeout(500)
            pg.click("#postAnotherBtn")
            pg.wait_for_timeout(900)
            drawn(pg, "pad")
            post(pg, title="Window cat, again")
            pg.wait_for_timeout(1200)
            n = pg.evaluate(CARD_BOX)
            check("the next post's caption starts at two lines again, with its 'more'",
                  n["lines"] <= 2.05 and (n["more"] or {}).get("word") == "more" and (n["more"] or {}).get("expanded") == "false", str(n))
            ctx.close()
            ctx, pg, ar = shaped("Flip", "phone", "wide")
            f = pg.evaluate(CARD_BOX)
            check("Flip: its long caption is at two lines with its 'more' too",
                  f["lines"] <= 2.05 and not f["whole"] and (f["more"] or {}).get("painted") and (f["more"] or {}).get("word") == "more", str(f))
            ctx.close()
            ctx, pg, ar = shaped("Flip", "phone", "wide", caption="Two pages, one ball, no rush.")
            s = pg.evaluate(CARD_BOX)
            check("Flip: a caption that fits in two lines shows whole, with no 'more'",
                  s["more"] is None and s["whole"] and 0.5 < s["lines"] <= 2.05, str(s))
            ctx.close()
            for theme in ("light", "dark"):
                ctx, pg, ar = shaped("Pad", "phone", "square", theme=theme)
                v = worst(pg, "#postCardMore", 3)
                check(f"{theme}: the card's 'more' reads 7:1 on what is painted behind it", v is not None and v >= 7, f"{v and round(v, 2)}:1")
                ctx.close()

    # ---------------------------------------------------------------- where to go next
    if part("next"):
        print("\nWHERE TO GO NEXT: Make another, both editors, with New Skribl's Undo")
        for ed, path in (("Pad", "/"), ("Flip", "/flip")):
            ctx = b.new_context(**PHONE)
            pg = ctx.new_page()
            goto(pg, path)
            drawn(pg, "pad" if ed == "Pad" else "flip")
            count = ("() => strokes.length" if ed == "Pad" else "() => frames.reduce((n, f) => n + f.strokes.length, 0)")
            before = pg.evaluate(count)
            post(pg, public=False)
            pg.wait_for_timeout(500)
            r = pg.evaluate("""() => { const a = document.getElementById('postAnotherBtn'), h = document.getElementById('postHomeBtn');
              const r = a.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { painted: !!hit && a.contains(hit), h: Math.round(r.height), words: a.textContent.trim(), home: h.hidden }; }""")
            check(f"{ed}: once posted, Make another is offered, painted, a 44px tap; with no home named there is no Back",
                  r["painted"] and r["h"] >= 44 and r["words"] == "Make another" and r["home"], str(r))
            pg.click("#postAnotherBtn", timeout=5000)
            pg.wait_for_timeout(600)
            after = pg.evaluate(count)
            gone = pg.evaluate("() => document.getElementById('postOverlay').hidden")
            act = pg.locator("#toast .toast-action, #flipChip .toast-action")
            offer = act.count() and act.first.inner_text().strip()
            check(f"{ed}: ...it puts the sheet away and starts a new drawing, offering Undo",
                  before > 0 and after == 0 and gone and offer == "Undo", f"strokes {before} -> {after}; sheet hidden {gone}; offer {offer!r}")
            if offer == "Undo":
                act.first.click()
                pg.wait_for_timeout(500)
                back = pg.evaluate(count)
                check(f"{ed}: ...and Undo brings the posted drawing back", back == before, f"strokes {before} -> {after} -> {back}")
            ctx.close()

    if part("home"):
        print("\nBACK TO THE SITE, only when the site named it")
        for ed, path in (("Pad", "/"), ("Flip", "/flip")):
            ctx = b.new_context(**PHONE)
            pg = ctx.new_page()
            goto(pg, path)
            pg.evaluate("() => { window.SKRIBL_HOME = { url: '/gallery', label: 'skribls.net' }; }")
            drawn(pg, "pad" if ed == "Pad" else "flip")
            post(pg, public=False)
            pg.wait_for_timeout(500)
            r = pg.evaluate("""() => { const h = document.getElementById('postHomeBtn'), a = document.getElementById('postAnotherBtn');
              const r = h.getBoundingClientRect(), q = a.getBoundingClientRect(), hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { words: h.textContent.trim(), painted: !!hit && h.contains(hit), row: Math.abs(r.top - q.top) < 1, h: Math.round(r.height) }; }""")
            check(f"{ed}: with the site's home named, Back to skribls.net sits beside Make another, painted, a 44px tap",
                  r["words"] == "Back to skribls.net" and r["painted"] and r["row"] and r["h"] >= 44, str(r))
            went = None
            if r["painted"]:
                try:
                    with pg.expect_navigation(timeout=10000):
                        pg.click("#postHomeBtn")
                    went = pg.url
                except Exception as exc:                            # noqa: BLE001
                    went = f"no navigation: {exc!r}"[:120]
            check(f"{ed}: ...and goes to the address the site named", bool(went) and went.endswith("/gallery"), str(went))
            ctx.close()

    if part("close"):
        print("\nTHE X")
        ctx = b.new_context(**PHONE)
        pg = ctx.new_page()
        goto(pg, "/")
        drawn(pg, "pad")
        post(pg, public=False)
        pg.wait_for_timeout(500)
        r = pg.evaluate("""() => { const x = document.getElementById('postCloseBtn'), r = x.getBoundingClientRect();
          const edge = document.elementFromPoint(r.left - 3, r.top + r.height / 2);
          return { name: x.getAttribute('aria-label'), w: Math.round(r.width), band: !!edge && x.contains(edge) }; }""")
        pg.click("#postCloseBtn", timeout=5000)
        pg.wait_for_timeout(500)
        hidden = pg.evaluate("() => document.getElementById('postOverlay').hidden")
        check("the band's x is named Close, its tap 44px wide around the 36px circle, and it puts the sheet away",
              r["name"] == "Close" and r["w"] == 36 and r["band"] and hidden, f"{r}; sheet hidden {hidden}")
        ctx.close()

    if part("inplace"):
        print("\nWATCH, FROM THE HOME SCREEN AND IN A TAB")
        for app in (True, False):
            ctx = b.new_context(**PHONE)
            pg = ctx.new_page()
            goto(pg, "/")
            if app:
                pg.evaluate("() => document.documentElement.setAttribute('data-skribl-app', '')")
            drawn(pg, "pad")
            post(pg, public=False)
            pg.wait_for_timeout(400)
            pages = []
            ctx.on("page", lambda q: pages.append(q))
            pg.click("#postWatchBtn")
            pg.wait_for_timeout(1500)
            here = "/s/" in pg.url
            if app:
                check("Watch on the Home Screen app opens the link page in place, not a new tab (which there is Safari)",
                      here and not pages, f"this page at {pg.url}; new tabs {len(pages)}")
            else:
                check("...and in a browser tab, in a new tab as before",
                      not here and len(pages) == 1, f"this page at {pg.url}; new tabs {len(pages)}")
            ctx.close()

    # ---------------------------------------------------------------- the host's home
    if part("server"):
        print("\nTHE HOST NAMES ITS HOME, once")
        import pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
        from flask import Flask
        import skribl as _sk
        rendered = {}
        for name, kw in (("named", {"home_url": "https://www.skribls.net/home"}), ("standalone", {})):
            app = Flask(__name__)
            app.config["SECRET_KEY"] = "harness-postmoment"
            app.register_blueprint(_sk.create_blueprint(session=False, csrf=False, **kw))
            for path in ("/skribl-pad", "/flip"):
                html = app.test_client().get(path).get_data(as_text=True)
                m = re.search(r"window\.SKRIBL_HOME = (.*?);\s*\n", html)
                rendered[(name, path)] = json.loads(m.group(1)) if m else "absent"
        check("create_blueprint(home_url=...) is rendered into both editors, named by its host ('www.' left off)",
              all(rendered[("named", x)] == {"url": "https://www.skribls.net/home", "label": "skribls.net"} for x in ("/skribl-pad", "/flip")),
              str(rendered))
        check("...and standalone, unnamed, it is null in both", all(rendered[("standalone", x)] is None for x in ("/skribl-pad", "/flip")),
              str(rendered))
        refused = {}
        for u, lab in (("javascript:alert(1)", None), ("//evil.example", "x"), ("/\\evil.example", "x"),
                       ("https://a.example/x y", None), ("/home", None), (None, "skribls.net")):
            try:
                _sk.create_blueprint(session=False, home_url=u, home_label=lab)
                refused[repr(u)] = False
            except ValueError:
                refused[repr(u)] = True
        check("anything but an http(s) address or a path on the site is refused at startup, and a path needs a label",
              all(refused.values()), str(refused))

    # ---------------------------------------------------------------- the reason
    if part("reason"):
        print("\nTHE REASON, IN A CALM CARD RIGHT ABOVE TRY AGAIN")
        said = {}
        for ed, path in (("Pad", "/"), ("Flip", "/flip")):
            for how in ("offline", "server"):
                ctx = b.new_context(**PHONE)
                pg = ctx.new_page()
                goto(pg, path)
                drawn(pg, "pad" if ed == "Pad" else "flip")

                def fail(route, request=None, how=how):
                    if route.request.method != "POST":
                        return route.continue_()
                    if how == "offline":
                        return route.abort("internetdisconnected")
                    return route.fulfill(status=503, content_type="application/json", body="{}")
                pg.route("**/api/skribls", fail)
                post(pg, title="Offline", caption="", public=False, wait=False)
                pg.wait_for_selector("#postStatus.error:not([hidden])", timeout=20000)
                pg.wait_for_timeout(600)
                r = pg.evaluate("""() => { const s = document.getElementById('postStatus'), b = document.getElementById('postSubmitBtn');
                  const l = document.getElementById('postStatusLabel'), cs = getComputedStyle(s), lc = getComputedStyle(l), mk = getComputedStyle(s, '::before');
                  const probe = document.createElement('i'); probe.style.color = 'var(--text-primary)'; probe.style.background = 'var(--menu-card)';
                  s.parentNode.appendChild(probe); const want = getComputedStyle(probe); const ink = want.color, card = want.backgroundColor;
                  probe.style.background = 'var(--danger)'; const danger = getComputedStyle(probe).backgroundColor; probe.remove();
                  const r = s.getBoundingClientRect(), q = b.getBoundingClientRect();
                  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                  return { words: l.textContent.trim(), above: r.bottom <= q.top + 0.5, both: q.bottom <= innerHeight && r.top >= 0,
                           painted: !!hit && s.contains(hit), ink: lc.color === ink, size: lc.fontSize, card: cs.backgroundColor === card,
                           round: parseFloat(cs.borderTopLeftRadius) >= 12, mark: mk.content.indexOf('!') >= 0 && mk.backgroundColor === danger,
                           btn: b.textContent.trim() }; }""")
                said[(ed, how)] = r["words"]
                check(f"{ed}, {how}: the reason is a card in the sheet's own ink, 14px, with the danger's mark, painted right above Try again, both on screen",
                      r["above"] and r["both"] and r["painted"] and r["ink"] and r["size"] == "14px" and r["card"]
                      and r["round"] and r["mark"] and r["btn"] == "Try again", str(r))
                ctx.close()
        check("Flip says animation, and that it is saved on this device, as the owner's words have it",
              said[("Flip", "offline")] == "Couldn’t post. Your animation is still here, saved on this device. Try again when you’re back online."
              and said[("Flip", "server")].startswith("Couldn’t post. Your animation is still here, saved on this device."),
              str({k: v for k, v in said.items() if k[0] == "Flip"}))
        check("...and the Pad's words are as they were", said[("Pad", "offline")].startswith("Couldn’t post. Your drawing is still here, saved on this device."),
              said[("Pad", "offline")])
        # While it sends, "Posting…" keeps its place under the button.
        ctx = b.new_context(**PHONE)
        pg = ctx.new_page()
        goto(pg, "/")
        drawn(pg, "pad")
        held = []
        pg.route("**/api/skribls", lambda route: held.append(route) if route.request.method == "POST" else route.continue_())
        post(pg, caption="", public=False, wait=False)
        pg.wait_for_timeout(500)
        r = pg.evaluate("""() => { const s = document.getElementById('postStatus'), b = document.getElementById('postSubmitBtn');
          return { busy: !s.hidden && !s.classList.contains('error'), words: s.textContent.trim(),
                   under: s.getBoundingClientRect().top >= b.getBoundingClientRect().bottom - 0.5 }; }""")
        check("while it sends, 'Posting…' sits under the button that started it", r["busy"] and r["under"] and "Posting" in r["words"], str(r))
        for route in held:
            route.abort()
        ctx.close()

    # ---------------------------------------------------------------- the sizes
    if part("sizes"):
        print("\nTHE WORDS AT THE MENU'S SIZES")
        SIZES = """() => { const out = { small: [], at: {} };
          const w = document.createTreeWalker(document.getElementById('postSheet'), NodeFilter.SHOW_TEXT);
          for (let n = w.nextNode(); n; n = w.nextNode()) {
            if (!n.nodeValue.trim() || !n.parentElement.getClientRects().length) continue;
            const f = parseFloat(getComputedStyle(n.parentElement).fontSize);
            if (f < 12) out.small.push([n.nodeValue.trim().slice(0, 24), f]); }
          for (const [k, s] of [['label', '.post-field-label'], ['tick', '.post-check-text'], ['sub', '.post-check-sub'],
                                ['count', '#postCharCount'], ['hint', '.post-speed-hint']]) {
            const e = document.querySelector('#postSheet ' + s); if (!e) continue; const c = getComputedStyle(e);
            out.at[k] = c.fontSize + '/' + c.fontWeight; }
          return out; }"""
        for ed, path in (("Pad", "/"), ("Flip", "/flip")):
            for size, kw in (("phone", PHONE), ("desk", DESK)):
                ctx = b.new_context(**kw)
                pg = ctx.new_page()
                goto(pg, path)
                drawn(pg, "pad" if ed == "Pad" else "flip")
                pg.click("#postBtn")
                pg.wait_for_timeout(600)
                r = pg.evaluate(SIZES)
                at = r["at"]
                want = (at.get("label") == "13px/700" and at.get("tick") == "15px/500" and at.get("sub") == "13px/400"
                        and at.get("count") == "12px/400" and (ed == "Flip" or at.get("hint") == "13px/400"))
                check(f"{ed}, {size}: nothing painted in the Post sheet is under 12px, and the words are at the mock's sizes",
                      not r["small"] and want, str(r))
                ctx.close()

    if part("compose"):
        print("\nCOMPOSE MODE renders none of it")
        for path in ("/skribl-pad?compose=1", "/flip?compose=1"):
            import urllib.request
            html = urllib.request.urlopen(BASE + path, timeout=20).read().decode("utf-8", "replace")
            band, way = 'id="postDone"' in html, 'id="postNext"' in html
            check(f"{path}: no Posted! band, card or way on is rendered, nothing being posted there",
                  not band and not way and 'id="postSheet"' in html, f"band {band}; way on {way}")

    b.close()

summarise_and_exit()
