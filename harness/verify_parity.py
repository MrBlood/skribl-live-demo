"""Pad and Flip must agree about the controls they share.

WHY THIS EXISTS. The two editors drive the SAME shared partials with
independent controllers — app.js (~6.9k lines) and flip.js (~2.9k) each
implement the eyedropper, colours, smoothing, photo and music controls. Most
bugs in recent sessions were one surface carrying a fix the other lacked, and
nothing failed when they drifted, because every suite drives ONE surface:
verify_review's 277 assertions never load Pad at all, and verify_ux hits Flip
twelve times against Pad's two.

The problem was never that there are two implementations. It is that they drift
and nobody notices. This suite makes drift fail.

WHY A MAP AND NOT AN ID DIFF. The same control has different ids on each
surface — undo is #undoBtn on Pad and #undo on Flip, brush size is
#brushSizeRange against #size — so comparing id sets reports noise and misses
the real divergence. CONTROLS below names each control ONCE and records where
it lives on each surface. That map is also the extraction plan: every row is a
controller boundary, and this suite is the acceptance test for moving it.

A row with a None selector is a DELIBERATE difference, annotated with why. Pad
and Flip should not converge on one interface — Pad is meant to be immediate,
Flip is meant to be an animation tool — so the point is that differences are
declared rather than accidental.
"""
import math
import os
import struct
import sys
import zlib

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

# canonical name -> (pad selector, flip selector, note)
# v224 merged Image and Music into ONE #mediaOpenBtn on BOTH surfaces, opening a
# router drawer whose rows open the real photo/music panels. Reaching a media
# drawer is therefore two taps -- and it is the SAME two taps on Pad and Flip,
# which is itself a parity gain: this used to be #imageOpenBtn on one and
# #imageBtn on the other. Kept as a function so a future change to the route has
# one place to edit rather than a dozen call sites.
def open_media(pg, which, settle=350):
    """which: 'photo' or 'music'."""
    pg.click("#mediaOpenBtn")
    pg.wait_for_timeout(200)
    pg.click("#mediaAddImage" if which == "photo" else "#mediaAddMusic")
    pg.wait_for_timeout(settle)

CONTROLS = [
    # --- drawing tools ----------------------------------------------------
    ("pen tool",           "#penToolBtn",      "#penToolBtn",     ""),
    ("eraser tool",        "#eraserToolBtn",   "#eraserToolBtn",  ""),
    ("undo",               "#undoBtn",         "#undo",           ""),
    ("redo",               "#redoBtn",         "#redo",           ""),
    # --- colour -----------------------------------------------------------
    ("open draw drawer",   "#colorOpenBtn",    "#colorCurrent",   ""),
    ("colour swatches",    "#colorGroup",      "#colorGroup",     ""),
    ("recent colours",     "#recentColors",    "#recentColors",   ""),
    ("recent colours row", "#recentRow",       "#recentRow",      ""),
    ("eyedropper",         "#eyedropperBtn",   "#eyedropperBtn",  ""),
    ("background swatches", "#bgGroup",        "#bgGroup",        ""),
    # --- brush ------------------------------------------------------------
    # DECLARED, and pinned here so it cannot drift further. The partial's own
    # header records it — Pad 1-30 default 5, Flip 2-34 default 7 — but records
    # only THAT they differ, not why. Pinned as characterization: if someone
    # decides they should match, this line is where the decision gets made.
    ("brush size input",   "#brushSizeRange",  "#size",           "@range-differs"),
    ("brush size readout", "#brushSizeVal",    "#sizeVal",        ""),
    ("smoothing control",  "#smoothSeg",       "#smoothSeg",      ""),
    # --- media ------------------------------------------------------------
    # One merged control on both, opening the router that leads to either
    # panel. The old pair (#imageOpenBtn / #imageBtn) was a naming divergence
    # for the same job; the merge removed it.
    ("open media router",  "#mediaOpenBtn",    "#mediaOpenBtn",   ""),
    ("media row: image",   "#mediaAddImage",   "#mediaAddImage",  ""),
    ("photo file input",   "#photoInput",      "#imageInput",     ""),
    ("photo fit control",  "#photoFitGroup",   "#photoFitGroup",  ""),
    ("reset photo",        "#resetPhotoBtn",   "#resetPhotoBtn",  ""),
    ("media row: music",   "#mediaAddMusic",   "#mediaAddMusic",  ""),
    ("media row: zoom",    "#mediaZoom",       "#mediaZoom",      ""),
    ("music waveform",     "#waveformCanvas",  "#waveformCanvas", ""),
    ("music trim start",   "#handleStart",     "#handleStart",    ""),
    ("music trim end",     "#handleEnd",       "#handleEnd",      ""),
    ("fine-tune loop",     "#fineTuneToggle",  "#fineTuneToggle", ""),
    # --- canvas / system --------------------------------------------------
    ("canvas size control", "#canvasSeg",      "#canvasSeg",      ""),
    ("first-use hints",    "#hintSeg",         "#hintSeg",        ""),
    ("zoom in",            "#zoomInBtn",       "#zoomInBtn",      ""),
    ("zoom out",           "#zoomOutBtn",      "#zoomOutBtn",     ""),
    ("zoom readout",       "#zoomVal",         "#zoomVal",        ""),
    ("clear",              "#clearDrawerBtn",  "#clear",          ""),
    ("undo a clear",       "#clearUndoBtn",    "#clearUndo",      ""),
    ("help drawer",        "#helpDrawer",      "#helpDrawer",     ""),
    ("report a problem",   "#reportSheet",     "#reportSheet",    ""),
    ("your skribls",       "#postedDrawer",    "#postedDrawer",   ""),
    # --- declared differences ---------------------------------------------
    ("page filmstrip",     None,               "#strip",
     "Flip only: pages are what make it an animation tool."),
    ("page grid overlay",  None,               "#gridBtn",
     "Flip only: alignment across pages is a Flip problem."),
    ("empty-canvas hint",  "#canvasEmptyHint", None,
     "Pad only: Flip's filmstrip already shows the page is blank."),
]

# Controls where the OPTIONS are the same feature on both surfaces. Everything
# else may legitimately differ in content.
SAME_OPTIONS = {"smoothing control", "canvas size control", "first-use hints",
                "photo fit control"}


def _read_static(name):
    """Read a client source file. Used by the few assertions that must check a
    source-level fact — that a duplicated constant is GONE — which no amount of
    driving the page can show, because the surviving copy would agree until the
    day someone changes one of them."""
    return open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "skribl", "static", name), encoding="utf-8").read()


def png_bytes(w=8, h=8):
    """A real 8x8 PNG. Generated rather than shipped as a fixture: the suite
    stays self-contained, and a binary blob in the tree is one more thing
    SHA256SUMS has to carry and nobody can read."""
    rows = b""
    for y in range(h):
        rows += b"\x00" + bytes(v for x in range(w)
                                for v in ((x * 30) % 256, (y * 30) % 256, 128))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def wav_bytes(seconds=1.0, rate=8000):
    """A real one-second 440Hz WAV, so the music path actually DECODES rather
    than being handed something the AudioContext rejects."""
    n = int(seconds * rate)
    frames = b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / rate)))
                      for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(frames)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(frames)) + frames)

EXISTS = """(sel) => { const e = document.querySelector(sel);
  return e ? { found: true, tag: e.tagName.toLowerCase(),
               type: e.getAttribute('type') || '',
               min: e.getAttribute('min') || '', max: e.getAttribute('max') || '',
               step: e.getAttribute('step') || '',
               opts: [...e.querySelectorAll('button')].map(b => b.textContent.trim()).join('|'),
               accept: e.getAttribute('accept') || '' }
            : { found: false }; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    surf = {}
    errs = {"pad": [], "flip": []}
    for name, path in (("pad", "/skribl-pad"), ("flip", "/flip")):
        pg = b.new_page(viewport={"width": 900, "height": 1100})
        pg.on("pageerror", lambda e, n=name: errs[n].append(str(e)))
        pg.goto(BASE + path)
        pg.wait_for_timeout(1500)
        surf[name] = pg
    pad, flip = surf["pad"], surf["flip"]

    print("PARITY — every shared control is present on both surfaces")
    for label, psel, fsel, note in CONTROLS:
        if psel is None or fsel is None:
            present = (flip if psel is None else pad).evaluate(
                EXISTS, fsel if psel is None else psel)["found"]
            check(f"{label} — declared {'Flip' if psel is None else 'Pad'}-only", present, note)
            other = (pad if psel is None else flip).evaluate(
                EXISTS, fsel or psel)["found"] if (fsel or psel) else False
            continue
        pi = pad.evaluate(EXISTS, psel)
        fi = flip.evaluate(EXISTS, fsel)
        check(f"{label} exists on both", pi["found"] and fi["found"],
              f"pad {psel}={pi['found']}, flip {fsel}={fi['found']}")

    print("\nPARITY — shared controls offer the same choices")
    for label, psel, fsel, note in CONTROLS:
        if psel is None or fsel is None:
            continue
        pi, fi = pad.evaluate(EXISTS, psel), flip.evaluate(EXISTS, fsel)
        if not (pi["found"] and fi["found"]):
            continue
        # Only controls whose CHOICES are the same feature on both surfaces.
        # Help and Report contain per-surface prose, and asserting that Pad's
        # help text matches Flip's would demand the two surfaces stop being
        # different, which is the opposite of the goal.
        if label in SAME_OPTIONS and (pi["opts"] or fi["opts"]):
            check(f"{label} offers the same options",
                  pi["opts"] == fi["opts"],
                  f"pad [{pi['opts']}] against flip [{fi['opts']}]")
        if pi["type"] == "range" or fi["type"] == "range":
            if note == "@range-differs":
                check(f"{label} still spans its declared per-surface range",
                      (pi["min"], pi["max"]) == ("1", "30")
                      and (fi["min"], fi["max"]) == ("2", "34"),
                      f"pad {pi['min']}-{pi['max']}, flip {fi['min']}-{fi['max']} "
                      "— declared in _skribl_draw_drawer.html; update both together")
            else:
                check(f"{label} spans the same range",
                      (pi["min"], pi["max"], pi["step"]) == (fi["min"], fi["max"], fi["step"]),
                      f"pad {pi['min']}-{pi['max']} step {pi['step']} against "
                      f"flip {fi['min']}-{fi['max']} step {fi['step']}")
        if pi["accept"] or fi["accept"]:
            check(f"{label} accepts the same file types",
                  pi["accept"] == fi["accept"],
                  "a format one surface takes and the other refuses is drift a "
                  "user meets as a broken upload")

    # ---- behaviour ---------------------------------------------------------
    # Structure parity says the controls are both THERE. An extraction has to
    # preserve what they DO, and that is where two independent implementations
    # actually diverge. Everything below drives the same user action on both
    # surfaces and compares the outcome, not the code.
    print("\nPARITY — the shared draw drawer behaves the same")
    pad.click("#colorOpenBtn")
    flip.click("#colorCurrent")
    pad.wait_for_timeout(400)
    flip.wait_for_timeout(400)

    # offsetParent, not .hidden: an author `display` beats the UA [hidden] rule,
    # which is how a bar stayed on screen for four versions while reporting
    # hidden === true.
    shown = "() => { const e = document.getElementById('drawPanel');" \
            " return !!e && e.offsetParent !== null; }"
    check("the draw drawer opens on both",
          pad.evaluate(shown) and flip.evaluate(shown),
          f"pad={pad.evaluate(shown)}, flip={flip.evaluate(shown)}")

    # Exactly one. `classList.toggle(name, undefined)` TOGGLES rather than
    # setting, which once left two swatches looking selected at the same time.
    sel = "() => document.querySelectorAll('#colorGroup .color-dot.active').length"
    ps, fs = pad.evaluate(sel), flip.evaluate(sel)
    check("exactly one colour reads as selected on both", ps == 1 and fs == 1,
          f"pad {ps} selected, flip {fs}")

    # Recent colours: same cap, same ordering, same de-duplication — three
    # things two independent implementations can each get right differently.
    feed = """(n) => { const hexes = ['#112233','#223344','#334455','#445566',
                                      '#556677','#667788','#778899','#8899aa'];
        hexes.slice(0, n).forEach(h => addRecent(h));
        return { count: recentColors.length, first: recentColors[0] || '' }; }"""
    pr, fr = pad.evaluate(feed, 8), flip.evaluate(feed, 8)
    check("recent colours keep the same number on both",
          pr["count"] == fr["count"],
          f"pad keeps {pr['count']}, flip keeps {fr['count']} — a cap that "
          "differs by surface is drift a user meets as a vanishing colour")
    check("and put the most recent first on both",
          pr["first"] == fr["first"],
          f"pad {pr['first']!r}, flip {fr['first']!r}")

    dedupe = "() => { addRecent('#abcdef'); const before = recentColors.length;" \
             " addRecent('#abcdef'); return [before, recentColors.length]; }"
    pd, fd = pad.evaluate(dedupe), flip.evaluate(dedupe)
    check("re-using a colour does not duplicate it, on either surface",
          pd[0] == pd[1] and fd[0] == fd[1],
          f"pad {pd}, flip {fd}")

    # Found by reading the two implementations side by side, which the
    # assertions above did not reach: Pad validated and lower-cased, Flip did
    # neither; Pad labelled swatches for screen readers, Flip set only a title.
    # Checks CONTENTS, not length: once the list is full at six, adding three
    # invalid entries leaves the length unchanged whether they were rejected or
    # stored, so a length assertion here passes without testing anything.
    junk = """() => { addRecent('nonsense'); addRecent('#GGGGGG'); addRecent('');
        return recentColors.filter(c => !/^#[0-9a-f]{6}$/i.test(c)); }"""
    pj, fj = pad.evaluate(junk), flip.evaluate(junk)
    check("neither surface stores a colour that is not a colour",
          pj == [] and fj == [],
          f"pad kept {pj}, flip kept {fj} — an unvalidated entry renders as a "
          "transparent swatch that sets the pen to nothing")

    casing = """() => { addRecent('#AABBCC'); return recentColors[0]; }"""
    pc2, fc2 = pad.evaluate(casing), flip.evaluate(casing)
    check("both normalise casing, so the same colour cannot appear twice",
          pc2 == fc2 == "#aabbcc", f"pad {pc2!r}, flip {fc2!r}")

    labelled = """() => { const b = document.querySelector('#recentColors .recent-swatch');
        return !!b && !!b.getAttribute('aria-label'); }"""
    pl, fl = pad.evaluate(labelled), flip.evaluate(labelled)
    check("recent swatches are labelled for screen readers on both",
          pl and fl, f"pad={pl}, flip={fl} — a title attribute is not an "
          "accessible name on a touch device")

    # Found by reading the two setters side by side: Pad validated and
    # lower-cased, Flip accepted any string — so setColor('nonsense') made the
    # pen a colour the canvas cannot paint with, and '#FF0000' did not match the
    # '#ff0000' swatch it IS.
    setc = """(hex) => { const fn = (typeof setPenColor === 'function') ? setPenColor : setColor;
        const before = color; fn(hex); return [before, color]; }"""
    for bad in ("nonsense", "#GGGGGG", "", "#12345"):
        pb, fb = pad.evaluate(setc, bad), flip.evaluate(setc, bad)
        check(f"neither surface accepts {bad or '(empty)'!r} as a colour",
              pb[0] == pb[1] and fb[0] == fb[1],
              f"pad {pb}, flip {fb} — an invalid pen colour paints nothing and "
              "is only noticed when a stroke fails to appear")

    pu, fu = pad.evaluate(setc, "#AABBCC"), flip.evaluate(setc, "#AABBCC")
    check("both normalise the case of an accepted colour",
          pu[1] == fu[1] == "#aabbcc", f"pad {pu[1]!r}, flip {fu[1]!r}")

    sel_after = "() => document.querySelectorAll('#colorGroup .color-dot.active').length"
    check("and still exactly one swatch reads as selected on both",
          pad.evaluate(sel_after) <= 1 and flip.evaluate(sel_after) <= 1,
          f"pad {pad.evaluate(sel_after)}, flip {flip.evaluate(sel_after)}")

    print("\nPARITY — colour selection runs through ONE shared implementation")
    # WHY THIS SECTION EXISTS, given the section above already passes.
    #
    # Everything above asserts that the two surfaces BEHAVE alike: they reject
    # the same junk, normalise the same casing, ring exactly one swatch. Every
    # one of those assertions would still pass if someone deleted
    # lib/colorselect.js and pasted the logic back into app.js and flip.js —
    # which is precisely the state the extraction was done to end, and
    # precisely the state that produced the original bug. Behavioural parity is
    # a snapshot; it says the copies agree TODAY, not that there is one copy.
    #
    # So this section asserts the extraction itself: one module, loaded by
    # both, and actually ON the path each editor's setter takes. The module
    # entered the archive unreviewed and was covered only by verify_ux.py,
    # which greps its source text and drives the swatch state — neither of
    # which notices a surface quietly re-inlining its own copy.
    lib_api = ("() => window.SkriblColorSelect ? Object.keys("
               "window.SkriblColorSelect).filter(k => typeof "
               "window.SkriblColorSelect[k] === 'function').sort() : null")
    pa, fa = pad.evaluate(lib_api), flip.evaluate(lib_api)
    check("the shared colour selector is loaded on both surfaces",
          pa == fa == ["apply", "normalise"],
          f"pad {pa}, flip {fa} — both setters are guarded with "
          "`window.SkriblColorSelect &&`, so a module that fails to load does "
          "not throw: colour selection silently stops working instead")

    # The ?v= is a content hash of the file, so equal query strings mean the
    # two surfaces are served the same BYTES, not merely the same path. A fork
    # that copied the file to a second name would still satisfy a path check.
    src_of = ("() => [...document.querySelectorAll('script[src]')]"
              ".map(s => s.getAttribute('src'))"
              ".filter(s => s && s.indexOf('colorselect') !== -1)")
    psrc, fsrc = pad.evaluate(src_of), flip.evaluate(src_of)
    check("and both load it from one URL, content hash included",
          len(psrc) == 1 and psrc == fsrc,
          f"pad {psrc}, flip {fsrc} — two URLs is two files, and two files "
          "drift; the ?v= is a hash of the contents, so it differs the moment "
          "the copies do")

    # Function source text is the cheapest available proof that these are the
    # same implementation rather than two that currently agree.
    fn_src = ("() => window.SkriblColorSelect ? String("
              "window.SkriblColorSelect.apply) + String("
              "window.SkriblColorSelect.normalise) : ''")
    check("and it is the same implementation on both, not two that agree",
          pad.evaluate(fn_src) == flip.evaluate(fn_src) != "",
          "identical behaviour from two sources is a coincidence with an "
          "expiry date")

    # The contract, asserted directly on the module rather than through a
    # surface, so a caller that stops using it cannot mask a regression here.
    norm = ("() => ['#AABBCC', '  #aabbcc  ', '#abc', 'nonsense', '', "
            "'#GGGGGG', null].map(v => window.SkriblColorSelect.normalise(v))")
    want = ["#aabbcc", "#aabbcc", None, None, None, None, None]
    pn, fn = pad.evaluate(norm), flip.evaluate(norm)
    check("normalise agrees with itself on both surfaces",
          pn == fn == want, f"pad {pn}, flip {fn}")

    # `matched` is not decoration: Pad feeds recents on `!matched`, so a module
    # that reported every colour as matched would silently stop recording
    # custom colours — a failure with no error and no visible cause.
    contract = """(preset) => {
        const g = document.getElementById('colorGroup');
        const S = window.SkriblColorSelect;
        const hit = S.apply(g, preset.toUpperCase());
        const custom = S.apply(g, '#0b0c0d');
        return { hitHex: hit && hit.hex, hitMatched: !!(hit && hit.matched),
                 customHex: custom && custom.hex,
                 customMatched: !!(custom && custom.matched) }; }"""
    presets = pad.evaluate("() => [...document.querySelectorAll("
                           "'#colorGroup .color-dot[data-color]')]"
                           ".map(d => d.dataset.color)")
    preset0 = presets[0] if presets else "#ffffff"
    pcon, fcon = pad.evaluate(contract, preset0), flip.evaluate(contract, preset0)
    check("apply reports a preset as matched and a custom colour as not",
          pcon == fcon and pcon["hitMatched"] and not pcon["customMatched"]
          and pcon["hitHex"] == preset0.lower()
          and pcon["customHex"] == "#0b0c0d",
          f"pad {pcon}, flip {fcon} — Pad decides whether to remember a colour "
          "from `matched`, so getting this wrong loses recents silently")

    # Refusing must leave the swatches ALONE. A half-applied selection — ring
    # cleared, colour not set — is worse than refusing outright, because the
    # user sees no selected colour and nothing explains why.
    untouched = """() => {
        const g = document.getElementById('colorGroup');
        const before = [...g.querySelectorAll('.color-dot.active')]
                         .map(d => d.dataset.color || '(custom)');
        const r = window.SkriblColorSelect.apply(g, 'nonsense');
        const after = [...g.querySelectorAll('.color-dot.active')]
                        .map(d => d.dataset.color || '(custom)');
        return { refused: r === null, same: before.join() === after.join(),
                 before: before, after: after }; }"""
    pu2, fu2 = pad.evaluate(untouched), flip.evaluate(untouched)
    check("an invalid colour is refused without disturbing the swatches",
          pu2["refused"] and pu2["same"] and fu2["refused"] and fu2["same"],
          f"pad {pu2}, flip {fu2}")

    # Strictly one, not `<= 1`: zero active swatches passes a `<= 1` check and
    # is its own bug — the state the custom-swatch toggle produced.
    exactly_one = """(preset) => {
        window.SkriblColorSelect.apply(
            document.getElementById('colorGroup'), preset);
        return document.querySelectorAll(
            '#colorGroup .color-dot.active').length; }"""
    pe, fe = pad.evaluate(exactly_one, preset0), flip.evaluate(exactly_one, preset0)
    check("applying a preset leaves exactly one swatch active on both",
          pe == fe == 1, f"pad {pe}, flip {fe} — zero would satisfy `<= 1`")

    # THE ROUTING ASSERTION. This is the one that fails if a surface re-inlines
    # its own copy: everything else here tests the module, and a module can sit
    # in the tree, load correctly and pass all of it while no editor calls it.
    # The spy delegates to the original and is restored in a `finally`, so the
    # surface is left exactly as it was found.
    spy = """(hex) => {
        const S = window.SkriblColorSelect;
        const orig = S.apply;
        let calls = 0;
        S.apply = function () { calls++; return orig.apply(this, arguments); };
        try {
            const fn = (typeof setPenColor === 'function') ? setPenColor : setColor;
            fn(hex);
        } finally { S.apply = orig; }
        return calls; }"""
    for _pg, _name in ((pad, "Pad"), (flip, "Flip")):
        _before = _pg.evaluate("() => color")
        _calls = _pg.evaluate(spy, preset0)
        check(f"{_name}'s colour setter delegates to the shared module",
              _calls == 1,
              f"the setter called it {_calls} times — a surface with its own "
              "copy passes every behavioural assertion above and drifts anyway")
        # Restore the pen colour so later sections see the state they expect.
        _pg.evaluate("(hex) => { const fn = (typeof setPenColor === 'function')"
                     " ? setPenColor : setColor; fn(hex); }", _before)

    print("\nPARITY — photo fit geometry comes from ONE shared implementation")
    # WHY. Pad drew the background photo with drawPhotoFitted, Flip computed it
    # with photoRect, and the PLAYER used Pad's copy — three call sites, two
    # implementations. They agreed on cover and contain and disagreed on the
    # third mode's NAME: the shared partial carried
    #   data-fit="{{ 'fill' if kind == 'flip' else 'stretch' }}"
    # because the markup had been bent to fit two controller vocabularies.
    #
    # THE BUG THAT FOUND. flip.js posts fit:(photoFit==='fill'?'stretch':fit),
    # so 'stretch' is what the player and the database see — but Flip's restore
    # whitelist was ['cover','contain','fill'], and photoRect special-cased only
    # 'fill'. Flip could not read the value Flip writes: a 'stretch' rendered as
    # COVER, with no fit button active. Measured before the extraction, on a
    # 100x50 image: fit='stretch' gave [-204,0,1224,612], byte-identical to
    # cover, where 'fill' gave [0,0,816,612].
    fit_lib = ("() => window.SkriblPhotoFit ? Object.keys(window.SkriblPhotoFit)"
               ".filter(k => typeof window.SkriblPhotoFit[k] === 'function').sort() : null")
    pfl, ffl = pad.evaluate(fit_lib), flip.evaluate(fit_lib)
    check("the shared photo-fit module is loaded on both surfaces",
          pfl == ffl == ["normalise", "rect"], f"pad {pfl}, flip {ffl}")

    fit_src = ("() => window.SkriblPhotoFit ? String(window.SkriblPhotoFit.rect)"
               " + String(window.SkriblPhotoFit.normalise) : ''")
    check("and it is the same implementation on both, not two that agree",
          pad.evaluate(fit_src) == flip.evaluate(fit_src) != "",
          "the two copies agreed on cover and contain and diverged on the third")

    # The geometry itself, compared surface to surface across every mode. This
    # is the assertion that would have caught the original divergence.
    geom = """(a) => { const r = window.SkriblPhotoFit.rect(a.iw, a.ih, a.cw, a.ch,
        { fit: a.fit, offX: a.ox, offY: a.oy, zoom: a.z });
        return [r.x, r.y, r.w, r.h]; }"""
    for _fit in ("cover", "contain", "stretch"):
        _a = {"iw": 100, "ih": 50, "cw": 816, "ch": 612,
              "fit": _fit, "ox": 0.25, "oy": 0.75, "z": 1.5}
        _p, _f = pad.evaluate(geom, _a), flip.evaluate(geom, _a)
        check(f"both surfaces place a {_fit} photo identically", _p == _f,
              f"pad {_p}, flip {_f} — the same photo in the same post must not "
              "land in two places depending on which editor drew it")

    # 'fill' is Flip's local spelling of 'stretch'. They must be one mode, not
    # two: the third button is data-fit='fill' on Flip and 'stretch' on Pad.
    _alias = {"iw": 100, "ih": 50, "cw": 816, "ch": 612, "ox": 0.5, "oy": 0.5, "z": 1}
    _s = flip.evaluate(geom, dict(_alias, fit="stretch"))
    _fl = flip.evaluate(geom, dict(_alias, fit="fill"))
    _cv = flip.evaluate(geom, dict(_alias, fit="cover"))
    check("'fill' and 'stretch' are one mode, not two",
          _s == _fl and _s != _cv,
          f"stretch {_s}, fill {_fl}, cover {_cv} — Flip posts 'stretch' and "
          "used to read it back as cover, silently changing the image on reload")

    check("an unknown fit degrades to cover rather than to nothing",
          pad.evaluate(geom, dict(_alias, fit="wat")) == _cv
          and flip.evaluate(geom, dict(_alias, fit="wat")) == _cv,
          "both surfaces already defaulted to cover; that must not change")

    # Degenerate input must not produce NaN coordinates: a zero-width image is
    # not a reason to draw at a position nobody can debug.
    _nan = ("(a) => { const r = window.SkriblPhotoFit.rect(a.iw, a.ih, a.cw, a.ch, {fit:'cover'});"
            " return [r.x, r.y, r.w, r.h].every(v => Number.isFinite(v)); }")
    for _bad in ({"iw": 0, "ih": 50, "cw": 816, "ch": 612},
                 {"iw": 100, "ih": 50, "cw": 0, "ch": 0}):
        check(f"a degenerate size still yields finite coordinates {_bad['iw']}x{_bad['ih']}",
              pad.evaluate(_nan, _bad) and flip.evaluate(_nan, _bad),
              "NaN in a drawImage call paints nothing and reports no error")

    # ROUTING. As with colorselect, everything above tests the MODULE, and a
    # module can sit in the tree passing all of it while no surface calls it.
    fit_spy = """() => {
        const S = window.SkriblPhotoFit;
        const orig = S.rect;
        let calls = 0;
        S.rect = function () { calls++; return orig.apply(this, arguments); };
        try { photoRect(100, 50); } catch (e) { /* Pad has no photoRect */ }
        finally { S.rect = orig; }
        return calls; }"""
    check("Flip's photoRect delegates to the shared module",
          flip.evaluate(fit_spy) == 1,
          "a surface with its own copy of the geometry passes every assertion "
          "above and drifts anyway")

    print("\nPARITY — loop trim obeys ONE clamp rule and ONE cap")
    # WHY. The 20-second cap was a NAMED CONSTANT on Flip (MAX_LOOP_SECONDS,
    # nine uses) and a BARE 20 on Pad, eight times, with no constant in the
    # file. Changing it meant one edit on one surface and eight on the other,
    # and nothing failed if the second was missed — the surfaces would simply
    # have allowed different loop lengths.
    #
    # THE DRIFT THAT FOUND. Flip re-clamped the cap inside updateTrimUI, with a
    # comment calling it "the single choke point ... so the <=20s invariant
    # can't be bypassed". Pad had no such line: it enforced the cap in its drag
    # and nudge paths ONLY, so a loop arriving any other way — a load, a draft
    # restore, a re-add — kept whatever length it came with. Measured: a 60s
    # loop through updateTrimUI stayed 60s on Pad and became 20s on Flip.
    trim_lib = ("() => window.SkriblLoopTrim ? [window.SkriblLoopTrim.MAX_LOOP_SECONDS,"
                " window.SkriblLoopTrim.MIN_LOOP_SECONDS] : null")
    pt, ft = pad.evaluate(trim_lib), flip.evaluate(trim_lib)
    check("both surfaces read the loop bounds from one shared module",
          pt == ft == [20, 0.5], f"pad {pt}, flip {ft}")

    check("and neither still carries a hardcoded cap in its trim paths",
          not any("trimEnd - trimStart > 20" in _src or "trimEnd-trimStart>20" in _src
                  for _src in (_read_static("app.js"), _read_static("flip.js"))),
          "a magic number in one surface and a constant in the other is how "
          "the two came to allow different loop lengths")

    # The clamp rule itself, compared surface to surface. Both modes, both
    # handles, including the over-cap case that is the whole point.
    clamp = """(a) => { const r = window.SkriblLoopTrim.setHandle(
        { start: a.s, end: a.e, duration: a.d }, a.w, a.t, a.m);
        return [r.start, r.end]; }"""
    for _mode in ("constrain", "slide"):
        for _w in ("start", "end"):
            _a = {"s": 5, "e": 30, "d": 120, "w": _w, "t": 0 if _w == "start" else 90,
                  "m": _mode}
            _p, _f = pad.evaluate(clamp, _a), flip.evaluate(clamp, _a)
            check(f"both clamp a {_mode} drag of the {_w} handle identically",
                  _p == _f and round(_p[1] - _p[0], 6) <= 20,
                  f"pad {_p}, flip {_f}")

    # The two modes must actually DIFFER, or the parameter is decoration and
    # the call sites have quietly converged on one behaviour.
    _over = {"s": 0, "e": 30, "d": 120, "w": "start", "t": 0}
    _c = pad.evaluate(clamp, dict(_over, m="constrain"))
    _s2 = pad.evaluate(clamp, dict(_over, m="slide"))
    check("'constrain' holds the far end still and 'slide' moves it",
          _c[1] == 30 and _s2[1] == 20 and _c != _s2,
          f"constrain {_c}, slide {_s2} — the main track constrains, the zoom "
          "track and nudge slide; declared, not accidental")

    # THE CHOKE POINT. This is the assertion that reproduces the old Pad bug.
    cap = """() => {
        audioDuration = 120; trimStart = 0; trimEnd = 60;
        try { updateTrimUI(); } catch (e) { return -1; }
        return trimEnd - trimStart; }"""
    _pc, _fc = pad.evaluate(cap), flip.evaluate(cap)
    check("a 60s loop is capped to 20s on BOTH surfaces, not just Flip",
          _pc == _fc == 20,
          f"pad kept {_pc}s, flip kept {_fc}s — Pad enforced the cap on drag "
          "and nudge only, so a loop from a load or a draft restore kept its "
          "length and travelled in the payload")

    check("Pad's trim clamp delegates to the shared module",
          pad.evaluate("""() => {
              // nudgeTrim returns early on !audioEl, so the preconditions have
              // to be established or the spy reads 0 and looks like drift. A
              // guard short-circuiting the call is the commonest false
              // negative for an assertion shaped like this one.
              audioEl = audioEl || {};
              audioDuration = 120; trimStart = 5; trimEnd = 10;
              const S = window.SkriblLoopTrim; const orig = S.setHandle;
              let calls = 0;
              S.setHandle = function () { calls++; return orig.apply(this, arguments); };
              try { nudgeTrim('start', 1); } catch (e) { return 'threw: ' + e; }
              finally { S.setHandle = orig; }
              return calls; }""") == 1,
          "a surface with its own copy of the arithmetic passes everything "
          "above and drifts anyway")

    print("\nPARITY — brush and smoothing respond the same")
    for label, psel, fsel in (("brush size", "#brushSizeRange", "#size"),):
        setv = """(sel) => { const e = document.querySelector(sel);
            const mid = Math.round((+e.min + +e.max) / 2);
            e.value = mid; e.dispatchEvent(new Event('input', {bubbles:true}));
            return mid; }"""
        pv, fv = pad.evaluate(setv, psel), flip.evaluate(setv, fsel)
        pad.wait_for_timeout(200); flip.wait_for_timeout(200)
        pt = pad.text_content("#brushSizeVal") or ""
        ft = flip.text_content("#sizeVal") or ""
        check(f"{label} updates its readout on both",
              str(pv) in pt and str(fv) in ft,
              f"pad readout {pt!r} for {pv}, flip {ft!r} for {fv}")

    onecount = "(sel) => document.querySelectorAll(sel + ' .smooth-btn.active').length"
    check("exactly one smoothing option reads as selected on both",
          pad.evaluate(onecount, "#smoothSeg") == 1
          and flip.evaluate(onecount, "#smoothSeg") == 1,
          f"pad {pad.evaluate(onecount, '#smoothSeg')}, "
          f"flip {flip.evaluate(onecount, '#smoothSeg')}")

    click_last = """(sel) => { const bs = document.querySelectorAll(sel + ' button');
        bs[bs.length - 1].click(); return bs.length; }"""
    pad.evaluate(click_last, "#smoothSeg"); flip.evaluate(click_last, "#smoothSeg")
    pad.wait_for_timeout(250); flip.wait_for_timeout(250)
    # The mapping level -> alpha was three magic numbers written out twice and
    # asserted nowhere: both surfaces could have drifted to different stabilizer
    # strengths and every existing assertion would still have passed.
    alphas = """() => { const out = [];
        document.querySelectorAll('#smoothSeg .smooth-btn').forEach(b => {
            b.click(); out.push([b.dataset.smooth, smoothingAlpha]); });
        return out; }"""
    pa2, fa2 = pad.evaluate(alphas), flip.evaluate(alphas)
    check("each smoothing level maps to the same stabilizer strength on both",
          pa2 == fa2 and len(pa2) > 1,
          f"pad {pa2}, flip {fa2}")

    check("choosing a smoothing option moves the selection, not adds to it",
          pad.evaluate(onecount, "#smoothSeg") == 1
          and flip.evaluate(onecount, "#smoothSeg") == 1,
          f"pad {pad.evaluate(onecount, '#smoothSeg')}, "
          f"flip {flip.evaluate(onecount, '#smoothSeg')}")

    print("\nPARITY — the eyedropper's tap-to-sample path")
    cursor_of = """(sel) => { const c = document.querySelector(sel);
        return c ? getComputedStyle(c).cursor : '?'; }"""
    # DECLARED DIFFERENCE, and the reason this is tested with window.EyeDropper
    # removed: Pad uses the NATIVE picker when the browser has one and returns
    # early, so it shows no armed state; Flip always uses the in-app path. On
    # iOS Safari — no EyeDropper — both fall back to tap-to-sample, and that
    # shared path is what most phone users actually get. Testing it with the
    # native API present would compare an OS dialog against an in-app mode and
    # prove nothing.
    # The native window.EyeDropper branch is GONE from both surfaces. It only
    # ever existed on Chromium, so the tap-to-sample path had to exist anyway,
    # and one button behaving two ways depending on the browser is not a
    # feature. This asserts the deletion holds even where the API IS present.
    check("the browser under test does have a native picker available",
          pad.evaluate("() => typeof window.EyeDropper === 'function'"),
          "otherwise the assertion below proves nothing")

    armed = "() => document.getElementById('eyedropperBtn').classList.contains('picking')"
    # Opening idempotently. Clicking the opener unconditionally TOGGLES, so a
    # drawer left open by an earlier section gets closed by the very step meant
    # to open it — which surfaced here as "element is not visible" on a button
    # that plainly exists.
    open_draw = "() => { const p = document.getElementById('drawPanel');" \
                " return !!p && p.offsetParent !== null; }"
    pad_idle_cursor = pad.evaluate(cursor_of, "#canvas")
    flip_idle_cursor = flip.evaluate(cursor_of, "#pad")
    for surf_pg, opener in ((pad, "#colorOpenBtn"), (flip, "#colorCurrent")):
        if not surf_pg.evaluate(open_draw):
            surf_pg.click(opener)
            surf_pg.wait_for_timeout(350)
        surf_pg.click("#eyedropperBtn")
        surf_pg.wait_for_timeout(300)
    pa, fa = pad.evaluate(armed), flip.evaluate(armed)
    check("both arm tap-to-sample even where a native picker exists",
          pa and fa,
          f"pad armed={pa}, flip armed={fa} — one button must not behave two "
          "ways depending on which browser opened it")

    pressed = "() => document.getElementById('eyedropperBtn').getAttribute('aria-pressed')"
    check("and both announce the armed state, not only style it",
          pad.evaluate(pressed) == flip.evaluate(pressed) == "true",
          f"pad {pad.evaluate(pressed)!r}, flip {flip.evaluate(pressed)!r}")

    pad.keyboard.press("Escape"); flip.keyboard.press("Escape")
    pad.wait_for_timeout(250); flip.wait_for_timeout(250)
    check("Escape disarms on both",
          not pad.evaluate(armed) and not flip.evaluate(armed),
          f"pad {pad.evaluate(armed)}, flip {flip.evaluate(armed)}")
    # NOT "the crosshair goes away": Pad's idle canvas cursor IS a crosshair,
    # because it is a drawing surface. The parity statement is that each
    # surface returns to its OWN baseline — a shared state machine must not
    # leave either one wearing the armed cursor.
    check("and each returns to the cursor it had before arming",
          pad.evaluate(cursor_of, "#canvas") == pad_idle_cursor
          and flip.evaluate(cursor_of, "#pad") == flip_idle_cursor,
          f"pad {pad.evaluate(cursor_of, '#canvas')!r} against baseline "
          f"{pad_idle_cursor!r}; flip {flip.evaluate(cursor_of, '#pad')!r} "
          f"against baseline {flip_idle_cursor!r}")

    pad.click("#eyedropperBtn"); flip.click("#eyedropperBtn")
    pad.wait_for_timeout(250); flip.wait_for_timeout(250)
    pc, fc = pad.evaluate(cursor_of, "#canvas"), flip.evaluate(cursor_of, "#pad")
    check("and both say so with the cursor, not only a button class",
          pc == fc == "crosshair", f"pad {pc!r}, flip {fc!r}")

    # ---- media --------------------------------------------------------------
    # The photo and music controllers are the largest duplicated pair — 350 and
    # 131 references in app.js against 83 and 97 in flip.js — so they are what
    # an extraction will hurt most if it is unguarded. Real bytes, because the
    # interesting behaviour is downstream of a file actually decoding.
    print("\nPARITY — a photo behaves the same on both")
    IMG, AUD = png_bytes(), wav_bytes()
    vis = "(id) => { const e = document.getElementById(id); return !!e && e.offsetParent !== null; }"

    for pg_, finput in ((pad, "#photoInput"), (flip, "#imageInput")):
        open_media(pg_, "photo")
        pg_.set_input_files(finput, {"name": "t.png", "mimeType": "image/png", "buffer": IMG})
        pg_.wait_for_timeout(1300)

    check("loading a photo marks the tab on both",
          pad.evaluate(vis, "photoTabDot") and flip.evaluate(vis, "photoTabDot"),
          f"pad={pad.evaluate(vis, 'photoTabDot')}, flip={flip.evaluate(vis, 'photoTabDot')}")
    check("and reveals the same fit choices on both",
          pad.text_content("#photoFitGroup").strip()
          == flip.text_content("#photoFitGroup").strip(),
          f"pad {pad.text_content('#photoFitGroup').strip()!r} against "
          f"flip {flip.text_content('#photoFitGroup').strip()!r}")

    fit_sel = "() => document.querySelectorAll('#photoFitGroup .active, #photoFitGroup .on').length"
    check("exactly one fit option reads as chosen on both",
          pad.evaluate(fit_sel) == 1 and flip.evaluate(fit_sel) == 1,
          f"pad {pad.evaluate(fit_sel)}, flip {flip.evaluate(fit_sel)}")

    pick_last = """() => { const bs = document.querySelectorAll('#photoFitGroup button');
        bs[bs.length - 1].click(); return bs.length; }"""
    pad.evaluate(pick_last); flip.evaluate(pick_last)
    pad.wait_for_timeout(300); flip.wait_for_timeout(300)
    check("choosing a different fit moves the choice, not adds to it",
          pad.evaluate(fit_sel) == 1 and flip.evaluate(fit_sel) == 1,
          f"pad {pad.evaluate(fit_sel)}, flip {flip.evaluate(fit_sel)}")

    opacity = """() => { const r = document.querySelector('.photo-opacity-row input[type=range]');
        return r ? { min: r.min, max: r.max, step: r.step, value: r.value } : null; }"""
    po, fo = pad.evaluate(opacity), flip.evaluate(opacity)
    check("photo opacity spans the same range and starts the same",
          po is not None and po == fo, f"pad {po}, flip {fo}")

    print("\nPARITY — music behaves the same on both")
    for pg_ in (pad, flip):
        open_media(pg_, "music")
        pg_.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
        pg_.wait_for_timeout(2500)

    check("loading music marks the tab on both",
          pad.evaluate(vis, "musicTabDot") and flip.evaluate(vis, "musicTabDot"),
          f"pad={pad.evaluate(vis, 'musicTabDot')}, flip={flip.evaluate(vis, 'musicTabDot')}")
    check("the trim handles report the same start on both",
          pad.text_content("#handleStart").strip() == flip.text_content("#handleStart").strip(),
          f"pad {pad.text_content('#handleStart').strip()!r} against "
          f"flip {flip.text_content('#handleStart').strip()!r}")
    check("and the same end, so both read the same duration from the file",
          pad.text_content("#handleEnd").strip() == flip.text_content("#handleEnd").strip(),
          f"pad {pad.text_content('#handleEnd').strip()!r} against "
          f"flip {flip.text_content('#handleEnd').strip()!r}")

    # The waveform is drawn, not declared: an empty canvas next to a loaded
    # track is exactly the kind of thing an assertion on state would miss.
    painted = """() => { const c = document.getElementById('waveformCanvas');
        if (!c || !c.width) return false;
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        for (let i = 3; i < d.length; i += 4) if (d[i] !== 0) return true;
        return false; }"""
    check("the waveform is actually drawn on both",
          pad.evaluate(painted) and flip.evaluate(painted),
          f"pad={pad.evaluate(painted)}, flip={flip.evaluate(painted)}")

    disclose = """() => { document.getElementById('fineTuneToggle').click(); return true; }"""
    pad.evaluate(disclose); flip.evaluate(disclose)
    pad.wait_for_timeout(500); flip.wait_for_timeout(500)
    check("the fine-tune disclosure opens the loop detail on both",
          pad.evaluate(vis, "zoomWaveformCanvas") and flip.evaluate(vis, "zoomWaveformCanvas"),
          f"pad={pad.evaluate(vis, 'zoomWaveformCanvas')}, "
          f"flip={flip.evaluate(vis, 'zoomWaveformCanvas')}")

    nudge = """() => { const before = document.getElementById('handleStart').textContent.trim();
        const b = document.querySelector('.edge-controls .nudge-btn');
        if (!b) return null;
        b.click();
        return [before, document.getElementById('handleStart').textContent.trim()]; }"""
    pn, fn = pad.evaluate(nudge), flip.evaluate(nudge)
    check("a nudge moves the trim edge by the same amount on both",
          pn is not None and fn is not None and pn == fn,
          f"pad {pn}, flip {fn} — a nudge step that differs by surface is drift "
          "a user meets as a loop that will not line up")

    # ---- segmented pills land where they claim to --------------------------
    # Slider positioning exists three times (attachSegSlider in app.js, another
    # in flip.js, lib/segslider.js) and the copies inject a div.seg-slider while
    # the shared partial supplies a span. Consolidating them risks a pill that
    # lands in the wrong place, which nothing else here would catch.
    #
    # This measures the RENDERED pill against the RENDERED active button. Three
    # things had to be got right, each of which produced a false result first:
    #  - open panels by clicking their real opener, not by setting hidden=false;
    #    a panel revealed by fiat has a pill that was never placed, and it
    #    measured 0 wide while Pad's segs measured 0 tall.
    #  - open idempotently, because clicking an opener TOGGLES.
    #  - wait for placement: segslider positions through ResizeObserver and
    #    MutationObserver, so a same-tick measurement reads zero.
    print("\nPARITY — segmented pills sit on their selected button")

    def settle(pg_, sel, tries=20):
        for _ in range(tries):
            w = pg_.evaluate("(s) => { const p = document.querySelector(s + ' > .seg-slider');"
                             " return p ? p.getBoundingClientRect().width : 0; }", sel)
            if w > 0:
                return True
            pg_.wait_for_timeout(100)
        return False

    measure = """(sel) => {
        const g = document.querySelector(sel);
        if (!g || g.getBoundingClientRect().height === 0) return null;
        const pill = g.querySelector(':scope > .seg-slider');
        // The active marker differs by control — canvasSeg and fps use `on`,
        // smoothSeg uses `active`. Ask the DOM rather than assuming either.
        const act = g.querySelector('button.on, button.active');
        if (!pill || !act) return null;
        const p = pill.getBoundingClientRect(), a = act.getBoundingClientRect();
        return { dLeft: +(p.left - a.left).toFixed(1),
                 dWidth: +(p.width - a.width).toFixed(1) }; }"""

    def ensure_open(pg_, opener, panel):
        if not pg_.evaluate("(id) => { const e = document.getElementById(id);"
                            " return !!e && e.offsetParent !== null; }", panel):
            pg_.click(opener)
            pg_.wait_for_timeout(500)

    # smoothSeg lives in the draw drawer and the menu CLOSES that drawer, so it
    # has to be measured before the menu is opened. Measuring it after produced
    # a null that looked exactly like a positioning failure.
    groups = [("#smoothSeg", [(pad, "#colorOpenBtn", "drawPanel"),
                              (flip, "#colorCurrent", "drawPanel")]),
              ("#hintSeg",   [(pad, "#menuBtn", "menuSheet"), (flip, "#moreBtn", "moreMenu")]),
              ("#canvasSeg", [(pad, "#menuBtn", "menuSheet"), (flip, "#moreBtn", "moreMenu")])]

    for sel, openers in groups:
        for pg_, opener, panel in openers:
            ensure_open(pg_, opener, panel)
        settle(pad, sel)
        settle(flip, sel)
        pm, fm = pad.evaluate(measure, sel), flip.evaluate(measure, sel)
        check(f"{sel} pill is placed on both surfaces",
              pm is not None and fm is not None,
              f"pad {pm}, flip {fm} — a null here means the pill was never "
              "positioned, which is what forcing a panel open produces")
        if pm and fm:
            check(f"{sel} pill covers its selected button on both",
                  abs(pm["dLeft"]) <= 2 and abs(pm["dWidth"]) <= 2
                  and abs(fm["dLeft"]) <= 2 and abs(fm["dWidth"]) <= 2,
                  f"pad {pm}, flip {fm}")

    # ---- the brush ring must not chase a finger ----------------------------
    # Reported from a phone: the ring trailed the ink badly enough that a fast
    # scribble showed it lagging behind its own line. A finger is already on the
    # glass, so the ring marks nothing a touch user cannot see — and being DOM,
    # it can only ever arrive after the canvas paint.
    print("\nPARITY — the brush ring is for pointing devices, not fingers")
    ring = """(kind) => {
        const pad = document.getElementById('pad') || document.getElementById('canvas');
        const r = pad.getBoundingClientRect();
        pad.dispatchEvent(new PointerEvent('pointermove', {
            pointerType: kind, clientX: r.left + r.width / 2,
            clientY: r.top + r.height / 2, bubbles: true }));
        const c = document.querySelector('.flip-brush-cursor, #brushCursor');
        if (!c) return 'absent';
        return getComputedStyle(c).display; }"""
    shown = flip.evaluate(ring, "mouse")
    hidden = flip.evaluate(ring, "touch")
    check("a mouse gets the ring", shown != "none", f"display was {shown!r}")
    check("a finger does not", hidden == "none",
          f"display was {hidden!r} — a DOM ring cannot keep up with the ink, "
          "and a finger needs no crosshair")

    positioned = """() => { const c = document.querySelector('.flip-brush-cursor, #brushCursor');
        if (!c) return null;
        return { left: c.style.left, top: c.style.top, transform: c.style.transform }; }"""
    pos = flip.evaluate(positioned)
    check("the ring is moved by transform, not by left/top",
          pos is not None and "translate3d" in (pos["transform"] or "")
          and not pos["left"] and not pos["top"],
          f"{pos} — left/top force layout and paint every pointermove, so the "
          "ring cannot be composited independently of the stroke")

    print("\nPARITY — no surface is silently erroring on load")
    check("Pad loads without JS errors", not errs["pad"], "; ".join(errs["pad"][:2]))
    check("Flip loads without JS errors", not errs["flip"], "; ".join(errs["flip"][:2]))

    b.close()

summarise_and_exit()
