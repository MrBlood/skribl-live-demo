"""v105 — the version label in the Pad's overflow menu is single-sourced.

It read "Skribl Pad · v96" while the app was at v105: a hardcoded literal in
skribl_editor.html that nothing forced anyone to update, so it drifted for nine
releases. Cosmetic, but actively misleading — it is the one place a user (or you,
debugging a deploy) looks to answer "what version is actually running?", and it
was answering wrong.

The fix moves the string to SKRIBL_VERSION in app.py and injects it. This suite
exists so the bug cannot come back: it fails if a version literal reappears in a
template, which is the only way this can silently rot again.
"""
import re
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:5001"
ROOT = Path(__file__).resolve().parent.parent

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# Read the constant from source rather than importing app.py, so the suite has no
# import side effects (app.py builds a Flask app at module scope).
src = (ROOT / "app.py").read_text(encoding="utf-8")
m = re.search(r'^SKRIBL_VERSION\s*=\s*"([^"]+)"', src, re.M)

print("\nSOURCE — one constant, one place")
check("app.py defines SKRIBL_VERSION", bool(m), m.group(1) if m else "not found")
version = m.group(1) if m else None
check("it looks like a version string", bool(version and re.fullmatch(r"v\d+(\.\d+)*", version)),
      repr(version))

print("\nTEMPLATES — no hardcoded version literals left to rot")
for tpl in sorted((ROOT / "templates").glob("*.html")):
    body = tpl.read_text(encoding="utf-8")
    # Ignore cache-busts (v='104') and prose inside comments; look for a version
    # literal rendered as visible text, which is what drifted.
    visible = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    hits = re.findall(r"·\s*v\d+|>\s*v\d+\s*<|Skribl \w+ · v\d+", visible)
    check(f"{tpl.name}: no hardcoded version in visible text", not hits, str(hits[:2]))

print("\nRENDERED — the page shows what app.py says")
html = urllib.request.urlopen(BASE + "/").read().decode("utf-8", "replace")
label = re.search(r'class="menu-version">([^<]*)</div>', html)
check("the Pad renders a version label", bool(label), label.group(1) if label else "missing")
rendered = label.group(1).strip() if label else ""
check("the label carries the current version", bool(version) and version in rendered,
      f"{rendered!r} should contain {version!r}")
check("the label still reads 'Skribl Pad · <version>'",
      rendered == f"Skribl Pad · {version}", repr(rendered))
check("the stale v96 string is gone from the served page", "v96" not in html)

print("\nANTI-DRIFT — the template is genuinely driven by the constant")
tpl_src = (ROOT / "templates" / "skribl_editor.html").read_text(encoding="utf-8")
check("skribl_editor.html interpolates skribl_version instead of a literal",
      "{{ skribl_version }}" in tpl_src)

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
