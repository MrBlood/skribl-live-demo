"""v106 — two UX fixes: honest export labels, and an undoable "Clear all".

1. FORMAT DISCLOSURE. The Pad has always labelled its export button with the
   container the browser will actually produce ("Video (MP4)" / "Video (WebM)").
   Flip never did — it said "Video" and then silently handed you WebM on any
   browser without WebCodecs H.264. Closes the last item in ROADMAP's "Known
   caveats to close". Flip's label now mirrors exportVideo()'s real decision,
   including the subtle case where music is present but AAC is unavailable, where
   the MP4 path deliberately bails rather than ship a silent video.

2. UNDOABLE CLEAR ALL. "Clear all" wiped strokes, music, photo and background,
   then called clearAutosave() — so the recovery copy went too. The two-tap arm
   guarded the accidental tap; nothing could undo a deliberate one. It now
   snapshots through serializeSkribl() and restores through loadSkribl(), the
   same pair the draft and autosave paths use, so media comes back with no
   parallel restore logic.

Note this sandbox's Chromium has VideoEncoder but no avc1, so the expected format
here is WebM on both surfaces — which is exactly the case the old Flip label got
wrong, and therefore the useful one to pin.
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def draw(page, sel, x0, y0, n=22):
    box = page.locator(sel).bounding_box()
    page.mouse.move(box["x"] + x0, box["y"] + y0)
    page.mouse.down()
    for i in range(n):
        page.mouse.move(box["x"] + x0 + i * 7, box["y"] + y0 + (i % 5) * 5)
    page.mouse.up()
    page.wait_for_timeout(150)


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900})

    print("\nFLIP — the export sheet now names the format (was the caveat)")
    flip = ctx.new_page()
    flip_errors = []
    flip.on("pageerror", lambda e: flip_errors.append(str(e)))
    flip.goto(BASE + "/flip", wait_until="load")
    flip.wait_for_timeout(1200)

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
    check("Flip's description names it too", ("MP4" in multi["desc"] or "WebM" in multi["desc"]),
          multi["desc"])

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
    pad.goto(BASE + "/", wait_until="load")
    pad.wait_for_timeout(1200)
    draw(pad, "#canvas", 80, 80, n=26)
    pad.evaluate("() => { document.getElementById('exportItem').click(); }")
    pad.wait_for_timeout(1400)
    padlbl = pad.evaluate("""() => ({
        title: document.querySelector('#exportVideo .export-opt-title').textContent,
        desc: document.getElementById('exportVideoDesc').textContent })""")
    check("Pad labels the container", padlbl["title"].strip() in ("Video (MP4)", "Video (WebM)"),
          padlbl["title"])
    check("Pad's desc names WebM too, not only MP4 (new in v106)",
          ("MP4" in padlbl["desc"] or "WebM" in padlbl["desc"]), padlbl["desc"])
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

    pad.evaluate("() => { document.getElementById('menuBtn').click(); }")
    pad.wait_for_timeout(400)
    pad.evaluate("() => { document.getElementById('clearMenuItem').click(); }")   # arms
    pad.wait_for_timeout(200)
    armed = pad.evaluate("() => document.getElementById('clearMenuItem').classList.contains('armed')")
    check("first tap arms rather than clears", armed and pad.evaluate("() => strokes.length") == before)
    pad.evaluate("() => { document.getElementById('clearMenuItem').click(); }")   # confirms
    pad.wait_for_timeout(600)
    check("second tap clears", pad.evaluate("() => strokes.length") == 0)

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
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _errs = []
    _pg.on("pageerror", lambda e: _errs.append(str(e)))
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)

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
    # menu is gone swallows every subsequent click on the app.
    check("the toolbar is reachable again afterwards",
          _pg.evaluate("() => { const b = document.getElementById('postBtn');"
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
    _b = _p.chromium.launch()
    # Measured by FORCING each candidate and reading header.scrollWidth against
    # clientWidth — not by summing child widths. Flex shrinks the controls
    # first, so an arithmetic "free space" figure hides the squeeze and reports
    # room that is not there; that is how the first pass concluded FLIPMODE
    # needed 440px when it actually clears at 360.
    # v220.x: the three text tiers (FLIPMODE/FLIP/FM) were replaced by a single
    # ~28px fanned-stack mark, smaller than the smallest tier was. The tier
    # assertion's INTENT survives: at every width the tiers used to cover,
    # exactly one visible mark, carrying the word for assistive tech.
    for _w in (1000, 430, 393, 375, 360, 340, 300):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1200)
        _shown = _pg.evaluate("""() => { const w = document.querySelector('.flip-word');
          const m = w && w.querySelector('.brand-mark');
          const r = m ? m.getBoundingClientRect() : {width: 0, height: 0};
          return { visible: !!m && r.width > 10 && r.height > 10,
                   label: (w && w.getAttribute('aria-label')) || '' }; }""")
        check(f"at {_w}px the mark is visible and labelled", 
              _shown["visible"] and _shown["label"].lower() == "flipmode",
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
    _b = _p.chromium.launch()
    for _w, _dpr in ((393, 3), (1000, 2), (760, 1)):
        _pg = _b.new_page(viewport={"width": _w, "height": 844},
                          device_scale_factor=_dpr)
        _errs = []
        _pg.on("pageerror", lambda e: _errs.append(str(e)))
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1250)
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
    _b = _p.chromium.launch()
    for _vw, _dpr, _label in ((393, 3, "phone"), (1000, 2, "desktop")):
        _ctx = _b.new_context(viewport={"width": _vw, "height": 852},
                              device_scale_factor=_dpr)
        _pg = _ctx.new_page()
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1300)
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
    _b = _p.chromium.launch()
    _ctx = _b.new_context(viewport={"width": 393, "height": 760},
                          has_touch=True, is_mobile=True)
    _pg = _ctx.new_page()
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1400)
    _pg.tap("#colorCurrent")
    _pg.wait_for_timeout(1100)

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
    _b = _p.chromium.launch()
    for _name, _path in (("Flip", "/flip"), ("Pad", "/skribl-pad")):
        _pg = _b.new_page(viewport={"width": 393, "height": 852})
        _pg.goto(f"{BASE}{_path}", wait_until="load")
        _pg.wait_for_timeout(1250)

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
# Was a font-size parity check on the text tiers ("15px below 440 for no
# remaining reason"). v220.x replaced the text with the fanned-stack mark;
# the intent is unchanged and now reads as RENDERED height: the mark is the
# same physical size on a phone as on a desktop, and never overflows.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _sizes = {}
    for _w in (375, 393, 430, 1000):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1150)
        _sizes[_w] = _pg.evaluate("""() => { const m = document.querySelector('.flip-word .brand-mark');
          const h = document.querySelector('.header');
          const r = m.getBoundingClientRect();
          return { size: Math.round(r.height * 2) / 2, weight: Math.round(r.width * 2) / 2,
                   overflow: Math.round(h.scrollWidth - h.clientWidth) }; }""")
        _pg.close()

    _ref = _sizes[1000]
    for _w, _m in _sizes.items():
        check(f"at {_w}px the mark is full size",
              _m["size"] == _ref["size"],
              f"{_m['size']}px tall vs {_ref['size']}px on desktop — it reads lighter")
        check(f"at {_w}px the mark keeps its width",
              _m["weight"] == _ref["weight"], f"{_m['weight']} vs {_ref['weight']}")
        check(f"at {_w}px the full size still does not overflow",
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
        _pg.wait_for_timeout(1200)
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
        check(f"at {_w}px the grid includes the fine subdivision",
              (_lines > 12) == _fine,
              f"{_lines} vertical lines — 9 majors alone, 17 with the fine layer")

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
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 390, "height": 844})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)

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
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 1100, "height": 900})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)

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
    _b = _p.chromium.launch()
    _pg = _b.new_page(viewport={"width": 1000, "height": 900})
    _pg.goto(f"{BASE}/flip", wait_until="load")
    _pg.wait_for_timeout(1300)
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
    _b = _p.chromium.launch()
    _pd = _b.new_page(viewport={"width": 1000, "height": 900})
    _errs = []
    _pd.on("pageerror", lambda e: _errs.append(str(e)))
    _pd.goto(f"{BASE}/skribl-pad", wait_until="load")
    _pd.wait_for_timeout(1300)

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
    _b = _p.chromium.launch()
    # Pad: tune button opens the drawer; Grid toggles the overlay canvas.
    pg = _b.new_page(viewport={"width": 900, "height": 800})
    pg.goto(BASE + "/", wait_until="load")
    pg.wait_for_timeout(900)
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
    # v225: the header row is 36, not 44 — Flip's size, adopted on Pad so the two
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
    pg.evaluate("() => document.getElementById('recordBtn').click()")
    pg.wait_for_timeout(300)
    pg.mouse.move(300, 300); pg.mouse.down(); pg.mouse.move(360, 340); pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.evaluate("() => document.getElementById('recordBtn').click()")
    pg.wait_for_timeout(500)
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
    check("F4 setup: tune drawer is open before Record", pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    pg.click("#recordBtn"); pg.wait_for_timeout(350)
    _st = pg.evaluate("() => { const sh = document.getElementById('tuneShell'), b = document.getElementById('tuneBtn'); return { open: sh.classList.contains('open'), ariaHidden: sh.getAttribute('aria-hidden'), expanded: b.getAttribute('aria-expanded') }; }")
    check("F4: Record closes the tune drawer (no .open)", not _st["open"], str(_st))
    check("F4: ...shell aria-hidden='true'", _st["ariaHidden"] == "true", str(_st))
    check("F4: ...button aria-expanded='false'", _st["expanded"] == "false", str(_st))
    pg.click("#recordBtn"); pg.wait_for_timeout(350)   # stop
    check("F4: stopping recording does NOT reopen the drawer",
          not pg.evaluate("() => document.getElementById('tuneShell').classList.contains('open')"))
    # Flip undo/redo are now rounded-square tiles, not circles.
    fpx = _b.new_page(viewport={"width": 900, "height": 800})
    fpx.goto(BASE + "/flip", wait_until="load"); fpx.wait_for_timeout(700)
    rad = fpx.evaluate("() => getComputedStyle(document.getElementById('undo')).borderRadius")
    check("V205-fix: Flip undo/redo are rounded-square tiles (were circles) — matches Pad + tool shape rule",
          rad == "12px", f"border-radius {rad}")
    fpx.close()

    # v206: Flip's grid toggle must LIGHT when on, like its .onion-tint siblings.
    # It toggled 'on' (unstyled) instead of 'active' since v204, so the overlay
    # drew but the button stayed dark. Pin all three siblings to .active.
    fg = _b.new_page(viewport={"width": 1280, "height": 900})
    fg.goto(BASE + "/flip", wait_until="load"); fg.wait_for_timeout(700)
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
    for pw in (363, 390, 1280):
        mp = _b.new_page(viewport={"width": pw, "height": 844})
        mp.goto(BASE + "/", wait_until="load"); mp.wait_for_timeout(700)
        mp.click("#musicOpenBtn"); mp.wait_for_timeout(300)
        mp.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD}); mp.wait_for_timeout(1500)
        mp.evaluate("() => { const t = document.getElementById('fineTuneToggle'); if (t && t.getAttribute('aria-expanded') !== 'true') t.click(); }")
        mp.wait_for_timeout(400)
        fit = mp.evaluate("""() => { const vw = document.documentElement.clientWidth;
            const grid = document.querySelector('#fineTuneBody .finetune-grid'); if (!grid) return null;
            const gr = grid.getBoundingClientRect();
            const b = document.querySelector('#fineTuneBody .nudge-btn').getBoundingClientRect();
            return { over: gr.right > vw + 1, scrollX: document.documentElement.scrollWidth > vw + 1, nudgeW: Math.round(b.width) }; }""")
        check(f"V206: nudge grid fits at {pw}px (no overflow)", fit and not fit["over"] and not fit["scrollX"], str(fit))
        # v207: the pills themselves must not overlap or spill their column. On
        # phone the groups STACK (one per row) — the earlier three-on-a-row
        # squeeze put 120px pills into 93px columns and they overlapped at 390.
        _ov = mp.evaluate("""() => { const ecs = [...document.querySelectorAll('#fineTuneBody .edge-controls')].map(e => e.getBoundingClientRect());
            const groups = [...document.querySelectorAll('#fineTuneBody .edge-group')].map(e => e.getBoundingClientRect());
            let overlap = false;
            for (let i = 0; i < ecs.length; i++) for (let j = i + 1; j < ecs.length; j++) {
                const a = ecs[i], b = ecs[j];
                const sameRow = Math.abs(a.top - b.top) < 4;
                if (sameRow && a.right > b.left + 1 && b.right > a.left + 1) overlap = true; }
            const spill = ecs.some((e, i) => e.right > groups[i].right + 1 || e.left < groups[i].left - 1);
            return { overlap, spill, rows: new Set(groups.map(g => Math.round(g.top))).size }; }""")
        check(f"V207: at {pw}px the nudge pills do not overlap each other or spill their column", not _ov["overlap"] and not _ov["spill"], str(_ov))
        if pw <= 640:
            # v210 (owner's iPhone): the layout is 2 + 1 — Start and End share
            # a row, Step size takes its own row underneath. The v207 pin said
            # "three rows"; that was guarding the three-ON-ONE-ROW overlap, not
            # arguing for one-per-row as a design, and the overlap/spill check
            # above still guards that class at every width. So: two rows, and
            # the first two groups on the SAME one.
            _rows = mp.evaluate("""() => [...document.querySelectorAll('#fineTuneBody .edge-group')]
                .map(e => Math.round(e.getBoundingClientRect().top))""")
            if pw >= 375:
                check(f"V210: at {pw}px the nudge groups lay out 2 + 1 (Start|End, then Step)",
                      len(set(_rows)) == 2 and _rows[0] == _rows[1] and _rows[2] > _rows[0],
                      f"group tops {_rows}")
            else:
                # 363 and narrower cannot hold two 128px pills; the grid must
                # fall back to one column rather than spill (v207 bug class).
                check(f"V210: at {pw}px (too narrow for 2-up) the nudge groups stack one per row",
                      len(set(_rows)) == 3, f"group tops {_rows}")
        if pw == 1280:
            check("V206: nudge buttons are 32px on desktop (option A)", fit and fit["nudgeW"] == 32, str(fit))
            # tap area: click 5px LEFT of the first "-" nudge (start-earlier). Its
            # readout must change, proving the expanded hit region fires the nudge.
            # the fine-tune body sits below the fold; bring the button on-screen
            # first or the coordinate click lands outside the viewport.
            mp.evaluate("() => document.querySelector('#fineTuneBody .nudge-btn[data-which=\"start\"][data-amount=\"1\"]').scrollIntoView({block: 'center'})")
            mp.wait_for_timeout(300)
            r = mp.evaluate("() => { const b = document.querySelector('#fineTuneBody .nudge-btn[data-which=\"start\"][data-amount=\"1\"]').getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height, r: b.right}; }")
            before = mp.evaluate("() => document.getElementById('startReadout').textContent")
            # click 5px to the RIGHT of the '+' (outside its box, in the tap zone, away from the readout on its left)
            mp.mouse.click(r["r"] + 5, r["y"] + r["h"] / 2); mp.wait_for_timeout(300)
            after = mp.evaluate("() => document.getElementById('startReadout').textContent")
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
            ph.goto(BASE + path, wait_until="load"); ph.wait_for_timeout(700)
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
        return { w: Math.round(r.width), h: Math.round(r.height),
                 text: (f.textContent || '').replace(/\\s+/g, ' ').trim() };
    }""")
    check("V219: ...and it has a real box once the menu is open (a row nobody can reach is not a relocation)",
          _fl["w"] > 100 and _fl["h"] >= 40, str(_fl))
    check("V219: ...and it carries the subtitle that says what Flip Mode IS — the 40px icon could not",
          "Draw a frame-by-frame animation" in _fl["text"], str(_fl))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(250)

    # v204-fix: at ~600px, recording must not let the tune button crowd the
    # record indicator onto the wordmark, and the wordmark must recover after
    # stop. Reproduces the reported 600px overlap + stuck-brand bug.
    narrow = _b.new_page(viewport={"width": 600, "height": 800})
    narrow.goto(BASE + "/", wait_until="load")
    narrow.wait_for_timeout(700)
    narrow.evaluate("() => document.getElementById('recordBtn').click()")
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
    fp.goto(BASE + "/flip", wait_until="load")
    fp.wait_for_timeout(900)
    toast = fp.evaluate("""() => {
        const el = document.querySelector('.skribl-hint');
        return el && !el.hidden ? el.textContent : null;
    }""")
    check("V204: Flip shows the intro toast on first load",
          toast and ("New here" in toast or "How it works" in toast), str(toast)[:50])
    # v206: the intro is a NORMAL small timed toast (the v205 panel is retired —
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

    # v206: menu verbiage aligned across editors + Clear all in BOTH menus.
    # (pg was closed above; open a fresh Pad page for the Pad-side checks.)
    pg = _b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(BASE + "/", wait_until="load"); pg.wait_for_timeout(600)
    pad_items = pg.evaluate("() => [...document.querySelectorAll('#menuSheet .menu-item, .menu-item')].map(b => b.textContent.replace(/\\s+/g,' ').trim())")
    flip_items = fp.evaluate("() => [...document.querySelectorAll('.flip-menu-item')].map(b => b.textContent.replace(/\\s+/g,' ').trim())")
    def has(items, s): return any(s in x for x in items)
    check("V206: Pad menu says 'Save draft (.skribl)' like Flip", has(pad_items, "Save draft (.skribl)"), str(pad_items))
    check("V206: Pad menu says 'Load draft (.skribl)' like Flip", has(pad_items, "Load draft (.skribl)"), str(pad_items))
    check("V206: Pad menu says 'Export…' like Flip", has(pad_items, "Export\u2026"), str(pad_items))
    check("V206: Flip menu has 'Clear all pages' (was drawer-only)", has(flip_items, "Clear all pages"), str(flip_items))
    check("V206: Pad menu has 'Clear all'", has(pad_items, "Clear all"), str(pad_items))
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
    pg.close()

    # v206: the Flip image/music drawer must SURVIVE picking a file. Flip's file
    # inputs live at the page root (outside the panels), and when the OS dialog
    # returns the browser fires click on that input; the click-outside handler
    # read it as "outside" and closed the drawer the instant a file was chosen —
    # which is why it "never opened" for the owner. Headless can't open a real
    # dialog, so dispatch the same click on the input the browser would.
    fp.click("#musicBtn"); fp.wait_for_timeout(400)
    check("V206: Flip music drawer opens", not fp.evaluate("() => document.getElementById('musicPanel').hidden"))
    fp.evaluate("() => document.getElementById('musicInput').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    fp.wait_for_timeout(300)
    check("V206: ...and stays open when the file input is clicked (dialog round-trip)",
          not fp.evaluate("() => document.getElementById('musicPanel').hidden"))
    fp.click("#musicBtn"); fp.wait_for_timeout(300)  # close
    fp.click("#imageBtn"); fp.wait_for_timeout(400)
    fp.evaluate("() => document.getElementById('imageInput').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
    fp.wait_for_timeout(300)
    check("V206: Flip image drawer also survives its file-input click",
          not fp.evaluate("() => document.getElementById('photoPanel').hidden"))
    fp.click("#imageBtn"); fp.wait_for_timeout(300)

    # v206: the two demo .skribl fixtures (harness/fixtures/) must load, render,
    # and PLAY in their own editor, and be refused by the other. These are real
    # non-trivial documents (a timed-replay galaxy; a 24-page bouncing-ball
    # flipbook), so they exercise the whole load->render->play path and pin the
    # format: if the schema drifts, the demos break here first.
    import pathlib as _pl
    _fx = _pl.Path(__file__).resolve().parent / "fixtures"
    _gal = (_fx / "demo-galaxy.skribl").read_bytes(); _bnc = (_fx / "demo-bounce.skribl").read_bytes()
    def _ink(page, sel):
        return page.evaluate(f"""() => {{ const c = document.querySelector('{sel}'); const x = c.getContext('2d');
            const d = x.getImageData(0,0,c.width,c.height).data; let n = 0; for (let i = 3; i < d.length; i += 16) if (d[i] > 0) n++; return n; }}""")
    dp = _b.new_page(viewport={"width": 1280, "height": 900}); dp.goto(BASE + "/", wait_until="load"); dp.wait_for_timeout(600)
    dp.set_input_files("#draftInput", {"name": "demo-galaxy.skribl", "mimeType": "application/json", "buffer": _gal}); dp.wait_for_timeout(1400)
    check("DEMO: galaxy .skribl loads in Pad", dp.evaluate("() => typeof strokes !== 'undefined' && strokes.length > 800"),
          f"strokes={dp.evaluate('() => (typeof strokes!==\'undefined\'?strokes.length:-1)')}")
    check("DEMO: galaxy renders ink on the canvas", _ink(dp, "#canvas") > 2000, f"ink={_ink(dp,'#canvas')}")
    dp.click("#playBtn"); dp.wait_for_timeout(1200); _a = _ink(dp, "#canvas"); dp.wait_for_timeout(1200); _b2 = _ink(dp, "#canvas")
    check("DEMO: galaxy REPLAYS — the drawing grows over time on Play", _b2 > _a, f"ink {_a} -> {_b2}")
    dp.close()
    df = _b.new_page(viewport={"width": 1280, "height": 900}); df.goto(BASE + "/flip", wait_until="load"); df.wait_for_timeout(800)
    df.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
    df.set_input_files("#draftInput", {"name": "demo-bounce.skribl", "mimeType": "application/json", "buffer": _bnc}); df.wait_for_timeout(1400)
    check("DEMO: bounce .skribl loads in Flip as 24 pages @ 12fps",
          df.evaluate("() => frames.length === 24 && fps === 12"), f"pages={df.evaluate('() => frames.length')} fps={df.evaluate('() => fps')}")
    check("DEMO: bounce renders ink", _ink(df, "#pad") > 5000, f"ink={_ink(df,'#pad')}")
    df.click("#play"); df.wait_for_timeout(500); _i1 = df.evaluate("() => idx"); df.wait_for_timeout(500); _i2 = df.evaluate("() => idx")
    check("DEMO: bounce FLIPS — page index advances on Play", df.evaluate("() => playing") and _i1 != _i2, f"idx {_i1} -> {_i2}")
    df.close()

    # v207: the player's Repeat (loop) button must VISIBLY light when pressed.
    # .player-btn.active is a JS-toggled class; every player scene in the
    # css-live capture was static, so cssgraph dropped the rule from player.css
    # and the button toggled loop internally but never lit — it read as dead.
    # Post the galaxy, open the real player, press Repeat, check the fill.
    import json as _json, re as _re
    _pp = _b.new_page(viewport={"width": 1280, "height": 900}); _pp.goto(BASE + "/", wait_until="load"); _pp.wait_for_timeout(600)
    _pp.set_input_files("#draftInput", {"name": "g.skribl", "mimeType": "application/json", "buffer": _gal}); _pp.wait_for_timeout(1200)
    _payload = _pp.evaluate("() => JSON.stringify(serializeSkribl())")
    _resp = _pp.evaluate("""async (body) => { const r = await fetch('/api/skribls', {method:'POST', headers:{'Content-Type':'application/json'}, body}); return {status: r.status, text: await r.text()}; }""", _payload)
    _pp.close()
    _pid = None
    try: _pid = _json.loads(_resp["text"]).get("id")
    except Exception: pass
    check("V207: posting the galaxy demo yields a player id", bool(_pid), str(_resp)[:100])
    if _pid:
        _pl = _b.new_page(viewport={"width": 1000, "height": 800}); _pl.goto(f"{BASE}/s/{_pid}", wait_until="load"); _pl.wait_for_timeout(1000)
        _pl.click("#playerLoopBtn"); _pl.wait_for_timeout(250)
        _lit = _pl.evaluate("() => { const b = document.getElementById('playerLoopBtn'); return { active: b.classList.contains('active'), bg: getComputedStyle(b).backgroundColor }; }")
        check("V207: player Repeat button LIGHTS (accent fill) when pressed — .player-btn.active is in player.css",
              _lit["active"] and _lit["bg"] == "rgb(124, 92, 255)", str(_lit))
        _pl.close()

    # v207: at 641px (the desktop breakpoint's first pixel) after recording,
    # "Post to Skribl" wrapped to THREE lines (59px pill), Record wrapped too,
    # and the header overflowed. Pills must never wrap; Post keeps its short
    # label until ~720px where the long one genuinely fits.
    for pw in (641, 660, 700):
        _n = _b.new_page(viewport={"width": pw, "height": 900}); _n.goto(BASE + "/", wait_until="load"); _n.wait_for_timeout(600)
        _n.click("#recordBtn"); _n.wait_for_timeout(250)
        _bb = _n.locator("#canvas").bounding_box(); _n.mouse.move(_bb["x"] + 200, _bb["y"] + 200); _n.mouse.down()
        for _i in range(1, 10): _n.mouse.move(_bb["x"] + 200 + _i * 12, _bb["y"] + 200 + _i * 7)
        _n.mouse.up(); _n.wait_for_timeout(300); _n.click("#recordBtn"); _n.wait_for_timeout(450)
        _g = _n.evaluate("""() => { const h = document.querySelector('.header'); const p = document.getElementById('postBtn'); const r = document.getElementById('recordBtn');
            const ph = p.getBoundingClientRect().height, rh = r.getBoundingClientRect().height;
            return { overflow: h.scrollWidth > h.clientWidth + 1, postH: Math.round(ph), recordH: Math.round(rh), headerH: Math.round(h.getBoundingClientRect().height) }; }""")
        check(f"V207: at {pw}px post-record the header does not overflow", not _g["overflow"], str(_g))
        check(f"V207: at {pw}px Post/Record pills are single-line (<=48px tall, not wrapped)",
              _g["postH"] <= 48 and _g["recordH"] <= 48, str(_g))
        _n.close()

    # v207: onion on/off moved from the header into the tune drawer's Onion row
    # (frees header space), styled as an .onion-tint toggle so it lights ORANGE
    # like grid / motion / tint. setOnion() and the row-mute behaviour unchanged.
    _o = _b.new_page(viewport={"width": 1280, "height": 900}); _o.goto(BASE + "/flip", wait_until="load"); _o.wait_for_timeout(800)
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

    # v207: the loop-detail Focus (Loop/Start/End) and Zoom (1x-8x) groups are
    # real .seg pill sliders (round shell, sliding highlight) matching the tune
    # drawer's Speed/Onion — not the ad-hoc rounded-rect buttons they were — and
    # a magnifier glyph labels the zoom group. Both editors build the same bar.
    for path, nm, opener in (("/", "Pad", "#musicOpenBtn"), ("/flip", "Flip", "#musicBtn")):
        _z = _b.new_page(viewport={"width": 1280, "height": 900}); _z.goto(BASE + path, wait_until="load"); _z.wait_for_timeout(800)
        _z.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
        _z.click(opener); _z.wait_for_timeout(300)
        _z.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD}); _z.wait_for_timeout(1500)
        _z.evaluate("() => { const t = document.getElementById('fineTuneToggle'); if (t && t.getAttribute('aria-expanded') !== 'true') t.click(); }")
        _z.wait_for_timeout(900)
        # RADIUS IS READ FROM THE TOKEN, NOT TYPED. This asserted the literal
        # "999px" until v220 squared every segmented control (--r-seg, styles.css).
        # A literal here meant the pin failed the moment the owner exercised a
        # decision the token exists to let them make, while still not catching
        # the thing that actually matters: that these two groups agree with every
        # other segmented group on the surface. Comparing against the resolved
        # value of --r-seg keeps the guarantee (both are .seg, both share the
        # one radius) and lets 12px or 999px both be correct — whichever the
        # token says. Set --r-seg back to 999px and this passes unchanged.
        _zi = _z.evaluate("""() => { const f = document.querySelector('.zoom-seg[data-role="focus"]'); const m = document.querySelector('.zoom-seg[data-role="mag"]');
            if (!f || !m) return null; const sl = f.querySelector('.seg-slider'); const cs = getComputedStyle(f);
            const token = getComputedStyle(document.documentElement).getPropertyValue('--r-seg').trim();
            const other = document.querySelector('#toolGroup');
            return { bothSeg: f.classList.contains('seg') && m.classList.contains('seg'), radius: cs.borderRadius,
                     token: token, magRadius: getComputedStyle(m).borderRadius,
                     matchesToolGroup: other ? getComputedStyle(other).borderRadius === cs.borderRadius : null,
                     sliderVisible: sl && getComputedStyle(sl).opacity === '1' && sl.getBoundingClientRect().width > 20,
                     magLabelled: !!(m.getAttribute('aria-label')
                       && (m.getAttribute('title') || m.getAttribute('data-tip'))),
                     rowNeed: (() => {
                       const bar = document.querySelector('.zoom-mag-bar');
                       const wrap = document.querySelector('.zoom-mag-wrap');
                       if (!bar || !wrap) return null;
                       const gap = parseFloat(getComputedStyle(bar).columnGap) || 0;
                       const lead = parseFloat(getComputedStyle(f).marginLeft) || 0;
                       return Math.round(lead + f.getBoundingClientRect().width + gap
                                         + wrap.getBoundingClientRect().width);
                     })() }; }""")
        check(f"V207: {nm} loop-detail focus/zoom groups are .seg groups carrying --r-seg",
              _zi and _zi["bothSeg"] and _zi["radius"] == _zi["token"]
              and _zi["magRadius"] == _zi["token"], str(_zi))
        check(f"V207: {nm} loop-detail groups share the tool group's radius",
              _zi and _zi["matchesToolGroup"] is True, str(_zi))
        check(f"V207: {nm} loop-detail slider highlight is visible on the selected cell", _zi and _zi["sliderVisible"], str(_zi))
        # v223 REPLACES the old "carries a magnifier glyph" pin, owner's call.
        # The glyph is gone: it cost 24px of the row (16px icon + 8px gap) and
        # forced a further 24px lead on the focus pill purely to push it back
        # into alignment with the pill the glyph had displaced. That 48px was
        # what dropped Loop/Start/End and 1x-8x onto separate lines at 510px,
        # which is where the owner reported it.
        #
        # What the glyph was FOR is pinned instead -- the zoom group still says
        # what it is -- plus the thing the glyph was costing. title OR data-tip:
        # the tooltip layer moves `title` to `data-tip` so the custom tooltip can
        # own the hover, so a title-only check reads as unlabelled at runtime. A width budget,
        # not a "same row" check: this page is 1280 wide, where anything fits,
        # so asserting one row here would pass no matter how much chrome came
        # back. Measured 361 after the change (171.5 focus + 10 gap + 179.3
        # mag); 400 leaves headroom for font and token changes while still
        # failing if another 48px of decoration is added. At 361 the row stays
        # on one line down to a 361px bar, i.e. a ~465px viewport.
        check(f"V207: {nm} zoom group says what it is (title + aria-label)",
              _zi and _zi["magLabelled"], str(_zi))
        check(f"v223: {nm} loop-detail row stays within its one-line budget",
              _zi and _zi["rowNeed"] is not None and _zi["rowNeed"] <= 400,
              f"row needs {_zi and _zi.get('rowNeed')}px (budget 400) — "
              f"above this the focus and zoom pills split onto two lines on a phone")
        _z.close()

    # v207: help pills that name a real tappable control carry that control's
    # actual glyph (same SVG the button renders); concept pills (Brush size,
    # Pressure) do not. And the Onion-skin text no longer says "in the header"
    # (onion moved to the tune drawer this release).
    _h = _b.new_page(viewport={"width": 1000, "height": 900}); _h.goto(BASE + "/flip", wait_until="load"); _h.wait_for_timeout(800)
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

    # v207: the eyedropper — the one control in the colour row that lacked its
    # 44pt tap area (the dots beside it had theirs). Box stays 30px (dot-sized,
    # on purpose); icon 16->18 to match tier-2 toggles; tap area added. And the
    # help pill's glyph must be the button's OWN glyph, not a lookalike.
    for path, nm, opener in (("/", "Pad", "#colorOpenBtn"), ("/flip", "Flip", "#colorCurrent")):
        _e = _b.new_page(viewport={"width": 1280, "height": 900}); _e.goto(BASE + path, wait_until="load"); _e.wait_for_timeout(800)
        _e.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
        _e.click(opener); _e.wait_for_timeout(400)
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

    # v207: icons are SVG, not Unicode text glyphs. The Flip page bar was MIXED
    # (Hold/Artwork SVG, Move/Move/Copy/Delete text: ◀ ▶ ⧉ ✕) and the add-page
    # buttons used the fullwidth ＋ — text glyphs render at different weights
    # across fonts/platforms and did not match their SVG neighbours. Hold's
    # ×N COUNT stays text (it is a number, not an icon).
    _s = _b.new_page(viewport={"width": 1280, "height": 900}); _s.goto(BASE + "/flip", wait_until="load"); _s.wait_for_timeout(800)
    _s.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); addFrame(true); }")
    _s.wait_for_timeout(300)
    _ic2 = _s.evaluate("""() => { const ids = ['pbLeft','pbRight','pbCopy','pbHold','pbDel'];
        const pb = ids.map(i => { const b = document.getElementById(i); return { id: i, svg: !!b.querySelector('svg') }; });
        const iconOnlyText = ['pbLeft','pbRight','pbCopy','pbDel'].some(i => document.getElementById(i).querySelector('.pb-ic'));
        const adds = [...document.querySelectorAll('.addbtn')].map(a => ({ svg: !!a.querySelector('svg.addbtn-ic'), hasFullwidthPlus: a.textContent.includes('\uFF0B') }));
        return { allPbSvg: pb.every(x => x.svg), iconOnlyText, adds }; }""")
    check("V207: every page-action button carries an SVG icon", _ic2["allPbSvg"], str(_ic2))
    check("V207: Move/Copy/Delete no longer use text-glyph icons", not _ic2["iconOnlyText"], str(_ic2))
    check("V207: add-page buttons use an SVG plus, not the fullwidth text ＋",
          _ic2["adds"] and all(a["svg"] and not a["hasFullwidthPlus"] for a in _ic2["adds"]), str(_ic2["adds"]))
    _s.close()

    # v207: COMPREHENSIVE phone fit. Measures every interactive control's real
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
    _AUDIT = """() => { const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
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
        for path, nm, openers in (("/", "Pad", ("#tuneBtn", "#colorOpenBtn", "#imageOpenBtn", "#musicOpenBtn")),
                                  ("/flip", "Flip", ("#tuneBtn", "#colorCurrent", "#imageBtn", "#musicBtn"))):
            _f = _b.new_page(viewport={"width": pw, "height": 844}); _f.goto(BASE + path, wait_until="load"); _f.wait_for_timeout(700)
            _f.evaluate("() => { const t = document.querySelector('.skribl-hint'); if (t) t.click(); }")
            _r = _f.evaluate(_AUDIT)
            check(f"PHONE {nm}@{pw}: every control on-screen, no scroll, no overlap, no clip (base)", _AUDIT_OK(_r), str(_r))
            for op in openers:
                if _f.locator(op).count():
                    _f.click(op); _f.wait_for_timeout(350); _r = _f.evaluate(_AUDIT)
                    check(f"PHONE {nm}@{pw}: ...with {op} drawer open", _AUDIT_OK(_r), str(_r))
                    _f.click(op); _f.wait_for_timeout(200)
            _f.click(openers[3]); _f.wait_for_timeout(300)
            _f.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD}); _f.wait_for_timeout(1400)
            _f.evaluate("() => { const t = document.getElementById('fineTuneToggle'); if (t && t.getAttribute('aria-expanded') !== 'true') t.click(); }"); _f.wait_for_timeout(600)
            _r = _f.evaluate(_AUDIT)
            check(f"PHONE {nm}@{pw}: ...with music loaded + fine-tune open", _AUDIT_OK(_r), str(_r))
            _f.close()
    # v210: the header brand vs the control cluster, both states, three widths.
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
        _h = _b.new_page(viewport={"width": pw, "height": 844}); _h.goto(BASE + "/", wait_until="load"); _h.wait_for_timeout(700)
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
        _mk = _h.evaluate("() => { const s = document.querySelector('.brand > span svg');"
                          " if (!s) return 0; const r = s.getBoundingClientRect();"
                          " return r.width > 0 && r.height > 0 ? Math.round(r.width) : 0; }")
        if pw >= 375:
            check(f"v223 header@{pw}: after record→stop the MARK IS BACK",
                  _mk > 0,
                  f"mark {_mk}px — the v210 take-saved hide is retired; "
                  f"initBrandFit sheds Record/gap/Post's label to seat it")
        else:
            check(f"v223 header@{pw}: the mark stays shed where it genuinely cannot fit",
                  _mk == 0,
                  f"mark {_mk}px — at {pw} it does not fit even with every label shed")
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
        _pw = _h.evaluate("() => { const p = document.getElementById('postBtn'); return p && !p.hidden ? Math.round(p.getBoundingClientRect().width) : null; }")
        if pw >= 430:
            check(f"V219 header@{pw}: Post KEEPS its label — at 430 the mark and the word both fit", _pw and _pw > 60, f"Post {_pw}px wide")
        elif pw >= 375:
            check(f"v223 header@{pw}: Post goes icon-only so the mark can be seated", _pw == 40, f"Post {_pw}px wide (icon)")
        else:
            check(f"V219 header@{pw}: Post may shed its label at the 320px safety net", _pw and _pw > 0, f"Post {_pw}px wide")
        _h.close()

    check("V204: the old crammed .flip-hint footer is gone",
          fp.evaluate("() => !document.querySelector('.flip-hint')"))
    fp.close()
    _b.close()

print("\nAMENDMENT PINS — A1 wiring, A2 narrow-viewport frame")
import re as _re
_appjs = (ROOT / "skribl" / "static" / "app.js").read_text()
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
check("the editor loop applies the same rule",
      "if (audioCtx.state === 'running') return go();" in _appjs)
check("a failed unlock hands off to native audio instead of claiming success",
      "onFail" in _appjs and "playNativeLooped" in _appjs
      and "startLoopPreviewNative" in _appjs)
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
    _b = _p.chromium.launch()
    for _w in (461, 390, 344):
        _pg = _b.new_page(viewport={"width": _w, "height": 800})
        _pg.goto(f"{BASE}/skribl-pad", wait_until="load")
        _pg.wait_for_timeout(400)
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
    _b = _p3.chromium.launch()
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
    _f3.goto(BASE + "/", wait_until="load")
    _f3.wait_for_timeout(700)
    _f3.click("#musicOpenBtn")
    _f3.wait_for_timeout(300)
    _f3.set_input_files("#musicInput",
                        {"name": "t.wav", "mimeType": "audio/wav", "buffer": _AUD})
    _f3.wait_for_timeout(1500)
    _f3.evaluate("() => { const c = document.getElementById('musicOpenBtn'); if (c) c.click(); }")
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


# v211 (owner, desktop): Space+drag DREW A LINE instead of grab-panning.
# Both editors gated the pan intercept on zoom>1, so at 100% the drag fell
# through to the drawing tool. And Flip draws on pointerdown, which fires
# BEFORE the mousedown the intercept listened for — a capture-phase mousedown
# was always too late there. Pinned by doing what the owner did: hold Space,
# drag across the canvas, and count strokes. Zero, at 100% AND magnified, on
# both editors. A key held down in Playwright is a real keydown/keyup pair.
with _sp() as _p4:
    _b = _p4.chromium.launch()
    for nm, url, canvas_sel, count_js in (
            ("pad", "/", "#canvas", "() => strokes.length"),
            ("flip", "/flip", "#pad", "() => frame().strokes.length")):
        for magnified in (False, True):
            _s = _b.new_page(viewport={"width": 1280, "height": 900})
            _s.goto(BASE + url, wait_until="load"); _s.wait_for_timeout(700)
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
    _br13 = _b13.chromium.launch()
    _c13 = _br13.new_context(viewport={"width": 900, "height": 900})
    _p13 = _c13.new_page()
    _p13.goto(BASE + "/", wait_until="load"); _p13.wait_for_timeout(700)
    _p13.evaluate("() => localStorage.clear()")
    _p13.click("#recordBtn"); _p13.wait_for_timeout(350)
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

ok = sum(1 for o, _ in results if o)   # recount AFTER the amendment pins
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
