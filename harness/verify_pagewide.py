"""No style rule searches the whole page.

THE COST (Phase 1 of the polish plan, measured at phone pace: Chromium, the
CPU 4x slower, 4G). Five rules began at the top of the page, `html:has(...)`
and `body:has(...)`: the Saved pill hid under an open drawer, sheet or card,
pull-to-refresh stopped under an open sheet, and the scrollbar gutter went
while anything was full screen. A :has() anchored at the root is checked again
whenever anything under it changes, and each check walks the whole page. An
editor makes about 235 small style passes while it opens, and those five
rules were 2.9 s of Pad's style work and 4.3 s of Flip's; a copy of the
stylesheet without them took 0.16 s and 0.23 s, every element's computed
style the same at rest. Now the page says what is open, as classes on <html>
(lib/opensurfaces.js; full screen is lib/immersive.js's), and the rules key on
those.

WHAT THIS ASKS, from source, with no browser and no server:

  1. No selector in any stylesheet, or in a template's <style>, puts :has()
     on html, body or :root. Read from the rule heads after the comments are
     gone, so prose that names the pattern does not count and a rule cannot
     hide behind one.
  2. Every `html.skribl-*` class a rule keys on is set by a module in lib/,
     and every page whose styles read one of the open-surface classes loads
     the module that sets them (or the rule never applies there).

The behaviour itself is pinned where it always was: verify_pillfit (the pill
and its x under a drawer and under Tune), verify_sheetswipe (no pull to
refresh while a sheet is open), verify_player_isolation (the full screen
gutter).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assertions import make_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "skribl" / "static"
TEMPLATES = ROOT / "skribl" / "templates" / "skribl"
results = []
check = make_check(results)


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def heads(css):
    """Every rule head (selector list) in a stylesheet, at any depth inside
    @media and @supports; at-rule preludes are left out."""
    out, start = [], 0
    for m in re.finditer(r"[{};]", css):
        if m.group() == "{":
            head = css[start:m.start()].strip()
            if head and not head.startswith("@"):
                out.append(head)
        start = m.end()
    return out


def split_top(text, seps):
    """Split at characters in `seps` that are not inside (), [] or quotes."""
    parts, cur, depth, quote = [], "", 0, None
    for ch in text:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if depth == 0 and ch in seps:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)
    return [p for p in (x.strip() for x in parts) if p]


ROOTED = re.compile(r"^(?:html|body)(?![\w-])|^:root(?![\w-])")


def rooted_has(selector):
    """True when a compound of the selector is html, body or :root and carries
    a :has()."""
    return any(ROOTED.match(c) and ":has(" in c for c in split_top(selector, " >+~"))


def sources():
    """(label, css text) for every stylesheet and every template <style>."""
    for p in sorted(STATIC.glob("*.css")):
        yield p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")
    for p in sorted(TEMPLATES.glob("*.html")):
        for i, block in enumerate(re.findall(r"<style[^>]*>(.*?)</style>", p.read_text(encoding="utf-8"), re.S)):
            yield f"{p.relative_to(ROOT).as_posix()} <style> {i + 1}", block


print("PAGE-WIDE :has() — no rule searches the whole page")
found, nsel = [], 0
for label, css in sources():
    for head in heads(strip_comments(css)):
        for sel in split_top(head, ","):
            nsel += 1
            if rooted_has(sel):
                found.append(f"{label}: {sel[:90]}")
check(f"no selector puts :has() on html, body or :root ({nsel} selectors read)",
      not found, "; ".join(found[:8]) + (f" (+{len(found) - 8} more)" if len(found) > 8 else ""))
check("...and the reader sees selectors at all (a reader that found none would pass anything)",
      nsel > 1000, f"{nsel} selectors")
check("...and it tells the shape apart: html:has(x), body.a:has(x) and :root:has(x) count, .a:has(x) does not",
      rooted_has("html:has(.x) .y") and rooted_has("body.a:has(.x)") and rooted_has(":root:has(x)")
      and not rooted_has(".panel:has(.x) .y") and not rooted_has("html .a:has(.x)")
      and not rooted_has("htmlish:has(x)"), "the classifier's own cases")

print("\nTHE CLASSES THAT SAY WHAT IS OPEN — each has an owner, on every page that reads it")
libs = {p.name: p.read_text(encoding="utf-8") for p in (STATIC / "lib").glob("*.js")}
used = {}
for label, css in sources():
    for head in heads(strip_comments(css)):
        for cls in re.findall(r"html\.(skribl-[a-z-]+)", head):
            used.setdefault(cls, set()).add(label.split(" <style>")[0])
owner = {cls: sorted(n for n, src in libs.items() if re.search(r"['\"]" + re.escape(cls) + r"['\"]", src))
         for cls in used}
check("every html.skribl-* class a rule keys on is set by a module in lib/",
      used and all(owner[c] for c in used),
      ", ".join(f"{c} <- {owner[c] or 'NOBODY'}" for c in sorted(used)))
OPEN = ("skribl-covered", "skribl-carded", "skribl-sheet")
src_os = libs.get("opensurfaces.js", "")
check("...lib/opensurfaces.js sets the three open-surface classes",
      all(f"'{c}'" in src_os for c in OPEN), str([c for c in OPEN if f"'{c}'" not in src_os]))
check("...lib/immersive.js sets skribl-fullscreen",
      "'skribl-fullscreen'" in libs.get("immersive.js", ""), "")


def page_css(tpl_text):
    """The stylesheets a page links, plus its own <style> blocks."""
    out = []
    for name in re.findall(r"skribl_asset\('([a-z0-9_]+\.css)'\)", tpl_text):
        p = STATIC / name
        if p.exists():
            out.append(p.read_text(encoding="utf-8"))
    out.extend(re.findall(r"<style[^>]*>(.*?)</style>", tpl_text, re.S))
    return strip_comments("\n".join(out))


missing, readers = [], []
for p in sorted(TEMPLATES.glob("*.html")):
    t = p.read_text(encoding="utf-8")
    css = page_css(t)
    for cls, module in [(c, "opensurfaces.js") for c in OPEN] + [("skribl-fullscreen", "immersive.js")]:
        if re.search(r"html\." + re.escape(cls) + r"(?![\w-])", css):
            readers.append(f"{p.name}:{cls}")
            # The script tag itself, not the words: a comment naming the module
            # beside a deleted tag must not count as loading it.
            if not re.search(r"<script[^>]*skribl_asset\('lib/" + re.escape(module) + r"'\)", t):
                missing.append(f"{p.name} reads html.{cls} but does not load lib/{module}")
check(f"every page whose styles read an open-surface class loads the module that sets it ({len(readers)} reads)",
      not missing and len(readers) >= 8, "; ".join(missing) or ", ".join(readers))

passed = sum(1 for ok_, _ in results if ok_)
bad = [n for ok_, n in results if not ok_]
print(f"\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(bad)))
sys.exit(1 if bad else 0)
