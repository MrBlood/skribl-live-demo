"""Rendered geometry for the header and tool row — the class of defect no
attribute check can see.

WHY THIS IS A NEW SUITE. Every assertion here is about LAYOUT, and layout is
the one thing this project has repeatedly got wrong while every attribute
passed: the v213 record pill wrapped, Pad wrapped at 320px, and the harness was
green throughout. A suite is its own suite because it asks one kind of
question, never because another suite passed a size.

THE RULE THIS SUITE ENFORCES ON ITSELF. Measure what the browser laid out,
never what the CSS was told to do. Flex shrinks controls before anything
overflows, so summing child widths reports room that is not there; and an
element can be `hidden` in every sense the DOM reports while still occupying
space. So: getBoundingClientRect, scrollWidth against clientWidth, and
offsetParent — not computed styles, not class lists.

SECTION 1 — the row fits on one line at every supported width.
    Pad WRAPPED at 320px (bar 113px tall against 68px) and Flip OVERFLOWED by
    16px, and neither was caught. The height IS the assertion: a wrapped bar is
    a taller bar, and that is measurable where "did it wrap" is not.

SECTION 2 — the header fits in every state, including mid-recording.
    This WAS a failing assertion. On the sealed v214 tree the recording state
    needed 396px against 355 available at 375px, and this section existed to
    reproduce that. Moving Flip Mode into the overflow menu freed 40px, which is
    more than the overage, so it now PASSES with +124px of slack at 375px.
    The section stays: it is the regression test for a bug that was real, and
    the header is the part of this layout with the least room to give.

SECTION 3 — touch targets.
    The mobile stylesheet sets .tool-open to 36px below 640px and the smallest
    control renders at 34px. That is below the 44px the docs assume. This
    section does not assert 44 — that is a product decision, not a fact — it
    asserts the floor the project has DECIDED on, so the number lives in one
    place and changing it is deliberate.

SECTION 4 — the Flip navigation guard.
    Asserts the URL after the click, not the sheet. A sheet appearing proves a
    sheet appeared; only the URL proves the work survived.

SECTION 5 — the move-bar readout does not spill its pill.
    The one defect in this file that every other measurement in it misses. A
    wrapped line inside a fixed-height pill leaves the BOX unchanged, so
    scrollWidth, the bar height and reachability all report "ok" while the
    second line paints over the control beside it. Measured as scrollHeight
    against the box's own height, with the offset written through the function
    that ships — setting textContent directly does not reproduce it.

Requires a running server. Run it like the other browser suites:
    ./harness/run_harness.sh verify_layout.py
"""
import sys
import base64
import pathlib
import tempfile

from playwright.sync_api import sync_playwright
from assertions import make_check
import browsing

BASE = "http://127.0.0.1:5001"

# One row, measured. A wrapped bar is a taller bar.
ONE_ROW_MAX_PX = 80

# TWO FLOORS, AND THEY ARE DIFFERENT NUMBERS ON PURPOSE (SK-AUD-005; the
# acquisition audit of v302 read the sentence that used to sit here -- "34
# because that is what ships today, not because 34 is defensible" -- as the
# product's touch-target policy, and it was never that. It was the VISIBLE box.)
#
#   MIN_TOUCH_PX  is the visible box: the glyph's own pill. 34 is the packing
#                 floor -- eight controls plus their gaps in a 360px row -- and
#                 the hit-region note in styles.css has the arithmetic for why
#                 widening the pills would make neighbouring targets ambiguous.
#   HIT_TOUCH_PX  is the box a finger actually gets: the pill plus its
#                 --tap-grow band (styles.css "Hit regions, separated from glyph
#                 size"), measured through elementFromPoint, which is the only
#                 thing that can see a band. 44 is Apple's number and it is
#                 what every bar and header control answers, at every width
#                 including 320, for the height. The width is the visible pill
#                 plus whatever is free beside it -- in a packed row the sides
#                 belong to the neighbours, so a mis-tap lands on a control,
#                 never on nothing; verify_a11y's census holds that half.
#
# Section 3 measures both. A control that shrinks its band is caught by the
# second even when its pill still clears the first.
MIN_TOUCH_PX = 34
HIT_TOUCH_PX = 44
# The 320 safety net degrades here too: the Pad's row wraps, and the second
# row sits inside the first row's band, so a tap 21px below a top-row control
# lands on the control beneath it -- a neighbour, never nothing. 40 is the
# same narrow-tier box verify_a11y's census records for Flip's bar below 360.
HIT_TOUCH_NARROW_PX = 40

# THE WIDTH POLICY, pinned here so it cannot drift back into folklore.
#
#   360px is the DESIGN TARGET — the narrowest width the layout must serve
#   properly, on one row, with nothing shrunk past the decided floor. It is a
#   very common Android width, so a two-row bar there is not a rare fallback.
#
#   320px is the SAFETY NET — not a design target. It is Display Zoom on a
#   modern iPhone, an accessibility setting rather than a legacy device, so it
#   must DEGRADE rather than break: wrap to a taller bar, clip nothing, spill
#   nothing off the page. A layout that survives 320 without breaking components
#   or spilling text works anywhere.
FIT_WIDTHS = [360, 375, 390, 393, 402, 430, 440, 600, 641, 768]
DEGRADE_WIDTHS = [320]

results = []
check = make_check(results)


GEOMETRY = """() => {
  // '.toolbar, .flip-tools' — BOTH, and the omission here was a real bug in this
  // suite rather than in the product. Pad's bar is `.toolbar`; Flip's is
  // `.flip-tools`. Section 2's REACH_Q below already used the compound selector,
  // this one did not, and so section 1 returned null on every Flip width and
  // reported "found a toolbar: False" ten times over. Nothing caught it because
  // this suite was written during the v219 build and the build was never run —
  // which is the whole argument for running one before sealing.
  const bar = document.querySelector('.toolbar, .flip-tools');
  if (!bar) return null;
  const r = bar.getBoundingClientRect();
  // offsetParent, not the hidden property: an explicit display defeats [hidden],
  // and this codebase has been bitten by that three times.
  const controls = [...bar.querySelectorAll('.tool-btn, .tool-open, .undo-btn')]
      .filter(e => e.offsetParent !== null)
      .map(e => ({ id: e.id, w: +e.getBoundingClientRect().width.toFixed(1) }));
  return {
    height: +r.height.toFixed(1),
    width:  +r.width.toFixed(1),
    overflow: bar.scrollWidth - bar.clientWidth,
    controls,
    smallest: controls.length ? Math.min(...controls.map(c => c.w)) : 0
  };
}"""

# THE EFFECTIVE BOX, per control: how far from its centre a tap still lands on
# it, walked in half-pixel steps through elementFromPoint. A band is a
# pseudo-element and has no box of its own, so this is the only measurement
# that reads it; getBoundingClientRect reads the pill. Disabled controls are
# skipped: they compute pointer-events: none and answer nothing at their own
# centre, which the hit-region note in styles.css records as a false alarm
# that has already cost one revert.
HIT_GEOMETRY = """() => {
  const bar = document.querySelector('.toolbar, .flip-tools');
  const hdr = document.querySelector('.header');
  const sel = '.tool-btn, .tool-open, .undo-btn, .t-btn, .icon-btn, .actions .btn';
  const pick = (root) => root ? [...root.querySelectorAll(sel)] : [];
  const els = [...pick(bar), ...pick(hdr)]
    .filter(e => e.offsetParent !== null && !e.disabled && e.getBoundingClientRect().width > 0);
  const own = (el, x, y) => { const t = document.elementFromPoint(x, y); return !!(t && (t === el || el.contains(t))); };
  return els.map(el => {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let up = 0, down = 0;
    while (up < 40 && own(el, cx, cy - up - 0.5)) up++;
    while (down < 40 && own(el, cx, cy + down + 0.5)) down++;
    return { id: el.id || el.className.toString().slice(0, 24),
             visH: +r.height.toFixed(1), hitH: up + down };
  });
}"""

PAGE_HIT_GEOMETRY = """
    () => {
      const sel = 'button, a[href], input, select, [role="button"]';
      const own = (el, x, y) => { const t = document.elementFromPoint(x, y);
                                  return !!(t && (t === el || el.contains(t))); };
      const out = [];
      for (const el of document.querySelectorAll(sel)) {
        if (!el.offsetParent || el.disabled) continue;
        el.scrollIntoView({block: 'center', inline: 'center'});
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || r.top < 0 || r.bottom > innerHeight) continue;
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        if (!own(el, cx, cy)) continue;
        let up = 0, down = 0;
        while (up < 30 && own(el, cx, cy - up - 0.5)) up++;
        while (down < 30 && own(el, cx, cy + down + 0.5)) down++;
        out.push({ id: el.id || el.className.toString().trim().slice(0, 26),
                   visH: Math.round(r.height), hitH: up + down });
      }
      return out; }"""

GALLERY_FIXTURE = """
    async () => {
      const r = await fetch('/api/skribls', { method: 'POST',
        headers: (window.skriblPostHeaders ? window.skriblPostHeaders()
                  : {'Content-Type': 'application/json'}),
        body: JSON.stringify({ title: 'Floor fixture', visibility: 'public',
          playbackMode: 'replay', canvasSize: {cssWidth: 800, cssHeight: 600},
          frames: [{ strokes: [{x:10,y:10,color:'#fff',size:6,t:0,start:true},
                               {x:400,y:300,color:'#fff',size:6,t:100}],
                     strokeGroups: [2], background: {color:'#101418'} }] }) });
      return r.status; }"""

SEED_POSTED = """
    () => { localStorage.setItem('skribl_posted_v1', '[]');
      window.SkriblPosted.add({id:'seedA', url:'/s/seedA', kind:'pad', pages:1,
        title:'A rather long title that will not fit', tok:'k', visibility:'public'});
      window.SkriblPosted.add({id:'seedB', url:'/s/seedB', kind:'flip', pages:6,
        title:'Unending J', tok:'k', visibility:'unlisted'}); }"""

ROW_STRIP = "() => { const r = document.querySelector('.posted-row-keyed');\n  if (!r) return null;\n  const acts = r.querySelector('.posted-actions');\n  const thumb = r.querySelector('.posted-thumb');\n  const btns = [...acts.querySelectorAll('button')];\n  const tops = new Set(btns.map(b => Math.round(b.getBoundingClientRect().top)));\n  return { thumbL: Math.round(thumb.getBoundingClientRect().left),\n           actsL: Math.round(btns[0].getBoundingClientRect().left),\n           lines: tops.size, n: btns.length,\n           right: Math.max(...btns.map(b => Math.round(b.getBoundingClientRect().right))),\n           words: btns.filter(b => { const l = b.querySelector('.posted-lbl');\n                     return l && getComputedStyle(l).display !== 'none'; }).length,\n           icons: btns.filter(b => { const i = b.querySelector('.posted-ico');\n                     return i && getComputedStyle(i).display !== 'none'; }).length,\n           named: btns.every(b => (b.getAttribute('aria-label') || '').length > 8) }; }"

# `del` WAS THE THIRD ITEM ON THE TITLE LINE and v311 took it off a posted
# row (the x that removed the entry without touching the Skribl). It is read
# back as a COUNT rather than a position, because the interesting question
# changed with it: not "did the x wrap?" but "is the x still gone?" A probe
# that simply stopped looking would have let the control return silently.
ROW_LINE = """
    () => { const row = document.querySelector('.posted-row-keyed');
      if (!row) return null;
      const y = (sel) => { const e = row.querySelector(sel);
                           return e ? Math.round(e.getBoundingClientRect().top) : null; };
      return { thumb: y('.posted-thumb'), main: y('.posted-main'),
               dels: row.querySelectorAll('.posted-del').length,
               acts: y('.posted-actions') }; }"""

HEADER_GEOMETRY = """() => {
  const h = document.querySelector('.header');
  const a = document.querySelector('.actions');
  if (!h || !a) return null;
  const cs = getComputedStyle(h);
  const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
  const brand = h.querySelector('.brand');
  const brandW = (brand && brand.offsetParent) ? brand.getBoundingClientRect().width : 0;
  return {
    height: +h.getBoundingClientRect().height.toFixed(1),
    available: +h.getBoundingClientRect().width.toFixed(1),
    // Intrinsic need, not the flexed width: .actions stretches to fill, which
    // hides overflow until a child clips. Sum what the children actually want.
    needed: +(brandW + a.scrollWidth + pad).toFixed(1),
    overflow: h.scrollWidth - h.clientWidth
  };
}"""


def measure(ctx, path, width, height=800, evaluate=GEOMETRY, prepare=None):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": width, "height": height})
    # A CLEAN EDITOR FOR EVERY MEASUREMENT. These pages share one context, so
    # the draft one case leaves behind is in storage for the next — and since
    # v294 the Pad APPLIES its draft at boot instead of offering it in a banner
    # (audit finding 5), which put the "review" state's page into a restored
    # take with no Record button to click. An init script runs before the page
    # scripts, so the slot is empty before the restore would read it.
    pg.add_init_script("try { localStorage.removeItem('skribl_autosave_v1'); } catch (e) {}")
    pg.goto(BASE + path, wait_until="load")
    if prepare:
        prepare(pg)
    pg.wait_for_timeout(120)          # let fitBrand() and any layout JS settle
    out = pg.evaluate(evaluate)
    pg.close()
    return out


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()

    # ------------------------------------------------------------ section 1
    print("\nLAYOUT 1 — the tool row is one line at every supported width")

    for surface, path in (("Pad", "/"), ("Flip", "/flip")):
        for w in FIT_WIDTHS:
            g = measure(ctx, path, w)
            if g is None:
                check(f"{surface} @{w}px — found a toolbar", False)
                continue
            check(f"{surface} @{w}px is one row",
                  g["height"] <= ONE_ROW_MAX_PX,
                  f"bar {g['height']}px tall, {len(g['controls'])} controls")
            check(f"{surface} @{w}px does not clip",
                  g["overflow"] <= 0,
                  f"scrollWidth exceeds clientWidth by {g['overflow']}px")

    # 320px is Display Zoom, an accessibility setting. It is not a design
    # target, but it must DEGRADE rather than clip: a taller bar is honest,
    # a clipped one hides controls with no cue that anything is missing.
    # The two surfaces degrade DIFFERENTLY, and both are legitimate. Pad wraps to
    # a taller bar. Flip sets `flex-wrap: nowrap; overflow-x: auto` below 560px
    # deliberately — its own comment says "keep the bottom tool row on ONE line
    # on phones (music was wrapping)" — so it scrolls instead.
    #
    # What matters is not WHICH, but that every control stays REACHABLE and the
    # page never spills sideways. An earlier version asserted `overflow <= 0`,
    # which forbade Flip's scroll row and would have failed a deliberate design
    # decision as though it were a defect.
    REACH_Q = (
        "() => {"
        "  const bar = document.querySelector('.toolbar, .flip-tools');"
        "  if (!bar) return null;"
        "  const cs = getComputedStyle(bar);"
        "  const over = bar.scrollWidth - bar.clientWidth;"
        "  const scrollable = cs.overflowX === 'auto' || cs.overflowX === 'scroll';"
        "  bar.scrollLeft = bar.scrollWidth;"
        "  const kids = [...bar.children].filter(e => e.offsetParent);"
        "  const last = kids[kids.length - 1].getBoundingClientRect();"
        "  const box = bar.getBoundingClientRect();"
        "  bar.scrollLeft = 0;"
        "  return { over, scrollable, lastReachable: last.right <= box.right + 2 };"
        "}"
    )
    for w in DEGRADE_WIDTHS:
        for surface, path in (("Pad", "/"), ("Flip", "/flip")):
            pg = ctx.new_page()
            pg.set_viewport_size({"width": w, "height": 800})
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(150)
            r = pg.evaluate(REACH_Q)
            pg.close()
            if r is None:
                check(f"{surface} @{w}px — found a toolbar", False)
                continue
            # Either it fits/wraps (no overflow), or it overflows into a scroller
            # whose end you can actually reach.
            reachable = r["over"] <= 0 or (r["scrollable"] and r["lastReachable"])
            how = "wraps" if r["over"] <= 0 else "scrolls"
            check(f"{surface} @{w}px keeps every control reachable ({how})",
                  reachable,
                  "overflowing without a scroller hides controls with no cue")
            # The whole point of the safety net: nothing spills off the page.
            pg = ctx.new_page()
            pg.set_viewport_size({"width": w, "height": 800})
            pg.goto(BASE + path, wait_until="load")
            pg.wait_for_timeout(120)
            spill = pg.evaluate("() => document.documentElement.scrollWidth "
                                "- document.documentElement.clientWidth")
            pg.close()
            check(f"{surface} @{w}px does not spill horizontally",
                  spill <= 0, f"page is {spill}px wider than the viewport")

    # ------------------------------------------------------------ section 2
    print("\nLAYOUT 2 — the header fits in every state")

    def draw_a_stroke(pg):
        """Put the editor into a state that has content, the way a user would."""
        # '#canvas, #pad' — Pad's drawing surface is #canvas and Flip's is #pad.
        # This read #pad only, and section 2 measures Pad, so every header state
        # that needed content on the canvas timed out waiting for an element that
        # is not on that page. Same root cause as the GEOMETRY selector above: a
        # suite written against one surface and never executed against either.
        box = pg.locator("#canvas, #pad").first.bounding_box()
        pg.mouse.move(box["x"] + 40, box["y"] + 40)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 120, box["y"] + 90, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(150)

    def stop_the_take(pg):
        draw_a_stroke(pg)
        pg.click("#recordBtn")            # ends the take; Play/Post/duration appear
        pg.wait_for_timeout(200)

    STATES = (("idle", None), ("recording", draw_a_stroke), ("review", stop_the_take))

    for state, prepare in STATES:
        for w in (375, 390, 393, 430):
            h = measure(ctx, "/", w, evaluate=HEADER_GEOMETRY, prepare=prepare)
            if h is None:
                check(f"header @{w}px in {state} — found a header", False)
                continue
            slack = h["available"] - h["needed"]
            check(f"header @{w}px fits in {state}",
                  slack >= 0,
                  f"needs {h['needed']:.0f}px, has {h['available']:.0f}px "
                  f"({slack:+.0f}px)")
            # A header that fits by wrapping is not a header that fits. The
            # v213 report was a wrapped record pill, and height is how that
            # shows up in a measurement.
            check(f"header @{w}px in {state} stays one row",
                  h["height"] <= ONE_ROW_MAX_PX,
                  f"{h['height']}px tall")

    # ------------------------------------------------------------ section 3
    print("\nLAYOUT 3 — touch targets hold the decided floor")

    for surface, path in (("Pad", "/"), ("Flip", "/flip")):
        for w in (375, 393, 430):
            g = measure(ctx, path, w)
            if not g or not g["controls"]:
                check(f"{surface} @{w}px — found controls to measure", False)
                continue
            worst = min(g["controls"], key=lambda c: c["w"])
            check(f"{surface} @{w}px every control >= {MIN_TOUCH_PX}px",
                  g["smallest"] >= MIN_TOUCH_PX,
                  f"smallest is {worst['id'] or '(unnamed)'} at {worst['w']}px")

    # THE BOX A FINGER GETS (SK-AUD-005). Every bar and header control, at the
    # design widths AND the 320 safety net: a tap HIT_TOUCH_PX tall, centred on
    # the control, lands on it. Measured on the page as it is used -- after a
    # stroke, so Undo is enabled and the Post pill is live -- because the
    # controls that only wake up then are exactly the ones a fresh page hides.
    # Red on the tree that gave the header pills no band (Post answered 37px).
    for surface, path, canvas in (("Pad", "/", "#canvas"), ("Flip", "/flip", "#pad")):
        for w in sorted(set(DEGRADE_WIDTHS + [360, 375, 393, 430])):
            page = ctx.new_page()
            page.set_viewport_size({"width": w, "height": 900})
            # The same clean slate measure() gives itself: the stroke below
            # leaves a draft, and a restored draft is a finished take with a
            # locked canvas, on which the next width's stroke would draw nothing.
            page.add_init_script("try { localStorage.removeItem('skribl_autosave_v1'); } catch (e) {}")
            browsing.goto(page, BASE, path)
            box = page.locator(canvas).bounding_box()
            page.mouse.move(box["x"] + 50, box["y"] + 50)
            page.mouse.down()
            page.mouse.move(box["x"] + 120, box["y"] + 90, steps=6)
            page.mouse.up()
            page.wait_for_timeout(250)
            hits = page.evaluate(HIT_GEOMETRY)
            page.close()
            if not hits:
                check(f"{surface} @{w}px — found live controls to hit-test", False)
                continue
            floor = HIT_TOUCH_PX if w >= 360 else HIT_TOUCH_NARROW_PX
            short = [h for h in hits if h["hitH"] < floor]
            check(f"{surface} @{w}px every live bar and header control answers a tap {floor}px tall",
                  not short,
                  ", ".join(f"{h['id']} {h['hitH']}px (pill {h['visH']}px)" for h in short[:4])
                  or f"{len(hits)} controls, shortest {min(h['hitH'] for h in hits)}px")

    # THE TWO PAGES THIS SECTION NEVER WALKED (from an iPhone).
    #
    # Everything above measures Pad and Flip. /library and /gallery were never
    # in it, and neither had ever been measured against the floors this file
    # decides. What was there when they finally were:
    #
    #   /library  the row × answered 23x23 -- the smallest control in the app,
    #             directly above Delete. The × forgets a row; Delete takes the
    #             Skribl down for everyone.
    #             the five action buttons, 33 (an explicit min-height: 32px)
    #             the row's own title link, 41
    #   /gallery  the in-post player's loop pill, 31 -- and that control ships
    #             in every host embed, not just here
    #
    # None of it width-dependent: identical at 375, 390 and 430. A gate that
    # covers two of four pages is not a policy, it is a habit that stopped.
    #
    # CALIBRATED PER COMPONENT, seven of them, each reverted on its own against
    # this block. Every one went red on the row named, and no row is carried by
    # another component's fix:
    #
    #   the × loses its pill and band        tap row     posted-del 23px (pill 22)
    #     -- v311 note: this case no longer reproduces on /library, because
    #     the posted row's × is gone and SEED_POSTED seeds no local save.
    #     The rule it calibrated is unchanged and the other six still run.
    #   action buttons back to min-height 32 SEE row     four at 32px
    #   the chips lose their 34px minimum    SEE row     three at 28px
    #   the strip loses its ::before band    tap row     four at 35px (pill 34)
    #   the row goes back to flex-wrap       one-line    tops [378, 389, 495]
    #   the transport pills lose their band  tap row     loop 31px (pill 30)
    #   the fixture, on an empty database    tile row    0 players -- and the two
    #                                                    floor rows stayed GREEN
    #                                                    on 6 controls, which is
    #                                                    the vacuous pass the
    #                                                    tile row exists to catch
    print("\nLAYOUT 3b — the pages the floor never reached")

    # A GALLERY WITH NO TILES MEASURES THE HEADER AND PASSES. The first run of
    # this block found six controls on /gallery -- the brand, two tabs, search
    # and Retry -- because the harness database has no public posts, so the
    # loop pill this section exists to catch was not on the page at all. One
    # public post is the fixture, and the tile count is asserted before the
    # floor is, so "0 under 44" can never again mean "nothing was there".
    _seedpg = ctx.new_page()
    browsing.goto(_seedpg, BASE, "/skribl-pad")
    _posted = _seedpg.evaluate(GALLERY_FIXTURE)
    _seedpg.close()
    check("gallery fixture: a public Skribl exists to draw tiles from",
          _posted in (200, 201),
          f"POST /api/skribls answered {_posted} — without a tile the rows "
          f"below measure the header and prove nothing")

    for label, path, seed in (("library", "/library", SEED_POSTED),
                              ("gallery", "/gallery", None)):
        for w in (360, 390, 430):
            page = ctx.new_page()
            page.set_viewport_size({"width": w, "height": 900})
            browsing.goto(page, BASE, path)
            if seed:
                page.evaluate(seed)
                page.reload(wait_until="load")
            page.wait_for_timeout(1200)
            hits = page.evaluate(PAGE_HIT_GEOMETRY)
            page_tiles = page.evaluate(
                "() => document.querySelectorAll('.skribl-inline').length")
            rowy = page.evaluate(ROW_LINE) if seed else None
            page.close()
            if not hits:
                check(f"{label} @{w}px — found controls to hit-test", False,
                      "an empty page measures nothing and passes everything")
                continue
            if label == "gallery":
                _tiles = page_tiles
                check(f"gallery @{w}px — tiles are on the page to measure",
                      _tiles > 0,
                      f"{_tiles} in-post players; the loop pill only exists on "
                      f"a tile, so an empty gallery cannot fail the floor")
            short = [h for h in hits if h["hitH"] < HIT_TOUCH_PX]
            check(f"{label} @{w}px every control answers a tap {HIT_TOUCH_PX}px tall",
                  not short,
                  ", ".join(f"{h['id']} {h['hitH']}px (pill {h['visH']}px)"
                            for h in short[:4])
                  or f"{len(hits)} controls, shortest {min(h['hitH'] for h in hits)}px")

            # AND THE VISIBLE FLOOR, WHICH THE HIT FLOOR DOES NOT IMPLY. The
            # band is invisible, so a page can answer 44 to a finger with a
            # 22px pill -- a target you cannot see to aim at, on a list whose
            # neighbours delete things. Both of the numbers this section
            # found were hiding behind a band that was already there: the
            # library's action buttons said `min-height: 32px`, under even
            # the visible floor, and its filter chips measured 28 with a 44px
            # ::before over them since the day they were written.
            #
            # THE EXEMPTION IS NAMED, NOT THE PAGE. The in-post player's
            # transport pills stay 30px on purpose: a feed tile is small and
            # two 44px slabs over somebody's drawing is a different product,
            # so there the band IS the fix. Exempting /gallery wholesale --
            # the first draft -- would have bought that one decision at the
            # price of never measuring the other nine controls on the page.
            EXEMPT_VIS = ("skribl-inline-loop", "skribl-inline-mute")
            small = [h for h in hits
                     if h["visH"] < MIN_TOUCH_PX
                     and not any(c in h["id"] for c in EXEMPT_VIS)]
            check(f"{label} @{w}px ...and every pill is {MIN_TOUCH_PX}px you can SEE",
                  not small,
                  ", ".join(f"{h['id']} {h['visH']}px" for h in small[:4])
                  or f"{len(hits)} controls, smallest countable "
                     f"{min([h['visH'] for h in hits if not any(c in h['id'] for c in EXEMPT_VIS)] or [0])}px")

            # THE TITLE LINE IS STRUCTURAL, which it was not until the row
            # became a grid. `.posted-sub` is `white-space: nowrap`, so
            # `.posted-main`'s flex base was the whole meta string and a
            # wrapping flex line pushes rather than squeezes -- so which item
            # fell off depended on how long THAT ROW's meta happened to be:
            # a long one dropped the text block under the thumbnail, a shorter
            # one dropped the × alone to the left, a shorter one still was
            # fine. One page, three shapes, row by row.
            #
            # TWO ITEMS ON THAT LINE NOW, not three. The grid is unchanged and
            # still the reason the text block cannot drop: what went is the
            # third item, and the row below says so rather than leaving its
            # absence to be inferred from a probe that no longer looks.
            if rowy and rowy.get("thumb") is not None:
                line = [rowy["thumb"], rowy["main"]]
                check(f"library @{w}px the thumb and the title share one line",
                      max(line) - min(line) < 40,
                      f"tops {line} — a spread this large means one of them "
                      f"wrapped, which is the defect the grid replaced")
                check(f"library @{w}px ...and the actions are BELOW it",
                      rowy["acts"] > max(line),
                      f"actions top {rowy['acts']} against title line {max(line)}")
                check(f"library @{w}px ...and a posted row carries no × at all",
                      rowy["dels"] == 0,
                      f"{rowy['dels']} .posted-del on a keyed row — v311 took "
                      f"the remove-from-list × out; a local save's × stays "
                      f"and this fixture posts, so any hit here is the "
                      f"control coming back")

    # THE ROW'S ACTIONS ON A PHONE ("there is no reason the buttons
    # shouldn't be left justified under the thumbnail. it forces them to be in
    # two rows when you could do one... use icons instead of words on phones").
    #
    # They were indented 94px past the thumbnail on this page and 52px in the
    # drawer, which is what spent the width that forced the wrap. Left-aligned
    # with the row's own edge and reduced to icons, five of them are 199px, so
    # they fit one line at 360 with room over.
    #
    # THE WORD IS STILL THE ACCESSIBLE NAME for a button without an explicit
    # aria-label, so it is HIDDEN rather than removed -- and every one of these
    # carries an aria-label anyway, asserted below, because an icon-only
    # control whose name is a hidden span is one refactor from being unnamed.
    for _w in (360, 390):
        _page = ctx.new_page()
        _page.set_viewport_size({"width": _w, "height": 900})
        browsing.goto(_page, BASE, "/library")
        _page.evaluate(SEED_POSTED)
        _page.reload(wait_until="load")
        _page.wait_for_timeout(1400)
        _strip = _page.evaluate(ROW_STRIP)
        _page.close()
        if not _strip:
            check(f"library @{_w}px — found a keyed row to measure", False)
            continue
        # THE FIRST BUTTON'S edge, not the strip's. A mutation that put the
        # 94px indent back left this green: `padding-left` moves the content
        # and not the element's own box, so the strip's left never moved and
        # the check was reading a number the defect cannot change.
        check(f"library @{_w}px the actions start at the thumbnail's own left edge",
              _strip["actsL"] == _strip["thumbL"],
              f"first button at {_strip['actsL']}, thumb at {_strip['thumbL']} — "
              f"the indent is what the owner asked to lose")
        check(f"library @{_w}px ...and all {_strip['n']} of them fit ONE line",
              _strip["lines"] == 1 and _strip["right"] <= _w,
              f"{_strip['lines']} line(s), rightmost edge {_strip['right']} of {_w}")
        check(f"library @{_w}px ...as icons, with the words put away",
              _strip["icons"] == _strip["n"] and _strip["words"] == 0,
              f"{_strip['icons']} icons and {_strip['words']} words showing on "
              f"{_strip['n']} buttons")
        check(f"library @{_w}px ...each still saying what it does, to a reader",
              _strip["named"],
              "an icon whose only name is a hidden span is one refactor from "
              "being an unnamed button")
    # AND THE WORDS COME BACK on a screen with room for them, which is the
    # other half: this is a compact-tier treatment, not a redesign.
    _wide = ctx.new_page()
    _wide.set_viewport_size({"width": 1100, "height": 900})
    browsing.goto(_wide, BASE, "/library")
    _wide.evaluate(SEED_POSTED)
    _wide.reload(wait_until="load")
    _wide.wait_for_timeout(1400)
    _ws = _wide.evaluate(ROW_STRIP)
    _wide.close()
    check("library @1100px the words are back and the icons are away",
          bool(_ws) and _ws["words"] == _ws["n"] and _ws["icons"] == 0,
          f"{_ws} — a desktop row reading as five unlabelled glyphs is the "
          f"opposite trade")

    # ------------------------------------------------------------ section 4
    print("\nLAYOUT 4 — leaving Pad cannot silently discard work")

    # TWO THINGS IN THIS SECTION WERE WRITTEN AGAINST A TREE THAT NEVER SHIPPED,
    # and both only surfaced when the suite was first executed. Read before
    # editing.
    #
    # 1. #flipBtn is no longer in the header. v219 moved Flip Mode into the •••
    #    menu with a subtitle, so a bare click times out waiting for an element
    #    that is not visible. The menu has to be opened first — which is also
    #    what a user does, so the test got MORE faithful, not less.
    #
    # 2. The guard's predicate has now changed TWICE, and this section pinned
    #    the middle version. History, so nobody re-pins a superseded contract:
    #      v1: recording || hasContent — any drawing at all; rejected because a
    #          confirm that is usually wrong is dismissed unread.
    #      v2: photoBg || currentAudioBuffer — right while media bytes could
    #          not be stored (localStorage held strokes only).
    #      v3 (current, editor_draft.js): media bytes persist to IndexedDB, so
    #          attached media with WORKING storage is not at risk and must
    #          navigate freely; the guard now fires on MEASURED durability —
    #          it flushes synchronously and confirms only when the flush could
    #          not make the draft durable (external review #19). This section
    #          asserted v2 and failed the moment v3 landed, correctly.
    #
    # So: strokes alone navigate freely, DURABLE media navigates freely, and a
    # BROKEN store confirms — with focus on the safe choice, and both exits
    # honoured. Both directions still asserted: a guard that never fires and a
    # guard that always fires fail this section identically otherwise.
    def open_flip_entry(pg):
        pg.click("#menuBtn")
        pg.wait_for_timeout(250)
        pg.click("#flipBtn")
        pg.wait_for_timeout(300)

    # A 1x1 PNG is enough: the guard reads whether photoBg is set, not what it is.
    _PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    _png_path = pathlib.Path(tempfile.gettempdir()) / "skribl_layout_probe.png"
    _png_path.write_bytes(_PNG)

    # Empty canvas: the guard must NOT fire. A dialog that appears when there is
    # nothing to lose teaches people to dismiss it unread.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    open_flip_entry(pg)
    check("empty canvas — Flip navigates with no confirm",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # Strokes only: still no confirm. Pad's autosave keeps strokes, so there is
    # nothing to lose and the guard is correct to stay silent.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    open_flip_entry(pg)
    check("strokes but no media — Flip still navigates (autosave keeps strokes)",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # With media attached and storage WORKING: the bytes are in IndexedDB, the
    # draft is durable, and the guard staying silent is the point — a confirm
    # here would be v2's mistake wearing v3's clothes.
    pg = ctx.new_page()
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    pg.set_input_files("#photoInput", str(_png_path))
    pg.wait_for_timeout(900)
    open_flip_entry(pg)
    check("attached media, working storage — Flip navigates (bytes are durable)",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # With storage BROKEN: the flush cannot make the draft durable, and this —
    # not media presence — is when work is genuinely lost. The drawing itself
    # is the thing at risk, which is exactly the case v2 waved through.
    pg = ctx.new_page()
    pg.add_init_script(
        "const _si = Storage.prototype.setItem;"
        "Storage.prototype.setItem = function (k, v) {"
        "  if (k === 'skribl_autosave_v1') { const e = new Error('quota');"
        "  e.name = 'QuotaExceededError'; throw e; }"
        "  return _si.apply(this, arguments); };")
    pg.goto(BASE + "/", wait_until="load")
    draw_a_stroke(pg)
    pg.wait_for_timeout(1500)
    before = pg.url
    open_flip_entry(pg)
    check("broken storage — Flip does not navigate",
          pg.url == before,
          f"navigated to {pg.url} — an un-durable drawing was discarded")
    sheet = pg.locator("#leaveSheet")
    check("with unposted work — a confirm is shown",
          sheet.count() > 0 and sheet.is_visible())
    # The safe choice takes focus, so a stray Enter or a mis-tap keeps the work.
    focused = pg.evaluate("() => document.activeElement && document.activeElement.id")
    check("the confirm focuses the safe choice", focused == "leaveCancel",
          f"focus is on {focused!r}")

    # Cancel keeps you here.
    pg.click("#leaveCancel")
    pg.wait_for_timeout(200)
    check("'Keep drawing' stays on Pad", pg.url == before, f"landed on {pg.url}")

    # Confirm lets you out — a guard that traps you is its own bug.
    # Via the ••• menu again: the guard closes that menu when it fires, so the
    # second approach starts from the same closed state as the first.
    open_flip_entry(pg)
    pg.click("#leaveGo")
    pg.wait_for_timeout(400)
    check("'Leave' navigates to Flip", "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()

    # Both surfaces — but NOT the same behaviour, and this is the one place in
    # the file where parity is the wrong instinct.
    #
    # The rule of thumb is sound: most v213 bugs were one surface having a fix
    # the other lacked. It does not apply here, and the ORIGINAL detail string
    # below said so while the assertion contradicted it — it read "the guard is
    # Pad-only", which is exactly right and was written as a failure message.
    #
    # Flip had no leave-guard DELIBERATELY: it persisted pages, music and the
    # background image, so nothing was at risk when you left. That held while
    # the bytes went to localStorage; since the spill model they go to
    # IndexedDB in a write that can die with the page, and v294 (finding 6 of
    # the media-restore audit) gave Flip the Pad's guard for exactly that case
    # — section 4b below. What this pin still holds, and must: with the store
    # WORKING, Flip navigates FREELY. A confirm here with durable media is the
    # false alarm this comment always warned about.
    pg = ctx.new_page()
    pg.goto(BASE + "/flip", wait_until="load")
    # Match on the accessible name, not the href literal: the href is now
    # url_for-derived (P0-1) and renders as /skribl-pad at the root and as
    # <prefix>/skribl-pad under a mount — a[href='/'] matched neither.
    back = pg.locator('#padBtn, .pad-btn, a[aria-label="Back to Skribl Pad"]').first
    if back.count() == 0:
        check("Flip has a link back to Pad to guard", False,
              "no back-link found — update this selector if it was renamed")
    else:
        box = pg.locator("#flipCanvas, canvas").first.bounding_box()
        if box:
            pg.mouse.move(box["x"] + 40, box["y"] + 40)
            pg.mouse.down(); pg.mouse.move(box["x"] + 110, box["y"] + 80, steps=6); pg.mouse.up()
            pg.wait_for_timeout(150)
        before = pg.url
        # The link is a row in the ⋯ menu (the mirror of the Pad's Flip
        # Mode row), opened AFTER the stroke — a press on the canvas closes it.
        pg.click("#moreBtn"); pg.wait_for_timeout(400)
        back.click()
        pg.wait_for_timeout(300)
        check("Flip — leaving navigates freely; Flip persists its work, so a confirm would be a false alarm",
              "/flip" not in pg.url,
              f"stayed on {pg.url} — a guard appeared on the surface that does not need one")
    pg.close()

    # ------------------------------------------------------------ section 4b
    print("\nLAYOUT 4b — the guard waits for a write in flight, and Flip guards its own media (v294 audit, PR 4)")
    # The v294 media-restore audit, finding 6. The Pad's guard read "not
    # durable" while a store write was merely IN FLIGHT, so the sheet opened
    # for up to twelve seconds after every attach on a phone — a false alarm
    # on the common path. And the note above this section is out of date:
    # since the spill model, Flip's media bytes go to IndexedDB in a write
    # that "can die with the page", so with the store broken they are exactly
    # the work at risk. The rule is the same on both editors now: a write in
    # flight gets a moment to land; media whose bytes cannot be stored gets
    # the sheet; durable media navigates freely (the pin above still holds).
    import math as _m, struct as _st, wave as _wv
    _wav = pathlib.Path(tempfile.gettempdir()) / "skribl_layout_guard.wav"
    with _wv.open(str(_wav), "wb") as _w:
        _w.setnchannels(2); _w.setsampwidth(2); _w.setframerate(44100)
        _buf = bytearray()
        for _i in range(30 * 44100):
            _v = int(12000 * _m.sin(2 * _m.pi * 220 * _i / 44100)); _buf += _st.pack("<hh", _v, _v)
        _w.writeframes(bytes(_buf))
    pg = ctx.new_page(); pg.goto(BASE + "/", wait_until="load"); draw_a_stroke(pg)
    pg.evaluate("() => { const orig = SkriblDraftStore.put.bind(SkriblDraftStore); SkriblDraftStore.put = (k, v) => new Promise(r => setTimeout(() => r(orig(k, v)), 800)); }")
    pg.set_input_files("#musicInput", str(_wav)); pg.wait_for_timeout(300)
    open_flip_entry(pg); pg.wait_for_timeout(2500)
    check("Pad: a write still landing when Flip is tapped does not raise the sheet — it lands, and Flip opens",
          "/flip" in pg.url, f"landed on {pg.url}")
    pg.close()
    pg = ctx.new_page(); pg.goto(BASE + "/", wait_until="load"); draw_a_stroke(pg)
    pg.evaluate("() => { SkriblDraftStore.put = (k, v) => new Promise(() => {}); }")
    pg.set_input_files("#musicInput", str(_wav)); pg.wait_for_timeout(300)
    before = pg.url; open_flip_entry(pg); pg.wait_for_timeout(2500)
    check("Pad: a write that never settles is at risk, and the sheet says so",
          pg.url == before and pg.locator("#leaveSheet").is_visible(), f"{pg.url}")
    pg.close()
    pg = ctx.new_page()
    pg.add_init_script("Object.defineProperty(window, 'indexedDB', { value: undefined, configurable: true });")
    pg.goto(BASE + "/flip", wait_until="load"); pg.wait_for_timeout(600)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    box = pg.locator("#pad").bounding_box()
    pg.mouse.move(box["x"] + 40, box["y"] + 40); pg.mouse.down(); pg.mouse.move(box["x"] + 110, box["y"] + 80, steps=6); pg.mouse.up()
    pg.set_input_files("#musicInput", str(_wav)); pg.wait_for_timeout(4000)
    before = pg.url
    pg.click("#moreBtn"); pg.wait_for_timeout(400); pg.click("#padBtn"); pg.wait_for_timeout(600)
    fl_sheet = pg.locator("#leaveSheet")
    check("Flip: media the store cannot hold — the Skribl Pad row confirms before leaving",
          pg.url == before and fl_sheet.count() > 0 and fl_sheet.is_visible(), f"landed on {pg.url}; sheet={fl_sheet.count()}")
    if pg.url == before and fl_sheet.count() > 0:
        check("Flip: the confirm focuses the safe choice",
              pg.evaluate("() => document.activeElement && document.activeElement.id") == "leaveCancel")
        pg.click("#leaveCancel"); pg.wait_for_timeout(200)
        check("Flip: 'Keep drawing' stays on Flip", pg.url == before, pg.url)
        pg.click("#moreBtn"); pg.wait_for_timeout(400); pg.click("#padBtn"); pg.wait_for_timeout(400)
        pg.click("#leaveGo"); pg.wait_for_timeout(600)
        check("Flip: 'Leave' navigates to the Pad", "/flip" not in pg.url, pg.url)
    pg.close()

    # ------------------------------------------------------------ section 5
    print("\nLAYOUT 5 — the move-bar readout does not spill its pill")
    # THIS SECTION EXISTS BECAUSE THE FILE'S OWN RULE WAS NOT ENOUGH. Raising
    # .mb-offset from 12px to 16px (the iOS zoom threshold — see the IOS ZOOM
    # section in verify_ux.py) made "-1000, -1000" WRAP to a second line inside
    # a pill that states `height: 30px`. The second line painted straight over
    # the scope pill beside it.
    #
    # Every geometry probe in this file would have passed it. The pill's BOX is
    # unchanged by the wrap, so scrollWidth against clientWidth reports zero,
    # the bar's height is unchanged, and Done stays reachable. Section 1's
    # REACH_Q returned "ok" at all five widths while the bar looked broken.
    #
    # So the measurement here is scrollHeight against the box's own height —
    # the content, not the container — and the offset is written through
    # applyMoveOffset(), the function that ships. Setting textContent directly
    # did NOT reproduce the wrap, which is worth knowing: the reproduction has
    # to go through the app's path.
    #
    # "-1000, -1000" is the pessimistic end of what applyMoveOffset can write
    # (it rounds dx/dy to integers and does not clamp). "-320, -240" is a
    # full-canvas drag on a phone, and it wrapped too, at 320 and 360.
    SPILL_Q = """([dx, dy]) => {
      moveDx = dx; moveDy = dy; applyMoveOffset();
      const off = document.getElementById('mbOffset');
      const nxt = document.querySelector('.mb-scope');
      if (!off || !nxt) return null;
      const cs = getComputedStyle(off);
      const b = off.getBoundingClientRect();
      // A single nowrap line fits the stated height; a wrapped one does not.
      // scrollHeight sees the content even when the box is unmoved.
      return { txt: off.textContent,
               boxH: +b.height.toFixed(1),
               contentH: off.scrollHeight,
               clips: cs.overflow === 'hidden',
               wraps: cs.whiteSpace === 'nowrap' ? false : true };
    }"""
    for w in (320, 360, 375, 390, 430):
        pg = ctx.new_page()
        pg.set_viewport_size({"width": w, "height": 800})
        browsing.goto(pg, BASE, "/flip")
        # A stroke to move, then the mode that shows the bar. setTool is the
        # same entry verify_move.py uses, for the same reason: the control has
        # moved between the page bar and the tool shelf once already.
        box = pg.locator("#pad").bounding_box()
        pg.mouse.move(box["x"] + 60, box["y"] + 60)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 160, box["y"] + 110, steps=8)
        pg.mouse.up()
        pg.evaluate("() => setTool('artmove')")
        pg.wait_for_timeout(200)
        for dx, dy in ((-320, -240), (-1000, -1000)):
            r = pg.evaluate(SPILL_Q, [dx, dy])
            if r is None:
                check(f"@{w}px — found the move bar readout", False)
                continue
            check(f"@{w}px the readout \"{r['txt']}\" stays on one line",
                  r["contentH"] <= r["boxH"] + 1,
                  f"content is {r['contentH']}px in a {r['boxH']}px pill — it "
                  "wrapped, and a wrapped line paints over the control beside it")
        # The two properties that make the above true, pinned by name so a
        # future edit that drops either fails HERE rather than in a screenshot.
        r = pg.evaluate(SPILL_Q, [-1000, -1000])
        check(f"@{w}px the readout declares nowrap", not r["wraps"],
              "without it a value too wide for the pill wraps instead of clipping")
        check(f"@{w}px the readout clips rather than overflowing", r["clips"],
              "overflow:visible let the text paint outside the pill by 4.9px "
              "at 320 and 4.7px at 360")
        pg.close()

    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# The failure has to travel through the channel run_harness.sh actually reads.
# Eight suites printed their failures and exited 0, and the runner recorded them
# as ok. Printing it is not reporting it.
sys.exit(1 if bad else 0)
