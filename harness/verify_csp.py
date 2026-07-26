"""v105 — a real Content-Security-Policy, now that nothing off-origin is loaded.

CSP was deferred for as long as gifenc/mp4-muxer came from jsdelivr: any workable
policy needed a third-party script-src, and the CDN loaders were themselves inline
<script type="module"> blocks. Vendoring both (v103/v104) removed the last
off-origin script and the last inline module, so script-src can now be strict.

This suite tests three separate things, because "the header is present" is the
weakest possible claim:
  1. SHAPE      — the policy says what we think it says.
  2. ENFORCED   — an un-nonced inline script is actually BLOCKED (positive
                  control). A header the browser ignores would pass (1) but fail
                  this.
  3. NON-BREAKING — every surface loads with ZERO securitypolicyviolation events,
                  the nonced config scripts still execute, and the two paths most
                  likely to trip a naive policy still work: a real GIF export
                  (blob:) and fetch() against a data: URL, which app.js does to
                  load audio and which `connect-src 'self'` alone would silently
                  break.
"""
import json
import urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def directives(policy):
    out = {}
    for part in policy.split(";"):
        part = part.strip()
        if part:
            bits = part.split()
            out[bits[0]] = bits[1:]
    return out


# Post a Skribl so /s/<id> can be exercised as a real page, not a 404 shell.
payload = {
    "title": "CSP probe",
    "frames": [{"strokes": [], "strokeGroups": [], "background": {"color": "#101418"},
                "photo": None, "music": None}],
    "canvasSize": {"w": 640, "h": 460},
}
req = urllib.request.Request(BASE + "/api/skribls",
                             data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    api_headers = dict(r.headers)
    public_id = json.loads(r.read())["id"]

SURFACES = [("Pad", "/"), ("Flip", "/flip"), ("Player", f"/s/{public_id}")]

LISTEN = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', e => {
    window.__csp.push(e.violatedDirective + ' <- ' + (e.blockedURI || '(inline)'));
});
"""

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    ctx.add_init_script(LISTEN)

    print("\nSHAPE — the policy says what we think it says")
    resp = ctx.request.get(BASE + "/")
    policy = resp.headers.get("content-security-policy")
    check("Content-Security-Policy header is set (enforcing, not report-only)", bool(policy))
    d = directives(policy or "")
    check("default-src is 'self'", d.get("default-src") == ["'self'"], str(d.get("default-src")))
    check("script-src carries a nonce", any(x.startswith("'nonce-") for x in d.get("script-src", [])),
          str(d.get("script-src")))
    check("script-src has no 'unsafe-inline'", "'unsafe-inline'" not in d.get("script-src", []))
    check("no 'unsafe-eval' anywhere in the policy", "unsafe-eval" not in (policy or ""))
    check("object-src is 'none'", d.get("object-src") == ["'none'"])
    check("base-uri is locked to 'self'", d.get("base-uri") == ["'self'"])
    # The specific trap: app.js does fetch(data:...) to load audio.
    check("connect-src allows data: (audio loading depends on it)",
          "data:" in d.get("connect-src", []), str(d.get("connect-src")))
    check("media-src allows data: and blob:",
          "data:" in d.get("media-src", []) and "blob:" in d.get("media-src", [])) 
    check("img-src allows data: and blob:",
          "data:" in d.get("img-src", []) and "blob:" in d.get("img-src", []))
    # Deliberate omission — the player is embedded in an iframe on skribls.net.
    check("frame-ancestors is deliberately ABSENT (embedding must keep working)",
          "frame-ancestors" not in d, str(d.get("frame-ancestors")))
    check("X-Frame-Options still absent for the same reason",
          "x-frame-options" not in {k.lower() for k in resp.headers})
    check("the API response carries the policy too",
          any(k.lower() == "content-security-policy" for k in api_headers))

    print("\nNONCE — per-request, and it matches the tag the template rendered")
    a = ctx.request.get(BASE + "/").headers.get("content-security-policy")
    b = ctx.request.get(BASE + "/").headers.get("content-security-policy")
    n_a = [x for x in directives(a)["script-src"] if x.startswith("'nonce-")][0]
    n_b = [x for x in directives(b)["script-src"] if x.startswith("'nonce-")][0]
    check("a fresh nonce is issued per request", n_a != n_b, f"{n_a[:18]}… vs {n_b[:18]}…")

    pad = ctx.new_page()
    pad_resp = pad.goto(BASE + "/", wait_until="load")
    header_nonce = [x for x in directives(pad_resp.headers["content-security-policy"])["script-src"]
                    if x.startswith("'nonce-")][0].split("-", 1)[1].rstrip("'")
    tag_nonce = pad.evaluate("""() => {
        const s = [...document.querySelectorAll('script')].find(s => !s.src && s.nonce);
        return s ? s.nonce : null; }""")
    check("the rendered inline <script> carries the same nonce as the header",
          tag_nonce == header_nonce, f"tag {str(tag_nonce)[:14]}… vs header {header_nonce[:14]}…")
    check("the nonced config script actually EXECUTED",
          pad.evaluate("() => window.SKRIBL_MODE") == "editor")

    print("\nENFORCED — an un-nonced inline script is blocked (positive control)")
    pad.evaluate("""() => { window.__csp = [];
        const s = document.createElement('script');
        s.textContent = 'window.__unnonced_ran = true;';
        document.head.appendChild(s); }""")
    pad.wait_for_timeout(300)
    check("a DOM-inserted inline script without the nonce does NOT run",
          pad.evaluate("() => window.__unnonced_ran") is None)
    check("and it raises a script-src violation",
          any("script-src" in v for v in pad.evaluate("() => window.__csp")),
          str(pad.evaluate("() => window.__csp")[:1]))

    print("\nNON-BREAKING — every surface loads clean under the policy")
    pages = {}
    for label, path in SURFACES:
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e, _e=errs: _e.append(str(e)))
        pg.goto(BASE + path, wait_until="load")
        pg.wait_for_timeout(1500)
        pages[label] = (pg, errs)
        v = pg.evaluate("() => window.__csp")
        check(f"{label}: zero CSP violations", not v, "; ".join(v[:3]))
        check(f"{label}: no page errors", not errs, "; ".join(errs[:2]))

    check("Player's nonced config script ran (SKRIBL_MODE set)",
          pages["Player"][0].evaluate("() => window.SKRIBL_MODE") == "player")
    check("vendored libraries still load under script-src 'self'",
          pages["Flip"][0].evaluate(
              "() => typeof (window.gifenc||{}).GIFEncoder === 'function' && !!window.Mp4Muxer"))

    print("\nNON-BREAKING — the two paths a naive policy would silently break")
    # 1. fetch() against a data: URL — exactly what app.js does to load audio.
    ok_data = pages["Pad"][0].evaluate("""async () => {
        try {
            const r = await fetch('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=');
            const b = await r.arrayBuffer();
            return b.byteLength > 0;
        } catch (e) { return 'THREW: ' + e.message; } }""")
    check("fetch() of a data: URL succeeds (connect-src data:)", ok_data is True, repr(ok_data))
    check("...and it raised no violation",
          not [v for v in pages["Pad"][0].evaluate("() => window.__csp") if "connect" in v])

    # 2. A real GIF export: blob: object URL + <a download>, under the policy.
    flip = pages["Flip"][0]
    for i in range(3):
        flip.evaluate("() => addFrame()")
        box = flip.locator("#pad").bounding_box()
        flip.mouse.move(box["x"] + 90 + i * 20, box["y"] + 90)
        flip.mouse.down()
        for k in range(20):
            flip.mouse.move(box["x"] + 90 + i * 20 + k * 6, box["y"] + 100 + (k % 4) * 5)
        flip.mouse.up()
    flip.evaluate("() => openExportSheet()")
    flip.wait_for_timeout(400)
    with flip.expect_download(timeout=60000) as dl:
        flip.click("#exportGif")
    raw = open(dl.value.path(), "rb").read()
    check("a real GIF still exports under CSP (blob: + download)",
          raw[:6] == b"GIF89a", f"{len(raw)} bytes")
    check("the export raised no CSP violation", not flip.evaluate("() => window.__csp"),
          "; ".join(flip.evaluate("() => window.__csp")[:2]))

    print("\nSTATIC — assets are covered too")
    st = ctx.request.get(BASE + "/static/skribl/gifenc.min.js")
    check("static assets carry the security headers",
          any(k.lower() == "content-security-policy" for k in st.headers)
          and st.headers.get("x-content-type-options") == "nosniff")

    br.close()

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
