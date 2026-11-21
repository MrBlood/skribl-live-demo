#!/usr/bin/env python3
"""Every colour token, as a browser resolves it, light and dark: what docs/COLOR-TOKENS.md is made from.

    SKRIBL_BASE=http://127.0.0.1:5001 python3 harness/tools/coloraudit.py --emit docs/COLOR-TOKENS.md

The owner's colour audit (Nov 21; docs/COLOR-AUDIT.md) asked for one table of every token in both themes, as HEX
or sRGB and as OKLCH, with how each is used. Typed by hand such a table is stale the day a colour moves, so it is
MADE: this opens the site (/social/, social.css) and the Pad (/skribl-pad, styles.css) on a running copy, stamps
each theme, and reads every custom property declared on the root the way the page itself would resolve it
(color-mix() and var() worked out by the browser, not by this file). Then, from the stylesheets' own text, which
properties read each token.

It also says what an audit asks next and nothing here can answer by reading one token alone:
  - SEE-THROUGH TOKENS OVER THEIR GROUNDS. A colour at 26% has no colour of its own; each is laid over every
    ground of its theme (source-over in sRGB, as the browser paints) and given as the colours it becomes.
  - ONE COLOUR UNDER SEVERAL NAMES, and NEAR-TWINS (Delta E OK under 0.012), inside a sheet.
  - THE SITE'S COPIES OF THE EDITORS' COLOURS: an exact twin, or a copy that has drifted.
  - WHAT THE SHEETS SAY: colours written straight into rules, color-mix(), gradients, shadows and the soft ones,
    and the blocks that answer forced colours and "more contrast".

NOT A SUITE (harness/tools/README.md): it asserts nothing about the tree and gates nothing. Its own arithmetic is
checked against known values every time it runs (white on black 21 to 1; #777 on white 4.48; Oklab of pure red).
WCAG contrast is the standard's own sum on sRGB. OKLCH and Delta E OK are for laying colours side by side and are
never a statement about whether words can be read.

THE TABLE IS A SNAPSHOT, and says of what: each stylesheet's last commit and its day (Mountain Time). Nothing
re-makes it when a colour moves. Making it again on the same sheets writes the same file byte for byte, so
`git diff docs/COLOR-TOKENS.md` after a re-make answers "is it still true?".

IT REFUSES A COPY THAT IS NOT THIS TREE'S. The values come from the running copy and the usage from this tree's
files; a server started before a stylesheet changed (the site warms its static files when it starts) would put
two trees in one table. So each sheet the copy serves is held to the file here first: by the app's own content
stamp (the ?v= on its link is the first eight of the file's SHA-256: skribl/__init__.py, asset_url), or failing
that byte for byte. Bytes alone cannot say for Skribl's sheets, which are served with their comments stripped.

Needs a server (harness/bootstrap.sh) and Playwright's Chromium, as the browser suites do. No other dependency."""
import argparse
import datetime
import hashlib
import io
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = (("site", "/social/", "social/static/social.css", "The site (`social/static/social.css`)"),
          ("editors", "/skribl-pad", "skribl/static/styles.css", "The Pad and Flip (`skribl/static/styles.css`)"))
# The grounds a see-through token can land on, by sheet: every opaque one that exists is used.
GROUNDS = {"site": ["--page", "--row-band", "--card", "--sheet-paper", "--row-band-sheet", "--btn2-bg"],
           "editors": ["--surface-base", "--surface-raised", "--surface-control", "--menu-paper", "--menu-card", "--btn2-bg"]}
INVENTORY = ("social/static/social.css", "skribl/static/styles.css", "skribl/static/flip.css", "skribl/static/inlineplayer.css",
             "skribl/static/pagemenu.css")


# ------------------------------------------------------------------------------------------------- arithmetic
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def wcag_lum(rgb):
    """WCAG 2.x relative luminance, channels 0..255 (the standard's own constant, 0.03928)."""
    v = [x / 255 for x in rgb[:3]]
    v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    x, y = wcag_lum(a), wcag_lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def over(fg, bg):
    """`fg` (r, g, b, a) over opaque `bg`, source-over in gamma-encoded sRGB: what CSS paints."""
    a = fg[3] if len(fg) > 3 else 1.0
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def oklab(rgb):
    r, g, b = (_lin(x / 255) for x in rgb[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklch(rgb):
    L, a, b = oklab(rgb)
    C = math.hypot(a, b)
    return L, C, (None if C < 0.0005 else math.degrees(math.atan2(b, a)) % 360)


def delta_e_ok(a, b):
    x, y = oklab(a), oklab(b)
    return math.sqrt(sum((x[i] - y[i]) ** 2 for i in range(3)))


def hexs(rgb):
    return "#" + "".join(f"{max(0, min(255, int(round(x)))):02x}" for x in rgb[:3])


def fmt_oklch(rgb, alpha=1.0):
    L, C, h = oklch(rgb)
    s = f"oklch({L * 100:.1f}% {C:.3f} {'none' if h is None else f'{h:.0f}'}"
    return s + (f" / {alpha:g})" if alpha < 0.999 else ")")


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?"
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^()]*\)|hsla?\([^()]*\)|color\([^()]*\)|oklch\([^()]*\)|oklab\([^()]*\)")


def parse(css):
    """One computed colour as Chromium says it -> (r, g, b, a), channels 0..255, or None."""
    if css is None:
        return None
    s = css.strip().lower()
    if s == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    m = re.fullmatch(r"rgba?\(([^)]*)\)", s)
    if m:
        parts = m.group(1).replace("/", " ").replace(",", " ").split()
        if len(parts) < 3:
            return None
        ch = [float(p[:-1]) * 2.55 if p.endswith("%") else float(p) for p in parts[:3]]
        a = 1.0 if len(parts) < 4 else (float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3]))
        return (ch[0], ch[1], ch[2], a)
    m = re.fullmatch(r"color\(srgb\s+(" + _NUM + r")\s+(" + _NUM + r")\s+(" + _NUM + r")(?:\s*/\s*(" + _NUM + r"%?))?\)", s)
    if m:
        a = m.group(4)
        a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return (float(m.group(1)) * 255, float(m.group(2)) * 255, float(m.group(3)) * 255, a)
    return None


def selftest():
    """The instrument against values it must know, every run: a wrong sum here would make every table wrong."""
    assert abs(contrast((255, 255, 255), (0, 0, 0)) - 21) < 1e-9
    assert abs(contrast((119, 119, 119), (255, 255, 255)) - 4.478) < 0.005
    L, a, b = oklab((255, 0, 0))
    assert abs(L - 0.628) < 0.001 and abs(a - 0.225) < 0.001 and abs(b - 0.126) < 0.001, (L, a, b)
    assert oklch((255, 255, 255))[2] is None and abs(oklch((255, 255, 255))[0] - 1) < 1e-4
    assert parse("color(srgb 0.5 0.25 1 / 0.5)") == (127.5, 63.75, 255.0, 0.5)
    assert parse("rgba(60, 40, 140, 0.14)") == (60.0, 40.0, 140.0, 0.14)
    assert hexs(over((0, 0, 0, 0.5), (255, 255, 255))) == "#808080"
    assert delta_e_ok((0, 0, 0), (255, 255, 255)) > 0.999


# ---------------------------------------------------------------------------------------------- the browser
DECLARED = r"""() => {
  const out = [];
  const walk = (rules, sheet, media) => { for (const r of rules) {
    if (r.cssRules && r.conditionText !== undefined) { walk(r.cssRules, sheet, (media ? media + ' and ' : '') + r.conditionText); continue; }
    if (!r.style) { if (r.cssRules) walk(r.cssRules, sheet, media); continue; }
    for (let i = 0; i < r.style.length; i++) { const n = r.style[i];
      if (n.startsWith('--')) out.push({ sheet, media: media || '', sel: r.selectorText, name: n }); }
  } };
  for (const s of document.styleSheets) { let rules = null; try { rules = s.cssRules; } catch (e) { continue; }
    walk(rules, s.href ? new URL(s.href).pathname.split('/').pop().split('?')[0] : '(inline)', ''); }
  return out; }"""

RESOLVE = r"""(names) => {
  const scope = document.body, cs = getComputedStyle(scope), out = {};
  const host = document.createElement('div'); host.style.cssText = 'position:fixed;left:-99px;top:-99px;width:1px;height:1px';
  scope.appendChild(host);
  for (const n of names) {
    const raw = cs.getPropertyValue(n).trim(); const o = { raw };
    if (raw && CSS.supports('color', raw)) {
      const p = document.createElement('i'); p.style.color = raw; host.appendChild(p);
      o.kind = 'color'; o.computed = getComputedStyle(p).color; p.remove();
    } else if (raw && raw !== 'none' && CSS.supports('box-shadow', raw)) {
      const p = document.createElement('i'); p.style.boxShadow = raw; host.appendChild(p);
      o.kind = 'shadow'; o.computed = getComputedStyle(p).boxShadow; p.remove();
    } else o.kind = 'other';
    out[n] = o;
  }
  host.remove();
  return out; }"""


SERVED = r"""async (name) => {
  const s = [...document.styleSheets].find(s => s.href && new URL(s.href).pathname.split('/').pop() === name);
  if (!s) return null;
  return { v: new URL(s.href).searchParams.get('v'), text: await (await fetch(s.href, { cache: 'no-store' })).text() }; }"""


def same_sheet(served, path):
    """Is what the copy serves this tree's file? Its content stamp says so, or its bytes do."""
    raw = (ROOT / path).read_bytes()
    return bool(served) and (served.get("v") == hashlib.sha256(raw).hexdigest()[:8]
                             or served.get("text") == raw.decode("utf-8"))


def read(base):
    """{key: {theme: {"order": [names], "resolved": {name: {...}}}}} from a running copy of THIS tree."""
    from playwright.sync_api import sync_playwright
    got = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for key, path, sheet, _ in SHEETS:
            got[key] = {}
            name = sheet.rsplit("/", 1)[1]
            for theme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": 402, "height": 874}, color_scheme=theme)
                # Skribl's one choice (skribl_theme_v1), stamped by its own boot before the first paint
                ctx.add_init_script("try { localStorage.setItem('skribl_theme_v1', '%s'); } catch (e) {}" % theme)
                pg = ctx.new_page()
                pg.goto(base + path)
                pg.wait_for_load_state("load")
                pg.wait_for_timeout(500)
                pg.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
                pg.wait_for_timeout(120)
                if theme == "light" and not same_sheet(pg.evaluate(SERVED, name), sheet):
                    b.close()
                    raise SystemExit(f"{base}{path} is not serving this tree's {sheet}: restart the copy (a server keeps the "
                                     "stylesheets it started with) and run this again. Nothing was written.")
                declared = [d for d in pg.evaluate(DECLARED) if d["sheet"] == name]
                # the root's own tokens: declared on :root, html or the body (the editors hang some on the body)
                order, seen = [], set()
                for d in declared:
                    if (d["sel"].startswith(":root") or d["sel"] in ("html", "body", "body:not(.player-mode)")) and d["name"] not in seen:
                        seen.add(d["name"])
                        order.append(d["name"])
                got[key][theme] = {"order": order, "resolved": pg.evaluate(RESOLVE, order)}
                ctx.close()
        b.close()
    return got


# ------------------------------------------------------------------------------------------- the sheets' text
def strip_comments(s):
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)


ROLE = (("color", "text"), ("-webkit-text-fill-color", "text"), ("caret-color", "caret"), ("background", "fill"), ("border", "edge"),
        ("outline", "focus"), ("box-shadow", "ring or shadow"), ("text-shadow", "text shadow"), ("fill", "icon"), ("stroke", "icon"),
        ("accent-color", "native control"), ("text-decoration", "underline"), ("scrollbar", "scrollbar"))


def usage(css):
    """{token: "text ×12; fill ×3; feeds --other"} from every declaration that reads var(--token)."""
    got = {}
    for m in re.finditer(r"([-\w]+)\s*:\s*([^;{}]*var\(--[^;{}]*)", css):
        prop, val = m.group(1), m.group(2)
        if prop.startswith("--"):
            role = "feeds " + prop
        else:
            role = next((r for k, r in ROLE if prop == k or prop.startswith(k)), prop)
        for t in set(re.findall(r"var\((--[-\w]+)", val)):
            got.setdefault(t, {})
            got[t][role] = got[t].get(role, 0) + 1
    out = {}
    for t, u in got.items():
        feeds = sorted(k[6:] for k in u if k.startswith("feeds "))
        parts = [f"{k} ×{n}" for n, k in sorted(((n, k) for k, n in u.items() if not k.startswith("feeds ")), reverse=True)]
        if feeds:
            parts.append("feeds " + ", ".join(f"`{f}`" for f in feeds[:3]) + (" …" if len(feeds) > 3 else ""))
        out[t] = "; ".join(parts)
    return out


def declarations(css):
    """(selector, property, value) for every declaration, nested blocks walked by brace depth."""
    out, stack, buf = [], [], ""
    for c in css:
        if c == "{":
            stack.append(buf.strip())
            buf = ""
        elif c in "};":
            if stack and ":" in buf:
                k, v = buf.split(":", 1)
                out.append((stack[-1], k.strip(), " ".join(v.split())))
            buf = ""
            if c == "}" and stack:
                stack.pop()
        else:
            buf += c
    return out


def _layers(value):
    depth, cur, parts = 0, "", []
    for ch in value:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parts + ([cur.strip()] if cur.strip() else [])


def inventory(path):
    css = strip_comments(io.open(ROOT / path, encoding="utf-8").read())
    decl = declarations(css)
    rules = [(s, k, v) for s, k, v in decl if not k.startswith("--")]
    soft = 0
    shadow_lines = [v for s, k, v in rules if k in ("box-shadow", "text-shadow") and v not in ("none", "inherit")]
    for v in shadow_lines:
        for layer in _layers(v):
            if re.fullmatch(r"var\(--[-\w]+\)", layer) or "inset" in layer:
                continue
            body = COLOUR.sub(" ", layer)
            body = re.sub(r"(?:var|calc)\([^()]*(?:\([^()]*\)[^()]*)*\)", " 0px ", body)
            px = [float(x) for x in re.findall(r"(-?\d*\.?\d+)px\b|(?<![\w.])(-?\d*\.?\d+)(?![\w.%])", body) for x in x if x != ""]
            if len(px) >= 3 and px[2] > 2.5:
                soft += 1
    media = re.findall(r"@media[^{]*\{", css)
    return {"tokens": len({k for s, k, v in decl if k.startswith("--")}),
            "literals": sum(len(COLOUR.findall(v)) for s, k, v in rules),
            "mix": sum(1 for s, k, v in decl if "color-mix(" in v),
            "gradients": sum(1 for s, k, v in decl if "gradient(" in v),
            "shadow_lines": len(shadow_lines), "soft": soft,
            "forced": sum("forced-colors" in m for m in media), "more": sum("prefers-contrast" in m for m in media)}


# ---------------------------------------------------------------------------------------------- the document
def stamp(path):
    """'as of commit `abc1234` (Nov 21, 2026)': the sheet's last commit and its day in Mountain Time."""
    def git(*args):
        return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    try:
        got = git("log", "-1", "--abbrev=7", "--format=%h %ct", "--", path).split()
        dirty = git("status", "--porcelain", "--", path)
    except (OSError, subprocess.SubprocessError):
        got, dirty = [], ""
    if len(got) != 2:
        return "as it stands in this tree"
    try:
        from zoneinfo import ZoneInfo
        day = datetime.datetime.fromtimestamp(int(got[1]), ZoneInfo("America/Denver"))
    except Exception:  # no zone data on this box: say the day in UTC, and say so
        day = None
    when = (f"{day:%b} {day.day}, {day.year}" if day else
            f"{datetime.datetime.fromtimestamp(int(got[1]), datetime.timezone.utc):%Y-%m-%d} UTC")
    return f"as of commit `{got[0]}` ({when})" + (", with changes not yet committed" if dirty else "")


def cell(v):
    c = parse(v.get("computed")) if v and v.get("kind") == "color" else None
    if c is None:
        return "–", "–", None
    if c[3] >= 0.999:
        return f"`{hexs(c)}`", f"`{fmt_oklch(c)}`", c
    return f"`rgb({c[0]:.0f} {c[1]:.0f} {c[2]:.0f} / {c[3]:g})`", f"`{fmt_oklch(c, c[3])}`", c


def shadow_words(computed):
    if not computed or computed == "none":
        return "none"
    out = []
    for layer in _layers(computed):
        m = COLOUR.search(layer)
        col = parse(m.group(0)) if m else None
        rest = (layer[:m.start()] + layer[m.end():]) if m else layer
        px = [float(x) for x in re.findall(r"(-?\d*\.?\d+)px", rest)] + [0.0] * 4
        colw = "?" if col is None else hexs(col) + ("" if col[3] >= 0.999 else f" at {col[3]:g}")
        out.append(f"{'inset ' if 'inset' in rest else ''}{px[0]:g} {px[1]:g} {px[2]:g}{'' if not px[3] else f' {px[3]:g}'} {colw}")
    return "; ".join(f"`{o}`" for o in out)


def document(data):
    selftest()
    md = ["# Every colour token, light and dark",
          "",
          "**Generated by `harness/tools/coloraudit.py`; do not edit it by hand.** The audit that asked for it, and",
          "what it found, is `docs/COLOR-AUDIT.md`.",
          "",
          "**A snapshot, and nothing keeps it in step.** It is these stylesheets, with days in Mountain Time:",
          ""] + [f"- `{sheet}` {stamp(sheet)}" for _, _, sheet, _ in SHEETS] + [
          "",
          "Making it again needs a running copy and a browser (the command is in the tool's first lines). Made again",
          "on the same sheets it comes out the same byte for byte, so a re-make that changes nothing says it is still",
          "true.",
          "",
          "Each value is what a browser resolved for the token with the theme stamped, mixes worked out. A value",
          "written `rgb(r g b / a)` is see-through: `a` is how solid it is, and it has no single colour until it",
          "lands on a ground (the tables after each token table). OKLCH is given for comparing colours with each",
          "other; contrast is always WCAG's own sum on sRGB. \"Usage\" is counted from the stylesheet's own text:",
          "which properties read the token, and how often.",
          "",
          "**Wide-gamut (P3) tokens:** none. Every colour here is sRGB, so there is nothing to list apart.",
          ""]
    colours = {}
    for key, path, sheet, title in SHEETS:
        css = strip_comments(io.open(ROOT / sheet, encoding="utf-8").read())
        use = usage(css)
        L, D = data[key]["light"], data[key]["dark"]
        rows, shadows, opaque = [], [], {"light": {}, "dark": {}}
        through = []
        for n in L["order"]:
            l, d = L["resolved"].get(n), D["resolved"].get(n)
            kinds = {(l or {}).get("kind"), (d or {}).get("kind")}
            if "color" in kinds:
                lc, dc = cell(l), cell(d)
                rows.append(f"| `{n}` | {lc[0]} | {lc[1]} | {dc[0]} | {dc[1]} | {use.get(n, 'not read in this sheet')} |")
                colours.setdefault(key, {})[n] = (lc[2], dc[2])
                for th, c in (("light", lc[2]), ("dark", dc[2])):
                    if c is not None and c[3] >= 0.999:
                        opaque[th][n] = c
                if any(c is not None and 0.001 < c[3] < 0.999 for c in (lc[2], dc[2])):
                    through.append(n)
            elif "shadow" in kinds:
                shadows.append(f"| `{n}` | {shadow_words((l or {}).get('computed') if (l or {}).get('kind') == 'shadow' else None)} |"
                               f" {shadow_words((d or {}).get('computed') if (d or {}).get('kind') == 'shadow' else None)} | {use.get(n, 'not read in this sheet')} |")
        md += [f"## {title}", "", f"{len(rows)} colour tokens.", "",
               "| Token | Light HEX/sRGB | Light OKLCH | Dark HEX/sRGB | Dark OKLCH | Usage |", "|---|---|---|---|---|---|"] + rows + [""]
        if shadows:
            md += ["### Shadow tokens (x y blur spread colour, layer by layer)", "", "| Token | Light | Dark | Usage |", "|---|---|---|---|"] + shadows + [""]
        # see-through tokens over the grounds of each theme
        md += ["### See-through tokens, on the grounds they can land on", "",
               "The colour each really is, ground by ground, and its contrast from that ground. \"Wanders\" is the",
               "widest Delta E OK between two of those colours: how much the token changes with what is under it.", ""]
        for th in ("light", "dark"):
            grounds = [(g, opaque[th][g]) for g in GROUNDS[key] if g in opaque[th]]
            md += [f"**{th.capitalize()}**", "", "| Token | Solid | " + " | ".join(f"on `{g}`" for g, _ in grounds) + " | Wanders |",
                   "|---|---|" + "---|" * len(grounds) + "---|"]
            for n in through:
                c = colours[key][n][0 if th == "light" else 1]
                if c is None or not 0.001 < c[3] < 0.999:
                    continue
                on = [over(c, g) for _, g in grounds]
                wander = max((delta_e_ok(a, b) for a in on for b in on), default=0.0)
                md.append(f"| `{n}` | {c[3]:g} | " + " | ".join(f"`{hexs(o)}` {contrast(o, g):.2f}" for o, (_, g) in zip(on, grounds)) + f" | {wander:.3f} |")
            md.append("")
        # one colour under several names; near-twins
        groups = {}
        for n, (lc, dc) in colours[key].items():
            if lc is not None and dc is not None:
                groups.setdefault((tuple(round(x, 2) for x in lc), tuple(round(x, 2) for x in dc)), []).append(n)
        same = [v for v in groups.values() if len(v) > 1]
        md += ["### One colour under several names (the same in both themes)", ""]
        md += [f"- {', '.join(f'`{n}`' for n in v)}" for v in sorted(same, key=lambda v: -len(v))] or ["None."]
        md.append("")
        near = []
        names = [n for n in colours[key] if all(c is not None and c[3] >= 0.999 for c in colours[key][n])]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                de = max(delta_e_ok(colours[key][a][0], colours[key][b][0]), delta_e_ok(colours[key][a][1], colours[key][b][1]))
                if 0 < de < 0.012:
                    near.append((de, a, b))
        md += ["### Near-twins (Delta E OK under 0.012 in both themes, and not identical)", "",
               "A diagnostic only: two names a person could not tell apart side by side. Deliberate steps of a ramp show up",
               "here too; the audit says which are which.", ""]
        md += [f"- `{a}` and `{b}`: {de:.4f}" for de, a, b in sorted(near)] or ["None."]
        md.append("")
    # the site's copies of the editors' colours
    md += ["## The site's copies of the editors' colours", "",
           "For each of the site's colour tokens, the editors' token nearest to it in both themes together (see-through",
           "ones only against tokens as see-through). 0 is an exact copy; a little more than 0 is a copy that has drifted,",
           "or a near miss.", "", "| The site | The editors | Light (site / editors) | Dark (site / editors) | Delta E OK |", "|---|---|---|---|---|"]
    twins = 0
    lines = []
    for a, (al, ad) in colours["site"].items():
        if al is None or ad is None:
            continue
        best = None
        for b, (bl, bd) in colours["editors"].items():
            if bl is None or bd is None or abs(al[3] - bl[3]) > 0.06 or abs(ad[3] - bd[3]) > 0.06:
                continue
            de = max(delta_e_ok(al, bl) + abs(al[3] - bl[3]), delta_e_ok(ad, bd) + abs(ad[3] - bd[3]))
            if best is None or de < best[0]:
                best = (de, b, bl, bd)
        if best is None:
            continue
        if best[0] < 1e-9:
            twins += 1
        elif best[0] < 0.03:
            f = lambda c: hexs(c) if c[3] >= 0.999 else f"rgb({c[0]:.0f} {c[1]:.0f} {c[2]:.0f} / {c[3]:g})"  # noqa: E731
            lines.append((best[0], f"| `{a}` | `{best[1]}` | `{f(al)}` / `{f(best[2])}` | `{f(ad)}` / `{f(best[3])}` | {best[0]:.4f} |"))
    md += [l for _, l in sorted(lines)] + ["", f"Exact copies: {twins} of the site's {len(colours['site'])} colour tokens.", ""]
    # what the sheets say
    md += ["## What the stylesheets say", "",
           "| Stylesheet | Tokens | Colours written into rules | color-mix() | Gradients | Shadow lines | of them soft (blur over 2.5px) | Forced-colours blocks | More-contrast blocks |",
           "|---|---|---|---|---|---|---|---|---|"]
    for path in INVENTORY:
        i = inventory(path)
        md.append(f"| `{path}` | {i['tokens']} | {i['literals']} | {i['mix']} | {i['gradients']} | {i['shadow_lines']} | {i['soft']} | {i['forced']} | {i['more']} |")
    md += ["", "A soft shadow line that is written is not always painted: the crisp rules later in the editors' sheet",
           "override many of the older ones. What is painted is read off the screen, and is in the audit.", ""]
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default=os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001"))
    ap.add_argument("--emit", help="write the document here (default: print it)")
    a = ap.parse_args()
    selftest()
    md = document(read(a.base))
    if a.emit:
        io.open(a.emit, "w", encoding="utf-8").write(md)
        print(f"wrote {a.emit}: {md.count(chr(10)) + 1} lines")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
