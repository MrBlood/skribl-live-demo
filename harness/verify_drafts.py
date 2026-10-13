"""Draft durability — the debounce is not a loss window, and the guard fires
on measured durability rather than on media presence.

External review P0-2/#19/#3, and DESIGN-DIRECTION.md's "durable drafts"
prerequisite. Every scenario here was a REAL loss path before this work:

  1. Draw one stroke and reload inside the 1.2s debounce — the work vanished,
     because nothing flushed on pagehide. Now it must survive.
  2. Break localStorage entirely and tap Flip — the old guard stayed silent
     (no media attached = "nothing at risk") and the drawing was gone. Now the
     leave sheet must appear, because the flush could not make the draft
     durable.
  3. Attach a photo, reload, restore — the drawing came back and the photo did
     not (metadata only, by design). Now the bytes come back from IndexedDB,
     through the same <input> change pipeline a manual re-add uses.
  4. "Saved without media" faded after 1.6s while the condition it described
     persisted. Now the amber pill stays up.
  5. A blank tab's empty-state autosave deleted a draft another tab wrote
     after it loaded. Now that clear is fenced.

Uses the runner's server on :5001 like the other browser suites.
"""
import json, sys, time
from pathlib import Path
from assertions import make_check
import os

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = Path(__file__).resolve().parents[1]

results = []
check = make_check(results)

# One tiny real PNG, drawn in-page, so the media path exercises the real
# validators rather than a fake byte string they would rightly reject.
MAKE_PNG_FILE = """async () => {
  const c = document.createElement('canvas'); c.width = 8; c.height = 8;
  const g = c.getContext('2d'); g.fillStyle = '#3355ff'; g.fillRect(0,0,8,8);
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  return Array.from(new Uint8Array(await blob.arrayBuffer()));
}"""

DRAW_STROKE = """() => {
  const cv = document.getElementById('drawCanvas') || document.querySelector('canvas');
  const r = cv.getBoundingClientRect();
  // Pointer events: the Pad draws on them since v315 (SK312-002).
  const opts = (x, y) => ({ bubbles: true, cancelable: true, clientX: r.left + x, clientY: r.top + y,
                            button: 0, pointerId: 1, pointerType: 'mouse', isPrimary: true });
  cv.dispatchEvent(new PointerEvent('pointerdown', opts(30, 30)));
  cv.dispatchEvent(new PointerEvent('pointermove', opts(90, 70)));
  cv.dispatchEvent(new PointerEvent('pointerup',   opts(90, 70)));
  return (typeof strokes !== 'undefined') ? strokes.length : -1;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- 1. pagehide flush beats the debounce -------------------------
    print("\nFLUSH — a reload inside the debounce window loses nothing")
    ctx = b.new_context()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    n = pg.evaluate(DRAW_STROKE)
    check("a synthetic stroke registers", n >= 1, f"strokes.length={n}")
    # Reload IMMEDIATELY — well inside the 1.2s debounce. Only the pagehide
    # flush can have written the draft.
    pg.reload(wait_until="load")
    pg.wait_for_timeout(600)
    back = pg.evaluate("() => strokes.length")
    check("the drawing is back after an instant reload",
          back >= 1, f"strokes.length={back} — the pagehide flush "
          "is the only thing that can have saved this")
    check("no page errors across draw/reload", not errors, "; ".join(errors[:2]))
    ctx.close()

    # ---------- 2. broken storage arms the guard -----------------------------
    print("\nGUARD — keyed to durability, not to media presence")
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.add_init_script("""
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) {
        if (k === 'skribl_autosave_v1') { const e = new Error('quota'); e.name = 'QuotaExceededError'; throw e; }
        return orig.apply(this, arguments);
      };""")
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(DRAW_STROKE)
    pg.wait_for_timeout(1600)   # let the debounced write run and FAIL
    pill = pg.evaluate("() => { const el = document.getElementById('autosaveStatus');"
                       " const t = document.getElementById('autosaveStatusText');"
                       " return el && !el.hidden ? t.textContent : null; }")
    # v224 splits the message: a QUOTA rejection -- which is what this block
    # injects -- is the one the user can act on, so it says so. Everything else
    # stays "Autosave failed". They used to be the same four words, which is
    # exactly why a real report of this could not be diagnosed from a screenshot.
    check("a full store is reported as a FULL store, not a generic failure",
          pill == "Storage full — not saved", str(pill))
    ctx.close()

    # ...and a non-quota exception must NOT claim the disk is full. Same forced
    # failure, different cause: this is the half that would have been silently
    # mislabelled if the split were keyed on anything but the error itself.
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.add_init_script("""
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) {
        if (k === 'skribl_autosave_v1') throw new TypeError('not a quota problem');
        return orig.apply(this, arguments);
      };""")
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(DRAW_STROKE)
    pg.wait_for_timeout(1600)
    pill = pg.evaluate("() => { const el = document.getElementById('autosaveStatus');"
                       " const t = document.getElementById('autosaveStatusText');"
                       " return el && !el.hidden ? t.textContent : null; }")
    check("any other write failure stays the generic message", pill == "Autosave failed", str(pill))
    pg.wait_for_timeout(2200)   # past the old 1.6s fade
    still = pg.evaluate("() => { const el = document.getElementById('autosaveStatus');"
                        " return el && !el.hidden && el.classList.contains('show'); }")
    check("and the warning is a STATE, not a toast — still up after 2.2s",
          bool(still), "the old fade told the user a live problem had resolved")
    # No media attached — the OLD guard would let this navigation straight
    # through and the drawing would be gone.
    pg.evaluate("() => document.getElementById('flipBtn').click()")
    pg.wait_for_timeout(400)
    state = pg.evaluate("() => ({ sheet: !document.getElementById('leaveSheet').hidden,"
                        " here: location.pathname })")
    check("tapping Flip with an un-durable drawing raises the leave sheet",
          state["sheet"] is True, str(state))
    check("and navigation did NOT happen", state["here"] == "/", state["here"])
    ctx.close()

    # ---------- 3. media bytes round-trip through IndexedDB ------------------
    print("\nMEDIA — photo bytes survive a reload via IndexedDB")
    ctx = b.new_context()
    pg = ctx.new_page()
    m_errors = []
    pg.on("pageerror", lambda e: m_errors.append(str(e)))
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(DRAW_STROKE)
    png = pg.evaluate(MAKE_PNG_FILE)
    pg.evaluate("""(bytes) => {
      const f = new File([new Uint8Array(bytes)], 'pin.png', { type: 'image/png' });
      const dt = new DataTransfer(); dt.items.add(f);
      const input = document.getElementById('photoInput');
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }""", png)
    pg.wait_for_timeout(2200)   # attach pipeline + IndexedDB put + autosave
    stored = pg.evaluate("""() => window.SkriblDraftStore.get('pad:photo')
        .then(r => r ? { name: r.name, size: r.blob.size } : null).catch(e => String(e))""")
    check("the attached photo's bytes are in the draft store",
          isinstance(stored, dict) and stored.get("name") == "pin.png" and stored.get("size", 0) > 0,
          str(stored))
    pill = pg.evaluate("() => { const el = document.getElementById('autosaveStatus');"
                       " const t = document.getElementById('autosaveStatusText');"
                       " return el && !el.hidden ? t.textContent : '(hidden)'; }")
    check("with the bytes durable, the pill does not cry media",
          pill in ("Saved", "(hidden)"), f"{pill!r} — amber now means FAILURE, "
          "and nothing failed")
    pg.reload(wait_until="load")
    pg.wait_for_timeout(3100)   # restore at boot (v294) + IDB get + DataTransfer re-add + image decode
    photo = pg.evaluate("() => { const img = document.getElementById('photoBgImg');"
                        " return img ? { shown: img.style.display !== 'none',"
                        " hasSrc: !!img.src && img.src.length > 40, name: img._fileName || null } : null; }")
    check("after restore, the photo is BACK — bytes, not a re-add card",
          bool(photo and photo["shown"] and photo["hasSrc"] and photo["name"] == "pin.png"),
          str(photo))
    # A restored drawing is a POSTABLE drawing. v269 made Post ship disabled
    # from first paint, with every take-producing path clearing the flag —
    # except restoreAutosave, which still only un-hid the button (the whole
    # reveal back when Post was hidden-until-take). Reported from the live
    # demo the day v269 shipped: restore a drawing and Post stays dimmed until
    # a NEW take is recorded on top of it.
    post = pg.evaluate("() => { const b = document.getElementById('postBtn');"
                       " return { hidden: b.hidden, disabled: b.disabled }; }")
    check("after restore, Post is live — a restored drawing is postable",
          post == {"hidden": False, "disabled": False}, str(post))
    check("no page errors across the media round-trip", not m_errors, "; ".join(m_errors[:2]))
    ctx.close()

    # ---------- 4. Flip: quota spills media to IndexedDB ---------------------
    print("\nFLIP — a quota fallback keeps the media, in IndexedDB")
    ctx = b.new_context()
    pg = ctx.new_page()
    # Simulate quota: the flip autosave key refuses any large value, which is
    # exactly what a real ~5MB overflow looks like to the code.
    pg.add_init_script("""
      const orig = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) {
        if (k === 'skribl_flip_autosave_v1' && String(v).length > 2000) {
          const e = new Error('quota'); e.name = 'QuotaExceededError'; throw e;
        }
        return orig.apply(this, arguments);
      };""")
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(800)
    # A background image is the media that blows the budget in real use.
    png = pg.evaluate(MAKE_PNG_FILE)
    pg.evaluate("""(bytes) => {
      // Inflate the payload past the fake quota with many strokes, then hand
      // saveNow a media field the same way the app stores one.
      const big = 'x'.repeat(4000);
      bgImage = new Image(); imageName = 'pin.png';
      musicData = 'data:audio/wav;base64,' + big;  // media bytes in the payload
      frames[0].strokes.push({ x: 1, y: 1, start: true });
      saveNow();
    }""", png)
    pg.wait_for_timeout(1200)   # IndexedDB put settles
    spilled = pg.evaluate("""() => window.SkriblDraftStore.get('flip:draft')
        .then(r => r ? { has: !!r.json, marked: JSON.parse(localStorage.getItem('skribl_flip_autosave_v1') || '{}').mediaInIdb === true } : null)
        .catch(e => String(e))""")
    check("the full payload landed in IndexedDB and the lite record is marked",
          isinstance(spilled, dict) and spilled.get("has") and spilled.get("marked"),
          str(spilled))
    pill = pg.evaluate("() => { const el = document.getElementById('autosaveStatus');"
                       " const t = document.getElementById('autosaveStatusText');"
                       " return el && !el.hidden ? t.textContent : '(hidden)'; }")
    check("once the spill settles the pill upgrades to Saved — the session IS recoverable",
          pill == "Saved", f"{pill!r}")
    ctx.close()

    # ---------- 5. an idle fresh tab's flush must not delete a draft ---------
    # Found by the v222 release aggregate (via verify_strokegroups' planted
    # draft): flushing on visibilitychange means a FRESH tab flushes while its
    # canvas is still empty — and the empty-state path cleared the slot, so
    # opening the app and switching tabs deleted the stored draft with the
    # restore banner still on screen offering it. Both surfaces now gate the
    # empty-state clear on session ownership: only a session that has written
    # real work here may treat empty as a deliberate clear.
    print("\nIDLE TAB — flushing an empty fresh session leaves the stored draft alone")
    for path, key, plant in [
        ("/", "skribl_autosave_v1",
         "{version:1, savedAt:'2026-01-01T00:00:00Z', strokes:[{x:1,y:1}],"
         " strokeGroups:[1], background:{color:'#fff'}}"),
        # Flip auto-restores a healthy draft (no banner), which makes the tab
        # non-empty and shields the record even without the fence — so the
        # sharp case is a record tryRestore REJECTS (empty frames array): the
        # tab stays empty, and only the ownership fence stands between an idle
        # flush and deleting data this session never owned. Data the app
        # cannot parse is still data; deletion is the one unrecoverable
        # outcome, so an unowned slot is left alone even when unreadable.
        ("/flip", "skribl_flip_autosave_v1",
         "{schemaVersion:2, version:2, playbackMode:'flip', fps:12,"
         " canvasSize:{cssWidth:800,cssHeight:600,dpr:1}, editIdx:0,"
         " frames:[]}"),
    ]:
        ctx = b.new_context()
        pg = ctx.new_page()
        pg.add_init_script(f"localStorage.setItem('{key}', JSON.stringify({plant}));")
        pg.goto(f"{BASE}{path}", wait_until="load")
        pg.wait_for_timeout(900)
        if path == "/":
            # Do NOT touch the banner — the draft is unclaimed, which is the point.
            pg.evaluate("() => { document.dispatchEvent(new Event('visibilitychange')); }")
        survived = pg.evaluate(
            f"""() => {{
              // Fire the flush the way a tab switch does, then read the slot.
              Object.defineProperty(document, 'visibilityState',
                                    {{ value: 'hidden', configurable: true }});
              document.dispatchEvent(new Event('visibilitychange'));
              return localStorage.getItem('{key}') !== null;
            }}""")
        check(f"{'Pad' if path == '/' else 'Flip'}: the stored draft survives an idle flush",
              survived is True,
              "an empty fresh tab's visibilitychange flush deleted a pre-existing draft")
        ctx.close()

    # ---------- 6. the empty-clear fence -------------------------------------
    print("\nMULTI-TAB — an empty tab cannot delete another tab's live draft")
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    # Simulate a SECOND tab writing after this one loaded: a foreign writerId
    # with a savedAt in the future of this page's load.
    fenced = pg.evaluate("""() => {
      const foreign = { version: 1, writerId: 'other-tab', savedAt: new Date(Date.now() + 5000).toISOString(),
                        strokes: [{x:1,y:1}], strokeGroups: [1], background: { color: '#fff' } };
      localStorage.setItem('skribl_autosave_v1', JSON.stringify(foreign));
      // This tab is EMPTY — its write path takes the clear branch.
      writeAutosave();
      return localStorage.getItem('skribl_autosave_v1') !== null;
    }""")
    check("the empty-state clear leaves the foreign draft alone", fenced is True,
          "writeAutosave's clear branch deleted a record another tab wrote after this one loaded")
    ctx.close()

    # ---------- 6. Flip's amber must describe a failure that HAPPENED --------
    print("\nFLIP PILL — amber is a verdict, not a placeholder")
    # WHY THIS SECTION EXISTS. Flip's media save writes the drawing to
    # localStorage and spills the media bytes to IndexedDB. Until v229 it
    # painted 'saved-no-media' -- an amber warning that deliberately NEVER
    # fades -- synchronously, before the spill had settled, on the path the
    # comments themselves call the normal way media is saved. Instrumented:
    #
    #     put:start bytes=4215866
    #     pill:saved-no-media        (+1ms)
    #     put:RESOLVED / pill:saved  (+13ms)
    #
    # 13ms of amber is invisible on a desktop, which is exactly why it shipped
    # and why the existing pill assertion (Pad, final state only) could not see
    # it. On a phone writing megabytes it is visible, and if the write is slow
    # or fails it never clears. The user's report was "the saved without media
    # stays stuck on flip".
    #
    # So this records the WHOLE sequence rather than the resting state. A final
    # -state check passes on both the broken and the fixed build.
    ctx = b.new_context()
    pg = ctx.new_page()
    f_errors = []
    pg.on("pageerror", lambda e: f_errors.append(str(e)))
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_timeout(900)
    pg.evaluate("""() => { window.__pill = [];
      const orig = window.showAutosaveStatus;
      window.showAutosaveStatus = function (st) { window.__pill.push(st); return orig.apply(this, arguments); };
    }""")
    png2 = pg.evaluate(MAKE_PNG_FILE)
    pg.evaluate("""(bytes) => {
      const f = new File([new Uint8Array(bytes)], 'flip.png', { type: 'image/png' });
      const dt = new DataTransfer(); dt.items.add(f);
      const input = document.getElementById('imageInput');
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }""", png2)
    pg.wait_for_timeout(2600)
    seq = pg.evaluate("() => window.__pill")
    check("Flip: the media save is instrumented at all", len(seq) > 0,
          f"{seq} — an empty sequence makes every check below vacuous")
    check("Flip: a SUCCESSFUL media save never shows the amber warning",
          "saved-no-media" not in seq,
          f"{seq} — amber means the bytes are lost; announcing it before the "
          f"write has settled is a warning about something that did not happen")
    check("Flip: it says 'saving' while the spill is in flight",
          "saving" in seq, f"{seq} — the pending state is what amber replaced")
    check("Flip: and settles on plain 'Saved'", seq and seq[-1] == "saved",
          f"{seq}")

    # The other half, and the one that must NOT regress: a real failure still
    # earns the amber. Without this, "never show amber" is satisfiable by
    # deleting the warning.
    pg2 = ctx.new_page()
    pg2.goto(f"{BASE}/flip", wait_until="load")
    pg2.wait_for_timeout(900)
    pg2.evaluate("""() => { window.__pill = [];
      const orig = window.showAutosaveStatus;
      window.showAutosaveStatus = function (st) { window.__pill.push(st); return orig.apply(this, arguments); };
      window.SkriblDraftStore.put = function () { return Promise.reject(new Error('forced')); };
    }""")
    png3 = pg2.evaluate(MAKE_PNG_FILE)
    pg2.evaluate("""(bytes) => {
      const f = new File([new Uint8Array(bytes)], 'flip.png', { type: 'image/png' });
      const dt = new DataTransfer(); dt.items.add(f);
      const input = document.getElementById('imageInput');
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }""", png3)
    pg2.wait_for_timeout(2600)
    seq2 = pg2.evaluate("() => window.__pill")
    check("Flip: a FAILED spill still raises the amber warning",
          "saved-no-media" in seq2,
          f"{seq2} — the fix must narrow when amber appears, never remove it")
    stuck = pg2.evaluate("""() => { const el = document.getElementById('autosaveStatus');
        const t = document.getElementById('autosaveStatusText');
        return { hidden: el.hidden, text: t.textContent,
                 opacity: getComputedStyle(el).opacity }; }""")
    check("Flip: and that warning STAYS on screen",
          stuck["hidden"] is False and stuck["text"] == "Saved without media"
          and stuck["opacity"] == "1",
          f"{stuck} — a warning that fades claims it was resolved")
    check("Flip: no page error through either path", not f_errors, "; ".join(f_errors[:2]))

    # ---- a spill that never settles, and a warning about a PAST loss --------
    print("\nFLIP PILL — the two ways it used to get stuck")
    # A PUT THAT HANGS. IndexedDB on iOS Safari can accept a multi-megabyte
    # write and then settle NEITHER way. Two handlers look like complete
    # coverage and are not: the third outcome of an async call to something
    # outside your process is silence, and without a deadline the pill sat on
    # "Saving…" for the rest of the session — reported as "saving stays
    # blinking". Every later save re-entered the same branch, so it was not just
    # stuck, it was self-renewing.
    pg3 = ctx2 = b.new_context()
    pg3 = ctx2.new_page()
    pg3.goto(f"{BASE}/flip", wait_until="load")
    pg3.wait_for_timeout(900)
    pg3.evaluate("() => { window.SkriblDraftStore.put = function(){ return new Promise(()=>{}); }; }")
    png4 = pg3.evaluate(MAKE_PNG_FILE)
    pg3.evaluate("""(bytes) => {
      const f = new File([new Uint8Array(bytes)], 'hang.png', { type: 'image/png' });
      const dt = new DataTransfer(); dt.items.add(f);
      const input = document.getElementById('imageInput');
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }""", png4)
    pg3.wait_for_timeout(2500)
    mid = pg3.evaluate("() => document.getElementById('autosaveStatusText').textContent")
    check("Flip: a hanging spill says 'Saving…' while it is genuinely pending",
          mid == "Saving…", f"{mid!r}")
    # Past SPILL_TIMEOUT_MS (12s from the dispatch). Polled with a deadline
    # well beyond it rather than slept to ~13.5s, which left about a second
    # and a half for the image decode on a loaded runner.
    _LATE = """() => { const el = document.getElementById('autosaveStatus');
        return { hidden: el.hidden,
                 text: document.getElementById('autosaveStatusText').textContent }; }"""
    try:
        pg3.wait_for_function(f"() => ({_LATE})().text === 'Saved without media'", timeout=20000)
    except PWTimeout:
        pass
    late = pg3.evaluate(_LATE)
    check("Flip: ...and does NOT sit there forever",
          late["text"] == "Saved without media" and late["hidden"] is False,
          f"{late} — a write that has not landed in twelve seconds is not one a "
          "reload can count on, and 'Saving…' never fades on its own")

    # ⚑ ASSERTION REVERSED, v238, FLAGGED — and it is MY OWN
    # assertion from v235 that is being reversed, on a decision taken deliberately, not a
    # ratchet raised to fit a commit.
    #
    # v235 read the pending record as "a memo about a PAST loss, not a property
    # of this save", and asserted the pill stays green. That framing does not
    # survive: the record means the session is missing media it expects, right
    # now, and v235's own change made a restored session say "Saved" with the
    # track gone. verify_amber has been failing on main ever since.
    #
    # What was actually wrong with the v229 amber was never that it was untrue.
    # It was that it went NOWHERE — the only controls that could resolve it,
    # Re-add and Dismiss, sat 0x0 inside a shut drawer with nothing pointing at
    # them. v238 makes the pill that route, so the warning is true AND has an
    # exit, and dismissing the record ends the amber because it ends the
    # situation. verify_amber owns the route; this owns the status.
    #
    # THE SECOND CHECK BELOW IS UNCHANGED and is the one that still constrains
    # the design either way: whatever the pill says, the record must survive, or
    # the recovery goes with it.
    pg4 = ctx2.new_page()
    pg4.goto(f"{BASE}/flip", wait_until="load")
    pg4.wait_for_timeout(900)
    pg4.evaluate("""() => { pendingPhotoMeta = { fit:'cover', opacity:1, blur:0,
        zoom:1, offX:.5, offY:.5, enabled:true, name:'gone.jpg' }; }""")
    # A REAL stroke on Flip's canvas. DRAW_STROKE targets Pad's #canvas, so on
    # Flip it draws nothing, no save is scheduled, and the pill reports whatever
    # it happened to be showing — which passed as "Saving…" and told us nothing.
    _pb = pg4.locator("#pad").bounding_box()
    _px, _py = _pb["x"] + _pb["width"] / 2, _pb["y"] + _pb["height"] / 2
    pg4.mouse.move(_px - 50, _py)
    pg4.mouse.down()
    pg4.mouse.move(_px + 50, _py)
    pg4.mouse.up()
    pg4.wait_for_timeout(2500)
    stale = pg4.evaluate("() => document.getElementById('autosaveStatusText').textContent")
    check("Flip: a save with media still MISSING says so, and offers the way back",
          stale == "Media missing" and pg4.evaluate("() => " + """(() => { const b = document.getElementById('autosaveStatusReadd'); if (!b || b.hidden || b.textContent !== 'Re-add') return false; const r = b.getBoundingClientRect(); if (r.width < 30) return false; const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); let op = 1; for (let a = b; a; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity); return !!hit && (hit === b || b.contains(hit)) && op > 0.5; })()"""),
          f"{stale!r} with a pending record standing — a session that cannot "
          "produce the file it says it has is not 'Saved', and the wording has "
          "to carry the action or the amber is the dead end that got it removed")
    check("Flip: ...and the record itself is kept, so re-adding still works",
          pg4.evaluate("() => !!pendingPhotoMeta") is True,
          "scoping the pill must not throw away the recovery affordance")
    ctx2.close()
    ctx.close()

    # ---------- 7. the restore prompt must not cover the tools ---------------
    print("\nBANNER — the restore prompt sits clear of the toolbar")
    # The banner is position:fixed at the bottom of the viewport, and so is the
    # toolbar — on every width, not only on a phone. At 1280x900 it landed on
    # Eraser, Shape, colour, Undo and Redo and stayed there until the person
    # chose (v287 audit SK-BUG-007). A prompt that hides the tools reads as an
    # interruption, and Restore is the answer most people want. Measured as
    # rectangle overlap between the banner and each visible toolbar button,
    # because a bottom offset that clears one viewport is exactly what the old
    # phone-only rule proved insufficient.
    BANNER_VS_TOOLS = """() => {
      const b = document.getElementById('restoreBanner');
      if (!b || b.hidden) return null;
      const br = b.getBoundingClientRect();
      const hit = [];
      for (const el of document.querySelectorAll('#toolBar button')) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        const w = Math.min(br.right, r.right) - Math.max(br.left, r.left);
        const h = Math.min(br.bottom, r.bottom) - Math.max(br.top, r.top);
        if (w > 0 && h > 0) hit.push((el.id || el.className) + ' ' + Math.round(w) + 'x' + Math.round(h));
      }
      return hit;
    }"""
    # v294 (audit finding 5): there is no banner to overlap anything. The
    # measurement above is kept as the record of why the banner had to move,
    # and the pin is what replaced it: the drawing is simply back, at both
    # widths, with nothing asking.
    for label, vp in (("desktop 1280x900", {"width": 1280, "height": 900}),
                      ("phone 390x844", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp)
        pg = ctx.new_page()
        pg.goto(f"{BASE}/", wait_until="load")
        pg.wait_for_timeout(800)
        pg.evaluate(DRAW_STROKE)
        pg.wait_for_timeout(1600)          # past the 1.2s debounce: a real write
        pg.reload(wait_until="load")
        pg.wait_for_timeout(700)
        hit = pg.evaluate(BANNER_VS_TOOLS)
        back = pg.evaluate("() => strokes.length")
        check(f"{label}: the drawing is back after the reload with nothing asking",
              hit is None and back >= 1, f"banner={hit} strokes={back}")
        ctx.close()

    # ---------- a long drawing --------------------------------------------
    print("\nLONG — a two-hour drawing autosaves, packed, and comes back whole")
    # v322 plan, step 1. Even written by the rule (lib/pointwrite.js) a point
    # is ~64 characters, so a two-hour drawing (170,717 points at the pace
    # measured) is eleven million: past the origin's whole localStorage, and
    # the pill said "Storage full -- not saved" for the rest of the session.
    # lib/pointpack.js keeps it in 0.69 million. The drawing is generated in
    # the page from a fixed seed, shaped like a pointer's points (long doubles,
    # whole milliseconds), loaded the way a draft loads, and generated again
    # after the reload to compare point for point against the rule.
    GEN = """(n) => { let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
      const pts = [], groups = []; let t = 0; const cols = ['#7c5cff', '#1d1a2b', '#1d1a2b', '#ff7a59'];
      while (pts.length < n) {
        const m = 15 + Math.floor(rnd() * 286); let x = 60 + rnd() * 824, y = 60 + rnd() * 600;
        let ang = rnd() * 6.283; const curv = (rnd() - 0.5) * 0.12, step = 3 + rnd() * 5;
        const w = [2, 3, 4, 6, 10][Math.floor(rnd() * 5)], col = cols[Math.floor(rnd() * 4)], er = rnd() < 0.05;
        let k = 0;
        for (let i = 0; i < m && pts.length < n; i++, k++) {
          const f = i / (m - 1), sc = 1.0000000123456789;
          const q = { x: x * sc, y: y * sc, color: col, size: (w * (0.35 + 0.65 * Math.sin(Math.PI * f)) + 0.3) * sc,
                      t: Math.round(t), erase: er };
          if (i === 0) q.start = true;
          pts.push(q); ang += curv;
          x = Math.min(939, Math.max(5, x + Math.cos(ang) * step)); y = Math.min(715, Math.max(5, y + Math.sin(ang) * step));
          t += 1000 / 55;
        }
        groups.push(k);
        const r = rnd(); t += r < 0.6 ? 150 + rnd() * 650 : r < 0.9 ? 1000 + rnd() * 3000 : 8000 + rnd() * 32000;
      }
      return { pts, groups }; }"""
    LOAD = """(n) => { const d = (""" + GEN + """)(n);
      restoreAutosave({ version: 1, strokes: d.pts, strokeGroups: d.groups, background: { color: '#f6f2ea' } });
      const durable = flushPadDraft();
      const raw = localStorage.getItem('skribl_autosave_v1') || '', rec = raw ? JSON.parse(raw) : null;
      const pill = document.getElementById('autosaveStatusText');
      return { n: d.pts.length, durable, chars: raw.length, keys: rec ? Object.keys(rec) : [],
               pill: pill ? pill.textContent : null }; }"""
    SAME = """(n) => { const d = (""" + GEN + """)(n), want = d.pts.map(SkriblPointWrite.point);
      const sig = (q) => [q.x, q.y, q.size, q.t, q.color, q.start === true, q.erase === true].join(',');
      let off = 0, first = null;
      for (let i = 0; i < Math.max(want.length, strokes.length); i++) {
        const a = want[i] ? sig(want[i]) : null, b = strokes[i] ? sig(strokes[i]) : null;
        if (a !== b) { off++; if (!first) first = { i, want: a, got: b }; } }
      return { n: strokes.length, off, first, groups: JSON.stringify(strokeGroups) === JSON.stringify(d.groups),
               undo: !document.getElementById('undoBtn').disabled }; }"""
    for _n, _label, _packed in ((170717, "two hours (170,717 points)", True),
                                (2000, "a short drawing (2,000 points)", False)):
        ctx = b.new_context()
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{BASE}/", wait_until="load")
        pg.wait_for_timeout(800)
        made = pg.evaluate(LOAD, _n)
        if _packed:
            check(f"{_label}: it autosaves, and the pill says so",
                  made["durable"] and "full" not in (made["pill"] or "").lower() and made["chars"] > 0,
                  f"durable={made['durable']} pill={made['pill']!r} stored {made['chars']:,} chars")
            check(f"{_label}: ...packed, in under a million characters of the origin's ~five",
                  "packed" in made["keys"] and "strokes" not in made["keys"] and made["chars"] < 1_000_000,
                  f"keys={made['keys']} chars={made['chars']:,}")
        else:
            # Under the threshold the draft is the plain JSON every reader and
            # suite has always read, key for key and in the same order -- with
            # the canvas's size, the one key added since (SHAPE, below).
            check(f"{_label}: stays the plain draft, key for key",
                  made["keys"] == ["version", "writerId", "savedAt", "baseSnapshot", "strokes", "strokeGroups",
                                   "redoStrokes", "redoStrokeGroups", "canvasSize", "background", "photoMeta",
                                   "musicMeta"],
                  str(made["keys"]))
        pg.reload(wait_until="load")
        pg.wait_for_timeout(1200)
        same = pg.evaluate(SAME, _n)
        check(f"{_label}: after a reload every point is back, by the rule, in its strokes",
              same["n"] == _n and same["off"] == 0 and same["groups"],
              f"{same['n']:,} of {_n:,} back, {same['off']} off, groups match {same['groups']}, first {same['first']}")
        check(f"{_label}: ...and it undoes, as a drawing kept this session does", same["undo"], str(same))
        check(f"{_label}: no page errors", not errors, "; ".join(errors[:2]))
        ctx.close()

    # Undone strokes are part of the draft (they come back as redo): packed too.
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(LOAD, 60000)
    for _ in range(3):
        pg.click("#undoBtn")
    pg.wait_for_timeout(200)
    kept = pg.evaluate("""() => { const durable = flushPadDraft(), rec = JSON.parse(localStorage.getItem('skribl_autosave_v1'));
        return { durable, keys: Object.keys(rec), applied: strokeGroups.length }; }""")
    pg.reload(wait_until="load")
    pg.wait_for_timeout(1200)
    redo = pg.evaluate("""() => { const before = strokeGroups.length, can = !document.getElementById('redoBtn').disabled;
        for (let i = 0; i < 3; i++) document.getElementById('redoBtn').click();
        return { before, can, after: strokeGroups.length, points: strokes.length }; }""")
    check("forty-some minutes with three strokes undone: the undone strokes are packed and come back as redo",
          kept["durable"] and "redoPacked" in kept["keys"] and redo["can"]
          and redo["before"] == kept["applied"] and redo["after"] == kept["applied"] + 3 and redo["points"] == 60000,
          f"saved {kept}, after reload {redo}")
    ctx.close()

    # FLIP'S HALF (v322 plan, step 1, lib/pointpack.js shared). The same
    # generator's strokes, cut into pages at stroke boundaries, loaded the way
    # a saved draft opens (applyFlipDraftObject) and flushed. 120,000 points is
    # about 7.7 million characters as plain JSON: past the origin's whole
    # localStorage, so main says it could not save.
    FLIPGEN = """(n, pages) => { const d = (""" + GEN + """)(n);
      const frames = [], per = Math.ceil(n / pages); let at = 0, gi = 0;
      for (let p = 0; p < pages && gi < d.groups.length; p++) {
        const st = [], gr = [];
        while (gi < d.groups.length && (st.length < per || p === pages - 1)) {
          const g = d.groups[gi++]; for (let j = 0; j < g; j++) st.push(d.pts[at++]); gr.push(g); }
        frames.push({ strokes: st, strokeGroups: gr, background: '#f6f2ea' });
      }
      return frames; }"""
    FLIPLOAD = """([n, pages, photo]) => { const fr = (""" + FLIPGEN + """)(n, pages);
      const doc = { schemaVersion: 2, version: 2, playbackMode: 'flip', fps: 12, frames: fr };
      if (photo) { const c = document.createElement('canvas'); c.width = c.height = 8;
        const x = c.getContext('2d'); x.fillStyle = '#7c5cff'; x.fillRect(0, 0, 8, 8);
        doc.bgImage = c.toDataURL('image/png'); doc.photo = { name: 'swatch.png', fit: 'cover', opacity: 1 }; }
      applyFlipDraftObject(doc);
      flushFlipDraft();
      const raw = localStorage.getItem('skribl_flip_autosave_v1') || '', rec = raw ? JSON.parse(raw) : null;
      const pill = document.getElementById('autosaveStatusText');
      return { n: fr.reduce((k, f) => k + f.strokes.length, 0), pages: fr.length, chars: raw.length,
               packed: rec ? rec.frames.filter(f => f.packed).length : 0,
               plain: rec ? rec.frames.filter(f => Array.isArray(f.strokes)).length : 0,
               lite: !!(rec && rec.mediaInIdb), pill: pill ? pill.textContent : null }; }"""
    FLIPSAME = """([n, pages]) => { const want = (""" + FLIPGEN + """)(n, pages);
      const sig = (q) => [q.x, q.y, q.size, q.t, q.color, q.start === true, q.erase === true].join(',');
      let off = 0, first = null, pts = 0, groups = frames.length === want.length;
      for (let p = 0; p < Math.max(frames.length, want.length); p++) {
        const a = want[p] ? want[p].strokes.map(SkriblPointWrite.point) : [], b = frames[p] ? frames[p].strokes : [];
        pts += b.length;
        if (!want[p] || !frames[p] || JSON.stringify(want[p].strokeGroups) !== JSON.stringify(frames[p].strokeGroups)) groups = false;
        for (let i = 0; i < Math.max(a.length, b.length); i++) {
          const x = a[i] ? sig(a[i]) : null, y = b[i] ? sig(b[i]) : null;
          if (x !== y) { off++; if (!first) first = { p, i, want: x, got: y }; } } }
      return { pages: frames.length, pts, off, first, groups, photo: !!bgImage }; }"""
    for _n, _pages, _photo, _label in ((120000, 40, False, "Flip, a long animation (120,000 points on 39 pages)"),
                                       (60000, 12, True, "Flip, a long animation with a photo (60,000 points)"),
                                       (6000, 6, False, "Flip, a short animation (6,000 points)")):
        ctx = b.new_context()
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{BASE}/flip", wait_until="load")
        pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip")
        pg.wait_for_timeout(500)
        made = pg.evaluate(FLIPLOAD, [_n, _pages, _photo])
        if _photo:
            # The photo's bytes go to IndexedDB beside the packed record; the
            # reload waits for that write to land, as a person's would have.
            pg.wait_for_function("() => _mediaSpillState === 'durable'", timeout=8000)
        if _n >= 20000:
            check(f"{_label}: it autosaves, every page packed, in well under a million characters",
                  made["packed"] == made["pages"] and made["plain"] == 0 and 0 < made["chars"] < 1_000_000
                  and not any(w in (made["pill"] or "").lower() for w in ("fail", "full")) and made["lite"] == _photo,
                  f"{made}")
        else:
            check(f"{_label}: stays the plain record every reader has always read",
                  made["packed"] == 0 and made["plain"] == made["pages"], f"{made}")
        pg.reload(wait_until="load")
        pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip")
        if _photo:
            pg.wait_for_function("() => !!bgImage", timeout=5000)
        pg.wait_for_timeout(600)
        same = pg.evaluate(FLIPSAME, [_n, _pages])
        check(f"{_label}: after a reload every page and point is back, by the rule"
              + (", and the photo too" if _photo else ""),
              same["pages"] == made["pages"] and same["pts"] == _n and same["off"] == 0 and same["groups"]
              and same["photo"] == _photo,
              f"{same['pages']} pages, {same['pts']:,} of {_n:,} points, {same['off']} off, "
              f"groups match {same['groups']}, photo {same['photo']}, first {same['first']}")
        check(f"{_label}: no page errors", not errors, "; ".join(errors[:2]))
        ctx.close()

    print("\nSHAPE — a reload brings a drawing back on its own canvas, not the one the window suggests")
    # The owner, on a desk: a square drawing came back low and to the left, its
    # foot cut off. The Pad's autosave did not hold the canvas's size, so a
    # reload put the strokes on whatever preset the window suggested
    # (lib/canvassizes.js bestFor) -- square on one window, 4:3 on another,
    # which is why it happened only sometimes. A 9:16 drawing on a desk makes it
    # certain: no desk band suggests 9:16. Its one mark is the middle of its
    # canvas, so on its own canvas the middle pixel is ink and on any other it
    # is not. Flip's autosave has always held its size; it is driven the same
    # way so the two cannot drift. Loaded through each editor's own Load, and
    # left by a reload, whose pagehide flush is the save (FLUSH, above).
    SHAPE_W, SHAPE_H = 531, 944                          # lib/canvassizes.js 'tall'
    def _shape_payload(flip):
        mark = [{"x": SHAPE_W / 2 - 30 + i * 6, "y": SHAPE_H / 2, "color": "#7c5cff", "size": 48, "t": i * 40,
                 **({"start": True} if i == 0 else {})} for i in range(11)]
        frame = {"strokes": mark, "strokeGroups": [len(mark)], "background": {"color": "#f6f2ea"}}
        return json.dumps({"version": 2, "schemaVersion": 2, "playbackMode": "flip" if flip else "replay",
                           "fps": 8 if flip else None, "canvasSize": {"cssWidth": SHAPE_W, "cssHeight": SHAPE_H, "dpr": 1},
                           "frames": [frame, frame] if flip else [frame]}).encode()
    SHAPE_READ = """(flip) => { const c = document.getElementById(flip ? 'pad' : 'canvas');
        const px = c.getContext('2d').getImageData(Math.floor(c.width / 2), Math.floor(c.height / 2), 1, 1).data;
        const r = c.getBoundingClientRect();
        return { size: flip ? [CW, CH] : [authoredW, authoredH], shown: [Math.round(r.width), Math.round(r.height)],
                 ink: Math.abs(px[0] - 124) < 40 && Math.abs(px[1] - 92) < 40 && Math.abs(px[2] - 255) < 40 }; }"""
    for _route, _flip, _menu, _item in (("/skribl-pad", False, "#menuBtn", "#loadDraftItem"),
                                        ("/flip", True, "#moreBtn", "#miLoad")):
        ctx = b.new_context(viewport={"width": 1333, "height": 906})
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{BASE}{_route}", wait_until="load")
        pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        pg.reload(wait_until="load"); pg.wait_for_timeout(700)
        pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide()")
        _fresh = pg.evaluate(SHAPE_READ, _flip)["size"]
        pg.click(_menu); pg.wait_for_timeout(300)
        with pg.expect_file_chooser() as _fc:
            pg.click(_item)
        _fc.value.set_files({"name": "tall.skribl", "mimeType": "application/json", "buffer": _shape_payload(_flip)})
        pg.wait_for_timeout(1200)
        _open = pg.evaluate(SHAPE_READ, _flip)
        pg.reload(wait_until="load"); pg.wait_for_timeout(1500)
        _back = pg.evaluate(SHAPE_READ, _flip)
        _label = "Pad" if not _flip else "Flip"
        check(f"{_label} at 1333x906: a 9:16 drawing reloads on its own 9:16 canvas, its middle in the middle"
              " (this window would start a fresh one at another shape)",
              _fresh != [SHAPE_W, SHAPE_H] and _open["size"] == [SHAPE_W, SHAPE_H] and _open["ink"]
              and _back["size"] == [SHAPE_W, SHAPE_H] and _back["ink"]
              and abs(_back["shown"][0] / _back["shown"][1] - SHAPE_W / SHAPE_H) < 0.01,
              f"fresh {_fresh}; opened {_open}; after the reload {_back}")
        check(f"{_label}: no page errors", not errors, "; ".join(errors[:2]))
        ctx.close()

    print("\nNEARLY TOO LONG — a note at 90% and at the limit, after a save, twice at most")
    # The Pad plan, step 5 (the owner's pick A). Nothing said anything until
    # Post failed at the end of the work. Now, after a save that crossed 90% of
    # what a post can hold, the toast where "Draft restored" goes says how many
    # minutes more fit at THIS drawing's pace; after one that reached the
    # limit, that it is all still saved here -- and only if that save landed.
    # Each is said once, again only after falling back under it, never over a
    # restored drawing, and taps go through it to the canvas. Every toast is
    # recorded by wrapping showToast, so "said once" is counted, not guessed.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from skribl import validation as _V
    _CAP = _V.MAX_POINTS_PER_PAD
    _LIMIT_WORDS = "That’s as long as a post can hold. It’s all still saved here."
    # Only the note's own sentences are counted: Add take and its kin have toasts of their own.
    WATCH = """() => { window.__toasts = []; const real = window.showToast;
      window.showToast = function (m) { if (/fit in a post|a post can hold/.test(m)) window.__toasts.push(m);
        return real.apply(this, arguments); }; }"""
    LOADN = """(n) => { const d = (""" + GEN + """)(n);
      restoreAutosave({ version: 1, strokes: d.pts, strokeGroups: d.groups, background: { color: '#f6f2ea' } });
      flushPadDraft(); window.__toasts = []; return strokes.length; }"""
    PACE = """() => ({ n: strokes.length, g: strokeGroups.length, ms: SkriblReplayLine.drawnMs(strokes) })"""
    # COVERED IS A PAINT. A button counts only where it is drawn under the
    # toast: elementFromPoint at the middle of the overlap, which sees through
    # the toast because taps do. A closed drawer's Done and a hidden grid
    # button keep their boxes there and are not drawn (a rect is not a paint).
    TOAST = """() => { const t = document.querySelector('.toast'), r = t.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      const over = [...document.querySelectorAll('button')].filter(b => { const q = b.getBoundingClientRect();
        const x0 = Math.max(q.left, r.left), x1 = Math.min(q.right, r.right), y0 = Math.max(q.top, r.top), y1 = Math.min(q.bottom, r.bottom);
        if (x1 <= x0 || y1 <= y0) return false;
        const h = document.elementFromPoint((x0 + x1) / 2, (y0 + y1) / 2);
        return !!(h && (h === b || b.contains(h))); }).map(b => b.id || b.className);
      return { shown: !t.hidden && t.classList.contains('show'), text: t.textContent,
               through: getComputedStyle(t).pointerEvents === 'none' && !!hit && hit !== t && !t.contains(hit),
               over }; }"""

    def _stroke(pg, dx=0):
        # A restored drawing is a finished take: Add take carries on drawing it.
        if pg.is_visible("#addTakePill"):
            pg.click("#addTakePill"); pg.wait_for_timeout(250)
        bx = pg.locator("#canvas").bounding_box()
        pg.mouse.move(bx["x"] + 60 + dx, bx["y"] + 60); pg.mouse.down()
        pg.mouse.move(bx["x"] + 220 + dx, bx["y"] + 140, steps=24); pg.mouse.up()
        pg.wait_for_timeout(1900)        # the autosave's 1.2 s, and the note after it

    def _minutes(st):
        share = max(st["n"] / _CAP, st["g"] / _V.MAX_GROUPS_PER_PAD)
        n = round((1 - share) / share * st["ms"] / 60000)
        return f"About {n} more minutes will fit in a post." if n >= 2 else None

    ctx = b.new_context(viewport={"width": 402, "height": 874})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(WATCH)
    pg.evaluate(LOADN, int(_CAP * 0.9) - 8)
    _stroke(pg)
    _st, _t = pg.evaluate(PACE), pg.evaluate(TOAST)
    _want = _minutes(_st)
    check("crossing 90%: after the save, how many minutes more fit, at this drawing's pace",
          _want is not None and _t["shown"] and _t["text"] == _want and pg.evaluate("() => __toasts.length") == 1,
          f"want {_want!r}; toast {_t}; said {pg.evaluate('() => __toasts')}; {_st}")
    check("...where taps go through it, and over no button that is drawn",
          _t["text"] == _want and _t["through"] and not _t["over"], str(_t))
    _stroke(pg, 30)
    check("...and the next save, still past 90%, says nothing more",
          pg.evaluate("() => __toasts.length") == 1, str(pg.evaluate("() => __toasts")))
    pg.evaluate(LOADN, _CAP - 8)
    _stroke(pg)
    check("reaching the limit: that it is as long as a post can hold, and all still saved here",
          pg.evaluate("() => __toasts") == [_LIMIT_WORDS], str(pg.evaluate("() => __toasts")))
    pg.click("#undoBtn"); pg.wait_for_timeout(1900)
    pg.click("#redoBtn"); pg.wait_for_timeout(1900)
    check("...said again after an undo took it back under and a redo over",
          pg.evaluate("() => __toasts") == [_LIMIT_WORDS, _LIMIT_WORDS], str(pg.evaluate("() => __toasts")))
    # FROM THE FIRST PAINT: the restore saves as it boots, so a note it owed
    # nobody would be said before any wrapper could be installed. The toast's
    # own text is watched from the moment the page parses.
    pg.add_init_script("""(() => { window.__boot = [];
      document.addEventListener('DOMContentLoaded', () => { const t = document.querySelector('.toast'); if (!t) return;
        new MutationObserver(() => { if (/fit in a post|a post can hold/.test(t.textContent)) window.__boot.push(t.textContent); })
          .observe(t, { childList: true, characterData: true, subtree: true }); }); })()""")
    pg.reload(wait_until="load")
    pg.wait_for_timeout(2500)
    _boot = pg.evaluate("() => window.__boot")
    pg.evaluate(WATCH)
    _stroke(pg)
    check("a drawing restored at the limit is not told again, as it boots or on its next save",
          _boot == [] and pg.evaluate("() => __toasts") == [] and pg.evaluate("() => strokes.length") > _CAP,
          f"at boot {_boot}, after a stroke {pg.evaluate('() => __toasts')} at {pg.evaluate('() => strokes.length')} points")
    check("no page errors", not errors, "; ".join(errors[:2]))
    ctx.close()

    # A save that did NOT land never says "still saved here".
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.goto(f"{BASE}/", wait_until="load")
    pg.wait_for_timeout(800)
    pg.evaluate(WATCH)
    pg.evaluate(LOADN, _CAP - 8)
    pg.evaluate("""() => { Storage.prototype.setItem = function () {
      throw new DOMException('full', 'QuotaExceededError'); }; }""")
    _stroke(pg)
    check("...and when the save failed, the limit is said without promising it is saved",
          pg.evaluate("() => __toasts") == ["That’s as long as a post can hold."],
          str(pg.evaluate("() => __toasts")))
    ctx.close()

    # Flip: the same note, counting pages, in the chip where its "Draft restored" goes.
    ctx = b.new_context(viewport={"width": 402, "height": 874})
    pg = ctx.new_page()
    pg.goto(f"{BASE}/flip", wait_until="load")
    pg.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip")
    pg.wait_for_timeout(500)
    pg.evaluate("""() => { window.__chips = []; const real = window.chip;
      window.chip = function (m) { window.__chips.push(m); return real.apply(this, arguments); };
      const B = window.SkriblPointBudget;
      while (frames.length < B.MAX_FRAMES * 0.9) frames.push({ strokes: [], strokeGroups: [], hold: 1 }); render(); }""")
    _bx = pg.locator("#pad").bounding_box()
    pg.mouse.move(_bx["x"] + 60, _bx["y"] + 60); pg.mouse.down()
    pg.mouse.move(_bx["x"] + 160, _bx["y"] + 130, steps=12); pg.mouse.up()
    pg.wait_for_timeout(1500)
    _fc = pg.evaluate("""() => ({ said: window.__chips, shown: document.getElementById('flipChip').classList.contains('show'),
                                  pages: frames.length }) """)
    check("Flip at 90% of its pages: how many more pages fit, in its chip",
          _fc["said"] == ["About 20 more pages will fit in a post."] and _fc["shown"], str(_fc))

    b.close()

# ---------------------------------------------------------------------------
print("\nTWO TABS — no save replaces another tab's drawing; the next visit offers it")
# SK-AUD-006, the owner's pick T1. Two tabs of one editor shared one slot and
# the last writer won: A's drawing was gone once A closed. Now a save moves
# another tab's drawing aside (<key>:waiting:<writer>) instead of writing over
# it, a tab writing again takes its own back, and the next visit opens the
# newest and offers the other: Open it (this tab's waits in its place, the
# page reloads into the other) or Keep for later (it becomes a draft). A tab
# still open answers a roll call, so its drawing is not offered elsewhere.
def _ink(pg, sel, dx):
    bx = pg.locator(sel).bounding_box()
    x, y = bx["x"] + bx["width"] / 2 + dx, bx["y"] + bx["height"] / 2
    pg.mouse.move(x, y); pg.mouse.down()
    for k in range(14):
        pg.mouse.move(x + k * 6, y + (k % 5) * 5)
    pg.mouse.up(); pg.wait_for_timeout(250)
_BAR = """() => { const b = document.querySelector('.othertab');
    if (!b || b.hidden) return null; const r = b.getBoundingClientRect();
    const at = document.elementFromPoint(r.left + 20, r.top + 16);
    const btns = [...b.querySelectorAll('button')].map(x => { const q = x.getBoundingClientRect();
      return [x.textContent || x.getAttribute('aria-label'), Math.round(q.width), Math.round(q.height), q.left >= 0 && q.right <= innerWidth]; });
    return { painted: !!(at && b.contains(at)), words: b.querySelector('.othertab-words').textContent, btns }; }"""
def _n(text):
    """Which drawing an autosave's text holds: its point count and where its
    first point is, never the save's timestamp (a flush rewrites that)."""
    try:
        d = json.loads(text or "null")
    except ValueError:
        return None
    if not d:
        return None
    pts = [p for f in d["frames"] for p in (f.get("strokes") or [])] if "frames" in d else (d.get("strokes") or [])
    return (len(pts), round(pts[0]["x"]) if pts else None)
_WAIT = "(k) => Object.keys(localStorage).filter(x => x.startsWith(k + ':waiting:')).sort().map(x => [x.split(':waiting:')[1], JSON.parse(localStorage.getItem(x)).data])"
with sync_playwright() as _p2:
    _b2 = _p2.chromium.launch()
    for _ed, _path, _sel, _key, _boot, _ink_js in (
            ("Pad", "/skribl-pad", "#canvas", "skribl_autosave_v1", "pad", "() => strokes.length"),
            ("Flip", "/flip", "#pad", "skribl_flip_autosave_v1", "flip", "() => frames.reduce((n, f) => n + f.strokes.length, 0)")):
        def _open(ctx, url=None, w=1100):
            pg = ctx.new_page()
            pg.set_viewport_size({"width": w, "height": 860})
            pg.goto(BASE + (url or _path), wait_until="load")
            pg.wait_for_function(f"() => window.__skriblBoot && window.__skriblBoot.{_boot}")
            pg.evaluate("() => { if (window.SkriblHints) SkriblHints.hide(); }")
            return pg
        _ctx = _b2.new_context()
        _a = _open(_ctx); _b = _open(_ctx)                 # both empty at load
        _ink(_a, _sel, -60); _a.wait_for_timeout(1800)     # A's autosave lands
        _mine = _a.evaluate(f"() => localStorage.getItem('{_key}')")
        _ink(_b, _sel, 60); _b.wait_for_timeout(1800)      # B writes: A's moves aside
        _theirs = _a.evaluate(f"() => localStorage.getItem('{_key}')")
        _w1 = _a.evaluate(_WAIT, _key)
        check(f"{_ed}: tab B's save did not replace tab A's drawing: A's waits beside the slot, whole",
              bool(_mine) and bool(_theirs) and _n(_theirs) != _n(_mine) and [_n(v) for _, v in _w1] == [_n(_mine)],
              f"waiting {[(k, len(v or '')) for k, v in _w1]}")
        _c0 = _open(_ctx); _c0.wait_for_timeout(700)
        check(f"{_ed}: a third tab does not offer the drawing a tab still open is holding (the roll call)",
              _c0.evaluate(_BAR) is None, str(_c0.evaluate(_BAR)))
        _c0.close()
        _ink(_a, _sel, -20); _a.wait_for_timeout(1800)     # A writes again
        _w2 = _a.evaluate(_WAIT, _key)
        _slot2 = _a.evaluate(f"() => localStorage.getItem('{_key}')")
        check(f"{_ed}: when A saves again it takes the slot back, B's drawing waits instead, and A's old copy goes",
              len(_w2) == 1 and _n(_w2[0][1]) == _n(_theirs) and _n(_slot2) not in (_n(_mine), _n(_theirs)),
              f"waiting {[(k, _n(v)) for k, v in _w2]}, slot {_n(_slot2)}")
        _bstrokes = _b.evaluate(_ink_js)
        _a.close(); _b.close()
        # The next visit: the newest opens, the other is offered.
        _c = _open(_ctx, w=402); _c.wait_for_timeout(700)
        _bar = _c.evaluate(_BAR)
        check(f"{_ed}: the next visit opens the newest drawing and offers the waiting one, painted, at 402px",
              bool(_bar) and _bar["painted"] and "waiting" in _bar["words"]
              and _n(_c.evaluate(f"() => localStorage.getItem('{_key}')")) == _n(_slot2), str(_bar))
        check(f"{_ed}: ...its buttons say Open it, Keep for later and Not now, each a 44px tap on screen",
              bool(_bar) and [b[0] for b in _bar["btns"]] == ["Open it", "Keep for later", "Not now"]
              and all(b[1] >= 44 and b[2] >= 44 and b[3] for b in _bar["btns"]), str(_bar and _bar["btns"]))
        if _bar:
            _c.click(".othertab-later"); _c.wait_for_timeout(900)
        _kept = _c.evaluate("() => window.SkriblSavedDrafts.list()")
        _k = [d for d in (_kept or []) if (d.get("title") or "").startswith("From another tab")]
        check(f"{_ed}: Keep for later files it under Drafts and it stops waiting",
              len(_k) == 1 and not _c.evaluate(_WAIT, _key) and _c.evaluate(_BAR) is None,
              f"drafts {[d.get('title') for d in (_kept or [])]}, waiting {len(_c.evaluate(_WAIT, _key))}")
        if _k:
            # The kept draft opens on a blank editor with B's strokes.
            # (Closed first: its pagehide flush would put its own drawing back.)
            _c.close()
            _e = _ctx.new_page(); _e.goto(BASE + "/api/skribls")
            _e.evaluate(f"() => {{ localStorage.removeItem('{_key}'); localStorage.removeItem('{_key}:owner'); }}")
            _e.close()
            _d = _open(_ctx, f"{_path}?draft={_k[0]['id']}"); _d.wait_for_timeout(900)
            check(f"{_ed}: ...and that draft opens with the other tab's drawing",
                  _d.evaluate(_ink_js) == _bstrokes and _bstrokes > 0, f"{_d.evaluate(_ink_js)} vs {_bstrokes}")
            _d.close()
        else:
            _c.close()
        _ctx.close()

        # OPEN IT: this tab's drawing waits in the other's place, and the page
        # reloads into the other one.
        _ctx = _b2.new_context()
        _a = _open(_ctx); _b = _open(_ctx)
        _ink(_a, _sel, -60); _a.wait_for_timeout(1800)
        _ink(_b, _sel, 60); _ink(_b, _sel, 20); _b.wait_for_timeout(1800)
        _astrokes, _bstrokes = _a.evaluate(_ink_js), _b.evaluate(_ink_js)
        _a.close(); _b.close()
        _c = _open(_ctx); _c.wait_for_timeout(700)
        _before = _c.evaluate(_ink_js)
        if _c.evaluate(_BAR):
            with _c.expect_navigation():
                _c.click(".othertab-open")
            _c.wait_for_function(f"() => window.__skriblBoot && window.__skriblBoot.{_boot}")
            _c.wait_for_timeout(800)
        _after, _bar2 = _c.evaluate(_ink_js), _c.evaluate(_BAR)
        _w3 = _c.evaluate(_WAIT, _key)
        check(f"{_ed}: Open it reloads into the waiting drawing, and the one it replaced waits in its place",
              _before == _bstrokes and _after == _astrokes and _astrokes != _bstrokes
              and len(_w3) == 1 and _w3[0][0].startswith("kept-") and bool(_bar2),
              f"before {_before} after {_after} (A {_astrokes}, B {_bstrokes}); waiting {[k for k, _ in _w3]}")
        _ctx.close()

    # A LONG DRAWING WAITING IN ANOTHER TAB'S PLACE is packed text (v322 plan,
    # step 1), and Keep for later is the second reader of it: it has to unpack
    # too, or the draft it files is empty. The text is the editor's own
    # serializeAutosave() of a long drawing, filed as another tab's waiting
    # drawing; the page that made it leaves for a page with no editor first, so
    # its own leaving flush lands where it can be cleared.
    _ctx = _b2.new_context()
    _g = _ctx.new_page(); _g.goto(BASE + "/skribl-pad", wait_until="load"); _g.wait_for_timeout(800)
    _made = _g.evaluate("""(n) => { const d = (""" + GEN + """)(n);
        restoreAutosave({ version: 1, strokes: d.pts, strokeGroups: d.groups, background: { color: '#f6f2ea' } });
        window.__longText = JSON.stringify(serializeAutosave());
        return { packed: !!JSON.parse(window.__longText).packed, chars: window.__longText.length }; }""", 60000)
    _text = _g.evaluate("() => window.__longText")
    _g.goto(BASE + "/api/skribls")
    _g.evaluate("""(t) => { localStorage.removeItem('skribl_autosave_v1'); localStorage.removeItem('skribl_autosave_v1:owner');
        localStorage.setItem('skribl_autosave_v1:waiting:longtab', JSON.stringify({ w: 'longtab', at: Date.now(), data: t })); }""", _text)
    _g.close()
    _c = _ctx.new_page(); _c.set_viewport_size({"width": 1100, "height": 860})
    _c.goto(BASE + "/skribl-pad", wait_until="load")
    _c.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad"); _c.wait_for_timeout(700)
    _offered = _c.evaluate(_BAR)
    if _offered:
        _c.click(".othertab-later"); _c.wait_for_timeout(1500)
    _k = [d for d in (_c.evaluate("() => window.SkriblSavedDrafts.list()") or [])
          if (d.get("title") or "").startswith("From another tab")]
    _c.close()
    _same = None
    if _k:
        _d = _ctx.new_page(); _d.goto(f"{BASE}/skribl-pad?draft={_k[0]['id']}", wait_until="load")
        _d.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.pad"); _d.wait_for_timeout(1200)
        _same = _d.evaluate(SAME, 60000)
        _d.close()
    check("a long drawing waiting in another tab's place: Keep for later files the whole drawing, every point back",
          _made["packed"] and bool(_offered) and len(_k) == 1 and bool(_same)
          and _same["n"] == 60000 and _same["off"] == 0 and _same["groups"],
          f"made {_made}, offered {bool(_offered)}, kept {len(_k)}, opened "
          + (f"{_same['n']:,} points, {_same['off']} off, groups {_same['groups']}" if _same else "nothing"))
    _ctx.close()

    # And Flip's: the waiting text is Flip's own serializer at its
    # localStorage setting, so a long animation is packed pages.
    _ctx = _b2.new_context()
    _g = _ctx.new_page(); _g.goto(BASE + "/flip", wait_until="load")
    _g.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip"); _g.wait_for_timeout(500)
    _made = _g.evaluate("""([n, pages]) => { const fr = (""" + FLIPGEN + """)(n, pages);
        applyFlipDraftObject({ schemaVersion: 2, version: 2, playbackMode: 'flip', fps: 12, frames: fr });
        window.__longText = JSON.stringify(serializeFlip({ media: false, recipes: true, pack: true }));
        const d = JSON.parse(window.__longText);
        return { packed: d.frames.filter(f => f.packed).length, pages: d.frames.length, chars: window.__longText.length }; }""",
        [60000, 12])
    _text = _g.evaluate("() => window.__longText")
    _g.goto(BASE + "/api/skribls")
    _g.evaluate("""(t) => { localStorage.removeItem('skribl_flip_autosave_v1'); localStorage.removeItem('skribl_flip_autosave_v1:owner');
        localStorage.setItem('skribl_flip_autosave_v1:waiting:longtab', JSON.stringify({ w: 'longtab', at: Date.now(), data: t })); }""", _text)
    _g.close()
    _c = _ctx.new_page(); _c.set_viewport_size({"width": 1100, "height": 860})
    _c.goto(BASE + "/flip", wait_until="load")
    _c.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip"); _c.wait_for_timeout(700)
    _offered = _c.evaluate(_BAR)
    if _offered:
        _c.click(".othertab-later"); _c.wait_for_timeout(1500)
    _k = [d for d in (_c.evaluate("() => window.SkriblSavedDrafts.list()") or [])
          if (d.get("title") or "").startswith("From another tab")]
    _c.close()
    _same = None
    if _k:
        _d = _ctx.new_page(); _d.goto(f"{BASE}/flip?draft={_k[0]['id']}", wait_until="load")
        _d.wait_for_function("() => window.__skriblBoot && window.__skriblBoot.flip"); _d.wait_for_timeout(1200)
        _same = _d.evaluate(FLIPSAME, [60000, 12])
        _d.close()
    check("Flip, a long animation waiting in another tab's place: Keep for later files every page, every point back",
          _made["packed"] == _made["pages"] == 12 and bool(_offered) and len(_k) == 1 and bool(_same)
          and _same["pts"] == 60000 and _same["off"] == 0 and _same["groups"],
          f"made {_made}, offered {bool(_offered)}, kept {len(_k)}, opened "
          + (f"{_same['pts']:,} points on {_same['pages']} pages, {_same['off']} off, groups {_same['groups']}" if _same else "nothing"))
    _ctx.close()
    _b2.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
