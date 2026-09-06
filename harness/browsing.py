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
}


def boot_key(path):
    """Which __skriblBoot flag a path should wait for, or None if the surface
    does not set one (the player, library and feed do not)."""
    return BOOT_MARKER.get(path.split("?")[0])


def open_page(target, base, path, *, viewport=None, settle=150, boot_timeout=5000):
    """goto `base+path` and return a page that has actually finished booting.

    `target` is anything with .new_page() — a Browser or a BrowserContext.
    """
    page = target.new_page(viewport=viewport) if viewport else target.new_page()
    goto(page, base, path, settle=settle, boot_timeout=boot_timeout)
    return page


def goto(page, base, path, *, settle=150, boot_timeout=5000):
    """Navigate an existing page and wait for the surface to be ready."""
    page.goto(base + path, wait_until="load")
    key = boot_key(path)
    if key:
        # A PATH DOES NOT IDENTIFY A SURFACE, which is what the first version
        # of this got wrong. "/" is Skribl's Pad when BASE points at Skribl —
        # but verify_example.py points BASE at the EXAMPLE HOST APP, whose root
        # is the host's own page and sets no marker. Insisting on it there took
        # the full timeout and then crashed the suite.
        #
        # So the marker is an OPTIMISATION, not a preconditon: wait a bounded
        # time for it, and fall through to the settle if the page turns out not
        # to be a Skribl editor. A page that IS Pad but failed to boot still
        # fails — on the assertions that then find no editor, which is the
        # honest place for that failure rather than a timeout in a helper.
        try:
            page.wait_for_function(
                "k => !!(window.__skriblBoot && window.__skriblBoot[k])",
                arg=key, timeout=boot_timeout)
        except Exception:
            pass
    if settle:
        page.wait_for_timeout(settle)
    return page
