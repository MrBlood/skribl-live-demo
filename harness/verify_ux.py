"""Honest export labels, and an undoable "Clear all".

1. FORMAT DISCLOSURE. The Pad labels its export button with the container the
   browser will actually produce ("Video (MP4)" / "Video (WebM)"). Flip must
   mirror exportVideo()'s real decision the same way, including the subtle case
   where music is present but AAC is unavailable and the MP4 path deliberately
   bails rather than ship a silent video. Saying "Video" and then handing over
   WebM on any browser without WebCodecs H.264 is the defect.

2. UNDOABLE CLEAR ALL. "Clear all" wipes strokes, music, photo and background.
   Calling clearAutosave() with it takes the recovery copy too, so the two-tap
   arm guards the accidental tap and nothing undoes a deliberate one. It
   snapshots through serializeSkribl() and restores through loadSkribl(), the
   same pair the draft and autosave paths use, so media comes back with no
   parallel restore logic.

Note this sandbox's Chromium has VideoEncoder but no avc1, so the expected format
here is WebM on both surfaces -- which is exactly the case a bare "Video" label
gets wrong, and therefore the useful one to pin.
"""
from playwright.sync_api import sync_playwright
import browsing
import waits
import os


def ux_open(pg, op):
    """Click a Flip opener, or reach a Pad drawer through the Pad's bar: "@pad:draw"
    is the pen tapped again, "@pad:photo" / "@pad:music" Media and its tab."""
    if op.startswith("@pad:"): browsing.pad_drawer(pg, op[5:], settle=0)
    else: pg.click(op)


def ux_close(pg, op):
    if op.startswith("@pad:"): browsing.pad_drawer_close(pg, settle=0)
    else: pg.click(op)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
import pathlib
from assertions import make_check
import source
ROOT = pathlib.Path(__file__).resolve().parents[1]

results = []
check = make_check(results)


def draw(page, sel, x0, y0, n=22):
    box = page.locator(sel).bounding_box()
    page.mouse.move(box["x"] + x0, box["y"] + y0)
    page.mouse.down()
    for i in range(n):
        page.mouse.move(box["x"] + x0 + i * 7, box["y"] + y0 + (i % 5) * 5)
    page.mouse.up()
    page.wait_for_timeout(150)


with sync_playwright() as p:
    br = waits.instrument(p.chromium.launch())
    ctx = br.new_context(viewport={"width": 1280, "height": 900})

    print("\nFLIP — the export sheet now names the format (was the caveat)")
    flip = ctx.new_page()
    flip_errors = []
    flip.on("pageerror", lambda e: flip_errors.append(str(e)))
    browsing.goto(flip, BASE, "/flip")

    # Single page: video is gated, and the label must not promise a format.
    flip.evaluate("() => openExportSheet()")
    flip.wait_for_timeout(500)
    single = flip.evaluate("""() => ({
        disabled: document.getElementById('exportVideo').disabled,
        title: document.querySelector('#exportVideo .export-opt-title').textContent,
        desc: document.getElementById('exportVideoDesc').textContent })""")
    check("one page: video disabled", single["disabled"], str(single))
    check("one page: title stays plain 'Video'", single["title"].strip() == "Video", single["title"])
    check("one page: desc explains why", "page" in single["desc"].lower(), single["desc"])

    # Multi-page: the label must name a real container.
    flip.evaluate("() => closeExportSheet()")
    for i in range(3):
        flip.evaluate("() => addFrame()")
        draw(flip, "#pad", 90 + i * 15, 100)
    flip.evaluate("() => openExportSheet()")
    flip.wait_for_timeout(1200)
    multi = flip.evaluate("""() => ({
        title: document.querySelector('#exportVideo .export-opt-title').textContent,
        desc: document.getElementById('exportVideoDesc').textContent })""")
    check("Flip labels the button with a container", multi["title"].strip() in ("Video (MP4)", "Video (WebM)"),
          multi["title"])
    # The container lives in the TITLE only — the description carries the
    # tradeoff, and repeating "WebM" in both lines said it twice.
    check("Flip's description does NOT repeat the container",
          "MP4" not in multi["desc"] and "WebM" not in multi["desc"], multi["desc"])

    # The label must agree with what this browser can really do.
    truth = flip.evaluate("""async () => {
        if (typeof VideoEncoder === 'undefined') return 'WebM';
        for (const c of ['avc1.640028','avc1.4d0028','avc1.42001f','avc1.42e01e']) {
            try { const r = await VideoEncoder.isConfigSupported(
                {codec:c,width:640,height:460,bitrate:6000000,framerate:30});
                if (r && r.supported) return 'MP4'; } catch (e) {}
        }
        return 'WebM'; }""")
    check("the label matches this browser's real capability",
          truth in multi["title"], f"probe says {truth}, label says {multi['title']!r}")
    check("no Flip page errors", not flip_errors, "; ".join(flip_errors[:2]))

    print("\nPAD — same treatment, including the WebM case it used to skip")
    pad = ctx.new_page()
    pad_errors = []
    pad.on("pageerror", lambda e: pad_errors.append(str(e)))
    browsing.goto(pad, BASE, "/")
    draw(pad, "#canvas", 80, 80, n=26)
    pad.evaluate("() => { document.getElementById('exportItem').click(); }")
    pad.wait_for_timeout(1400)
    padlbl = pad.evaluate("""() => ({
        title: document.querySelector('#exportVideo .export-opt-title').textContent,
        desc: document.getElementById('exportVideoDesc').textContent })""")
    check("Pad labels the container", padlbl["title"].strip() in ("Video (MP4)", "Video (WebM)"),
          padlbl["title"])
    # Same rule as Flip — the title names the container once, the
    # description keeps to the tradeoff.
    check("Pad's desc does NOT repeat the container",
          "MP4" not in padlbl["desc"] and "WebM" not in padlbl["desc"], padlbl["desc"])
    check("both surfaces agree on the format",
          padlbl["title"].strip() == multi["title"].strip(),
          f"pad {padlbl['title']!r} vs flip {multi['title']!r}")

    print("\nCLEAR ALL — now undoable (it wiped media AND the autosave)")
    pad.evaluate("""() => { const o=document.getElementById('exportOverlay');
                            if(o){o.classList.remove('open'); o.hidden=true;} }""")
    pad.wait_for_timeout(300)
    before = pad.evaluate("() => strokes.length")
    check("there is a drawing to lose", before > 0, f"{before} strokes")

    # Drawing auto-starts recording, and updateClearVisibility() disables the menu
    # item while recording — worth pinning, since a disabled button silently
    # swallows clicks and made this test look broken rather than blocked.
    check("Clear all is disabled mid-recording",
          pad.evaluate("() => recording && document.getElementById('clearMenuItem').disabled"))
    pad.evaluate("() => { document.getElementById('recordBtn').click(); }")   # stop recording
    pad.wait_for_timeout(700)
    check("stopping the recording re-enables Clear all",
          pad.evaluate("() => !recording && !document.getElementById('clearMenuItem').disabled"),
          f"recording={pad.evaluate('() => recording')}")

    # NEW SKRIBL ASKS ON ITS OWN PAGE (after v323): New opens the page with the
    # shape, which is the question the two-tap arm used to ask; Start clears.
    pad.evaluate("() => { document.getElementById('menuBtn').click(); }")
    pad.wait_for_timeout(400)
    pad.evaluate("() => { document.getElementById('menuNewTile').click(); }")
    pad.wait_for_timeout(300)
    asked = pad.evaluate("() => SkriblMenuPages.current()")
    check("New asks first: it opens its page and clears nothing", asked == "new" and pad.evaluate("() => strokes.length") == before,
          f"page {asked}")
    pad.evaluate("() => { document.getElementById('clearMenuItem').click(); }")   # Start
    pad.wait_for_timeout(600)
    check("Start clears", pad.evaluate("() => strokes.length") == 0)

    toast = pad.evaluate("""() => { const t=document.getElementById('toast');
        const b=t.querySelector('.toast-action');
        return { hidden: t.hidden, text: t.textContent, action: b ? b.textContent : null,
                 clickable: b ? getComputedStyle(b).pointerEvents : null }; }""")
    check("a toast offers an Undo", toast["action"] == "Undo", str(toast))
    check("the toast is actually visible", not toast["hidden"], str(toast["hidden"]))
    # .toast is pointer-events:none, so the button must opt back in or it's a lie.
    check("the Undo button is genuinely clickable", toast["clickable"] == "auto",
          f"pointer-events: {toast['clickable']}")

    pad.click(".toast-action")
    pad.wait_for_timeout(900)
    after = pad.evaluate("() => strokes.length")
    check("Undo restores the drawing", after == before, f"{after} strokes, was {before}")
    check("the toast confirms the restore",
          "restor" in pad.evaluate("() => document.getElementById('toast').textContent").lower(),
          pad.evaluate("() => document.getElementById('toast').textContent"))
    check("no Pad page errors through the whole cycle", not pad_errors, "; ".join(pad_errors[:2]))

    print("\nTOASTS — the action is opt-in and doesn't leak into ordinary toasts")
    plain = pad.evaluate("""() => { showToast('plain message', null);
        const t=document.getElementById('toast');
        return { text: t.textContent, action: !!t.querySelector('.toast-action') }; }""")
    check("an ordinary toast has no button", not plain["action"], str(plain))
    check("an ordinary toast still shows its text", plain["text"] == "plain message", str(plain))
    check("a toast never blocks the canvas underneath",
          pad.evaluate("() => getComputedStyle(document.getElementById('toast')).pointerEvents") == "none")

    br.close()

print("\nDISMISS — every overlay has a keyboard and a pointer exit")
# Flip's ... menu closed on an outside click only: no Escape, and no handler on
# its own scrim. Every other dismissible surface in the tree already had both —
# the export sheet, the tune panel, the help drawer, and Pad's own menu — so
# this one trapped you. It mattered less before the menu gained a full-screen
# dim; a scrim with no keyboard exit is a dead end, and dimming the page
# implies tapping the dim dismisses it.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _errs = []
    _pg.on("pageerror", lambda e: _errs.append(str(e)))
    _pg.goto(f"{BASE}/flip", wait_until="load")
    waits.settle(_pg, 1300)

    def _menu_open():
        return _pg.evaluate("() => !document.getElementById('moreMenu').hidden")

    def _scrim_open():
        return _pg.evaluate("() => { const s = document.getElementById('moreScrim');"
                            " return !!s && !s.hidden; }")

    _pg.click("#moreBtn")
    _pg.wait_for_timeout(250)
    check("the menu opens", _menu_open())
    check("and dims the page behind it", _scrim_open(),
          "Pad has dimmed behind its menu since v131; Flip had no scrim at all")

    _pg.keyboard.press("Escape")
    _pg.wait_for_timeout(250)
    check("Escape closes the menu", not _menu_open(),
          "every other overlay here closes on Escape; this one trapped you")
    check("and takes the scrim with it", not _scrim_open(),
          "a scrim left behind blocks every click on the page")

    _pg.click("#moreBtn")
    _pg.wait_for_timeout(250)
    _pg.evaluate("() => document.getElementById('moreScrim').click()")
    _pg.wait_for_timeout(250)
    check("tapping the dimmed area closes the menu", not _menu_open(),
          "dimming the page implies the dim is dismissable")
    check("and the scrim hides with it", not _scrim_open())

    # The state that actually breaks a session: a scrim still painted while the
    # menu is gone swallows every subsequent click on the app. Hit-tested on
    # #moreBtn, the control that was just used and is enabled on an empty page;
    # #postBtn is disabled until there is something to post (v288) and a
    # disabled button falls through elementFromPoint, which read as a scrim.
    check("the toolbar is reachable again afterwards",
          _pg.evaluate("() => { const b = document.getElementById('moreBtn');"
                       " const r = b.getBoundingClientRect();"
                       " const top = document.elementFromPoint("
                       "   r.left + r.width / 2, r.top + r.height / 2);"
                       " return !!top && (top === b || b.contains(top)); }"),
          "something is still painted over the page after the menu closed")
    check("no JS errors dismissing the menu", not _errs, "; ".join(_errs[:2]))
    _b.close()

print("\nWORDMARK — the fullest label that fits, at every width")
# "FM" appeared below 440px, tuned for a header that ALSO held fps, onion,
# grid, draw-on and more inline. Those moved into the settings button and the
# abbreviation was never revisited, so a phone with 104px of free header space
# was showing a 23px abbreviation. Measured: FLIP MODE needs 86px, FLIP 34, FM
# 23; free space is 193px at 760+, 154 at 440, 66 at 340.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    # Measured by FORCING each candidate and reading header.scrollWidth against
    # clientWidth — not by summing child widths. Flex shrinks the controls
    # first, so an arithmetic "free space" figure hides the squeeze and reports
    # room that is not there; that is how the first pass concluded FLIPMODE
    # needed 440px when it actually clears at 360.
    # The three text tiers (FLIPMODE/FLIP/FM) were replaced by a single
    # ~28px fanned-stack mark, smaller than the smallest tier was. The tier
    # assertion's INTENT survives: at every width the tiers used to cover,
    # exactly one visible mark, carrying the word for assistive tech.
    for _w in (1000, 430, 393, 375, 360, 340, 300):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        waits.settle(_pg, 1200)
        _shown = _pg.evaluate("""() => { const w = document.querySelector('.flip-word');
          const m = w && w.querySelector('.brand-mark');
          const r = m ? m.getBoundingClientRect() : {width: 0, height: 0};
          return { visible: !!m && r.width > 10 && r.height > 10,
                   label: (w && w.getAttribute('aria-label')) || '' }; }""")
        # The unified lockup — the shared SKRIBL sticker plus a mode tag —
        # labels this surface "Skribl Flip" (was "Flipmode" back when each mode
        # wore its own sticker).
        check(f"at {_w}px the mark is visible and labelled",
              _shown["visible"] and _shown["label"].lower() == "skribl flip",
              f"{_shown!r} — exactly one visible mark, aria-label carries the word")

        # Real overflow, not arithmetic. A wordmark that "fits" by squeezing
        # the controls or spilling past the edge is not fitting.
        _over = _pg.evaluate("""() => { const h = document.querySelector('.header');
          return Math.round(h.scrollWidth - h.clientWidth); }""")
        check(f"at {_w}px the header does not overflow",
              _over <= 0, f"{_over}px past the edge")
        _pg.close()
    _b.close()

print("\nGRID — centred, on exact pixels, closed on all four edges")
# THE BUG. The grid was a div painted with CSS gradients. Three faults at once:
#   1. Gradients repeat from the origin, so a line lands on 0% but the CLOSING
#      edge gets none — it saturated the top and left borders and stopped short
#      of the bottom and right, reading as top-left justified.
#   2. Percentage stops land on fractional pixels; a 1px line at x=103.6 paints
#      as two dim half-lines, which is what the phantom doubling was.
#   3. syncGrid inset by a hard-coded 1px while the canvas border had become
#      2px, so the whole grid sat a pixel off centre.
# It is a canvas now: every line on a whole DEVICE pixel, closing edges drawn
# explicitly, inset read from the border rather than assumed.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    for _w, _dpr in ((393, 3), (1000, 2), (760, 1)):
        _pg = _b.new_page(viewport={"width": _w, "height": 844},
                          device_scale_factor=_dpr)
        _errs = []
        _pg.on("pageerror", lambda e: _errs.append(str(e)))
        _pg.goto(f"{BASE}/flip", wait_until="load")
        waits.settle(_pg, 1250)
        _pg.evaluate("() => { document.getElementById('flipGrid')"
                     ".classList.add('on'); syncGrid(); }")
        _pg.wait_for_timeout(350)

        _m = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const p = document.getElementById('pad');
          const gb = g.getBoundingClientRect(), pb = p.getBoundingClientRect();
          const c = g.getContext('2d');
          const a = (x, y) => c.getImageData(x, y, 1, 1).data[3];
          const midX = Math.floor(g.width / 2), midY = Math.floor(g.height / 2);
          return {
            tag: g.tagName,
            insets: [ +(gb.left - pb.left).toFixed(1), +(gb.top - pb.top).toFixed(1),
                      +(pb.right - gb.right).toFixed(1), +(pb.bottom - gb.bottom).toFixed(1) ],
            // A line on every closing edge, sampled away from intersections.
            edges: [ a(midX, 0), a(midX, g.height - 1), a(0, midY), a(g.width - 1, midY) ],
            // A cell centre must be EMPTY. If gradients were still painting, or
            // lines had smeared, this would pick up stray alpha.
            //
            // Sampled at 1/32 x 1/24 — the middle of a FINE cell. It used to be
            // 1/16 x 1/12, which is exactly where a fine line falls once the
            // subdivision runs at every size, so the check was reading the
            // grid's own line and calling it a smear.
            cellCentre: a(Math.floor(g.width / 32), Math.floor(g.height / 24))
          };
        }""")

        check(f"at {_w}px/{_dpr}x the grid is a canvas", _m["tag"] == "CANVAS",
              f"{_m['tag']} — CSS gradients cannot hit an exact device pixel")
        _ins = _m["insets"]
        check(f"at {_w}px/{_dpr}x the grid is centred in the frame",
              max(_ins) - min(_ins) < 0.6,
              f"insets L/T/R/B {_ins} — it is justified to one corner")
        check(f"at {_w}px/{_dpr}x every closing edge has a line",
              all(e > 20 for e in _m["edges"]),
              f"edge alphas {_m['edges']} — a zero means that side has none")
        check(f"at {_w}px/{_dpr}x cell interiors are clean",
              _m["cellCentre"] == 0,
              f"alpha {_m['cellCentre']} inside a cell — stray or smeared lines")
        check(f"at {_w}px/{_dpr}x drawing the grid raises no errors",
              not _errs, "; ".join(_errs[:2]))
        _pg.close()
    _b.close()

print("\nGRID — even lines, measured from the pixels")
# The grid is a <canvas>, drawn by drawGrid() at integer device-pixel
# positions. Two failure modes this guards:
#   1. uneven spacing — the old CSS-gradient grid used PERCENTAGE background
#      sizes, so every line landed on a fractional pixel and the browser
#      rounded each one independently, giving visibly irregular columns
#   2. a double grid — a canvas still paints its CSS background-image, so a
#      leftover gradient rule under the canvas draws a SECOND grid through it
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    for _vw, _dpr, _label in ((393, 3, "phone"), (1000, 2, "desktop")):
        _ctx = _b.new_context(viewport={"width": _vw, "height": 852},
                              device_scale_factor=_dpr)
        _pg = _ctx.new_page()
        _pg.goto(f"{BASE}/flip", wait_until="load")
        waits.settle(_pg, 1300)
        _pg.evaluate("() => { grid = true;"
                     " const g = document.getElementById('flipGrid');"
                     " g.classList.add('on'); syncGrid(); }")
        _pg.wait_for_timeout(350)

        check(f"{_label}: the grid canvas has no CSS background image",
              _pg.evaluate("() => getComputedStyle("
                           "document.getElementById('flipGrid')).backgroundImage") == "none",
              "a canvas still paints its background — that is a second grid "
              "drawn through the first")

        _g = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const c = g.getContext('2d'), W = g.width, H = g.height;
          // Rows are H/6 apart, so H/12 is the midpoint of the first row —
          // except when rounding puts a line there, which it did at desktop.
          // Search for a row that actually crosses verticals instead of
          // assuming one: sampling blind measured a solid horizontal and
          // reported "1 line".
          let y = Math.round(H / 12);
          for (let k = 0; k < 40; k++) {
            const probe = c.getImageData(0, y, W, 1).data;
            let opaque = 0;
            for (let x = 0; x < W; x++) if (probe[x * 4 + 3] > 10) opaque++;
            if (opaque > 0 && opaque < W * 0.5) break;   // crosses lines, not on one
            y = Math.round(H / 12) + k + 1;
          }
          const d = c.getImageData(0, y, W, 1).data;
          const xs = [];
          for (let x = 0; x < W; x++) if (d[x * 4 + 3] > 10) xs.push(x);
          const runs = [];
          if (xs.length) { let s = xs[0], prev = xs[0];
            for (const x of xs.slice(1)) { if (x !== prev + 1) { runs.push([s, prev]); s = x; } prev = x; }
            runs.push([s, prev]); }
          const centers = runs.map(r => (r[0] + r[1]) / 2);
          const gaps = centers.slice(1).map((v, i) => v - centers[i]);
          return { lines: runs.length, gaps,
                   widths: [...new Set(runs.map(r => r[1] - r[0] + 1))] };
        }""")
        check(f"{_label}: the sample row crosses vertical lines",
              _g["lines"] >= 5, f"found {_g['lines']} — the sample landed on a "
              "horizontal line and measures nothing")

        # Even spacing is the whole point. One device pixel of variation is
        # rounding; more than two means lines are landing where they fall.
        # Tightened from 4 to 1. A spread of 4 was the LAST column being narrow:
        # clamping only the closing line inward kept it on the canvas but stole
        # its width from the final cell alone — 129,129,129,129,129,129,130,126.
        # One narrow column on the right edge reads as "the grid is off" without
        # being obviously wrong anywhere you can point at. Laying the lines out
        # over (W - line) instead of W makes every gap equal.
        _spread = max(_g["gaps"]) - min(_g["gaps"]) if _g["gaps"] else 0
        check(f"{_label}: the columns are evenly spaced",
              _spread <= 1,
              f"gap spread {_spread} device px across {_g['gaps']} — "
              "fractional positions rounded independently")
        check(f"{_label}: every line is the same width",
              len(_g["widths"]) == 1,
              f"widths {_g['widths']} — a grid with mixed line weights reads "
              "as noise")
        _ctx.close()
    _b.close()

print("\nDRAWERS ON A PHONE — the last row is not sliced by the browser")
# THE BUG. The drawers are the last thing on the page and had ZERO bottom
# padding, so the colour swatches and the eyedropper sat under iOS Safari's
# bottom toolbar, visibly cut in half. Two causes, both needed:
#   1. no safe-area padding, so nothing reserved space for the browser chrome
#   2. refitDrawer() used scrollIntoView({block:'nearest'}), which scrolls the
#      MINIMUM amount — a drawer already partly on screen got no scroll at all
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _ctx = _b.new_context(viewport={"width": 393, "height": 760},
                          has_touch=True, is_mobile=True)
    _pg = _ctx.new_page()
    _pg.goto(f"{BASE}/flip", wait_until="load")
    waits.settle(_pg, 1400)
    browsing.pad_drawer(_pg, "draw", settle=1100)   # the pen, tapped again

    _m = _pg.evaluate("""() => {
      const eye = document.getElementById('eyedropperBtn').getBoundingClientRect();
      const dots = [...document.querySelectorAll('#colorGroup .color-dot')]
        .map(d => d.getBoundingClientRect());
      const lowest = Math.max(...dots.map(d => d.bottom), eye.bottom);
      const drawers = document.querySelector('.flip-drawers');
      return { lowest: Math.round(lowest), vh: innerHeight,
               pad: parseFloat(getComputedStyle(drawers).paddingBottom) };
    }""")
    check("opening the colour drawer brings its swatches on screen",
          _m["lowest"] <= _m["vh"],
          f"lowest swatch at {_m['lowest']}px in a {_m['vh']}px viewport — "
          "block:'nearest' scrolls the minimum, so a partly-visible drawer "
          "never comes fully into view")
    check("the drawers reserve space for the browser's bottom chrome",
          _m["pad"] >= 20,
          f"padding-bottom {_m['pad']}px — on iOS the toolbar overlays the "
          "viewport and slices whatever is last")
    # ...but only while one is open (owner: "why is there so much blank space at
    # the bottom?" -- the empty container kept the 24px under the dock).
    browsing.pad_drawer_close(_pg, settle=500)
    _shut = _pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.flip-drawers')).paddingBottom)")
    check("with every drawer shut, the drawers reserve nothing under the dock", _shut < 1, f"padding-bottom {_shut}px")
    browsing.pad_drawer(_pg, "draw", settle=900)

    # A transient pill must not cover a destructive control.
    _pg.evaluate("() => { const a = document.getElementById('autosaveStatus');"
                 " if (a) { a.hidden = false; a.classList.add('show'); } }")
    _pg.wait_for_timeout(250)
    check("the Saving pill is hidden while a drawer is open",
          float(_pg.evaluate("() => getComputedStyle("
                             "document.getElementById('autosaveStatus')).opacity")) < 0.05,
          "it sits over Clear all pages — a pill covering a destructive button "
          "is worse than one you cannot see")
    _ctx.close()
    _b.close()

print("\nCOLOUR SWATCHES — exactly one is ever selected")
# THE BUG. setColor did:
#   toggle('active', d.dataset.color && d.dataset.color.toLowerCase() === hex)
# The custom swatch has NO data-color, so that is `undefined && ...` ->
# undefined — and classList.toggle(name, undefined) is treated as no second
# argument, which TOGGLES rather than forcing off. Every colour change flipped
# the custom swatch's ring, so two swatches showed as selected and the wrong
# one looked current. Pad was unaffected: it passes `b === btn`, a real boolean.
import os as _os
# The toggle now lives in lib/colorselect.js, shared by BOTH editors — so this
# reads the lib rather than flip.js. That is the point of the extraction: the
# coercion had to be right in two files and is now right in one. Reading the
# old location would have passed forever once the code moved, which is the
# failure mode of a source-level assertion.
_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_TOGGLE_SRC = open(_os.path.join(_root, "skribl", "static", "lib",
                                 "colorselect.js"), encoding="utf-8").read()
check("the shared colour selector coerces its toggle condition to a boolean",
      "!!(d.dataset" in _TOGGLE_SRC,
      "an && chain can yield undefined, and toggle(name, undefined) TOGGLES")
check("and neither editor still carries its own copy of that toggle",
      all("classList.toggle('active'" not in open(
          _os.path.join(_root, "skribl", "static", f), encoding="utf-8").read()
          .split("function set" + n)[1].split("\n}")[0]
          for f, n in (("flip.js", "Color(hex){"), ("app.js", "PenColor(hex) {")))
      if True else False,
      "two copies of a rule is how they drift apart")

with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    for _name, _path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        _pg = _b.new_page(viewport={"width": 393, "height": 852})
        _pg.goto(f"{BASE}{_path}", wait_until="load")
        waits.settle(_pg, 1250)

        def _active():
            return _pg.evaluate("() => [...document.querySelectorAll("
                                "'#colorGroup .color-dot.active')]"
                                ".map(d => d.id || d.dataset.color || '(dot)')")

        _a = _active()
        check(f"{_name}: exactly one swatch is selected at load",
              len(_a) == 1, f"{len(_a)} selected: {_a}")

        # Clicking through several presets is what surfaced it: the custom
        # swatch flipped on every call, so a single check could pass by luck.
        _dots = _pg.evaluate("() => document.querySelectorAll("
                             "'#colorGroup .color-dot[data-color]').length")
        for _i in range(min(5, _dots)):
            _pg.evaluate(f"() => document.querySelectorAll("
                         f"'#colorGroup .color-dot[data-color]')[{_i}].click()")
            _pg.wait_for_timeout(90)
            _a = _active()
            check(f"{_name}: still exactly one selected after change {_i + 1}",
                  len(_a) == 1, f"{len(_a)} selected: {_a}")

        check(f"{_name}: the custom swatch is not selected by a preset click",
              "customColorBtn" not in _active(),
              "the custom picker shows as current while a preset is in use")
        _pg.close()
    _b.close()

print("\nWORDMARK WEIGHT — the phone is not a thinner brand")
# Was a font-size parity check on the text tiers, then (v220.x) exact height
# parity at every width. The 36px signature (owner's spec) DELIBERATELY
# SUPERSEDES exact parity: at 36px the mark is ~78px wide, and holding that
# on a 320-430px header forced the shed system to spend the two things this
# suite pins harder — the mark itself (hidden at 320) and Post's label
# (dropped at 390). The contract is now a SINGLE declared step, not a slide:
# full size above 480, one smaller-but-still-signature size below, the same
# on every phone tier, and never overflowing. "Not a thinner brand" now
# means: the step is designed (one size per band, mark always present), not
# an accident of shrinking.
_PHONE_MARK = 26   # must match the 480px step in styles.css / flip.css
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _sizes = {}
    for _w in (375, 393, 430, 1000):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        waits.settle(_pg, 1150)
        _sizes[_w] = _pg.evaluate("""() => { const m = document.querySelector('.flip-word .brand-mark');
          const h = document.querySelector('.header');
          const r = m.getBoundingClientRect();
          return { size: Math.round(r.height * 2) / 2, weight: Math.round(r.width * 2) / 2,
                   overflow: Math.round(h.scrollWidth - h.clientWidth) }; }""")
        _pg.close()

    _ref = _sizes[1000]
    check("desktop wears the full 36px signature",
          _ref["size"] == 36, f"{_ref['size']}px")
    _phone_sizes = {w: m["size"] for w, m in _sizes.items() if w <= 480}
    check("every phone tier wears the SAME stepped size — one step, not a slide",
          len(set(_phone_sizes.values())) == 1, str(_phone_sizes))
    for _w, _m in _sizes.items():
        _want = _ref["size"] if _w > 480 else _PHONE_MARK
        check(f"at {_w}px the mark is its band's declared size",
              _m["size"] == _want, f"{_m['size']}px tall vs the declared {_want}px")
        check(f"at {_w}px the mark is present with real width",
              _m["weight"] >= 40, f"{_m['weight']}px wide — collapsed or hidden")
        check(f"at {_w}px it does not overflow",
              _m["overflow"] <= 0, f"{_m['overflow']}px past the edge")

    print("\nGRID DENSITY — the fine subdivision runs at every size")
    # It used to be gated to >=560px, from when the grid was CSS gradients:
    # percentage background-size put lines on fractional pixels, so at ~10px
    # spacing the fine layer rendered as an uneven wash. Drawing to a canvas
    # snapped to whole device pixels removed that cause, and the gate outlived
    # it — a phone was left with 43px cells and nothing between them.
    #
    # Counted by sampling the canvas rather than reading CSS, because the grid
    # is no longer painted with gradients.
    for _w, _fine in ((1000, True), (393, True)):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        waits.settle(_pg, 1200)
        _pg.evaluate("() => { document.getElementById('flipGrid')"
                     ".classList.add('on'); syncGrid(); }")
        _pg.wait_for_timeout(300)
        # Count distinct vertical lines along one scanline.
        _lines = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const c = g.getContext('2d');
          const y = Math.floor(g.height * 0.37);   // avoid horizontal lines
          const row = c.getImageData(0, y, g.width, 1).data;
          let n = 0, run = false;
          for (let x = 0; x < g.width; x++) {
            const on = row[x * 4 + 3] > 8;
            if (on && !run) n++;
            run = on;
          }
          return n;
        }""")
        # The fresh canvas preset follows the viewport (a 393px phone opens
        # 9:16), and the grid derives its column count from the canvas ASPECT —
        # so the expected line count is computed the same way the overlay does,
        # rather than assuming the old fixed 4:3's 8 columns.
        _exp = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const m = SkriblGrid.majors();
          const cols = g.width >= g.height ? m : Math.max(1, Math.round(m * g.width / g.height));
          return { fine: cols * 2 + 1, coarse: cols + 1 };
        }""")
        check(f"at {_w}px the grid includes the fine subdivision",
              (_lines == _exp["fine"]) == _fine,
              f"{_lines} vertical lines — {_exp['coarse']} majors alone, "
              f"{_exp['fine']} with the fine layer")

        # Evenness is the property that made the fine layer usable at all:
        # equal gaps and one opacity per tier. A denser grid that is uneven is
        # worse than a sparse one.
        _even = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const c = g.getContext('2d');
          const y = Math.floor(g.height * 0.37);
          const row = c.getImageData(0, y, g.width, 1).data;
          const starts = []; let run = false;
          for (let x = 0; x < g.width; x++) {
            const on = row[x * 4 + 3] > 8;
            if (on && !run) starts.push(x);
            run = on;
          }
          const gaps = [];
          for (let i = 1; i < starts.length; i++) gaps.push(starts[i] - starts[i - 1]);
          return { spread: gaps.length ? Math.max(...gaps) - Math.min(...gaps) : 0 };
        }""")
        check(f"at {_w}px the lines are evenly spaced",
              _even["spread"] <= 2,
              f"{_even['spread']}px spread between gaps — uneven spacing is what "
              "made the old gradient grid read as a wash")
        _pg.close()

    _b.close()

print("\nICONS — legible at button size, not just at 24px")
# The onion glyph was drawn at stroke-width 1.1 while every neighbour in the
# header is 1.9-2, with four curved paths converging inside a 34px circle. At
# actual size on a dim panel it mushed into a blob. Replaced with a three-sheet
# stack — three because the depth control beside it is 1/2/3, so a two-sheet
# icon would quietly contradict its own setting. The NAME stays "Onion skin":
# it is the correct animation term, and only the drawing was the problem.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    waits.settle(_pg, 1300)

    # STROKED icons only. A filled glyph — the play triangle, the ... dots —
    # reports stroke-width 1 because nothing sets it, and it is never drawn.
    # Including them made this fail on two icons that are perfectly legible.
    _widths = _pg.evaluate("""() => [...document.querySelectorAll(
      '.header button svg, .header a svg')]
      .filter(s => getComputedStyle(s).fill === 'none')
      .flatMap(s => [...s.querySelectorAll('path, circle, line')])
      .map(p => parseFloat(getComputedStyle(p).strokeWidth))
      .filter(w => w > 0)""")
    check("no header icon is drawn thinner than the rest",
          _widths and (max(_widths) - min(_widths)) <= 0.6,
          f"stroke widths {sorted(set(_widths))} — a thin glyph vanishes on a "
          "dim display while its neighbours hold up")

    _paths = _pg.evaluate("() => document.querySelectorAll('#onion svg path').length")
    check("the onion icon is a simple shape, not a tangle",
          _paths <= 3, f"{_paths} paths inside a 34px circle")
    check("its stroke matches its neighbours",
          _pg.evaluate("() => parseFloat(getComputedStyle("
                       "document.querySelector('#onion svg path')).strokeWidth)") >= 1.8)
    check("the name is still Onion skin",
          "onion" in (_pg.get_attribute("#onion", "aria-label") or "").lower(),
          "the term is right; only the drawing was wrong")
    _b.close()

print("\nPENDING MEDIA — dismissing the re-add card clears its dot")
# THE BUG. refreshPendingCards() set the dot hidden=false in its pending
# branch, and the else branch dropped only the 'pending' class — never
# restoring hidden. So dismissing the re-add card left a VISIBLE dot with no
# pending styling, which renders in the "has media" green, until syncMusicUI()
# next ran and hid it. Dismissing turned the dot green; opening the drawer made
# it vanish.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _pg = _b.new_page(viewport={"width": 1100, "height": 900})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    waits.settle(_pg, 1300)

    def _dot(kind):
        return _pg.evaluate(f"""() => {{ const d = document.getElementById('{kind}TabDot');
          return {{ hidden: d.hidden, pending: d.classList.contains('pending') }}; }}""")

    for _kind, _meta, _btn in (("music", "pendingMusicMeta", "musicPendingDismiss"),
                               ("photo", "pendingPhotoMeta", "photoPendingDismiss")):
        _pg.evaluate(f"() => {{ {_meta} = {{ name: 'saved.file' }}; refreshPendingCards(); }}")
        _pg.wait_for_timeout(150)
        _d = _dot(_kind)
        check(f"{_kind}: a saved-but-unloaded file shows a pending dot",
              _d["hidden"] is False and _d["pending"] is True, str(_d))

        _pg.evaluate(f"() => document.getElementById('{_btn}').click()")
        _pg.wait_for_timeout(200)
        _d = _dot(_kind)
        check(f"{_kind}: dismissing the card HIDES the dot",
              _d["hidden"] is True,
              "the dot stays visible without pending styling — it renders green, "
              "as though media were loaded")
        check(f"{_kind}: and drops the pending styling",
              _d["pending"] is False, str(_d))

        # The original symptom was the dot disappearing only when the drawer
        # was opened. Opening must now be a no-op, not the thing that fixes it.
        _pg.evaluate("() => syncMediaUI()")
        _pg.wait_for_timeout(150)
        check(f"{_kind}: opening the drawer does not change it",
              _dot(_kind)["hidden"] is True, str(_dot(_kind)))
    _b.close()

print("\nTUNE PANEL — controls in a stacked row are the same size")
# #fps was a bare .seg on the default height while .onion-seg overrode it to
# 26, so Speed rendered visibly larger than Onion skin directly below it. The
# tint toggle was 28x26 — wider than tall, and 4px proud of the segments —
# which read as a box rather than a round toggle once its active state gave it
# a background.
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    _pg = _b.new_page(viewport={"width": 1000, "height": 900})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    waits.settle(_pg, 1300)
    _pg.click("#tuneBtn")
    _pg.wait_for_timeout(400)

    _m = _pg.evaluate("""() => {
      const g = s => { const e = document.querySelector(s); if (!e) return null;
        const r = e.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height) }; };
      return { fps: g('#fps'), onion: g('#onionDepthSeg'), tint: g('#onionTintBtn') };
    }""")
    check("Speed and Onion skin are the same height",
          abs(_m["fps"]["h"] - _m["onion"]["h"]) < 1.5,
          f"fps {_m['fps']['h']} vs onion {_m['onion']['h']}")
    check("and the same width",
          abs(_m["fps"]["w"] - _m["onion"]["w"]) < 1.5,
          f"fps {_m['fps']['w']} vs onion {_m['onion']['w']}")
    check("the tint toggle matches the segment height",
          abs(_m["tint"]["h"] - _m["onion"]["h"]) < 1.5,
          f"tint {_m['tint']['h']} vs segment {_m['onion']['h']} — it sits proud")
    check("the tint toggle is square",
          _m["tint"]["w"] == _m["tint"]["h"],
          f"{_m['tint']['w']}x{_m['tint']['h']} — wider than tall reads as a box")

    # The header too: .tool-open is 44x44 and .onion-tool overrode it to 34,
    # but .tune-tool did not — so the settings button stood 8px taller than
    # everything beside it. Measured as a SPREAD across the row, which is the
    # check that finds the next one of these rather than this one again.
    _hdr = _pg.evaluate("""() => {
      // 'onion' left the header for the tune drawer's Onion row (v207) — it is
      // an in-drawer 32px toggle now, not a header control.
      const ids = ['tuneBtn', 'postBtn', 'moreBtn'];
      const hs = ids.map(i => { const e = document.getElementById(i);
        return e ? Math.round(e.getBoundingClientRect().height) : null; })
        .filter(h => h !== null);
      return { hs, spread: Math.max(...hs) - Math.min(...hs) };
    }""")
    check("every control in the header row is the same height",
          _hdr["spread"] <= 2,
          f"heights {_hdr['hs']} — spread {_hdr['spread']}px")

    _pg.click("#onionTintBtn")
    _pg.wait_for_timeout(250)
    _after = _pg.evaluate("() => { const r = document.querySelector"
                          "('#onionTintBtn').getBoundingClientRect();"
                          " return { w: Math.round(r.width), h: Math.round(r.height) }; }")
    check("activating the tint does not change its size",
          _after["w"] == _m["tint"]["w"] and _after["h"] == _m["tint"]["h"],
          f"{_after} vs {_m['tint']} — the highlight grows the control")
    _b.close()

print("\nCANVAS — the edge survives every state, and a stroke survives the edge")
with sync_playwright() as _p:
    _b = waits.instrument(_p.chromium.launch())
    # The ring's rgba is the DARK theme's; since v292 a bare page follows the
    # OS, and headless Chromium says light. Ask for the theme the pin measures.
    _pd = _b.new_page(viewport={"width": 1000, "height": 900}, color_scheme="dark")
    _errs = []
    _pd.on("pageerror", lambda e: _errs.append(str(e)))
    _pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    waits.settle(_pd, 1300)

    def _ring():
        return _pd.evaluate("() => getComputedStyle(document.querySelector"
                            "('.canvas-wrap')).boxShadow")

    check("the canvas has an outer ring at rest",
          "rgba(255, 255, 255, 0.18)" in _ring(),
          "no findable edge on a dim panel")
    check("Pad's canvas is rounded like Flip's",
          _pd.evaluate("() => parseFloat(getComputedStyle("
                       "document.querySelector('.canvas-wrap')).borderTopLeftRadius)") > 8,
          "two editors in one app disagreeing about the shape you draw on")

    # THE BUG. .canvas-wrap.recording replaced box-shadow wholesale and dropped
    # the ring — and Pad enters that class on the FIRST STROKE, so the edge
    # vanished exactly when it was needed. A rest-state-only check misses it.
    _box = _pd.locator("#canvas").bounding_box()
    _pd.mouse.move(_box["x"] + 120, _box["y"] + 120)
    _pd.mouse.down()
    _pd.mouse.move(_box["x"] + 300, _box["y"] + 200, steps=8)
    _pd.wait_for_timeout(250)
    check("the canvas is in its recording state", _pd.evaluate(
        "() => document.querySelector('.canvas-wrap').classList.contains('recording')"))
    check("and the ring is STILL there while recording",
          "rgba(255, 255, 255, 0.18)" in _ring(),
          "every state that restyles box-shadow must keep --canvas-ring")

    # A stroke must not end because the pointer crossed the border. It did on
    # mouse and not on touch, so the same gesture behaved differently by device.
    _pd.mouse.move(_box["x"] + _box["width"] + 120, _box["y"] + 220, steps=8)
    _pd.wait_for_timeout(120)
    check("leaving the canvas does not end the stroke",
          _pd.evaluate("() => drawing") is True,
          "a stroke that ends where you did not lift the button is one you "
          "did not draw")
    _pd.mouse.move(_box["x"] + 340, _box["y"] + 300, steps=8)
    _pd.mouse.up()
    _pd.wait_for_timeout(300)
    check("returning and releasing leaves ONE unbroken stroke",
          _pd.evaluate("() => strokeGroups.length") == 1,
          f"{_pd.evaluate('() => strokeGroups.length')} strokes — it broke at the edge")
    check("and releasing outside still commits it",
          _pd.evaluate("() => drawing") is False
          and _pd.evaluate("() => strokes.length") > 0,
          "painted but unrecorded")
    check("no JS errors drawing across the edge", not _errs, "; ".join(_errs[:2]))
    _b.close()




ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print("\nV204 PINS — Pad tune drawer, Grid overlay, Flip intro toast")
from playwright.sync_api import sync_playwright as _sp204
with _sp204() as _p:
    _b = waits.instrument(_p.chromium.launch())
    # Pad: tune button opens the drawer; Grid toggles the overlay canvas.
    pg = _b.new_page(viewport={"width": 900, "height": 800})
    browsing.goto(pg, BASE, "/")
    check("V204: Pad has a tune button (new drawer)",
          pg.locator("#tuneBtn").count() == 1)
    check("V204-fix: the Pad tune button is in the header actions, not the toolbar",
          pg.evaluate("() => !!document.querySelector('.header #tuneBtn')"
                      " && !document.querySelector('#toolBar #tuneBtn')"))

    # v205-fix: the tune button must match its header neighbours (flipBtn, menuBtn)
    # in size — it was a larger .tool-open (44px) dropped among 36px .icon-btns,
    # which read as inconsistent. It is now an .icon-btn like them.
    sizes = pg.evaluate("""() => {
        const ids = ['tuneBtn', 'menuBtn'];
        const r = {};
        for (const id of ids) {
            const el = document.getElementById(id);
            if (el) { const b = el.getBoundingClientRect(); r[id] = [Math.round(b.width), Math.round(b.height)]; }
        }
        return r;
    }""")
    check("V205-fix: the tune button matches the menu button's size",
          sizes.get("tuneBtn") == sizes.get("menuBtn"),
          f"tune {sizes.get('tuneBtn')} vs menu {sizes.get('menuBtn')}")
    # The header row is 36, not 44 — Flip's size, adopted on Pad so the two
    # headers stop reading as two design systems. The 44px TAP band is not given
    # up; it moved to the ::before via --tap-grow, so assert BOTH: the painted
    # box is 36 and the hit box is still at least 44. Pinning only the visual
    # size is how a shrink quietly costs a tap target.
    check("V225: header buttons are the 36px row size",
          sizes.get("tuneBtn") == [36, 36],
          f"tuneBtn {sizes.get('tuneBtn')}")
    _tap = pg.evaluate("""() => {
        const el = document.getElementById('tuneBtn');
        const grow = parseFloat(getComputedStyle(el).getPropertyValue('--tap-grow')) || 0;
        const r = el.getBoundingClientRect();
        return { w: Math.round(r.width + grow * 2), h: Math.round(r.height + grow * 2), grow };
      }""")
    check("V225: ...and the tap band is still 44 via --tap-grow",
          _tap["w"] >= 44 and _tap["h"] >= 44,
          f"{_tap['w']}x{_tap['h']} from a {36}px box with --tap-grow {_tap['grow']}")
    # A grown hit box is only real if it WINS the hit test — the ::before extends
    # outside the button, over the header, and without a stacking context the
    # header takes the tap (the trap the --tap-grow block in styles.css records).
    _hit = pg.evaluate("""() => {
        const el = document.getElementById('tuneBtn'), r = el.getBoundingClientRect();
        const hit = document.elementFromPoint(r.left - 3, r.top + r.height / 2);
        return !!(hit && (hit === el || el.contains(hit) || hit.parentElement === el));
      }""")
    check("V225: ...and a tap 3px outside the visual box still lands on the button",
          _hit, "the ::before is not winning the hit test")

    # v205-fix: the compact/recording row (Record, Play, Post, menu) must be one
    # uniform height — Play was a short .btn-icon (~29px) among 44px pills.
    pg.mouse.move(300, 300); pg.mouse.down(); pg.mouse.move(360, 340); pg.mouse.up()   # arms the take (v288)
    pg.wait_for_timeout(200)
    pg.evaluate("() => document.getElementById('recordBtn').click()")   # stop
    pg.wait_for_timeout(500)
    # After the take the Record button is hidden (v288) and reads 0 here, which
    # the `if v` filter below drops; the row that remains is Play, Post, menu.
    rowh = pg.evaluate("""() => {
        const h = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : null; };
        return { record: h('#recordBtn'), play: h('.btn.play'), post: h('#postBtn'), menu: h('#menuBtn') };
    }""")
    hs = [v for v in rowh.values() if v]
    check("V205-fix: the compact row is one uniform height (Play no longer short)",
          hs and (max(hs) - min(hs)) <= 2,
          f"heights {rowh}")

    # v205-fix: HIG tap areas. Sub-44 controls grow an invisible ::before hit
    # region. Prove it: click 5px OUTSIDE the grid toggle's 32px visual box (in
    # the expanded zone) and the toggle must still fire. That is the entire
    # point of the tap-area rule; a rule that only exists in CSS is not proof.
    pg.click("#tuneBtn"); pg.wait_for_timeout(350)
    r = pg.evaluate("() => { const b = document.getElementById('gridBtn').getBoundingClientRect(); return {x:b.left, y:b.top, w:b.width, h:b.height}; }")
    # visual should be 32; the ::before extends 6px each side -> 44 hit box
    check("V205-fix: the grid toggle's VISUAL stays 32px (layout untouched)",
          round(r["w"]) == 32 and round(r["h"]) == 32, f"{r['w']}x{r['h']}")
    before = pg.evaluate("() => document.getElementById('gridBtn').getAttribute('aria-checked')")
    # click 5px left of the visual left edge, vertically centered: inside the
    # 7px expanded zone, outside the 32px box.
    pg.mouse.click(r["x"] - 5, r["y"] + r["h"] / 2)
    pg.wait_for_timeout(250)
    after = pg.evaluate("() => document.getElementById('gridBtn').getAttribute('aria-checked')")
    check("V205-fix: a tap 5px OUTSIDE the toggle's visual box still toggles it (44pt hit area)",
          before != after, f"aria-checked {before} -> {after}")
    # and 12px outside (past the 6px zone) must NOT toggle -> the zone is bounded
    pg.mouse.click(r["x"] - 12, r["y"] + r["h"] / 2)
    pg.wait_for_timeout(250)
    after2 = pg.evaluate("() => document.getElementById('gridBtn').getAttribute('aria-checked')")
    check("V205-fix: ...but 12px outside (beyond the 44 zone) does not — the hit area is bounded",
          after2 == after, f"aria-checked {after} -> {after2}")
    # Restore: turn grid back off and close the drawer, so the later V204 pins
    # (which expect the drawer closed on this same page) are unaffected.
    if after == "true":
        pg.click("#gridBtn"); pg.wait_for_timeout(150)
    pg.click("#tuneBtn"); pg.wait_for_timeout(350)

    # v208 (v207 review F4): starting recording with the Tune drawer OPEN must
    # close it and sync ARIA — recording hides the Tune button, so an open
    # drawer would have no visible opener. And stopping must NOT reopen it.
    pg.click("#tuneBtn"); pg.wait_for_timeout(300)
    check("F4 setup: tune drawer is open before the take", pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    # No idle Record button. This page already holds a finished take (the
    # V205 block above), so the canvas is locked and the way to start another
    # take is the "+ Keep drawing" pill — the same beginRecording path, which is
    # what must close the drawer.
    pg.click("#addTakePill"); pg.wait_for_timeout(350)
    check("F4 setup: Keep drawing started a take", pg.evaluate("() => recording === true"))
    _st = pg.evaluate("() => { const sh = document.getElementById('tuneShell'), b = document.getElementById('tuneBtn'); return { open: sh.classList.contains('open'), ariaHidden: sh.getAttribute('aria-hidden'), expanded: b.getAttribute('aria-expanded') }; }")
    check("F4: starting a take closes the tune drawer (no .open)", not _st["open"], str(_st))
    check("F4: ...shell aria-hidden='true'", _st["ariaHidden"] == "true", str(_st))
    check("F4: ...button aria-expanded='false'", _st["expanded"] == "false", str(_st))
    pg.click("#recordBtn"); pg.wait_for_timeout(350)   # stop
    check("F4: stopping recording does NOT reopen the drawer",
          not pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    # Flip undo/redo are now rounded-square tiles, not circles.
    fpx = _b.new_page(viewport={"width": 900, "height": 800})
    fpx.goto(BASE + "/flip", wait_until="load"); waits.settle(fpx, 700)
    rad = fpx.evaluate("() => getComputedStyle(document.getElementById('undo')).borderRadius")
    check("V205-fix: Flip undo/redo are rounded-square tiles (were circles) — matches Pad + tool shape rule",
          rad == "12px", f"border-radius {rad}")
    fpx.close()

    # Flip's grid toggle must LIGHT when on, like its .onion-tint siblings.
    # It toggled 'on' (unstyled) instead of 'active' since v204, so the overlay
    # drew but the button stayed dark. Pin all three siblings to .active.
    fg = _b.new_page(viewport={"width": 1280, "height": 900})
    fg.goto(BASE + "/flip", wait_until="load"); waits.settle(fg, 700)
    fg.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
    fg.click("#tuneBtn"); fg.wait_for_timeout(350)
    for bid, nm in (("gridBtn", "grid"), ("arcGuideBtn", "motion guides"), ("onionTintBtn", "onion tint")):
        fg.click("#" + bid); fg.wait_for_timeout(200)
        lit = fg.evaluate(f"() => document.getElementById('{bid}').classList.contains('active')")
        check(f"V206: Flip {nm} toggle lights (.active) when on", lit)
        fg.click("#" + bid); fg.wait_for_timeout(150)  # off again
    fg.close()

    # v206 (music drawer option A): nudge +/- are 32px with a 44pt invisible tap
    # area; the 3-column Start/End/Step grid must fit a 375px phone; and a real
    # click 5px OUTSIDE a nudge button must still nudge (tap area is real).
    import struct, io, math
    def wav_bytes(seconds=1.0, rate=8000):
        """A real one-second 440Hz WAV, so the music path actually DECODES rather
        than being handed something the AudioContext rejects."""
        n = int(seconds * rate)
        frames = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / rate)))
                          for i in range(n))
        return (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt "
                + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
                + b"data" + struct.pack("<I", len(frames)) + frames)
    _AUD = wav_bytes()
    for pw in (340, 363, 375, 390, 1280):
        mp = _b.new_page(viewport={"width": pw, "height": 844})
        mp.goto(BASE + "/", wait_until="load"); waits.settle(mp, 700)
        browsing.pad_drawer(mp, "music"); mp.wait_for_timeout(300)
        mp.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD}); mp.wait_for_timeout(1500)
        mp.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[data-dp=\"exact\"]'); if (t && t.getAttribute('aria-expanded') !== 'true') t.click(); }")
        mp.wait_for_timeout(400)
        fit = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
            const grid = document.querySelector('#musicDoorExact .finetune-grid'); if (!grid) return null;
            const gr = grid.getBoundingClientRect();
            const b = document.querySelector('#musicDoorExact .nudge-btn').getBoundingClientRect();
            return { over: gr.right > vw + 1, scrollX: document.documentElement.scrollWidth > vw + 1, nudgeW: Math.round(b.width) }; }""")
        check(f"V206: nudge grid fits at {pw}px (no overflow)", fit and not fit["over"] and not fit["scrollX"], str(fit))
        # The pills themselves must not overlap or spill their column. On
        # phone the groups STACK (one per row) — the earlier three-on-a-row
        # squeeze put 120px pills into 93px columns and they overlapped at 390.
        _ov = mp.evaluate("""() => { const ecs = [...document.querySelectorAll('#musicDoorExact .edge-controls')].map(e => e.getBoundingClientRect());
            const groups = [...document.querySelectorAll('#musicDoorExact .edge-group')].map(e => e.getBoundingClientRect());
            let overlap = false;
            for (let i = 0; i < ecs.length; i++) for (let j = i + 1; j < ecs.length; j++) {
                const a = ecs[i], b = ecs[j];
                const sameRow = Math.abs(a.top - b.top) < 4;
                if (sameRow && a.right > b.left + 1 && b.right > a.left + 1) overlap = true; }
            const spill = ecs.some((e, i) => e.right > groups[i].right + 1 || e.left < groups[i].left - 1);
            return { overlap, spill, rows: new Set(groups.map(g => Math.round(g.top))).size }; }""")
        check(f"V207: at {pw}px the nudge pills do not overlap each other or spill their column", not _ov["overlap"] and not _ov["spill"], str(_ov))
        if pw <= 640:
            # v210 (owner's iPhone): Start and End share a row. Step size, a
            # third group under them, was Each tap, and is gone (lib/
            # musicdrawer.js). The overlap/spill check above still guards the
            # class at every width.
            _rows = mp.evaluate("""() => [...document.querySelectorAll('#musicDoorExact .edge-group')]
                .map(e => Math.round(e.getBoundingClientRect().top))""")
            if pw >= 375:
                check(f"V210: at {pw}px Start of loop and End of loop share a row",
                      len(_rows) == 2 and _rows[0] == _rows[1], f"group tops {_rows}")
            else:
                # 363 and 340 cannot hold two 130px groups: inside the Exact
                # door's card (as inside More's) the grid is the screen less
                # 104px (it was 78px on the drawer's paper, two-up from 348),
                # and two need 270. The grid must fall
                # back to one column rather than spill (v207 bug class).
                check(f"V210: at {pw}px (too narrow for 2-up) the nudge groups stack one per row",
                      len(_rows) == 2 and _rows[1] > _rows[0], f"group tops {_rows}")
        if pw == 1280:
            check("V206: nudge buttons are 32px on desktop (option A)", fit and fit["nudgeW"] == 32, str(fit))
            # tap area: click 5px LEFT of the first "-" nudge (start-earlier). Its
            # readout must change, proving the expanded hit region fires the nudge.
            # the fine-tune body sits below the fold; bring the button on-screen
            # first or the coordinate click lands outside the viewport.
            mp.evaluate("() => document.querySelector('#musicDoorExact .nudge-btn[data-which=\"start\"][data-amount=\"1\"]').scrollIntoView({block: 'center'})")
            mp.wait_for_timeout(300)
            r = mp.evaluate("() => { const b = document.querySelector('#musicDoorExact .nudge-btn[data-which=\"start\"][data-amount=\"1\"]').getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height, r: b.right}; }")
            before = mp.evaluate("() => document.getElementById('startReadout').value")
            # click 5px to the RIGHT of the '+' (outside its box, in the tap zone, away from the readout on its left)
            mp.mouse.click(r["r"] + 5, r["y"] + r["h"] / 2); mp.wait_for_timeout(300)
            after = mp.evaluate("() => document.getElementById('startReadout').value")
            check("V206: a click 5px outside the '+' nudge still nudges (44pt tap area is real)",
                  before != after, f"readout {before!r} -> {after!r}")
        mp.close()

    # v205-fix: PHONE FIT. The bigger buttons + tap areas must not overflow at
    # real phone widths. iPhone SE (375) is the tightest; check both editors,
    # header, toolbar, and with the tune drawer open. No horizontal page scroll,
    # nothing past the right edge.
    for pw in (375, 390):
        for path, nm in (("/", "Pad"), ("/flip", "Flip")):
            ph = _b.new_page(viewport={"width": pw, "height": 844})
            ph.goto(BASE + path, wait_until="load"); waits.settle(ph, 700)
            def _fit(page):
                return page.evaluate("""() => {
                    const vw = document.documentElement.clientWidth;
                    const over = [];
                    for (const s of ['.header', '#toolBar', '.toolbar', '.flip-tools', '.tune-shell']) {
                        const e = document.querySelector(s); if (!e) continue;
                        for (const c of e.querySelectorAll('button,a')) {
                            const r = c.getBoundingClientRect();
                            if (r.width > 0 && r.right > vw + 1) over.push((c.id || c.className.split(' ')[0]) + '@' + Math.round(r.right));
                        }
                    }
                    return { scrollX: document.documentElement.scrollWidth > vw + 1, over };
                }""")
            f1 = _fit(ph)
            check(f"V205-fix: {nm} fits at {pw}px — no horizontal overflow, nothing clipped",
                  not f1["scrollX"] and not f1["over"], f"scrollX={f1['scrollX']} over={f1['over']}")
            if ph.locator("#tuneBtn").count():
                ph.click("#tuneBtn"); ph.wait_for_timeout(350)
                f2 = _fit(ph)
                check(f"V205-fix: {nm} at {pw}px with tune drawer open still fits",
                      not f2["scrollX"] and not f2["over"], f"scrollX={f2['scrollX']} over={f2['over']}")
            ph.close()

    # v205-fix: the round header actions must match the tune opener's box so they
    # do not read as smaller mismatched siblings.
    #
    # v219 CHANGED WHAT THIS GUARDS, so read this before restoring the old form.
    # Flip Mode used to be a third round header button and is now a row inside
    # the ••• menu, with the original book glyph and a subtitle saying what it
    # is — because a 40px icon could not, which is why Flip went unrecognised
    # for several versions. The old assertion compared #flipBtn's box to
    # #tuneBtn's; after the move it measured [0, 0] against [44, 44] and failed.
    # That is the pin reporting a DESIGN CHANGE, not a defect, and the fix is to
    # assert the new arrangement rather than to loosen the old one:
    #   * the header pair (tune, •••) must still match each other exactly,
    #   * #flipBtn must still EXIST and still carry an <svg> book glyph — the
    #     v219 note is explicit that the original glyph was kept and that it
    #     stays an <a href> so open-in-new-tab and the navigation guard survive,
    #   * and it must be reachable: zero-sized while the menu is closed, a real
    #     box once the menu is open. A menu item that never gains a box is the
    #     failure mode this replacement exists to catch.
    sizes = pg.evaluate("""() => {
        const box = el => { const r = el.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
        const svg = el => { const s = el.querySelector('svg'); const r = s.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
        const tune = document.getElementById('tuneBtn');
        const menu = document.getElementById('menuBtn');
        const flip = document.getElementById('flipBtn');
        return { tuneBox: box(tune), menuBox: box(menu),
                 tuneSvg: svg(tune), menuSvg: svg(menu),
                 flipExists: !!flip, flipIsLink: !!flip && flip.tagName === 'A',
                 flipHasSvg: !!flip && !!flip.querySelector('svg'),
                 flipBoxClosed: box(flip) };
    }""")
    check("V205-fix: the ⋯ menu button matches the tune button box",
          sizes["menuBox"] == sizes["tuneBox"], str(sizes))
    check("V205-fix: the ⋯ glyph matches the tune glyph size",
          sizes["menuSvg"] == sizes["tuneSvg"], str(sizes))
    check("V219: Flip Mode survived the move into the ⋯ menu as a real <a> with its book glyph",
          sizes["flipExists"] and sizes["flipIsLink"] and sizes["flipHasSvg"], str(sizes))
    pg.click("#menuBtn"); pg.wait_for_timeout(350)
    _fl = pg.evaluate("""() => {
        const f = document.getElementById('flipBtn');
        const r = f.getBoundingClientRect();
        // Its words and its name: since the menu's tiles (after v323) the
        // switch shows "Flip" and its name says the rest.
        return { w: Math.round(r.width), h: Math.round(r.height),
                 text: ((f.textContent || '') + ' ' + (f.getAttribute('aria-label') || '')).replace(/\\s+/g, ' ').trim() };
    }""")
    check("V219: ...and it has a real box once the menu is open (a row nobody can reach is not a relocation)",
          _fl["w"] > 100 and _fl["h"] >= 40, str(_fl))
    check("V219: ...and it carries the subtitle that says what Flip Mode IS — the 40px icon could not",
          "page by page" in _fl["text"] and "separate draft" in _fl["text"], str(_fl))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(250)

    # v204-fix: at ~600px, recording must not let the tune button crowd the
    # record indicator onto the wordmark, and the wordmark must recover after
    # stop. Reproduces the reported 600px overlap + stuck-brand bug.
    narrow = _b.new_page(viewport={"width": 600, "height": 800})
    browsing.goto(narrow, BASE, "/")
    narrow.evaluate("() => { if (!recording) beginRecording(false); }")   # v288: no idle Record button
    narrow.wait_for_timeout(400)
    check("V204-fix: the tune button is hidden while recording (reclaims width)",
          narrow.evaluate("() => { const t = document.getElementById('tuneBtn');"
                          " return t && getComputedStyle(t).display === 'none'; }"))
    # Record indicator and brand must not horizontally overlap.
    overlap = narrow.evaluate("""() => {
        const b = document.querySelector('.brand');
        const r = document.getElementById('recIndicator');
        if (!b || !r || r.hidden) return false;
        const br = b.getBoundingClientRect(), rr = r.getBoundingClientRect();
        // brand is collapsed (wordmark hidden — there is no logo any more);
        // whatever remains of its box must still clear the indicator
        return br.right > rr.left + 1;
    }""")
    check("V204-fix: the record indicator does not overlap the brand at 600px",
          not overlap)
    narrow.evaluate("() => document.getElementById('recordBtn').click()")  # stop
    narrow.wait_for_timeout(500)
    check("V204-fix: the tune button returns after recording stops",
          narrow.evaluate("() => { const t = document.getElementById('tuneBtn');"
                          " return t && getComputedStyle(t).display !== 'none'; }"))
    narrow.close()
    check("V204: Pad's tune drawer starts closed",
          not pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    pg.click("#tuneBtn"); pg.wait_for_timeout(350)
    check("V204: clicking the tune button opens it",
          pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    check("V204: Grid lives in the tune drawer, not the draw drawer",
          pg.evaluate("() => !!document.querySelector('#tunePanel #gridBtn')"))
    # Draw something so the grid has a canvas box, then toggle grid on.
    draw(pg, "#canvas", 120, 120, n=10)
    pg.click("#gridBtn"); pg.wait_for_timeout(300)
    gridpaints = pg.evaluate("""() => {
        const g = document.getElementById('padGrid');
        if (!g || !g.classList.contains('on')) return false;
        const c = g.getContext('2d');
        const d = c.getImageData(0, 0, g.width, g.height).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] !== 0) return true;
        return false;
    }""")
    check("V204: toggling Grid paints the overlay canvas", gridpaints)
    check("V204: the Grid button lights when on",
          pg.evaluate("() => document.getElementById('gridBtn').classList.contains('active')"))
    # Grid must NOT appear inside the shared draw drawer anymore.
    check("V204: Grid row removed from the draw drawer",
          pg.evaluate("() => !document.querySelector('#drawPanel #gridBtn')"))
    pg.close()
    # Flip: the intro toast fires on load (Tips default on, first visit).
    fp = _b.new_page(viewport={"width": 900, "height": 800})
    browsing.goto(fp, BASE, "/flip")
    toast = fp.evaluate("""() => {
        const el = document.querySelector('.skribl-hint');
        return el && !el.hidden ? el.textContent : null;
    }""")
    check("V204: Flip shows the intro toast on first load",
          toast and ("New here" in toast or "How it works" in toast), str(toast)[:50])
    # The intro is a NORMAL small timed toast (the v205 panel is retired —
    # it hid the pointer and could leave a dead zone) that carries a tap-through
    # "How it works ->" action opening the help drawer.
    check("V206: the intro toast is NOT the retired panel variant",
          fp.evaluate("() => !document.querySelector('.skribl-hint-panel')"))
    check("V206: the intro toast carries a 'How it works' action link",
          fp.evaluate("() => { const a = document.querySelector('.skribl-hint-action');"
                      " return !!(a && /how it works/i.test(a.textContent)); }"))
    fp.evaluate("() => document.querySelector('.skribl-hint-action').click()")
    fp.wait_for_timeout(500)
    check("V206: tapping the action opens the How-it-works help drawer",
          fp.evaluate("() => { const h = document.getElementById('helpDrawer');"
                      " return !!(h && !h.hidden && h.classList.contains('open')); }"))
    check("V206: ...and dismisses the toast",
          fp.evaluate("() => { const t = document.querySelector('.skribl-hint');"
                      " return !t || !t.classList.contains('in'); }"))
    fp.evaluate("() => { const c = document.getElementById('helpClose'); if (c) c.click(); }")
    fp.wait_for_timeout(400)

    # Menu verbiage aligned across editors + Clear all in BOTH menus.
    # (pg was closed above; open a fresh Pad page for the Pad-side checks.)
    pg = _b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/", wait_until="load"); waits.settle(pg, 600)
    # Every row, tile and button the menu holds, its pages and the rows that
    # move into Your drafts included (the ⋯ menu after v323).
    _ITEMS = "(sel) => [...document.querySelectorAll(sel + ' :is(.menu-item, .menu-tile, .menu-start)')].map(b => b.textContent.replace(/\\s+/g,' ').trim())"
    pad_items = pg.evaluate(_ITEMS, "#menuSheet")
    flip_items = fp.evaluate(_ITEMS, "#moreMenu")
    def has(items, s): return any(s in x for x in items)
    # The extension moved out of the action's name into a sub-label —
    # "Save draft" is the action, ".skribl" is a detail. Parity still holds:
    # both editors carry the same words, and neither puts "(.skribl)" back in
    # the label itself.
    # A backup, not a draft — autosave is the persistence model, the file
    # is the copy you keep or move.
    # Since the menu's tiles (after v323) the file rows say what they make:
    # "Save as a file" / "Open a file…", each over its .skribl sub-label.
    check("V269: Pad menu says 'Save as a file' like Flip", has(pad_items, "Save as a file"), str(pad_items))
    check("V269: Pad menu says 'Open a file…' like Flip", has(pad_items, "Open a file"), str(pad_items))
    check("V269: Flip menu says 'Save as a file' / 'Open a file…' too",
          has(flip_items, "Save as a file") and has(flip_items, "Open a file"), str(flip_items))
    check("V269: neither menu titles an action with '(.skribl)' any more",
          not has(pad_items, "(.skribl)") and not has(flip_items, "(.skribl)"),
          str([x for x in pad_items + flip_items if "(.skribl)" in x]))
    check("V206: Pad menu says 'Export' like Flip", has(pad_items, "Export") and has(flip_items, "Export"), str(pad_items))
    # v316: "New Skribl" (owner) -- since the tiles, the New tile and its page's
    # "Start a new Skribl".
    check("V316: Flip menu has 'New' and 'Start a new Skribl'", has(flip_items, "Start a new Skribl") and "New" in flip_items, str(flip_items))
    check("V316: Pad menu has 'New' and 'Start a new Skribl'", has(pad_items, "Start a new Skribl") and "New" in pad_items, str(pad_items))
    # New is the first tile (the four done most), and How it works still leads
    # the list, tinted (owner chose it, "B").
    _first = lambda page_, sel: page_.evaluate(f"""() => {{ const m = document.querySelector('{sel}'); if (!m) return null;
      const t = m.querySelector('.menu-tile'), r = m.querySelector('.menu-list > .menu-item');
      return [t && t.id, r && r.id, !!(r && r.classList.contains('menu-feature'))]; }}""")
    check("V316: New is the first tile on both, and How it works leads the list, tinted",
          _first(pg, "#menuSheet") == ["menuNewTile", "helpItem", True] and _first(fp, "#moreMenu") == ["menuNewTile", "miInfo", True],
          f"pad {_first(pg, '#menuSheet')}, flip {_first(fp, '#moreMenu')}")
    # V317: A NEW SKRIBL IS A NEW TITLE (owner: "it should change title, not
    # leave the last title"). New Skribl kept the old name, so the next save and
    # every export carried it. The typed title and the export sheet's own field
    # both clear; get() falls back to a fresh auto-name; Undo brings it back.
    for page_, nm, fn in ((pg, "Pad", "clearAllWithUndo()"), (fp, "Flip", "clearAllPages()")):
        page_.evaluate("() => { if (window.SkriblSavedDrafts) SkriblSavedDrafts.resume('draft-before'); }")
        page_.evaluate("() => { SkriblName.set('Old title'); const e = document.getElementById('exportName');"
                       " if (e) { e.value = 'old-export'; e._skriblDirty = true; } }")
        page_.evaluate(f"() => {fn}")
        page_.wait_for_timeout(300)
        st = page_.evaluate("() => ({ typed: document.getElementById('skriblName').value, got: SkriblName.get(),"
                            " exp: (document.getElementById('exportName') || {}).value || '' })")
        check(f"V317: {nm}: New Skribl starts a new title, not the last one",
              st["typed"] == "" and st["got"] != "Old title" and st["got"].startswith("Skribl") and st["exp"] == "",
              str(st))
    pg.click(".toast-action")
    pg.wait_for_timeout(500)
    fp.evaluate("() => document.getElementById('clearUndo').click()")
    fp.wait_for_timeout(300)
    back = (pg.evaluate("() => SkriblName.get()"), fp.evaluate("() => SkriblName.get()"))
    check("V317: Undo brings the old title back with the drawing, on both editors",
          back == ("Old title", "Old title"), str(back))
    _exp = "() => { const e = document.getElementById('exportName'); return e ? [e.value, !!e._skriblDirty] : null; }"
    back_exp = (pg.evaluate(_exp), fp.evaluate(_exp))
    back_draft = (pg.evaluate("() => SkriblSavedDrafts.current()"), fp.evaluate("() => SkriblSavedDrafts.current()"))
    check("V317: ...and the saved draft it was, so the next Save updates it rather than copying it",
          back_draft == ("draft-before", "draft-before"), str(back_draft))
    check("V317: ...and the typed export name with it (Undo used to lose it for good)",
          back_exp == (["old-export", True], ["old-export", True]), str(back_exp))
    # .skribl file input accepts the types iOS tags an unknown-ext JSON file with
    for page_, nm in ((pg, "Pad"), (fp, "Flip")):
        acc = page_.evaluate("() => document.getElementById('draftInput').getAttribute('accept')")
        check(f"V206: {nm} draft input accepts iOS-friendly types (.skribl + json + text/plain + octet-stream)",
              acc and ".skribl" in acc and "application/json" in acc and "text/plain" in acc and "application/octet-stream" in acc, str(acc))
    # cross-load guard: a Flip .skribl into Pad is refused with directions, and vice versa
    flip_doc = '{"schemaVersion":2,"playbackMode":"flip","fps":12,"frames":[{"strokes":[]}]}'
    pad_doc  = '{"schemaVersion":2,"playbackMode":"replay","fps":30,"frames":[{"strokes":[]}]}'
    pg.set_input_files("#draftInput", {"name": "flip.skribl", "mimeType": "application/json", "buffer": flip_doc.encode()})
    pg.wait_for_timeout(600)
    ptoast = pg.evaluate("() => { const t = document.querySelector('.toast, #toast, .skribl-toast'); return t ? t.textContent : (document.body.textContent.includes('Flip Skribl') ? 'Flip Skribl' : ''); }")
    check("V206: loading a Flip .skribl into Pad is refused with 'open it in Flip Mode'",
          "Flip Skribl" in ptoast or "Flip Mode" in ptoast, repr(ptoast)[:80])
    fp.set_input_files("#draftInput", {"name": "pad.skribl", "mimeType": "application/json", "buffer": pad_doc.encode()})
    fp.wait_for_timeout(600)
    ftoast = fp.evaluate("() => { const c = document.querySelector('.chip'); return c ? c.textContent : (document.body.textContent.includes('Pad Skribl') ? 'Pad Skribl' : ''); }")
    check("V206: loading a Pad .skribl into Flip is refused with 'open it in Skribl Pad'",
          "Pad Skribl" in ftoast or "Skribl Pad" in ftoast, repr(ftoast)[:80])
    # V317 (third review): a backup file opened over a saved draft is a NEW
    # document. It kept the draft's id, so the next Save draft overwrote that
    # draft with the backup ("Draft updated") and the draft was gone.
    _left = []
    for page_, doc in ((pg, pad_doc), (fp, flip_doc)):
        page_.evaluate("() => SkriblSavedDrafts.resume('draft-before')")
        page_.set_input_files("#draftInput", {"name": "backup.skribl", "mimeType": "application/json", "buffer": doc.encode()})
        page_.wait_for_timeout(600)
        _left.append(page_.evaluate("() => SkriblSavedDrafts.current()"))
    check("V317: opening a backup file lets go of the saved draft, so Save cannot overwrite it (Pad, Flip)",
          _left == [None, None], str(_left))
    pg.close()

    # The Flip image/music drawer must SURVIVE picking a file. Flip's file
    # inputs live at the page root (outside the panels), and when the OS dialog
    # returns the browser fires click on that input; the click-outside handler
    # read it as "outside" and closed the drawer the instant a file was chosen —
    # which is why it "never opened" for the owner. Headless can't open a real
    # dialog, so dispatch the same click on the input the browser would.
    browsing.pad_drawer(fp, "music", settle=400)   # Media, then Music
    check("V206: Flip music drawer opens", not fp.evaluate("() => document.getElementById('musicPanel').hidden"))
    fp.evaluate("() => document.getElementById('musicInput').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    fp.wait_for_timeout(300)
    check("V206: ...and stays open when the file input is clicked (dialog round-trip)",
          not fp.evaluate("() => document.getElementById('musicPanel').hidden"))
    browsing.pad_drawer_close(fp)
    browsing.pad_drawer(fp, "photo", settle=400)
    fp.evaluate("() => document.getElementById('imageInput').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    fp.wait_for_timeout(300)
    check("V206: Flip image drawer also survives its file-input click",
          not fp.evaluate("() => document.getElementById('photoPanel').hidden"))
    browsing.pad_drawer_close(fp)

    # THE FORMAT'S load -> render -> play PATH, on documents built for the job.
    # This used to load two .skribl files the owner had asked for as DEMOS —
    # drawings to look at — which a later session promoted into fixtures. That
    # made 2.7 MB of somebody's artwork load-bearing, and left the tested
    # properties to be whatever those particular drawings happened to have.
    # harness/makeskribl.py builds both documents in memory instead, so the
    # repo stores no drawing and each fixture exhibits exactly the property its
    # assertions name.
    import makeskribl as _mk
    _gal = _mk.replay(); _bnc = _mk.flipbook()
    def _ink(page, sel):
        """Pixels that differ from the canvas background.

        THIS COUNTED ALPHA > 0 UNTIL v282, WHICH IS VACUOUS ON FLIP. Flip's
        #pad canvas paints an opaque background, so every sampled pixel had
        alpha 255 and the count was always exactly width*height/4 — 124,848,
        reported identically for a 24-page bouncing-ball drawing and for a
        generated bar pattern. `ink > 5000` would have passed on a blank page.
        It survived since v206 because the fixture in use also saturated it.

        The background is taken from pixel (0,0): transparent on Pad, the
        paper colour on Flip. Either way a drawn pixel differs from it, and a
        blank canvas now measures ~0.
        """
        return page.evaluate(f"""() => {{
            const c = document.querySelector('{sel}');
            const x = c.getContext('2d');
            const d = x.getImageData(0, 0, c.width, c.height).data;
            const br = d[0], bg = d[1], bb = d[2], ba = d[3];
            let n = 0;
            for (let i = 0; i < d.length; i += 16) {{
                if (Math.abs(d[i] - br) + Math.abs(d[i+1] - bg)
                    + Math.abs(d[i+2] - bb) + Math.abs(d[i+3] - ba) > 24) n++;
            }}
            return n; }}""")
    dp = _b.new_page(viewport={"width": 1280, "height": 900}); dp.goto(BASE + "/", wait_until="load"); waits.settle(dp, 600)
    dp.set_input_files("#draftInput", {"name": "replay.skribl", "mimeType": "application/json", "buffer": _gal}); dp.wait_for_timeout(1400)
    # No backslash inside the f-string expression: legal only from Python 3.12,
    # a SyntaxError that kills the whole suite on 3.11.
    _nstrokes = dp.evaluate("() => (typeof strokes !== 'undefined' ? strokes.length : -1)")
    check("FORMAT: a replay .skribl loads in Pad", dp.evaluate("() => typeof strokes !== 'undefined' && strokes.length > 800"),
          f"strokes={_nstrokes}")
    check("FORMAT: ...and renders ink on the canvas", _ink(dp, "#canvas") > 2000, f"ink={_ink(dp,'#canvas')}")
    # GROWS OVER TIME, measured as a state: Play clears and redraws, so take the
    # first reading below the finished drawing, then wait for a larger one.
    # Two fixed 1.2s samples failed whenever the replay ended inside the first.
    _full = _ink(dp, "#canvas")
    dp.click("#playBtn")
    _a, _b2 = _full, -1                                   # -1: never grew, which must fail
    for _ in range(80):                                   # up to ~8s
        dp.wait_for_timeout(100)
        _now = _ink(dp, "#canvas")
        if _a == _full and _now < _full:
            _a = _now
        elif _a < _full and _now > _a:
            _b2 = _now
            break
    check("FORMAT: ...and REPLAYS — the drawing grows over time on Play", _b2 > _a, f"ink {_a} -> {_b2}")
    dp.close()
    df = _b.new_page(viewport={"width": 1280, "height": 900}); df.goto(BASE + "/flip", wait_until="load"); waits.settle(df, 800)
    df.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
    df.set_input_files("#draftInput", {"name": "flipbook.skribl", "mimeType": "application/json", "buffer": _bnc}); df.wait_for_timeout(1400)
    check("FORMAT: a flipbook .skribl loads in Flip as 24 pages @ 12fps",
          df.evaluate("() => frames.length === 24 && fps === 12"), f"pages={df.evaluate('() => frames.length')} fps={df.evaluate('() => fps')}")
    check("FORMAT: ...and renders ink", _ink(df, "#pad") > 5000, f"ink={_ink(df,'#pad')}")
    df.click("#play"); df.wait_for_timeout(500); _i1 = df.evaluate("() => idx"); df.wait_for_timeout(500); _i2 = df.evaluate("() => idx")
    check("FORMAT: ...and FLIPS — page index advances on Play", df.evaluate("() => playing") and _i1 != _i2, f"idx {_i1} -> {_i2}")
    df.close()

    # The player's Repeat (loop) button must VISIBLY light when pressed.
    # .player-btn.active is a JS-toggled class; every player scene in the
    # css-live capture was static, so cssgraph dropped the rule from player.css
    # and the button toggled loop internally but never lit — it read as dead.
    # Post the galaxy, open the real player, press Repeat, check the fill.
    import json as _json, re as _re
    _pp = _b.new_page(viewport={"width": 1280, "height": 900}); _pp.goto(BASE + "/", wait_until="load"); waits.settle(_pp, 600)
    _pp.set_input_files("#draftInput", {"name": "g.skribl", "mimeType": "application/json", "buffer": _gal}); _pp.wait_for_timeout(1200)
    _payload = _pp.evaluate("() => JSON.stringify(serializeSkribl())")
    _resp = _pp.evaluate("""async (body) => { const r = await fetch('/api/skribls', {method:'POST', headers:{'Content-Type':'application/json'}, body}); return {status: r.status, text: await r.text()}; }""", _payload)
    _pp.close()
    _pid = None
    try: _pid = _json.loads(_resp["text"]).get("id")
    except Exception: pass
    check("V207: posting the galaxy demo yields a player id", bool(_pid), str(_resp)[:100])
    if _pid:
        _pl = _b.new_page(viewport={"width": 1000, "height": 800}); _pl.goto(f"{BASE}/s/{_pid}", wait_until="load"); waits.settle(_pl, 1000)
        # Loop ships ON (the players' one-family pass), so the lit look is
        # read at rest and the press must put it OUT. Lit is the one pill's
        # tint, not Play's solid violet.
        _lp_state = "() => { const b = document.getElementById('playerLoopBtn'); return { active: b.classList.contains('active'), bg: getComputedStyle(b).backgroundColor }; }"
        _lit = _pl.evaluate(_lp_state)
        _pl.click("#playerLoopBtn"); _pl.wait_for_timeout(250)
        _out = _pl.evaluate(_lp_state)
        check("V207: player Repeat button is LIT (the one pill's tint) — .player-btn.active is in player.css",
              _lit["active"] and _lit["bg"] == "rgba(124, 92, 255, 0.22)", str(_lit))
        check("V207: ...and pressing it puts it out",
              not _out["active"] and _out["bg"] != _lit["bg"], str(_out))
        _pl.close()

    # At 641px (the desktop breakpoint's first pixel) after recording,
    # "Post to Skribl" wrapped to THREE lines (59px pill), Record wrapped too,
    # and the header overflowed. Pills must never wrap; Post keeps its short
    # label until ~720px where the long one genuinely fits.
    for pw in (641, 660, 700):
        _n = _b.new_page(viewport={"width": pw, "height": 900}); _n.goto(BASE + "/", wait_until="load"); waits.settle(_n, 600)
        _bb = _n.locator("#canvas").bounding_box(); _n.mouse.move(_bb["x"] + 200, _bb["y"] + 200); _n.mouse.down()   # arms the take (v288)
        for _i in range(1, 10): _n.mouse.move(_bb["x"] + 200 + _i * 12, _bb["y"] + 200 + _i * 7)
        _n.mouse.up(); _n.wait_for_timeout(300); _n.click("#recordBtn"); _n.wait_for_timeout(450)
        _g = _n.evaluate("""() => { const h = document.querySelector('.header'); const p = document.getElementById('postBtn'); const r = document.getElementById('recordBtn');
            const ph = p.getBoundingClientRect().height, rh = r.getBoundingClientRect().height;
            return { overflow: h.scrollWidth > h.clientWidth + 1, postH: Math.round(ph), recordH: Math.round(rh), headerH: Math.round(h.getBoundingClientRect().height) }; }""")
        check(f"V207: at {pw}px post-record the header does not overflow", not _g["overflow"], str(_g))
        # Record is hidden after a take (recordH reads 0); Post is the pill
        # that can still wrap here.
        check(f"V207: at {pw}px the Post pill is single-line (<=48px tall, not wrapped)",
              _g["postH"] <= 48, str(_g))
        _n.close()

    # Onion on/off moved from the header into the tune drawer's Onion row
    # (frees header space), styled as an .onion-tint toggle so it lights ORANGE
    # like grid / motion / tint. setOnion() and the row-mute behaviour unchanged.
    # The orange below is the dark theme's shade (v292: a bare page follows the OS, so ask for dark).
    _o = _b.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark"); _o.goto(BASE + "/flip", wait_until="load"); waits.settle(_o, 800)
    _o.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
    check("V207: the onion toggle is no longer in the header",
          _o.evaluate("() => !document.querySelector('.header #onion')"))
    _o.click("#tuneBtn"); _o.wait_for_timeout(350)
    check("V207: the onion toggle lives in the tune drawer's Onion row",
          _o.evaluate("() => !!document.querySelector('#tuneOnionRow #onion')"))
    _on0 = _o.evaluate("() => onion")
    _o.click("#onion"); _o.wait_for_timeout(200); _on1 = _o.evaluate("() => onion")
    check("V207: clicking it toggles onion skin", _on0 != _on1, f"{_on0} -> {_on1}")
    # make sure it's ON, then check the orange
    if not _on1: _o.click("#onion"); _o.wait_for_timeout(200)
    _col = _o.evaluate("() => { const o = document.getElementById('onion'); return { active: o.classList.contains('active'), color: getComputedStyle(o).color }; }")
    check("V207: onion toggle lights ORANGE when on (matches grid/motion/tint)",
          _col["active"] and _col["color"] == "rgb(255, 159, 67)", str(_col))
    _o.close()

    # The loop detail's Focus group (Loop | Start | End) and its magnification
    # stepper (V207, V254) went with the loop detail in step 2: the timeline
    # and the Restart view do its job, and verify_musictimeline.py has them.

    # Help pills that name a real tappable control carry that control's
    # actual glyph (same SVG the button renders); concept pills (Brush size,
    # Pressure) do not. And the Onion-skin text no longer says "in the header"
    # (onion moved to the tune drawer this release).
    _h = _b.new_page(viewport={"width": 1000, "height": 900}); _h.goto(BASE + "/flip", wait_until="load"); waits.settle(_h, 800)
    _h.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
    _h.evaluate("() => openHelpDrawer()"); _h.wait_for_timeout(400)
    _h.evaluate("() => document.querySelectorAll('#helpDrawer .accordion-header').forEach(h => { if (!h.classList.contains('open')) h.click(); })"); _h.wait_for_timeout(300)
    _ic = _h.evaluate("""() => { const pills = [...document.querySelectorAll('#helpDrawer .help-pill')];
        const withIcon = pills.filter(p => p.querySelector('.help-pill-ic svg')).map(p => p.textContent.trim());
        const without = pills.filter(p => !p.querySelector('.help-pill-ic svg')).map(p => p.textContent.trim());
        const onionTxt = (document.querySelector('#helpDrawer .help-pill-ic') ? [...document.querySelectorAll('#helpDrawer .help-tip')].map(t=>t.textContent).join(' ') : '');
        return { withIcon, without, saysHeader: /stacked-sheets.*button in the header/i.test(onionTxt) }; }""")
    check("V207: Pen/Eraser/Magnifier/Onion/Grid help pills carry the real button glyph",
          all(x in _ic["withIcon"] for x in ("Pen", "Eraser", "Magnifier", "Onion skin", "Grid")), str(_ic["withIcon"]))
    check("V207: concept pills (Brush size, Pressure) stay icon-less", "Brush size" in _ic["without"] and "Pressure" in _ic["without"], str(_ic["without"])[:120])
    check("V207: help no longer says the onion button is 'in the header'", not _ic["saysHeader"])
    _h.close()

    # The eyedropper — the one control in the colour row that lacked its
    # 44pt tap area (the dots beside it had theirs). Box stays 30px (dot-sized,
    # on purpose); icon 16->18 to match tier-2 toggles; tap area added. And the
    # help pill's glyph must be the button's OWN glyph, not a lookalike.
    for path, nm, opener in (("/", "Pad", "@pad:draw"), ("/flip", "Flip", "@pad:draw")):
        _e = _b.new_page(viewport={"width": 1280, "height": 900}); _e.goto(BASE + path, wait_until="load"); waits.settle(_e, 800)
        _e.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
        ux_open(_e, opener); _e.wait_for_timeout(400)
        _eg = _e.evaluate("""() => { const e = document.getElementById('eyedropperBtn'); if (!e) return null;
            const r = e.getBoundingClientRect(); const s = e.querySelector('svg').getBoundingClientRect();
            return { box: Math.round(r.width), icon: Math.round(s.width), tap: getComputedStyle(e, '::before').inset, x: r.left, y: r.top, h: r.height }; }""")
        check(f"V207: {nm} eyedropper is 30px box / 18px icon with a 44pt tap area", _eg and _eg["box"] == 30 and _eg["icon"] == 18 and _eg["tap"] == "-8px", str(_eg))
        _e.mouse.click(_eg["x"] - 5, _eg["y"] + _eg["h"] / 2); _e.wait_for_timeout(250)
        check(f"V207: {nm} a tap 5px outside the eyedropper still enters picking mode",
              _e.evaluate("() => document.getElementById('eyedropperBtn').classList.contains('picking')"))
        if nm == "Flip":
            _bp = _e.evaluate("() => [...document.querySelectorAll('#eyedropperBtn svg path')].map(p => p.getAttribute('d')).join('|')")
            _e.evaluate("() => openHelpDrawer()"); _e.wait_for_timeout(400)
            _e.evaluate("() => document.querySelectorAll('#helpDrawer .accordion-header').forEach(h => { if (!h.classList.contains('open')) h.click(); })"); _e.wait_for_timeout(300)
            _hp = _e.evaluate("""() => { const pill = [...document.querySelectorAll('#helpDrawer .help-pill')].find(p => p.textContent.trim().startsWith('Eyedropper'));
                return pill ? [...pill.querySelectorAll('svg path')].map(p => p.getAttribute('d')).join('|') : null; }""")
            check("V207: the help Eyedropper pill uses the button's OWN glyph (not a lookalike)", _bp and _bp == _hp, f"btn {str(_bp)[:30]} vs help {str(_hp)[:30]}")
        _e.close()

    # Icons are SVG, not Unicode text glyphs. The Flip page bar was MIXED
    # (Hold/Artwork SVG, Move/Move/Copy/Delete text: ◀ ▶ ⧉ ✕) and the add-page
    # buttons used the fullwidth ＋ — text glyphs render at different weights
    # across fonts/platforms and did not match their SVG neighbours. Hold's
    # ×N COUNT stays text (it is a number, not an icon).
    _s = _b.new_page(viewport={"width": 1280, "height": 900}); _s.goto(BASE + "/flip", wait_until="load"); waits.settle(_s, 800)
    _s.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); addFrame(true); }")
    _s.wait_for_timeout(300)
    _ic2 = _s.evaluate("""() => { const ids = ['pbLeft','pbRight','pbCopy','pbDel'];
        const pb = ids.map(i => { const b = document.getElementById(i); return { id: i, svg: !!b.querySelector('svg') }; });
        const iconOnlyText = ['pbLeft','pbRight','pbCopy','pbDel'].some(i => document.getElementById(i).querySelector('.pb-ic'));
        const adds = [...document.querySelectorAll('.addbtn')].map(a => ({ svg: !!a.querySelector('svg.addbtn-ic'), hasFullwidthPlus: a.textContent.includes('\uFF0B') }));
        return { allPbSvg: pb.every(x => x.svg), iconOnlyText, adds }; }""")
    check("V207: every page-action button carries an SVG icon", _ic2["allPbSvg"], str(_ic2))
    check("V207: Move/Copy/Delete no longer use text-glyph icons", not _ic2["iconOnlyText"], str(_ic2))
    check("V207: add-page buttons use an SVG plus, not the fullwidth text ＋",
          _ic2["adds"] and all(a["svg"] and not a["hasFullwidthPlus"] for a in _ic2["adds"]), str(_ic2["adds"]))
    _s.close()

    # COMPREHENSIVE phone fit. Measures every interactive control's real
    # rectangle (not container boxes — that is how the nudge-grid overlap slipped
    # past an earlier "fits" check): nothing off-screen, no horizontal page
    # scroll, no same-row overlap between distinct controls. Both editors, each
    # drawer opened in turn, plus music-loaded + fine-tune open, at 375 and 390.
    # v210 WIDENED (v207 review caveat + the owner's iPhone). The v207 audit was
    # a right-edge + same-row check, and it slept through two real bugs:
    #  - the header cluster painting OVER the wordmark: .brand is not a button,
    #    so it was never in the set, and its 34px mark vs the 40px button failed
    #    the |height diff| < 12 "sameRow" heuristic, so nothing was compared;
    #  - the onion tint 4px from an overflow:hidden ancestor (.tune-clip): the
    #    audit checked the viewport edge, not clipping ancestors.
    # Now: the brand is in the set; overlap is a true 2-D rectangle
    # intersection (no row heuristic); left<0 and vertical overflow are
    # checked; and every control's rect is tested against each ancestor whose
    # overflow is not visible, with a minimum clearance so "not yet clipped by
    # 4px" is caught before iOS font metrics eat it. Real vertical scroll is
    # fine (the page scrolls); the horizontal axis and clipping are not.
    # A DOOR'S FIRST CONTROL WINS OVER THE DOCK (lib/musicdrawer.js, opening
    # one of the music drawer's doors, as it did opening More): on a phone too
    # short for both, the page scrolls the dock under the pinned header so that
    # the door's first control is on the screen, as it already did on a 664px
    # phone (verify_sheetswipe). With the drawers' words a size up (B) a
    # 375x844 phone is one, so with a door open ({door: true}) the dock's
    # controls under the header are tucked, not overlapping -- but only if the
    # dock kept below the header would have left that control off the screen;
    # scrolled under for any other reason, they still overlap.
    _AUDIT = """(o) => { const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
        let tucked = new Set();
        if (o && o.door) {
          const det = window.SkriblDrawerDetent, top = det && det.stuckBottom ? det.stuckBottom() : 0;
          const dock = document.getElementById('toolBar') || document.querySelector('.flip-tools');
          const first = document.querySelector('#musicDoors .dp-panel:not([hidden]) button, #musicDoors .dp-panel:not([hidden]) input');
          if (dock && first) { const short = top + 4 - dock.getBoundingClientRect().top;
            if (short > 0 && first.getBoundingClientRect().bottom + short > vh - 12) tucked = new Set(dock.querySelectorAll('*')); } }
        const CLEAR = 6;   // px a control must keep from any clipping ancestor's edge
        const els = [...document.querySelectorAll('button, a[href], input[type=range], [role=switch], .color-dot, .brand')]
          .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; });
        const rects = els.map(e => ({ id: e.id || String(e.className).split(' ')[0] || e.tagName, r: e.getBoundingClientRect() }));
        const offRight = rects.filter(x => x.r.right > vw + 1).map(x => x.id);
        const offLeft = rects.filter(x => x.r.left < -1).map(x => x.id);
        const overlaps = [], clipped = [];
        // Ghosts (inside a collapsed drawer) and the transient hint toast are
        // excluded from OVERLAP tests: a closed drawer's controls have rects
        // but are not on screen, and the toast is an overlay by design.
        const isGhost = i => { for (let p = els[i].parentElement; p && p !== document.body; p = p.parentElement) {
            const pcs = getComputedStyle(p);
            if ((pcs.overflowY !== 'visible' || pcs.overflowX !== 'visible') && p.getBoundingClientRect().height < 2) return true; } return false; };
        const isToast = i => !!els[i].closest('.skribl-hint');
        for (let i = 0; i < rects.length; i++) {
          if (isGhost(i) || isToast(i)) continue;
          for (let j = i + 1; j < rects.length; j++) {
            if (isGhost(j) || isToast(j)) continue;
            if (els[i].contains(els[j]) || els[j].contains(els[i])) continue;
            if (tucked.has(els[i]) || tucked.has(els[j])) continue;
            const a = rects[i].r, b = rects[j].r;
            const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            if (ox > 2 && oy > 2) overlaps.push(rects[i].id + '~' + rects[j].id); }
          // clipping ancestors: any ancestor whose overflow is not visible on
          // the axis where the control's rect exceeds it (minus clearance).
          const r = rects[i].r;
          // A control inside a COLLAPSED container (a closed drawer's clip at
          // 0 height) is clipped BY DESIGN — that is what closed means. Only
          // controls that are visible in the page count.
          // Reliable across Chromium builds (checkVisibility is not): a control
          // is "shown" only if no clipping ancestor has collapsed to ~0 height.
          let shown = true;
          for (let p = els[i].parentElement; p && p !== document.body; p = p.parentElement) {
            const pcs = getComputedStyle(p);
            if ((pcs.overflowY !== 'visible' || pcs.overflowX !== 'visible') && p.getBoundingClientRect().height < 2) { shown = false; break; } }
          if (!shown) { rects[i].ghost = true; continue; }
          for (let p = els[i].parentElement; p && p !== document.body; p = p.parentElement) {
            const cs = getComputedStyle(p);
            const cx = cs.overflowX !== 'visible', cy = cs.overflowY !== 'visible';
            if (!cx && !cy) continue;
            const pr = p.getBoundingClientRect();
            if (pr.height < 2 || pr.width < 2) break;   // collapsed ancestor: by design
            // A segment control's buttons sit FLUSH inside their pill on purpose
            // (the pill's overflow:hidden gives them its rounded corners); the
            // clearance rule is for content that could be cut, not for a
            // rounded frame around its own children.
            // The design's own shape language: "pill segment = one-of-N slider
            // (.seg, .tool-btn pen/eraser, .smooth-btn)" (styles.css, BUTTON
            // SYSTEM). Their buttons sit FLUSH inside a rounded pill that
            // clips only its own corners; that is the shape, not a defect.
            const isSeg = p.classList.contains('seg') || p.classList.contains('smooth-seg')
                       || p.classList.contains('tool-group') || p.id === 'toolGroup' || p.id === 'smoothSeg';
            const need = isSeg ? 0 : CLEAR;
            // A badge INSIDE a rounded card (the page thumbnail's delete) sits
            // near the card edge on purpose; a rounded frame is not a clipper
            // of its own decorations. Only .frame is exempted, by name.
            const isCard = p.classList.contains('frame');
            if (!isCard && cx && (r.right > pr.right - need + 0.5 || r.left < pr.left + need - 0.5))
              clipped.push(rects[i].id + ' in ' + (p.id || String(p.className).split(' ')[0]) + ' x');
            // Vertical: the invisible 44pt tap area (--tap-grow ::before, with
            // z-index so it wins the hit-test) EXTENDS a sub-44 control past
            // its pill on purpose; the pill clips it visually and that is the
            // design (v205-fix). Only the visual box may not be cut.
            const grows = parseFloat(getComputedStyle(els[i]).getPropertyValue('--tap-grow')) > 0;
            if (!grows && !isSeg && cy && cs.overflowY === 'hidden' && (r.bottom > pr.bottom + 0.5 || r.top < pr.top - 0.5))
              clipped.push(rects[i].id + ' in ' + (p.id || String(p.className).split(' ')[0]) + ' y'); } }
        return { scrollX: document.documentElement.scrollWidth > vw + 1, offRight, offLeft,
                 overlaps: [...new Set(overlaps)].slice(0, 6), clipped: [...new Set(clipped)].slice(0, 6) }; }"""
    _AUDIT_OK = lambda r: not r["scrollX"] and not r["offRight"] and not r["offLeft"] and not r["overlaps"] and not r["clipped"]
    for pw in (375, 390):
        for path, nm, openers in (("/", "Pad", ("#tuneBtn", "@pad:draw", "@pad:photo", "@pad:music")),
                                  ("/flip", "Flip", ("#tuneBtn", "@pad:draw", "@pad:photo", "@pad:music"))):
            _f = _b.new_page(viewport={"width": pw, "height": 844}); _f.goto(BASE + path, wait_until="load"); waits.settle(_f, 700)
            _f.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
            _r = _f.evaluate(_AUDIT)
            check(f"PHONE {nm}@{pw}: every control on-screen, no scroll, no overlap, no clip (base)", _AUDIT_OK(_r), str(_r))
            for op in openers:
                if op.startswith("@pad:") or _f.locator(op).count():
                    ux_open(_f, op); _f.wait_for_timeout(350); _r = _f.evaluate(_AUDIT)
                    check(f"PHONE {nm}@{pw}: ...with {op} drawer open", _AUDIT_OK(_r), str(_r))
                    ux_close(_f, op); _f.wait_for_timeout(200)
            ux_open(_f, openers[3]); _f.wait_for_timeout(300)
            _f.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD}); _f.wait_for_timeout(1400)
            _f.evaluate("() => { const t = document.querySelector('#musicDoors .dp-tile[data-dp=\"restart\"]'); if (t && t.getAttribute('aria-expanded') !== 'true') t.click(); }"); _f.wait_for_timeout(600)
            _r = _f.evaluate(_AUDIT, {"door": True})
            check(f"PHONE {nm}@{pw}: ...with music loaded and its tallest door open", _AUDIT_OK(_r), str(_r))
            _f.close()
    # The header brand vs the control cluster, both states, three widths.
    # State 1 (first load): the wordmark shows and the cluster must clear it —
    # or the wordmark must collapse. State 2 (take saved): the wordmark is
    # hidden by CSS and the cluster must still keep a real gap from the MARK,
    # not snug against it (owner's iPhone screenshot). Real click on the real
    # button; the visual audit above cannot see a "gap that is too small".
    _HDR = """() => { const brand = document.querySelector('.brand');
        // The brand used to be icon+wordmark; the icon was removed when the
        // wordmark reduced to PAD (the host site is branded, the header names
        // the mode). Measure whatever brand content is VISIBLE — with nothing
        // visible (fully collapsed) the gap is taken from the brand box's own
        // left edge, i.e. the cluster merely has to stay inside the header.
        const mark = brand.querySelector('svg');
        const words = [...brand.querySelectorAll(':scope > span')].filter(w => getComputedStyle(w).display !== 'none' && w.getBoundingClientRect().width > 0);
        const edges = words.map(w => w.getBoundingClientRect().right);
        if (mark) edges.push(mark.getBoundingClientRect().right);
        const brandRight = edges.length ? Math.max(...edges) : brand.getBoundingClientRect().left;
        const ctrls = [...document.querySelectorAll('.header .actions button')].filter(b => !b.hidden && b.getBoundingClientRect().width > 0);
        const first = Math.min(...ctrls.map(b => b.getBoundingClientRect().left));
        return { wordsShown: words.length, gap: Math.round(first - brandRight) }; }"""
    # Floors are MEASURED, not aspirational: 8px is what the collapsed cluster
    # clears the mark by at 375/390 (and 430 keeps Post's word at exactly 8);
    # 320-class phones run the 36px tier and clear it visually with the mark
    # box reading ~-2 (the box includes the mark's own inner padding), so 4 is
    # the honest floor there. Above these the header would be shedding labels
    # for air nobody can see.
    for pw in (320, 375, 390, 430):
        _floor = 4 if pw <= 340 else 8
        _h = _b.new_page(viewport={"width": pw, "height": 844}); _h.goto(BASE + "/", wait_until="load"); waits.settle(_h, 700)
        _g = _h.evaluate(_HDR)
        check(f"V210 header@{pw}: on first load the cluster clears the brand (or the wordmark collapsed)",
              _g["gap"] >= _floor, f"gap {_g['gap']}px (floor {_floor}), words shown {_g['wordsShown']}")
        # take saved: draw a stroke, stop.
        _bx = _h.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return {x: r.x, y: r.y}; }")
        _h.mouse.move(_bx["x"] + 40, _bx["y"] + 60); _h.mouse.down(); _h.mouse.move(_bx["x"] + 160, _bx["y"] + 120, steps=6); _h.mouse.up()
        _h.wait_for_timeout(300); _h.click("#recordBtn"); _h.wait_for_timeout(600)
        _g = _h.evaluate(_HDR)
        check(f"V210 header@{pw}: with a take saved the cluster still clears the mark",
              _g["gap"] >= _floor - 6 if pw <= 340 else _g["gap"] >= _floor,
              f"gap {_g['gap']}px (floor {_floor}), words shown {_g['wordsShown']}")
        # v223 REGRESSION PIN — the reported iPhone bug: the mark vanished when
        # recording started (intended) and never came back when it stopped.
        # This state IS record→stop, so the assertion below is the repro.
        #
        # The gap check above could not catch it and never will: with the mark
        # hidden the probe measures from the brand box's own left edge, so a
        # missing mark makes the gap LARGER and the assertion greener. Measure
        # the mark itself. The brand is logo-only — there is no wordmark behind
        # it — so a hidden mark leaves nothing naming the surface.
        # The mark is an <img class="brand-mark"> (cached static SVG), so
        # probe the class, not the svg element.
        _mk = _h.evaluate("() => { const s = document.querySelector('.brand > span .brand-mark');"
                          " if (!s) return 0; const r = s.getBoundingClientRect();"
                          " return r.width > 0 && r.height > 0 ? Math.round(r.width) : 0; }")
        # v269 CHANGED THE ARITHMETIC AGAIN, in the mark's favour: the brand is
        # now the ~43px one-stroke signature, a third the old sticker's width,
        # and it fits EVERY width this loop drives — including the 320px safety
        # net where the old mark genuinely could not. The "stays shed" branch
        # is retired with the width problem it described.
        check(f"v223 header@{pw}: after record→stop the MARK IS BACK",
              _mk > 0,
              f"mark {_mk}px — the signature fits at every width; nothing "
              f"should be hiding it")
        # And Post keeps its word wherever the arithmetic allows.
        #
        # v219 CHANGED THE ARITHMETIC, and the old pin's own reason is what says
        # so: it read "six controls cannot fit a labelled Post". There are five
        # now. Moving Flip Mode into the ••• menu freed 40px of header — that is
        # the change that closed the recording-header overage — and with it Post
        # keeps its label all the way down to 375px, measured at 81px wide.
        # Demanding icon-only below 430 would now be demanding that the header
        # shed something it no longer needs to shed, which is the opposite of
        # what this assertion was written to protect.
        #
        # The floor is what matters and it is kept: 320px is the safety net, not
        # a design target, and there Post must still be free to drop to its icon.
        # v223 NARROWS THIS PIN, deliberately, and the owner made the call. The
        # v219 reasoning above is still correct on its own terms — the 40px from
        # moving Flip is real — but it was settled while the take-saved state hid
        # the mark unconditionally, so Post's word was competing against empty
        # space. It now competes against the mark, and the mark is the WHOLE
        # brand: the header carries no wordmark behind it, so shedding it leaves
        # nothing naming the surface, while Post shedding its word leaves a
        # labelled icon with a title attribute. Measured at 390 with a take
        # saved: the mark is 21px over-full, Record is already icon-only there,
        # the gap step frees 8px, and Post's label frees 47 — Post's word is the
        # only thing large enough to pay for the mark.
        #
        # So the split moves from 375 to 430, and ONLY for the take-saved state
        # this loop measures; idle is untouched and keeps the word everywhere.
        # To reverse: restore `pw >= 375` here and drop pass A of the shed in
        # initBrandFit().
        # v269 revisits v223's trade: the signature mark costs ~43px, so Post's
        # word no longer has to pay for the brand — with a take saved, Post
        # keeps its label from 390 up (measured 83px there). At 375 the
        # arithmetic is still ~10px short, so Post may drop to its icon; below
        # that is the safety net where Post is merely required to exist.
        _pw = _h.evaluate("() => { const p = document.getElementById('postBtn'); return p && !p.hidden ? Math.round(p.getBoundingClientRect().width) : null; }")
        if pw >= 390:
            check(f"v269 header@{pw}: Post KEEPS its label — the signature mark and the word both fit",
                  _pw and _pw > 60, f"Post {_pw}px wide")
        else:
            check(f"v269 header@{pw}: Post is present, label optional at this width", _pw and _pw > 0, f"Post {_pw}px wide")
        _h.close()

    check("V204: the old crammed .flip-hint footer is gone",
          fp.evaluate("() => !document.querySelector('.flip-hint')"))
    fp.close()
    _b.close()

print("\nAMENDMENT PINS — A1 wiring, A2 narrow-viewport frame")
import re as _re
# CODE ONLY. A mutation commented the late-decode hook out and left the
# original line verbatim in the comment above it: the hook was never
# defined, the feature was dead, and both pins below PASSED -- the second
# reporting "3 references", because the comment added one. 371 assertions
# green with the feature removed. See harness/source.py.
_appjs = source.read_js(ROOT / "skribl" / "static" / "app.js")
check("A1: the late-decode hook is defined",
      "_skriblLateAudio = " in _appjs or "_skriblLateAudio=(" in _appjs)
check("A1: ...and invoked from the decode-complete path",
      _appjs.count("_skriblLateAudio") >= 2,
      f"{_appjs.count('_skriblLateAudio')} references")
# A1's retry (`p.then(() => { if (running && !paSource) audioStart(); })`) is
# GONE ON PURPOSE in v210, and this pin now guards its absence. It could never
# fire: begin() had already called audioStart(), which started a source on the
# suspended context and set paSource, so `!paSource` was false by the time the
# promise resolved. Three builds read as "iOS audio fixed" on the strength of
# it while every shared link was silent on a real iPhone. The invariant that
# replaced it is stronger and is what is pinned here: a buffer source is never
# CONSTRUCTED unless the context reports running.
check("A1's unreachable retry is not reintroduced",
      "if (running && !paSource) audioStart()" not in _appjs,
      "the retry that could never fire is back")
check("player audio only constructs a source on a RUNNING context",
      "audioCtx.state !== 'running') return false;" in _appjs
      and "createBufferSource" in _appjs)
# The editor loop engine is lib/audioloop.js's since v315 (one copy for Pad,
# Flip and the player), so the rule is read THERE, and app.js must use it --
# a pin on app.js's text alone would pass on an engine nobody calls.
_loopjs = source.read_js(ROOT / "skribl" / "static" / "lib" / "audioloop.js")
check("the editor loop applies the same rule",
      "if (ctx.state === 'running') return go();" in _loopjs
      and "c.state !== 'running') return false;" in _loopjs
      and "SkriblAudioLoop.engine(" in _appjs)
# The two native fallbacks are Play's music loop's (editor_music.js) and
# Preview Loop's, which is lib/musicdrawer.js's, one copy for both editors (the
# player names neither); the onFail they are handed is still app.js's
# startWebAudioLoop's.
_musicjs = source.read_js(ROOT / "skribl" / "static" / "editor_music.js")
_drawerjs = source.read_js(ROOT / "skribl" / "static" / "lib" / "musicdrawer.js")
check("a failed unlock hands off to native audio instead of claiming success",
      "onFail" in _appjs and "playNativeLooped" in _musicjs
      and "h.loop.start(fallback" in _drawerjs and "function loopNative" in _drawerjs)
check("A1: decode/fetch failures are no longer silent",
      "music decode failed" in _appjs and "music fetch failed" in _appjs)

# F3 (v207 review): the same unlock-timing class as A1, in the EDITOR replay
# A1 never touched. Pad's Play calls clearAndRestore, which on a first play
# after recording goes through `new Image()` + onload — so anything the
# callback does happens AFTER the click gesture has returned, and iOS will not
# unlock an AudioContext there. Not a source pin: drive the real button and
# watch the ORDER, because the whole bug was that the code looked right and
# ran late.
#
# The page is made to behave like iOS: state reports 'suspended' until a
# resume() promise resolves. Headless Chromium starts contexts running, so
# without this the branch under test is never entered — and a green light for
# a path that was never taken is what F1 was.

# A2: at the widths that used to clip, the ring must be sampleable INSIDE the
# wrap's left and right edges. Computed-style + geometry, not screenshots:
# an inset shadow is unclippable by construction, so pin the construction.
from playwright.sync_api import sync_playwright as _sp
with _sp() as _p:
    _b = waits.instrument(_p.chromium.launch())
    for _w in (461, 390, 344):
        _pg = _b.new_page(viewport={"width": _w, "height": 800})
        _pg.goto(f"{BASE}/skribl-pad", wait_until="load")
        waits.settle(_pg, 400)
        _probe = _pg.evaluate("""() => {
            const el = document.querySelector('.canvas-wrap');
            if (!el) return null;
            const cs = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return { shadow: cs.boxShadow, left: r.left, right: r.right,
                     vw: document.documentElement.clientWidth };
        }""")
        check(f"A2 @{_w}px: the frame ring is INSET (paints inside the box)",
              _probe and "inset" in (_probe["shadow"] or ""),
              str((_probe or {}).get("shadow"))[:60])
        check(f"A2 @{_w}px: the wrap's edges are on-screen where the ring paints",
              _probe and _probe["left"] >= 0
              and _probe["right"] <= _probe["vw"] + 0.5,
              f"left {_probe['left']:.1f}, right {_probe['right']:.1f}, "
              f"vw {_probe['vw']}" if _probe else "no .canvas-wrap")
        _pg.close()
    _b.close()

with _sp() as _p3:
    _b = waits.instrument(_p3.chromium.launch())
    _F3_INIT = """
    window.__ord = [];
    const AC = window.AudioContext || window.webkitAudioContext;
    let unlocked = false;
    Object.defineProperty(AC.prototype, 'state',
      { configurable: true, get() { return unlocked ? 'running' : 'suspended'; } });
    const _resume = AC.prototype.resume;
    AC.prototype.resume = function () {
      window.__ord.push('resume');
      return _resume.call(this).then(() => { unlocked = true; });
    };
    const _draw = CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage = function (src) {
      if (src instanceof HTMLImageElement) window.__ord.push('base-image-painted');
      return _draw.apply(this, arguments);
    };
    // clearAndRestore caches the decoded base image and paints SYNCHRONOUSLY on
    // every later call, so by the time we press Play the async branch would be
    // gone — and the bug with it. Reporting complete=false keeps the cache
    // fast-path shut, which is how the reviewer specified forcing this: onto
    // the Image.onload branch, not around it.
    Object.defineProperty(HTMLImageElement.prototype, 'complete',
      { configurable: true, get() { return false; } });
    const _start = AudioBufferSourceNode.prototype.start;
    AudioBufferSourceNode.prototype.start = function () {
      window.__ord.push('loop-started:' + this.context.state);
      return _start.apply(this, arguments);
    };
    """
    _f3 = _b.new_page(viewport={"width": 1280, "height": 900})
    _f3.add_init_script(_F3_INIT)
    browsing.goto(_f3, BASE, "/")
    browsing.pad_drawer(_f3, "music")
    _f3.wait_for_timeout(300)
    _f3.set_input_files("#musicInput",
                        {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD})
    _f3.wait_for_timeout(1500)
    browsing.pad_drawer_close(_f3)
    _f3.wait_for_timeout(200)


    def _f3_stroke(pg, y):
        box = pg.evaluate("() => { const r = document.getElementById('canvas')"
                          ".getBoundingClientRect(); return {x: r.x, y: r.y}; }")
        pg.mouse.move(box["x"] + 60, box["y"] + y)
        pg.mouse.down()
        pg.mouse.move(box["x"] + 200, box["y"] + y, steps=8)
        pg.mouse.up()


    # Drawing AUTO-STARTS the take (there is no separate arm step), so two
    # strokes and one Stop is a complete recording with a baseSnapshot behind
    # it — which is what sends Play through clearAndRestore's Image branch.
    _f3_stroke(_f3, 60)
    _f3.wait_for_timeout(400)
    _f3_stroke(_f3, 120)
    _f3.wait_for_timeout(300)
    _f3.click("#recordBtn")          # Stop
    _f3.wait_for_timeout(600)
    _f3.evaluate("() => { window.__ord = []; "
                 "document.getElementById('playBtn').addEventListener('click', "
                 "() => window.__ord.push('gesture-returned')); }")
    _f3.click("#playBtn")
    _f3.wait_for_timeout(1800)
    _ord = _f3.evaluate("() => window.__ord")
    _ix = lambda tag: next((i for i, e in enumerate(_ord) if e.startswith(tag)), -1)
    _i_resume, _i_gesture = _ix("resume"), _ix("gesture-returned")
    _i_paint, _i_loop = _ix("base-image-painted"), _ix("loop-started")

    # The listener above is registered AFTER app.js's, so on the same element it
    # runs last in the same dispatch: anything before it happened synchronously
    # inside the gesture.
    check("F3: the replay really took the async Image.onload branch — the base "
          "image is painted AFTER the click handler returned (else this proves "
          "nothing)", _i_paint > _i_gesture >= 0, str(_ord))
    check("F3: resume() begins SYNCHRONOUSLY inside the Play gesture, before the "
          "canvas restore calls back", 0 <= _i_resume < _i_gesture, str(_ord))
    check("F3: ...and before the base image paints, which is where the old code "
          "reached resume()", 0 <= _i_resume < _i_paint, str(_ord))
    check("F3: the loop starts only once the context is genuinely running — no "
          "start() against a suspended context",
          _i_loop > 0 and _ord[_i_loop].endswith(":running"), str(_ord))
    check("F3: and it does start — the unlock defers the loop, it does not lose it",
          _i_loop > _i_resume, str(_ord))
    _f3.close()
    _b.close()


# v211 (desktop): Space+drag DREW A LINE instead of grab-panning.
# Both editors gated the pan intercept on zoom>1, so at 100% the drag fell
# through to the drawing tool. And Flip draws on pointerdown, which fires
# BEFORE the mousedown the intercept listened for — a capture-phase mousedown
# was always too late there. Pinned by doing what the owner did: hold Space,
# drag across the canvas, and count strokes. Zero, at 100% AND magnified, on
# both editors. A key held down in Playwright is a real keydown/keyup pair.
with _sp() as _p4:
    _b = waits.instrument(_p4.chromium.launch())
    for nm, url, canvas_sel, count_js in (
            ("pad", "/", "#canvas", "() => strokes.length"),
            ("flip", "/flip", "#pad", "() => frame().strokes.length")):
        for magnified in (False, True):
            _s = _b.new_page(viewport={"width": 1280, "height": 900})
            _s.goto(BASE + url, wait_until="load"); waits.settle(_s, 700)
            if magnified:
                # magnify through the app's own zoom API (both editors expose
                # ZoomView.setPct) — the button is behind the magnify toggle
                _z = _s.evaluate("() => { if (typeof ZoomView === 'undefined' || !ZoomView) return null; ZoomView.setPct(200); return ZoomView.isZoomed(); }")
                _s.wait_for_timeout(300)
                if not _z:
                    _s.close(); continue
            before = _s.evaluate(count_js)
            box = _s.evaluate(f"() => {{ const r = document.querySelector('{canvas_sel}').getBoundingClientRect(); return {{x: r.x, y: r.y, w: r.width, h: r.height}}; }}")
            _s.mouse.move(box["x"] + box["w"] * 0.3, box["y"] + box["h"] * 0.5)
            _s.keyboard.down("Space")
            _s.wait_for_timeout(50)
            _s.mouse.down()
            _s.mouse.move(box["x"] + box["w"] * 0.6, box["y"] + box["h"] * 0.55, steps=8)
            _s.mouse.up()
            _s.keyboard.up("Space")
            _s.wait_for_timeout(200)
            after = _s.evaluate(count_js)
            check(f"V211 {nm}@{'magnified' if magnified else '100%'}: Space+drag does NOT draw",
                  after == before, f"strokes {before} -> {after}")
            if nm == "flip":
                # On Flip an unzoomed Space is play/stop BY DESIGN (verify_keys
                # guards the scoped split). A Space held down for a grab must
                # not have left the flipbook PLAYING — if it did, "no stroke"
                # above would be true for the wrong reason (pointerdown bails
                # on `playing`). Holding Space to drag fires ONE keydown; a
                # toggle would be visible here.
                _pl = _s.evaluate("() => (typeof playing !== 'undefined') ? playing : null")
                check(f"V211 flip@{'magnified' if magnified else '100%'}: ...and Space+drag did not toggle PLAYBACK "
                      "(the no-draw result is the stroke guard, not a side effect of playing)",
                      _pl is False, f"playing={_pl}")
            # and a plain drag right after DOES draw (the key was released cleanly)
            _s.mouse.move(box["x"] + box["w"] * 0.3, box["y"] + box["h"] * 0.7)
            _s.mouse.down(); _s.mouse.move(box["x"] + box["w"] * 0.5, box["y"] + box["h"] * 0.72, steps=6); _s.mouse.up()
            _s.wait_for_timeout(200)
            after2 = _s.evaluate(count_js)
            check(f"V211 {nm}@{'magnified' if magnified else '100%'}: ...and drawing resumes once Space is released",
                  after2 > after, f"strokes {after} -> {after2}")
            _s.close()
    _b.close()


# ---------------------------------------------------------------------------
# V213 — undo during a take must not reveal the finished-take controls.
#
# syncStateAfterHistoryChange() derives `recorded` from stroke count alone, then
# unhid #playWrap, #postBtn and #durationBadge from it — the three things
# startRecording() had just deliberately hidden. So undoing mid-recording, with
# ANY stroke still on the canvas, put Play / Post / the duration badge back into
# a header with no room for them: the row overflowed and #recIndicator wrapped
# its "1:04 · 0:19 play" text onto three lines, which is the record pill
# visibly ballooning. Undoing to an empty canvas appeared to "fix" it only
# because `recorded` went false and the same line re-hid them — which is why the
# report said it happens only while something is still drawn.
#
# Measured before the fix at 900x900: the pill went 133x29 -> 66x74 and the
# header overflowed by 16px. Asserted on RENDERED GEOMETRY as well as the hidden
# flags, because `hidden` alone would pass against a build that showed the
# controls without overflowing, and the overflow is what the user saw.
#
# The v213 TOOL work lives in verify_tools.py — these two stay here because they
# are behaviour fixes to recording and drawing, not new tools.
print("\nV213 — undo mid-take keeps the finished-take controls hidden")

_HDR = """() => {
  const g = id => document.getElementById(id);
  const rec = g('recIndicator').getBoundingClientRect();
  const hdr = document.querySelector('.header');
  return {
    recording: recording, strokes: strokes.length,
    play: g('playWrap').hidden, post: g('postBtn').hidden,
    dur: g('durationBadge').hidden,
    recH: Math.round(rec.height),
    overflow: hdr.scrollWidth - hdr.clientWidth,
  };
}"""

with sync_playwright() as _b13:
    _br13 = waits.instrument(_b13.chromium.launch())
    _c13 = _br13.new_context(viewport={"width": 900, "height": 900})
    _p13 = _c13.new_page()
    _p13.goto(BASE + "/", wait_until="load"); waits.settle(_p13, 700)
    _p13.evaluate("() => localStorage.clear()")
    _p13.evaluate("() => { if (!recording) beginRecording(false); }"); _p13.wait_for_timeout(350)   # v288: no idle Record button
    _baseline = _p13.evaluate(_HDR)

    def _stroke13(x0, y0, x1, y1):
        _bx = _p13.locator("#canvas").bounding_box()
        _p13.mouse.move(_bx["x"] + x0, _bx["y"] + y0); _p13.mouse.down()
        for _i in range(1, 15):
            _p13.mouse.move(_bx["x"] + x0 + (x1 - x0) * _i / 14,
                            _bx["y"] + y0 + (y1 - y0) * _i / 14)
        _p13.mouse.up(); _p13.wait_for_timeout(120)

    _stroke13(60, 60, 200, 160)
    _stroke13(60, 300, 220, 380)
    _p13.click("#undoBtn"); _p13.wait_for_timeout(400)
    _mid = _p13.evaluate(_HDR)

    check("V213 gate: still recording with a stroke remaining after the undo",
          _mid["recording"] is True and _mid["strokes"] > 0,
          f"recording={_mid['recording']}, strokes={_mid['strokes']}")
    check("V213 undo mid-take leaves Play, Post and the duration badge HIDDEN",
          _mid["play"] and _mid["post"] and _mid["dur"],
          f"play hidden={_mid['play']}, post hidden={_mid['post']}, "
          f"duration hidden={_mid['dur']}")
    check("V213 ...and the record pill does not grow, nor the header overflow "
          "(the wrap is what the pill ballooning actually is)",
          _mid["recH"] == _baseline["recH"] and _mid["overflow"] <= 0,
          f"pill height {_baseline['recH']} -> {_mid['recH']}, "
          f"header overflow {_mid['overflow']}px")

    # V213b — one mousemove must capture ONE point.
    #
    # continueDraw was bound on the canvas AND on the window (the window one so
    # a stroke keeps following the pointer off-canvas). Over the canvas the
    # element handler runs and the SAME event then bubbles to the window, so
    # every move was captured twice: 21 events -> 41 points, measured. No wrong
    # pixel results, which is why it survived — but the replay array and the
    # posted payload carried double the points, and the stabiliser lerped twice
    # per event, so the smoothing slider meant one thing over the canvas and
    # another outside it.
    _p13.evaluate("() => { strokes = []; strokeGroups = []; }")
    _bx13 = _p13.locator("#canvas").bounding_box()
    _p13.mouse.move(_bx13["x"] + 100, _bx13["y"] + 400); _p13.mouse.down()
    _N13 = 20
    for _i in range(1, _N13 + 1):
        _p13.mouse.move(_bx13["x"] + 100 + _i * 6, _bx13["y"] + 400 + _i * 3)
    _p13.mouse.up(); _p13.wait_for_timeout(250)
    _pts13 = _p13.evaluate("() => strokeGroups.slice(-1)[0] || 0")
    check("V213b one mousemove over the canvas captures ONE point "
          "(the window fallback must not re-handle a bubbled event)",
          _N13 <= _pts13 <= _N13 + 2,
          f"{_N13} moves -> {_pts13} points (double-capture would give ~{_N13 * 2})")
    _p13.close(); _c13.close()
    _br13.close()

print("\nIOS ZOOM — no text field is under 16px, anywhere")
# THE RULE THIS PINS is written in styles.css twice — "16px is the threshold
# below which iOS Safari zooms the whole PAGE on focus" — and was broken a
# third time anyway: the export sheet's file-name field shipped at 13.5px, so
# tapping it on an iPhone zoomed the page. A rule stated in prose twice and
# broken again is a rule that wants a gate.
#
# A RATCHET THAT IS NOW EMPTY. Seven fields were under the threshold when this
# was written and were NAMED rather than fixed, because raising them changes
# real layout and wanted its own pass with eyes on it. That pass happened: all
# seven are at 16px, so the ratchet is empty and the rule is absolute.
#
# The pass was not free, which is why the exemptions existed. Raising
# .mb-offset from 12px made "-1000, -1000" WRAP inside a pill that states its
# height, so the second line painted over the scope pill beside it — while
# scrollWidth against clientWidth reported nothing, because the BOX never
# changed. flip.css now carries `white-space: nowrap` and a clipping
# `safe center`, and verify_layout.py section 5 pins it.
#
# The mechanism stays so that a future exemption is a deliberate edit here
# rather than a number quietly dropped into a stylesheet. The list may SHRINK
# and must never grow.
_ZOOM_EXEMPT = {}
_MEASURE = """() => {
  const out = [];
  document.querySelectorAll('input, textarea').forEach(el => {
    const t = (el.getAttribute('type') || 'text').toLowerCase();
    if (['checkbox','radio','range','file','color','hidden','button','submit'].includes(t)) return;
    out.push({ id: el.id || '.' + (el.className || '').split(' ')[0],
               size: parseFloat(getComputedStyle(el).fontSize) });
  });
  return out;
}"""
with sync_playwright() as _pz:
    _zb = waits.instrument(_pz.chromium.launch())
    _under_new = []
    _seen = set()
    _export_size = None
    for _url, _label in (("/", "Pad"), ("/flip", "Flip")):
        _zp = _zb.new_page(viewport={"width": 1280, "height": 900})
        _zp.goto(BASE + _url, wait_until="load")
        waits.settle(_zp, 2000)
        for _sel in ("#menuBtn", "#exportItem"):
            try:
                _zp.click(_sel, timeout=3000)
                _zp.wait_for_timeout(400)
            except Exception:
                pass
        for _row in _zp.evaluate(_MEASURE):
            _seen.add(_row["id"])
            if _row["id"] == "exportName" and _url == "/":
                _export_size = _row["size"]
            if _row["size"] < 16 and _row["id"] not in _ZOOM_EXEMPT:
                _under_new.append(f"{_label} {_row['id']} at {_row['size']}px")
        _zp.close()
    _zb.close()

check("no text field is under 16px — the ratchet is empty",
      not _under_new,
      "; ".join(_under_new) + " — under 16px iOS Safari zooms the whole page "
      "on focus, which styles.css states twice")
# Name the field this gate was written for, so the regression that prompted it
# fails loudly rather than generically.
check("the export file-name field is at least 16px",
      _export_size is not None and _export_size >= 16,
      f"{_export_size}px — it shipped at 13.5 and zoomed the page on iOS")
# An exemption for a field that no longer exists is a licence nobody is using.
_stale = sorted(k for k in _ZOOM_EXEMPT if k not in _seen)
check("no exemption names a field that no longer exists",
      not _stale, "stale: " + ", ".join(_stale))

print("\nAUTO-RECORD — the header button is a Done button, and one honest exception")
# v288 (the v287 audit, owner's call). The first stroke has armed a take since
# the auto-arm in editor_draw.js; an idle "Record" beside "Recording starts
# automatically" was two ways to say one thing. The button now shows for what
# only a button can do — stop a take, or start one over ink that is on the
# canvas but not in a take — and is otherwise gone. Asserted on the hidden
# property through the real transitions; red on v287, where the button was
# always in the header.
with _sp204() as _ar:
    _arb = waits.instrument(_ar.chromium.launch())
    _arp = _arb.new_page(viewport={"width": 1100, "height": 900})
    browsing.goto(_arp, BASE, "/")
    _arp.evaluate("() => localStorage.clear()")
    _arp.reload(wait_until="load"); waits.settle(_arp, 700)
    _AR = """() => { const b = document.getElementById('recordBtn');
        return { hidden: b.hidden, active: b.classList.contains('active'), recording: recording,
                 pill: !document.getElementById('addTakePill').hidden }; }"""
    _s0 = _arp.evaluate(_AR)
    check("AUTO-RECORD: an empty canvas offers no Record button",
          _s0["hidden"] and not _s0["recording"], str(_s0))
    draw(_arp, "#canvas", 120, 120, n=18)
    _arp.wait_for_timeout(300)
    _s1 = _arp.evaluate(_AR)
    check("AUTO-RECORD: the first stroke starts the take and the button appears as Stop",
          _s1["recording"] and not _s1["hidden"] and _s1["active"], str(_s1))
    _arp.click("#recordBtn"); _arp.wait_for_timeout(500)
    _s2 = _arp.evaluate(_AR)
    check("AUTO-RECORD: after Stop the button is gone and the Keep drawing pill is the way on",
          not _s2["recording"] and _s2["hidden"] and _s2["pill"], str(_s2))
    # The exception, driven through the same function: ink with no take (a
    # restored draft's unrecorded pixels) is where the auto-arm does not fire
    # and a button is the only way to start recording over it.
    _arp2 = _arb.new_page(viewport={"width": 1100, "height": 900})
    browsing.goto(_arp2, BASE, "/")
    _arp2.evaluate("() => localStorage.clear()")
    _arp2.reload(wait_until="load"); waits.settle(_arp2, 700)
    _s3 = _arp2.evaluate("""() => { hasContent = true; recorded = false; recording = false;
        updateEmptyHint(); const b = document.getElementById('recordBtn');
        return { hidden: b.hidden, active: b.classList.contains('active') }; }""")
    check("AUTO-RECORD: unrecorded ink with no take brings Record back, not Stop",
          not _s3["hidden"] and not _s3["active"], str(_s3))
    _arp2.close(); _arp.close(); _arb.close()

print("\nTHE TAKE'S READOUT — calm while you draw, and lit while the pen is down")
# The recording header read as an alarm (crimson pill, blinking dot, crimson
# Stop) on a screen where it is always showing while you draw. It is now a
# purple dot, level bars, the clock and "plays", with Done (in the action's
# purple since after v330, and the dot breathing: see DONE, THE DOT AND THE
# FIRST LINE, below). The bars
# move only while the pen is down -- and while the pen is down the header's
# contents recede to 0.1, so the owner asked of the mock: "doesn't it get
# hidden while you're drawing?" It did. What is asserted is what the eye
# gets: the readout's EFFECTIVE opacity (itself times every ancestor) with
# the pen down and moving, that the bars are running then and still at rest,
# and that nothing in the recording header paints the danger colour.
with _sp204() as _rr:
    _rrb = waits.instrument(_rr.chromium.launch())
    _rrp = _rrb.new_page(viewport={"width": 402, "height": 874})
    browsing.goto(_rrp, BASE, "/")
    _rrp.evaluate("() => localStorage.clear()")
    _rrp.reload(wait_until="load"); waits.settle(_rrp, 700)
    draw(_rrp, "#canvas", 120, 120, n=18)
    _rrp.wait_for_timeout(400)
    _RR = """() => {
        const eff = el => { let o = 1; for (; el; el = el.parentElement) o *= +getComputedStyle(el).opacity; return o; };
        const t = document.getElementById('recTimer'), r = t.getBoundingClientRect();
        const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        const danger = getComputedStyle(document.documentElement).getPropertyValue('--danger').trim();
        const tmp = document.createElement('i'); tmp.style.color = danger; document.body.appendChild(tmp);
        const dRGB = getComputedStyle(tmp).color; tmp.remove();
        const hdr = [document.getElementById('recIndicator'), ...document.querySelectorAll('#recIndicator *'),
                     document.getElementById('recordBtn'), ...document.querySelectorAll('#recordBtn *')];
        const red = hdr.filter(e => { const cs = getComputedStyle(e);
            return cs.color === dRGB || cs.backgroundColor === dRGB || cs.fill === dRGB; }).length;
        return { stroking: document.body.classList.contains('stroking'),
                 clock: eff(t), bars: eff(document.querySelector('.rec-bars')),
                 plays: eff(document.getElementById('recPlays')),
                 painted: !!hit && (hit === t || t.contains(hit)),
                 run: getComputedStyle(document.querySelector('.rec-bars i')).animationPlayState,
                 label: document.getElementById('recordBtn').textContent.trim(), red: red }; }"""
    _rest = _rrp.evaluate(_RR)
    _cb = _rrp.locator("#canvas").bounding_box()
    _rrp.mouse.move(_cb["x"] + 60, _cb["y"] + 60); _rrp.mouse.down()
    _rrp.mouse.move(_cb["x"] + 160, _cb["y"] + 140, steps=20)
    _rrp.wait_for_timeout(700)                # past the recede's delay and fade
    _pen = _rrp.evaluate(_RR)
    _rrp.mouse.up(); _rrp.wait_for_timeout(300)
    check("READOUT: at rest the bars hold still, and the take ends on Done, not Stop",
          _rest["run"] == "paused" and _rest["label"] == "Done", str(_rest))
    check("READOUT: nothing in the recording header paints the danger colour",
          _rest["red"] == 0 and _pen["red"] == 0, f"rest {_rest['red']}, pen {_pen['red']}")
    check("READOUT: with the pen down the clock and bars stay lit (not receded with the header)",
          _pen["stroking"] and _pen["clock"] > 0.9 and _pen["bars"] > 0.9 and _pen["painted"], str(_pen))
    check("READOUT: with the pen down the bars run, and the 'plays' caption recedes",
          _pen["run"] == "running" and _pen["plays"] < 0.5, str(_pen))
    _rrp.close(); _rrb.close()

print("\nTHE POST SHEET'S TICK BOX AND CAPTION — the box is there, the caption shows what you wrote, its corner is yours")
# The owner, after v330, with screenshots: "The little box is almost invisible
# until checked. Also maybe a way to expand box in lower right?"; of the mock,
# "I like your ideas". The unticked box was the card's own faint line, 1.40:1
# against the light sheet and 1.38:1 against the dark; the caption showed
# three lines and scrolled, cutting a five-line caption's top line in half.
# Read off the pixels at 2x (the box's edge against the sheet beside it), and
# from the page (the caption's height on every frame, a mouse's drag and a
# finger's on the grip), on the Pad and Flip, light and dark.
import io as _pio
from PIL import Image as _PImg
_PLUM = lambda c: sum(w * ((v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4)
                      for w, v in zip((0.2126, 0.7152, 0.0722), c[:3]))
_pr = lambda a, b: (max(_PLUM(a), _PLUM(b)) + 0.05) / (min(_PLUM(a), _PLUM(b)) + 0.05)
_FIVE = "A cat for my sister.\nShe drew the first one\nwhen we were kids,\nso this one is for her.\nHappy birthday, Jo!"
_CAP = """() => { const t = document.getElementById('postCaptionInput'); return { h: Math.round(t.getBoundingClientRect().height * 10) / 10,
    hidden: t.scrollHeight - t.clientHeight }; }"""
# The words go in and the box is read on every frame from that same moment:
# read after the typing returned, most of the 0.18s ease had already gone by.
_HEIGHTS = """([text, ms]) => new Promise(done => { const t = document.getElementById('postCaptionInput'), out = [], t0 = performance.now();
    t.focus(); t.value = text; t.dispatchEvent(new Event('input', { bubbles: true }));
    (function tick() { out.push(Math.round(t.getBoundingClientRect().height * 10) / 10); if (performance.now() - t0 < ms) requestAnimationFrame(tick); else done(out); })(); })"""
_GRIP = "() => { const g = document.getElementById('postCaptionGrip'); if (!g) return null; const r = g.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"


def _sheet(pg, path):
    if path == "/":
        draw(pg, "#canvas", 200, 200, n=16); pg.wait_for_timeout(300)
        pg.click("#recordBtn"); pg.wait_for_timeout(500)
    else:
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        draw(pg, "#pad", 200, 200, n=16); pg.wait_for_timeout(300)
    pg.click("#postBtn"); pg.wait_for_timeout(800)


with _sp204() as _ps:
    _psb = waits.instrument(_ps.chromium.launch())
    _box, _fit, _grip = {}, {}, {}
    for _name, _path in (("Pad", "/"), ("Flip", "/flip")):
        for _th in ("light", "dark"):
            _c = _psb.new_context(viewport={"width": 1280, "height": 860}, device_scale_factor=2)
            _pg = _c.new_page(); browsing.goto(_pg, BASE, f"{_path}?theme={_th}"); waits.settle(_pg, 500)
            _sheet(_pg, _path)
            _im = _PImg.open(_pio.BytesIO(_pg.screenshot())).convert("RGB")
            _k = _pg.evaluate("() => { const r = document.querySelector('#postSheet .post-check-box').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
            _edge = _im.getpixel((int(_k[0] * 2) + 1, int((_k[1] + _k[3] / 2) * 2)))
            _ground = _im.getpixel((int((_k[0] - 6) * 2), int((_k[1] + _k[3] / 2) * 2)))
            _box[(_name, _th)] = round(_pr(_edge, _ground), 2)
            if _th == "light":
                # The caption: three lines to start; five written ease it to fit them all.
                _h0 = _pg.evaluate(_CAP)
                _hs = _pg.evaluate(_HEIGHTS, [_FIVE, 400])
                _h1 = _pg.evaluate(_CAP)
                _mid = sorted(set(h for h in _hs if _h0["h"] + 1 < h < _h1["h"] - 1))
                _out = [h for h in _hs if not (_h0["h"] - 1 <= h <= _h1["h"] + 1)]
                # The grip: a mouse's drag 60px down, then 300px up to the floor.
                _gx, _gy = _pg.evaluate(_GRIP) or (0, 0)
                _pg.mouse.move(_gx, _gy); _pg.mouse.down(); _pg.mouse.move(_gx, _gy + 60, steps=8); _pg.mouse.up(); _pg.wait_for_timeout(250)
                _h2 = _pg.evaluate(_CAP)
                _pg.type("#postCaptionInput", " More.")
                _pg.wait_for_timeout(300)
                _h3 = _pg.evaluate(_CAP)
                _pg.evaluate("() => document.activeElement && document.activeElement.blur()")   # the typing's caret put away
                _gx, _gy = _pg.evaluate(_GRIP)
                _pg.mouse.move(_gx, _gy); _pg.mouse.down(); _pg.mouse.move(_gx, _gy - 300, steps=8); _pg.mouse.up(); _pg.wait_for_timeout(250)
                _h4 = _pg.evaluate(_CAP)
                _focus = _pg.evaluate("() => document.activeElement && document.activeElement.id")
                _pg.keyboard.press("Escape"); _pg.wait_for_timeout(500)
                _pg.click("#postBtn"); _pg.wait_for_timeout(800)
                _h5 = _pg.evaluate(_CAP)
                _fit[_name] = {"start": _h0, "fitted": _h1, "between": len(_mid), "outside": _out, "dragged": _h2, "typed": _h3, "floor": _h4, "reopened": _h5, "focus": _focus}
            _c.close()
    # A finger on the grip, on a phone: the drag is the grip's, not the sheet's
    # scroll. On a screen 520px tall, as with the keyboard up, so the sheet does
    # scroll: on a full phone screen nothing in it scrolls, and a finger kept
    # the drag with or without the grip's touch-action.
    _c = _psb.new_context(viewport={"width": 402, "height": 520}, device_scale_factor=2, is_mobile=True, has_touch=True)
    _pg = _c.new_page(); browsing.goto(_pg, BASE, "/"); waits.settle(_pg, 500)
    _sheet(_pg, "/")
    _pg.evaluate("() => document.getElementById('postCaptionInput').scrollIntoView({ block: 'center' })"); _pg.wait_for_timeout(300)
    _pg.evaluate("""() => { window.__gc = 0; document.addEventListener('pointercancel', () => window.__gc++, true); }""")
    _t0 = _pg.evaluate(_CAP); _gx, _gy = _pg.evaluate(_GRIP) or (0, 0)
    _cdp = _c.new_cdp_session(_pg)
    _cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": _gx, "y": _gy}]}); _pg.wait_for_timeout(40)
    for _k in range(1, 13):
        _cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": _gx, "y": _gy + 60 * _k / 12}]}); _pg.wait_for_timeout(16)
    _cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); _pg.wait_for_timeout(300)
    _grip = {"before": _t0, "after": _pg.evaluate(_CAP), "cancels": _pg.evaluate("() => window.__gc"),
             "sheet scrolls": _pg.evaluate("() => { const s = document.getElementById('postSheet'); return s.scrollHeight > s.clientHeight + 1; }"),
             "focus": _pg.evaluate("() => document.activeElement && document.activeElement.id")}
    _c.close()
    _psb.close()
check("TICK BOX: unticked, the gallery box is at least 3:1 against the sheet beside it, on the Pad and Flip, light and dark",
      len(_box) == 4 and all(v >= 3.0 for v in _box.values()), str(_box))
check("CAPTION: five lines written, the box eases to show them all: no line hidden, every frame between where it was and where it goes (a frame between, none outside), on the Pad and Flip",
      len(_fit) == 2 and all(v["fitted"]["hidden"] <= 1 and v["fitted"]["h"] > v["start"]["h"] + 20 and v["between"] >= 1 and not v["outside"]
                             for v in _fit.values()),
      str({k: (v["start"], v["fitted"], v["between"], v["outside"]) for k, v in _fit.items()}))
check("CAPTION GRIP: a mouse drags it 60px down and the box is 60px taller; what is typed after keeps that height; up, it stops at the three lines it started with; and the drag puts no caret in the box",
      len(_fit) == 2 and all(abs(v["dragged"]["h"] - v["fitted"]["h"] - 60) <= 2 and abs(v["typed"]["h"] - v["dragged"]["h"]) <= 1
                             and abs(v["floor"]["h"] - v["start"]["h"]) <= 1 and v["focus"] != "postCaptionInput" for v in _fit.values()),
      str({k: (v["fitted"]["h"], v["dragged"]["h"], v["typed"]["h"], v["floor"]["h"], v["focus"]) for k, v in _fit.items()}))
check("CAPTION GRIP: ...opened again, the box fits its words again; and on a phone a finger's drag moves it 60px, none of it taken by the sheet",
      len(_fit) == 2 and all(v["reopened"]["hidden"] <= 1 and abs(v["reopened"]["h"] - v["fitted"]["h"]) <= 26 for v in _fit.values())
      and _grip["sheet scrolls"] and abs(_grip["after"]["h"] - _grip["before"]["h"] - 60) <= 2 and _grip["cancels"] == 0 and _grip["focus"] != "postCaptionInput",
      f"reopened {[v['reopened'] for v in _fit.values()]}; phone {_grip}")

print("\nTHE OFF SWITCH IS A LILAC GROOVE — the on colour at a fraction, pressed in, the knob lifted; it glides")
# The owner, after v330, of the on/off switches: "If you are going to change
# it, I want subtle sophistication, simple and elegant and kind"; of the
# mock's D3, "Yes". Off was a flat grey (the wash at .16) and the knob sat on
# a tight dark shadow. Read off the pixels at 2x on a phone, light and dark:
# the track's middle, against the row beside it, leans to the on colour's
# violet (blue held up over green, where the grey moved all three alike);
# its top inside edge is darker than its middle (the groove: the darkest of
# the device rows 1 to 3px inside the top, clear of the edge's own blending,
# against the middle; one pixel at 1.5px read 1.04 on the CI's Flip, where the
# row sits at another fraction of a pixel, and failed main after #706). The knob's
# shadow is read as computed, the property it governs: a soft, wide layer and
# no tight dark one. And turned off, the groove is read on every frame from
# the click, inside the page: none when on, at least one frame part-way,
# none outside. On the Pad (the photo row) and Flip (Draw-on): one style,
# every switch.
import io as _swio
import re as _swre
from PIL import Image as _SwImg
_SW_LUM = lambda c: sum(w * ((v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4)
                        for w, v in zip((0.2126, 0.7152, 0.0722), c[:3]))
_SW_RECT = "(id) => { const r = document.getElementById(id).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
_SW_FRAMES = """(id) => new Promise(done => { const e = document.getElementById(id), out = [], t0 = performance.now();
    const first = getComputedStyle(e).boxShadow; e.click();
    (function tick() { out.push(getComputedStyle(e).boxShadow); if (performance.now() - t0 < 450) requestAnimationFrame(tick); else done([first, out]); })(); })"""
_SW_KNOB = "(id) => getComputedStyle(document.getElementById(id).querySelector('.layer-toggle-knob')).boxShadow"


def _sw_layers(s):
    """[(alpha, blur, inset)] for each layer of a computed box-shadow; [] for none."""
    out = []
    for lay in _swre.split(r",\s*(?![^()]*\))", s or "none"):
        if lay.strip() == "none":
            continue
        m = _swre.search(r"rgba?\(([^)]*)\)", lay)
        parts = [float(v) for v in _swre.findall(r"[\d.]+", m.group(1))] if m else [0, 0, 0, 0]
        lengths = [float(v) for v in _swre.findall(r"(-?[\d.]+)px", lay[m.end():] if m else lay)]
        out.append((parts[3] if len(parts) > 3 else 1.0, lengths[2] if len(lengths) > 2 else 0.0, "inset" in lay))
    return out


def _sw_groove(s):
    return max([a for a, _, inset in _sw_layers(s) if inset] or [0.0])


def _sw_png():
    _b = _swio.BytesIO(); _SwImg.new("RGB", (120, 90), (120, 170, 220)).save(_b, "PNG"); return _b.getvalue()


with _sp204() as _sw:
    _swb = waits.instrument(_sw.chromium.launch())
    _swr = {}
    for _name, _path, _id in (("Pad", "/", "photoToggle"), ("Flip", "/flip", "drawOnBtn")):
        for _th in ("light", "dark"):
            _c = _swb.new_context(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
            _pg = _c.new_page(); browsing.goto(_pg, BASE, f"{_path}?theme={_th}"); waits.settle(_pg, 500)
            _pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            if _name == "Pad":
                _pg.click("#mediaOpenBtn"); _pg.wait_for_timeout(400)
                _pg.set_input_files("#photoInput", {"name": "sky.png", "mimeType": "image/png", "buffer": _sw_png()})
                _pg.wait_for_function("() => document.getElementById('photoToggle').getAttribute('aria-checked') === 'true'", timeout=10000)
            else:
                _pg.evaluate("() => _flipDrawerCtl.open('draw')"); _pg.wait_for_timeout(500)
                _pg.click('#drawTiles .dp-tile[data-dp="feel"]'); _pg.wait_for_timeout(500)
            _pg.evaluate(f"() => document.getElementById('{_id}').scrollIntoView({{ block: 'center' }})"); _pg.wait_for_timeout(300)
            if _pg.evaluate(f"() => document.getElementById('{_id}').getAttribute('aria-checked')") != "true":
                _pg.click(f"#{_id}"); _pg.wait_for_timeout(450)                     # on first, so it can be turned off
            _first, _frames = _pg.evaluate(_SW_FRAMES, _id)
            _pg.wait_for_timeout(250)
            _r = _pg.evaluate(_SW_RECT, _id)
            _im = _SwImg.open(_swio.BytesIO(_pg.screenshot())).convert("RGB")
            _px = lambda x, y: _im.getpixel((int(round(x * 2)), int(round(y * 2))))
            _mid = _r[1] + _r[3] / 2
            _ground, _fill = _px(_r[0] + _r[2] + 4, _mid), _px(_r[0] + _r[2] - 6, _mid)
            _gx = int(round((_r[0] + 26) * 2))
            _band = [_im.getpixel((_gx, _y)) for _y in range(int(-(-(_r[1] + 1.0) * 2 // 1)), int((_r[1] + 3.0) * 2) + 1)]
            _top = min(_band, key=_SW_LUM)
            _low = _px(_r[0] + 26, _r[1] + 12.5)
            _gs = [_sw_groove(f) for f in _frames]
            _full = _gs[-1] if _gs else 0.0
            _swr[(_name, _th)] = {
                "off": _pg.evaluate(f"() => document.getElementById('{_id}').getAttribute('aria-checked')"),
                "lean": (_fill[2] - _ground[2]) - (_fill[1] - _ground[1]),
                "depth": round((_SW_LUM(_low) + 0.05) / (_SW_LUM(_top) + 0.05), 3),
                "knob": _sw_layers(_pg.evaluate(_SW_KNOB, _id)),
                "on groove": _sw_groove(_first), "full": _full,
                "part-way": sum(1 for g in _gs if 0.01 < g < _full - 0.01),
                "outside": [g for g in _gs if g < -0.001 or g > _full + 0.001],
                "px": (_ground, _fill, _top, _low)}
            _c.close()
    _swb.close()
check("OFF SWITCH: off, the track leans to the on colour's violet against the row beside it (blue over green by 10 levels and more), on the Pad and Flip, light and dark",
      len(_swr) == 4 and all(v["off"] == "false" and v["lean"] >= 10 for v in _swr.values()),
      str({k: (v["off"], v["lean"], v["px"][:2]) for k, v in _swr.items()}))
check("OFF SWITCH: ...pressed in: its top inside edge is darker than its middle, on the Pad and Flip, light and dark",
      len(_swr) == 4 and all(v["depth"] >= 1.02 for v in _swr.values()),
      str({k: (v["depth"], v["px"][2:]) for k, v in _swr.items()}))
check("OFF SWITCH: the knob sits on a soft, wide shadow (a layer blurred 5px and more), with no tight dark one (no layer at .3 and darker)",
      len(_swr) == 4 and all(any(b >= 5 for _, b, _i in v["knob"]) and all(a < 0.3 for a, _, _i in v["knob"]) for v in _swr.values()),
      str({k: v["knob"] for k, v in _swr.items()}))
check("OFF SWITCH: turned off, the groove glides in: none while on, at least one frame part-way, none outside, on the Pad and Flip, light and dark",
      len(_swr) == 4 and all(v["on groove"] == 0 and v["full"] > 0.1 and v["part-way"] >= 1 and not v["outside"] for v in _swr.values()),
      str({k: (v["on groove"], v["full"], v["part-way"], v["outside"]) for k, v in _swr.items()}))

print("\nDONE, THE DOT AND THE FIRST LINE — you can find Done, and you know you're recording")
# The owner, after v330: "It's not noticeable. I had to look around to find it
# and wasn't sure I was even recording." Done was a glass pill in the header's
# own ink, 1.15:1 against the light header and 1.18:1 against the dark: its
# words were plain, the button was not there. The mock's three, all yes: Done
# in the action's purple; the first take says so once, under Done; the dot
# breathes. Read off the pixels (the fill against the header just above it,
# the words against the fill), on a phone and a desk, light and dark; the
# line's caret against Done's middle, which on a desk is a scrollbar gutter
# away from the screen's edge (styles.css, `scrollbar-gutter: stable
# both-edges`); the halo's scale on every frame.
import io as _dio
from PIL import Image as _DImg
_DLUM = lambda c: sum(w * ((v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4)
                      for w, v in zip((0.2126, 0.7152, 0.0722), c[:3]))
_dratio = lambda a, b: (max(_DLUM(a), _DLUM(b)) + 0.05) / (min(_DLUM(a), _DLUM(b)) + 0.05)
_DONE = """() => { const d = document.getElementById('recordBtn'), R = d.getBoundingClientRect(), L = d.querySelector('.btn-label').getBoundingClientRect();
    return { box: [R.left, R.top, R.width, R.height], label: [L.left, L.top, L.width, L.height], inReadout: d.parentElement.id === 'recIndicator' }; }"""
_LINE = """() => { const h = document.querySelector('.skribl-hint'), d = document.getElementById('recordBtn');
    if (!h || h.hidden || !h.classList.contains('in')) return { shown: false };
    const H = h.getBoundingClientRect(), D = d.getBoundingClientRect(), a = getComputedStyle(h, '::after');
    const caret = H.left + parseFloat(a.left) + (parseFloat(a.width) + parseFloat(a.borderLeftWidth)) / 2;
    const at = document.elementFromPoint(D.left + D.width / 2, D.top + D.height / 2);
    return { shown: true, text: h.textContent, below: Math.round(H.top - D.bottom), caret: Math.round((caret - D.left - D.width / 2) * 10) / 10,
             inside: H.left >= 15.5 && H.right <= innerWidth - 15.5, donePainted: !!at && d.contains(at) }; }"""
_BREATH = """() => new Promise(done => { const d = document.querySelector('#recIndicator .dot'), out = [], t0 = performance.now();
    (function tick() { out.push(new DOMMatrix(getComputedStyle(d, '::before').transform).a);
      if (performance.now() - t0 < 2700) requestAnimationFrame(tick); else done(out); })(); })"""


def _stroke(pg, dy=0):
    _b = pg.locator("#canvas").bounding_box()
    pg.mouse.move(_b["x"] + 60, _b["y"] + 120 + dy); pg.mouse.down()
    pg.mouse.move(_b["x"] + 220, _b["y"] + 150 + dy, steps=16); pg.mouse.up()
    pg.wait_for_timeout(600)


with _sp204() as _dn:
    _dnb = waits.instrument(_dn.chromium.launch())
    _dres = {}
    for _dev, _vp, _kw in (("phone", {"width": 402, "height": 874}, {"is_mobile": True, "has_touch": True}),
                           ("desk", {"width": 1280, "height": 860}, {})):
        for _theme in ("light", "dark"):
            _dc = _dnb.new_context(viewport=_vp, device_scale_factor=2, **_kw)
            _dc.add_init_script("window.__skriblTakeHintForce = true;")
            _dp = _dc.new_page()
            browsing.goto(_dp, BASE, f"/?theme={_theme}")
            _dp.evaluate("() => localStorage.removeItem('skribl_hints_seen_v1')")
            _stroke(_dp)
            _first = _dp.evaluate(_LINE)
            _g = _dp.evaluate(_DONE)
            _im = _DImg.open(_dio.BytesIO(_dp.screenshot())).convert("RGB")
            _x, _y, _w, _h = _g["box"]
            _fill = _im.getpixel((int((_x + _w - 6) * 2), int((_y + _h / 2) * 2)))
            _hdr = _im.getpixel((int((_x + _w / 2) * 2), int((_y - 4) * 2)))
            _lx, _ly, _lw, _lh = _g["label"]
            _ink = max((_dratio(_im.getpixel((i, j)), _fill), _im.getpixel((i, j)))
                       for i in range(int(_lx * 2), int((_lx + _lw) * 2)) for j in range(int(_ly * 2), int((_ly + _lh) * 2)))[1]
            # The first line put away (it stays six seconds), the next stroke
            # must not bring it back.
            _dp.evaluate("() => SkriblHints.hide()"); _dp.wait_for_timeout(300)
            _stroke(_dp, 90)
            _again = _dp.evaluate(_LINE)
            _dres[(_dev, _theme)] = {"edge": round(_dratio(_fill, _hdr), 2), "words": round(_dratio(_ink, _fill), 2),
                                     "inReadout": _g["inReadout"], "first": _first, "again": _again.get("shown")}
            _dc.close()
    check("DONE STANDS OUT: while a take records, Done's fill is at least 3:1 against the header and its words at least 4.5:1 on it, on a phone and a desk, light and dark",
          len(_dres) == 4 and all(v["inReadout"] and v["edge"] >= 3.0 and v["words"] >= 4.5 for v in _dres.values()),
          str({k: (v["edge"], v["words"]) for k, v in _dres.items()}))
    _want = {"phone": "You’re recording. Tap Done when you’re finished.", "desk": "You’re recording. Click Done when you’re finished."}
    check("FIRST LINE: the first stroke of the first take hangs the line under Done (Tap on a phone, Click on a desk), 10-14px below it, its caret within 1px of Done's middle, inside the screen's 16px margins, Done still painted",
          len(_dres) == 4 and all(v["first"].get("shown") and v["first"]["text"] == _want[k[0]] and 10 <= v["first"]["below"] <= 14
                                  and abs(v["first"]["caret"]) <= 1 and v["first"]["inside"] and v["first"]["donePainted"]
                                  for k, v in _dres.items()),
          str({k: v["first"] for k, v in _dres.items()}))
    check("FIRST LINE: ...once: the next stroke brings nothing",
          len(_dres) == 4 and not any(v["again"] for v in _dres.values()), str({k: v["again"] for k, v in _dres.items()}))
    # Done puts it away (it spoke of a take that has ended); and a suite that
    # does not ask never meets it.
    _dc = _dnb.new_context(viewport={"width": 1280, "height": 860})
    _dc.add_init_script("window.__skriblTakeHintForce = true;")
    _dp = _dc.new_page(); browsing.goto(_dp, BASE, "/")
    _dp.evaluate("() => localStorage.removeItem('skribl_hints_seen_v1')")
    _stroke(_dp)
    _up = _dp.evaluate(_LINE)["shown"]
    _dp.click("#recordBtn"); _dp.wait_for_timeout(450)
    _gone = not _dp.evaluate(_LINE)["shown"]
    _dc.close()
    _dc = _dnb.new_context(viewport={"width": 1280, "height": 860})
    _dp = _dc.new_page(); browsing.goto(_dp, BASE, "/")
    _dp.evaluate("() => localStorage.removeItem('skribl_hints_seen_v1')")
    _stroke(_dp)
    _quiet = not _dp.evaluate(_LINE)["shown"]
    _dc.close()
    check("FIRST LINE: Done puts it away, and automation that does not ask (window.__skriblTakeHintForce) never meets it",
          _up and _gone and _quiet, f"up {_up}, gone after Done {_gone}, quiet unasked {_quiet}")
    # The dot breathes, and holds still under Reduce Motion.
    _breath = {}
    for _rm in ("no-preference", "reduce"):
        _dc = _dnb.new_context(viewport={"width": 402, "height": 874}, reduced_motion=_rm)
        _dp = _dc.new_page(); browsing.goto(_dp, BASE, "/")
        _stroke(_dp)
        _s = _dp.evaluate(_BREATH)
        _breath[_rm] = {"min": round(min(_s), 3), "max": round(max(_s), 3), "step": round(max(abs(a - b) for a, b in zip(_s, _s[1:])), 4), "frames": len(_s)}
        _dc.close()
    _dnb.close()
_bm = _breath["no-preference"]
check("THE DOT BREATHES: while a take records its halo swells and settles (scale 0.64 to 1 in 2.4s, read every frame, no step over 0.03)",
      _bm["min"] <= 0.66 and _bm["max"] >= 0.98 and _bm["step"] <= 0.03 and _bm["frames"] >= 60, str(_bm))
check("THE DOT BREATHES: ...and under Reduce Motion it holds still, a 4px ring",
      _breath["reduce"]["max"] - _breath["reduce"]["min"] < 0.001 and abs(_breath["reduce"]["max"] - 0.727) < 0.01, str(_breath["reduce"]))

print("\nREADOUT ALIGNMENT — the dot, bars, clock, plays and Done share one line, in any font")
# A centred line box centres the font's ascent and descent, not the digits,
# and fonts split those differently: a 1px nudge tuned here in Liberation
# Sans put the clock visibly LOW on the owner's Windows machine (Segoe UI).
# The cure (text-box: trim-both cap alphabetic) is font-independent, so it is
# asserted in more than one font: each installed face is forced onto the
# readout and the INK is measured (a box says where text could be, not where
# its glyphs are). Every part's ink centre must sit within 1px of the dot's.
import io as _io
from PIL import Image as _Img
with _sp204() as _al:
    _alb = waits.instrument(_al.chromium.launch())
    _alp = _alb.new_page(viewport={"width": 1280, "height": 860}, device_scale_factor=2)
    browsing.goto(_alp, BASE, "/")
    _alp.evaluate("() => localStorage.clear()")
    _alp.reload(wait_until="load"); waits.settle(_alp, 700)
    draw(_alp, "#canvas", 120, 120, n=18); _alp.wait_for_timeout(600)
    _alp.evaluate("""() => { clearInterval(recTimerInterval); document.getElementById('recTimer').textContent = '0:05';
        document.getElementById('recPlays').textContent = 'plays 2:33'; }""")
    _faces = _alp.evaluate("""() => ['DejaVu Sans', 'Liberation Sans', 'FreeSans'].filter(f => {
        const c = document.createElement('canvas').getContext('2d'), t = 'plays 0:05 Done';
        c.font = '40px monospace'; const a = c.measureText(t).width;
        c.font = '40px "' + f + '", monospace'; return Math.abs(c.measureText(t).width - a) > 0.5; })""")
    _align = {}
    for _f in _faces:
        _alp.evaluate("""f => { let s = document.getElementById('alignFace'); if (!s) { s = document.createElement('style');
            s.id = 'alignFace'; document.head.appendChild(s); } s.textContent = '.rec-indicator, .rec-indicator * { font-family: "' + f + '", sans-serif !important; }'; }""", _f)
        _alp.wait_for_timeout(250)
        _r = _alp.evaluate("() => { const e = document.getElementById('recIndicator').getBoundingClientRect(); return [e.left, e.top, e.width, e.height]; }")
        _im = _Img.open(_io.BytesIO(_alp.screenshot(clip={"x": _r[0], "y": _r[1] - 8, "width": _r[2], "height": _r[3] + 16}))).convert("RGB")
        _parts = _alp.evaluate("""() => { const o = document.getElementById('recIndicator').getBoundingClientRect();
            return ['.rec-indicator .dot', '.rec-bars', '#recTimer', '#recPlays', '#recordBtn .btn-label'].map(s => {
              const q = document.querySelector(s).getBoundingClientRect();
              // "plays" is measured on its digits: the p and y descend by design
              return s === '#recPlays' ? [q.right - o.left - q.width * 0.38, q.right - o.left] : [q.left - o.left, q.right - o.left]; }); }""")
        _bg = _im.getpixel((1, 1)); _c = []
        # Done's words are read against Done's own fill, inside the pill: since
        # Done wears the action's purple (after v330) the whole pill differs
        # from the header, and against the header's ground this measured the
        # pill's middle, not the words.
        _pill = _alp.evaluate("""() => { const o = document.getElementById('recIndicator').getBoundingClientRect(),
            R = document.getElementById('recordBtn').getBoundingClientRect(); return [R.right - o.left - 6, R.top - o.top + 8, R.bottom - o.top + 8]; }""")
        _pfill = _im.getpixel((int(_pill[0] * 2), int((_pill[1] + _pill[2]) * 0.5 * 2)))
        for _i, (_x0, _x1) in enumerate(_parts):
            _ref, _rows = (_pfill, range(int(_pill[1] * 2) + 3, int(_pill[2] * 2) - 3)) if _i == 4 else (_bg, range(_im.height))
            _ys = [y for y in _rows if any(sum(abs(a - b) for a, b in zip(_im.getpixel((x, y)), _ref)) > 150
                                           for x in range(int(_x0 * 2) + 1, int(_x1 * 2) - 1))]
            _c.append((min(_ys) + max(_ys)) / 4 if _ys else None)
        _align[_f] = {k: (round(v - _c[0], 2) if v is not None else None) for k, v in zip(["dot", "bars", "clock", "plays", "done"], _c)}
    _alp.close(); _alb.close()
check("READOUT ALIGNMENT: at least one face beyond the default was available to force (fixture)",
      len(_faces) >= 1, f"faces found: {_faces}")
_off = {f: {k: v for k, v in d.items() if k != "dot" and (v is None or abs(v) > 1.0)} for f, d in _align.items()}
check("READOUT ALIGNMENT: in every face, each part's ink centre is within 1px of the dot's",
      _align and not any(_off.values()), str(_align))

print("\nWORDS IN THE MIDDLE — a button's capitals sit in its middle, in any font (lib/labels.js)")
# The owner: "Make your first Skribl doesn't look centered vertically", then
# "if this happened here, it happened all over?" It had: a flex-centred button
# centres its label's line box, and where the capitals sit in that box is the
# font's business. lib/labels.js gives each label its own span and styles.css
# .lbl trims it to cap height and baseline, padding back the line it took.
# Asserted on the INK of the first capital, in each installed face, against
# the button's own box: Flip's Duplicate and Blank (a word alone), Pad's Post
# (a mark and a word). And no control changes size: every .lbl is exactly one
# line tall.
with _sp204() as _wm:
    _wmb = waits.instrument(_wm.chromium.launch())
    _wmres, _wmlh = {}, {}
    for _path, _sels in (("/flip", ["#addcopy", "#addblank"]), ("/", ["#postBtn"])):
        _wmp = _wmb.new_page(viewport={"width": 1280, "height": 860}, device_scale_factor=3)
        browsing.goto(_wmp, BASE, _path); waits.settle(_wmp, 700)
        if _path == "/":
            draw(_wmp, "#canvas", 120, 120, n=18); _wmp.wait_for_timeout(400)
            _wmp.click("#recordBtn"); _wmp.wait_for_timeout(600)
        _wmlh[_path] = _wmp.evaluate("""() => [...document.querySelectorAll('.lbl')].filter(e => e.offsetWidth)
            .map(e => { const c = getComputedStyle(e); return Math.abs(e.getBoundingClientRect().height - parseFloat(c.lineHeight)) < 0.6
                || c.lineHeight === 'normal'; })""")
        for _f in _faces:
            _wmp.evaluate("""f => { let s = document.getElementById('wmFace'); if (!s) { s = document.createElement('style');
                s.id = 'wmFace'; document.head.appendChild(s); } s.textContent = 'button, button * { font-family: "' + f + '", sans-serif !important; }'; }""", _f)
            _wmp.wait_for_timeout(250)
            for _sel in _sels:
                _el = _wmp.locator(_sel)
                _geo = _wmp.evaluate("""(s) => { const e = document.querySelector(s), r = e.getBoundingClientRect(),
                    w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
                    for (let t; (t = w.nextNode());) { const i = t.nodeValue.search(/\\S/); if (i < 0) continue;
                      const g = document.createRange(); g.setStart(t, i); g.setEnd(t, i + 1); const q = g.getBoundingClientRect();
                      return [q.left - r.left, q.right - r.left, r.height]; } return null; }""", _sel)
                _full = _Img.open(_io.BytesIO(_el.screenshot())).convert("L")
                _wmp.evaluate("(s) => { const e = document.querySelector(s); [e, ...e.querySelectorAll('*')].forEach(c => c.style.color = 'transparent'); }", _sel)
                _plate = _Img.open(_io.BytesIO(_el.screenshot())).convert("L")
                _wmp.evaluate("(s) => { const e = document.querySelector(s); [e, ...e.querySelectorAll('*')].forEach(c => c.style.color = ''); }", _sel)
                _ys = [y for y in range(_full.height) if any(abs(_full.getpixel((x, y)) - _plate.getpixel((x, y))) > 60
                                                            for x in range(int(_geo[0] * 3) + 1, int(_geo[1] * 3) - 1))]
                _wmres[(_sel, _f)] = round((min(_ys) + max(_ys) + 1) / 6 - _geo[2] / 2, 2) if _ys else None
        _wmp.close()
    _wmb.close()
check("WORDS IN THE MIDDLE: in every face, the first capital of Duplicate, Blank and Post is within half a pixel of its button's middle",
      _wmres and all(v is not None and abs(v) <= 0.5 for v in _wmres.values()), str(_wmres))
check("WORDS IN THE MIDDLE: ...and no control changed size for it: every label span is exactly one line tall, on Pad and Flip",
      all(len(v) >= 3 and all(v) for v in _wmlh.values()), str(_wmlh))

print("\nHEADER ORDER — the take's controls, then settings and the menu; Done beside the readout")
# Owner's layout B. After a take the header reads Play, Post, then settings
# and the menu as a pair; while a take records, Done moves to sit beside the
# readout (the readout and the control that ends it are one unit) and goes
# home when the take ends. Done must still RECEDE while the pen is down --
# it now lives inside the readout, which is the one thing that stays lit.
with _sp204() as _ho:
    _hob = waits.instrument(_ho.chromium.launch())
    _hop = _hob.new_page(viewport={"width": 1280, "height": 860})
    browsing.goto(_hop, BASE, "/")
    _hop.evaluate("() => localStorage.clear()")
    _hop.reload(wait_until="load"); waits.settle(_hop, 700)
    draw(_hop, "#canvas", 120, 120, n=18); _hop.wait_for_timeout(400)
    _HO = """() => { const d = document.getElementById('recordBtn'), t = document.getElementById('recTimer');
        const eff = el => { let o = 1; for (; el; el = el.parentElement) o *= +getComputedStyle(el).opacity; return o; };
        const dr = d.getBoundingClientRect(), tr = t.getBoundingClientRect();
        return { inReadout: d.parentElement.id, doneRight: Math.round(dr.left - tr.right), done: eff(d),
                 order: [...document.getElementById('actions').children].filter(e => !e.hidden && e.offsetWidth).map(e => e.id) }; }"""
    _rec = _hop.evaluate(_HO)
    _cb = _hop.locator("#canvas").bounding_box()
    _hop.mouse.move(_cb["x"] + 60, _cb["y"] + 60); _hop.mouse.down()
    _hop.mouse.move(_cb["x"] + 160, _cb["y"] + 140, steps=20); _hop.wait_for_timeout(700)
    _pen = _hop.evaluate(_HO)
    _hop.mouse.up(); _hop.wait_for_timeout(300)
    _hop.click("#recordBtn"); _hop.wait_for_timeout(600)
    _take = _hop.evaluate("""() => ({ home: document.getElementById('recordBtn').parentElement.id,
        order: [...document.getElementById('actions').children].filter(e => !e.hidden && e.offsetWidth).map(e => e.id) })""")
    _lab = _hop.evaluate("""() => [...document.querySelectorAll('.toolbar .tool-btn-label')].filter(e => e.offsetWidth)
        .map(e => getComputedStyle(e).textShadow)""")
    _hop.close(); _hob.close()
check("HEADER: while recording, Done sits inside the readout, just right of the clock",
      _rec["inReadout"] == "recIndicator" and 0 <= _rec["doneRight"] <= 140, str(_rec))
check("HEADER: while the pen is down, Done recedes with the header (the readout around it stays lit)",
      _pen["done"] < 0.5, str(_pen))
check("HEADER: after the take, Record goes home and the header reads Play, Post, settings, menu",
      _take["home"] == "actions" and _take["order"] == ["playWrap", "postBtn", "tuneBtn", "menuBtn"], str(_take))
check("DOCK LABELS: each wears the hard 1px edge (owner's row 3)",
      len(_lab) >= 3 and all(t and t != "none" and "0px 1px 0px" in t for t in _lab), str(_lab))

print("\nPHONE RECORDING HEADER — the take is centred, and the header comes back after Done")
# On a phone, recording puts away the mark, settings and the menu, so the
# readout and Done are the whole header. They sat against the left edge;
# owner: "if you're removing the branding, then center it". Measured as the
# space either side of the readout inside the header, at two phone widths.
with _sp204() as _pc:
    _pcb = waits.instrument(_pc.chromium.launch())
    _pcr = {}
    for _w in (320, 390):
        _pcx = _pcb.new_context(viewport={"width": _w, "height": 844}, has_touch=True, is_mobile=True)
        _pcp = _pcx.new_page()
        browsing.goto(_pcp, BASE, "/")
        _pcp.evaluate("() => localStorage.clear()")
        _pcp.reload(wait_until="load"); waits.settle(_pcp, 700)
        draw(_pcp, "#canvas", 60, 80, n=18); _pcp.wait_for_timeout(500)
        _m = _pcp.evaluate("""() => { const h = document.querySelector('.header').getBoundingClientRect(),
              r = document.getElementById('recIndicator').getBoundingClientRect();
              return { left: Math.round(r.left - h.left), right: Math.round(h.right - r.right), inside: r.left >= h.left && r.right <= h.right }; }""")
        _pcp.click("#recordBtn"); _pcp.wait_for_timeout(600)
        _m["after"] = _pcp.evaluate("""() => ({ brand: getComputedStyle(document.querySelector('.header > .brand')).display,
              actions: getComputedStyle(document.getElementById('actions')).display })""")
        _pcr[_w] = _m
        _pcx.close()
    _pcb.close()
check("PHONE RECORDING HEADER: the readout and Done sit centred in the header (320 and 390)",
      all(m["inside"] and abs(m["left"] - m["right"]) <= 2 for m in _pcr.values()), str(_pcr))
check("PHONE RECORDING HEADER: after Done, the mark and the controls are back",
      all(m["after"]["brand"] != "none" and m["after"]["actions"] != "none" for m in _pcr.values()), str(_pcr))

print("\nSEG PILLS — every visible segmented control shows its selection, on both editors")
# The tune drawer's Mirror, Pauses and Preview speed (and Flip's Mirror and
# smear weight) showed their selection by label colour alone: lib/segslider.js
# had trackAll() and nothing called it, so a group got its pill only if a
# surface remembered to track it by name. Owner, on the phone: "not bright
# enough to tell what's selected". For every seg on screen with a selected
# option, the pill's computed opacity is 1 and it spans that option, centred
# under it. (The pill sits BEHIND the label, so a hit-test would find the
# button either way; opacity plus geometry is the property the bug removed --
# the old pill was there, 0 wide and 0 opaque.) Red on the tree before
# trackAll() was called: Pad mirror/pause/speed (speed has since moved to
# the replay's line), Flip mirror/smear weight.
with _sp204() as _sg:
    _sgb = waits.instrument(_sg.chromium.launch())
    for _route in ("/", "/flip"):
        _sgp = _sgb.new_page(viewport={"width": 402, "height": 874})
        browsing.goto(_sgp, BASE, _route)
        _sgp.evaluate("() => document.getElementById('tuneBtn').click()")
        _sgp.wait_for_timeout(900)
        _sgr = _sgp.evaluate("""() => [...document.querySelectorAll('#tunePanel .seg')].filter(g => {
              const r = g.getBoundingClientRect(); return r.width > 0 && r.height > 0 && g.querySelector('button.on');
            }).map(g => { const pill = g.querySelector('.seg-slider'), on = g.querySelector('button.on');
              const pr = pill ? pill.getBoundingClientRect() : null, br = on.getBoundingClientRect();
              return { id: g.id, opacity: pill ? +getComputedStyle(pill).opacity : 0,
                       w: pr ? Math.round(pr.width) : 0, bw: Math.round(br.width),
                       under: pr ? Math.abs((pr.left + pr.width / 2) - (br.left + br.width / 2)) < 3 : false }; })""")
        _bad = [g for g in _sgr if not (g["opacity"] > 0.9 and g["w"] >= g["bw"] - 1 and g["under"])]
        # A floor of 2, not 3: Pad's tune drawer lost its third seg (Preview
        # speed) to the line under the replay at the owner's replay picks.
        check(f"SEG PILLS {_route}: the tune drawer's segs each paint a pill under the selected option",
              len(_sgr) >= 2 and not _bad, f"{len(_sgr)} segs; missing/misplaced: {_bad}")
        _sgp.close()
    _sgb.close()

print("\nSEG PILLS — the selection is painted even where the pill script never lands")
# The pill is placed by lib/segslider.js measuring a laid-out button. On the
# owner's iPhone the tune drawer still showed the selection by label colour
# alone after the pill fix merged, and no engine here reproduces it. So the
# selected option paints the tint ITSELF until the script confirms the pill
# (data-pill on the group). Driven by blocking the script outright -- the
# failure it guards against -- and asserted on the computed fill of the
# selected option. And the converse: where the pill IS placed the option is
# transparent, or the tint would double.
def _seg_fill(page):
    return page.evaluate("""() => [...document.querySelectorAll('#tunePanel .seg')].filter(g => {
          const r = g.getBoundingClientRect(); return r.width > 0 && r.height > 0 && g.querySelector('button.on');
        }).map(g => { const bg = getComputedStyle(g.querySelector('button.on')).backgroundColor;
          const m = bg.match(/rgba?\\(([^)]+)\\)/), a = m ? (m[1].split(',')[3] === undefined ? 1 : +m[1].split(',')[3]) : 0;
          return { id: g.id, pill: g.hasAttribute('data-pill'), alpha: a }; })""")
with _sp204() as _sf:
    _sfb = waits.instrument(_sf.chromium.launch())
    _sfp = _sfb.new_page(viewport={"width": 402, "height": 874})
    # Matched as a regex: the asset URL carries a content-hash query
    # (segslider.js?v=...), which a glob ending in .js does not match -- the
    # first draft "blocked" nothing and read the placed pill as the fallback.
    _sfp.route(_re.compile(r"/lib/segslider\.js(\?|$)"), lambda r: r.abort())
    browsing.goto(_sfp, BASE, "/", require_boot=False)
    _sfp.evaluate("() => document.getElementById('tuneBtn').click()")
    _sfp.wait_for_timeout(900)
    _nojs = _seg_fill(_sfp)
    check("SEG FALLBACK: with the pill script blocked, every visible tune seg still paints its selected option",
          len(_nojs) >= 2 and all(g["alpha"] > 0.05 and not g["pill"] for g in _nojs), str(_nojs))
    _sfp.close()
    _sfp = _sfb.new_page(viewport={"width": 402, "height": 874})
    browsing.goto(_sfp, BASE, "/")
    _sfp.evaluate("() => document.getElementById('tuneBtn').click()")
    _sfp.wait_for_timeout(900)
    _js = _seg_fill(_sfp)
    check("SEG FALLBACK: with the pill placed, the option itself is transparent (no doubled tint)",
          len(_js) >= 2 and all(g["pill"] and g["alpha"] == 0 for g in _js), str(_js))
    _sfp.close(); _sfb.close()

print("\nPHOTO FIT PILL — Fill / Fit / Stretch shows its selection after a draft restore")
# Owner, desktop: "Fit" selected in the photo drawer, no highlight under it.
# The fit control's pill was sized once -- on a pick, a reset, a restore --
# and a draft restored with the drawer shut sized it to 0px; opening the
# drawer never corrected it. Driven down that exact path: pick a photo, choose
# Fit, draw, reload (the draft restores the photo with the drawer shut), open
# the drawer. Then the CSS fallback: with lib/segslider.js blocked the
# selected option still paints its own tint.
_fit_png = _io.BytesIO(); _Img.new("RGB", (400, 300), (40, 60, 90)).save(_fit_png, "PNG")
_FITQ = """() => { const g = document.getElementById('photoFitGroup'), s = document.getElementById('photoFitSlider'), a = g.querySelector('button.active');
    const sr = s.getBoundingClientRect(), ar = a.getBoundingClientRect();
    return { active: a.textContent.trim(), pillW: Math.round(sr.width), btnW: Math.round(ar.width),
             under: Math.abs((sr.left + sr.width / 2) - (ar.left + ar.width / 2)) < 3, bg: getComputedStyle(a).backgroundColor }; }"""
with _sp204() as _ft:
    _ftb = waits.instrument(_ft.chromium.launch())
    _ftp = _ftb.new_page(viewport={"width": 1400, "height": 900})
    browsing.goto(_ftp, BASE, "/")
    _ftp.evaluate("() => localStorage.clear()")
    _ftp.reload(wait_until="load"); waits.settle(_ftp, 700)
    browsing.pad_drawer(_ftp, "photo")
    _ftp.set_input_files("#photoInput", files=[{"name": "fit.png", "mimeType": "image/png", "buffer": _fit_png.getvalue()}])
    _ftp.wait_for_timeout(1000)
    _ftp.click('.photo-fit-btn[data-fit="contain"]'); _ftp.wait_for_timeout(300)
    browsing.pad_drawer_close(_ftp)
    draw(_ftp, "#canvas", 120, 120, n=18); _ftp.wait_for_timeout(2500)
    _ftp.reload(wait_until="load"); waits.settle(_ftp, 2500)
    browsing.pad_drawer(_ftp, "photo"); _ftp.wait_for_timeout(600)
    _fit_restored = _ftp.evaluate(_FITQ)
    _ftp.close()
    _ftp = _ftb.new_page(viewport={"width": 1400, "height": 900})
    _ftp.route(_re.compile(r"/lib/segslider\.js(\?|$)"), lambda r: r.abort())
    browsing.goto(_ftp, BASE, "/", require_boot=False)
    _ftp.evaluate("() => localStorage.clear()")
    _ftp.reload(wait_until="load"); waits.settle(_ftp, 700)
    browsing.pad_drawer(_ftp, "photo")
    _ftp.set_input_files("#photoInput", files=[{"name": "fit.png", "mimeType": "image/png", "buffer": _fit_png.getvalue()}])
    _ftp.wait_for_timeout(1000)
    _ftp.evaluate("() => { const s = document.getElementById('photoFitSlider'); s.style.width = '0'; }")   # the one-shot sizing lost, as on a restore
    _ftp.wait_for_timeout(200)
    _fit_nojs = _ftp.evaluate(_FITQ)
    _ftp.close(); _ftb.close()
check("PHOTO FIT PILL: after a draft restore the selected option's pill spans it and sits under it",
      _fit_restored["active"] == "Fit" and abs(_fit_restored["pillW"] - _fit_restored["btnW"]) <= 1 and _fit_restored["under"],
      str(_fit_restored))
check("PHOTO FIT PILL: with the pill script blocked, the selected option paints its own tint",
      _fit_nojs["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), str(_fit_nojs))

print("\nCLEAR ALL — arming is announced, does not race a timer, and Flip's menu clears through the action")
# Outside review of v291, SK-AUD-018/019. The two-tap arm relabelled the item
# and disarmed on a 3-second timer: a screen reader heard nothing change, and
# a slow second tap met a disarmed button and armed it again — a destructive
# action behind a race. And Flip's menu item executed by dispatching TWO
# synthetic clicks at the drawer's Clear button, riding its confirmation
# state to reach its backup+undo. Now: the armed label is written to a live
# region; the arm holds until the person leaves it (menu closed, focus gone,
# a long safety net) rather than for three seconds; and both Flip controls
# call one clearAllPages() after their own confirmation.
with _sp() as _cp:
    _cb = waits.instrument(_cp.chromium.launch())
    for _path, _name, _item in (("/", "Pad", "#clearMenuItem"), ("/flip", "Flip", "#miClearAll")):
        _pg = _cb.new_page(viewport={"width": 1100, "height": 900})
        browsing.goto(_pg, BASE, _path)
        waits.settle(_pg, 600)
        if _path == "/flip":
            draw(_pg, "#pad", 200, 200, n=16)
            _pg.evaluate("() => addFrame(true)")
            _pg.wait_for_timeout(300)
            _pg.evaluate("() => { window.__cbClicks = 0; document.getElementById('clear').addEventListener('click', () => window.__cbClicks++); }")
        else:
            # Drawing auto-starts a take and Clear all is disabled mid-take; Stop first.
            draw(_pg, "#canvas", 200, 200, n=16)
            _pg.wait_for_timeout(300)
            _pg.click("#recordBtn")
            _pg.wait_for_timeout(500)
        # THE QUESTION IS A PAGE NOW (after v323): New opens New Skribl, the
        # shape and a Start button, and nothing is cleared until Start. Focus
        # goes to the page (its Back), so a screen reader is told where it is.
        _pg.click("#menuBtn" if _path == "/" else "#moreBtn")
        _pg.wait_for_timeout(500)
        _pg.click("#menuNewTile")
        _pg.wait_for_timeout(300)
        _asked = _pg.evaluate("""() => ({ page: SkriblMenuPages.current(),
          focus: document.activeElement && document.activeElement.getAttribute('aria-label'),
          content: typeof hasContent !== 'undefined' ? hasContent : frames[0].strokes.length > 0 })""")
        check(f"CLEAR ALL ({_name}): New asks first, on its own page, focus there, nothing cleared",
              _asked["page"] == "new" and _asked["focus"] == "Back" and _asked["content"], str(_asked))
        _pg.wait_for_timeout(3600)
        _still = _pg.evaluate("() => SkriblMenuPages.current()")
        check(f"CLEAR ALL ({_name}): the question does not expire under the person's finger", _still == "new",
              f"page {_still} after 3.6 s")
        _pg.click(_item)
        _pg.wait_for_timeout(600)
        if _path == "/flip":
            _after = _pg.evaluate("() => ({ frames: frames.length, strokes: frames[0].strokes.length, undo: !document.getElementById('clearUndo').disabled, cbClicks: window.__cbClicks })")
            check(f"CLEAR ALL ({_name}): Start clears every page and offers Undo",
                  _after["frames"] == 1 and _after["strokes"] == 0 and _after["undo"], str(_after))
            check(f"CLEAR ALL ({_name}): ...through the shared action, not by clicking the drawer's button for it",
                  _after["cbClicks"] == 0, f"{_after['cbClicks']} synthetic clicks on #clear")
        else:
            _after = _pg.evaluate("() => ({ content: typeof hasContent !== 'undefined' ? hasContent : null })")
            check(f"CLEAR ALL ({_name}): Start clears the drawing", _after["content"] is False, str(_after))
        _pg.close()
    _cb.close()

print("\nNEW SKRIBL TAKES THE PHOTO AND MUSIC TOO (Flip), and Clear all pages says what it keeps")
# After v320, from the owner's screen: a page whose picture was the background PHOTO
# could not be cleared at all. Both controls judged "empty" by strokes alone, so
# the drawer's Clear did nothing and the menu said "Already a fresh one", and the
# photo rode every reload. The Pad's New Skribl has always taken media; Flip's
# now does too, Undo brings the whole document back, and the drawer's Clear --
# which keeps media by design -- says so instead of doing nothing.
# Measured as PAINT on the canvas, because the owner's complaint was the canvas.
_PHOTO = """() => { const c = document.createElement('canvas'); c.width = 816; c.height = 612; const x = c.getContext('2d');
  x.fillStyle = '#0d0f14'; x.fillRect(0, 0, 816, 612); x.strokeStyle = '#fff'; x.lineWidth = 12;
  x.beginPath(); x.moveTo(100, 100); x.bezierCurveTo(300, 500, 500, 0, 700, 400); x.stroke();
  setBgImage(c.toDataURL('image/png')); }"""
# A real (silent) WAV, so the track decodes the way a picked one does.
_TRACK = """() => { const n = 8000, b = new ArrayBuffer(44 + n * 2), v = new DataView(b);
  const w = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, 8000, true); v.setUint32(28, 16000, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true);
  let s = ''; new Uint8Array(b).forEach(c => s += String.fromCharCode(c)); setMusic('data:audio/wav;base64,' + btoa(s)); }"""
_WHITE = """() => { const cv = document.getElementById('pad'); const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
  let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 200 && d[i + 1] > 200 && d[i + 2] > 200) n++; return n; }"""
_DOC = "() => ({ pages: frames.length, strokes: frames[0].strokes.length, photo: bgImage ? bgImage.length : 0, music: musicData ? musicData.length : 0 })"
with _sp() as _np:
    _nb = waits.instrument(_np.chromium.launch())
    _pg = _nb.new_page(viewport={"width": 1100, "height": 900}, color_scheme="dark")
    browsing.goto(_pg, BASE, "/flip")
    waits.settle(_pg, 600)
    _pg.evaluate("() => window.SkriblHints && SkriblHints.hide()")
    _pg.evaluate(_PHOTO)
    _pg.wait_for_timeout(600)
    _ink0 = _pg.evaluate(_WHITE)
    # The drawer's Clear all pages keeps the photo -- and now says so.
    browsing.pad_drawer(_pg, "draw", settle=600)
    _pg.click("#clear")
    _pg.wait_for_timeout(200)
    _said = _pg.evaluate("() => document.getElementById('flipChip').textContent")
    check("NEW SKRIBL: Clear all pages on a photo-only page says the photo is what is left, instead of doing nothing",
          "photo" in _said and "Photo and music" in _said and _pg.evaluate("() => !!bgImage"), repr(_said))
    _pg.keyboard.press("Escape")
    _pg.wait_for_timeout(300)
    # The owner's page: New Skribl, through the real menu: New, then Start.
    _pg.click("#moreBtn")
    _pg.wait_for_timeout(400)
    _pg.click("#menuNewTile")
    _pg.wait_for_timeout(300)
    _pg.click("#miClearAll")
    _pg.wait_for_timeout(600)
    _fresh = _pg.evaluate("() => document.getElementById('flipChip').textContent")
    _ink1 = _pg.evaluate(_WHITE)
    check("NEW SKRIBL: on a page whose picture is the photo, New Skribl clears the canvas (not 'Already a fresh one')",
          _ink0 > 2000 and _ink1 == 0 and _pg.evaluate("() => !bgImage") and "fresh one" not in _fresh,
          f"white px {_ink0} -> {_ink1}, chip {_fresh!r}, photo left {_pg.evaluate('() => !!bgImage')}")
    # Strokes, photo and music together; all three go, and Undo brings all three back.
    draw(_pg, "#pad", 200, 200, n=16)
    _pg.evaluate(_PHOTO)
    _pg.evaluate(_TRACK)
    _pg.wait_for_timeout(800)
    _before = _pg.evaluate(_DOC)
    _pg.click("#moreBtn")
    _pg.wait_for_timeout(400)
    _pg.click("#menuNewTile")
    _pg.wait_for_timeout(300)
    _pg.click("#miClearAll")
    _pg.wait_for_timeout(600)
    _cleared = _pg.evaluate(_DOC)
    check("NEW SKRIBL: pages, photo and music all go, as on the Pad",
          _before["strokes"] > 0 and _before["photo"] > 0 and _before["music"] > 0
          and _cleared == {"pages": 1, "strokes": 0, "photo": 0, "music": 0}, f"{_before} -> {_cleared}")
    _pg.evaluate("() => document.getElementById('clearUndo').click()")
    _pg.wait_for_timeout(800)
    _back = _pg.evaluate(_DOC)
    check("NEW SKRIBL: Undo brings the pages, the photo and the music back", _back == _before, f"{_before} -> {_back}")
    _nb.close()

print("\nSHARE — on a device with a share sheet, Send it is a Share button; Copy link stays")
# Outside review of v291, SK-AUD-016. The product's thesis is "Make it. Send
# it." and the post result ended at Copy link — a clipboard step and a manual
# switch to wherever the link was going. Where navigator.share exists (every
# phone, Safari on the Mac) the result offers Share, which opens the system
# sheet with the title and the link; where it does not, the button is not
# there and Copy link is what it always was. navigator.share is stubbed in the
# page and its argument read back: the mechanism is the call, with the URL
# the page shows.
with _sp() as _sh:
    _shb = waits.instrument(_sh.chromium.launch())
    for _path, _name, _btn in (("/flip", "Flip", "#postShareBtn"), ("/", "Pad", "#postShareBtn")):
        for _has in (True, False):
            _ctx = _shb.new_context(viewport={"width": 1100, "height": 900})
            if _has:
                _ctx.add_init_script("""Object.defineProperty(navigator, 'share', { configurable: true,
                    value: async (d) => { window.__shared = d; } });""")
            else:
                _ctx.add_init_script("""Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });""")
            _pg = _ctx.new_page()
            browsing.goto(_pg, BASE, _path)
            waits.settle(_pg, 600)
            if _path == "/flip":
                draw(_pg, "#pad", 200, 200, n=16)
                _pg.wait_for_timeout(300)
                _pg.click("#postBtn")
                _pg.wait_for_timeout(400)
                _pg.fill("#postTitleInput", "Share probe")
                _pg.click("#postSubmitBtn")
                try:
                    _pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
                except Exception:                                    # noqa: BLE001
                    check(f"SHARE ({_name}): with navigator.share the result offers Share" if _has else
                          f"SHARE ({_name}): without navigator.share there is no Share button",
                          False, "no result row after posting")
                    _ctx.close()
                    continue
                _pg.wait_for_timeout(500)
                _url = _pg.evaluate("() => { const u = (SkriblPosted.list()[0] || {}).url || ''; return u ? new URL(u, location.href).href : ''; }")
            else:
                draw(_pg, "#canvas", 200, 200, n=16)
                _pg.wait_for_timeout(300)
                _pg.click("#recordBtn")
                _pg.wait_for_timeout(500)
                _pg.click("#postBtn")
                _pg.wait_for_timeout(800)
                _pg.fill("#postTitleInput", "Share probe")
                _pg.click("#postSubmitBtn")
                _pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
                _pg.wait_for_timeout(400)
                _url = None
            _vis = _pg.evaluate(f"() => {{ const b = document.querySelector('{_btn}'); return b ? (!b.hidden && getComputedStyle(b).display !== 'none') : null; }}")
            _copy = _pg.evaluate("() => { const c = document.getElementById('postCopyBtn'); return c ? !c.hidden : null; }") if _path == "/flip" else True
            if _has:
                check(f"SHARE ({_name}): with navigator.share the result offers Share", _vis is True, f"visible={_vis}")
                if _vis:
                    _pg.click(_btn)
                    _pg.wait_for_timeout(300)
                    _d = _pg.evaluate("() => window.__shared || null")
                    _ok = _d and isinstance(_d.get("url"), str) and "/s/" in _d["url"] and (not _url or _d["url"] == _url) and (_d.get("title") or "").strip() != ""
                    check(f"SHARE ({_name}): Share hands the system sheet the title and the link the page shows", bool(_ok), str(_d))
                if _path == "/flip":
                    check(f"SHARE ({_name}): ...and Copy link is still there beside it", _copy is True, f"copy={_copy}")
            else:
                check(f"SHARE ({_name}): without navigator.share there is no Share button", not _vis, f"visible={_vis}")
                if _path == "/flip":
                    check(f"SHARE ({_name}): ...and Copy link is what it always was", _copy is True, f"copy={_copy}")
            _ctx.close()
    _shb.close()

print("\nPOST RESULT — one row of what to do next, and the title stays on screen")
# Owner, v293, from a phone ("after post on pad"): the sheet kept the compose
# form on screen at half opacity with its title and caption wiped, and under
# it two full-width chips stacked. The Pad's became Watch / Share / Copy link
# on one row, Share only where navigator.share is; the form returns to full
# opacity, and the posted title stays in its field as the record of what was
# just posted. Copy link is the mechanism, read from a clipboard stub.
# FLIP POSTS THROUGH THE SAME SHEET NOW (owner: "shouldn't flip and pad look
# the same? flip is not as clean as pad"). Its own card had wrapped Open player
# onto two lines beside one-line buttons, which this would have said, had it
# ever been asked of Flip. So it is asked of both editors.
with _sp() as _pr:
    _prb = waits.instrument(_pr.chromium.launch())
    for _name, _path in (("Pad", "/"), ("Flip", "/flip")):
      for _w in (390, 1100):
        _ctx = _prb.new_context(viewport={"width": _w, "height": 844 if _w == 390 else 900})
        _ctx.add_init_script("""Object.defineProperty(navigator, 'share', { configurable: true, value: async (d) => { window.__shared = d; } });
            Object.defineProperty(navigator, 'clipboard', { configurable: true,
                value: { writeText: async (t) => { window.__copied = t; } } });""")
        _pg = _ctx.new_page()
        browsing.goto(_pg, BASE, _path)
        waits.settle(_pg, 600)
        if _path == "/":
            draw(_pg, "#canvas", 200, 200, n=16)
            _pg.wait_for_timeout(300)
            _pg.click("#recordBtn"); _pg.wait_for_timeout(500)
        else:
            _pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            draw(_pg, "#pad", 200, 200, n=16)
            _pg.wait_for_timeout(300)
        _pg.click("#postBtn"); _pg.wait_for_timeout(800)
        if not _pg.locator("#postSheet").count():
            check(f"POST RESULT ({_name}) at {_w}: Watch, Share and Copy link are all offered",
                  False, f"{_name} has no post sheet of the Pad's")
            _ctx.close()
            continue
        _pg.fill("#postTitleInput", "Result probe")
        # K1: the gallery tick's line says what ticking means, and for an
        # anonymous author that a public post comes with a key. Ticked and
        # unticked again, so this probe posts unlisted as before.
        _subs = []
        if _pg.locator("#postPublicInput").count():
            _pg.locator("#postSheet .post-check").click(); _pg.wait_for_timeout(100)
            _subs.append(_pg.text_content("#postPublicSub"))
            _pg.locator("#postSheet .post-check").click(); _pg.wait_for_timeout(100)
            _subs.append(_pg.text_content("#postPublicSub"))
        check(f"DELETE KEY ({_name}) at {_w}: ticking the gallery box says a key comes with a public post, unticking says link only",
              len(_subs) == 2 and "key to delete it from anywhere" in (_subs[0] or "")
              and "link only" in (_subs[1] or ""), str(_subs))
        _pg.click("#postSubmitBtn")
        try:
            _pg.wait_for_selector("#postWatchBtn", state="visible", timeout=20000)
        except Exception:                                        # noqa: BLE001
            check(f"POST RESULT ({_name}) at {_w}: Watch, Share and Copy link are all offered",
                  False, "no Watch after posting")
            _ctx.close()
            continue
        _pg.wait_for_timeout(600)
        _st = _pg.evaluate("""() => {
            const sheet = document.getElementById('postSheet').getBoundingClientRect();
            const btns = ['postWatchBtn', 'postShareBtn', 'postCopyBtn'].map(id => {
              const b = document.getElementById(id); if (!b || b.hidden) return null;
              const r = b.getBoundingClientRect(); const lab = b.querySelector('span:last-child');
            return { id, top: Math.round(r.top), h: Math.round(r.height), right: Math.round(r.right), w: Math.round(r.width),
                     lines: Math.round(10 * lab.getBoundingClientRect().height / parseFloat(getComputedStyle(lab).fontSize)) / 10 }; });
            return { title: document.getElementById('postCardTitle').textContent,
                     form: document.getElementById('postBody').getClientRects().length,
                     sheetRight: Math.round(sheet.right), btns }; }""")
        # The owner, from the iPhone: "Posted!" sat under the buttons with the
        # progress bar, cut off at the screen's edge. It was the title, and is
        # now the Posted! band's (the posted moment, verify_postmoment); the
        # status line, its job done, goes.
        _hd = _pg.evaluate("""() => ({ head: document.getElementById('postDoneHead').textContent.trim(),
            status: document.getElementById('postStatus').hidden })""")
        check(f"POST RESULT ({_name}) at {_w}: the sheet's band says Posted!, and no progress bar is left under the buttons",
              _hd["head"] == "Posted!" and _hd["status"], str(_hd))
        # It stayed in its field, the form at full strength, as the record of
        # what was posted (v293: dimmed and wiped read as lost). The form folds
        # away now, and the card under the band is that record.
        check(f"POST RESULT ({_name}) at {_w}: the posted title is on the posted card",
              _st["title"] == "Result probe", f"card reads {_st['title']!r}")
        check(f"POST RESULT ({_name}) at {_w}: the form folds away, rather than staying dimmed under the result",
              _st["form"] == 0, f"the form's boxes {_st['form']}")
        _b = [x for x in _st["btns"] if x]
        check(f"POST RESULT ({_name}) at {_w}: Watch, Share and Copy link are all offered",
              [x["id"] for x in _b] == ["postWatchBtn", "postShareBtn", "postCopyBtn"], str(_st["btns"]))
        if len(_b) == 3:
            check(f"POST RESULT ({_name}) at {_w}: ...on one row, each a tap target, inside the sheet",
                  max(x["top"] for x in _b) - min(x["top"] for x in _b) <= 1 and min(x["h"] for x in _b) >= 44
                  and max(x["right"] for x in _b) <= _st["sheetRight"], str(_b))
            # "Copy link" wrapped to two lines in a 103px cell on the first cut:
            # the label's box was 2.3x its font size; one line is under 1.3x.
            check(f"POST RESULT ({_name}) at {_w}: no label in the row wraps",
                  all(x["lines"] < 1.6 for x in _b), str([(x["id"], x["lines"]) for x in _b]))
            _pg.click("#postCopyBtn"); _pg.wait_for_timeout(300)
            _c = _pg.evaluate("() => window.__copied || null")
            check(f"POST RESULT ({_name}) at {_w}: Copy link puts the player's absolute link on the clipboard",
                  isinstance(_c, str) and _c.startswith(BASE) and "/s/" in _c, str(_c))
        # K1 (SK-AUD-009): the delete key, where you post. Painted (asked of
        # elementFromPoint, not a rect), inside the sheet, a 44px tap, one line,
        # and it copies the very key the posted list holds for this post.
        _k = _pg.evaluate("""() => {
            const row = document.getElementById('postKeyRow'), b = document.getElementById('postKeyBtn');
            if (!row || row.hidden || !b) return null;
            const r = b.getBoundingClientRect(), s = document.getElementById('postSheet').getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { painted: !!hit && b.contains(hit), h: Math.round(r.height), inside: r.right <= s.right + 0.5 && r.left >= s.left - 0.5,
                     words: row.textContent.replace(/\\s+/g, ' ').trim() }; }""")
        check(f"DELETE KEY ({_name}) at {_w}: the posted card offers Copy delete key, painted, a 44px tap, inside the sheet",
              bool(_k) and _k["painted"] and _k["h"] >= 44 and _k["inside"]
              and "Only this browser can delete it" in _k["words"], str(_k))
        if _k:
            _pg.evaluate("() => { window.__copied = null; }")
            _pg.click("#postKeyBtn"); _pg.wait_for_timeout(300)
            _kc = _pg.evaluate("""() => { const l = (window.SkriblPosted && window.SkriblPosted.list()) || [];
                const e = l.find(x => x.title === 'Result probe' && x.tok); return { copied: window.__copied || null, tok: e ? e.tok : null }; }""")
            check(f"DELETE KEY ({_name}) at {_w}: ...and copies the key the posted list holds for this post",
                  bool(_kc["tok"]) and _kc["copied"] == _kc["tok"], str(_kc)[:160])
        _ctx.close()
    _prb.close()

# K1's other half: a host that signs people in renders no key row at all (the
# account is the key), on either editor. The server side, as verify_library
# pins /library's: the blueprint's current_user_id decides.
import sys as _ksys
_ksys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from flask import Flask as _KFlask
import skribl as _kskribl
for _uid, _want in ((lambda: "u-1", False), (None, True)):
    _ka = _KFlask(__name__)
    _ka.config["SECRET_KEY"] = "harness-ux-k1"
    _ka.register_blueprint(_kskribl.create_blueprint(session=False, current_user_id=_uid, csrf=False))
    for _kp in ("/skribl-pad", "/flip"):
        _kr = _ka.test_client().get(_kp)
        _kh = _kr.get_data(as_text=True)
        check(f"DELETE KEY: {_kp} {'renders' if _want else 'does not render'} the key row "
              f"when the host {'has no' if _want else 'signs people in, so has a'} current user",
              _kr.status_code == 200 and ('id="postKeyRow"' in _kh) == _want, f"HTTP {_kr.status_code}")

print("\nPOST SHEET — Flip posts through the Pad's own sheet, so the two look the same")
# The owner, looking at Flip's post dialog beside the Pad's: "shouldn't flip and
# pad look the same? flip is not as clean as pad". Flip's was a card of its own:
# its title, link and buttons fell back to the browser's Arial beside the app's
# face, its two fields touched, and its counter sat off to one side. One
# partial now (_skribl_post.html) and one module (lib/postsheet.js); this holds
# the two editors' sheets to each other, open, field by field, as painted.
_SIG = r"""() => { const o = {};
  for (const sel of ['#postSheet', '#postTitleInput', '#postCaptionInput', '#postSheet .post-field-label',
                     '#postSubmitBtn', '#postCharCount', '#postSheet .post-check-text']) {
    const e = document.querySelector(sel);
    if (!e || !e.getClientRects().length) { o[sel] = null; continue; }
    const c = getComputedStyle(e), r = e.getBoundingClientRect();
    o[sel] = [c.fontFamily, c.fontSize, c.fontWeight, c.color, c.backgroundColor, c.padding,
              c.borderRadius, c.textAlign, Math.round(r.width), Math.round(r.left)].join(' | ');
  }
  return o; }"""
with _sp() as _ps:
    _psb = waits.instrument(_ps.chromium.launch())
    for _w in (390, 1100):
        _sigs = {}
        for _name, _path in (("Pad", "/"), ("Flip", "/flip")):
            _ctx = _psb.new_context(viewport={"width": _w, "height": 844 if _w == 390 else 900})
            _pg = _ctx.new_page()
            browsing.goto(_pg, BASE, _path)
            waits.settle(_pg, 600)
            _pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            draw(_pg, "#canvas" if _path == "/" else "#pad", 200, 200, n=16)
            _pg.wait_for_timeout(300)
            if _path == "/":
                _pg.click("#recordBtn"); _pg.wait_for_timeout(500)
            _pg.click("#postBtn"); _pg.wait_for_timeout(900)
            _sigs[_name] = _pg.evaluate(_SIG)
            _ctx.close()
        _diff = {k: (_sigs["Pad"].get(k), _sigs["Flip"].get(k)) for k in _sigs["Pad"]
                 if _sigs["Pad"].get(k) != _sigs["Flip"].get(k)}
        check(f"POST SHEET at {_w}: Flip's sheet is the Pad's, field for field",
              not _diff and all(_sigs["Pad"].values()), str(_diff)[:600] or "identical")
    _psb.close()

print("\nCOPY — one noun for the unit, a backup is a backup, and the two editors say how they relate")
# Outside review of v291, SK-AUD-009/010/017/020. Flip said "page" on the
# canvas and "frame" in the Tune drawer, the scrub bar and the export sheet;
# a person learning holds and Draw-on was also translating two nouns for one
# unit. The unit is a PAGE everywhere the person reads; "frames per second"
# survives once, in Help, as the explanation of the fps pill. "Save draft"
# downloaded a file and read as the persistence model, when autosave is;
# it is a backup and says so. Your Skribls stated its browser-local truth
# at the BOTTOM of the list, after the person had read the list as a
# library; it says it first. And Help opens, on both editors, with one
# sentence on how Pad and Flip relate.
with _sp() as _cp:
    _cb = waits.instrument(_cp.chromium.launch())
    _fp = _cb.new_page(viewport={"width": 1100, "height": 900})
    browsing.goto(_fp, BASE, "/flip")
    waits.settle(_fp, 600)
    _fp.click("#tuneBtn"); _fp.wait_for_timeout(300)
    _words = _fp.evaluate("""() => {
      const out = [];
      const hiddenUp = el => { for (let e = el; e && e !== document.body; e = e.parentElement) { if (e.hidden || e.id === 'helpDrawer' || getComputedStyle(e).display === 'none') return true; } return false; };
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n; while ((n = walker.nextNode())) { const t = n.textContent; if (/\\bframes?\\b/i.test(t) && !hiddenUp(n.parentElement)) out.push('text: ' + t.trim().slice(0, 60)); }
      for (const el of document.querySelectorAll('[aria-label], [title]')) {
        if (hiddenUp(el)) continue;
        for (const a of ['aria-label', 'title']) { const v = el.getAttribute(a) || ''; if (/\\bframes?\\b/i.test(v)) out.push((el.id || el.tagName) + ' ' + a + ': ' + v.slice(0, 60)); }
      }
      return out; }""")
    check("COPY (Flip): the editor's chrome says page, never frame — one noun for the unit",
          not _words, "; ".join(_words[:6]))
    _fp.click("#moreBtn"); _fp.wait_for_timeout(300)
    _fp.click("#miInfo"); _fp.wait_for_timeout(500)
    _help = _fp.evaluate("() => document.getElementById('helpDrawer').textContent.replace(/\\s+/g, ' ')")
    check("COPY (Flip): Help explains fps as pages per second, once, and says how Pad and Flip relate",
          "pages per second" in _help and "two ways to make a Skribl" in _help, _help[:200])
    _fp.close()
    _pp = _cb.new_page(viewport={"width": 1100, "height": 900})
    browsing.goto(_pp, BASE, "/")
    waits.settle(_pp, 600)
    _pp.click("#menuBtn"); _pp.wait_for_timeout(400)
    _items = _pp.evaluate("() => [...document.querySelectorAll('#menuSheet .menu-item')].map(b => b.textContent.replace(/\\s+/g, ' ').trim())")
    check("COPY (Pad): the file rows say what they make: Save as a file / Open a file, each a .skribl file",
          any("Save as a file" in x and ".skribl" in x for x in _items) and any("Open a file" in x and ".skribl" in x for x in _items), str(_items))
    # The switch to Flip says it in its name since the menu's tiles (after v323).
    _fm = _pp.evaluate("() => document.getElementById('flipBtn').getAttribute('aria-label') || ''")
    check("COPY (Pad): the way to Flip says it is a separate draft, page by page",
          "page by page" in _fm and "separate" in _fm, _fm)
    _pp.click("#helpItem"); _pp.wait_for_timeout(500)
    _helpp = _pp.evaluate("() => document.getElementById('helpDrawer').textContent.replace(/\\s+/g, ' ')")
    check("COPY (Pad): Help opens with how Pad and Flip relate", "two ways to make a Skribl" in _helpp, _helpp[:200])
    _pp.keyboard.press("Escape"); _pp.wait_for_timeout(400)
    # Your Skribls is the profile page since v304; the same sentence, UNDER the
    # list since the owner's pick A after v324 ("a calmer Library list": the
    # list is what a person came for, and the note is said once, after it).
    # It still names this browser; verify_posted pins the site-data clause.
    _pp.goto(BASE + "/library", wait_until="load"); waits.settle(_pp, 900)
    _order = _pp.evaluate("""() => { const f = document.querySelector('#postedPanel .posted-foot'), l = document.getElementById('postedList');
      if (!f || !l) return null; return { foot: f.getBoundingClientRect().top, list: l.getBoundingClientRect().top, text: f.textContent.trim().slice(0, 40) }; }""")
    check("COPY (Pad): Your Skribls says it is kept in this browser, under the list",
          _order and _order["foot"] > _order["list"] and "browser" in _order["text"], str(_order))
    _pp.close()
    _cb.close()

print("\nTHE PILL UNDER HOW IT WORKS — the amber warning yields to every surface that covers the page")
# Owner, from an iPhone (v304): "Media missing — tap to re-add" sat on top of
# the open help drawer. The list of surfaces the pill yields to had the
# drawers and the menus and not the help drawer, the report sheet or Flip's
# post and export sheets. Same rule, same mechanism (opacity 0, and the × loses
# its taps), driven on both editors through the real menu row.
with sync_playwright() as _pp_:
    _pb = waits.instrument(_pp_.chromium.launch())
    for _path, _open in (("/skribl-pad", ("#menuBtn", "#helpItem")), ("/flip", ("#moreBtn", "#miInfo"))):
        _hp = _pb.new_page(viewport={"width": 390, "height": 844})
        _hp.goto(BASE + _path, wait_until="load"); waits.settle(_hp, 1200)
        # The pill is put up and HELD: the editor's autosave loop would take a
        # hand-shown pill down again within a second (a saved pill self-hides),
        # which is the module's behaviour and not the rule under test. The rule
        # is the stylesheet's: a shown pill fades while a covering surface is
        # open and returns when it closes. So the module's show() is stubbed
        # once the pill is up, and the 0.3s fade is waited out at each step.
        _hp.evaluate("() => { if (window.SkriblHints) window.SkriblHints.hide(); const a = document.getElementById('autosaveStatus');"
                     " if (a) { a.hidden = false; a.classList.add('show', 'partial'); }"
                     " window.SkriblAutosavePill.show = function () {}; window.SkriblAutosavePill.hide = function () {}; }")
        _hp.wait_for_timeout(500)
        _before = float(_hp.evaluate("() => getComputedStyle(document.getElementById('autosaveStatus')).opacity"))
        _hp.click(_open[0]); _hp.wait_for_timeout(300); _hp.click(_open[1]); _hp.wait_for_timeout(700)
        _st = _hp.evaluate("""() => { const a = document.getElementById('autosaveStatus'), x = document.getElementById('autosaveStatusDismiss');
            return { help: !document.getElementById('helpDrawer').hidden, pill: parseFloat(getComputedStyle(a).opacity),
                     pe: getComputedStyle(a).pointerEvents, xpe: x ? getComputedStyle(x).pointerEvents : 'none' }; }""")
        check(f"{_path}: with How it works open the pill is hidden and its × takes no taps",
              _st["help"] and _before > 0.9 and _st["pill"] < 0.05 and _st["pe"] == "none" and _st["xpe"] == "none", str(_st))
        _hp.keyboard.press("Escape"); _hp.wait_for_timeout(1000)
        _after = float(_hp.evaluate("() => getComputedStyle(document.getElementById('autosaveStatus')).opacity"))
        check(f"{_path}: ...and it returns when the drawer closes", _after > 0.9, str(_after))
        _hp.close()
    _pb.close()

# NO CONTAINER AT REST (owner, from a mock: "It looks good"). On the Pad and
# Flip the header and the dock paint no card; the header's ground comes back
# only while the drawing is under it -- the pinned phone header once the Pen
# drawer scrolls the page (lib/headerglass.js marks .over-canvas). Asked of
# what is PAINTED where it matters: at rest the header's own fill and shadow
# are gone; over the drawing, the point under the Tune button belongs to the
# header and the header's fill is opaque, so the controls are not on the ink.
print("\nNO CONTAINER — the header and dock at rest; the header's ground over the drawing")
import math as _m, struct as _st
_n = 22050 * 3
_body = b"".join(_st.pack("<h", int(9000 * _m.sin(2 * _m.pi * 440 * i / 22050))) for i in range(_n))
_WAV = (b"RIFF" + _st.pack("<I", 36 + len(_body)) + b"WAVEfmt " + _st.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16)
        + b"data" + _st.pack("<I", len(_body)) + _body)
_GROUND = """(dock) => { const h = document.querySelector('.header'), t = document.querySelector(dock);
    const hc = getComputedStyle(h), tc = getComputedStyle(t), b = document.getElementById('tuneBtn').getBoundingClientRect();
    const at = document.elementFromPoint(b.left + 3, b.top + b.height / 2);
    const a = (c) => { const m = c.match(/[\\d.]+/g); return !m ? 0 : (m.length > 3 ? +m[3] : 1); };
    // A shadow PAINTS only if one of its colours does: at rest the header
    // already carries its band's two shadows, transparent, so the band can
    // fade in by colour alone (styles.css, THE GROUND IS A BAND).
    const paints = (s) => s !== 'none' && (s.match(/rgba?\\([^)]*\\)/g) || []).some(c => a(c) > 0);
    return { over: h.classList.contains('over-canvas'), hFill: a(hc.backgroundColor), hShadow: paints(hc.boxShadow),
             dFill: a(tc.backgroundColor), dShadow: paints(tc.boxShadow), scrolled: Math.round(scrollY),
             tuneOnHeader: !!at && h.contains(at) }; }"""
with sync_playwright() as _gp:
    _gb = waits.instrument(_gp.chromium.launch())
    for _route, _dock, _canvas in (("/skribl-pad", ".toolbar", "#canvas"), ("/flip", ".flip-tools", "#pad")):
        for _theme in ("dark", "light"):
            # 664 tall, a short phone: at 844 the end of Music left the drawing
            # 1-3px past the header, so the precondition below passed in one
            # font and failed in another (CI's), and main was red for it.
            _gc = _gb.new_context(viewport={"width": 390, "height": 664}, is_mobile=True, has_touch=True,
                                  color_scheme=_theme)
            _gc.add_init_script(f"try{{localStorage.setItem('skribl_theme_v1','{_theme}')}}catch(e){{}}")
            _g = _gc.new_page()
            browsing.goto(_g, BASE, _route); waits.settle(_g, 900)
            _g.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            _r = _g.evaluate(_GROUND, _dock)
            check(f"{_route} {_theme}: at rest the header and the dock paint no card",
                  not _r["over"] and _r["hFill"] == 0 and not _r["hShadow"] and _r["dFill"] == 0 and not _r["dShadow"], str(_r))
            browsing.pad_drawer(_g, "draw", settle=900)
            _o = _g.evaluate(_GROUND, _dock)
            check(f"{_route} {_theme}: the Pen drawer scrolls the drawing under the header, and the header's ground returns",
                  _o["scrolled"] > 0 and _o["over"] and _o["hFill"] == 1 and _o["tuneOnHeader"], str(_o))
            check(f"{_route} {_theme}: ...while the dock still paints none",
                  _o["dFill"] == 0 and not _o["dShadow"], str(_o))
            # THE GROUND IS A BAND (owner, after v324: "I def don't like the look
            # of the stuff showing under top bar"). The floating card left the
            # drawing showing in the gap above it and beside its corners. Read
            # as PAINT, once the fade is done: above the header, and beside it
            # on both sides, every pixel is the page's own ground.
            _g.wait_for_timeout(500)
            _hb = _g.evaluate("""() => { const r = document.querySelector('.header').getBoundingClientRect(), i = document.createElement('i');
                i.style.color = 'var(--surface-deep)'; document.body.appendChild(i); const g = getComputedStyle(i).color; i.remove();
                return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, vw: innerWidth, ground: g }; }""")
            _im = _Img.open(_io.BytesIO(_g.screenshot())).convert("RGB")
            _want = tuple(int(float(v)) for v in _re.findall(r"[\d.]+", _hb["ground"])[:3])
            _ys = range(int(_hb["top"]) + 4, int(_hb["bottom"]) - 4)
            _strip = ([(x, y) for y in range(0, max(1, int(_hb["top"]))) for x in range(0, _hb["vw"], 3)]
                      + [(x, y) for y in _ys for x in range(0, max(1, int(_hb["left"]) - 1))]
                      + [(x, y) for y in _ys for x in range(int(_hb["right"]) + 1, _hb["vw"])])
            _off = max(max(abs(a - b_) for a, b_ in zip(_im.getpixel(xy), _want)) for xy in _strip)
            check(f"{_route} {_theme}: ...and its ground is a band: above the header and beside it, only the page's ground",
                  _off <= 6, f"{len(_strip)} pixels read, the most off by {_off}/255 from {_want}; header {_hb}")
            # SCROLLED PAST THE DRAWING (owner's iPhone, after v321): at the
            # end of a long drawer the drawing has gone above the header and
            # the dock and the drawer are what is under it. The ground stayed
            # only while the DRAWING overlapped, so it went, and the dock's
            # icons showed through, stacked on the header's. A song in Music,
            # the Restart door open, scrolled to the end, with the drawing
            # confirmed above the header first so the check cannot pass on a
            # short page.
            browsing.pad_drawer(_g, "music", settle=400)
            _g.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _WAV})
            _g.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded')", timeout=15000)
            _g.click('#musicDoors .dp-tile[data-dp="restart"]'); _g.wait_for_timeout(400)
            _g.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
            browsing.wait_scroll_still(_g); _g.wait_for_timeout(300)
            _e = _g.evaluate(_GROUND, _dock)
            _past = _g.evaluate("""(cv) => document.querySelector(cv).getBoundingClientRect().bottom
                <= document.querySelector('.header').getBoundingClientRect().top + 1""", _canvas)
            check(f"{_route} {_theme}: scrolled to the end of Music, the drawing has gone above the header",
                  _past, str(_e))
            check(f"{_route} {_theme}: ...and the header keeps its ground over the dock and the drawer",
                  _e["over"] and _e["hFill"] == 1 and _e["tuneOnHeader"], str(_e))
            browsing.pad_drawer_close(_g); _g.wait_for_timeout(1200)
            _c = _g.evaluate(_GROUND, _dock)
            check(f"{_route} {_theme}: ...and closing it takes the ground away again",
                  _c["scrolled"] == 0 and not _c["over"] and _c["hFill"] == 0, str(_c))
            _gc.close()
    # FLIP'S PLAYBACK SETTINGS open ABOVE the drawing (owner's iPhone, after
    # v321): scrolled a little, the panel slides under the header while the
    # drawing is still below it, so a ground keyed to the drawing never came.
    # A short phone, so the page can scroll; both preconditions are asserted
    # so the check cannot pass on a page that did not get there.
    for _theme in ("dark", "light"):
        _fc = _gb.new_context(viewport={"width": 390, "height": 664}, is_mobile=True, has_touch=True, color_scheme=_theme)
        _fc.add_init_script(f"try{{localStorage.setItem('skribl_theme_v1','{_theme}')}}catch(e){{}}")
        _f = _fc.new_page()
        browsing.goto(_f, BASE, "/flip"); waits.settle(_f, 900)
        _f.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _f.click("#tuneBtn"); _f.wait_for_timeout(500)
        browsing.wait_scroll_still(_f, 3000)
        # With no drawer open, lib/drawers.js brings the page home once a scroll
        # settles, and in Chromium that wins at once; on the owner's iPhone the
        # page stayed scrolled. So the header is read while the scroll stands:
        # a few frames after it, before the page settles home. The colour fades
        # in over 0.25s, so the class is what is asked here, and the point under
        # Tune; the fill itself is pinned by the drawer checks above.
        _s, _below = _f.evaluate("""(dock) => new Promise(done => { window.scrollTo(0, 80);
            requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(() => {
              const h = document.querySelector('.header'), b = document.getElementById('tuneBtn').getBoundingClientRect();
              const at = document.elementFromPoint(b.left + 3, b.top + b.height / 2);
              done([{ over: h.classList.contains('over-canvas'), scrolled: Math.round(scrollY), tuneOnHeader: !!at && h.contains(at) },
                    document.getElementById('pad').getBoundingClientRect().top > h.getBoundingClientRect().bottom]); }))); })""", ".flip-tools")
        check(f"/flip {_theme}: Playback settings open and scrolled, with the drawing still below the header",
              _s["scrolled"] > 0 and _below, str(_s))
        check(f"/flip {_theme}: ...and the header takes its ground over the panel",
              _s["over"] and _s["tuneOnHeader"], str(_s))
        _fc.close()
    _g = _gb.new_page(viewport={"width": 1366, "height": 900})
    browsing.goto(_g, BASE, "/skribl-pad"); waits.settle(_g, 800)
    _d = _g.evaluate(_GROUND, ".toolbar")
    check("/skribl-pad desktop: the header and the dock paint no card",
          not _d["over"] and _d["hFill"] == 0 and _d["dFill"] == 0, str(_d))
    _gb.close()

print("\nTHE BAND FADES — read on every frame, it changes colour only")
# KIND TRANSITIONS, NEVER JUMPY (WORKING-AGREEMENTS). The header's band is its
# ::before, a strip fixed to the screen. Read on every animation frame as it
# comes and goes: the strip keeps its place and size (the band never grows out
# of the controls), its colour passes through in-between values (a fade, not
# a snap), and on every frame it ends at the header's foot. A shadow round the header (clipped,
# then lifted) was painted by Safari only inside the header's box (owner's
# iPhone, after v324: "still shows after reload"); a fixed box is the
# screen's. Pad and Flip share the rule; Pad is read, and
# the Gallery's band (pagemenu.css) is read the same way in verify_galib.
BAND_FRAMES = """(on) => new Promise(done => { const h = document.querySelector('.header'), out = [];
    h.classList.toggle('over-canvas', on); let n = 0;
    const f = () => { const c = getComputedStyle(h, '::before');
      out.push([c.position, c.top, c.height, c.backgroundColor, h.getBoundingClientRect().bottom, getComputedStyle(h).clipPath, c.content]);
      if (++n < 30) requestAnimationFrame(f); else done(out); };
    requestAnimationFrame(f); })"""
def band_frames(frames):
    """[(geometry, alpha, ends at the foot)] per frame, from the header's ::before strip."""
    rows = []
    for pos, top, height, bg, foot, clip, content in frames:
        m = _re.findall(r"[\d.]+", bg)
        alpha = float(m[3]) if len(m) > 3 else (1.0 if m else 0.0)
        num = lambda v: float(v[:-2]) if v.endswith("px") else float("nan")   # "auto" when there is no strip
        t, hgt = num(top), num(height)
        rows.append(((pos, t if t == t else None, hgt if hgt == hgt else None, content != "none"), alpha, abs(t + hgt - foot) <= 1))
    return rows
with sync_playwright() as _bp:
    _bb = _bp.chromium.launch()
    for _theme in ("light", "dark"):
        _bc = _bb.new_context(viewport={"width": 390, "height": 664}, is_mobile=True, has_touch=True, color_scheme=_theme)
        _bc.add_init_script(f"try{{localStorage.setItem('skribl_theme_v1','{_theme}')}}catch(e){{}}")
        _q = _bc.new_page()
        browsing.goto(_q, BASE, "/skribl-pad"); waits.settle(_q, 900)
        for _on, _way in ((True, "in"), (False, "out")):
            _fr = _q.evaluate(BAND_FRAMES, _on)
            _rows = band_frames(_fr)
            _clip = sorted({f[5] for f in _fr} - {"none"})
            _geo = {r[0] for r in _rows}
            _mid = [r for r in _rows if 0.02 < r[1] < 0.98]
            _bare = [i for i, r in enumerate(_rows) if r[1] > 0.01 and not r[2]]
            check(f"Pad {_theme}: the band is a strip fixed to the screen, fading {_way} by colour alone, never growing, ending at the header's foot",
                  len(_geo) == 1 and next(iter(_geo))[0] == "fixed" and next(iter(_geo))[3] and len(_mid) >= 3 and not _bare and not _clip,
                  f"strip {sorted(_geo)[:3]}, {len(_mid)} in-between frames, frames off the foot {_bare[:5]}, clip {_clip}")
        _bc.close()
    _bb.close()

print("\nTHE HEADER SETTLES — an idle Pad asks for no frames, and a replay asks for its own")
# THE PAD'S HEADER WAS FITTING ITSELF FOREVER. initBrandFit() snaps the button
# cluster to a whole pixel by writing actions' padding, and the observer that
# re-fits the header on any change inside actions watches `style` -- so every
# fit queued the next, from page load, on a page that looked idle. Each outside
# change (a class toggled, the replay's badge ticking) started one more such
# chain beside the first, and nothing ever ended one. Measured on main: about
# 180 frame requests a second on a blank Pad left alone, about 3,500 a second
# after one replay -- some 58 fits a frame, each a forced layout. Flip and the
# shared-link player were clean (Flip has no such fit; the player's header is
# display:none, so it never writes the padding).
#
# THE MEASURE IS THE MECHANISM: every requestAnimationFrame request on the page,
# counted for a second while nothing is happening. Not a count of calls to a
# function by name -- a renamed function would pass that forever. Headless
# Chromium paints 60 frames a second, so one stuck chain reads 60 and the old
# tree read 120-3,500; a settled page reads 0-3 (the save pill's own fade).
#
# AND WHILE A REPLAY PLAYS, ITS OWN FRAMES AND LITTLE ELSE. The badge beside
# Play was rewritten every frame, and each write woke the fit for another
# layout: 120 requests a second where the replay asks for 60. It is written
# when its second changes now.
_RAF_COUNT = """(() => { const raf = window.requestAnimationFrame.bind(window); window.__rafN = 0;
  window.requestAnimationFrame = (cb) => { window.__rafN++; return raf(cb); }; })()"""


def _frames_per_second(pg):
    pg.evaluate("() => { window.__rafN = 0; }")
    pg.wait_for_timeout(1000)
    return pg.evaluate("() => window.__rafN")


with sync_playwright() as _ip:
    _ib = waits.instrument(_ip.chromium.launch())
    for _vw, _vh, _mob in ((1280, 860, False), (402, 874, True)):
        _ic = _ib.new_context(viewport={"width": _vw, "height": _vh}, is_mobile=_mob, has_touch=_mob)
        _ic.add_init_script(_RAF_COUNT)
        _ipg = _ic.new_page()
        browsing.goto(_ipg, BASE, "/")
        waits.settle(_ipg, 1500)
        _ipg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _blank = _frames_per_second(_ipg)
        # A stroke drawn at a hand's pace (about two seconds), so the replay
        # below lasts long enough to be counted while it runs.
        _cb = _ipg.locator("#canvas").bounding_box()
        _ipg.mouse.move(_cb["x"] + 60, _cb["y"] + 80)
        _ipg.mouse.down()
        for _i in range(120):
            _ipg.mouse.move(_cb["x"] + 60 + (_i % 40) * 6, _cb["y"] + 80 + (_i // 40) * 30 + (_i % 40) * 2)
            _ipg.wait_for_timeout(16)
        _ipg.mouse.up()
        _ipg.evaluate("() => document.getElementById('recordBtn').click()")    # Done
        _ipg.wait_for_timeout(1500)
        _take = _frames_per_second(_ipg)
        _ipg.evaluate("() => document.getElementById('playBtn').click()")
        _ipg.wait_for_timeout(150)
        _playing = _frames_per_second(_ipg)
        _was_playing = _ipg.evaluate("() => playing")
        # WAIT FOR THE END, THEN COUNT. A fixed four seconds counted the
        # replay's own last frames as "left running" whenever the stroke above
        # was drawn slowly: the take lasts as long as the hand took, and under
        # a full battery's load 120 steps of 16ms ran past the wait (9 frames,
        # every one editorReplayFrame; reproduced with 44ms steps). The fixture
        # check below is now the wait's own verdict.
        try:
            _ipg.wait_for_function("() => !playing", timeout=30000)
            _still = False
        except Exception:
            _still = True
        _ipg.wait_for_timeout(300)
        _done = _frames_per_second(_ipg)
        check(f"Pad {_vw}: a blank page left alone asks for no frames", _blank <= 5,
              f"{_blank} requestAnimationFrame calls in one idle second")
        check(f"Pad {_vw}: ...nor once a take is saved", _take <= 5,
              f"{_take} in one second after Done")
        check(f"Pad {_vw}: the replay was still running while it was counted (the fixture)", _was_playing)
        check(f"Pad {_vw}: while the replay plays, its own frames and little else", 0 < _playing <= 90,
              f"{_playing} in one second (the replay asks for 60)")
        check(f"Pad {_vw}: the replay ended by itself (the fixture)", not _still)
        check(f"Pad {_vw}: ...and once it has, nothing is left running", _done <= 5,
              f"{_done} in one second after the replay ended")
        _ic.close()
    _ib.close()


ok = sum(1 for o, _ in results if o)   # recount AFTER the amendment pins
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
