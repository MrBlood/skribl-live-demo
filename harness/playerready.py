"""Wait for a /s/<id> player to be READY, not merely painted.

WHY THIS EXISTS. `/s/<id>` serves its markup complete: the transport buttons,
the progress bar and the canvas are all in the HTML and visible the moment the
page paints, because initPlayer() puts `player-mode` on <body> BEFORE it
fetches anything -- deliberately, so the editor chrome never flashes while the
fetch is in flight. Only afterwards does it `await fetch('/api/skribls/<id>')`,
and only after THAT does it bind the transport, draw the idle poster and set
the progress bar.

So several readiness signals a suite reaches for are already true while the
page can do nothing at all:

    paintStrokesStatic exists    defined when app.js is parsed
    #canvas exists               server-rendered markup
    the page has fired load      the fetch is not a subresource

WHAT IS NOT ON THAT LIST, AND THE MEASUREMENT THAT MOVED IT OFF. A visible
transport is NOT one of them, though the first draft of this file said it was.
`_skribl_player_controls.html` ships `<div class="player-shell" id="playerShell"
hidden>`, and `shell.hidden = false` (app.js, in the player setup) runs in the
SAME SYNCHRONOUS TASK as the addEventListener calls and setProgress(0) that
follow it -- there is no top-level await between them. The browser therefore
cannot paint a visible-but-inert button, so Playwright's click(), which waits
for visibility, is sound on this page.

Measured against a deliberately slow /api/skribls/<id>, which is what a runner
mid-checkpoint serves:

    verify_audiostate     29/29   reaches the transport through click()
    verify_audiosession   32/32   reaches the transport through click()
    verify_hold           60/61   samples the poster after a fixed wait
    verify_player_isolation 40/44  samples four things after fixed waits

So the fragile shape is not "press a button that is not bound yet". It is
"SAMPLE THE PAGE AFTER A FIXED WAIT" -- and, separately, a raw
`evaluate(() => el.click())`, which bypasses actionability altogether and is
how verify_framecache lost its clicks for three releases.

THAT MAKES THE VISIBILITY PROXY TRUE BY COINCIDENCE, WHICH IS WHY THIS FILE
DOES NOT USE IT. It holds only while nothing awaits between the unhide and the
last binding; one `await` added in that stretch turns a sound proxy into a
silent race, and nothing would report it. The latch below does not depend on
that property.

WHAT THIS WAITS FOR, AND WHY IT IS THE RIGHT LATCH. `setProgress(0)` is the
LAST statement of initPlayer(), after every addEventListener; and setProgress
is the only writer of an inline width on #playerProgressFill anywhere in the
tree (`grep -rn 'playerProgressFill\\|pFill' skribl/` -- one reader, one
writer). The controls template ships that element with no style attribute at
all. So an inline width on it means exactly one thing: initPlayer ran to its
end on this page.

AND IT IS NON-INVASIVE, which a click-and-read-back probe is not.
verify_framecache can arm its transport by clicking because its verdict is a
paint count. Two suites here assert on what the player holds BEFORE anything is
pressed -- verify_audiosession's "the shared player holds nothing before you
press Play" is the whole point of that section -- and a probing click would
claim the very media session the assertion is about.

ON THE ERROR PATH this times out rather than passing. A 404, or a fetch that
throws, leaves initPlayer through showPlayerError and never reaches
setProgress. That is correct -- there is no player to drive -- and the message
says so instead of leaving a bare Playwright timeout.

A fixed sleep AFTER this is a different thing and stays where a suite has one:
waiting for an animation to settle is a real wait. Waiting for a load is not.
The settles left in place did not move; they now start from a defined zero.

WHAT THE TWO SUITES WERE ACTUALLY LOSING, which is worse than the failures
that led here. Against the slow API they did not simply report fewer passes --
they reported fewer ASSERTIONS, because the rows that failed were the
calibration arms other rows are gated on:

    verify_hold              60/61 -> 62/62   1 assertion was not running
    verify_player_isolation  40/44 -> 55/55  11 assertions were not running

The one in verify_hold is "on /s/ too, a Draw-on page reaches its last stroke
before the page turns". The eleven in verify_player_isolation are the WHOLE
full-screen section of the shared link -- among them "a way OUT is on screen
while full screen", "the drawing FILLS the screen rather than staying
page-sized" and "the transport came with it, painted and pressable". A suite
printing 40/44 looks like four small problems. It had quietly stopped asking
eleven questions about the page people are actually sent.

CALIBRATED ON THE LATCH ITSELF, not just on the suites it fixed. With
setProgress(0) removed from initPlayer -- the one statement this reads --
against the same pages:

    tree          await_player                 await_player_error
    unmutated     returned  2537ms             returned  2520ms
    mutated       RAISED at the timeout,       returned  2510ms
                  naming the missing style

So it reads that signal rather than elapsing a clock, and the two latches are
independent: breaking the success path does not quietly satisfy the error one.
"""

# One reader, one writer. Matched on the MECHANISM -- the inline style the
# player's own code writes -- rather than on any element merely existing.
PLAYER_READY = ("() => { const f = document.getElementById('playerProgressFill');"
                " return !!f && !!f.style.width; }")


def await_player(page, timeout_ms=30000, what="the /s/ player"):
    """Block until this page's player has finished initPlayer().

    Raises with a message naming the cause rather than a bare timeout, because
    the two reasons to reach it are worth telling apart: a page that answered
    an error (no player), and an API read slow enough to outlast the window.
    """
    try:
        page.wait_for_function(PLAYER_READY, timeout=timeout_ms)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise AssertionError(
            f"{what} never finished loading within {timeout_ms}ms: "
            f"#playerProgressFill still carries no inline width, so "
            f"initPlayer() did not reach its last statement. Either the page "
            f"took the showPlayerError path (no post to play), or the read of "
            f"/api/skribls/<id> outlasted the window. Original: {exc}"
        ) from exc


# The ERROR path needs its own latch, and that is not a detail. `await_player`
# waits for something initPlayer only reaches on success, so a page that took
# showPlayerError would sit there until the timeout -- the wait would be
# correct about the player and useless to the assertion. Same defect, different
# surface, different signal: CLAUDE.md's rule that two surfaces sharing a fix
# may need DIFFERENT assertions, met in the one file that fixes both.
PLAYER_ERROR_SHOWN = ("() => { const p = document.getElementById('playerError');"
                      " return !!p && !p.hidden && p.offsetParent !== null; }")


def await_player_error(page, timeout_ms=30000, what="the /s/ error panel"):
    """Block until this page has SHOWN its player-error panel.

    The panel is server-rendered and starts hidden; showPlayerError is the only
    thing that reveals it, so a visible panel means the failure path ran --
    which is the event the assertions about its wording and its Try again
    button are waiting for.
    """
    try:
        page.wait_for_function(PLAYER_ERROR_SHOWN, timeout=timeout_ms)
    except Exception as exc:                      # noqa: BLE001 - re-raised
        raise AssertionError(
            f"{what} never appeared within {timeout_ms}ms: #playerError is "
            f"still hidden, so showPlayerError did not run. Either the page "
            f"loaded a post after all, or the read of /api/skribls/<id> "
            f"outlasted the window. Original: {exc}"
        ) from exc
