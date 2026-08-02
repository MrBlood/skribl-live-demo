# Harness

708 assertions across 20 suites. All green as of v137, with nothing skipped —
`mp4-muxer.min.js` is present and PostgreSQL was live for `verify_postgres.py`.
From the repo root: `./harness/run_harness.sh verify_gifenc.py ...`

Per-suite counts below are the v137 run. They drift whenever assertions are
added, so `harness/LAST-RUN.txt` and the machine-generated aggregate are the
authority — this list is a map, not a total.

This sandbox is not browser-gated: Flask runs, `flask_sqlalchemy` installs from
PyPI, and Playwright's Chromium launches.

    pip install flask_sqlalchemy --break-system-packages
    python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
    python3 -m flask --app app run --port 5001 --no-reload

Then, from `harness/`:

    python3 verify_audio.py      #  9  post -> /s/<id> with sound + numeric seam check
    python3 verify_lib.py        #  8  shared audioloop + load-order negative test
    python3 verify_fix.py        # 18  autosave quota fallback + regressions
    python3 verify_amber.py      # 15  amber media state + re-add cards
    python3 verify_dots.py       # 10  amber toolbar dots + card colours
    python3 verify_loopcap.py    # 18  20s loop cap + cropped post payload  (v102)
    python3 verify_race.py       # 17  Pad pre-decode autosave race         (v102)
    python3 verify_muxer.py      # 18  vendored mp4-muxer + MP4 gate        (v103)
    python3 verify_gifenc.py     # 35  vendored gifenc + REAL GIF encode    (v104)
    python3 verify_csp.py        # 31  CSP shape + enforcement + no breakage (v105)
    python3 verify_media.py      # 24  server-side media validation (no browser) (v105)
    python3 verify_version.py    # 20  UI version label single-sourced       (v105)
    python3 verify_ux.py         # 24  export format labels + undoable clear (v106)
    python3 verify_pages.py      # 60  page ops, settings drawer, long strips (v107)
    python3 verify_exopts.py     # 23  export size + page range, byte-verified (v108)
    python3 verify_hold.py       # 26  drag-reorder + per-page hold + compat  (v109)
    python3 verify_canvas.py     # 21  canvas sizes + round-trip + help text  (v110)
    python3 verify_review.py     # 279 external review regressions      (v111-v122)
    python3 verify_postgres.py   # 14  4-worker gunicorn vs live PostgreSQL   (v123)
    python3 verify_pressure.py   # 38  stylus pressure: width, clamp, compat  (v132)

## Gotchas

- **Every suite builds SHORT documents, and that hides a whole class of bug.** The
  thumbnail strip failed to follow the current page for its entire existence: on
  a 62-page flipbook, restoring put the canvas on page 62 while the strip sat at
  page 1, and arrow-key navigation walked the selection off-screen. A strip that
  does not overflow cannot be scrolled to the wrong place, so 20 suites and ~700
  assertions never saw it. Found by a user looking at a real document. The v137
  block in `verify_pages.py` builds 40 pages and asserts the strip overflows
  BEFORE asserting anything about it — an overflow check is what stops that test
  from silently becoming vacuous again.

- **Don't smooth-scroll something you are about to rebuild.** `go()` calls
  `buildStrip()`, which replaces every thumbnail node, so a smooth `scrollIntoView`
  animates an element that is destroyed on the next keypress. Twelve rapid presses
  left `scrollLeft` at 40px. Navigation scrolls instantly; only `addFrame()`
  animates, because nothing rebuilds under it.

- **Don't wait a fixed number of milliseconds for a CSS transition.** The Flip
  settings drawer transitions `grid-template-rows` over 260ms, and
  `verify_pages.py` used to measure the collapsed height after a flat 300ms
  wait. 40ms of margin is not enough on a loaded machine: the assertion reported
  a sub-pixel sliver (0.015625px, 0.375px, 0.765625px) and failed roughly three
  runs in four — **on v131 as well as v132**, which means v131's recorded 38/38
  was a lucky run rather than a stable one. It now waits for `transitionend`.
  Five consecutive green runs before and after the pressure work. If you add an
  animated element, wait for the event, not the clock.

- **The rate limiter will bite you.** `POST /api/skribls` allows 20/hour/IP, and
  the posting suites together sit just under it — so a few new posting assertions
  anywhere produce mystery 429s that look like validation failures. `run_harness.sh`
  exports `SKRIBL_RATE_MAX_POSTS=100000` to keep suites deterministic. The flip
  side is that the limiter is not under test in the harness; check it by hand, or
  run a suite with the variable set low.

- **`app.py` must be present at the app root.** It was missing from the v101 zip,
  which made every suite unrunnable. Check it survives the next zip.
- **Background processes may not survive between tool calls.** If you're driving
  this from an agent sandbox, start the server and run the suite in ONE shell
  invocation, or use `run_harness.sh`.
- `verify_amber.py` / `verify_dots.py` synthesize their over-quota WAV rather
  than reading an uploaded file (the original boom-bap loop is gone). A 30s
  stereo tone fills the same role: its base64 exceeds the ~4.5 MB localStorage
  ceiling, which is what drives the amber state.
- **Don't regenerate `requirements.txt` from the sandbox.** It has no
  `DATABASE_URL`, so it never touches Postgres and never needs `gunicorn` — but
  production needs both. `psycopg[binary]` in particular is required by the
  `postgresql+psycopg://` rewrite in `app.py`.
- **`verify_muxer.py` needs `static/skribl/mp4-muxer.min.js`**, which lives in the
  repo and is not shipped in handoff zips. The suite exits with a readable SKIP
  if it's missing.
- **jsdelivr is blocked here — and as of v104 nothing needs it.** Both libraries
  are vendored, so `verify_gifenc.py` can run the GIF encoder for real. If you add
  a new third-party script, expect it to fail here and vendor it instead; the
  "zero off-origin requests" assertion in `verify_gifenc.py` will catch it.
- **`verify_gifenc.py` needs `static/skribl/gifenc.min.js`** and SKIPs readably
  without it. Unlike the muxer this file ships in the v104 zip (the repo doesn't
  have it yet); from v105 it is repo-resident. It is a build artifact — rebuild it
  with the command in its own banner comment, don't hand-edit it.
- **Downloads are how the GIF suite reads its output.** It drives the real export
  UI and captures the download, so the browser context needs `accept_downloads`.
  The Pad's export sheet also needs its `.open` class forced before the button is
  hit-testable — `openExport()` is IIFE-scoped and can only be reached by click.
- **Headless Chromium here has `VideoEncoder` but not avc1**, so no MP4 can
  actually be encoded. `verify_muxer.py` tests the capability gate and the WebM
  fallback, not the encoder. A real MP4 needs a real Chrome.
- **PostgreSQL installs here — don't assume otherwise.** `verify_postgres.py`
  skips without a live server, and a skip contributes zero assertions. It is
  three commands: `apt-get update && apt-get install -y postgresql`, then
  `initdb`/`pg_ctl start` as the `postgres` user, then create a `skribl` role
  and database (the default DSN is
  `postgresql://skribl:skribl@127.0.0.1:5432/skribl`, overridable with
  `SKRIBL_PG_DSN`). You also need `pip install "psycopg[binary]" gunicorn`. The
  apt index in a fresh sandbox is usually stale, so `apt-get update` first or
  every fetch 404s.

- **No stylus exists in the sandbox.** `verify_pressure.py` asserts the width
  maths, the clamping and the byte-identity rule by calling `pointWidth()`
  against the real loaded modules, and it draws a mouse stroke through the true
  event path to prove no `p` key is recorded. What it cannot reach is the line
  that reads `Touch.force` or `PointerEvent.pressure` from hardware. That needs
  a real pen on a real device.

- **Drawing before adding music triggers `setLoopToDrawingLength()`**, so the loop
  will be the drawing's length, not 20s. That's intended; don't read it as a bug.

- **The quota race was never a flake — RETRACTED in v134.** v133 recorded the
  12-thread burst occasionally admitting 1 instead of 2 as "load-sensitive rather
  than broken". That was wrong, and an external review caught it. `reserve()` is
  insert -> commit -> count -> delete-if-over, so two racers can each commit
  before either counts, both see a total over quota, and both withdraw. **One
  winner is the algorithm working**, and load only changes how often you see it.
  Two suites — `verify_review.py` and `verify_postgres.py`, the latter also
  asserting "no UNDER-admission" — had been asserting a guarantee the code never
  made, and passing on luck. A test barrier would have hidden this rather than
  fixed it.

  **`verify_review.py` has THREE concurrency bursts, and v134 fixed only one.**
  A second reviewer caught that the base3 burst still asserted an exact split.
  Fixed in v135. If you touch this area, the bursts are at roughly lines 364
  (base3, SQLite threads), 725 (exhausted bucket, must admit zero) and 752
  (fresh bucket). Grep for `threading.Thread` — do not assume the one you found
  is the only one.
