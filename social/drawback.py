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

THE AUTHOR'S BACKGROUND AND MUSIC (the owner's yes, Nov 19): a draw-back
keeps her paper, her photo and her song, and the answer adds none of its own
(drawable's `answer`); the Pad keeps its own picture and music drawer aside
while drawing back (lib/drawback.js). Her photo and song come as data, read
back from Skribl's store (skribl.read_payload inline_media), and the store
keeps content once, so the draw-back costs no more room for them.

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

WHAT CAN BE DRAWN BACK ON, FOR NOW: a drawing of one page with no
recolours (recolours index the strokes by number and time, which a join would
have to carry over too: a step of its own). drawable() says which, and the
row offers Draw back only where it can be done (posts.py, the pen).

AND A FLIP, PAGE FOR PAGE (the owner's "all yes", Nov 25, to the Flip Draw
Back mock: five answers, A each). One of his pages for each of hers, in her
order and at her timing (answer 1); it plays together, each page hers and his
at once, at her speed, as one animation (answer 2): join() lays his strokes
on her page, page by page, and keeps her pages' holds, her pages per second
and her shape, paper, picture and song. Kept as the Pad's (answer 3): joined
while the owner's switch is off, two hands once it is on (own() and view()
learn pages too). A PAGE THAT DRAWS ITSELF plays hers, then his (the owner,
Nov 25: "draw-on pages play hers then his"): her strokes as she drew them,
then his a beat after her last point, at his own pace, so the page lasts as
long as the two together. NOT IN THE FIRST STEP (said in the mock): a Flip
with a loop, a page kept underneath or beat timing; drawable() names each
("loop", "under", "beat"), so its row offers no pen."""

#: How long the original plays before the answer, at most (choice 4's B).
OVERTURE_MS = 3000

# ---- TWO HANDS (the owner's "all yes", Nov 25, to the Two Hands mock: its
# nine answers, A each, and its first step; docs/SOCIAL-SITE.md section 41) ----
# A draw-back kept as two people's own work. His post's drawing holds HIS
# strokes alone, on her paper; the post points to her drawing as it was
# (Post.drawn_on_skribl_id); and the site lays hers under his as it plays
# (join, the same as today's, at the moment of watching), so it looks as a
# draw-back always has. Her work stays hers to take back: once her drawing is
# removed (deleted, or taken down), his post shows his strokes alone and says
# so; to somebody her post is not shown (a block, either way), the same, and
# it says that. Three views on his post's own page: Both (hers, then his, as
# today), hers alone and his alone, each at its own pace (views below).
#
# THE OWNER'S SWITCH. Made so only while SKRIBL_SOCIAL_TWO_HANDS is on in the
# site's settings, which only whoever runs the site can set (the live site's
# own settings, on its host); off, every draw-back is joined as before. What
# was made while it was on stays two hands whichever way it is set: the
# switch says how a NEW draw-back is kept, never how one is read.
#
# THE FIRST STEP: one original and one answer (the seventh answer). A
# two-hands draw-back is not drawn back on yet (drawable's "hands"); drawing
# back on a joined one from before makes a two-hands one whose original is
# that joined drawing. Draw-backs from before stay exactly as they are (the
# eighth).

#: What the switch reads as on.
_ON = ("1", "true", "yes", "on")


def two_hands():
    """Whether a new draw-back is kept as two hands: the owner's switch,
    SKRIBL_SOCIAL_TWO_HANDS in the app's config or its environment."""
    import os
    from flask import current_app
    v = current_app.config.get("SKRIBL_SOCIAL_TWO_HANDS")
    if v is None:
        v = os.environ.get("SKRIBL_SOCIAL_TWO_HANDS", "")
    return str(v).strip().lower() in _ON


def own(original, answer):
    """What a two-hands draw-back's drawing keeps: `answer`'s strokes alone,
    as it was drawn, on `original`'s paper (its ground and its shape, where
    he drew them), with no picture and no music (hers stay hers: drawable's
    `answer` refused his own). Both drawable(). Its resting picture is the
    caller's (posts._drawing_back: his lines alone). A Flip's: his pages
    alone, each on her page's paper, at her timing (_own_pages)."""
    if flip_pages(original) is not None:
        return _own_pages(original, answer)
    of, af = _frame0(original), _frame0(answer)
    frame = {"strokes": [dict(p) for p in _points(af)], "strokeGroups": _groups(af, len(_points(af))),
             "background": of.get("background")}
    out = {"version": answer.get("version", 2), "schemaVersion": answer.get("schemaVersion", 2),
           "playbackMode": "replay", "pauseMode": answer.get("pauseMode") or "tight", "fps": None,
           "frames": [frame], "canvasSize": original.get("canvasSize")}
    if frame["strokes"]:
        frame["strokes"][0]["start"] = True
    for k2 in ("playSpeed", "visibility", "caption"):
        if answer.get(k2) is not None:
            out[k2] = answer[k2]
    return out


#: The three views of a two-hands draw-back (the mock's choice under it):
#: both hands (hers, then his, as a draw-back has always played), hers alone,
#: his alone.
VIEWS = ("both", "hers", "his")


def view(original, mine, which):
    """A two-hands draw-back's drawing as `which` view plays it: "both", hers
    then his (join, as a draw-back always played); "hers", her drawing as she
    posted it; "his", his strokes at his own pace on her paper, her picture
    under them and her song with them, as he drew them there. `original` as
    the viewer may see it (read_payload), `mine` his post's own drawing
    (own). None for any other `which`."""
    if which == "hers":
        return original
    if which == "both":
        return join(original, mine)
    if which != "his":
        return None
    if flip_pages(original) is not None:
        return _his_pages(original, mine)
    of = _frame0(original) or {}
    out = dict(mine)
    frame = dict(_frame0(mine) or {})
    photo = of.get("photo") if _truthy(of.get("photo")) else original.get("photo") if _truthy(original.get("photo")) else None
    music = of.get("music") if _truthy(of.get("music")) else original.get("music") if _truthy(original.get("music")) else None
    frame.update(background=of.get("background"), photo=photo, music=music)
    out["frames"] = [frame]
    out["canvasSize"] = original.get("canvasSize") or mine.get("canvasSize")
    return out

#: The pause rules a replay knows (app.js PAUSE_CAPS), in milliseconds.
PAUSE_CAPS = {"keep": None, "trim": 250, "tight": 50}


def _frame0(payload):
    frames = payload.get("frames") if isinstance(payload, dict) else None
    if not isinstance(frames, list) or len(frames) != 1 or not isinstance(frames[0], dict):
        return None
    return frames[0]


def _frames(payload):
    """A drawing's pages, or None when it has none or one is not a page."""
    frames = payload.get("frames") if isinstance(payload, dict) else None
    if not isinstance(frames, list) or not frames or not all(isinstance(f, dict) for f in frames):
        return None
    return frames


def flip_pages(payload):
    """A Flip's pages, when `payload` is one: more than one page, played as
    pages (its playbackMode "flip", or none: Skribl's own rule for which
    editor made it, validation._payload_kind). None for anything else, a
    drawing of one page included (a one-page Flip replays as a still, and is
    drawn back on in the Pad)."""
    frames = _frames(payload)
    if frames is None or len(frames) < 2 or payload.get("playbackMode") not in (None, "flip"):
        return None
    return frames


def same_pages(original, answer):
    """The answer has one page for each of the original's (the Pad's one,
    a Flip's every one): drawn page for page, in her order (answer 1)."""
    a, b = _frames(original), _frames(answer)
    return a is not None and b is not None and len(a) == len(b)


def all_points(payload):
    """Every point of every page, in page order."""
    out = []
    for f in _frames(payload) or []:
        out.extend(_points(f))
    return out


def _pages_drawable(payload, pages, answer):
    """drawable() for a Flip (flip_pages): what the first step can't do yet
    (the mock's "not in the first step"), then the answer's own picture and
    song, as the Pad's. A page that draws itself can be drawn back on: it
    plays hers, then his (drawback.py's opening)."""
    for k in ("loop", "under", "beat"):
        if payload.get(k) is not None:
            return k
    if answer and (any(_truthy(f.get("photo")) for f in pages) or _truthy(payload.get("photo"))):
        return "photo"
    if answer and (any(_truthy(f.get("music")) for f in pages) or _truthy(payload.get("music"))):
        return "music"
    if any(f.get("recolors") for f in pages) or payload.get("recolors"):
        return "recolors"
    return None


def _truthy(v):
    """Whether a picture or a sound is there: its data (a dict's `data`, as
    the editors write a photo and a song), or a string; a dict of settings
    alone (a fit, an opacity) is none."""
    if isinstance(v, dict):
        return bool(v.get("data"))
    return bool(v)


def drawable(payload, answer=False):
    """None when `payload` can be drawn back on, else why not: "pages" (no
    frames, or pages that are not a Flip's), "recolors"; for a Flip
    (flip_pages, page for page since Nov 25) "loop", "under" or "beat", the
    first step's limits. (A two-hands
    draw-back is not drawn back on yet, whatever its drawing: its post says
    "hands", posts.py.) With `answer`,
    whether it can be the strokes of an answer: then a picture under it
    ("photo") or music ("music") are refused too, since a draw-back keeps the
    author's background and music and the answer adds neither (the owner,
    Nov 19: "why not just only let a drawback be on author's background and
    music?", and their yes)."""
    pages = flip_pages(payload)
    if pages is not None:
        return _pages_drawable(payload, pages, answer)
    f0 = _frame0(payload)
    if f0 is None:
        return "pages"
    if payload.get("playbackMode") not in (None, "replay"):
        return "pages"
    for k in ("loop", "under", "beat"):
        if payload.get(k) is not None:
            return "pages"
    if answer and (_truthy(f0.get("photo")) or _truthy(payload.get("photo"))):
        return "photo"
    if answer and (_truthy(f0.get("music")) or _truthy(payload.get("music"))):
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


def _media_of(original, of, key):
    """Her picture or her song (`key`), on her first page or, for a drawing
    from before pages, at the top; None when there is none."""
    return of.get(key) if _truthy(of.get(key)) else original.get(key) if _truthy(original.get(key)) else None


def _timed(points, base):
    """`points` laid on from `base` at their own pace, a gap back in time (a
    new take) as none; the first one starts a stroke."""
    out, at = [], base
    for i, p in enumerate(points):
        if i:
            gap = _t(p) - _t(points[i - 1])
            if gap > 0:
                at += gap
        q = dict(p)
        q["t"] = int(round(at))
        if i == 0:
            q["start"] = True
        out.append(q)
    return out


def _paged(original, answer, frames):
    """A Flip draw-back's envelope around `frames`: her pages per second (and
    the time grid it was written for), her shape; the answer's starting
    speed, its gallery choice and its caption, as on the Pad: it is the
    answer's post."""
    out = {"version": answer.get("version", 2), "schemaVersion": answer.get("schemaVersion", 2),
           "playbackMode": "flip", "fps": original.get("fps"), "frames": frames,
           "canvasSize": original.get("canvasSize")}
    if original.get("subdiv") is not None:
        out["subdiv"] = original["subdiv"]
    for k2 in ("playSpeed", "visibility", "caption"):
        if answer.get(k2) is not None:
            out[k2] = answer[k2]
    return out


def _her_page(of, frame):
    """Her page's own paper and timing on `frame`: its ground, how long it
    holds, and (never, in the first step) whether it draws itself."""
    frame["background"] = of.get("background")
    if of.get("hold") is not None:
        frame["hold"] = of["hold"]
    if of.get("draw") is True:
        frame["draw"] = True
    return frame


def _join_pages(original, answer):
    """A Flip draw-back's drawing (answers 1 and 2): page for page, her page
    with his on it, as one animation at her speed. Each page: her strokes
    as she drew them, then his a beat on from her last point at his own pace
    (a still page shows them whole; a page that draws itself draws hers, then
    his: the owner's "hers then his"); her paper, her hold, and whether it
    draws itself. Her picture and song on the first page, her shape and pages
    per second (_paged). Both drawable() and same_pages()."""
    ofs, afs = flip_pages(original), _frames(answer)
    frames = []
    for i, of in enumerate(ofs):
        af = afs[i]
        ops, aps = _points(of), _points(af)
        strokes = [dict(p) for p in ops]
        if strokes:
            strokes[0]["start"] = True
        strokes += _timed(aps, (_t(strokes[-1]) if strokes else 0) + PAUSE_CAPS["tight"])
        frame = {"strokes": strokes, "strokeGroups": _groups(of, len(ops)) + _groups(af, len(aps))}
        if i == 0:
            frame.update(photo=_media_of(original, of, "photo"), music=_media_of(original, of, "music"))
        frames.append(_her_page(of, frame))
    out = _paged(original, answer, frames)
    # THE PICTURE IT RESTS ON: Flip's card of the two (lib/drawback.js under
    # flip.js's card), as the Pad's.
    if isinstance(answer.get("thumbnail"), str) and answer["thumbnail"]:
        out["thumbnail"] = answer["thumbnail"]
    return out


def _own_pages(original, answer):
    """A two-hands Flip draw-back's own drawing (own): his pages alone, each
    on her page's paper and at her hold, her shape and pages per second; no
    picture and no music (hers stay hers)."""
    ofs, afs = flip_pages(original), _frames(answer)
    frames = []
    for of, af in zip(ofs, afs):
        aps = [dict(p) for p in _points(af)]
        if aps:
            aps[0]["start"] = True
        frames.append(_her_page(of, {"strokes": aps, "strokeGroups": _groups(af, len(aps))}))
    return _paged(original, answer, frames)


def _his_pages(original, mine):
    """His alone (view "his") on a Flip: his pages, each on her page's paper
    and at her hold, her picture and song on the first page, as he drew them
    there."""
    ofs, mfs = flip_pages(original), _frames(mine) or []
    frames = []
    for i, of in enumerate(ofs):
        mf = dict(mfs[i]) if i < len(mfs) else {"strokes": [], "strokeGroups": []}
        if i == 0:
            mf.update(photo=_media_of(original, of, "photo"), music=_media_of(original, of, "music"))
        frames.append(_her_page(of, mf))
    out = dict(mine)
    out["frames"] = frames
    out["canvasSize"] = original.get("canvasSize") or mine.get("canvasSize")
    return out


def join(original, answer):
    """The draw-back's drawing: `original`'s strokes first, as it plays,
    squeezed to OVERTURE_MS at most, then `answer`'s at its own pace; the
    original's shape and ground, the answer's pause rule and speed. Both
    drawable(). Each point keeps everything it carries but its time. A
    Flip's, page for page (_join_pages)."""
    if flip_pages(original) is not None:
        return _join_pages(original, answer)
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
    # THE AUTHOR'S BACKGROUND AND MUSIC (the owner's yes, Nov 19): her photo
    # and her song, as Skribl handed them (read_payload's inline_media: data,
    # ready to post again), on her page or, for a drawing from before pages,
    # at the top.
    photo = of.get("photo") if _truthy(of.get("photo")) else original.get("photo") if _truthy(original.get("photo")) else None
    music = of.get("music") if _truthy(of.get("music")) else original.get("music") if _truthy(original.get("music")) else None
    frame = {"strokes": strokes,
             "strokeGroups": _groups(of, len(ops)) + _groups(af, len(aps)),
             "background": of.get("background"), "photo": photo, "music": music}
    out = {"version": answer.get("version", 2), "schemaVersion": answer.get("schemaVersion", 2),
           "playbackMode": "replay", "pauseMode": answer.get("pauseMode") or "tight", "fps": None,
           "frames": [frame], "canvasSize": original.get("canvasSize")}
    if answer.get("playSpeed") is not None:
        out["playSpeed"] = answer.get("playSpeed")
    for k2 in ("visibility", "caption"):
        if k2 in answer:
            out[k2] = answer[k2]
    # THE PICTURE IT RESTS ON (a post's card: what a feed and a strip show
    # before it plays). The Pad makes it with her drawing under his
    # (lib/drawback.js paintUnder); without it a draw-back rested as an
    # empty box (the owner, Nov 19: "there's no image on the drawbacks").
    if isinstance(answer.get("thumbnail"), str) and answer["thumbnail"]:
        out["thumbnail"] = answer["thumbnail"]
    return out


# ---- WHAT A DRAW-BACK SAYS OF ITSELF (the walkthrough's mocks, choice 6; the
# owner's "all yes", Nov 19) -------------------------------------------------
# Its line and its play button said "drawn in 8 sec" under a cat that took
# 15: they counted the joined drawing, in which hers plays squeezed to three
# seconds. Each hand's own drawing time is kept when the draw-back is made
# (hands, on the post: models.Post.hands_json), and the line says them,
# "Drawn in 15 sec + 5 sec", the play button who and the whole, "Ana + Theo ·
# 20 sec".

#: How many names a play button says one by one; past them, "Ana + 4 others".
NAMED = 4


def _whole(ms):
    """A hand's time in whole seconds, a second at least, as its words are
    said ("15 sec"): kept so, the parts a line says add up to the whole its
    play button says ("15 sec + 5 sec", "20 sec"), which two roundings of
    14.6 and 4.6 would not."""
    return max(1000, int(ms / 1000 + 0.5) * 1000)


def drawn_ms(points):
    """How long `points` took to draw, as a drawing's line counts it
    (lib/replayline.js drawnMs, skribl/validation.py _payload_line): every
    positive gap between consecutive points, uncapped; a gap back in time (a
    new take) adds nothing."""
    total = 0
    for a, b in zip(points, points[1:]):
        gap = _t(b) - _t(a)
        if gap > 0:
            total += gap
    return int(round(total))


def paged_ms(payload):
    """How long a drawing took to draw, page by page (drawn_ms on each, the
    time between pages not counted): a Pad drawing's one page is its
    drawn_ms."""
    return sum(drawn_ms(_points(f)) for f in _frames(payload) or [])


def hands(original, answer, theirs, owner_id, me_id):
    """A draw-back's hands, [[person id, ms], ...] in the order they play:
    the original's (`theirs`, its own list, when it is a draw-back itself: a
    jam; else its maker `owner_id` and how long its drawing took), then
    `me_id` and how long the answer took. `original` and `answer` as join()
    takes them, before it. A Flip's, page by page (paged_ms): its line says
    its pages, so the times are kept and not shown."""
    before = read_hands(theirs) or [[owner_id, _whole(paged_ms(original))]]
    return before + [[me_id, _whole(paged_ms(answer))]]


def read_hands(raw):
    """hands_json read back, or a list as hands() made it: [[person id, ms],
    ...], or None when it is not one (a column never written, a row
    hand-edited): a person's id may be None, once they are gone."""
    import json
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return None
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for h in raw:
        if (not isinstance(h, (list, tuple)) or len(h) != 2 or isinstance(h[1], bool)
                or not isinstance(h[1], (int, float)) or h[1] < 0
                or not (h[0] is None or (isinstance(h[0], int) and not isinstance(h[0], bool)))):
            return None
        out.append([h[0], int(h[1])])
    return out


def hands_from_lines(orig_line, line, owner_id, me_id):
    """A draw-back from before its hands were kept, said from the two
    drawings' stored lines (Skribl's: "drawn", the artist's time, and
    "play", how long the replay runs): the original's own drawn time; and
    for the answer, the joined drawing's drawn time less the original's
    part as join() laid it down (its replay, squeezed to OVERTURE_MS at
    most) and the one beat between the two. None when either line is not
    there, or the sum does not come out (the original changed hands since)."""
    try:
        theirs, play, both = int(orig_line["drawn"]), int(orig_line["play"]), int(line["drawn"])
    except (KeyError, TypeError, ValueError):
        return None
    mine = both - min(play, OVERTURE_MS) - PAUSE_CAPS["tight"]
    if theirs <= 0 or mine < 0:
        return None
    return [[owner_id, _whole(theirs)], [me_id, _whole(mine)]]


def by_words(names):
    """Who drew it, for the play button: "Ana + Theo", "Ana + Theo + Mira",
    and past NAMED names "Ana + 4 others". `names` in the order they play."""
    names = [n for n in names if n]
    if len(names) <= NAMED:
        return " + ".join(names)
    return f"{names[0]} + {len(names) - 1} others"


def same_shape(original, answer):
    """The answer was drawn on the original's canvas (the Pad opens on its
    shape), so its strokes sit where the original's do."""
    a, b = original.get("canvasSize") or {}, answer.get("canvasSize") or {}
    try:
        return (round(float(a.get("cssWidth"))) == round(float(b.get("cssWidth")))
                and round(float(a.get("cssHeight"))) == round(float(b.get("cssHeight"))))
    except (TypeError, ValueError):
        return False
