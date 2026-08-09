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
    for _w, _want in ((1000, "FLIPMODE"), (430, "FLIPMODE"), (393, "FLIPMODE"),
                      (375, "FLIPMODE"), (360, "FLIPMODE"),
                      (340, "FLIP"), (300, "FM")):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1200)
        _shown = _pg.evaluate("() => document.querySelector('.flip-word').innerText.trim()")
        check(f"at {_w}px the wordmark reads {_want!r}", _shown == _want,
              f"shows {_shown!r} — exactly one tier must be visible")

        # Real overflow, not arithmetic. A wordmark that "fits" by squeezing
        # the controls or spilling past the edge is not fitting.
        _over = _pg.evaluate("""() => { const h = document.querySelector('.header');
          return Math.round(h.scrollWidth - h.clientWidth); }""")
        check(f"at {_w}px the header does not overflow",
              _over <= 0, f"{_over}px past the edge")
        _pg.close()
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
_TOGGLE_SRC = open(_os.path.join(_os.path.dirname(_os.path.dirname(
    _os.path.abspath(__file__))), "skribl", "static", "flip.js"),
    encoding="utf-8").read()
check("setColor coerces its toggle condition to a boolean",
      "!!(d.dataset.color" in _TOGGLE_SRC,
      "an && chain can yield undefined, and toggle(name, undefined) TOGGLES")

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
# .flip-word was shrunk to 15px below 440px, part of the same block that gave
# us "FM" — a header that also held fps, onion, grid and draw-on inline. The
# controls moved out and the shrink stayed, so the wordmark read visibly
# lighter on a phone than on a desktop for no remaining reason. Measured, 17px
# overflows by zero at every phone width.
with sync_playwright() as _p:
    _b = _p.chromium.launch()
    _sizes = {}
    for _w in (375, 393, 430, 1000):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1150)
        _sizes[_w] = _pg.evaluate("""() => { const w = document.querySelector('.flip-word');
          const h = document.querySelector('.header');
          const cs = getComputedStyle(w);
          return { size: parseFloat(cs.fontSize), weight: cs.fontWeight,
                   overflow: Math.round(h.scrollWidth - h.clientWidth) }; }""")
        _pg.close()

    _ref = _sizes[1000]
    for _w, _m in _sizes.items():
        check(f"at {_w}px the wordmark is full size",
              _m["size"] == _ref["size"],
              f"{_m['size']}px vs {_ref['size']}px on desktop — it reads lighter")
        check(f"at {_w}px the wordmark keeps its weight",
              _m["weight"] == _ref["weight"], f"{_m['weight']} vs {_ref['weight']}")
        check(f"at {_w}px the full size still does not overflow",
              _m["overflow"] <= 0, f"{_m['overflow']}px past the edge")

    print("\nGRID — the finest level is dropped where it becomes noise")
    # The grid is three nested gradient levels at 12.5% / 6.25% / 3.125% of the
    # canvas. The finest is 21px on a 673px desktop canvas but 10.8px on a
    # 347px phone one, where it stops reading as a grid and becomes a wash —
    # and at that spacing the 1px lines land on fractional pixels and render
    # unevenly. Two levels below 560px.
    _counts = {}
    for _w in (393, 1000):
        _pg = _b.new_page(viewport={"width": _w, "height": 844})
        _pg.goto(f"{BASE}/flip", wait_until="load")
        _pg.wait_for_timeout(1150)
        _pg.evaluate("() => { const g = document.getElementById('flipGrid');"
                     " if (g) g.classList.add('on');"
                     " if (typeof syncGrid === 'function') syncGrid(); }")
        _pg.wait_for_timeout(250)
        _counts[_w] = _pg.evaluate("""() => {
          const g = document.getElementById('flipGrid');
          const box = g.getBoundingClientRect();
          const layers = getComputedStyle(g).backgroundImage
            .split('linear-gradient').length - 1;
          return { layers, finest: +(box.width * 0.03125).toFixed(1),
                   mid: +(box.width * 0.0625).toFixed(1) };
        }""")
        _pg.close()

    check("desktop keeps all three grid levels",
          _counts[1000]["layers"] == 6, f"{_counts[1000]['layers']} gradients")
    check("a phone drops to two levels",
          _counts[393]["layers"] == 4, f"{_counts[393]['layers']} gradients")
    check("and its finest remaining line is wide enough to read as a grid",
          _counts[393]["mid"] >= 16,
          f"{_counts[393]['mid']}px spacing — below ~16px it reads as a wash")
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
      const ids = ['tuneBtn', 'onion', 'postBtn', 'moreBtn'];
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
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
