"""Which blocks of styles.css can a player page never match?

NOT A SECTION SPLIT. styles.css carries 35 section banners and most of them read
editor-only — "Post composer sheet", "Help button + drawer", "More tools drawer".
Cutting along those names is the same move that nearly swallowed initBrandFit
during the JS extraction: the banner describes what the author was thinking
about, not what the rules match. This asks the browser instead.

METHOD. Parse styles.css into top-level blocks, keeping each block's byte range
so the split can be a verbatim move rather than a rewrite. For every block,
collect its selectors — recursing into @media, which holds most of the file's
responsive rules — and ask a real player page whether any of them matches
anything, across several scenes.

WHAT IS DELIBERATELY NOT CLASSIFIED, and why each would be a bug to cut:

  @keyframes / @font-face   have no selectors. A keyframes block matches
                            nothing by construction and would read as dead.
  :root and *               match everywhere; they carry the custom properties
                            every other rule reads.
  @media print,
  prefers-reduced-motion,
  orientation               conditions this harness does not enter. A rule that
                            is live only under a media query nobody exercised
                            is not evidence of anything.

Those are held as KEEP regardless of whether they matched, which is the superset
gate: the classifier is allowed to be wrong in the direction of shipping a rule
the player does not need, and is not allowed to be wrong in the other direction.

STATE. Selectors are tested as written AND with state stripped
(:hover/:focus/:active and pseudo-elements removed), because .menu-overlay.open
never matches at rest and .menu-overlay is what actually decides the question.
A block counts as live if EITHER form matches in ANY scene.
"""
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "skribl" / "static" / "styles.css"

# --- parse into top-level blocks ---------------------------------------------


def blocks(text):
    """Yield (start, end, header, body) for each top-level construct."""
    i, n = 0, len(text)
    out = []
    while i < n:
        # skip whitespace and comments, but keep them attached to what follows
        start = i
        while i < n:
            if text[i : i + 2] == "/*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
            elif text[i].isspace():
                i += 1
            else:
                break
        if i >= n:
            if start < n:
                out.append((start, n, "", ""))
            break
        head_start = i
        # at-rules without a body end at ';'
        depth = 0
        brace = -1
        while i < n:
            c = text[i]
            if text[i : i + 2] == "/*":
                j = text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            if c in "\"'":
                q = c
                i += 1
                while i < n and text[i] != q:
                    i += 2 if text[i] == "\\" else 1
                i += 1
                continue
            if c == ";" and depth == 0 and brace < 0:
                i += 1
                break
            if c == "{":
                if depth == 0:
                    brace = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        header = text[head_start : brace if brace > 0 else i].strip()
        body = text[brace + 1 : i - 1] if brace > 0 else ""
        out.append((start, i, header, body))
    return out


ALWAYS_KEEP = re.compile(
    r"^@(keyframes|-webkit-keyframes|font-face|import|charset|supports|property|layer)",
    re.I)
UNEXERCISED_MEDIA = re.compile(
    r"print|prefers-reduced-motion|prefers-contrast|forced-colors|orientation|"
    r"hover\s*:\s*none|pointer\s*:\s*coarse", re.I)
STATE = re.compile(r"::?(hover|focus|focus-visible|focus-within|active|"
                   r"before|after|placeholder|selection|backdrop|"
                   r"-webkit-[a-z-]+)(\([^)]*\))?", re.I)


def selectors_of(header, body, depth=0):
    """Every selector a block contributes, recursing into @media."""
    h = header.strip()
    if ALWAYS_KEEP.match(h):
        return None                       # unclassifiable by matching
    if h.startswith("@media"):
        if UNEXERCISED_MEDIA.search(h):
            return None                   # condition this run never enters
        out = []
        for _s, _e, hh, bb in blocks(body):
            sub = selectors_of(hh, bb, depth + 1)
            if sub is None:
                return None
            out.extend(sub)
        return out
    if h.startswith("@"):
        return None
    return [p.strip() for p in re.split(r",(?![^(]*\))", h) if p.strip()]


text = CSS.read_text()
parsed = []
for s, e, h, b in blocks(text):
    sels = selectors_of(h, b)
    parsed.append({"start": s, "end": e, "header": h[:70], "sels": sels,
                   "bytes": e - s})

classifiable = [p for p in parsed if p["sels"]]
kept_blind = [p for p in parsed if p["sels"] is None]
all_sels = sorted({s for p in classifiable for s in p["sels"]})

print(f"styles.css       {len(text):,} B")
print(f"blocks           {len(parsed)}")
print(f"  classifiable   {len(classifiable)}  ({sum(p['bytes'] for p in classifiable):,} B)")
print(f"  held KEEP      {len(kept_blind)}  ({sum(p['bytes'] for p in kept_blind):,} B)"
      f"  — at-rules with no selectors, and media queries this run never enters")
print(f"distinct selectors {len(all_sels)}")

# The classification's scratch output, for the browser step. Not written when
# the run is only an --emit: verify_seam runs --emit on the PR gate, and a
# fixed shared /tmp path written on every run races under parallel runs.
if not (len(sys.argv) > 1 and sys.argv[1] == "--emit"):
    Path("/tmp/css_selectors.json").write_text(json.dumps({
        "selectors": all_sels,
        "blocks": [{"start": p["start"], "end": p["end"], "header": p["header"],
                    "sels": p["sels"], "bytes": p["bytes"]} for p in parsed],
    }))
    print("\nwrote /tmp/css_selectors.json")


# --- emit ---------------------------------------------------------------------
# `python3 harness/tools/cssgraph.py --emit <live.json>` writes player.css from
# styles.css and the recorded live-selector set. Kept as a separate step so the
# classification (which needs a browser) and the generation (which does not) can
# be re-run independently — and so verify_cssplit.py can regenerate and compare
# without deciding anything itself.
def _split_media(block_text, live):
    """Emit only the live rules inside one @media block, or None to keep it whole.

    The block-level rule — keep the construct if ANY selector in it is live —
    was applied to a whole @media, so one live rule dragged in every editor rule
    that happened to share the breakpoint. styles.css puts most of its
    responsive rules in a handful of large media blocks, so that is thousands of
    bytes of drawer and composer styling on a page with neither.

    The condition is not re-evaluated here: liveness is a property of a
    selector, measured by asking a real page whether anything matches it, and
    that answer does not change with the viewport the rule is gated on. This is
    the same classification, applied one level deeper.

    Returns None when the block should be emitted verbatim — when every inner
    rule is live (so a rebuild could only differ in whitespace), when none is
    (the caller drops it), or when anything inside cannot be classified by
    matching at all, which is the superset gate one level down.
    """
    brace = block_text.find("{")
    close = block_text.rfind("}")
    if brace < 0 or close < brace:
        return None
    inner = block_text[brace + 1:close]
    kept, total = [], 0
    for s, e, hh, bb in blocks(inner):
        sub = selectors_of(hh, bb)
        if sub is None:
            return None                     # nested at-rule: do not touch it
        total += 1
        if any(x in live for x in sub):
            kept.append(inner[s:e])
    if not kept or len(kept) == total:
        return None
    return block_text[:brace + 1] + "".join(kept) + block_text[close:]


def emit(live_path, out_path):
    live = set(json.loads(Path(live_path).read_text())["player"])
    parts = []
    for p in parsed:
        block_text = text[p["start"]:p["end"]]
        if p["sels"] is None:
            parts.append(block_text)
            continue
        if not any(s in live for s in p["sels"]):
            continue
        if p["header"].startswith("@media"):
            split = _split_media(block_text, live)
            if split is not None:
                parts.append(split)
                continue
        parts.append(block_text)
    Path(out_path).write_text(HEADER + "".join(parts))
    return sum(len(p) for p in parts) + len(HEADER)


HEADER = Path(__file__).with_name("player_css_header.txt").read_text()
BAND_HEADER = Path(__file__).with_name("fullband_css_header.txt").read_text()


# --- the band: the link page's full screen, for the Gallery and the Library ---
# A SECOND SUBSET, AND A STRICTER ONE. player.css is a whole page's sheet and
# keeps a block when anything in it matches, because it replaces styles.css on
# that page. fullband.css lands on pages that have their own sheets, so it
# takes RULES, not blocks, and only a rule that styles the full-screen frame
# and nothing else on the page: a stray `button` or `*` would restyle the
# Gallery. The census (--band-census) records both answers per selector:
# "band", matched inside the frame, and "band_out", matched outside it.
NESTED = ("@media", "@starting-style")
BAND_FRAME = ".watch-full:is(:fullscreen, .is-immersive-page)"
INHERITED = ("color", "font-family", "font-size", "font-weight", "font-style", "line-height", "letter-spacing",
             "-webkit-font-smoothing", "-moz-osx-font-smoothing", "font-variant-numeric", "text-rendering")


def _rule_selectors(head):
    return [x.strip() for x in re.split(r",(?![^(]*\))", head) if x.strip()]


def every_selector(region=None):
    """Every selector in styles.css's rules, at any depth inside @media and
    @starting-style -- what the census asks the page about."""
    out = []
    for _s, _e, h, b in blocks(text if region is None else region):
        h = h.strip()
        if h.startswith(NESTED):
            out.extend(every_selector(b))
        elif h and not h.startswith("@"):
            out.extend(_rule_selectors(h))
    return out


def _band_rules(region, band, out_sel, used):
    parts = []
    for s, e, h, b in blocks(region):
        h = h.strip()
        if h.startswith(NESTED):
            whole = region[s:e]
            brace, close = whole.find("{"), whole.rfind("}")
            inner = _band_rules(whole[brace + 1:close], band, out_sel, used)
            if inner.strip():
                parts.append(whole[:brace + 1] + inner + "\n" + whole[close:])
            continue
        if not h or h.startswith("@"):
            continue
        sels = _rule_selectors(h)
        if any(x in band for x in sels) and not any(x in out_sel for x in sels):
            parts.append(region[s:e])
            used.update(re.findall(r"animation(?:-name)?\s*:\s*([\w-]+)", b))
    return "".join(parts)


def _tokens(header):
    """The custom properties one of styles.css's token blocks sets."""
    out = {}
    for _s, _e, h, b in blocks(text):
        if h.strip() == header:
            for m in re.finditer(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", re.sub(r"/\*.*?\*/", "", b, flags=re.S)):
                out[m.group(1)] = " ".join(m.group(2).split())
    return out


def emit_band(live_path, out_path):
    live = json.loads(Path(live_path).read_text())
    if "band" not in live:
        return 0
    used = set()
    rules = _band_rules(text, set(live["band"]), set(live.get("band_out", [])), used)
    # The keyframes a kept rule names, and only those.
    frames = "".join(text[s:e] for s, e, h, _b in blocks(text)
                     if re.match(r"@(-webkit-)?keyframes\s+([\w-]+)", h.strip())
                     and re.match(r"@(-webkit-)?keyframes\s+([\w-]+)", h.strip()).group(2) in used)
    # THE WORDS THOSE RULES ARE WRITTEN IN, with styles.css's values for each
    # theme, set on the frame: these pages keep their own palette, and the
    # band inside the frame is the link page's to the colour. Every name a
    # kept rule reads, and every name those values read in turn.
    dark, light = _tokens(":root"), _tokens(':root[data-theme="light"]')
    # WHAT THE BAND INHERITS is the link page's body: its type and ink, from
    # styles.css's own body rule, and the browser's line-height where that
    # rule sets none. Only on a frame that is full screen, so a card at rest
    # is untouched.
    body = {}
    for _s, _e, h, b in blocks(text):
        if h.strip() == "body":
            for m in re.finditer(r"([a-z-]+)\s*:\s*([^;]+);", re.sub(r"/\*.*?\*/", "", b, flags=re.S)):
                if m.group(1) in INHERITED:
                    body[m.group(1)] = " ".join(m.group(2).split())
    body.setdefault("line-height", "normal")
    need = set(re.findall(r"var\((--[a-z0-9-]+)", re.sub(r"/\*.*?\*/", "", rules, flags=re.S) + " ".join(body.values())))
    todo = list(need)
    while todo:
        t = todo.pop()
        for ref in re.findall(r"var\((--[a-z0-9-]+)", dark.get(t, "") + " " + light.get(t, "")):
            if ref not in need:
                need.add(ref)
                todo.append(ref)
    def block(sel, vals):
        names = sorted(n for n in need if n in vals)
        return sel + " {\n" + "".join(f"  {n}: {vals[n]};\n" for n in names) + "}\n" if names else ""
    tokens = ("\n/* The band's tokens: styles.css's :root and its light theme, on a full-screen frame. */\n"
              + block(BAND_FRAME, dark) + block(':root[data-theme="light"] ' + BAND_FRAME, light)
              + "/* What the band inherits: styles.css's body rule's type and ink. */\n"
              + BAND_FRAME + " {\n" + "".join(f"  {k}: {v};\n" for k, v in sorted(body.items())) + "}\n")
    body = BAND_HEADER + tokens + rules + frames
    Path(out_path).write_text(body)
    return len(body)


def band_census(base, live_path):
    """Ask the Gallery, in every state its full screen has, which selectors
    match inside the frame and which match anything outside it; ask the
    Library the second question too. Writes "band" and "band_out"."""
    import math as _m
    import urllib.request as _u
    sys.path.insert(0, str(ROOT / "harness"))
    import browsing
    from playwright.sync_api import sync_playwright

    sels = sorted(set(every_selector()))
    strip = {x: STATE.sub("", x).strip() for x in sels}

    def post(title, ground, ink, flip=False):
        def ring(r, n, t0, cx=201, cy=380):
            return [{"x": round(cx + r * _m.cos(i / n * 6.283), 1), "y": round(cy + r * _m.sin(i / n * 6.283), 1),
                     "color": ink, "t": t0 + i * 400, "start": i == 0, "size": 6} for i in range(n + 1)]
        if flip:
            frames = [{"strokes": ring(60 + 40 * k, 60, 0), "strokeGroups": [61], "background": {"color": ground}}
                      for k in range(3)]
            body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public", "playbackMode": "flip",
                    "canvasSize": {"cssWidth": 402, "cssHeight": 760}, "frames": frames, "fps": 6}
        else:
            pts = ring(60, 400, 0) + ring(150, 400, 200000) + ring(180, 400, 400000)
            body = {"title": title, "version": 2, "schemaVersion": 2, "visibility": "public", "playbackMode": "replay",
                    "canvasSize": {"cssWidth": 402, "cssHeight": 760},
                    "frames": [{"strokes": pts, "strokeGroups": [401, 401, 401], "background": {"color": ground}}]}
        req = _u.Request(base + "/api/skribls", data=json.dumps(body).encode(),
                         headers={"Content-Type": "application/json"})
        return json.loads(_u.urlopen(req, timeout=30).read())["id"]

    names = {"dark": post("Census dark", "#2e1b52", "#c9b8ff"),
             "pale": post("Census pale", "#fdfcf7", "#3a24a8"),
             "flip": post("Census flip", "#203040", "#ffd166", flip=True)}
    # INSIDE is the open frame and the band's own parts in it: the band, the
    # x, the name. Not the drawing's player, which inlineplayer.css styles. A
    # card's frame and its band, put away, are the same component on another
    # card and are not OUTSIDE; everything else on the page is.
    ASK = """([sels, strip, frameSel]) => {
      const PARTS = '.watch-full > :is(.player-bar, .player-btn.full-exit, .fb-who)';
      const frame = frameSel ? document.querySelector(frameSel) : null, inside = [], outside = [];
      const part = e => e.matches('.watch-full') || !!e.closest(PARTS);
      const within = e => !!frame && (e === frame || (frame.contains(e) && !!e.closest(PARTS)));
      for (const x of sels) {
        let ins = false, outs = false;
        for (const q of new Set([x, strip[x]])) {
          if (!q) continue;
          let all;
          try { all = document.querySelectorAll(q); } catch (e) { continue; }
          for (const e of all) {
            if (within(e)) ins = true; else if (!part(e)) outs = true;
            if (ins && outs) break;
          }
        }
        if (ins) inside.push(x);
        if (outs) outside.push(x);
      }
      return [inside, outside]; }"""
    NO_API = """(() => { try { Object.defineProperty(Document.prototype, 'fullscreenEnabled', { get: () => false, configurable: true }); } catch (e) {}
      try { delete Element.prototype.requestFullscreen; } catch (e) {} try { delete Element.prototype.webkitRequestFullscreen; } catch (e) {} })();"""
    band, out = set(), set()
    PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
    DESK = dict(viewport={"width": 1280, "height": 800})
    plan = [("phone", "dark", "dark"), ("phone", "light", "dark"), ("desk", "dark", "dark"), ("desk", "light", "dark"),
            ("desk", "light", "pale"), ("phone", "dark", "pale"), ("desk", "dark", "flip"), ("phone", "light", "flip")]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for view, theme, which in plan:
            pg = b.new_page(color_scheme=theme, **(PHONE if view == "phone" else DESK))
            if view == "phone":
                pg.add_init_script(NO_API)
            pg.add_init_script(f"try {{ localStorage.setItem('skribl_theme_v1', '{theme}'); }} catch (e) {{}}")
            browsing.goto(pg, base, "/gallery")
            pg.wait_for_timeout(1500)
            tile = pg.locator(f".tile:has(.skribl-inline[data-skribl-id='{names[which]}'])").first
            tile.scroll_into_view_if_needed()
            tile.evaluate("t => t.classList.add('ctl-on')")
            tile.locator(".skfull-card .skfull-full").first.click()
            pg.wait_for_timeout(1500)
            frame = ".tileStage.watch-full:is(:fullscreen, .is-immersive-page)"
            def ask():
                i, o = pg.evaluate(ASK, [sels, strip, frame])
                band.update(i)
                out.update(o)
            # Pressed in the page, not by pointer: the census runs before the
            # sheet it makes, when the band is not yet where a finger can be.
            def press(sel):
                pg.evaluate("(s) => document.querySelector(s).click()", f"{frame} {sel}")
                pg.wait_for_timeout(300)
            ask()                                                            # playing
            press(".player-controls .primary")                               # paused
            ask()
            pg.evaluate(f"() => document.querySelector('{frame} .rl-scrub').classList.add('dragging')")
            ask()                                                            # a drag on the scrubber
            pg.evaluate(f"() => document.querySelector('{frame} .rl-scrub').classList.remove('dragging')")
            press(".rl-speed")
            ask()                                                            # the speeds open
            press(".rl-speed")
            pg.evaluate(f"() => document.querySelector('{frame}').classList.add('chrome-asleep')")
            ask()                                                            # stepped back
            pg.close()
        # The Library: nothing here outside its stage may match either.
        for view in ("phone", "desk"):
            pg = b.new_page(**(PHONE if view == "phone" else DESK))
            browsing.goto(pg, base, "/library")
            pg.wait_for_timeout(1500)
            _i, o = pg.evaluate(ASK, [sels, strip, ".stageCanvasWrap"])
            out.update(o)
            pg.close()
        b.close()
    live = json.loads(Path(live_path).read_text())
    live["band"] = sorted(band - out)
    live["band_out"] = sorted(band & out)
    Path(live_path).write_text(json.dumps(live, indent=1) + "\n")
    print(f"band: {len(live['band'])} selectors inside the frame only; "
          f"{len(live['band_out'])} inside it and outside too (left out):")
    for x in live["band_out"]:
        print("   ", x)


if len(sys.argv) > 2 and sys.argv[1] == "--band-census":
    band_census(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ROOT / "harness" / "tools" / "css_live.json")

if len(sys.argv) > 2 and sys.argv[1] == "--emit":
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "skribl" / "static" / "player.css"
    n = emit(sys.argv[2], out)
    print(f"emitted {n:,} chars")
    # The band's sheet beside it: the same command keeps both current.
    nb = emit_band(sys.argv[2], out.with_name("fullband.css"))
    if nb:
        print(f"emitted {nb:,} chars of the band (fullband.css)")
