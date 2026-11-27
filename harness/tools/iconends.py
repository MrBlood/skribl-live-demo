#!/usr/bin/env python3
"""THE ENDS OF AN ICON'S LINES: where one stroke ends on another, it ends ON it.

THE REPORT (the owner, Nov 27, a screenshot of Make's pencil with a circle
drawn round "a little nub that needs fixing"). The pencil's band, the line
across it below the cap, ran 0.21 units past the pencil's left edge. A line
with round ends is a pen dragged along it (a disk of half its width swept
along the path), so where it ends ON another line its round end hides inside
that line only when the end point sits on the other line's centre. Past it by
d, the end pokes out of the other line by d: a nub, which a phone at 3x shows
as a bump on an edge that should be straight.

WHAT THIS READS: every icon drawing in the tree, in its own units, from the
source, so it needs no browser and no server:
  - the site's icons, each macro in social/templates/social/_icons.html
    rendered (and its filled or lit variant), as the pages draw them;
  - every inline <svg> in the templates (the site's and Skribl's) and every
    one written whole in a script, and a script's bare <path> strings (Flip's
    page menu keeps its icons as those);
  - a script's drawing written as string pieces joined with + is read whole;
    one assembled from template or script variables is skipped, and read
    where its pieces are written whole.

WHAT IT CALLS A NUB, AND WHAT IT DOES NOT. An end P of an open stroke whose
nearest other stroke S lies within half P's width of it, which P's stroke
CROSSES just before it ends (walking back from P over about one width), so P
overshoots S's centre line by d < half its width: P's round end then pokes out
of S by d + (P's half width) - (S's half width). Past half its width the end is
an overhang drawn on purpose (a bin's lid wider than the bin, a bell's stem
above the bell) and is not reported. Nor is an end that stops short of S: that
is a gap, and most gaps here are drawn on purpose (a page's lines inside its
edge, the pen's circle that does not quite close).

    python3 harness/tools/iconends.py          # every nub, largest first
"""
import glob
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")

# What a nub must poke out by to be reported, in the icon's own units (24 to
# its box). Every icon here is drawn at 13 to 36 CSS px, so 0.06 units is under
# a tenth of a CSS pixel even at the largest: below it is a rounding of the
# coordinates, not a drawing. The pencil's was 0.21.
NUB_MIN = 0.06


# ---- path data to polylines ---------------------------------------------------
class _Reader:
    def __init__(self, d):
        self.s, self.i = d, 0

    def _skip(self):
        while self.i < len(self.s) and self.s[self.i] in " ,\t\r\n":
            self.i += 1

    def done(self):
        self._skip()
        return self.i >= len(self.s)

    def peek_cmd(self):
        self._skip()
        if self.i < len(self.s) and self.s[self.i].isalpha():
            return self.s[self.i]
        return None

    def cmd(self):
        self._skip()
        c = self.s[self.i]
        self.i += 1
        return c

    def num(self):
        self._skip()
        m = NUM.match(self.s, self.i)
        if not m:
            raise ValueError(f"a number was expected at {self.i}: {self.s[self.i:self.i + 12]!r}")
        self.i = m.end()
        return float(m.group(0))

    def flag(self):
        # An arc's two flags may be written with nothing between them ("0 01").
        self._skip()
        c = self.s[self.i]
        if c not in "01":
            raise ValueError("an arc flag was expected")
        self.i += 1
        return c == "1"


def _cubic(p0, p1, p2, p3, n=20):
    out = []
    for k in range(1, n + 1):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _quad(p0, p1, p2, n=14):
    out = []
    for k in range(1, n + 1):
        t = k / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


def _arc(p0, rx, ry, phi, large, sweep, p1):
    """An SVG arc as points, by the endpoint-to-centre conversion (SVG 1.1, F.6.5)."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    cphi, sphi = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cphi * dx + sphi * dy, -sphi * dx + cphi * dy
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cx1, cy1 = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cphi * cx1 - sphi * cy1 + (p0[0] + p1[0]) / 2
    cy = sphi * cx1 + cphi * cy1 + (p0[1] + p1[1]) / 2

    def ang(u, v):
        return math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])
    t1 = ang((1, 0), ((x1 - cx1) / rx, (y1 - cy1) / ry))
    dt = ang(((x1 - cx1) / rx, (y1 - cy1) / ry), ((-x1 - cx1) / rx, (-y1 - cy1) / ry))
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(4, int(abs(dt) / math.radians(8)))
    out = []
    for k in range(1, n + 1):
        t = t1 + dt * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cphi * x - sphi * y + cx, sphi * x + cphi * y + cy))
    out[-1] = p1
    return out


def path_polylines(d):
    """[(points, closed)], one per subpath of the path data `d`."""
    r = _Reader(d)
    subs, pts, closed = [], [], False
    cur = start = (0.0, 0.0)
    last_c = last_q = None
    cmd = None

    def flush():
        nonlocal pts, closed
        if len(pts) > 1:
            subs.append((pts, closed))
        pts, closed = [], False

    while not r.done():
        if r.peek_cmd():
            cmd = r.cmd()
        elif cmd is None:
            break
        rel, C = cmd.islower(), cmd.upper()
        if C == "Z":
            if pts and pts[-1] != start:
                pts.append(start)
            closed = True
            flush()
            cur = start
            pts = [cur]
            last_c = last_q = None
            continue
        if C == "M":
            x, y = r.num(), r.num()
            if rel:
                x, y = cur[0] + x, cur[1] + y
            flush()
            cur = start = (x, y)
            pts = [cur]
            cmd = "l" if rel else "L"
            last_c = last_q = None
            continue
        if C == "L":
            x, y = r.num(), r.num()
            cur = (cur[0] + x, cur[1] + y) if rel else (x, y)
            pts.append(cur)
            last_c = last_q = None
        elif C == "H":
            x = r.num()
            cur = (cur[0] + x if rel else x, cur[1])
            pts.append(cur)
            last_c = last_q = None
        elif C == "V":
            y = r.num()
            cur = (cur[0], cur[1] + y if rel else y)
            pts.append(cur)
            last_c = last_q = None
        elif C in "CS":
            k = 6 if C == "C" else 4
            a = [r.num() for _ in range(k)]
            if rel:
                a = [a[j] + (cur[0] if j % 2 == 0 else cur[1]) for j in range(k)]
            if C == "C":
                p1, p2, p3 = (a[0], a[1]), (a[2], a[3]), (a[4], a[5])
            else:
                p1 = (2 * cur[0] - last_c[0], 2 * cur[1] - last_c[1]) if last_c else cur
                p2, p3 = (a[0], a[1]), (a[2], a[3])
            pts.extend(_cubic(cur, p1, p2, p3))
            last_c, last_q, cur = p2, None, p3
        elif C in "QT":
            k = 4 if C == "Q" else 2
            a = [r.num() for _ in range(k)]
            if rel:
                a = [a[j] + (cur[0] if j % 2 == 0 else cur[1]) for j in range(k)]
            if C == "Q":
                p1, p2 = (a[0], a[1]), (a[2], a[3])
            else:
                p1 = (2 * cur[0] - last_q[0], 2 * cur[1] - last_q[1]) if last_q else cur
                p2 = (a[0], a[1])
            pts.extend(_quad(cur, p1, p2))
            last_q, last_c, cur = p1, None, p2
        elif C == "A":
            rx, ry, phi = r.num(), r.num(), r.num()
            large, sweep = r.flag(), r.flag()
            x, y = r.num(), r.num()
            if rel:
                x, y = cur[0] + x, cur[1] + y
            pts.extend(_arc(cur, rx, ry, phi, large, sweep, (x, y)))
            cur = (x, y)
            last_c = last_q = None
        else:
            raise ValueError(f"unknown path command {cmd!r}")
    flush()
    return subs


def shape_polylines(tag, g):
    """[(points, closed)] for one element, from its attributes `g`."""
    def f(k, dv=0.0):
        try:
            return float(g.get(k, dv) or dv)
        except ValueError:
            return dv
    if tag == "path":
        return path_polylines(g.get("d", ""))
    if tag == "line":
        return [([(f("x1"), f("y1")), (f("x2"), f("y2"))], False)]
    if tag in ("polyline", "polygon"):
        nums = [float(n) for n in NUM.findall(g.get("points", ""))]
        pts = list(zip(nums[0::2], nums[1::2]))
        if tag == "polygon" and pts:
            pts.append(pts[0])
        return [(pts, tag == "polygon")]
    if tag in ("circle", "ellipse"):
        cx, cy = f("cx"), f("cy")
        rx = f("r") if tag == "circle" else f("rx")
        ry = f("r") if tag == "circle" else f("ry")
        return [([(cx + rx * math.cos(2 * math.pi * k / 72), cy + ry * math.sin(2 * math.pi * k / 72))
                  for k in range(73)], True)]
    if tag == "rect":
        x, y, w, h = f("x"), f("y"), f("width"), f("height")
        rx = min(f("rx", f("ry")), w / 2, h / 2)
        if rx <= 0:
            return [([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], True)]
        return path_polylines(
            f"M{x + rx},{y} H{x + w - rx} A{rx},{rx} 0 0 1 {x + w},{y + rx} V{y + h - rx} A{rx},{rx} 0 0 1 "
            f"{x + w - rx},{y + h} H{x + rx} A{rx},{rx} 0 0 1 {x},{y + h - rx} V{y + rx} A{rx},{rx} 0 0 1 {x + rx},{y} Z")
    return []


# ---- the ends -------------------------------------------------------------------
def _closest(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    q = (a[0] + t * dx, a[1] + t * dy)
    return q, math.hypot(p[0] - q[0], p[1] - q[1])


def _arclen(pts):
    out = [0.0]
    for i in range(1, len(pts)):
        out.append(out[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return out


def _out(pts, at_start, reach=0.35):
    """The direction a stroke's end points: out of the stroke, away from it."""
    seq = pts if at_start else pts[::-1]
    p = seq[0]
    for q in seq[1:] + [seq[-1]]:
        n = math.hypot(p[0] - q[0], p[1] - q[1])
        if n >= reach or q is seq[-1]:
            n = n or 1.0
            return ((p[0] - q[0]) / n, (p[1] - q[1]) / n)
    return (0.0, 0.0)


def _side(p, a, b):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _crosses(pts, at_start, A, B, reach):
    """Does the stroke, walked back from its end over `reach`, cross segment AB?"""
    seq = pts if at_start else pts[::-1]
    walked, s0 = 0.0, _side(seq[0], A, B)
    for i in range(1, len(seq)):
        walked += math.hypot(seq[i][0] - seq[i - 1][0], seq[i][1] - seq[i - 1][1])
        s1 = _side(seq[i], A, B)
        if s0 == 0 or s1 == 0 or (s0 > 0) != (s1 > 0):
            p, q = seq[i - 1], seq[i]
            r = (q[0] - p[0], q[1] - p[1])
            sv = (B[0] - A[0], B[1] - A[1])
            den = r[0] * sv[1] - r[1] * sv[0]
            if den == 0:
                return True
            u = ((A[0] - p[0]) * r[1] - (A[1] - p[1]) * r[0]) / den     # along AB: 0 to 1 is on it
            slack = 0.6 / (math.hypot(*sv) or 1.0)
            if -slack <= u <= 1 + slack:
                return True
        if walked > reach:
            break
        s0 = s1
    return False


def nubs(strokes):
    """strokes: [(points, closed, width, cap)], one user space. Each end that
    pokes out of the line it ends on, as {at, by}: `by` in the same units."""
    found, segs = [], []
    # One line drawn twice is one line: the heart is three copies of its one
    # stroke (its fill, its line and the ink that draws round when you like
    # it), and each copy's end would hide inside the next.
    seen, uniq = set(), []
    for st in strokes:
        key = (tuple((round(x, 3), round(y, 3)) for x, y in st[0]), st[2])
        if key not in seen:
            seen.add(key)
            uniq.append(st)
    strokes = uniq
    for si, (pts, closed, w, cap) in enumerate(strokes):
        L = _arclen(pts)
        for k in range(1, len(pts)):
            segs.append((si, pts[k - 1], pts[k], w, L[k - 1], L[k]))
    for si, (pts, closed, w, cap) in enumerate(strokes):
        if closed or len(pts) < 2 or cap not in ("round", "square"):
            continue
        total = _arclen(pts)[-1]
        h = w / 2
        for at_start in (True, False):
            P = pts[0] if at_start else pts[-1]
            s_at = 0.0 if at_start else total
            best = None
            for (sj, A, B, wS, la, lb) in segs:
                # its own stroke only where it comes back round (a loop)
                if sj == si and min(abs(la - s_at), abs(lb - s_at)) < 2.5 * w:
                    continue
                q, d = _closest(P, A, B)
                if d < h and (best is None or d < best[1]):
                    best = (q, d, wS / 2, A, B)
            if best is None or best[1] < 1e-9:
                continue
            q, d, hS, A, B = best
            t = _out(pts, at_start)
            u = ((P[0] - q[0]) / d, (P[1] - q[1]) / d)
            if u[0] * t[0] + u[1] * t[1] > 0.2 and _crosses(pts, at_start, A, B, d + 2 * h):
                by = d + h - hS
                if by > 1e-9:
                    found.append({"at": (round(P[0], 3), round(P[1], 3)), "by": round(by, 3)})
    return found


# ---- every drawing in the tree ------------------------------------------------------
_SVG = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.S)
_EL = re.compile(r"<(path|circle|ellipse|line|polyline|polygon|rect)\b([^>]*?)/?>", re.S)
_ATTR = re.compile(r"([a-zA-Z:-]+)\s*=\s*(\"[^\"]*\"|'[^']*')")
_BARE = re.compile(r"'((?:<(?:path|circle|rect|line|polyline|polygon|ellipse)\b[^'<>]*/>)+)'")


def _attrs(s):
    return {k: v[1:-1] for k, v in _ATTR.findall(s)}


def _strokes(svg_attrs, body, default_sw=None, default_cap=None):
    out = []
    for em in _EL.finditer(body):
        tag, ea = em.group(1), _attrs(em.group(2))
        stroke = ea.get("stroke", svg_attrs.get("stroke", "currentColor" if default_sw else "none"))
        if stroke in ("none", ""):
            continue
        if "transform" in ea:
            continue
        try:
            sw = float(ea.get("stroke-width", svg_attrs.get("stroke-width", default_sw or "1")))
        except ValueError:
            continue
        cap = ea.get("stroke-linecap", svg_attrs.get("stroke-linecap", default_cap or "butt"))
        for pts, closed in shape_polylines(tag, ea):
            if pts:
                out.append((pts, closed, sw, cap))
    return out


def _templated(s):
    return any(t in s for t in ("{{", "{%", "${", "' +", '" +', "+ '", '+ "'))


def site_drawings():
    """The site's icons, each macro rendered as its pages draw it."""
    import jinja2
    path = os.path.join(ROOT, "social/templates/social/_icons.html")
    src = open(path, encoding="utf-8").read()
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "social/templates")))
    mod = env.get_template("social/_icons.html").module
    for name, args in re.findall(r"{%\s*macro\s+([a-z_]+)\s*\(([^)]*)\)", src):
        if name.startswith("_"):
            continue
        variants = [({}, name)]
        if "filled" in args:
            variants.append(({"filled": True}, name + "(filled)"))
        if "lit" in args:
            variants.append(({"lit": True}, name + "(lit)"))
        for kw, label in variants:
            html = str(getattr(mod, name)(**kw))
            for m in _SVG.finditer(html):
                yield "social/templates/social/_icons.html " + label, _strokes(_attrs(m.group(1)), m.group(2))


def source_drawings():
    """Every inline <svg> written whole in a template or a script, and a
    script's bare <path> strings (drawn in the dock's stroke, 2 and round)."""
    pats = ("social/templates/social/*.html", "skribl/templates/skribl/*.html",
            "skribl/static/*.js", "skribl/static/lib/*.js", "social/static/*.js")
    for pat in pats:
        for f in sorted(glob.glob(os.path.join(ROOT, pat))):
            rel = os.path.relpath(f, ROOT)
            if rel.endswith("social/_icons.html"):
                continue                       # read through its macros, above
            src = open(f, encoding="utf-8").read()
            if f.endswith(".js"):
                # a drawing written as string pieces joined with + is read whole
                src = re.sub(r"'\s*\+\s*'", "", re.sub(r'"\s*\+\s*"', "", src))
                src = src.replace("\\'", "'").replace('\\"', '"')
            for m in _SVG.finditer(src):
                body = m.group(2)
                if _templated(body) or _templated(m.group(1)):
                    continue
                line = src[:m.start()].count("\n") + 1
                yield f"{rel}:{line}", _strokes(_attrs(m.group(1)), body)
            if f.endswith(".js"):
                for m in _BARE.finditer(src):
                    line = src[:m.start()].count("\n") + 1
                    yield f"{rel}:{line}", _strokes({}, m.group(1), default_sw="2", default_cap="round")


def report(min_by=NUB_MIN):
    """[(where, at, by)] for every nub in the tree of at least `min_by` units."""
    out = []
    for where, strokes in list(site_drawings()) + list(source_drawings()):
        if not strokes:
            continue
        for n in nubs(strokes):
            if n["by"] >= min_by:
                out.append((where, n["at"], n["by"]))
    return sorted(out, key=lambda x: -x[2])


if __name__ == "__main__":
    got = report(0.0)
    for where, at, by in got:
        print(f"{by:6.3f}  {where}  at {at}")
    print(f"{len(got)} end(s) poke out; {sum(1 for g in got if g[2] >= NUB_MIN)} at {NUB_MIN} units or more")
