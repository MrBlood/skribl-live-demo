#!/usr/bin/env python3
"""Shared page-opening for the harness.

WHY. The declutter review aimed Phase 6 at the 133 browser-launch sites. The
measurement says the launches are not the cost:

    133 chromium.launch()            ~78 seconds in total
    1,330 wait_for_timeout() calls   ~17 minutes of unconditional sleeping

Thirteen times more wall-clock is spent sleeping than starting browsers, and
274 of those sleeps sit directly after a `goto()` — waiting for the app to
boot by guessing how long booting takes.

THERE IS A REAL SIGNAL, so the guess is unnecessary. app.js and flip.js each
set `window.__skriblBoot` on their last executed line:

    window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { pad: true });
    window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { flip: true });

Waiting for that is FASTER on a fast machine and SAFER on a slow one — a fixed
1200 ms sleep is simultaneously too long for CI and too short for a loaded
laptop, which is how a suite becomes intermittently red. Four suites already
read the marker; this makes it the default way in.

A SMALL SETTLE REMAINS ON PURPOSE. Booted is not the same as laid out: some
assertions measure geometry that a resize observer or a font swap can still
move. `settle` keeps a fraction of the old sleep rather than assuming the
marker is the end of all work.
"""

BOOT_MARKER = {
    "/": "pad", "/skribl-pad": "pad", "/flip": "flip",
    "/library": "library", "/feed": "feed", "/gallery": "gallery",
}

# The PLAYER runs app.js, so it raises the same flag Pad does — verified in a
# browser rather than assumed, because "which script backs this surface" is
# exactly the kind of thing that reads obvious and is wrong. /s/<id> is a
# prefix rather than a fixed path, so it cannot live in the table above.
PLAYER_PREFIX = "/s/"


def boot_key(path):
    """Which __skriblBoot flag a path should wait for, or None if unknown.

    Every Skribl surface raises one as of v282; library.js and feed.js gained
    theirs here. None still happens legitimately — verify_example points BASE
    at a HOST application whose root is not a Skribl surface at all.
    """
    p = path.split("?")[0]
    if p.startswith(PLAYER_PREFIX):
        return "pad"
    return BOOT_MARKER.get(p)


def open_page(target, base, path, *, viewport=None, settle=150,
              boot_timeout=5000, require_boot=None):
    """goto `base+path` and return a page that has actually finished booting.

    `target` is anything with .new_page() — a Browser or a BrowserContext.
    """
    page = target.new_page(viewport=viewport) if viewport else target.new_page()
    goto(page, base, path, settle=settle, boot_timeout=boot_timeout,
         require_boot=require_boot)
    return page


class BootFailure(RuntimeError):
    """A surface that should have booted did not, within boot_timeout."""


def goto(page, base, path, *, settle=150, boot_timeout=5000, require_boot=None):
    """Navigate an existing page and wait for the surface to be ready.

    A known Skribl surface must raise its boot marker; a missing marker is a
    BootFailure naming the path, the marker and what `window.__skriblBoot`
    actually held. It fails closed so a dead script reports itself rather than
    surfacing three screens later as "no editor" — `verify_boot.py` asserts
    both directions, including that this helper can go red.

    `require_boot` resolves three ways:

      None (default)  require the marker when boot_key() knows one for `path`,
                      and skip the wait when it does not.
      False           never wait, never raise. Documented cases below ONLY;
                      each call site must say which, and why.
      True            require, and raise if no marker is known for the path —
                      that combination is a programming error, not a slow page.

    TWO OPT-OUT CASES EXIST AND THEY ARE NOT THE SAME:

      1. NOT A SKRIBL SURFACE. verify_example.py points BASE at the example
         HOST app, whose "/" raises no marker.
      2. A SKRIBL SURFACE DELIBERATELY PREVENTED FROM BOOTING. verify_visual.py
         aborts app.js on purpose, to assert the editor is not blank while it
         downloads. The page can never set the marker; that IS the assertion.

    Blocking ONE script is not case 2: verify_gifenc.py aborts gifenc.min.js and
    Flip still boots, which it asserts on the next line, so it requires the
    marker like everything else.

    A growing count of require_boot=False call sites is itself the warning.
    """
    page.goto(base + path, wait_until="load")
    key = boot_key(path)

    if require_boot is True and key is None:
        raise BootFailure(
            f"require_boot=True for {path!r}, but no boot marker is known for "
            f"that path. Add it to BOOT_MARKER, or the caller means "
            f"require_boot=False.")

    if key and require_boot is not False:
        try:
            page.wait_for_function(
                "k => !!(window.__skriblBoot && window.__skriblBoot[k])",
                arg=key, timeout=boot_timeout)
        except Exception:
            # Report what DID boot. An empty/absent object means the script
            # never reached its last line; a populated one missing this key
            # means the wrong surface answered.
            try:
                seen = page.evaluate("() => window.__skriblBoot || null")
            except Exception:
                seen = "<unreadable>"
            raise BootFailure(
                f"{path!r} did not raise __skriblBoot.{key} within "
                f"{boot_timeout} ms — the script backing this surface threw "
                f"before its last line, or never ran.\n"
                f"  window.__skriblBoot = {seen!r}\n"
                f"  If this page legitimately cannot boot, pass "
                f"require_boot=False AND say why at the call site.") from None

    if settle:
        page.wait_for_timeout(settle)
    return page


def submit_post(page, *, timeout_ms=20000, step_ms=200):
    """Press the Pad's Post button and wait for the sheet to say what happened.

    Returns {"url": <the share link or None>, "status": <the POST's HTTP status
    or None>, "label": <the sheet's status text>, "console": [...warnings]}.

    THREE FIXTURES USED TO CLICK, SLEEP A FIXED SPAN AND GREP THE DOM FOR '/s/'
    (verify_player_photo, verify_sharecard, verify_visual). Every push to main
    from v304's first gallery merge failed exactly those three, in both CI
    jobs, with "no /s/ URL found" and nothing else. Instrumented, the failure
    read: POST 201, the sheet says "Posted!". The post was fine. What the
    scrape had been finding was the Your Skribls DRAWER, which the editor
    included and re-rendered after a post -- a row whose href is the share
    link -- and v304 moved that drawer to the profile page (#186), so the
    editor's DOM no longer carries the link at all. Three fixtures depended on
    a surface they never named, and the merge that moved it ran the suites it
    knew about. So: read the URL from the POST's own response, which is the
    server's answer and the thing post_one() in verify_library reads; poll
    for the result row rather than sleeping; and when neither comes, carry
    the status and the sheet's words out through the check, which is the
    channel the runner reads. A fixture that fails should say why.
    """
    seen = {"status": None, "url": None}
    console = []

    def _on_response(r):
        try:
            if r.request.method == "POST" and r.url.split("?")[0].endswith("/api/skribls"):
                seen["status"] = r.status
                if r.ok:
                    body = r.json()
                    u = body.get("url") if isinstance(body, dict) else None
                    if u:
                        seen["url"] = u if u.startswith("http") else (r.url.split("/api/")[0] + u)
        except Exception:
            pass

    def _on_console(m):
        try:
            if m.type in ("warning", "error"):
                console.append(m.text[:160])
        except Exception:
            pass

    page.on("response", _on_response)
    page.on("console", _on_console)
    page.click("#postSubmitBtn")
    url = None
    waited = 0
    while waited < timeout_ms:
        page.wait_for_timeout(step_ms)
        waited += step_ms
        state = page.evaluate("""() => {
            const row = document.getElementById('postResult');
            const shown = !!row && !row.hidden;
            const v = [...document.querySelectorAll('*')].map(e => e.value || e.href || '')
              .find(v => typeof v === 'string' && v.includes('/s/'));
            const label = (document.getElementById('postStatusLabel') || {}).textContent || '';
            const btn = document.getElementById('postSubmitBtn');
            return { shown, url: v || null, label, idle: !!btn && !btn.disabled };
        }""")
        if state["shown"] and (seen["url"] or state["url"]):
            url = seen["url"] or state["url"]
            break
        # The sheet has settled without a result: an error state re-enables
        # the button ("Try again"); do not sit out the whole timeout for it.
        if seen["status"] is not None and state["idle"] and waited >= 1500:
            break
    try:
        page.remove_listener("response", _on_response)
        page.remove_listener("console", _on_console)
    except Exception:
        pass
    return {"url": url, "status": seen["status"], "label": (state or {}).get("label", ""),
            "console": console[:3]}
