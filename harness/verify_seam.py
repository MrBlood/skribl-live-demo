"""Static guards for the two failure modes the v132 refactor exposed.

Neither is catchable by a browser test at the root prefix, which is precisely
why both survived so long.

SECTION 1 — route literals.
    flip.js hardcoded fetch('/api/skribls') and a '/s/' fallback, and the server
    returned a hardcoded f"/s/{id}" in the 201 body. All three were CORRECT at
    the root and wrong everywhere else, so 632 assertions stayed green while a
    prefixed mount would have 404'd. Every route must be derived: url_for() on
    the server, an injected global on the client.

SECTION 2 — module-level names.
    Splitting app.py into a package left five NameErrors that no suite reached
    (MAX_CARD_BYTES, RATE_PENDING_TTL, RATE_CLEANUP_BATCH, ipaddress,
    IntegrityError). Only one was on a path a test walked. A name that no
    import provides is a crash waiting for the right request.

Both sections read source only — no server, no browser.
"""
import ast
import builtins
import importlib
import re
import sys
from pathlib import Path

import _layout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def strip_comments(js):
    """Remove // line and /* */ block comments so prose doesn't trip the guard."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    return "\n".join(re.sub(r"//.*$", "", line) for line in js.split("\n"))


# ---------------------------------------------------------------- section 1
print("\nSEAM 1 — no route literals in client code")

ROUTE_LITERALS = [
    (r"""['"]/api/skribls""", "/api/skribls"),
    (r"""['"]/s/['"]""", "/s/"),
    (r"""['"]/skribl-pad""", "/skribl-pad"),
]

# Vendored libraries are third-party and not ours to police.
VENDORED = {"gifenc.min.js", "mp4-muxer.min.js"}

js_files = [p for p in sorted(_layout.STATIC_DIR.rglob("*.js"))
            if p.name not in VENDORED]
check("found the client scripts to scan", len(js_files) >= 3,
      ", ".join(p.name for p in js_files))

for p in js_files:
    src = strip_comments(p.read_text(encoding="utf-8"))
    for pattern, label in ROUTE_LITERALS:
        hits = re.findall(pattern, src)
        check(f"{p.name} contains no {label!r} literal", not hits,
              f"{len(hits)} occurrence(s)")

print("\nSEAM 1b — every surface is handed its routes")
tpls = {p.name: p.read_text(encoding="utf-8")
        for p in _layout.TEMPLATES_DIR.glob("skribl_*.html")}
for name in ("skribl_editor.html", "skribl_flip.html", "skribl_player.html"):
    src = tpls.get(name, "")
    check(f"{name} exists", bool(src))
    check(f"{name} injects SKRIBL_API_BASE", "window.SKRIBL_API_BASE" in src)
    # The value must come from Jinja, not be typed in.
    m = re.search(r"window\.SKRIBL_API_BASE\s*=\s*([^;]+);", src)
    check(f"{name} derives it rather than hardcoding it",
          bool(m) and "skribl_api_base" in m.group(1),
          m.group(1).strip() if m else "not assigned")
    check(f"{name}'s config block is nonced",
          re.search(r'<script nonce="\{\{ csp_nonce \}\}">', src) is not None)

print("\nSEAM 1d — asset cache-busts are derived, not typed")
for name, src in sorted(tpls.items()):
    hand = re.findall(r"v='[0-9]+'", src)
    check(f"{name} has no hand-typed ?v= bust", not hand, ", ".join(hand[:3]))
    check(f"{name} routes assets through skribl_asset()",
          "url_for('skribl.static'" not in src)


print("\nSEAM 1c — the server builds share URLs from routes")
def strip_py_comments(src):
    """Drop # comments and docstrings, so prose about a fixed bug does not read
    as the bug. (This guard caught its own changelog comment on first run.)"""
    out = []
    for line in src.split("\n"):
        q = None
        buf = []
        for i, ch in enumerate(line):
            if q:
                buf.append(ch)
                if ch == q and line[i-1:i] != "\\":
                    q = None
            elif ch in "\"'":
                q = ch; buf.append(ch)
            elif ch == "#":
                break
            else:
                buf.append(ch)
        out.append("".join(buf))
    return "\n".join(out)


route_src = ""
for cand in (ROOT / "skribl" / "routes.py", ROOT / "app.py"):
    if cand.exists():
        route_src += strip_py_comments(cand.read_text(encoding="utf-8"))
check("no f\"/s/{...}\" literal in the route layer",
      not re.search(r'f"/s/\{', route_src))
check("the created-post response uses url_for",
      re.search(r'"url":\s*url_for', route_src) is not None)


# ---------------------------------------------------------------- section 2
print("\nSEAM 2 — every module-level name resolves")

pkg = ROOT / "skribl"
modules = ([f"skribl.{p.stem}" for p in sorted(pkg.glob("*.py"))
            if p.stem != "__init__"] if pkg.is_dir() else ["app"])
check("found modules to sweep", bool(modules), ", ".join(modules))

unresolved = []
for modname in modules:
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        check(f"{modname} imports", False, f"{type(e).__name__}: {e}")
        continue
    path = ROOT / (modname.replace(".", "/") + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    provided = set(dir(mod)) | set(dir(builtins))
    bound = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(n.name)
            a = n.args
            for arg in a.args + a.kwonlyargs + a.posonlyargs:
                bound.add(arg.arg)
            if a.vararg: bound.add(a.vararg.arg)
            if a.kwarg: bound.add(a.kwarg.arg)
        elif isinstance(n, ast.Lambda):
            for arg in n.args.args: bound.add(arg.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.ClassDef):
            bound.add(n.name)
    missing = sorted({(n.id, n.lineno) for n in ast.walk(tree)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                      and n.id not in provided and n.id not in bound})
    check(f"{modname}: all names resolve", not missing,
          ", ".join(f"{n}@{l}" for n, l in missing[:4]))
    unresolved.extend(missing)

check("no unresolved names anywhere in the package", not unresolved,
      f"{len(unresolved)} total")

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
