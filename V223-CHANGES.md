# v223 — what changed since the sealed v222

**Evidence status: SEALED.** `harness/RELEASE.md` is generated from a full
aggregate run against this tree — PASS, 3134 assertions, 74/74 suites
reporting, 1 skipped (`verify_mp4.py`, no H.264 profile in the build
container's Chromium). The tree hash and the counts are computed, not typed.

That run is the headline of this release as much as any feature: RELEASE.md had
been frozen describing a 64-suite tree at v222 and could not be regenerated at
all, because `release_run.py` refuses to start when a suite on disk is in no
batch and TEN were.

## Narrative

Six user-visible defects and one structural change. The through-line is that
five of the six were invisible to a harness of 3000+ assertions for the same
reason, which is recorded in DECISIONS.md v242–v246 and summarised here.

**The in-between grew a blur, and it was wrong twice.** The halo started as a
MULTIPLE of the brush — the widest pass 3.4x. On the 6px stroke every
measurement used, that is a 7px soft edge and looks right; on a 60px ball it is
a 204px cloud, so the ball inflates instead of smearing. Motion blur does not
fatten an object: it smears it ALONG its travel, which the sample sequence
already did, and leaves the edge ACROSS the travel nearly sharp. The halo is now
a small bounded softness ADDED to the brush.

Then the colour. Canvas composites through PREMULTIPLIED 8-bit alpha, so a pass
at alpha 2/255 stores `round(32 * 2/255) = 0` for `#ffb020`'s blue: an orange
ball grew a RED halo, measured on the canvas as (240,134,2) against a plain
ball's (255,176,32). Hue holds from about `darkest_channel * alpha >= 1.2`, and
alpha 1/255 is wrong for EVERY ink including near-white. `buildTween` now sheds
passes the ink cannot colour and keeps the core, so a saturated ink gets a
sharper exposure rather than a wrong one.

**Playback timing, twice.** A frame becomes visible when its paint COMPLETES, so
scheduling a flat interval stretched every frame by the cost of the one after
it — the page before each blurred in-between held 127ms against a target of 83.
The wait is now the interval MINUS the measured cost of the paint about to
happen. Separately, `hold` did nothing noticeable, and did not: the delay was
read off `frames[playI]` AFTER `playStep()` advanced it, and `playI` is never
wrapped, so a hold stretched the page BEFORE the one carrying it and was ignored
entirely from the second loop onward.

**The add controls moved above the strip.** They act on the page you are on —
`addFrame` and `addTween` both splice at `idx+1` — but were the last child of a
box that scrolls, so inserting after page 2 of 43 meant scrolling to the far end
and back. Above the strip they cannot scroll away at any width, need no scrim,
and give the thumbnails their full width: 7 visible at 1280px against 5.

**Two surfaces, one rule.** `verify_parity.py` has guarded the CONTROLS Pad and
Flip share since v207, and says why: they drift and nobody notices, because
every other suite drives one surface. Three RULES had the same problem, and all
three had drifted — what a hold means, what one frame may spend layering, and
what alpha a stroke carries. `lib/holdtiming.js` and a budget in
`lib/strokelayers.js` own the first two now. The third was a live bug: flip.js's
`alphaOf` was unanchored and matched `rgb()` as well as `rgba()`, and the greedy
body let the BLUE channel land in the alpha group, so
`alphaOf('rgb(255,176,32)')` returned 32. `tweenFade` multiplied by it and
clamped, making an in-between of any such drawing fully opaque.

## Why the harness did not catch any of it

Every one of these passed through a suite that already covered the feature.

  * `verify_tween` had eleven blur assertions and every one asked WHETHER there
    was a falloff. None asked how wide it got relative to what was blurred, and
    none varied the ink. Both defects lived on axes nothing swept.
  * `verify_hold` had 46 assertions proving a hold is written, read, and
    round-trips. None watched a hold HAPPEN.
  * the alpha bug was in code no suite drove with an `rgb()` colour, because the
    pen never produces one — only loaded files and posted payloads do, and the
    server does not validate colour strings.

The answer taken here is parameter sweeps rather than more single-point
assertions. `verify_tween` now runs a 6x5 grid over brush size and ink
saturation; against the old multiplicative halo it reports `+256px`, against the
missing hue guard `12px #ffb020 (0.033 vs 0.125)`.

## Suites

    verify_sharedrules.py   43   NEW — holds, layering budget, stroke alpha,
                                 asserted on the editors AND the player
    verify_tween.py         61   (47 -> 61: the size x saturation sweep)
    verify_hold.py          52   (46 -> 52: a hold measured on a later pass,
                                 which is the only way the wrap defect shows)
    verify_pages.py         58   (54 -> 58: the add controls, hit-tested)
    verify_parity.py       118   unchanged

## Release evidence

`harness/release_run.py` refused to start: TEN suites were on disk and in no
batch — boot, flipdraft, fuzz, liquify, pillfit, select, sharedrules, theme,
tray, tween. `RELEASE.md` was therefore frozen describing a 64-suite tree at
v222 while 74 suites were passing, and every other doc points at RELEASE.md for
volatile facts. That refusal is the feature working; the failure is that adding
a suite means adding a line to `BATCHES` and nothing but a comment says so. It
is the third time (v199, v219, v223).

## Files

    skribl/static/lib/holdtiming.js     NEW — what a hold means, both surfaces
    skribl/static/lib/strokelayers.js   + the layering budget
    skribl/static/flip.js               blur model, hue guard, playback clock,
                                        anchored alphaOf, strokeAlphaOf
    skribl/static/app.js                reads both modules; gains the ceiling
    skribl/templates/skribl/*.html      all three surfaces load the modules
    skribl/static/flip.css              add controls above the strip
    harness/release_run.py              the ten unplaced suites
    harness/fixtures/demo-blur.skribl   regenerated — it showed the old blur
