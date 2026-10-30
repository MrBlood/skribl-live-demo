#!/usr/bin/env python3
"""The words a review found saying what is no longer true (after v326).

How it works, Ask, the button cards, the little book and Draw along, on the
Pad and Flip, each read where a person reads it, and each red on the words
before. What they had said:

  * that a saved draft "stays on this browser" and that "nothing is uploaded
    until you post", to someone signed in, whose drafts and their photo and
    music go to the account;
  * "Save draft" for the button that says Save;
  * that Flip's stamp shelf stays up while you place (it steps away, as the
    owner asked), that a scrub bar lies over the canvas (the page strip is
    the timeline), that a page's x deletes it on a phone (its ⋯ does) and
    that hovering a page moves it (the bar above the strip does);
  * a "stacked-sheets toggle" for Onion skin, in Tune;
  * that a take keeps the timing "not the pauses" (every pause is kept, and
    Pauses decides how it replays), and "new pixels can't silently diverge";
  * a "+" for the custom colours, a rainbow swatch since the + went;
  * "Media" for the button named Photo and music;
  * Crossfade without where it is (under Fine-tune; it is Smooth restart now); "Flip Mode" for Flip; the P and E
    shortcuts as Flip's alone, which the Pad has too; Smudge saying one
    thing twice; "hold one" to a mouse, which rests;
  * that a drawing's name goes with its posts (the Post title starts empty);
  * Ask's "Draw more over a replay" beginning with Play, which hides the pill
    that draws more (Add take then, Keep drawing now);
  * Draw along's ending, cut off mid-word in a phone's pill, and "Press Play"
    on a one-page Flip, which has no Play;
  * the Post card telling a Flip it will "draw itself", the Shape card named
    Shapes, and the book's "sixteen times faster to see an hour in a minute";
  * and the posting mock's plain words: Stroke layers keeping strokes "from
    beading", which nobody says, and "Add take" and "Take saved", which ask a
    person to learn what a take is before they can draw more (it is Keep
    drawing now, the pill, its toasts, How it works and Ask alike).
"""
import os
import pathlib
import re
import sys

from assertions import make_check
import browsing

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    print(f"SUITE-SKIPPED: {exc}")
    print("No assertions were executed. This is NOT evidence the words are right.")
    raise SystemExit(77)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parent.parent
results = []
check = make_check(results, with_detail=True)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)

TIPS = """() => { const out = {}; const sq = s => (s || '').replace(/\\s+/g, ' ').trim();
  document.querySelectorAll('#helpDrawer .help-tip').forEach(t => {
    const p = t.querySelector('.help-pill'), d = t.querySelector('.help-desc');
    if (p && d) out[sq(p.textContent)] = sq(d.textContent); });
  document.querySelectorAll('#helpDrawer .help-step').forEach(t => {
    const p = t.querySelector('.help-title'), d = t.querySelector('.help-desc');
    if (p && d) out['step: ' + sq(p.textContent)] = sq(d.textContent); });
  const e = document.getElementById('helpEmpty'); out['(empty)'] = e ? sq(e.textContent) : '';
  return out; }"""

ANSWER = """(id) => { if (typeof openHelpDrawer === 'function') openHelpDrawer();
  document.getElementById('askAnswer').innerHTML = '';
  const r = document.createElement('button'); r.setAttribute('data-answer', id); r.hidden = true;
  document.getElementById('helpWatch').appendChild(r); r.click(); r.remove();
  return [...document.querySelectorAll('#askAnswer .ask-steps li')].map(li => ({
    text: li.textContent.replace(/\\s+/g, ' ').trim(), sel: li.getAttribute('data-sel') })); }"""


def page(b, path, view=DESK, signed=False):
    pg = b.new_page(**view)
    pg.add_init_script("window.__skriblLearnForce = true;")
    if signed:
        # The page as the server writes it for someone signed in: the drafts'
        # own switch, the one lib/savedrafts.js and Ask both read.
        def as_signed(route):
            r = route.fetch()
            route.fulfill(response=r, body=r.text().replace("signedIn: false", "signedIn: true", 1))
        pg.route(re.compile(r"/(flip)?(\?.*)?$"), as_signed)
    browsing.goto(pg, BASE, path)
    pg.wait_for_timeout(1200)
    return pg


def has(text, *want, without=()):
    return bool(text) and all(w in text for w in want) and not any(w in text for w in without)


with sync_playwright() as p:
    b = p.chromium.launch()
    pad = page(b, "/")
    flip = page(b, "/flip")
    T = {"Pad": pad.evaluate(TIPS), "Flip": flip.evaluate(TIPS)}
    P, F = T["Pad"], T["Flip"]

    print("\nHOW IT WORKS")
    check("Pad: Autosave says Save, in the ⋯ menu, keeps named copies in Your drafts",
          has(P.get("Autosave"), "keeps named ones in Your drafts", without=("Save draft",)), P.get("Autosave"))
    check("Flip: Stamps says the shelf steps away as you place, and Stamps brings it back",
          has(F.get("Stamps"), "steps away as you place", "bring the shelf back", without=("stays up while you place",)),
          F.get("Stamps"))
    check("Flip: Play & scrub says the page strip is the timeline while it plays, as does the last step",
          has(F.get("Play & scrub"), "the page strip is the timeline", without=("scrub bar",))
          and has(F.get("step: Play & Post"), "page strip", without=("scrub bar",)),
          f"{F.get('Play & scrub')} | {F.get('step: Play & Post')}")
    check("Flip: Pages says how to delete a page on a phone and on a computer, and the strip's bar moves it",
          has(F.get("Pages"), "on a computer", "Delete at the end of its ⋯ on a phone")
          and has(F.get("step: Add pages to animate"), "with the bar above the strip", without=("Hover a page",)),
          f"{F.get('Pages')} | {F.get('step: Add pages to animate')}")
    check("Flip: Onion skin is found in Tune, by its own name",
          has(F.get("Onion skin"), "Onion skin, in Tune", without=("stacked-sheets", "settings panel")), F.get("Onion skin"))
    check("Pad: the two timers say every pause is kept, and Pauses, in Tune, decides how it replays",
          has(P.get("Two timers"), "Every pause is kept", "Pauses, in Tune", without=("not the pauses",)), P.get("Two timers"))
    check("Pad: a finished take is locked, said in plain words",
          has(P.get("Canvas locks between takes"), "what you see is always what replays", without=("diverge",)),
          P.get("Canvas locks between takes"))
    for ed in ("Pad", "Flip"):
        t = T[ed]
        check(f"{ed}: the custom colours are the rainbow swatches, not a +",
              has(t.get("Color"), "the rainbow one", without=("+ dot",)) and has(t.get("Background"), "rainbow", without=("Tap +",)),
              f"{t.get('Color')} | {t.get('Background')}")
        check(f"{ed}: the photo and the music are under Photo and music, the button's own name",
              has(t.get("Add a track"), "Tap Photo and music", without=("Media",))
              and has(t.get("Add a photo"), "Tap Photo and music", without=("Media",)),
              f"{t.get('Add a track', '')[:80]} | {t.get('Add a photo', '')[:60]}")
        check(f"{ed}: Pen and Eraser name their shortcuts, P and E",
              has(t.get("Pen"), "Shortcut: P.") and has(t.get("Eraser"), "Shortcut: E."), f"{t.get('Pen', '')[-40:]} | {t.get('Eraser', '')[-40:]}")
    # Where it is moved with the drawer: under Adjust and Fine-tune until the
    # streamline (#616), in More until the four doors, behind the Restart
    # door since. The old names are gone.
    check("Smooth restart (it was Crossfade) says where it is, behind the Restart door, on the Pad and Flip alike",
          all(has(t.get("Smooth restart"), "In Restart", without=("Adjust", "Fine-tune", "In More")) for t in (P, F)),
          f"Pad {P.get('Smooth restart')}; Flip {F.get('Smooth restart')}")
    switch = pad.evaluate("() => { const b = document.getElementById('flipBtn'); return b ? b.getAttribute('aria-label') : null; }")
    check("Pad: the editor switch names Flip as Skribl Flip, as the Pad is Skribl Pad, not Flip Mode",
          bool(switch) and switch.startswith("Skribl Flip:"), str(switch))
    check("Flip: Smudge says once what happens where you have not drawn",
          bool(F.get("Smudge")) and F["Smudge"].count("rather than doing nothing") == 1, F.get("Smudge"))
    check("How it works' empty search says how to ask a button, with a finger or a pointer",
          has(P.get("(empty)"), "hold one, or rest your pointer on it"), P.get("(empty)"))
    # A post's title since the owner's Q3: a name you give starts it.
    check("Pad: the name's tip says what the name goes with, a post's title among them",
          has(P.get("Name"), "drafts, backups and exports", "a name you give starts its title when you post",
              without=("and posts",)), P.get("Name"))
    check("Signed out, Photo & music says nothing is uploaded until you post",
          has(P.get("Photo & music"), "Nothing is uploaded until you post."), P.get("Photo & music"))

    print("\nASK")
    steps = pad.evaluate(ANSWER, "drafts")
    check("Ask, signed out: a draft is saved on this browser",
          any("Tap Save. It stays on this browser." in s["text"] for s in steps), str(steps))
    sp = page(b, "/", signed=True)
    signed_steps = sp.evaluate(ANSWER, "drafts")
    check("Ask, signed in: a draft is kept in the account, in any browser you sign in to",
          any("kept in your account" in s["text"] for s in signed_steps)
          and not any("this browser" in s["text"] for s in signed_steps), str(signed_steps))
    sp.close()
    takes = pad.evaluate(ANSWER, "takes")
    check("Ask's Draw more over a replay starts where Keep drawing shows, on the canvas between takes",
          bool(takes) and "Keep drawing" in takes[0]["text"] and takes[0]["sel"] == "#addTakePill"
          and not any("Play your drawing" in s["text"] for s in takes), str(takes))

    print("\nTHE BUTTON CARDS AND THE BOOK")
    cards = {}
    for ed, pg in (("Pad", pad), ("Flip", flip)):
        cards[ed] = pg.evaluate("""() => { const L = window.SkriblLearnCard; if (!L) return null;
            const read = s => { L.close(); if (!L.open(s)) return null; const c = document.querySelector('.lc-card');
              const r = c && { t: c.querySelector('.lc-t').textContent, line: c.querySelector('.lc-line').textContent };
              L.close(); return r; };
            return { post: read('#postBtn'), shape: read('#shapeToolBtn') }; }""")
    check("The Post card says a Flip plays and a Pad drawing draws itself",
          bool(cards["Pad"] and cards["Flip"] and cards["Pad"]["post"] and cards["Flip"]["post"])
          and "draw itself" in cards["Pad"]["post"]["line"] and "watch it play" in cards["Flip"]["post"]["line"],
          str({k: v and v["post"] for k, v in cards.items()}))
    check("The Shape card is named Shape, as the button is",
          bool(cards["Pad"] and cards["Pad"]["shape"]) and cards["Pad"]["shape"]["t"] == "Shape", str(cards["Pad"]))
    # The book from a fresh page: How it works opens on Ask's home, where New
    # here? is (an answer left open above would hide it).
    bk = page(b, "/")
    bk.evaluate("() => openHelpDrawer()")
    bk.wait_for_timeout(700)
    bk.click("#askTour")
    bk.wait_for_timeout(1200)
    for _ in range(2):
        bk.click("#bkNext")
        bk.wait_for_timeout(300)
    line = bk.evaluate("() => (document.getElementById('bkLine') || {}).textContent || ''")
    bk.close()
    check("The little book's speeds add up: Fit shows an hour in half a minute",
          has(line, "Fit to see an hour in half a minute", without=("an hour in a minute",)), line)

    # THE POSTING MOCK'S PLAIN WORDS. Stroke layers says what it saves you
    # from, in Tune and in its tip, on the Pad and Flip alike (lib/tooltip.js
    # moves a title into data-tip, so the tip is read where it went).
    print("\nPLAIN WORDS (the posting mock)")
    LAYERS = """() => { const h = document.querySelector('#tuneLayersRow .tune-hint'), s = document.getElementById('strokeLayersBtn');
      return { hint: h ? h.textContent.trim() : null, title: s ? (s.getAttribute('data-tip') || s.getAttribute('title')) : null }; }"""
    for ed, pg in (("Pad", pad), ("Flip", flip)):
        ly = pg.evaluate(LAYERS)
        check(f"{ed}: Stroke layers says no dark spots where see-through ink overlaps, in Tune and in its tip",
              ly["hint"] == "no dark spots where see-through ink overlaps"
              and has(ly["title"], "dark spots", without=("beads", "beading")), str(ly))
    # Keep drawing where it said Add take: what to do next, so nobody has to
    # learn what a take is first. The tips, the step and the card are read
    # where How it works says them; the whole sheet must not say the old name.
    sheet = pad.evaluate("() => document.getElementById('helpDrawer').textContent.replace(/\\s+/g, ' ')")
    check("Pad: How it works says Keep drawing, in its tips, its step and its card, and never Add take",
          has(P.get("Keep drawing"), "Tap Keep drawing on the canvas to add more")
          and has(P.get("Canvas locks between takes"), "Keep drawing on the canvas adds more")
          and has(P.get("step: Record the replay"), "tap Keep drawing on the canvas to add more")
          and "Tap Keep drawing to add more." in sheet and not re.search(r"Add (a )?takes?\b", sheet),
          f"{P.get('Keep drawing')} | {P.get('Canvas locks between takes')} | {P.get('step: Record the replay')}")
    pad.close()
    flip.close()

    # A take ended for real (a stroke, then Done): what the toast says, what
    # the canvas's pill says, and what a press on the finished drawing says.
    tk = b.new_page(**DESK)
    browsing.goto(tk, BASE, "/")
    tk.wait_for_timeout(900)
    tk.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    bx = tk.locator("#canvas").bounding_box()
    cx, cy = bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2
    tk.mouse.move(cx - 60, cy)
    tk.mouse.down()
    for i in range(24):
        tk.mouse.move(cx - 60 + i * 5, cy + (i % 5) * 4)
        tk.wait_for_timeout(12)
    tk.mouse.up()
    tk.wait_for_timeout(300)
    tk.evaluate("() => document.getElementById('recordBtn').click()")
    tk.wait_for_timeout(450)
    TOAST = "() => { const t = document.getElementById('toast'); return t && t.classList.contains('show') ? t.textContent.trim() : null; }"
    ended = tk.evaluate(TOAST)
    pill = tk.evaluate("() => { const p = document.getElementById('addTakePill'); return p && !p.hidden ? p.innerText.trim() : null; }")
    tk.mouse.move(cx, cy + 40)
    tk.mouse.down()
    tk.mouse.up()
    tk.wait_for_timeout(300)
    pressed = tk.evaluate(TOAST)
    tk.close()
    check("Pad: a take done, the toast says Saved and what to do next, in plain words",
          ended == "Saved. Play to watch it, or Keep drawing to add more", repr(ended))
    check("Pad: ...the canvas's pill says Keep drawing", pill == "Keep drawing", repr(pill))
    check("Pad: ...and a press on the finished drawing says how to add more, by the pill's own name",
          pressed == "Saved. Tap Keep drawing to add more, or New Skribl to start over", repr(pressed))

    print("\nDRAW ALONG'S LAST WORDS, in a phone's pill")
    for ed, path, want in (("Pad", "/", "Tap Play"), ("Flip", "/flip", "Tap Duplicate")):
        q = page(b, path, PHONE)
        end = None
        try:
            q.evaluate("() => openHelpDrawer()")
            q.wait_for_timeout(700)
            q.click("#askTour")
            q.wait_for_timeout(1200)
            q.click("#bkNext")
            q.wait_for_timeout(400)
            q.click("#bkAlong")
            q.wait_for_function("() => window.SkriblDrawAlong && SkriblDrawAlong.state()", timeout=10000)
            end = q.evaluate("""() => { const D = window.SkriblDrawAlong; let s = D.state();
                while (s && s.k < s.n) { D.skip(); s = D.state(); }
                const w = document.querySelector('.da-pill .da-where');
                return w && { text: w.textContent, fits: w.scrollWidth <= w.clientWidth, need: w.scrollWidth, room: w.clientWidth }; }""")
        except Exception as exc:
            end = {"error": str(exc)[:120]}
        check(f"{ed}: Draw along ends whole in a phone's pill, and names the next step ({want})",
              bool(end) and end.get("fits") is True and want in end.get("text", ""), str(end))
        q.close()
    b.close()

# Signed in, the page is the server's to write: the tip's other branch, from
# the blueprint itself with a signed-in user.
sys.path.insert(0, str(ROOT))
from flask import Flask  # noqa: E402
import skribl  # noqa: E402
_a = Flask(__name__)
_a.config["SECRET_KEY"] = "harness-words"
_a.register_blueprint(skribl.create_blueprint(session=False, current_user_id=lambda: "u-1", csrf=False))
_html = _a.test_client().get("/skribl-pad").get_data(as_text=True)   # the Pad, without the demo's "/"
_tip = re.search(r'help-pill">Photo &amp; music</span><div class="help-desc">(.*?)</div>', _html, re.S)
_tip = re.sub(r"<[^>]+>", "", _tip.group(1)) if _tip else ""
check("Signed in, Photo & music says they leave this browser only when you Save to your account or Post",
      has(_tip, "leave this browser only when you Save to your account or Post", without=("Nothing is uploaded",)), _tip)

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
