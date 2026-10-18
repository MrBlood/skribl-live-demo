#!/usr/bin/env python3
"""Ask: How it works as one question in your own words (lib/ask.js; owner,
after v323: the Ask mock, "All yes"; piece two of the help, FUTURE.md 6p).
Each row holds a promise, on the Pad and on Flip:

  1. IT OPENS ON ASK'S HOME, every time: the field empty, the one-minute
     tour, what people often ask (each editor its own four), the examples,
     Name every button and Everything, by section. A sheet that rises most
     of the way on a phone, the drawing still showing above it; a dialog in
     the middle on a desk.
  2. TYPING ANSWERS: the best how-to first, with Show me, and every entry
     that matches with the word lit. The everyday cousins of a word count
     ("repeat" finds the loop entries), but only as whole words: "loop" is
     not "repeated". Nothing found says so kindly, never a dead end.
  3. AN ANSWER is its title, its example, its steps and Show me, and no
     answer names a button that is not on its editor's page.
  4. SHOW ME steps aside and lights the real button with its card; tapping
     the lit button goes on to the next step; Back to Ask comes back to the
     answer. Escape on an answer, or on the answers, goes back a step.
  5. NEW HERE? plays the one-minute tour full screen.

Visible means painted: elementFromPoint. Touch is real touch.
"""
import os
import sys

from assertions import make_check
import browsing

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
results = []
check = make_check(results, detail_on_pass=False)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

PHONE = dict(viewport={"width": 402, "height": 874}, device_scale_factor=2, is_mobile=True, has_touch=True)
DESK = dict(viewport={"width": 1333, "height": 906})
OFTEN = {"Pad": ["music", "speed", "takes", "post"], "Flip": ["move", "floop", "music", "post"]}
LOOP_BEST = {"Pad": "Add a song that loops", "Flip": "Make a Flip that loops"}
# The first answer Show me is walked through, and the button its first two
# steps light.
WALK = {"Pad": ("music", "#mediaOpenBtn", "#mediaTabMusic"), "Flip": ("move", None, "#addcopy")}

PAINTED = """(sel) => { const e = document.querySelector(sel); if (!e || e.hidden) return false;
  const r = e.getBoundingClientRect(); if (!r.width || !r.height) return false;
  const at = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 20));
  return !!at && (e === at || e.contains(at)); }"""
VIEW = """() => ({ home: !document.getElementById('helpWatch').hidden, look: !document.getElementById('helpLook').hidden,
  answer: !document.getElementById('askAnswer').hidden, open: !document.getElementById('helpDrawer').hidden,
  field: document.getElementById('helpSearch').value, focus: document.activeElement && (document.activeElement.id || document.activeElement.className) })"""


def fresh(b, opts, route, scheme="light"):
    c = b.new_context(color_scheme=scheme, **opts)
    c.add_init_script("try { localStorage.setItem('skribl.learncard.note.v1', '1'); } catch (e) {}")
    q = c.new_page()
    errs = []
    q.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(q, BASE, route)
    q.wait_for_timeout(900)
    q.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
    return c, q, errs


def open_ask(q):
    q.evaluate("() => openHelpDrawer()")
    q.wait_for_timeout(700)


def ask(q, words):
    q.fill("#helpSearch", words)
    q.wait_for_timeout(350)


with sync_playwright() as p:
    b = p.chromium.launch()
    for name, route in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        print(f"\n{name}")
        c, q, errs = fresh(b, PHONE, route)

        # 1. home
        open_ask(q)
        home = q.evaluate("""() => { const often = [...document.querySelectorAll('#askOften [data-answer]')];
          const f = document.getElementById('helpSearch');
          return { field: f.value, size: getComputedStyle(f).fontSize,
                   often: often.map(o => o.getAttribute('data-answer')),
                   examples: document.querySelectorAll('#helpWatch .learn-card').length,
                   tabs: document.querySelectorAll('#helpDrawer [role=tab]').length }; }""")
        v = q.evaluate(VIEW)
        painted = {s: q.evaluate(PAINTED, s) for s in ("#helpSearch", "#askTour", "#askOften", "#learnNames")}
        check(f"{name}: How it works opens on Ask's home: the field empty, no tabs, the tour and the field painted",
              v["home"] and not v["look"] and not v["answer"] and home["field"] == "" and home["tabs"] == 0
              and painted["#helpSearch"] and painted["#askTour"], f"{v} {home} {painted}")
        check(f"{name}: ...what people often ask is this editor's four", home["often"] == OFTEN[name], str(home["often"]))
        check(f"{name}: ...and the examples are there to watch", home["examples"] > 10, str(home))
        check(f"{name}: the field is 16px or more, so iOS does not magnify the page",
              float(home["size"].rstrip("px")) >= 16, home["size"])
        # Ask's top (owner, after v324: the sheets mock, "Tighter"): the field
        # sits as far below the title as the first card sits below the field.
        gap = q.evaluate("""() => { const t = document.querySelector('#helpDrawer .help-drawer-head span').getBoundingClientRect(),
          f = document.querySelector('#helpDrawer .help-search').getBoundingClientRect(), c = document.getElementById('askTour').getBoundingClientRect();
          return { above: Math.round(f.top - t.bottom), below: Math.round(c.top - f.bottom) }; }""")
        check(f"{name}: the field sits as far below the title as the first card below it (within 4px)",
              abs(gap["above"] - gap["below"]) <= 4, str(gap))
        geo = q.evaluate("""() => { const r = document.querySelector('.help-drawer-inner').getBoundingClientRect();
          return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), vw: innerWidth, vh: innerHeight }; }""")
        check(f"{name}: on a phone Ask is a sheet: full width, rising most of the way, the drawing showing above it",
              geo["left"] == 0 and geo["right"] == geo["vw"] and geo["bottom"] == geo["vh"]
              and 0.05 * geo["vh"] <= geo["top"] <= 0.15 * geo["vh"], str(geo))

        # 2. typing
        ask(q, "loop")
        res = q.evaluate("""() => { const b = document.getElementById('askBest');
          const tips = [...document.querySelectorAll('#helpLook .help-tip')].filter(t => t.offsetParent !== null);
          return { best: b.hidden ? null : (b.querySelector('.ask-best-t') || {}).textContent,
                   show: !!b.querySelector('[data-show]'), how: !!b.querySelector('[data-answer]'),
                   n: tips.length, lit: tips.filter(t => t.querySelector('mark')).length,
                   texts: tips.map(t => t.textContent.replace(/\\s+/g, ' ').trim()) }; }""")
        v = q.evaluate(VIEW)
        check(f"{name}: typing \"loop\" shows the answers: \"{LOOP_BEST[name]}\" first, with Show me and How",
              v["look"] and not v["home"] and res["best"] == LOOP_BEST[name] and res["show"] and res["how"], f"{v} best={res['best']}")
        check(f"{name}: ...then every entry that mentions it, the word lit", res["n"] >= 2 and res["lit"] == res["n"],
              f"{res['n']} entries, {res['lit']} lit")
        # Whole words only: "repeated" is not a cousin of "loop".
        import re as _re
        cousin = _re.compile(r"loop|\b(repeat|again and again|forever)\b", _re.I)
        stray = [t[:50] for t in res["texts"] if not cousin.search(t)]
        check(f"{name}: ...and each one holds the word, or a cousin as a whole word (\"repeated\" is not \"repeat\")",
              not stray, str(stray))
        # "song" is in no entry: only its cousins (music, sound...) find them.
        ask(q, "song")
        rep = q.evaluate("() => [...document.querySelectorAll('#helpLook .help-tip')].filter(t => t.offsetParent !== null).map(t => t.textContent)")
        check(f"{name}: an everyday cousin finds them: \"song\", a word no entry uses, lists the music entries",
              any("music" in t.lower() for t in rep) and not any("song" in t.lower() for t in rep), f"{len(rep)} entries")
        ask(q, "zzqx")
        none = q.evaluate("""() => { const e = document.querySelector('#helpLook .help-empty');
          return { shown: !!e && !e.hidden && e.offsetParent !== null, best: !document.getElementById('askBest').hidden,
                   text: e ? e.textContent.replace(/\\s+/g, ' ').trim() : '' }; }""")
        check(f"{name}: nothing found says so kindly, with other words to try and the buttons to ask",
              none["shown"] and not none["best"] and "Try other words" in none["text"] and "hold one" in none["text"], str(none))

        # Escape on the answers goes back home, the field emptied and focused
        # (from elsewhere in the answers, so the focus is the move's).
        q.focus("#askLookBack")
        q.keyboard.press("Escape"); q.wait_for_timeout(400)
        v = q.evaluate(VIEW)
        check(f"{name}: Escape on the answers goes back to Ask's home, the field empty and focused, How it works still open",
              v["open"] and v["home"] and v["field"] == "" and v["focus"] == "helpSearch", str(v))

        # 3. an answer
        q.click(f"#askOften [data-answer={WALK[name][0]}]"); q.wait_for_timeout(600)
        ans = q.evaluate("""() => { const a = document.getElementById('askAnswer');
          return { title: (a.querySelector('#askAnswerT') || {}).textContent, steps: a.querySelectorAll('.ask-steps li').length,
                   show: !!a.querySelector('.ask-show[data-show]'), pic: !!a.querySelector('.ask-answer-pic'),
                   related: a.querySelectorAll('.ask-list [data-answer]').length,
                   focus: document.activeElement && document.activeElement.id }; }""")
        v = q.evaluate(VIEW)
        check(f"{name}: an answer shows its title, its example, its steps, Show me and what is related; focus on its title",
              v["answer"] and not v["home"] and ans["steps"] >= 2 and ans["show"] and ans["pic"] and ans["related"] >= 1
              and ans["focus"] == "askAnswerT", f"{v} {ans}")
        check(f"{name}: ...and Show me is painted", q.evaluate(PAINTED, "#askAnswer .ask-show"))
        # Named by its title once there is one (WAVE, after v325: the template's
        # reference pointed at a heading that only an answer creates).
        nm = q.evaluate("""() => { const a = document.getElementById('askAnswer'), id = a.getAttribute('aria-labelledby');
          const t = id && document.getElementById(id);
          return { id, inside: !!t && a.contains(t), text: t ? t.textContent.trim() : null }; }""")
        check(f"{name}: ...and the answer is named by its own title", nm["id"] == "askAnswerT" and nm["inside"]
              and nm["text"] == ans["title"], str(nm))

        # Every answer this editor has: each step that names a button names
        # one on this page. Opened as a person does, one by one, through a
        # row the suite adds (the rows Ask draws are only some of them).
        ids = ["music", "speed", "fps", "takes", "post", "export", "photo", "undo", "pen", "new", "drafts", "move", "floop"]
        missing, opened = [], []
        for aid in ids:
            # Emptied first: an answer this editor does not have leaves the
            # last one showing.
            got = q.evaluate("""(id) => { document.getElementById('askAnswer').innerHTML = '';
              const r = document.createElement('button'); r.setAttribute('data-answer', id); r.hidden = true;
              document.getElementById('helpWatch').appendChild(r); r.click(); r.remove();
              const a = document.getElementById('askAnswer'); if (a.hidden || !a.querySelector('.ask-steps')) return null;
              return [...a.querySelectorAll('.ask-steps li[data-sel]')].map(li => li.getAttribute('data-sel'))
                .filter(s => !document.querySelector(s)); }""", aid)
            if got is None:
                continue
            opened.append(aid)
            missing += [f"{aid}: {s}" for s in got]
        mine = [a for a in ids if a not in (("fps", "move", "floop") if name == "Pad" else ("speed", "takes"))]
        check(f"{name}: every answer it has ({len(opened)}) opens, and no step names a button that is not on the page",
              sorted(opened) == sorted(mine) and not missing, f"opened {opened}; missing {missing}")

        # Escape on an answer goes back a step, to Ask's home.
        q.evaluate("(id) => { const r = document.createElement('button'); r.setAttribute('data-answer', id); document.getElementById('helpWatch').appendChild(r); r.click(); r.remove(); }", WALK[name][0])
        q.wait_for_timeout(400)
        q.keyboard.press("Escape"); q.wait_for_timeout(400)
        v = q.evaluate(VIEW)
        check(f"{name}: Escape on an answer goes back to Ask's home, How it works still open",
              v["open"] and v["home"] and not v["answer"], str(v))

        # 4. Show me
        q.evaluate("(id) => { const r = document.createElement('button'); r.setAttribute('data-answer', id); document.getElementById('helpWatch').appendChild(r); r.click(); r.remove(); }", WALK[name][0])
        q.wait_for_timeout(500)
        q.click("#askAnswer .ask-show"); q.wait_for_timeout(1300)
        STEP = """() => { const c = document.querySelector('.lc-card.lc-step'); if (!c) return null;
          const r = c.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2, r.top + 24);
          const lit = document.querySelector('.lc-target');
          return { kick: c.querySelector('.lc-k').textContent, name: c.querySelector('.lc-t').textContent,
                   painted: !!at && c.contains(at), free: c.classList.contains('lc-free'),
                   lit: lit ? '#' + lit.id : null, ok: c.querySelector('.lc-ok').textContent }; }"""
        s1 = q.evaluate(STEP)
        v = q.evaluate(VIEW)
        want1 = WALK[name][1]
        check(f"{name}: Show me puts How it works away and shows step 1 of the answer on a painted card",
              not v["open"] and s1 and s1["painted"] and " 1 of " in s1["kick"], f"{v} {s1}")
        if want1:
            check(f"{name}: ...lighting the real button ({want1})", s1 and s1["lit"] == want1 and not s1["free"], str(s1))
            q.locator(want1).first.tap(); q.wait_for_timeout(1500)
        else:
            check(f"{name}: ...a step with no button is said in words, with no arrow", s1 and s1["free"] and s1["lit"] is None, str(s1))
            q.click(".lc-step .lc-ok"); q.wait_for_timeout(900)
        s2 = q.evaluate(STEP)
        check(f"{name}: " + ("tapping the lit button" if want1 else "Next") + f" goes on to step 2, lighting {WALK[name][2]}",
              s2 and " 2 of " in s2["kick"] and s2["lit"] == WALK[name][2] and s2["painted"], str(s2))
        q.click(".lc-step .lc-more"); q.wait_for_timeout(900)
        v = q.evaluate(VIEW)
        check(f"{name}: Back to Ask puts the card away and comes back to the answer",
              v["open"] and v["answer"] and not q.evaluate("() => !!document.querySelector('.lc-card')"), str(v))

        # Every opening starts on Ask's home with an empty field.
        ask(q, "export")
        q.evaluate("() => document.getElementById('helpClose').click()"); q.wait_for_timeout(700)
        open_ask(q)
        v = q.evaluate(VIEW)
        check(f"{name}: closed and opened again, Ask starts on its home, the field empty",
              v["home"] and not v["look"] and not v["answer"] and v["field"] == "", str(v))

        # 5. New here? opens the little book (lib/book.js; verify_book holds it).
        q.click("#askTour"); q.wait_for_timeout(1200)
        tour = q.evaluate("() => ({ open: !document.getElementById('bookRoot').hidden, title: document.getElementById('bkTitle').textContent })")
        check(f"{name}: New here? opens the little book", tour["open"] and tour["title"], str(tour))
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

        # On a desk, a dialog in the middle.
        c, q, errs = fresh(b, DESK, route, scheme="dark")
        open_ask(q)
        geo = q.evaluate("""() => { const r = document.querySelector('.help-drawer-inner').getBoundingClientRect();
          return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom),
                   w: Math.round(r.width), vw: innerWidth, vh: innerHeight }; }""")
        check(f"{name}: on a desk Ask is a dialog in the middle, at most 680px wide, clear of the edges",
              abs((geo["left"] + geo["right"]) / 2 - geo["vw"] / 2) <= 1 and geo["w"] <= 680
              and geo["top"] > 20 and geo["bottom"] < geo["vh"] - 20, str(geo))
        check(f"{name}: ...the field painted in it", q.evaluate(PAINTED, "#helpSearch"))
        check(f"{name}: no page errors on a desk", not errs, "; ".join(errs[:2]))
        c.close()
    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
