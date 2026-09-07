#!/usr/bin/env python3
"""Build minimal .skribl documents for tests, in memory.

WHY THIS EXISTS. The format's load -> render -> play path was pinned by two
files the OWNER had asked for as DEMOS — drawings to look at — which a later
session quietly promoted into regression fixtures. That is backwards twice
over: it made 2.7 MB of somebody's artwork load-bearing, and it meant the
tested properties (24 pages at 12fps; enough ink to prove rendering; a replay
that advances) were whatever those particular drawings happened to have.

A fixture should be built for the property it proves. These are, and they are
built at test time, so no drawing is stored in the repo at all.

THE SCHEMA, read out of flip.js rather than guessed:
  * `strokes` is a FLAT point array of {x, y, color, size, t, start, erase}
  * `strokeGroups` counts the points in each stroke, and the server validates
    the partition: sum(strokeGroups) == len(strokes), one group per start flag
Both invariants are asserted here, so a malformed document fails at build.
"""
import json

CANVAS = {"cssWidth": 816, "cssHeight": 612, "dpr": 1}
INK = "#e8ecf5"


def _stroke(pts, color=INK, size=6, t0=0.0, dt=8.0):
    out = []
    for i, (x, y) in enumerate(pts):
        out.append({"x": round(x, 1), "y": round(y, 1), "color": color,
                    "size": size, "t": round(t0 + i * dt, 1),
                    "start": i == 0, "erase": False})
    return out


def _frame(strokes):
    flat, groups = [], []
    for s in strokes:
        flat.extend(s); groups.append(len(s))
    assert sum(groups) == len(flat)
    assert len(groups) == sum(1 for p in flat if p["start"])
    return {"strokes": flat, "strokeGroups": groups, "background": None}


def flipbook(pages=24, fps=12, bars=14):
    """A `pages`-page flipbook with a bar that marches across, at `fps`.

    Proves: the document loads as N pages at the declared fps, renders ink,
    and the page index advances on Play. Thick short strokes give plenty of
    covered pixels without many points.
    """
    frames = []
    for p in range(pages):
        strokes = []
        for b in range(bars):
            x = 40 + b * 52
            y0 = 90 + ((p + b) % 6) * 60
            strokes.append(_stroke([(x, y0), (x, y0 + 150)], size=14))
        frames.append(_frame(strokes))
    doc = {"version": 1, "schemaVersion": 1, "playbackMode": "flip",
           "fps": fps, "canvasSize": CANVAS, "frames": frames, "editIdx": 0}
    assert len(doc["frames"]) == pages and doc["fps"] == fps
    return json.dumps(doc, separators=(",", ":")).encode()


def replay(points=900, per_stroke=6):
    """A single-frame timed replay with more than `points` points.

    Proves: a replay document loads in Pad, renders ink, and GROWS over time
    on Play — so the points carry an increasing `t` and are spread over the
    canvas rather than stacked.
    """
    strokes, t = [], 0.0
    n = 0
    while n < points:
        i = len(strokes)
        cx = 60 + (i * 37) % 700
        cy = 70 + (i * 53) % 460
        pts = [(cx + k * 7, cy + (k % 3) * 6) for k in range(per_stroke)]
        strokes.append(_stroke(pts, size=7, t0=t, dt=6.0))
        t += per_stroke * 6.0 + 40.0
        n += per_stroke
    doc = {"version": 1, "schemaVersion": 1, "playbackMode": "replay",
           "fps": 24, "canvasSize": CANVAS, "frames": [_frame(strokes)],
           "editIdx": 0}
    assert len(doc["frames"][0]["strokes"]) > points - per_stroke
    return json.dumps(doc, separators=(",", ":")).encode()


if __name__ == "__main__":
    fb, rp = flipbook(), replay()
    print(f"  flipbook: {len(fb):,} B   replay: {len(rp):,} B")
