"""How a hand moves a pen -- the timing and pressure behind How it works' examples.

The first examples were drawn along mathematically even paths at an even pace,
and the owner saw it at once: "the drawings are not actually drawing like they
actually would". A hand does not move like that, and the ways it differs are
well measured, so this follows them:

* SPEED FOLLOWS CURVATURE (the two-thirds power law of human drawing): the pen
  slows into tight turns and runs on straight stretches, v = K * R^(1/3), with
  R the radius of curvature.
* EACH STROKE ACCELERATES AND SETTLES: a minimum-jerk envelope at both ends, so
  a line lands, travels and lifts rather than starting and stopping at speed.
* THE PACE WANDERS: a slow random swell of about +-12% within a stroke.
* THE HAND TREMBLES: a faint 8-11 Hz tremor and a slower drift, a fraction of
  a pixel, on top of the intended path.
* PRESSURE: light on a fast stroke, heavier on a slow one; it rises over the
  first tens of milliseconds and eases off before the lift. Delivered as a
  stylus's pressure, so the editor's own pressure curve (lib/pressure.js) turns
  it into a line that swells and tapers.
* BETWEEN STROKES: a pause that grows with how far the pen has to travel.

Points come out at 240 Hz, an Apple Pencil's rate, and DRIVER (below) delivers
them as pen PointerEvents inside the page on a precise clock, so the editor
timestamps each one as it would a real stylus. Nothing here edits a recording;
the editor records what this does.
"""
import math
import random

HZ = 240


def catmull(points, spacing=1.0):
    """A smooth path through hand-placed points, sampled about `spacing` apart."""
    if len(points) < 3:
        (x0, y0), (x1, y1) = points[0], points[-1]
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / spacing))
        return [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * i / (n - 1)) for i in range(n)]
    p = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(p) - 2):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p[i - 1], p[i], p[i + 1], p[i + 2]
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / spacing))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append((0.5 * (2 * x1 + (-x0 + x2) * t + (2 * x0 - 5 * x1 + 4 * x2 - x3) * t2 + (-x0 + 3 * x1 - 3 * x2 + x3) * t3),
                        0.5 * (2 * y1 + (-y0 + y2) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2 + (-y0 + 3 * y1 - 3 * y2 + y3) * t3)))
    out.append(points[-1])
    return out


def _radius(a, b, c):
    """Radius of the circle through three points (large on a straight run)."""
    ab = math.hypot(b[0] - a[0], b[1] - a[1]); bc = math.hypot(c[0] - b[0], c[1] - b[1])
    ca = math.hypot(a[0] - c[0], a[1] - c[1])
    area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    if area2 < 1e-9:
        return 5000.0
    return min(5000.0, ab * bc * ca / (2 * area2))


def stroke(path, *, pace=1.0, seed=0, pmin=0.30, pmax=0.95, tremor=0.45):
    """[(x, y, ms, pressure)] for one pen-down..pen-up along `path` (dense points).

    `pace` scales the whole hand: 1.0 is an unhurried sketch (~0.9 canvas px/ms
    on a straight run); faster for quick hatching, slower for careful lines."""
    rnd = random.Random(seed)
    n = len(path)
    if n < 2:
        return [(path[0][0], path[0][1], 0.0, pmax)]
    # Arc length, and a curvature-smoothed radius at each point (over ~6 px).
    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]))
    L = s[-1] or 1.0
    w = 6
    R = [_radius(path[max(0, i - w)], path[i], path[min(n - 1, i + w)]) for i in range(n)]
    K = 0.9 * pace / (60.0 ** (1 / 3))           # 60 px radius ~ a gentle curve at base pace
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    v = []
    for i in range(n):
        u = s[i] / L
        base = K * max(R[i], 2.0) ** (1 / 3)
        base = min(base, 2.4 * pace)             # a straight run tops out
        # Minimum-jerk ends: settle over the first 14% and the last 12% of the line.
        a = min(1.0, u / 0.14); e = min(1.0, (1 - u) / 0.12)
        env = (10 * a ** 3 - 15 * a ** 4 + 6 * a ** 5) * (10 * e ** 3 - 15 * e ** 4 + 6 * e ** 5)
        swell = 1 + 0.12 * math.sin(6.28 * 1.3 * u * L / 300 + ph[0])
        v.append(max(0.06 * pace, base * (0.18 + 0.82 * env) * swell))
    # Time along the path, then resampled at the stylus rate.
    t = [0.0]
    for i in range(1, n):
        t.append(t[-1] + (s[i] - s[i - 1]) / ((v[i] + v[i - 1]) / 2))
    T = t[-1]
    out, j = [], 0
    vmax = max(v); vmin = min(v)
    steps = max(2, int(T * HZ / 1000) + 1)
    for k in range(steps):
        tk = min(T, k * 1000 / HZ)
        while j < n - 2 and t[j + 1] < tk:
            j += 1
        f = 0 if t[j + 1] == t[j] else (tk - t[j]) / (t[j + 1] - t[j])
        x = path[j][0] + (path[j + 1][0] - path[j][0]) * f
        y = path[j][1] + (path[j + 1][1] - path[j][1]) * f
        sec = tk / 1000
        x += tremor * (0.6 * math.sin(6.28 * 9.3 * sec + ph[1]) + 0.4 * math.sin(6.28 * 1.4 * sec + ph[2]))
        y += tremor * (0.6 * math.sin(6.28 * 10.1 * sec + ph[3]) + 0.4 * math.sin(6.28 * 1.7 * sec + ph[0]))
        vk = v[j] + (v[j + 1] - v[j]) * f
        speed = 0 if vmax == vmin else (vk - vmin) / (vmax - vmin)
        p = pmax - (pmax - pmin) * speed ** 0.8
        p *= min(1.0, 0.25 + tk / 45.0)          # pressure rises as the nib lands
        p *= min(1.0, 0.3 + (T - tk) / 70.0)     # and eases before the lift
        out.append((x, y, tk, max(0.05, min(1.0, p))))
    return out


def pause(prev_end, next_start, seed=0):
    """Milliseconds between one stroke's lift and the next one's touch."""
    rnd = random.Random(seed)
    d = math.hypot(next_start[0] - prev_end[0], next_start[1] - prev_end[1])
    return 110 + d * 0.55 + rnd.uniform(0, 140)


# Delivers [{k: 'd'|'m'|'u', x, y, t, p}] (client px, ms from now, pressure) as
# pen PointerEvents on the canvas, each when its moment comes. Runs in the
# page, so the editor's clock sees the hand's timing and not the automation's.
DRIVER = """(events) => new Promise(done => {
  const c = document.getElementById('canvas') || document.querySelector('canvas.flip-canvas, #pad');
  const t0 = performance.now(); let i = 0;
  const fire = (ev) => {
    // A stroke can carry its own ink: colour and width are set as the pen
    // lands, through the editor's hook (window.__demoSet), so a whole traced
    // picture draws in one pass with the hand's own pauses between strokes.
    if (ev.k === 'd' && (ev.c || ev.s) && window.__demoSet) window.__demoSet(ev);
    const type = ev.k === 'd' ? 'pointerdown' : ev.k === 'u' ? 'pointerup' : 'pointermove';
    c.dispatchEvent(new PointerEvent(type, { bubbles: true, cancelable: true, composed: true,
      pointerId: 7, pointerType: 'pen', isPrimary: true, clientX: ev.x, clientY: ev.y,
      pressure: ev.k === 'u' ? 0 : ev.p, buttons: ev.k === 'u' ? 0 : 1, button: ev.k === 'm' ? -1 : 0,
      width: 1, height: 1 }));
  };
  const tick = () => {
    const now = performance.now() - t0;
    while (i < events.length && events[i].t <= now) fire(events[i++]);
    if (i < events.length) setTimeout(tick, 1); else done(events.length);
  };
  tick();
})"""
