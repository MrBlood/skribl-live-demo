"""DRAW BACK: answering a drawing by drawing with it (the owner's "All yes",
Nov 19, to the mock; DECISIONS.md, "Draw back, mocked"; FUTURE.md 4, idea 7).

The Pad opens with the original faint underneath (lib/drawback.js) and hands
back the new strokes alone. The SERVER joins the two (join below), from the
original as Skribl stores it (skribl.read_payload), never from what a browser
says the original was: the answer's drawing holds the original's strokes
first, then its own, so it plays as one performance with two hands, on every
player there is, and plays on when the original goes. A draw-back on a
draw-back (a jam) is the same join: its original already holds every hand
before it.

HOW IT PLAYS (choice 4, "hers first, quick"): the original as it plays (its
own pause rule), squeezed to about OVERTURE_MS when it is longer, then the
answer at its own pace. Its own pause rule and starting speed are the
answer's: it is the answer's post.

THE PAPER, NOT ITS PICTURE. Every Pad drawing carries a picture of the
canvas as its take began (baseSnapshot: app.js captureCurrentFrame), which
is its paper; the answer's is the paper the Pad opened on for it. The join
keeps the original's ground (its colour) and neither picture, so ink laid
down before a take began (rare: the Pad starts a take with the first
stroke) is not carried. A photo under a drawing is: see below.

WHAT CAN BE DRAWN BACK ON, FOR NOW: a drawing of one page, with no photo
under it, no music and no recolours. Those carry media or indexes into the
strokes that a join would have to carry over too; each comes with a step of
its own. drawable() says which, and the row offers Draw back only where it
can be done (posts.py, the pen)."""

#: How long the original plays before the answer, at most (choice 4's B).
OVERTURE_MS = 3000

#: The pause rules a replay knows (app.js PAUSE_CAPS), in milliseconds.
PAUSE_CAPS = {"keep": None, "trim": 250, "tight": 50}


def _frame0(payload):
    frames = payload.get("frames") if isinstance(payload, dict) else None
    if not isinstance(frames, list) or len(frames) != 1 or not isinstance(frames[0], dict):
        return None
    return frames[0]


def _truthy(v):
    """Whether a picture or a sound is there: its data (a dict's `data`, as
    the editors write a photo and a song), or a string; a dict of settings
    alone (a fit, an opacity) is none."""
    if isinstance(v, dict):
        return bool(v.get("data"))
    return bool(v)


def drawable(payload):
    """None when `payload` can be drawn back on (or be the strokes of an
    answer), else why not: "pages" (a Flip of more than one page, or no
    frames), "photo" (a picture under it), "music", "recolors"."""
    f0 = _frame0(payload)
    if f0 is None:
        return "pages"
    if payload.get("playbackMode") not in (None, "replay"):
        return "pages"
    for k in ("loop", "under", "beat"):
        if payload.get(k) is not None:
            return "pages"
    if _truthy(f0.get("photo")) or _truthy(payload.get("photo")):
        return "photo"
    if _truthy(f0.get("music")) or _truthy(payload.get("music")):
        return "music"
    if f0.get("recolors") or payload.get("recolors"):
        return "recolors"
    return None


def _points(f0):
    pts = f0.get("strokes")
    return [p for p in pts if isinstance(p, dict)] if isinstance(pts, list) else []


def _groups(f0, n):
    g = f0.get("strokeGroups")
    if isinstance(g, list) and g and all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in g) \
            and sum(g) == n:
        return list(g)
    return [n] if n else []


def _t(p):
    t = p.get("t")
    return t if isinstance(t, (int, float)) and not isinstance(t, bool) else 0


def played(points, pause_mode):
    """Each point's time as the replay plays it: the gaps between points, a
    gap past the pause rule's cap played as the cap (app.js
    buildPlaybackTimeline), a gap back in time (a new take) as none."""
    cap = PAUSE_CAPS.get(pause_mode, PAUSE_CAPS["tight"]) if pause_mode in PAUSE_CAPS else PAUSE_CAPS["tight"]
    out, at = [], 0
    for i, p in enumerate(points):
        if i:
            gap = _t(p) - _t(points[i - 1])
            if gap > 0:
                at += gap if cap is None else min(gap, cap)
        out.append(at)
    return out


def join(original, answer):
    """The draw-back's drawing: `original`'s strokes first, as it plays,
    squeezed to OVERTURE_MS at most, then `answer`'s at its own pace; the
    original's shape and ground, the answer's pause rule and speed. Both
    drawable(). Each point keeps everything it carries but its time."""
    of, af = _frame0(original), _frame0(answer)
    ops, aps = _points(of), _points(answer["frames"][0])
    otimes = played(ops, original.get("pauseMode"))
    total = otimes[-1] if otimes else 0
    k = min(1.0, OVERTURE_MS / total) if total > 0 else 1.0
    strokes = []
    for p, at in zip(ops, otimes):
        q = dict(p)
        q["t"] = int(round(at * k))
        strokes.append(q)
    # The answer at its own pace, one beat on from the original's last point,
    # its takes laid end to end (a gap back in time plays as none either way).
    base = (strokes[-1]["t"] if strokes else 0) + PAUSE_CAPS["tight"]
    at = base
    for i, p in enumerate(aps):
        if i:
            gap = _t(p) - _t(aps[i - 1])
            if gap > 0:
                at += gap
        q = dict(p)
        q["t"] = int(round(at))
        if i == 0:
            q["start"] = True
        strokes.append(q)
    if strokes:
        strokes[0]["start"] = True
    frame = {"strokes": strokes,
             "strokeGroups": _groups(of, len(ops)) + _groups(af, len(aps)),
             "background": of.get("background"), "photo": None, "music": None}
    out = {"version": answer.get("version", 2), "schemaVersion": answer.get("schemaVersion", 2),
           "playbackMode": "replay", "pauseMode": answer.get("pauseMode") or "tight", "fps": None,
           "frames": [frame], "canvasSize": original.get("canvasSize")}
    if answer.get("playSpeed") is not None:
        out["playSpeed"] = answer.get("playSpeed")
    for k2 in ("visibility", "caption"):
        if k2 in answer:
            out[k2] = answer[k2]
    return out


def same_shape(original, answer):
    """The answer was drawn on the original's canvas (the Pad opens on its
    shape), so its strokes sit where the original's do."""
    a, b = original.get("canvasSize") or {}, answer.get("canvasSize") or {}
    try:
        return (round(float(a.get("cssWidth"))) == round(float(b.get("cssWidth")))
                and round(float(a.get("cssHeight"))) == round(float(b.get("cssHeight"))))
    except (TypeError, ValueError):
        return False
