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
import sys, time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

BASE = "http://127.0.0.1:5001"
ROOT = Path(__file__).resolve().parents[1]

results = []
def check(name, ok, detail=""):
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

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
  const opts = (x, y) => ({ bubbles: true, clientX: r.left + x, clientY: r.top + y, button: 0 });
  cv.dispatchEvent(new MouseEvent('mousedown', opts(30, 30)));
  cv.dispatchEvent(new MouseEvent('mousemove', opts(90, 70)));
  cv.dispatchEvent(new MouseEvent('mouseup',   opts(90, 70)));
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
    banner = pg.evaluate("() => { const el = document.getElementById('restoreBanner');"
                         " return el ? !el.hidden : null; }")
    check("the restore banner appears after an instant reload",
          banner is True, f"restoreBanner visible={banner} — the pagehide flush "
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
    pg.wait_for_timeout(600)
    pg.evaluate("() => document.getElementById('restoreConfirm').click()")
    pg.wait_for_timeout(2500)   # IDB get + DataTransfer re-add + image decode
    photo = pg.evaluate("() => { const img = document.getElementById('photoBgImg');"
                        " return img ? { shown: img.style.display !== 'none',"
                        " hasSrc: !!img.src && img.src.length > 40, name: img._fileName || null } : null; }")
    check("after restore, the photo is BACK — bytes, not a re-add card",
          bool(photo and photo["shown"] and photo["hasSrc"] and photo["name"] == "pin.png"),
          str(photo))
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
    pg3.wait_for_timeout(11000)          # past SPILL_TIMEOUT_MS
    late = pg3.evaluate("""() => { const el = document.getElementById('autosaveStatus');
        return { hidden: el.hidden,
                 text: document.getElementById('autosaveStatusText').textContent }; }""")
    check("Flip: ...and does NOT sit there forever",
          late["text"] == "Saved without media" and late["hidden"] is False,
          f"{late} — a write that has not landed in twelve seconds is not one a "
          "reload can count on, and 'Saving…' never fades on its own")

    # ⚑ ASSERTION REVERSED, v238, FLAGGED FOR THE OWNER — and it is MY OWN
    # assertion from v235 that is being reversed, on the owner's decision, not a
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
          stale == "Media missing — tap to re-add",
          f"{stale!r} with a pending record standing — a session that cannot "
          "produce the file it says it has is not 'Saved', and the wording has "
          "to carry the action or the amber is the dead end that got it removed")
    check("Flip: ...and the record itself is kept, so re-adding still works",
          pg4.evaluate("() => !!pendingPhotoMeta") is True,
          "scoping the pill must not throw away the recovery affordance")
    ctx2.close()
    ctx.close()

    b.close()

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
