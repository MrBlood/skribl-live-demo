#!/usr/bin/env python3
"""The caption where people look: under the gallery's drawings, and on the Library's stage and rows.

THE OWNER, on the posting mock ("all yes"): the gallery shows the caption
"under the drawing, two lines with more, and the ≡ button goes"; the Library
"shows it under the title and on each row", and "from now on the list keeps
it". Told, and agreed: two cards side by side can then end at different
heights, with the drawings staying level.

WHAT IS ASKED, AND HOW IT IS READ
  THE GALLERY, on a phone and a desk, light and dark, searched down to this
  suite's own posts so nothing another suite posts can move them:
  * A captioned card shows its caption AT REST, under the drawing, painted
    (elementFromPoint on its first line, never a rect), at 15px in the
    card's own ink, and at most two lines of it; the whole text is in the
    tree all the same.
  * THE HEAD CARRIES NO CAPTION MARK, on any card.
  * "MORE" EXACTLY WHERE THE WORDS RUN PAST TWO LINES, asked of the words
    at the width they are set at, and asked again when the width changes:
    a caption that fits in two lines on a desk and not on a phone has its
    "more" only on the phone, in the same page, after the window narrows.
  * "MORE" OPENS THE WHOLE CAPTION AND "LESS" PUTS IT BACK, to the height
    it had; its state is in aria-expanded, its name holds its word, its box
    is 44px tall, and its words are the accent ink, read against the card.
  * IT GLIDES BOTH WAYS, read on every frame: it moves over several frames,
    no frame takes more than 40% of the way, and it lands where it should;
    a close keeps the words whole while the box shrinks. One frame the box
    held, with no long task of the page's own in it, is set aside, as the
    Posted! moment's glide does (verify_postmoment).
  * REDUCE MOTION: it just changes.
  * TWO CARDS SIDE BY SIDE END AT THEIR OWN HEIGHTS: the card without a
    caption has nothing under its drawing, the drawings' tops are level,
    and opening one card's caption leaves the other as it was.
  THE LIBRARY:
  * A post from the Pad and from Flip keeps its caption in this browser's
    list (driven through each editor's real Post sheet).
  * THE STAGE says the caption in full under the title, 16px in the page's
    ink; a post with none says nothing (hidden, not an empty line).
  * EACH ROW says one line of it, cut with an ellipsis.
  * A ROW KEPT BEFORE THE LIST KEPT CAPTIONS learns its caption once from
    /api/skribls/meta, and an empty answer is kept, so the next visit asks
    nothing; with the meta answer refused, the stage still says the caption,
    from the post it fetches to play.
"""
import json
import os
import sys
import urllib.request

from assertions import make_check

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, with_detail=True)


def summarise_and_exit():
    bad = [r for r in results if not r[0]]
    print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
          + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
    sys.exit(1 if bad else 0)


try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the caption is where people look.")
    raise SystemExit(77)
import browsing  # noqa: E402

# For calibration: CAPTIONS_PART=gallery,glide,pair,library runs only those parts.
PART = [p for p in (os.environ.get("CAPTIONS_PART") or "").split(",") if p]


def part(name):
    return not PART or name in PART


TAG = "cap" + os.urandom(3).hex()
PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1100, "height": 1000})
LONG = ("She sits there every morning and tells the birds what she thinks of them. "
        "Then she naps in the one square of sun, and nobody may move her, not even "
        "the dog, who has tried twice and still has the scar on his nose.")
# Between the two: under two lines on a desk's card, more than two on the
# narrowest phone measured (320).
MEDIUM = "Ten pages, one ball, no rush. It bounces twice and rolls off to the left, a little slower each time."
SHORT = "Took my time on this one."


def make_post(title, caption, visibility="public"):
    """A post through the API: the caption is what this suite reads, and the
    Post sheet that writes it is driven below, where it is the thing asked."""
    n = 14
    pts = [{"x": 90 + i * 46, "y": 150 + (i % 4) * 44, "color": "#7c5cff",
            "size": 12, "t": i * 120} for i in range(n)]
    body = {"title": title, "caption": caption, "version": 2, "schemaVersion": 2,
            "visibility": visibility, "playbackMode": "replay",
            "frames": [{"strokes": pts, "strokeGroups": [n]}],
            "canvasSize": {"cssWidth": 816, "cssHeight": 612}}
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["id"]


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Oldest first: the gallery lists newest first, so on a desk the first row is
# the long caption beside the card with none, and the next row the medium
# beside the short.
SHORT_ID = make_post(f"{TAG} short", SHORT)
MEDIUM_ID = make_post(f"{TAG} medium", MEDIUM)
NONE_ID = make_post(f"{TAG} none", "")
LONG_ID = make_post(f"{TAG} long", LONG)
IDS = {"long": LONG_ID, "none": NONE_ID, "medium": MEDIUM_ID, "short": SHORT_ID}

# Each card's facts, by its title's last word. PAINTED is asked of the first
# line's middle; the ink is the computed colour against the card's own.
CARDS = """() => {
  const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
  const probe = document.createElement('span'); probe.style.color = 'var(--accent-ink)';
  document.body.appendChild(probe); const accentInk = rgb(getComputedStyle(probe).color); probe.remove();
  const y0 = window.scrollY, out = {}, tiles = [];
  /* GEOMETRY FIRST, all at one scroll, so two cards' tops can be compared. */
  for (const t of document.querySelectorAll('.tile')) {
    const tt = t.querySelector('.tt'); if (!tt) continue;
    const key = tt.textContent.trim().split(' ').pop();
    const p = t.querySelector('.tcap'), m = t.querySelector('.tcapMore'), st = t.querySelector('.tileStage');
    const o = { h: t.getBoundingClientRect().height, top: t.getBoundingClientRect().top,
                stageTop: st ? st.getBoundingClientRect().top : null,
                headMarks: t.querySelectorAll('.thead button:not(.tileMore), .tileCapBtn').length,
                /* SLACK: what is under the card's last part beyond that part's
                   own margin and the card's padding and border, i.e. height the
                   card was given and holds nothing in. */
                slack: (() => { const kids = [...t.children].filter(c => c.getClientRects().length);
                  const last = kids.reduce((a, c) => c.getBoundingClientRect().bottom >= a.getBoundingClientRect().bottom ? c : a);
                  const tc = getComputedStyle(t);
                  return t.getBoundingClientRect().bottom - last.getBoundingClientRect().bottom
                    - parseFloat(getComputedStyle(last).marginBottom) - parseFloat(tc.paddingBottom)
                    - parseFloat(tc.borderBottomWidth); })(),
                card: rgb(getComputedStyle(t).backgroundColor),
                accentInk: accentInk };
    if (p) {
      const cs = getComputedStyle(p), r = p.getBoundingClientRect();
      const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom), lh = parseFloat(cs.lineHeight);
      Object.assign(o, { cap: true, text: p.textContent, size: cs.fontSize, ink: rgb(cs.color),
        lh: lh, shown: (r.height - pad) / lh, words: (p.scrollHeight - pad) / lh,
        below: r.top >= (st ? st.getBoundingClientRect().bottom - 1 : 0), capH: r.height });
    }
    if (m) {
      const cs = getComputedStyle(m), r = m.getBoundingClientRect();
      Object.assign(o, { more: !m.hidden && r.height > 0, moreWord: m.textContent.trim(), moreH: r.height,
        moreName: m.getAttribute('aria-label') || '', expanded: m.getAttribute('aria-expanded'),
        moreInk: rgb(cs.color) });
    }
    out[key] = o; tiles.push([key, p, m]);
  }
  /* THEN THE PAINT, each part brought on screen to be asked: a point off the
     screen has nothing painted at it. */
  for (const [key, p, m] of tiles) {
    if (p) { p.scrollIntoView({ block: 'center' });
      const cs = getComputedStyle(p), r = p.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + parseFloat(cs.paddingLeft) + 6,
                                            r.top + parseFloat(cs.paddingTop) + parseFloat(cs.lineHeight) / 2);
      out[key].painted = !!hit && (hit === p || p.contains(hit)); }
    if (m && !m.hidden) { m.scrollIntoView({ block: 'center' }); const r = m.getBoundingClientRect();
      out[key].moreHit = r.height > 0 && document.elementFromPoint(r.left + 8, r.top + r.height / 2) === m; }
  }
  window.scrollTo(0, y0);
  return out; }"""


def gallery(pg, theme):
    browsing.goto(pg, BASE, "/gallery")
    pg.wait_for_timeout(600)
    pg.fill("#galleryQ", TAG)
    pg.wait_for_function(f"() => document.querySelectorAll('.tile').length === 4 && "
                         f"[...document.querySelectorAll('.tile .tt')].every(t => t.textContent.indexOf('{TAG}') === 0)",
                         timeout=20000)
    pg.wait_for_timeout(700)


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- THE GALLERY AT REST ----------------------------------------------
    if part("gallery"):
        print("\nTHE GALLERY: the caption under the drawing, two lines at rest, and a more where there is more")
        for theme in ("light", "dark"):
            for dev, spec in (("phone", PHONE), ("desk", DESK)):
                c = b.new_context(color_scheme=theme, **spec)
                pg = c.new_page()
                gallery(pg, theme)
                k = pg.evaluate(CARDS)
                where = f"{dev}, {theme}"
                if dev == "phone" and theme == "light":
                    check("the fixture: the four posts, and the search found only them",
                          sorted(k) == ["long", "medium", "none", "short"], str(sorted(k)))
                cap = [k.get(x, {}) for x in ("long", "medium", "short")]
                check(f"{where}: each captioned card shows its caption at rest, painted, under the drawing",
                      all(x.get("cap") and x.get("painted") and x.get("below") and x.get("shown", 0) >= 0.9 for x in cap),
                      str([(x.get("painted"), x.get("below"), round(x.get("shown", 0), 2)) for x in cap]))
                check(f"{where}: ...at 15px in the card's own ink, 7:1 and up",
                      all(x.get("size") == "15px" and ratio(x.get("ink", [0, 0, 0]), x.get("card", [255, 255, 255])) >= 7 for x in cap),
                      str([(x.get("size"), round(ratio(x.get("ink", [0, 0, 0]), x.get("card", [255, 255, 255])), 1)) for x in cap]))
                check(f"{where}: ...and two lines of it at most, the whole text in the tree all the same",
                      all(x.get("shown", 9) <= 2.05 for x in cap) and k.get("long", {}).get("text") == LONG,
                      str([round(x.get("shown", 0), 2) for x in cap]))
                check(f"{where}: the head carries no caption mark, on any card",
                      all(x.get("headMarks") == 0 for x in k.values()),
                      str({n: x.get("headMarks") for n, x in k.items()}))
                check(f"{where}: a card with no caption has no caption and no more",
                      not k.get("none", {}).get("cap") and not k.get("none", {}).get("more"), str(k.get("none")))
                over = {n: (x.get("words", 0) > 2.05, bool(x.get("more"))) for n, x in k.items() if x.get("cap")}
                check(f"{where}: 'more' shows exactly where the words run past two lines",
                      all(a == m for a, m in over.values()) and over.get("long") == (True, True)
                      and over.get("short") == (False, False),
                      str({n: (round(k[n].get("words", 0), 2), v[1]) for n, v in over.items()}))
                lg = k.get("long", {})
                check(f"{where}: ...it is a control a finger can find: painted, 44px tall, named with its word",
                      lg.get("moreHit") and lg.get("moreH", 0) >= 44 and lg.get("moreWord") == "more"
                      and "more" in lg.get("moreName", "") and lg.get("expanded") == "false",
                      f"hit={lg.get('moreHit')} h={lg.get('moreH')} word={lg.get('moreWord')!r} "
                      f"name={lg.get('moreName')!r} expanded={lg.get('expanded')}")
                mr = ratio(lg.get("moreInk", [0, 0, 0]), lg.get("card", [255, 255, 255]))
                ai = lg.get("accentInk") or [0, 0, 0]
                check(f"{where}: ...in the accent ink, 7:1 against the card",
                      mr >= 7 and lg.get("moreInk") == ai and ai[2] - ai[0] >= 40 and ai[2] - ai[1] >= 40,
                      f"{lg.get('moreInk')} (the accent ink is {ai}) on {lg.get('card')}: {mr:.2f}:1")
                if dev == "desk":
                    md = k.get("medium", {})
                    check(f"{where}: the medium caption fits in two lines on a desk, so it has no more",
                          md.get("cap") and md.get("words", 9) <= 2.05 and not md.get("more"),
                          f"words={md.get('words')} more={md.get('more')}")
                    # THE SAME PAGE, NARROWED TO A SMALL PHONE: the question is
                    # asked again when the card changes width, not only when it
                    # is built.
                    pg.set_viewport_size({"width": 320, "height": 640})
                    pg.wait_for_timeout(500)
                    k2 = pg.evaluate(CARDS)
                    md2 = k2.get("medium", {})
                    check(f"{where}: ...narrowed to a 320 phone in the same page, it runs past two lines and has its more",
                          md2.get("words", 0) > 2.05 and md2.get("more") is True,
                          f"words={md2.get('words')} more={md2.get('more')}")
                c.close()

    # ---- MORE, LESS, AND THE GLIDE ----------------------------------------
    # The caption's height on every frame from the press, with the page's own
    # long tasks beside it so a frame the box held is told from one the page did.
    SAMPLE = """(key) => new Promise(resolve => {
      const t = [...document.querySelectorAll('.tile')].find(x => x.querySelector('.tt').textContent.trim().endsWith(' ' + key));
      const p = t.querySelector('.tcap'), m = t.querySelector('.tcapMore');
      const lt = []; let obs = null;
      try { obs = new PerformanceObserver(l => l.getEntries().forEach(e => lt.push([e.startTime, e.duration])));
            obs.observe({ type: 'longtask' }); } catch (e) {}
      const fr = []; const t0 = performance.now();
      const read = () => ({ t: performance.now() - t0, h: p.getBoundingClientRect().height,
                            whole: getComputedStyle(p).display !== '-webkit-box' });
      fr.push(read());
      m.click();
      fr.push(read());
      function tick() { fr.push(read()); if (performance.now() - t0 < 700) requestAnimationFrame(tick);
        else { obs && obs.disconnect(); resolve({ fr: fr, lt: lt.map(([s, d]) => [s - t0, d]), t0: t0,
                 word: m.textContent.trim(), expanded: m.getAttribute('aria-expanded'),
                 name: m.getAttribute('aria-label') || '', fits: p.scrollHeight <= p.clientHeight + 1 }); } }
      requestAnimationFrame(tick);
    })"""

    def glide_facts(s, start, end):
        fr = s["fr"]
        hs = [f["h"] for f in fr]
        way = abs(end - start)
        steps = [(fr[i]["t"] - fr[i - 1]["t"], abs(hs[i] - hs[i - 1]), i) for i in range(2, len(fr))]
        moving = [x for x in steps if x[1] > 0.5]
        usual = sorted(x[0] for x in steps)[len(steps) // 2] if steps else 16
        held = [x for x in moving if x[0] >= max(30, 1.5 * usual) and x[1] > 0.4 * way
                and not any(a < fr[x[2]]["t"] and a + d > fr[x[2] - 1]["t"] for a, d in s["lt"])]
        aside = max(held, key=lambda x: x[1]) if held else None
        big = max([x[1] for x in moving if x is not aside] or [0])
        jump0 = abs(hs[1] - hs[0])   # the frame of the press itself, before any paint
        return dict(way=round(way, 1), moving=len(moving), big=round(big, 1), aside=aside and round(aside[1], 1),
                    land=round(hs[-1], 1), jump0=round(jump0, 1), mid=[f for f in fr if
                    min(start, end) + 0.2 * way < f["h"] < max(start, end) - 0.2 * way])

    if part("glide"):
        print("\nMORE OPENS IT, LESS PUTS IT BACK, AND BOTH WAYS GLIDE")
        for theme in ("light", "dark"):
            c = b.new_context(color_scheme=theme, **PHONE)
            pg = c.new_page()
            gallery(pg, theme)
            rest = pg.evaluate(CARDS)["long"]["capH"]
            s = pg.evaluate(SAMPLE, "long")
            pg.wait_for_timeout(300)
            open_h = pg.evaluate(CARDS)["long"]["capH"]
            g = glide_facts(s, rest, open_h)
            check(f"{theme}: 'more' opens the whole caption",
                  open_h > rest + 20 and s["fits"] and s["word"] == "less" and s["expanded"] == "true"
                  and "less" in s["name"],
                  f"rest {rest:.1f} -> open {open_h:.1f}, fits={s['fits']}, word={s['word']!r}, "
                  f"expanded={s['expanded']}, name={s['name']!r}")
            check(f"{theme}: ...gliding there: several frames, none more than 40% of the way, landing on the whole text",
                  g["moving"] >= 6 and g["big"] <= 0.4 * g["way"] and g["jump0"] < 0.5 and abs(g["land"] - open_h) < 1,
                  f"{g['moving']} moving frames, biggest {g['big']}px of {g['way']}px, press frame {g['jump0']}px,"
                  f" landed {g['land']} (open {open_h:.1f})" + (f", set aside one held frame of {g['aside']}px" if g["aside"] else ""))
            s2 = pg.evaluate(SAMPLE, "long")
            pg.wait_for_timeout(300)
            back = pg.evaluate(CARDS)["long"]
            g2 = glide_facts(s2, open_h, rest)
            check(f"{theme}: 'less' puts it back to the two lines it had",
                  abs(back["capH"] - rest) < 0.5 and back.get("moreWord") == "more" and back.get("expanded") == "false"
                  and back.get("shown", 9) <= 2.05,
                  f"back {back['capH']:.1f} vs rest {rest:.1f}, word={back.get('moreWord')!r}, expanded={back.get('expanded')}")
            check(f"{theme}: ...gliding there too, with the words whole while the box shrinks",
                  g2["moving"] >= 6 and g2["big"] <= 0.4 * g2["way"] and g2["jump0"] < 0.5 and abs(g2["land"] - rest) < 1
                  and len(g2["mid"]) > 0 and all(f["whole"] for f in g2["mid"]),
                  f"{g2['moving']} moving frames, biggest {g2['big']}px of {g2['way']}px, press frame {g2['jump0']}px, "
                  f"landed {g2['land']}; mid-way frames {len(g2['mid'])}, whole in all: {all(f['whole'] for f in g2['mid'])}")
            c.close()
        c = b.new_context(color_scheme="light", reduced_motion="reduce", **PHONE)
        pg = c.new_page()
        gallery(pg, "light")
        rest = pg.evaluate(CARDS)["long"]["capH"]
        s = pg.evaluate(SAMPLE, "long")
        hs = [f["h"] for f in s["fr"]]
        check("Reduce Motion: 'more' just opens, in the frame it is pressed",
              hs[1] > rest + 20 and len(set(round(h, 1) for h in hs[1:])) == 1,
              f"rest {rest:.1f}, then {sorted(set(round(h, 1) for h in hs[1:]))}")
        c.close()

    # ---- TWO CARDS SIDE BY SIDE -------------------------------------------
    if part("pair"):
        print("\nTWO CARDS SIDE BY SIDE END AT THEIR OWN HEIGHTS, AND THE DRAWINGS STAY LEVEL")
        c = b.new_context(color_scheme="light", **DESK)
        pg = c.new_page()
        gallery(pg, "light")
        k = pg.evaluate(CARDS)
        lg, nn = k["long"], k["none"]
        check("the fixture: the long caption and the card with none share the desk's first row",
              abs(lg["top"] - nn["top"]) < 1, f"tops {lg['top']:.1f} and {nn['top']:.1f}")
        check("the two end at their own heights: the captioned one is taller",
              lg["h"] > nn["h"] + 30, f"{lg['h']:.1f} vs {nn['h']:.1f}")
        check("...the card with no caption has nothing under its drawing it did not ask for",
              abs(nn["slack"]) <= 1 and abs(lg["slack"]) <= 1,
              f"{nn['slack']:.1f}px of slack under the uncaptioned card's drawing, {lg['slack']:.1f}px under the long caption")
        check("...and their drawings are level",
              abs(lg["stageTop"] - nn["stageTop"]) < 1, f"stage tops {lg['stageTop']:.1f} and {nn['stageTop']:.1f}")
        pg.evaluate(SAMPLE, "long")
        pg.wait_for_timeout(300)
        k2 = pg.evaluate(CARDS)
        check("opening the long one's caption grows that card and leaves the one beside it as it was",
              k2["long"]["h"] > lg["h"] + 20 and abs(k2["none"]["h"] - nn["h"]) < 0.5
              and abs(k2["none"]["stageTop"] - nn["stageTop"]) < 0.5,
              f"long {lg['h']:.1f} -> {k2['long']['h']:.1f}; none {nn['h']:.1f} -> {k2['none']['h']:.1f}")
        c.close()

    # ---- THE LIBRARY ------------------------------------------------------
    if part("library"):
        print("\nTHE LIBRARY: the list keeps the caption; the stage says it all, each row one line")
        # THE POST SHEET, DRIVEN. Each editor's own sheet, a drawing, a caption.
        for ed, path in (("Pad", "/"), ("Flip", "/flip")):
            c = b.new_context(color_scheme="light", **DESK)
            pg = c.new_page()
            browsing.goto(pg, BASE, path)
            pg.wait_for_timeout(900)
            pg.evaluate("() => { window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide(); }")
            sel = "#canvas" if ed == "Pad" else "#pad"
            box = pg.locator(sel).bounding_box()
            x0, y0 = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.4
            pg.mouse.move(x0, y0)
            pg.mouse.down()
            for i in range(1, 22):
                pg.mouse.move(x0 + i * box["width"] * 0.02, y0 + (i % 5) * box["height"] * 0.03, steps=2)
                pg.wait_for_timeout(16)
            pg.mouse.up()
            pg.wait_for_timeout(400)
            if ed == "Pad":
                pg.evaluate("() => { if (typeof recording !== 'undefined' && recording) endRecordingTake(); }")
                pg.wait_for_timeout(300)
            pg.click("#postBtn")
            pg.wait_for_selector("#postSheet", state="visible")
            pg.wait_for_timeout(450)
            pg.fill("#postTitleInput", f"{TAG} {ed} kept")
            pg.fill("#postCaptionInput", "  " + MEDIUM + "  ")
            pg.click("#postSubmitBtn")
            pg.wait_for_selector("#postDone:not([hidden])", timeout=20000)
            kept = pg.evaluate("() => JSON.parse(localStorage.getItem('skribl_posted_v1') || '[]')[0] || null")
            check(f"{ed}: a post keeps its caption in this browser's list, as the server keeps it",
                  kept and kept.get("caption") == MEDIUM and kept.get("title") == f"{TAG} {ed} kept",
                  f"{kept and {k: kept.get(k) for k in ('title', 'caption')}}")
            c.close()

        def entry(pid, title, caption=None):
            e = {"id": pid, "url": BASE + "/s/" + pid, "title": title, "kind": "pad", "pages": 1,
                 "visibility": "public", "tok": None, "local": False, "has_audio": False,
                 "canvas_w": 816, "canvas_h": 612, "at": 1700000000000}
            if caption is not None:
                e["caption"] = caption
            return e
        # Newest first, as the list keeps it: the long one is kept WITH its
        # caption; the short and the none were kept before the list kept any.
        seed = [entry(LONG_ID, f"{TAG} long", LONG), entry(SHORT_ID, f"{TAG} short"), entry(NONE_ID, f"{TAG} none")]
        ROWS = """() => { const rgb = s => (s.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
          const out = {}, y0 = window.scrollY;
          const s = document.getElementById('pCap'), cs = s && getComputedStyle(s);
          out.stage = s ? { text: s.textContent, hidden: s.hidden, h: s.getBoundingClientRect().height,
            size: cs.fontSize, ink: rgb(cs.color), title: (document.getElementById('pTitle') || {}).textContent,
            below: s.getBoundingClientRect().top >= document.getElementById('pTitle').getBoundingClientRect().bottom - 1 } : null;
          let g = null; for (let e = s; e && !g; e = e.parentElement) { const bg = getComputedStyle(e).backgroundColor;
            const c = rgb(bg), a = (bg.match(/[\\d.]+/g) || [])[3];
            if (c.length === 3 && (a === undefined || +a === 1)) g = c; }
          if (out.stage) out.stage.ground = g || [255, 255, 255];
          /* THE ROW'S LINK CARRIES A TAP BAND (posted.css .posted-main::before),
             transparent and over its words, so a hit test lands on the link.
             Taken out of hit testing while the words are asked, and only then. */
          const lift = document.createElement('style');
          lift.textContent = '.posted-main::before { pointer-events: none !important; }';
          document.head.appendChild(lift);
          for (const r of document.querySelectorAll('.posted-row')) {
            const t = r.querySelector('.posted-title'); if (!t) continue;
            const key = t.textContent.trim().split(' ').pop(), cp = r.querySelector('.posted-cap');
            const o = { cap: null };
            if (cp) { cp.scrollIntoView({ block: 'center' });
              const cs2 = getComputedStyle(cp), q = cp.getBoundingClientRect();
              const hit = document.elementFromPoint(q.left + 4, q.top + q.height / 2);
              o.cap = { text: cp.textContent, lines: q.height / parseFloat(cs2.lineHeight), cut: cp.scrollWidth > cp.clientWidth,
                        ellipsis: cs2.textOverflow, painted: !!hit && (hit === cp || cp.contains(hit)), size: cs2.fontSize,
                        below: q.top >= t.getBoundingClientRect().bottom - 1 }; }
            out[key] = o;
          }
          lift.remove();
          window.scrollTo(0, y0);
          out.kept = JSON.parse(localStorage.getItem('skribl_posted_v1') || '[]');
          return out; }"""

        def pick(pg, key):
            pg.evaluate("(k) => { const r = [...document.querySelectorAll('.posted-row')].find(x => x.querySelector('.posted-title').textContent.trim().endsWith(' ' + k)); r.querySelector('.posted-main').click(); }", key)
            pg.wait_for_function(f"() => (document.getElementById('pTitle').textContent || '').endsWith(' {key}')", timeout=15000)
            pg.wait_for_timeout(500)

        for theme in ("light", "dark"):
            c = b.new_context(color_scheme=theme, **PHONE)
            metas = []
            c.on("request", lambda r: metas.append(r.url) if "/api/skribls/meta" in r.url else None)
            c.add_init_script("try { if (!sessionStorage.getItem('capseeded')) { localStorage.setItem('skribl_posted_v1', "
                              + json.dumps(json.dumps(seed)) + "); sessionStorage.setItem('capseeded', '1'); } } catch (e) {}")
            pg = c.new_page()
            browsing.goto(pg, BASE, "/library")
            pg.wait_for_function("() => document.querySelectorAll('.posted-row').length >= 3", timeout=15000)
            pg.wait_for_timeout(1500)
            r = pg.evaluate(ROWS)
            st = r.get("stage") or {}
            check(f"{theme}: the stage says the caption in full under the title",
                  st.get("text") == LONG and not st.get("hidden") and st.get("h", 0) > 40 and st.get("below")
                  and (st.get("title") or "").endswith(" long"),
                  f"{st and {k: st.get(k) for k in ('hidden', 'h', 'below', 'title')}} text={str(st.get('text'))[:40]!r}")
            check(f"{theme}: ...16px in the page's own ink, 7:1 and up",
                  st.get("size") == "16px" and ratio(st.get("ink", [0, 0, 0]), st.get("ground", [255, 255, 255])) >= 7,
                  f"{st.get('size')}, {ratio(st.get('ink', [0, 0, 0]), st.get('ground', [255, 255, 255])):.1f}:1")
            lr = (r.get("long") or {}).get("cap") or {}
            check(f"{theme}: each row says one line of its caption, under the title, cut with an ellipsis",
                  lr.get("painted") and lr.get("below") and lr.get("lines", 9) < 1.2 and lr.get("cut")
                  and lr.get("ellipsis") == "ellipsis" and lr.get("text") == LONG,
                  str(lr))
            kept = {e["id"]: e for e in r.get("kept", [])}
            check(f"{theme}: a row kept before the list kept captions learns its caption from the server",
                  kept.get(SHORT_ID, {}).get("caption") == SHORT and ((r.get("short") or {}).get("cap") or {}).get("text") == SHORT,
                  f"stored {kept.get(SHORT_ID, {}).get('caption')!r}, row {((r.get('short') or {}).get('cap') or {}).get('text')!r}")
            check(f"{theme}: ...and one with none keeps the empty answer, and shows no line",
                  kept.get(NONE_ID, {}).get("caption") == "" and (r.get("none") or {}).get("cap") is None,
                  f"stored {kept.get(NONE_ID, {}).get('caption')!r}, row {(r.get('none') or {}).get('cap')}")
            pick(pg, "none")
            st2 = pg.evaluate(ROWS).get("stage") or {}
            check(f"{theme}: a post with no caption says nothing on the stage, not an empty line",
                  st2.get("hidden") is True and st2.get("h") == 0, str({k: st2.get(k) for k in ("hidden", "h", "text")}))
            asked = [u for u in metas if SHORT_ID in u or NONE_ID in u]
            metas.clear()
            pg.reload()
            pg.wait_for_function("() => document.querySelectorAll('.posted-row').length >= 3", timeout=15000)
            pg.wait_for_timeout(1500)
            again = [u for u in metas if SHORT_ID in u or NONE_ID in u]
            check(f"{theme}: the old rows were asked once, and the next visit asks nothing",
                  len(asked) >= 1 and not again, f"first visit {len(asked)} meta asks for them, the next {len(again)}")
            c.close()

        # THE META ANSWER REFUSED: the stage still says the caption, from the
        # post it fetches to play.
        c = b.new_context(color_scheme="light", **DESK)
        c.route("**/api/skribls/meta**", lambda route: route.abort())
        c.add_init_script("try { localStorage.setItem('skribl_posted_v1', "
                          + json.dumps(json.dumps([entry(SHORT_ID, f"{TAG} short")])) + "); } catch (e) {}")
        pg = c.new_page()
        browsing.goto(pg, BASE, "/library")
        pg.wait_for_function("() => (document.getElementById('pTitle').textContent || '').endsWith(' short')", timeout=15000)
        pg.wait_for_timeout(1500)
        r = pg.evaluate(ROWS)
        check("with the meta answer refused, the stage still says the caption, from the post it plays",
              (r.get("stage") or {}).get("text") == SHORT and not (r.get("stage") or {}).get("hidden")
              and ((r.get("short") or {}).get("cap")) is None,
              f"stage {(r.get('stage') or {}).get('text')!r}, row {(r.get('short') or {}).get('cap')}")
        c.close()

    b.close()

summarise_and_exit()
