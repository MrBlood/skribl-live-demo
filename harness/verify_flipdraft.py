"""Flip's draft: strokes in localStorage, media bytes in IndexedDB.

THE BUG THIS CLOSES was reported as "autosave is failing on pad".
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
from assertions import make_check
import browsing
import os

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("SKIP: playwright is not installed")
    sys.exit(0)

results = []


check = make_check(results)


# ~1.2 MB and ~0.5 MB once base64'd: together they are what used to fill the
# budget. Deliberately not real media — this suite is about where bytes go, and
# a decodable file would only add flakiness.
FAKE_AUDIO = "data:audio/wav;base64," + ("QUJD" * 300000)
FAKE_IMAGE = "data:image/png;base64," + ("QUJD" * 120000)
FAKE_AUDIO_BYTES = 300000 * 3   # "QUJD" is "ABC": what the text is, as bytes

# The song's bytes in the store, kept beside the draft since the speed fixes
# (flip.js musicBlob, saveNow): their size, type and the song's name, or null.
SONG_STORED = """() => window.SkriblDraftStore.get('flip:music')
  .then(r => r ? { size: r.blob ? r.blob.size : null, type: r.blob ? r.blob.type : null, name: r.name } : null)
  .catch(() => 'error')"""

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
    browsing.goto(page, BASE, "/flip")
    page.evaluate("""() => {
      frames = [newFrame()]; idx = 0;
      musicData = null; musicName = ''; bgImage = null; bgImageObj = null; imageName = '';
      if (typeof forgetMusicBytes === 'function') { forgetMusicBytes(); _musicStoreP = null; }
      pendingMusicMeta = null; pendingPhotoMeta = null;
      try { buildStrip(); render(); } catch (e) {}
      for (const k of Object.keys(localStorage))
        if (k.indexOf('skribl') === 0) localStorage.removeItem(k);
    }""")
    page.evaluate("() => window.SkriblDraftStore "
                  "? Promise.all([window.SkriblDraftStore.del('flip:draft').catch(()=>{}),"
                  " window.SkriblDraftStore.del('flip:music').catch(()=>{})]) : null")
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
    song = page.evaluate(SONG_STORED)
    # THE SONG IS KEPT AS A FILE (the speed fixes, Nov 5). It was written into
    # this record as text on every save: a two-minute song's 28 MB, 0.3 to 0.9 s
    # a save at a slower phone's pace. Its bytes are kept once, beside it.
    check("IndexedDB has the full record: the photo in the draft, the song's bytes kept beside it",
          rec["present"] and rec["hasBg"] and isinstance(song, dict) and song["size"] == FAKE_AUDIO_BYTES
          and song["type"] == "audio/wav" and song["name"] == "track.wav",
          f"the draft {rec['bytes']:,} B; the song's bytes {song}")
    check("and the draft leaves the song's text out: a save writes the drawing, not the song",
          not rec["hasMusic"] and rec["bytes"] < len(FAKE_AUDIO),
          f"the draft {rec['bytes']:,} B, the song's text {len(FAKE_AUDIO):,} B; {rec}")
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
    browsing.goto(legacy_page, BASE, "/flip")
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

    # FLIP KEEPS A SONG AS A FILE (the speed fixes, Nov 5; flip.js musicBlob).
    # A two-minute song is 28 MB of text. At a slower phone's pace an <audio>
    # element handed that text held the page 2.3 s reading it back, the decode
    # turned it into bytes again on the page, and every autosave wrote all of
    # it again. Now the song plays and decodes from its bytes, and a save
    # keeps them once, beside the draft, as the Pad keeps its file.
    print("\nDRAFT — Flip keeps a song as a file")
    import math, struct, tempfile, wave
    song_path = os.path.join(tempfile.mkdtemp(), "tune.wav")
    with wave.open(song_path, "wb") as w:   # a real song: 3 s of a tone, 16-bit mono
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 330 * i / 22050))) for i in range(22050 * 3)))
    song_size = os.path.getsize(song_path)
    song_page = browser.new_page(viewport={"width": 1000, "height": 800})
    song_page.on("pageerror", lambda e: errors.append(str(e)))
    clean(song_page)
    # Counted from here: the song's text turned back into bytes on the page,
    # and the song's bytes written to the store.
    COUNT = """() => { window.__d2ab = 0; window.__songPuts = 0;
      const d2ab = window.dataURLToArrayBuffer; window.dataURLToArrayBuffer = function () { window.__d2ab++; return d2ab.apply(this, arguments); };
      const put = SkriblDraftStore.put; SkriblDraftStore.put = function (k) { if (k === 'flip:music') window.__songPuts++; return put.apply(this, arguments); }; }"""
    DRAFT_TEXT = """() => SkriblDraftStore.get('flip:draft').then(r => r && r.json
      ? { bytes: r.json.length, music: !!JSON.parse(r.json).music } : null).catch(() => 'error')"""

    def until(pg, expr, ms):
        """True once `expr` holds, False past `ms`: a broken build reads red, not a stopped run."""
        try:
            pg.wait_for_function(expr, timeout=ms)
            return True
        except Exception:
            return False

    def stored_song(pg, want, ms=8000):
        """The song's record in the store once it is what `want` says (a size, or None)."""
        got = None
        for _ in range(ms // 200):
            got = pg.evaluate(SONG_STORED)
            if (want is None and got is None) or (isinstance(got, dict) and got["size"] == want):
                return got
            pg.wait_for_timeout(200)
        return got

    song_page.evaluate(COUNT)
    song_page.set_input_files("#musicInput", song_path)
    until(song_page, "() => !!currentAudioBuffer && !!audioEl", 20000)
    got = song_page.evaluate("""() => ({ src: audioEl ? audioEl.src.slice(0, 5) : null,
      bytes: musicBlob ? musicBlob.size : null, d2ab: window.__d2ab, seconds: currentAudioBuffer ? currentAudioBuffer.duration : 0 })""")
    check("a song added is played from its bytes, not from its text",
          got["src"] == "blob:" and got["bytes"] == song_size,
          f"the <audio> element's address begins {got['src']!r}; the bytes kept {got['bytes']} of {song_size}")
    check("...and decoded from its bytes: the page never turns its text back into bytes",
          got["d2ab"] == 0 and abs(got["seconds"] - 3) < 0.05,
          f"text turned into bytes {got['d2ab']} time(s); decoded {got['seconds']:.2f} s of 3")
    first = stored_song(song_page, song_size)
    for _ in range(3):   # three more saves, as three more strokes would make
        song_page.evaluate("() => saveNow()"); song_page.wait_for_timeout(400)
    until(song_page, "() => _mediaSpillState === 'durable'", 8000)
    draft = song_page.evaluate(DRAFT_TEXT)
    puts = song_page.evaluate("() => window.__songPuts")
    check("every save writes the drawing; the song's bytes are written once, beside it",
          isinstance(first, dict) and first["name"] == "tune.wav" and first["type"] == "audio/wav" and puts == 1
          and isinstance(draft, dict) and not draft["music"] and draft["bytes"] < 50_000,
          f"the song's bytes {first}, written {puts} time(s) in four saves; the draft {draft}")

    text_was = song_page.evaluate("() => ({ n: musicData.length, head: musicData.slice(0, 64), tail: musicData.slice(-64) })")
    song_page.reload(wait_until="load")
    until(song_page, "() => !!currentAudioBuffer && !!musicData && !!audioEl", 20000)
    song_page.evaluate(COUNT)
    for _ in range(2):
        song_page.evaluate("() => saveNow()"); song_page.wait_for_timeout(400)
    back = song_page.evaluate("""() => ({ name: musicName, n: musicData ? musicData.length : 0, head: musicData ? musicData.slice(0, 64) : null,
      tail: musicData ? musicData.slice(-64) : null, bytes: musicBlob ? musicBlob.size : null, src: audioEl ? audioEl.src.slice(0, 5) : null,
      seconds: currentAudioBuffer ? currentAudioBuffer.duration : 0, puts: window.__songPuts })""")
    check("a reload brings the song back from its bytes: the same song, played from them, and not written again",
          back["name"] == "tune.wav" and back["n"] == text_was["n"] and back["head"] == text_was["head"] and back["tail"] == text_was["tail"]
          and back["bytes"] == song_size and back["src"] == "blob:" and abs(back["seconds"] - 3) < 0.05 and back["puts"] == 0,
          f"{back['name']}, its text {back['n']:,} of {text_was['n']:,} characters, the same at both ends: "
          f"{back['head'] == text_was['head'] and back['tail'] == text_was['tail']}; bytes {back['bytes']}; "
          f"played from {back['src']!r}; written {back['puts']} time(s) in two saves")

    song_page.evaluate("() => { removeMusic(); saveNow(); }")
    gone = stored_song(song_page, None)
    check("the song taken away takes its bytes out of the store", gone is None, f"the store still holds {gone}")
    song_page.close()

    # A save from before this change kept the song as text inside the draft in
    # IndexedDB. It must come back, and the next save keeps it as a file.
    old_page = browser.new_page(viewport={"width": 1000, "height": 800})
    old_page.on("pageerror", lambda e: errors.append(str(e)))
    clean(old_page)
    lite = dict(legacy, bgImage=None, music=None, photo=None, mediaInIdb=True, mediaOmitted=True,
                musicMeta=dict(legacy["musicMeta"], name="before.wav"))
    full = dict(legacy, bgImage=None, photo=None, music=FAKE_AUDIO, musicMeta=dict(legacy["musicMeta"], name="before.wav"))
    old_page.evaluate("""([lite, full]) => SkriblDraftStore.put('flip:draft', { json: full, savedAt: Date.now() })
      .then(() => localStorage.setItem('skribl_flip_autosave_v1', lite))""", [json.dumps(lite), json.dumps(full)])
    old_page.reload(wait_until="load")
    until(old_page, "() => !!musicData", 10000)
    r = old_page.evaluate(RESTORED)
    old_page.evaluate("() => saveNow()")
    moved = stored_song(old_page, FAKE_AUDIO_BYTES)
    draft = old_page.evaluate(DRAFT_TEXT)
    check("an older save, its song as text in the draft, comes back, and the next save keeps the song as a file",
          r["musicBack"] and r["musicLen"] == len(FAKE_AUDIO) and r["musicName"] == "before.wav"
          and isinstance(moved, dict) and moved["name"] == "before.wav" and isinstance(draft, dict) and not draft["music"],
          f"back: {r['musicBack']}, {r['musicLen']:,} of {len(FAKE_AUDIO):,} characters, {r['musicName']!r}; "
          f"its bytes then {moved}; the draft then {draft}")
    old_page.close()

    check("no page errors anywhere in this suite", not errors, "; ".join(errors[:3]))
    browser.close()

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
