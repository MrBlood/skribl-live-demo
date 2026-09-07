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
    "/library": "library", "/feed": "feed",
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

    Raises BootFailure if a surface that should raise a boot marker does not.

    THIS FAILS CLOSED, AND THE FIRST VERSION DID NOT. It swallowed the timeout
    with `except: pass` on the reasoning that a Pad which failed to boot would
    still fail later, on the assertions that then find no editor. That reasoning
    is true and insufficient, for the two reasons verify_boot.py exists:

      * the failure surfaces three screens from its cause, as "no editor" rather
        than "flip.js died at line N" — the misattribution that cost four
        debugging rounds in one session and motivated the boot marker at all;
      * a readiness check that cannot go red is not a readiness check. The v282
        release that ADDED "a green check is not evidence until it has been
        shown to go red" to CLAUDE.md shipped this function violating it, which
        is how the outside audit found it.

    `require_boot` resolves three ways:

      None (default)  require the marker when boot_key() knows one for `path`,
                      and skip the wait when it does not.
      False           never wait, never raise. For the two legitimate cases
                      below ONLY, each of which must say WHY at the call site.
      True            require, and raise immediately if no marker is known for
                      the path — that combination is a programming error, not a
                      slow page.

    TWO LEGITIMATE OPT-OUTS EXIST, AND THEY ARE NOT THE SAME CASE:

      1. THE PAGE IS NOT A SKRIBL SURFACE. verify_example.py points BASE at the
         example HOST application, whose "/" is the host's own page and sets no
         marker. Insisting there took the full timeout and then crashed.
      2. THE PAGE IS A SKRIBL SURFACE, DELIBERATELY PREVENTED FROM BOOTING.
         verify_visual.py aborts app.js on purpose to assert the editor is not
         blank in the window a real visitor sits in while it downloads. That is
         the regression a user photographed, so the assertion is load-bearing
         and the page can never set the marker.

    Blocking ONE script is not case 2: verify_gifenc.py aborts gifenc.min.js and
    Flip still boots — it asserts exactly that on the next line — so it requires
    the marker like everything else, and is stronger for it.
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
