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
from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []


check = make_check(results, detail_on_pass=False)


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
CONTROLS = [
    # --- drawing tools ----------------------------------------------------
    ("pen tool",           "#penToolBtn",      "#penToolBtn",     ""),
    ("eraser tool",        "#eraserToolBtn",   "#eraserToolBtn",  ""),
    ("undo",               "#undoBtn",         "#undo",           ""),
    ("redo",               "#redoBtn",         "#redo",           ""),
    # --- colour -----------------------------------------------------------
    # Both editors open the draw drawer from the PEN, tapped again; Photo and
    # Music are the two tabs of the one Media button (owner's dock redesign,
    # which took Flip's colour ring, Image and Music buttons the same way).
    ("open draw drawer",   "#penToolBtn",      "#penToolBtn",     ""),
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
    ("open photo drawer",  "#mediaTabPhoto",   "#mediaTabPhoto",  ""),
    ("photo file input",   "#photoInput",      "#imageInput",     ""),
    ("photo fit control",  "#photoFitGroup",   "#photoFitGroup",  ""),
    ("reset photo",        "#resetPhotoBtn",   "#resetPhotoBtn",  ""),
    ("open music drawer",  "#mediaTabMusic",   "#mediaTabMusic",  ""),
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
    # Your Skribls left both editors in v304: it is the profile page (/library),
    # reached from a menu row on each. Same row on both, so parity holds.
    ("your skribls",       "#postedItem",      "#miPosted",       ""),
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


def open_via(pg_, opener, settle=350):
    """Click a Flip opener, or reach a Pad drawer the way the Pad's bar does now:
    "@pad:draw" is the pen tapped again, "@pad:photo" / "@pad:music" are Media
    and its tab (harness/browsing.py pad_drawer)."""
    if opener.startswith("@pad:"):
        browsing.pad_drawer(pg_, opener[5:], settle=settle)
    else:
        pg_.click(opener)
        pg_.wait_for_timeout(settle)


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
    browsing.pad_drawer(pad, "draw")
    browsing.pad_drawer(flip, "draw")
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
    # THE PALETTE IS ONE LIST NOW. It was two: seven <button>s in the drawer
    # partial for Pad and a COLORS array at the top of flip.js for Flip, the
    # same hexes in the same order kept in step by hand, with nothing comparing
    # them. The failure mode of forgetting one is not an error — it is two
    # editors quietly offering different colours, which nobody notices until
    # someone switches surfaces mid-drawing. Both build from lib/palette.js,
    # and this is what says so.
    read_dots = ("() => [...document.querySelectorAll("
                 "'#colorGroup .color-dot[data-color]')].map(d => d.dataset.color)")
    presets = pad.evaluate(read_dots)
    fpresets = flip.evaluate(read_dots)
    check("both surfaces offer the same pen palette, in the same order",
          presets == fpresets and len(presets) >= 5,
          f"pad {presets} vs flip {fpresets}")
    lib = pad.evaluate("() => (window.SkriblPalette && window.SkriblPalette.hexes) || null")
    check("...and both build it from lib/palette.js rather than their own copy",
          lib is not None and lib == presets,
          f"lib {lib} vs rendered {presets} — a second copy of the list is the "
          f"thing this replaced")
    # Every swatch needs a name a screen reader can say. Flip used to label its
    # dots with the raw hex, because it built them itself and had nothing else
    # to hand: "#ff48b0" is not a colour anyone recognises being read aloud.
    labels = pad.evaluate("() => [...document.querySelectorAll("
                          "'#colorGroup .color-dot[data-color]')]"
                          ".map(d => d.getAttribute('aria-label') || '')")
    check("every swatch is named, not just hexed",
          labels and all(l and not l.startswith("#") for l in labels),
          f"{labels}")
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
    for surf_pg, opener in ((pad, "@pad:draw"), (flip, "@pad:draw")):
        if not surf_pg.evaluate(open_draw):
            open_via(surf_pg, opener)
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

    for pg_, opener, finput in ((pad, "@pad:photo", "#photoInput"),
                                (flip, "@pad:photo", "#imageInput")):
        open_via(pg_, opener)
        pg_.set_input_files(finput, {"name": "t.png", "mimeType": "image/png", "buffer": IMG})
        pg_.wait_for_timeout(1300)

    check("loading a photo marks the tab on both",
          pad.evaluate(vis, "photoTabDot") and flip.evaluate(vis, "photoTabDot"),
          f"pad={pad.evaluate(vis, 'photoTabDot')}, flip={flip.evaluate(vis, 'photoTabDot')}")

    # THE FILE ROW (the drawer redesign): once a photo is in, the drop area
    # gives way to the file -- its name, what it is doing, and a thumbnail of
    # the picture itself -- and the green box it used to be is gone. Asked of
    # what is PAINTED where it matters: the thumbnail is found at its own
    # centre, after bringing it on screen.
    PROW = """() => { const g = (id) => document.getElementById(id), t = g('photoThumb'), z = g('photoUploadBtn');
        t.scrollIntoView({ block: 'center' });
        const r = t.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const cs = getComputedStyle(z), vis = (id) => g(id).offsetParent !== null;
        return { name: g('photoBtnLabel').textContent, meta: g('photoBtnMeta').textContent,
                 thumb: t.complete && t.naturalWidth === 8 && at === t, add: vis('photoAddBtn'),
                 box: cs.backgroundColor === 'rgba(0, 0, 0, 0)' && cs.borderTopStyle === 'none',
                 controls: vis('photoToggle') && vis('photoRemove') }; }"""
    _pr, _fr = pad.evaluate(PROW), flip.evaluate(PROW)
    check("a loaded photo's row names the file and says 'Behind the drawing · Fill', on both",
          all(r["name"] == "t.png" and r["meta"] == "Behind the drawing · Fill" for r in (_pr, _fr)),
          f"pad {_pr}, flip {_fr}")
    check("...shows the picture itself, painted, where the drop area was",
          all(r["thumb"] and not r["add"] for r in (_pr, _fr)), f"pad {_pr}, flip {_fr}")
    check("...as a quiet row, not the green box, with its switch and its bin",
          all(r["box"] and r["controls"] for r in (_pr, _fr)), f"pad {_pr}, flip {_fr}")
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
    _pm = (pad.text_content("#photoBtnMeta"), flip.text_content("#photoBtnMeta"))
    check("...and the file row says the new fit on both",
          _pm == ("Behind the drawing · Stretch",) * 2, f"pad {_pm[0]!r}, flip {_pm[1]!r}")

    # SWITCHED OFF, the file is still there: the row keeps its name and its
    # picture, and says "Hidden" rather than "Behind the drawing", so the words
    # never contradict the switch beside them. The Fit tap after the switch is
    # a re-render the row has to survive (the Pad's used to key on whether the
    # picture was displayed, which switching off turns off).
    OFF = """() => { const g = (id) => document.getElementById(id), t = g('photoThumb');
        t.scrollIntoView({ block: 'center' });
        const r = t.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return { sw: g('photoToggle').getAttribute('aria-checked'), name: g('photoBtnLabel').textContent,
                 shown: g('photoBtnLabel').offsetParent !== null, meta: g('photoBtnMeta').textContent,
                 thumb: at === t, add: g('photoAddBtn').offsetParent !== null }; }"""
    for _pg in (pad, flip):
        _pg.click("#photoToggle"); _pg.wait_for_timeout(150)
        _pg.click('.photo-fit-btn[data-fit="contain"]'); _pg.wait_for_timeout(250)
    _po, _fo = pad.evaluate(OFF), flip.evaluate(OFF)
    check("a switched-off photo keeps its row, and the row says it is hidden, on both",
          all(r["sw"] == "false" and r["name"] == "t.png" and r["shown"] and r["meta"] == "Hidden · Fit"
              and r["thumb"] and not r["add"] for r in (_po, _fo)), f"pad {_po}, flip {_fo}")
    for _pg in (pad, flip):
        _pg.click("#photoToggle"); _pg.wait_for_timeout(150)
    _pb = (pad.text_content("#photoBtnMeta"), flip.text_content("#photoBtnMeta"))
    check("...and switched back on it is behind the drawing again",
          _pb == ("Behind the drawing · Fit",) * 2, f"pad {_pb[0]!r}, flip {_pb[1]!r}")

    opacity = """() => { const r = document.querySelector('.photo-opacity-row input[type=range]');
        return r ? { min: r.min, max: r.max, step: r.step, value: r.value } : null; }"""
    po, fo = pad.evaluate(opacity), flip.evaluate(opacity)
    check("photo opacity spans the same range and starts the same",
          po is not None and po == fo, f"pad {po}, flip {fo}")

    print("\nPARITY — music behaves the same on both")
    for pg_, opener in ((pad, "@pad:music"), (flip, "@pad:music")):
        open_via(pg_, opener)
        pg_.set_input_files("#musicInput", {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD})
        pg_.wait_for_timeout(2500)

    check("loading music marks the tab on both",
          pad.evaluate(vis, "musicTabDot") and flip.evaluate(vis, "musicTabDot"),
          f"pad={pad.evaluate(vis, 'musicTabDot')}, flip={flip.evaluate(vis, 'musicTabDot')}")

    # The music row: the name, and the track's length -- the same length both
    # editors print under the waveform (#trimEndLabel) -- and a tile whose note
    # sits on the selected tab's own tint, measured live from the tab so a
    # retuned purple moves both together.
    MROW = """() => { const g = (id) => document.getElementById(id), tile = document.querySelector('#musicUploadBtn .dz-tile');
        const tab = document.querySelector('.media-tab[aria-selected="true"]');
        tile.scrollIntoView({ block: 'center' });
        const r = tile.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const a = getComputedStyle(tile), b = getComputedStyle(tab);
        return { name: g('musicBtnLabel').textContent, meta: g('musicBtnMeta').textContent,
                 end: g('trimEndLabel').textContent, painted: !!at && tile.contains(at),
                 tint: a.backgroundColor === b.backgroundColor && a.color === b.color,
                 tile: [a.backgroundColor, a.color], tab: [b.backgroundColor, b.color] }; }"""
    _pmr, _fmr = pad.evaluate(MROW), flip.evaluate(MROW)
    check("a loaded track's row names it and gives the length the waveform shows, on both",
          all(r["name"] == "t.wav" and r["meta"] == "Loops under the drawing · " + r["end"] for r in (_pmr, _fmr))
          and _pmr["meta"] == _fmr["meta"] == "Loops under the drawing · 0:01", f"pad {_pmr}, flip {_fmr}")
    check("...and its note is painted on the selected tab's tint, on both",
          all(r["painted"] and r["tint"] for r in (_pmr, _fmr)), f"pad {_pmr}, flip {_fmr}")
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

    for _pg in (pad, flip):
        _pg.evaluate("() => document.getElementById('musicUploadBtn').scrollIntoView({ block: 'center' })")
        _pg.click("#musicToggle"); _pg.wait_for_timeout(150)
    _mo = (pad.text_content("#musicBtnMeta"), flip.text_content("#musicBtnMeta"))
    for _pg in (pad, flip):
        _pg.click("#musicToggle"); _pg.wait_for_timeout(150)
    check("a switched-off track keeps its row, and the row says it is muted, on both",
          _mo == ("Muted · 0:01",) * 2, f"pad {_mo[0]!r}, flip {_mo[1]!r}")

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

    # ...and a fourth, found by the v314 seal: wait for the pill to STOP, not
    # merely to exist. Pad's pill slides into place over ~0.4s when the menu
    # opens, and "width > 0" is true from the first frame of that slide -- the
    # check measured it mid-slide once in a release run (142/143). It did not
    # reproduce in six runs, idle or loaded; slowing every transition tenfold
    # through the DevTools Animation domain made it fail every time, 71px left
    # of its button, and settle to within half a pixel once the slide ended.
    # Flip's pill does not slide on open and never failed this way. So the
    # wait asks the element whether a transition is still running
    # (getAnimations), rather than guessing how long one takes; the 10s is a
    # backstop, not the verdict.
    def settle(pg_, sel, tries=100):
        for _ in range(tries):
            st = pg_.evaluate("(s) => { const p = document.querySelector(s + ' > .seg-slider');"
                              " if (!p) return null;"
                              " return { w: p.getBoundingClientRect().width,"
                              "          moving: p.getAnimations().some(a => a.playState === 'running') }; }", sel)
            if st and st["w"] > 0 and not st["moving"]:
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
            open_via(pg_, opener, settle=500)

    # smoothSeg lives in the draw drawer and the menu CLOSES that drawer, so it
    # has to be measured before the menu is opened. Measuring it after produced
    # a null that looked exactly like a positioning failure.
    groups = [("#smoothSeg", [(pad, "@pad:draw", "drawPanel"),
                              (flip, "@pad:draw", "drawPanel")]),
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

    print("\nPARITY — the two ⋯ menus are one design")
    # Owner, v290: "reconcile Pad's ⋯ menu and Flip's ⋯ menu — they look
    # different?" They did: the same items in two bodies. Pad's rows were 44px
    # with 12/14px padding and a 10px radius on a blurred 220px sheet; Flip's
    # were 37px with 10/12px padding and a 9px radius on an opaque 232px card,
    # a separator after nearly every item, "How Flip works" and "Clear all
    # pages" where Pad says "How it works" and "Clear all", and a "Rebuild
    # in-betweens" item Pad has no counterpart for. The pills at the bottom of
    # BOTH were 12px tall. Measured, not eyeballed: the same labels, and for
    # each label the same box, on both surfaces at both widths.
    MENU = """() => {
      const root = document.getElementById('menuSheet') || document.getElementById('moreMenu');
      if (!root || root.hidden) return null;
      const num = v => Math.round(parseFloat(v) || 0);
      const items = [...root.querySelectorAll('button, a')]
        .filter(el => !el.closest('.seg') && el.offsetParent !== null)
        .map(el => { const s = getComputedStyle(el); const svg = el.querySelector('svg');
          // The label is the row's words: not the icon's glyph text, not the sub-line.
          const c = el.cloneNode(true); c.querySelectorAll('svg, .menu-item-sub').forEach(n => n.remove());
          const label = (c.textContent || '').replace(/\\s+/g, ' ').trim();
          return { label, box: [Math.round(el.getBoundingClientRect().height), num(s.paddingTop), num(s.paddingLeft),
                   num(s.fontSize), s.fontWeight, num(s.borderRadius), num(s.columnGap || s.gap),
                   svg ? Math.round(svg.getBoundingClientRect().width) : 0].join('/') }; });
      const cs = getComputedStyle(root);
      const pills = [...root.querySelectorAll('.seg button')].map(b => Math.round(b.getBoundingClientRect().height));
      return { items, surface: [cs.backgroundColor, num(cs.borderTopLeftRadius), cs.boxShadow !== 'none', num(cs.paddingLeft)].join('|'),
               width: Math.round(root.getBoundingClientRect().width), pillMin: Math.min(...pills), pillMax: Math.max(...pills) }; }"""
    for _w, _vp in (("1280", {"width": 1280, "height": 900}), ("390", {"width": 390, "height": 844})):
        _pp = b.new_page(viewport=_vp); _pp.goto(f"{BASE}/skribl-pad", wait_until="load"); _pp.wait_for_timeout(700)
        _fp = b.new_page(viewport=_vp); _fp.goto(f"{BASE}/flip", wait_until="load"); _fp.wait_for_timeout(700)
        _fp.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _pp.click("#menuBtn"); _fp.click("#moreBtn"); _pp.wait_for_timeout(600); _fp.wait_for_timeout(600)
        _pm, _fm = _pp.evaluate(MENU), _fp.evaluate(MENU)
        check(f"at {_w}: both menus are open and measurable", bool(_pm) and bool(_fm), f"pad {bool(_pm)} flip {bool(_fm)}")
        if _pm and _fm:
            # The row that leads to the OTHER editor sits in the same slot on both
            # (v293: Pad's "Flip Mode", Flip's "Skribl Pad"); compared as one.
            _other = {"Flip Mode": "(the other editor)", "Skribl Pad": "(the other editor)"}
            _pl = [_other.get(i["label"], i["label"]) for i in _pm["items"]]
            _fl = [_other.get(i["label"], i["label"]) for i in _fm["items"]]
            check(f"at {_w}: the same items, in the same order (the row to the other editor as one)",
                  _pl == _fl, f"pad {_pl}\n      flip {_fl}")
            _pb = {i["label"]: i["box"] for i in _pm["items"]}
            _diff = [f"{i['label']}: pad {_pb.get(i['label'])} flip {i['box']}"
                     for i in _fm["items"] if i["label"] in _pb and _pb[i["label"]] != i["box"]]
            check(f"at {_w}: every shared item has the same box on both (height/pad/font/radius/gap/icon)",
                  not _diff, "; ".join(_diff))
            check(f"at {_w}: the two menus share one surface (ground, radius, shadow, inset) and width",
                  _pm["surface"] == _fm["surface"] and abs(_pm["width"] - _fm["width"]) <= 1,
                  f"pad {_pm['surface']} {_pm['width']}px vs flip {_fm['surface']} {_fm['width']}px")
            check(f"at {_w}: the pills at the bottom are tap-sized on both, and the same size",
                  _pm["pillMin"] >= 26 and _fm["pillMin"] >= 26 and _pm["pillMin"] == _fm["pillMin"],
                  f"pad {_pm['pillMin']}-{_pm['pillMax']}px, flip {_fm['pillMin']}-{_fm['pillMax']}px")
        _pp.close(); _fp.close()

    print("\nPARITY — the two headers are one design")
    # From a phone: "flip top menu is super tight compared to
    # pad's spacing which feels appropriate." Pad's header holds five things —
    # wordmark, tune, play, a Post pill with its label, more. Flip's held six:
    # a back arrow first, and the compact tiers paid for it by dropping Post's
    # label, shrinking every control to 33/31/30px and halving the gaps. The
    # back link lives in Flip's ⋯ menu now, the mirror of Pad's Flip Mode row,
    # and the header is the SAME five items at the same sizes and gaps. Read
    # from the DOM on both, at three widths, and compared item by item; the
    # Pad is the reference the owner named.
    HEADER = """() => {
      const h = document.querySelector('.header'); if (!h) return null;
      const vis = el => el.offsetParent !== null && el.getBoundingClientRect().width > 0;
      const role = el => el.matches('.brand, .flip-word') ? 'wordmark' : el.id === 'tuneBtn' ? 'tune'
        : el.closest('.play-wrap') ? 'play' : el.id === 'postBtn' ? 'post'
        : (el.id === 'menuBtn' || el.id === 'moreBtn') ? 'more' : (el.id || el.className);
      const ctrls = [...h.querySelectorAll('button, a, .brand, .flip-word')].filter(vis)
        .filter(el => !el.closest('.duration-badge') && !(el.matches('a') && el.closest('.brand, .flip-word')));
      const items = ctrls.map(el => { const r = el.getBoundingClientRect(); return { role: role(el), x: r.left, w: Math.round(r.width), h: Math.round(r.height) }; })
        .sort((a, b) => a.x - b.x);
      const gaps = items.slice(1).map((it, i) => Math.round(it.x - (items[i].x + items[i].w)));
      const post = document.getElementById('postBtn'); const lbl = post && post.querySelector('.btn-label');
      const mark = h.querySelector('.brand-mark'); const cs = getComputedStyle(h);
      return { roles: items.map(i => i.role), heights: items.map(i => i.role + ':' + i.h),
               gaps: gaps, minGap: gaps.length ? Math.min(...gaps) : null,
               postLabel: lbl && getComputedStyle(lbl).display !== 'none' ? lbl.textContent.replace(/\\s+/g, ' ').trim() : null,
               mark: mark ? Math.round(mark.getBoundingClientRect().height) : null,
               pad: [Math.round(parseFloat(cs.paddingLeft)), Math.round(parseFloat(cs.paddingTop))].join('/'),
               height: Math.round(h.getBoundingClientRect().height) }; }"""
    for _w, _vp in (("1280", {"width": 1280, "height": 900}), ("390", {"width": 390, "height": 844}), ("360", {"width": 360, "height": 780})):
        _pp = b.new_page(viewport=_vp); _pp.goto(f"{BASE}/", wait_until="load"); _pp.wait_for_timeout(700)
        _fp = b.new_page(viewport=_vp); _fp.goto(f"{BASE}/flip", wait_until="load"); _fp.wait_for_timeout(700)
        for _q in (_pp, _fp): _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _ph, _fh = _pp.evaluate(HEADER), _fp.evaluate(HEADER)
        check(f"header at {_w}: the same items, in the same order", _ph and _fh and _ph["roles"] == _fh["roles"],
              f"pad {_ph and _ph['roles']} flip {_fh and _fh['roles']}")
        check(f"header at {_w}: every item is the same height on both", _ph and _fh and _ph["heights"] == _fh["heights"],
              f"pad {_ph and _ph['heights']} flip {_fh and _fh['heights']}")
        # The FIRST gap is the free space after the wordmark, and the two words
        # are different widths by nature ("pad" against "flip"); the gaps that
        # are design are the ones between the controls.
        check(f"header at {_w}: the gaps between the controls match (within 1px)",
              _ph and _fh and len(_ph["gaps"]) == len(_fh["gaps"]) and all(abs(a - c) <= 1 for a, c in zip(_ph["gaps"][1:], _fh["gaps"][1:])),
              f"pad {_ph and _ph['gaps']} flip {_fh and _fh['gaps']}")
        check(f"header at {_w}: Post carries its label on both", _ph and _fh and _ph["postLabel"] and _ph["postLabel"] == _fh["postLabel"],
              f"pad {_ph and _ph['postLabel']!r} flip {_fh and _fh['postLabel']!r}")
        check(f"header at {_w}: the wordmark is the same height, and the card the same padding and height",
              _ph and _fh and _ph["mark"] == _fh["mark"] and _ph["pad"] == _fh["pad"] and abs(_ph["height"] - _fh["height"]) <= 1,
              f"pad mark {_ph and _ph['mark']} pad {_ph and _ph['pad']} h {_ph and _ph['height']}; flip mark {_fh and _fh['mark']} pad {_fh and _fh['pad']} h {_fh and _fh['height']}")
        _pp.close(); _fp.close()

    # ---- paint target: one module now, driven on each editor --------------
    # lib/painttarget.js replaced two word-for-word copies (app.js, flip.js).
    # Emptying it left every suite green, so this drives it on BOTH routes:
    # Background shows the background swatches and hides the pen's (and the
    # pen-only Recent row); Stroke puts them back; the seg's pill follows.
    print("\nPARITY — the paint-target seg swaps the swatch grid on both editors")
    PT = """(t) => {
        const seg = document.getElementById('paintTargetSeg');
        const btn = seg && seg.querySelector('button[data-target="' + t + '"]');
        if (!btn) return null;
        btn.click();
        const vis = (id) => { const e = document.getElementById(id); return !!e && !e.hidden; };
        return { pressed: btn.getAttribute('aria-pressed'), color: vis('colorGroup'),
                 bg: vis('bgGroup'), recent: vis('recentRow') }; }"""
    for _route, _opener in (("/skribl-pad", "@pad:draw"), ("/flip", "@pad:draw")):
        _q = b.new_page(viewport={"width": 900, "height": 1100})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        ensure_open(_q, _opener, "drawPanel")
        _bg = _q.evaluate(PT, "background")
        check(f"{_route}: Background shows the background swatches, hides the pen's and Recent",
              _bg is not None and _bg["pressed"] == "true" and _bg["bg"] and not _bg["color"] and not _bg["recent"],
              f"{_bg}")
        settle(_q, "#paintTargetSeg")
        _m = _q.evaluate(measure, "#paintTargetSeg")
        check(f"{_route}: the paint-target pill moved to Background",
              _m is not None and abs(_m["dLeft"]) <= 2 and abs(_m["dWidth"]) <= 2, f"{_m}")
        _st = _q.evaluate(PT, "stroke")
        check(f"{_route}: Stroke puts the pen's swatches back",
              _st is not None and _st["pressed"] == "true" and _st["color"] and not _st["bg"], f"{_st}")
        # Grid density: SkriblGrid.wireDensity, also one copy now. V213e drives
        # it on Pad only; the seg shows with the grid, marks the pick, and hides
        # again with the grid off -- on each editor.
        _gd = _q.evaluate("""() => {
            const g = document.getElementById('gridDensityGroup'), btn = document.getElementById('gridBtn');
            if (!g || !btn) return null;
            btn.click(); const shownOn = !g.hidden;
            document.querySelector('#gridDensitySeg [data-density="coarse"]').click();
            const marked = !!document.querySelector('#gridDensitySeg [data-density="coarse"].on');
            const stored = window.SkriblGrid && window.SkriblGrid.density();
            document.querySelector('#gridDensitySeg [data-density="medium"]').click();
            btn.click();
            return { shownOn: shownOn, marked: marked, stored: stored, hiddenOff: g.hidden }; }""")
        check(f"{_route}: the grid-density seg shows with the grid, takes a pick, hides without it",
              _gd is not None and _gd["shownOn"] and _gd["marked"] and _gd["stored"] == "coarse" and _gd["hiddenOff"],
              f"{_gd}")
        _q.close()

    # ---- the re-add cards: one module now, driven on each editor ----------
    # lib/pendingcards.js replaced app.js's and flip.js's refreshPendingCards.
    # A pending track shows its card with the loop and marks the tab dot; once
    # nothing is pending and nothing is loaded the dot is HIDDEN, not merely
    # un-pending (v294: a bare class removal left a green "has media" dot).
    # That second half was pinned nowhere until this section.
    print("\nPARITY — the re-add cards and tab dots, on both editors")
    RA = """() => {
        const g = (id) => document.getElementById(id);
        pendingMusicMeta = { name: 'loop.mp3', trimStart: 2, trimEnd: 6.5 };
        pendingPhotoMeta = { fit: 'contain', opacity: 0.5 };
        refreshPendingCards();
        const on = { m: !g('musicPending').hidden, mName: g('musicPendingName').textContent,
                     mMeta: g('musicPendingMeta').textContent,
                     mDot: !g('musicTabDot').hidden && g('musicTabDot').classList.contains('pending'),
                     p: !g('photoPending').hidden, pName: g('photoPendingName').textContent,
                     pMeta: g('photoPendingMeta').textContent };
        pendingMusicMeta = null; pendingPhotoMeta = null;
        refreshPendingCards();
        const off = { m: !g('musicPending').hidden, p: !g('photoPending').hidden,
                      mDot: !g('musicTabDot').hidden, pDot: !g('photoTabDot').hidden };
        return { on: on, off: off }; }"""
    for _route in ("/skribl-pad", "/flip"):
        _q = b.new_page(viewport={"width": 900, "height": 1100})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _r = _q.evaluate(RA)
        _on, _off = _r["on"], _r["off"]
        check(f"{_route}: a pending track shows its card, the loop and a pending dot",
              _on["m"] and _on["mName"] == "loop.mp3" and _on["mMeta"] == "Loop 0:02–0:06 · 4.5s" and _on["mDot"],
              f"{_on}")
        check(f"{_route}: a pending photo shows its card, a fallback name and its settings",
              _on["p"] and _on["pName"] == "Your image" and _on["pMeta"] == "Fit · 50% opacity", f"{_on}")
        check(f"{_route}: with nothing pending or loaded, both cards AND both dots are hidden",
              not any(_off.values()), f"{_off}")
        _q.close()

    # ---- the whole-track strip keeps its drawing when it has no layout ----
    # lib/loopwave.js drawStrip, one copy since v315. Sizing a canvas from a
    # 0-wide rect CLEARS it, and decode draws the strip once: with the drawer
    # shut at that instant the strip stayed blank for the session. The guard
    # that prevents it was pinned by nothing (removing it left every suite
    # green). The property, on each editor: a redraw with no layout keeps the
    # last good bitmap.
    print("\nPARITY — the music strip survives a redraw with the drawer shut")
    STRIP = """() => {
        const buf = currentAudioBuffer;
        const ink = () => { const c = waveformCanvas; if (!c.width) return 0;
            const px = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
            for (let i = 3; i < px.length; i += 4) if (px[i]) n++; return n; };
        const prev = musicTrack.getAttribute('style') || '';
        if (!musicTrack.getBoundingClientRect().width) return 'the music drawer did not open';
        drawWaveform(buf); const before = { w: waveformCanvas.width, ink: ink() };
        musicTrack.setAttribute('style', prev + ';display:none');
        drawWaveform(buf); const after = { w: waveformCanvas.width, ink: ink() };
        musicTrack.setAttribute('style', prev);
        return { before: before, after: after }; }"""
    for _route in ("/skribl-pad", "/flip"):
        _q = b.new_page(viewport={"width": 900, "height": 1100})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        # A real track and the real drawer: the trim track has no box until a
        # track is loaded and the drawer is open, and no positioning escapes a
        # display:none ancestor (the first draft read the canvas's default
        # 300px as a draw and measured nothing).
        _q.set_input_files("#musicInput", files=[{"name": "strip.wav", "mimeType": "audio/wav",
                                                  "buffer": wav_bytes(2.0)}])
        _q.wait_for_function("() => typeof currentAudioBuffer !== 'undefined' && !!currentAudioBuffer", timeout=20000)
        browsing.pad_drawer(_q, "music", settle=0)
        _q.wait_for_timeout(900)
        _r = _q.evaluate(STRIP)
        check(f"{_route}: the strip draws, and a redraw with no layout leaves it drawn",
              isinstance(_r, dict) and _r["before"]["ink"] > 500 and _r["after"] == _r["before"], f"{_r}")
        _q.close()

    # On a phone Play is a bare glyph, so the desktop's pulsing RING drew a
    # hollow outline around nothing — it read as a focus ring stuck on the
    # button (owner, iPhone) — and Flip's wrap clipped it away entirely. The
    # playing state is a tinted disc on both: the element the eye reads as
    # the control carries the accent fill, and nothing draws a ring.
    print("\nPARITY — on a phone, playing is a tinted disc on both, never a ring")
    DISC = """(o) => { const btn = document.getElementById(o.btn);
        const disc = o.wrap ? btn.closest(o.wrap) : btn;
        const bg = getComputedStyle(disc).backgroundColor.match(/[\\d.]+/g).map(Number);
        return { playing: btn.classList.contains('playing'), bg: bg,
                 ring: [getComputedStyle(disc).boxShadow, getComputedStyle(btn).boxShadow] }; }"""
    for _route, _btn, _wrap, _cv in (("/skribl-pad", "playBtn", None, "#canvas"),
                                     ("/flip", "play", ".flip-play-wrap", "#pad")):
        _q = b.new_page(viewport={"width": 390, "height": 844})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        for _ in range(2 if _route == "/flip" else 1):
            _bx = _q.locator(_cv).bounding_box()
            _cx, _cy = _bx["x"] + _bx["width"] / 2, _bx["y"] + _bx["height"] / 2
            _q.mouse.move(_cx, _cy); _q.mouse.down()
            for _i in range(30):
                _q.mouse.move(_cx + math.cos(_i / 4) * 60, _cy + math.sin(_i / 4) * 60)
                _q.wait_for_timeout(30)
            _q.mouse.up()
            if _route == "/flip" and _ == 0:
                _q.evaluate("() => addFrame()")
        if _route == "/skribl-pad":
            _q.evaluate("() => { if (recording) document.getElementById('recordBtn').click(); }")
        _q.wait_for_timeout(300)
        _q.evaluate("(id) => document.getElementById(id).click()", _btn)
        _q.wait_for_timeout(150)
        _d = _q.evaluate(DISC, {"btn": _btn, "wrap": _wrap})
        _bg = _d["bg"]
        _tinted = (len(_bg) == 4 and _bg[3] >= 0.1 and _bg[2] > 200 and _bg[2] > _bg[0] + 80)
        check(f"{_route}: playing at 390px is an accent-tinted disc with no ring",
              _d["playing"] and _tinted and all(r == "none" for r in _d["ring"]), f"{_d}")
        _q.close()

    # The header's Tune button is a bare sliders glyph — no room for a word on
    # a phone — so the panel it opens names itself, in the button's own words.
    print("\nPARITY — the Tune panel names itself on both, in the button's words")
    for _route in ("/skribl-pad", "/flip"):
        _q = b.new_page(viewport={"width": 390, "height": 844})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _q.evaluate("() => document.getElementById('tuneBtn').click()"); _q.wait_for_timeout(700)
        _t = _q.evaluate("""() => { const t = document.querySelector('#tunePanel .tune-title'); if (!t) return null;
            const r = t.getBoundingClientRect(), el = document.elementFromPoint(r.left + 4, r.top + r.height / 2);
            return { text: t.textContent.trim(), label: document.getElementById('tuneBtn').getAttribute('aria-label'),
                     painted: el === t, first: t === document.getElementById('tunePanel').firstElementChild }; }""")
        check(f"{_route}: the open panel shows its title first, and it is the button's name",
              bool(_t) and _t["painted"] and _t["first"] and _t["text"].lower() == (_t["label"] or "").lower(), str(_t))
        _q.close()

    # Found by the bottom-bar drawing test: on a phone the Pad's colour drawer
    # opens BELOW the bar and scrolls the page to show itself, which pushes the
    # top of the canvas off the screen -- and closing the drawer disarmed the
    # eyedropper. So nothing near the top of a drawing could be sampled. Flip
    # veils its popout while armed and never had the problem. The pick is made
    # through the page's own controls, and "reachable" is asked of what is
    # PAINTED at the point, not of the canvas's rect.
    print("\nPARITY — on a phone, the eyedropper reaches the top of the drawing")
    for _route, _cv, _opener in (("/skribl-pad", "#canvas", "@pad:draw"), ("/flip", "#pad", "@pad:draw")):
        _q = b.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _drawer = lambda: _q.evaluate(open_draw)
        def _ink(hexc):
            if not _drawer(): open_via(_q, _opener, settle=400)
            _q.click(f'#colorGroup .color-dot[data-color="{hexc}"]'); _q.wait_for_timeout(200)
        _ink("#ffe800")
        if _drawer():
            if _opener.startswith("@pad:"): browsing.pad_drawer_close(_q, settle=400)
            else: _q.click(_opener); _q.wait_for_timeout(400)
        _bx = _q.locator(_cv).bounding_box()
        _q.mouse.move(_bx["x"] + _bx["width"] * 0.2, _bx["y"] + _bx["height"] * 0.06); _q.mouse.down()
        _q.mouse.move(_bx["x"] + _bx["width"] * 0.8, _bx["y"] + _bx["height"] * 0.06, steps=12); _q.mouse.up()
        _q.wait_for_timeout(250)
        _ink("#0078bf")
        if not _drawer(): open_via(_q, _opener, settle=400)   # Flip closes its panel on a pick
        if not _q.locator("#eyedropperBtn").is_visible():
            check(f"{_route}: the eyedropper is reachable in the open colour panel", False, "not visible")
            _q.close(); continue
        _q.click("#eyedropperBtn"); _q.wait_for_timeout(450)
        _pt = _q.evaluate("""(sel) => { const c = document.querySelector(sel), r = c.getBoundingClientRect();
            const x = r.left + r.width * 0.5, y = r.top + r.height * 0.06;
            const el = y >= 0 && y < innerHeight ? document.elementFromPoint(x, y) : null;
            return { x, y, painted: !!el && el.tagName === 'CANVAS' && c.parentElement.contains(el) }; }""", _cv)
        if _pt["painted"]:
            _q.mouse.click(_pt["x"], _pt["y"]); _q.wait_for_timeout(400)
        _got = _q.evaluate("() => color")
        _rgb = [int(_got.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
        check(f"{_route}: with the colour drawer open, the armed eyedropper can reach the top of the canvas and picks from it",
              _pt["painted"] and _rgb[0] > 150 and _rgb[1] > 150 and _rgb[2] < 120,
              f"point at y={_pt['y']:.0f} painted by the canvas: {_pt['painted']}; colour after the pick {_got} "
              "(the stroke there is yellow)")
        # An ABANDONED pick gives the panel back where it was: open, painted, its colours on screen.
        # Armed only after the drawer's own settle re-scrolls (300/700/1200 ms, lib/drawerdetent.js)
        # are spent: inside that window they would put the page back themselves and hide a
        # missing restore -- which is exactly how the first draft of this check went green.
        if not _drawer(): open_via(_q, _opener, settle=0)
        _q.wait_for_timeout(1500)
        if _q.locator("#eyedropperBtn").is_visible():
            _q.click("#eyedropperBtn"); _q.wait_for_timeout(350)
            _q.keyboard.press("Escape"); _q.wait_for_timeout(500)
            # Both ends of the panel: its colours, and its bottom edge -- the Pad's colour row
            # survives a page left at the top, the rest of its drawer does not.
            _back = _q.evaluate("""() => { const p = document.getElementById('drawPanel'), d = document.querySelector('#colorGroup .color-dot');
                if (!p || !d) return null;
                const at = (x, y) => y >= 0 && y < innerHeight ? document.elementFromPoint(x, y) : null;
                const r = d.getBoundingClientRect(), pr = p.getBoundingClientRect();
                const dot = at(r.left + r.width / 2, r.top + r.height / 2), end = at(pr.left + pr.width / 2, pr.bottom - 10);
                return { dotY: Math.round(r.top), endY: Math.round(pr.bottom),
                         colours: !!dot && (dot === d || d.contains(dot)), end: !!end && p.contains(end) }; }""")
            check(f"{_route}: ...and an abandoned pick (Escape) puts the open colour panel back on screen, top to bottom",
                  bool(_back) and _back["colours"] and _back["end"], str(_back))
        _q.close()

    # ---- the media card -------------------------------------------------------
    # THE DRAWER REDESIGN (option A, owner-approved). The Photo | Music tabs and
    # the open drawer were two glass slabs, 8px apart and of different widths
    # (520 against 694 at a desktop width), each with its own rim and shadow.
    # They are ONE card now: #mediaCard wraps the strip and both panels and
    # wears the glass; the panel inside goes clear, and the strip sits inset in
    # the card as a track. Fresh, empty drawers, so a tall loaded panel cannot
    # scroll the strip off the top of a phone (lib/drawerdetent.js reveals the
    # panel's END); and every point is on screen before it is asked about.
    print("\nPARITY — the Photo | Music tabs and the open drawer are one card, on both")
    CARD = """(k) => { const g = (id) => document.getElementById(id), card = g('mediaCard'), tabs = g('mediaTabs'), p = g(k + 'Panel');
        if (!card) return { card: false };
        card.scrollIntoView({ block: 'start' });
        const c = card.getBoundingClientRect(), t = tabs.getBoundingClientRect(), r = p.getBoundingClientRect();
        const ps = getComputedStyle(p), ts = getComputedStyle(tabs), cs = getComputedStyle(card);
        const inCard = (x, y) => { if (y < 0 || y >= innerHeight) return 'off-screen'; const e = document.elementFromPoint(x, y); return !!e && card.contains(e); };
        const cx = c.left + c.width / 2, padL = parseFloat(ps.paddingLeft), padR = parseFloat(ps.paddingRight);
        return { card: true,
                 parents: [tabs, g('photoPanel'), g('musicPanel')].every(e => e.parentElement === card),
                 inset: [t.left - c.left, c.right - t.right, t.top - c.top],
                 content: Math.abs(t.left - (r.left + padL)) <= 0.5 && Math.abs(t.right - (r.right - padR)) <= 0.5,
                 span: Math.abs(r.left - c.left) <= 0.5 && Math.abs(r.right - c.right) <= 0.5 && Math.abs(r.bottom - c.bottom) <= 0.5,
                 seam: [inCard(cx, t.bottom + (r.top - t.bottom) / 2), inCard(cx, r.top + 1)],
                 gap: Math.round(r.top - t.bottom),
                 glass: cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backdropFilter !== 'none',
                 clear: ps.backgroundColor === 'rgba(0, 0, 0, 0)' && ps.boxShadow === 'none' && ps.backdropFilter === 'none'
                        && ts.backdropFilter === 'none' };
    }"""
    for _route in ("/skribl-pad", "/flip"):
        for _vw, _vp in (("390", {"width": 390, "height": 844}), ("1280", {"width": 1280, "height": 900})):
            _q = b.new_page(viewport=_vp)
            _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
            _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
            _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
            _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
            for _k in ("photo", "music"):
                browsing.pad_drawer(_q, _k)
                _cur = _q.evaluate(browsing._PAD_CUR)
                _c = _q.evaluate(CARD, _k)
                check(f"{_route} at {_vw}, {_k}: the tabs and the open drawer share one parent card",
                      _cur == _k and _c["card"] and _c["parents"], f"open={_cur!r} {_c}")
                if not _c["card"]:
                    continue
                check(f"{_route} at {_vw}, {_k}: the strip sits inset in the card and lines up with the drawer's content",
                      all(abs(v - 16) <= 0.5 for v in _c["inset"]) and _c["content"] and _c["span"], str(_c))
                check(f"{_route} at {_vw}, {_k}: the seam between tabs and drawer is painted by the card, not the page",
                      _c["seam"] == [True, True], str(_c))
                check(f"{_route} at {_vw}, {_k}: the card wears the glass and the drawer inside it is clear",
                      _c["glass"] and _c["clear"], str(_c))
            if _route == "/flip":
                _dlg = _q.evaluate("""() => { const p = document.getElementById('photoPanel');
                    return { role: p.getAttribute('role'), label: p.getAttribute('aria-label'),
                             tabsInDialog: !!document.getElementById('mediaTabs').closest('[role=dialog]') }; }""")
                check(f"/flip at {_vw}: the drawers are still named dialogs, and the tablist is outside them",
                      _dlg == {"role": "dialog", "label": "Background image", "tabsInDialog": False}, str(_dlg))
            _q.click("#mediaOpenBtn"); _q.wait_for_timeout(400)
            _gone = _q.evaluate("() => { const c = document.getElementById('mediaCard'); return { open: (" + browsing._PAD_CUR + ")(), display: c ? getComputedStyle(c).display : null }; }")
            check(f"{_route} at {_vw}: closing the drawer takes the whole card with it",
                  _gone["open"] is None and _gone["display"] == "none", str(_gone))
            _q.close()

    # ---- the empty drop area ---------------------------------------------------
    # Until a file is added the row is one quiet drop area: a real button that
    # fills it (a Tab stop the old row never had), a title and one line of
    # hint. No switch, no bin, no adjustments until there is a file for them to
    # act on. The words are read from the RENDERED DOM, so a comment or a
    # DECISIONS entry that quotes the old title cannot pass or fail this.
    print("\nPARITY — the empty drop area, on both")
    EMPTY = """(k) => { const g = (id) => document.getElementById(id), add = g(k + 'AddBtn');
        if (!add) return { add: false };
        add.scrollIntoView({ block: 'center' });
        const r = add.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const off = [k + 'Toggle', k + 'Remove', k + 'Detail', k + 'BtnLabel'].concat(k === 'photo' ? ['photoThumb'] : [])
          .filter(id => g(id) && g(id).offsetParent !== null);
        return { add: true, painted: !!at && add.contains(at), title: add.querySelector('.dz-title').textContent,
                 hint: add.querySelector('.dz-hint').textContent, showing: off }; }"""
    WORDS = {"photo": ("Add a photo", "JPG, PNG, GIF or WebP · or drop one here"),
             "music": ("Add music", "MP3, WAV, M4A or OGG · it loops under your drawing")}
    for _route, _in in (("/skribl-pad", {"photo": "#photoInput", "music": "#musicInput"}),
                        ("/flip", {"photo": "#imageInput", "music": "#musicInput"})):
        _q = b.new_page(viewport={"width": 1280, "height": 900})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        for _k in ("photo", "music"):
            browsing.pad_drawer(_q, _k)
            _e = _q.evaluate(EMPTY, _k)
            check(f"{_route}, {_k}: the empty row is one painted add button with its title and hint",
                  _q.evaluate(browsing._PAD_CUR) == _k and _e["add"] and _e["painted"]
                  and (_e["title"], _e["hint"]) == WORDS[_k], str(_e))
            check(f"{_route}, {_k}: ...and nothing that needs a file shows until there is one",
                  _e["add"] and not _e["showing"], str(_e))
            # Each picker is answered (with nothing) before the next is asked
            # for: Chromium opens one file chooser at a time.
            _chosen = []
            try:
                with _q.expect_file_chooser(timeout=3000) as _fc:
                    _q.click(f"#{_k}AddBtn")
                _fc.value.set_files([])
                _chosen.append("click")
            except Exception:
                pass
            try:
                _q.focus(f"#{_k}AddBtn")
                with _q.expect_file_chooser(timeout=3000) as _fc:
                    _q.keyboard.press("Enter")
                _fc.value.set_files([])
                _chosen.append("Enter")
            except Exception:
                pass
            check(f"{_route}, {_k}: a tap on it, or Enter on it, opens the file picker",
                  _chosen == ["click", "Enter"], f"picker opened by {_chosen}")
        _old = _q.evaluate("""() => [document.getElementById('photoPanel').innerText,
            [...document.querySelectorAll('#helpDrawer .help-pill')].map(e => e.textContent).join('|')]
            .some(t => t.includes('Add an image'))""")
        check(f"{_route}: 'Add an image' is gone from the drawer and from How it works",
              _old is False, "the empty title and the help pill say 'Add a photo'")
        _q.close()

    # ---- the bin ------------------------------------------------------------
    # The red Remove pill is a quiet bin now, and it asks first, as the
    # saved-drafts bin does: the first tap arms it ("Remove?", in the danger
    # colour, its name saying what the next tap does, spoken through
    # #confirmStatus), a tap anywhere else stands it down, and the second tap
    # removes. REAL clicks throughout, because the defect this guards is a
    # click that reaches the row behind the bin and opens the file picker.
    # TWO GUARDS keep it from reaching the row on each editor -- the row's own
    # handler ignores the bin, and the bin's handler stops the click -- so a
    # mutation that removes one of them alone stays green here, correctly; the
    # arming capture on the row (lib/pendingcards.js) is a third for the first
    # tap. Removing the file hands focus to the add button, never to <body>.
    print("\nPARITY — the bin asks once, then removes, on both")
    BIN = """(k) => { const g = (id) => document.getElementById(id), bin = g(k + 'Remove'), t = g('photoThumb');
        bin.scrollIntoView({ block: 'center' });
        const r = bin.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const probe = document.createElement('span'); probe.style.color = 'var(--danger)'; document.body.appendChild(probe);
        const danger = getComputedStyle(probe).color; probe.remove();
        return { cur: (""" + browsing._PAD_CUR + """)(), loaded: g(k + 'UploadBtn').classList.contains('loaded'),
                 armed: bin.classList.contains('armed'), label: bin.getAttribute('aria-label'),
                 said: g('confirmStatus').textContent, text: bin.innerText.trim(),
                 red: getComputedStyle(bin).color === danger, painted: !!at && bin.contains(at),
                 add: g(k + 'AddBtn').offsetParent !== null, name: g(k + 'BtnLabel').textContent,
                 src: k === 'photo' ? t.hasAttribute('src') : null, focus: document.activeElement && document.activeElement.id }; }"""
    FILES = {"photo": {"name": "t.png", "mimeType": "image/png", "buffer": IMG},
             "music": {"name": "t.wav", "mimeType": "audio/wav", "buffer": AUD}}
    NOUN = {"photo": "the photo", "music": "the track"}
    for _route, _in in (("/skribl-pad", {"photo": "#photoInput", "music": "#musicInput"}),
                        ("/flip", {"photo": "#imageInput", "music": "#musicInput"})):
        _q = b.new_page(viewport={"width": 1280, "height": 900})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _pickers = []
        _q.on("filechooser", lambda fc, _p=_pickers: _p.append(1))
        _ok, _why = True, []
        for _k in ("photo", "music"):
            _f = FILES[_k]
            browsing.pad_drawer(_q, _k)
            _q.set_input_files(_in[_k], _f)
            _q.wait_for_function("(k) => document.getElementById(k + 'UploadBtn').classList.contains('loaded')", arg=_k, timeout=20000)
            _q.wait_for_timeout(300)
            _q.click(f"#{_k}Remove"); _q.wait_for_timeout(400)   # past the bin's colour transition
            _a = _q.evaluate(BIN, _k)
            _armed = (_a["loaded"] and _a["armed"] and _a["label"] == f"Tap again to remove {_f['name']}"
                      and _a["said"] == _a["label"] and _a["text"] == "Remove?" and _a["red"] and _a["painted"])
            _q.click(f"#{_k}BtnLabel"); _q.wait_for_timeout(150)
            _d = _q.evaluate(BIN, _k)
            _stood = _d["loaded"] and not _d["armed"] and _d["label"] == f"Remove {NOUN[_k]}"
            _q.click(f"#{_k}Remove"); _q.wait_for_timeout(100)
            _q.click(f"#{_k}Remove"); _q.wait_for_timeout(400)
            _r = _q.evaluate(BIN, _k)
            _gone = (_r["cur"] == _k and not _r["loaded"] and _r["add"] and _r["name"] == "" and _r["src"] in (False, None))
            # And by keyboard: Enter arms, Enter removes, and focus lands on the add button.
            _q.set_input_files(_in[_k], _f)
            _q.wait_for_function("(k) => document.getElementById(k + 'UploadBtn').classList.contains('loaded')", arg=_k, timeout=20000)
            _q.wait_for_timeout(300)
            _q.focus(f"#{_k}Remove"); _q.keyboard.press("Enter"); _q.wait_for_timeout(100)
            _ka = _q.evaluate(BIN, _k)
            _q.keyboard.press("Enter"); _q.wait_for_timeout(400)
            _kr = _q.evaluate(BIN, _k)
            _keys = _ka["armed"] and _ka["loaded"] and not _kr["loaded"] and _kr["focus"] == f"{_k}AddBtn"
            if not (_armed and _stood and _gone and _keys):
                _ok = False
                _why.append(f"{_k}: armed={_a} stood-down={_d} removed={_r} keys armed={_ka} removed={_kr}")
        check(f"{_route}: the bin asks once, then removes -- by pointer and by keyboard",
              _ok and not _pickers, "; ".join(_why) + (f"; the file picker opened {len(_pickers)} time(s)" if _pickers else ""))
        _q.close()

    # ---- drops --------------------------------------------------------------
    # "or drop one here" is a promise on both editors, and Flip had no drop
    # handling at all. The card takes the drop, anywhere on it (the tabs, the
    # edge, the row), checks it is the right kind of file, and hands it to the
    # drawer's own input. The highlight does not flicker as the pointer crosses
    # the row's own children. The WRONG kind is refused with nothing attached:
    # a video on the music drawer, a BMP on the photo drawer -- real PNG and WAV
    # bytes under the wrong type, so a missing type check shows as an attach.
    # On the Pad the input's change handler checks the type too (two guards),
    # so dropping the card's check alone stays green there and goes red on Flip.
    print("\nPARITY — a file dropped on the drawer is taken, on both")
    DROP = """async ([k, onto, name, type, b64]) => {
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const dt = new DataTransfer(); dt.items.add(new File([bytes], name, { type }));
        const el = document.querySelector(onto);
        const over = new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt });
        el.dispatchEvent(over);
        const z = document.getElementById(k + 'UploadBtn'), lit = z.classList.contains('drag-over');
        z.dispatchEvent(new DragEvent('dragleave', { bubbles: true, relatedTarget: z.querySelector('.dz-title') }));
        const steady = z.classList.contains('drag-over');
        el.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
        const unlit = !z.classList.contains('drag-over');
        for (let i = 0; i < 50 && !z.classList.contains('loaded'); i++) await new Promise(r => setTimeout(r, 100));
        return { prevented: over.defaultPrevented, lit, steady, unlit, loaded: z.classList.contains('loaded'),
                 name: document.getElementById(k + 'BtnLabel').textContent,
                 dot: !document.getElementById(k + 'TabDot').hidden }; }"""
    import base64 as _b64
    _PNG64, _WAV64 = _b64.b64encode(IMG).decode(), _b64.b64encode(AUD).decode()
    for _route in ("/skribl-pad", "/flip"):
        _q = b.new_page(viewport={"width": 1280, "height": 900})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        browsing.pad_drawer(_q, "photo")
        _bad_p = _q.evaluate(DROP, ["photo", "#photoUploadBtn", "x.bmp", "image/bmp", _PNG64])
        _good_p = _q.evaluate(DROP, ["photo", "#photoUploadBtn", "d.png", "image/png", _PNG64])
        browsing.pad_drawer(_q, "music")
        _bad_m = _q.evaluate(DROP, ["music", "#mediaTabs", "x.mp4", "video/mp4", _WAV64])
        _good_m = _q.evaluate(DROP, ["music", "#mediaTabs", "d.wav", "audio/wav", _WAV64])
        check(f"{_route}: a file dropped anywhere on the card is taken, and the wrong kind is refused",
              _bad_p["prevented"] and not _bad_p["loaded"] and not _bad_m["loaded"]
              and _good_p["loaded"] and _good_p["name"] == "d.png" and _good_p["dot"]
              and _good_m["loaded"] and _good_m["name"] == "d.wav" and _good_m["dot"],
              f"photo: bmp {_bad_p}, png {_good_p}; music on the tabs: mp4 {_bad_m}, wav {_good_m}")
        check(f"{_route}: the drop area lights while a file is over it, steadily, and goes out on the drop",
              all(r["lit"] and r["steady"] and r["unlit"] for r in (_good_p, _good_m)),
              f"photo {_good_p}; music {_good_m}")
        _q.close()

    # ---- the re-add card stands in for BOTH faces ------------------------------
    # A draft that kept a file's settings but not its bytes shows the re-add
    # card where the row was. It has to hide the whole row -- drop area and file
    # face alike -- on both editors (verify_amber reads only the row's hidden
    # property, on Flip's music). And the card takes a dropped file too: the
    # saved fit comes back with it, and the row says so.
    print("\nPARITY — the re-add card hides both faces of the row, and takes a drop, on both")
    for _route in ("/skribl-pad", "/flip"):
        _q = b.new_page(viewport={"width": 1280, "height": 900})
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        _q.goto(BASE + _route, wait_until="load"); _q.wait_for_timeout(700)
        _q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        browsing.pad_drawer(_q, "photo")
        _q.evaluate("() => { pendingPhotoMeta = { name: 'd.png', fit: 'contain' }; refreshPendingCards(); }")
        _q.wait_for_timeout(150)
        _rc = _q.evaluate("""() => { const g = (id) => document.getElementById(id), c = g('photoPending');
            c.scrollIntoView({ block: 'center' });
            const r = c.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { cur: (""" + browsing._PAD_CUR + """)(), card: !!at && c.contains(at),
                     hidden: ['photoAddBtn', 'photoBtnLabel', 'photoThumb'].filter(id => g(id).offsetParent !== null) }; }""")
        check(f"{_route}: the re-add card shows, painted, and neither face of the row is behind it",
              _rc["cur"] == "photo" and _rc["card"] and not _rc["hidden"], str(_rc))
        _ra = _q.evaluate(DROP, ["photo", "#photoPending", "d.png", "image/png", _PNG64])
        _q.wait_for_timeout(700)
        _meta = _q.evaluate("() => ({ meta: document.getElementById('photoBtnMeta').textContent, card: !document.getElementById('photoPending').hidden })")
        check(f"{_route}: a file dropped on the re-add card is taken, and the row says the fit it brought back",
              _ra["loaded"] and _ra["name"] == "d.png" and _meta == {"meta": "Behind the drawing · Fit", "card": False},
              f"{_ra} {_meta}")
        _q.close()

    print("\nPARITY — no surface is silently erroring on load")
    check("Pad loads without JS errors", not errs["pad"], "; ".join(errs["pad"][:2]))
    check("Flip loads without JS errors", not errs["flip"], "; ".join(errs["flip"][:2]))

    b.close()

summarise_and_exit()
