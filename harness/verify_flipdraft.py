"""Flip's draft: strokes in localStorage, media bytes in IndexedDB.

THE BUG THIS CLOSES was reported by the owner as "autosave is failing on pad".
It was not Pad's fault. localStorage is capped at roughly 5 MB PER ORIGIN and
both editors share it, and Flip was writing its media into that budget as base64
data URLs — inflated 4/3 by the encoding, so a 30-second WAV is ~6.7 MB on its
own. One Flip draft measured 2.7 MB of the shared 5 MB, and Pad's autosave was
what fell over.

The spill to IndexedDB existed before this, but only as an EMERGENCY path,
reached after localStorage had already refused the write. That made a 5 MB quota
the thing standing between a user and their drawing. It is the normal path now:
strokes and media METADATA to localStorage (small, synchronous, fast to restore),
media BYTES to IndexedDB, whose quota is measured in hundreds of MB. The merge
on the restore side was written for the quota case and was correct all along —
what changed is that it is reached on purpose rather than after a failure.

The measurement that matters, and the first assertion below: the same draft that
put 1.68 MB into localStorage now puts about 3.5 KB there.

BACKWARD COMPATIBILITY IS NOT OPTIONAL. Anyone with a draft saved before this
has the old full payload sitting in localStorage, media inline. That must still
restore, so the last section plants one by hand and reloads.
"""
import json
import sys

BASE = "http://127.0.0.1:5001"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# ~1.2 MB and ~0.5 MB once base64'd: together they are what used to fill the
# budget. Deliberately not real media — this suite is about where bytes go, and
# a decodable file would only add flakiness.
FAKE_AUDIO = "data:audio/wav;base64," + ("QUJD" * 300000)
FAKE_IMAGE = "data:image/png;base64," + ("QUJD" * 120000)

DRAW_AND_SAVE = """(m) => {
  frames = [newFrame()]; idx = 0;
  const f = frames[0];
  for (let i = 0; i < 40; i++)
    f.strokes.push({x:10+i*4, y:50, color:'#fff', size:6, t:i, erase:false, start:i===0});
  f.strokeGroups = [40];
  if (m) { musicData = m.a; musicName = 'track.wav'; bgImage = m.i; imageName = 'pic.png'; }
  saveNow();
}"""

LOCAL_STATE = """() => {
  const raw = localStorage.getItem('skribl_flip_autosave_v1') || '';
  const d = raw ? JSON.parse(raw) : null;
  return {bytes: raw.length, mediaOmitted: !!(d && d.mediaOmitted),
          mediaInIdb: !!(d && d.mediaInIdb),
          inlineBg: !!(d && d.bgImage), inlineMusic: !!(d && d.music),
          photoName: d && d.photo && d.photo.name,
          musicName: d && d.musicMeta && d.musicMeta.name,
          spill: typeof _mediaSpillState !== 'undefined' ? _mediaSpillState : null,
          strokes: d && d.frames && d.frames[0] ? d.frames[0].strokes.length : 0};
}"""

RESTORED = """() => ({
  strokes: frames[0].strokes.length,
  musicBack: typeof musicData === 'string' && musicData.slice(0,10) === 'data:audio',
  bgBack: typeof bgImage === 'string' && bgImage.slice(0,10) === 'data:image',
  musicLen: musicData ? musicData.length : 0,
  bgLen: bgImage ? bgImage.length : 0,
  pendingMusic: !!pendingMusicMeta, pendingPhoto: !!pendingPhotoMeta,
  musicName: musicName, imageName: imageName,
})"""


def clean(page):
    """Empty the DOCUMENT as well as the two stores.

    Clearing storage alone is not enough and it cost this suite a debugging
    round: the live page still holds musicData, bgImage and frames in memory,
    and the next reload saves them on the way out — so the record is written
    back after the clear and restored by the very reload meant to be rid of it.
    The legacy section then found 40 strokes and pic.png where it had planted
    two strokes and old.png, and reported a backward-compatibility failure that
    did not exist. (Third time this trap has been hit in this codebase; see
    fresh() in verify_select.py.)"""
    page.goto(BASE + "/flip", wait_until="load")
    page.wait_for_timeout(400)
    page.evaluate("""() => {
      frames = [newFrame()]; idx = 0;
      musicData = null; musicName = ''; bgImage = null; bgImageObj = null; imageName = '';
      pendingMusicMeta = null; pendingPhotoMeta = null;
      try { buildStrip(); render(); } catch (e) {}
      for (const k of Object.keys(localStorage))
        if (k.indexOf('skribl') === 0) localStorage.removeItem(k);
    }""")
    page.evaluate("() => window.SkriblDraftStore "
                  "? window.SkriblDraftStore.del('flip:draft').catch(()=>{}) : null")
    page.wait_for_timeout(300)
    left = page.evaluate("() => (localStorage.getItem('skribl_flip_autosave_v1') || '').length")
    if left:
        raise SystemExit(f"clean() left {left} B of draft behind — every "
                         f"assertion after this would be measuring the wrong record")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    print("DRAFT — media bytes stay out of localStorage")
    clean(page)
    check("IndexedDB is available to this editor",
          page.evaluate("() => !!window.SkriblDraftStore"),
          "lib/draftstore.js is where the bytes go; without it Flip falls back "
          "to the old behaviour and the quota is in play again")
    page.evaluate(DRAW_AND_SAVE, {"a": FAKE_AUDIO, "i": FAKE_IMAGE})
    page.wait_for_timeout(1400)
    st = page.evaluate(LOCAL_STATE)
    # 1.68 MB before this change. The threshold is generous on purpose: what is
    # being asserted is an order of magnitude, not a byte count that would have
    # to be edited every time a stroke field is added.
    check("localStorage holds kilobytes, not megabytes",
          st["bytes"] < 50_000,
          f"{st['bytes']:,} B — the same draft used to write 1,683,508 B here")
    check("no media bytes inline in the local record",
          not st["inlineBg"] and not st["inlineMusic"])
    check("the local record says where the bytes went",
          st["mediaOmitted"] and st["mediaInIdb"], str(st))
    check("and keeps the metadata the restore needs",
          st["photoName"] == "pic.png" and st["musicName"] == "track.wav", str(st))
    check("the strokes are still in the local record",
          st["strokes"] == 40,
          "the drawing is what has to survive synchronously; only the bytes moved")
    check("the spill settled as durable", st["spill"] == "durable", str(st["spill"]))

    rec = page.evaluate("() => window.SkriblDraftStore.get('flip:draft')"
                        ".then(r => ({present: !!r, bytes: r && r.json ? r.json.length : 0,"
                        " hasBg: !!(r && JSON.parse(r.json).bgImage),"
                        " hasMusic: !!(r && JSON.parse(r.json).music),"
                        " claimsOmitted: !!(r && JSON.parse(r.json).mediaOmitted)}))")
    check("IndexedDB has the full record", rec["present"] and rec["bytes"] > 1_000_000,
          f"{rec['bytes']:,} B")
    check("with both media present", rec["hasBg"] and rec["hasMusic"], str(rec))
    check("and it does not claim its own bytes are missing",
          not rec["claimsOmitted"],
          "pendingPhotoMeta/pendingMusicMeta used to be set on every spill, which "
          "made serializeFlip() stamp mediaOmitted onto the record that HAS the bytes")

    print("\nDRAFT — a reload brings the media back")
    page.reload(wait_until="load")
    page.wait_for_timeout(2000)
    r = page.evaluate(RESTORED)
    check("the drawing restored", r["strokes"] == 40, str(r["strokes"]))
    check("the music came back from IndexedDB",
          r["musicBack"] and r["musicLen"] == len(FAKE_AUDIO),
          f"{r['musicLen']:,} of {len(FAKE_AUDIO):,} B")
    check("the photo came back from IndexedDB",
          r["bgBack"] and r["bgLen"] == len(FAKE_IMAGE),
          f"{r['bgLen']:,} of {len(FAKE_IMAGE):,} B")
    check("no re-add cards are offered",
          not r["pendingMusic"] and not r["pendingPhoto"],
          "the bytes are here; offering to re-add them would be a lie")
    check("the file names survived", r["musicName"] == "track.wav"
          and r["imageName"] == "pic.png", str(r))

    print("\nDRAFT — a drawing with no media takes the short path")
    clean(page)
    page.evaluate(DRAW_AND_SAVE, None)
    page.wait_for_timeout(900)
    st = page.evaluate(LOCAL_STATE)
    check("it saves to localStorage as before",
          st["strokes"] == 40 and st["bytes"] > 0, str(st["bytes"]))
    check("and does not claim an IndexedDB spill",
          not st["mediaInIdb"],
          "nothing to spill means no round trip and no amber pill")
    empty = page.evaluate("() => window.SkriblDraftStore.get('flip:draft')"
                          ".then(r => !r).catch(() => true)")
    check("nothing was written to IndexedDB", empty)

    print("\nDRAFT — drafts saved before this change still restore")
    clean(page)
    # Exactly the old shape: one localStorage record, media inline, no spill
    # flags. Anyone who had Flip open before this version has one of these.
    legacy = {
        "schemaVersion": 2, "version": 2, "playbackMode": "flip", "fps": 12,
        "canvasSize": {"cssWidth": 900, "cssHeight": 1200, "dpr": 1},
        "savedAt": "2026-01-01T00:00:00.000Z", "editIdx": 0,
        "bgImage": FAKE_IMAGE, "music": FAKE_AUDIO,
        "photo": {"fit": "cover", "opacity": 1, "blur": 0, "zoom": 1, "offX": 0,
                  "offY": 0, "enabled": True, "name": "old.png"},
        "musicMeta": {"enabled": True, "trimStart": 0, "trimEnd": 3,
                      "crossfadeMs": 0, "name": "old.wav"},
        "frames": [{"strokes": [{"x": 10, "y": 10, "color": "#fff", "size": 6,
                                 "t": 0, "erase": False, "start": True},
                                {"x": 90, "y": 90, "color": "#fff", "size": 6,
                                 "t": 1, "erase": False}],
                    "strokeGroups": [2], "background": "#0d0f14"}],
    }
    # A FRESH PAGE, not the one above, and the reason is _sessionOwnedDraft.
    # That flag is set by the first real save of a session, and it licenses
    # saveNow() to DELETE the slot when the document is empty — an empty state
    # is then a deliberate clear-all rather than an idle tab. Emptying this
    # page's document and planting a record therefore had the flush remove the
    # planted record on the way out, and the section reported 0 strokes.
    # A page that has never saved leaves the slot alone, which is exactly the
    # fence the flag exists to provide.
    legacy_page = browser.new_page(viewport={"width": 1000, "height": 800})
    legacy_page.on("pageerror", lambda e: errors.append(str(e)))
    legacy_page.goto(BASE + "/flip", wait_until="load")
    legacy_page.wait_for_timeout(400)
    legacy_page.evaluate("""(raw) => {
      for (const k of Object.keys(localStorage))
        if (k.indexOf('skribl') === 0) localStorage.removeItem(k);
      localStorage.setItem('skribl_flip_autosave_v1', raw);
    }""", json.dumps(legacy))
    legacy_page.evaluate("() => window.SkriblDraftStore "
                         "? window.SkriblDraftStore.del('flip:draft').catch(()=>{}) : null")
    legacy_page.reload(wait_until="load")
    legacy_page.wait_for_timeout(1600)
    r = legacy_page.evaluate(RESTORED)
    check("a legacy inline-media draft still restores its drawing",
          r["strokes"] == 2, str(r["strokes"]))
    check("and its media, straight from localStorage",
          r["musicBack"] and r["bgBack"],
          "no IndexedDB record exists for this one — the old path has to keep "
          "working or every existing draft loses its media on upgrade")
    check("with the original names", r["imageName"] == "old.png", str(r["imageName"]))
    legacy_page.close()

    check("no page errors anywhere in this suite", not errors, "; ".join(errors[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
