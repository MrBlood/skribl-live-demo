"""Flip: does every point captured end up inside a stroke group?

`strokes` is a FLAT point array and `strokeGroups` holds one positive count per
stroke, and the server requires them to agree exactly — `_validate_stroke_groups`
refuses a payload where they do not, which surfaces to the user as a red box on
the share sheet and a Skribl that cannot be posted at all:

    'frames[9].strokeGroups' accounts for 317 points, but the strokes array
    contains 318.

That was reported from the live demo. The cause is not the arithmetic, which is
balanced: Flip pushes a point and increments `curCount` at every step, and
`endStroke` pushes `curCount` once. The cause is that a stroke had no OWNER.
`pointerdown` had no guard against firing while a stroke was already in
progress, so a second finger — or a palm landing beside a pen — reset
`curCount` to 1 while its own point went into the same `strokes` array. Every
point captured before that moment lost its group entry.

An off-by-one is the SMALL version of this bug and the one most likely to be
reported, because it means the second touch landed before the first had moved.
Land it twenty points in and twenty points go missing from the accounting.

WHY THE PAD IS NOT TESTED HERE. It cannot reach this shape. `startDraw`
accumulates into a separate `currentStroke`, and `endDraw`/`commitActiveStroke`
concatenate it into `strokes` in the same step as pushing its count, so the two
arrays cannot disagree — a re-entrant start discards points but never orphans
them. Flip pushes into the shared array and counts alongside it. This is a real
difference in the two implementations rather than one surface missing the
other's fix, and it is why the guard belongs only here.

THE LAST CASE IS THE ONE THAT PROBABLY BIT THE REPORTER. Pinch-to-zoom mid
stroke: `abortStrokeForPinch` splices exactly `curCount` points back off, so
with `curCount` already reset by the second finger it removed one point and
orphaned the rest. Zooming while drawing is an ordinary thing to do on a phone.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORT = 5015
BASE = f"http://127.0.0.1:{PORT}"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# Every scenario draws the SAME 21-point stroke and differs only in what
# interrupts it, so any difference in the totals is the interruption.
DRAW = """(mode) => {
  const el = document.getElementById('pad');
  const r = el.getBoundingClientRect();
  const at = (x, y) => ({clientX: r.left + x, clientY: r.top + y});
  const ev = (t, id, x, y, type) => el.dispatchEvent(new PointerEvent(t, {
    pointerId: id, isPrimary: true, bubbles: true, cancelable: true,
    pointerType: type || 'touch', ...at(x, y)}));
  const touch = (x, y, id) => new Touch({identifier: id, target: el, ...at(x, y)});

  const penMode = mode === 'palm';
  ev('pointerdown', 1, 100, 100, penMode ? 'pen' : 'touch');
  for (let i = 0; i < 20; i++) {
    ev('pointermove', 1, 100 + i * 4, 100 + i * 2, penMode ? 'pen' : 'touch');
  }

  if (mode === 'second')    ev('pointerdown', 2, 300, 300);
  if (mode === 'immediate') ev('pointerdown', 2, 101, 101);
  if (mode === 'palm')      ev('pointerdown', 2, 300, 300, 'touch');
  if (mode === 'pinch') {
    ev('pointerdown', 2, 300, 300);
    el.dispatchEvent(new TouchEvent('touchstart', {bubbles: true, cancelable: true,
      touches: [touch(100, 100, 1), touch(300, 300, 2)],
      targetTouches: [touch(100, 100, 1), touch(300, 300, 2)],
      changedTouches: [touch(300, 300, 2)]}));
  }

  window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 1, bubbles: true}));

  const f = frames[idx];
  const sum = f.strokeGroups.reduce((a, b) => a + b, 0);
  return {points: f.strokes.length, groups: sum, entries: f.strokeGroups.slice(),
          // Serialised the way share does, so the payload can be posted as-is.
          frames: frames.map(fr => ({strokes: fr.strokes, strokeGroups: fr.strokeGroups,
                                     baseSnapshot: null, background: {color: '#101418'}}))};
}"""


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls", method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


env = dict(os.environ, DATABASE_URL=f"sqlite:///{__import__('tempfile').mkdtemp()}/sg.db",
           SKRIBL_RATE_MAX_POSTS="100000", SKRIBL_RATE_MAX_ATTEMPTS="100000",
           SECRET_KEY="harness-strokegroups")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=env, check=True, capture_output=True)
proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                         "--port", str(PORT), "--no-reload"],
                        cwd=ROOT, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.time() + 25
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    proc.kill()
    sys.exit("SKIP: instance did not start.")

SCENARIOS = [
    ("clean",     "an uninterrupted stroke"),
    ("second",    "a second finger lands mid-stroke"),
    ("immediate", "a second finger lands before the first has moved"),
    ("palm",      "a palm lands beside a pen (both are isPrimary)"),
    ("pinch",     "a pinch begins mid-stroke"),
]

try:
    with sync_playwright() as sp:
        b = sp.chromium.launch()
        print("\nSTROKE GROUPS — every captured point belongs to a group")
        baseline = None
        for mode, label in SCENARIOS:
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + "/flip", wait_until="load")
            pg.wait_for_timeout(1200)
            out = pg.evaluate(DRAW, mode)
            pg.close()

            if mode == "clean":
                baseline = out
                # GATE. Everything below compares against this. A fixture that
                # captures nothing would make every scenario agree at zero, which
                # reads as a pass and proves nothing.
                check("FIXTURE GATE: the control stroke captured points at all",
                      out["points"] >= 20,
                      f"{out['points']} points — a silent fixture makes every "
                      "scenario agree trivially")
                if out["points"] < 20:
                    break

            check(f"{label}: groups account for every point",
                  out["points"] == out["groups"],
                  f"{out['points']} points vs {out['groups']} accounted "
                  f"{out['entries']}")
            check(f"{label}: no uncaught error", not errs, "; ".join(errs)[:160])

            # The user-visible failure is not the mismatch, it is the refusal to
            # share. Post the payload the editor would have sent.
            st, body = post({"title": f"sg {mode}", "schemaVersion": 2,
                             "frames": out["frames"]})
            check(f"{label}: the server accepts the share", st == 201,
                  f"{st} {body.get('error', '')}")
        b.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

bad = [n for ok, n in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {', '.join(bad)}" if bad else ""))
sys.exit(1 if bad else 0)
