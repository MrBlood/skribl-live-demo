"""The controls check_centring.py must reach: read from the SOURCE, not the page.

A census taken from the live DOM only knows the controls it happened to open.
This lists every control the templates and scripts can produce -- each
<button>, each role="button", and each button a script builds -- so the suite
can fail on one it never reached.

Each entry is identified the way the page will be: by its id where the source
gives a fixed one, otherwise by its class (the first class that is the
control's own, not a shared look like "btn" or "menu-item").

    entries()  -> [{"key": "#playBtn" | ".rl-speed", "src": "file:line", "face": "icon"|"short"|"text"|"?"}]

"face" is what the source says the control shows: an SVG or icon macro, a
label of three characters or fewer, longer text, or "?" where a script fills
it in later. Only the suite's live look decides what is measured; the face is
for the report.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "skribl" / "templates" / "skribl"
JS = [p for p in (ROOT / "skribl" / "static").rglob("*.js") if not p.name.endswith(".min.js")]

# Classes that say how a control looks, shared by many; identity comes from
# the next class along. Kept short on purpose: a class here must be a look,
# not a role.
LOOKS = {"btn", "menu-item", "player-btn", "export-opt", "tb", "on", "active", "primary",
         "icon-btn", "btn-icon", "onion-tint", "post-submit", "post-watch", "post-result-soft",
         "pill", "soft", "chip", "seg-btn", "tool-btn", "small", "ghost", "danger", "secondary",
         "is-on", "selected", "lit", "sm", "lg", "round", "glass", "accent", "quiet"}


def _key(attrs):
    m = re.search(r'\bid="([^"{}]+)"', attrs)
    if m:
        return "#" + m.group(1)
    m = re.search(r'\bclass="([^"]*)"', attrs)
    if m:
        cls = [c for c in m.group(1).split() if "{" not in c and "}" not in c]
        own = [c for c in cls if c not in LOOKS]
        if own:
            return "." + own[0]
        if cls:
            return "." + cls[0]
    # No id and no class: a script's button known by its data attribute
    # (the replay line's speeds, data-r).
    m = re.search(r'\b(data-[a-z-]+)=', attrs)
    if m:
        return "[" + m.group(1) + "]"
    return None


def _face(inner):
    if re.search(r"<svg|\{\{\s*[a-z_]+_glyph\(|\{\{\s*icon\(", inner):
        return "icon"
    text = re.sub(r"<[^>]+>|\{[{%#].*?[}%#]\}", "", inner, flags=re.S)
    text = re.sub(r"&[a-z#0-9]+;", "x", text).strip()
    if not text:
        return "?"
    return "short" if len(text) <= 3 else "text"


def _templates():
    out = []
    for p in sorted(TPL.glob("*.html")):
        src = p.read_text()
        # Jinja comments carry example markup; they are prose, not controls.
        src = re.sub(r"\{#.*?#\}", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
        for m in re.finditer(r"<button\b([^>]*)>(.*?)</button>", src, flags=re.S):
            k = _key(m.group(1))
            if k:
                out.append({"key": k, "src": f"{p.name}:{src[:m.start()].count(chr(10)) + 1}", "face": _face(m.group(2))})
        for m in re.finditer(r"<(?!button)([a-z]+)\b([^>]*\brole=\"button\"[^>]*)>", src):
            k = _key(m.group(2))
            if k:
                out.append({"key": k, "src": f"{p.name}:{src[:m.start()].count(chr(10)) + 1}", "face": "?"})
    return out


def _scripts():
    out = []
    for p in sorted(JS):
        src = p.read_text()
        src_nc = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
        src_nc = re.sub(r"(?m)^\s*//.*$", "", src_nc)
        rel = p.relative_to(ROOT / "skribl" / "static")
        for m in re.finditer(r"(\w+)\s*=\s*(?:doc|document)\.createElement\(\s*['\"]button['\"]\s*\)", src_nc):
            var = m.group(1)
            tail = src_nc[m.end():m.end() + 900]
            cm = re.search(re.escape(var) + r"\.(?:className|id)\s*=\s*['\"]([^'\"]+)['\"]", tail)
            if not cm:
                cm = re.search(r"el\(\s*['\"]button['\"]\s*,\s*['\"]([^'\"]+)['\"]", tail)
            if cm:
                attr = cm.group(0)
                if ".id" in attr:
                    k = "#" + cm.group(1)
                else:
                    cls = [c for c in cm.group(1).split() if c not in LOOKS] or cm.group(1).split()
                    k = "." + cls[0]
                out.append({"key": k, "src": f"{rel}:{src_nc[:m.start()].count(chr(10)) + 1}", "face": "?"})
        for m in re.finditer(r"el\(\s*['\"]button['\"]\s*,\s*['\"]([^'\"]+)['\"]", src_nc):
            cls = [c for c in m.group(1).split() if c not in LOOKS] or m.group(1).split()
            out.append({"key": "." + cls[0], "src": f"{rel}:{src_nc[:m.start()].count(chr(10)) + 1}", "face": "?"})
        for m in re.finditer(r"<button\b([^>]*)>", src_nc):
            k = _key(m.group(1).replace("\\'", "'"))
            if k and "'" not in k and "+" not in k:
                out.append({"key": k, "src": f"{rel}:{src_nc[:m.start()].count(chr(10)) + 1}", "face": "?"})
    return out


def entries():
    seen, out = set(), []
    for e in _templates() + _scripts():
        if e["key"] in seen:
            continue
        seen.add(e["key"])
        out.append(e)
    return out


if __name__ == "__main__":
    es = entries()
    for e in es:
        print(f"{e['key']:34} {e['face']:6} {e['src']}")
    print(len(es), "controls")
