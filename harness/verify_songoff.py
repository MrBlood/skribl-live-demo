#!/usr/bin/env python3
"""A song's text and its bytes are made and kept off the page, in both editors.

THE OWNER, Nov 5: "do the song speed for both editors". Adding a two-minute
song held a slower phone's page (this box's Chromium, the CPU 4x slower) in
two places the editors share: making the song's text (its data URL, which the
post, a backup file and a saved draft carry), 0.3 to 0.4 s in one stretch, and
writing its bytes to the draft store, 0.1 to 0.2 s. lib/songtext.js now makes
the text in a worker, and lib/draftstore.js writes a record that holds a file
from a worker running itself. Where a worker cannot be had, or will not do,
the page does both, as it always did: nothing is lost for want of one.

WHAT IS ASKED, AND HOW IT IS READ (each editor, a song added through the
music drawer's own file input, then a stroke drawn, as a person would)
  * OFF THE PAGE: the page's own FileReader.readAsDataURL is never called,
    and the text the editor keeps (the Pad's audio's _draftData, Flip's
    musicData) is the file's own data URL; the page's own IDBObjectStore.put
    is never called for the song's record ('pad:music', 'flip:music'), and
    the record holds the same file (its name, its size, its bytes' digest).
  * NO WORKER TO BE HAD (window.Worker gone): the page makes the text and
    writes the bytes itself, and both are the same.
  * A WORKER WHOSE SCRIPT WILL NOT LOAD (a 404): both give up on it at once,
    and the page makes the text and writes the bytes.
  * A WORKER THAT WILL NOT DO: one that cannot make the text (it answers with
    an error), and one whose store does not answer (its IndexedDB open never
    fires): the page makes the text, and writes the bytes, itself.
  * A WORKER THAT NEVER ANSWERS (the Pad only; one module serves both): after
    its 20 s the page makes the text itself.

NOT TESTED HERE: a writer that never answers at all (its deadline is the
store's own 34 s), and WebKit (no WebKit here).
"""
import base64
import hashlib
import io
import math
import os
import struct
import sys
import time
import wave

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
    print("No assertions were executed. This is NOT evidence a song is made or kept off the page.")
    raise SystemExit(77)
import browsing  # noqa: E402
import waits  # noqa: E402

# For calibration: SONGOFF_ONLY=Pad (or Flip) runs one editor, and
# SONGOFF_MODES=off,none,404,refuse,silent the named cases. A real run sets neither.
ONLY = os.environ.get("SONGOFF_ONLY", "")
MODES = [m for m in os.environ.get("SONGOFF_MODES", "off,none,404,refuse,silent").split(",") if m]
EDITORS = [e for e in (("Pad", "/", "pad:music"), ("Flip", "/flip", "flip:music")) if not ONLY or e[0] == ONLY]


def _wav(seconds, rate=8000, bpm=120.0, f0=70.0):
    """A pulse on every beat."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    p = 60.0 / bpm
    w.writeframes(b"".join(struct.pack("<h", int(16000 * math.sin(2 * math.pi * f0 * i / rate) * math.exp(-((i / rate) % p) * 9)))
                           for i in range(int(seconds * rate))))
    w.close()
    return buf.getvalue()


SONG = {"name": "offpage.wav", "mimeType": "audio/wav", "buffer": _wav(4.0)}
TEXT = "data:audio/wav;base64," + base64.b64encode(SONG["buffer"]).decode()
DIGEST = hashlib.sha256(SONG["buffer"]).hexdigest()
NO_EARS = "Object.defineProperty(window, 'SkriblEars', { configurable: true, get() { return undefined; }, set(v) {} });"

# What the page itself is asked to do, and which workers it makes.
COUNT = """(() => { const c = window.__off = { dataurl: 0, puts: {}, made: [] };
  const rd = FileReader.prototype.readAsDataURL;
  FileReader.prototype.readAsDataURL = function () { c.dataurl++; return rd.apply(this, arguments); };
  const put = IDBObjectStore.prototype.put;
  IDBObjectStore.prototype.put = function (v, k) { c.puts[k] = (c.puts[k] || 0) + 1; return put.apply(this, arguments); };
  const W = window.Worker;
  if (W) { const C = function (u, o) { c.made.push(String(u).split('/').pop().split('?')[0]); return new W(u, o); };
    C.prototype = W.prototype; window.Worker = C; } })();"""
# A worker made from this suite's own few lines in front of the real script:
# the worker is the module's own, told to fail the way the case asks.
WRAP = """(() => { const W = window.Worker, PRE = %s;
  const C = function (u, o) { const name = String(u).split('/').pop().split('?')[0];
    if (!(name in PRE)) return new W(u, o);
    const abs = new URL(String(u), location.href).href;
    return new W(URL.createObjectURL(new Blob([PRE[name] + '\\nimportScripts(' + JSON.stringify(abs) + ');'], { type: 'text/javascript' })), o); };
  C.prototype = W.prototype; window.Worker = C; })();"""
CASES = {
    "off": [],
    "none": ["(() => { Object.defineProperty(window, 'Worker', { value: undefined, configurable: true, writable: true }); })();"],
    "404": ["""(() => { const W = window.Worker; const C = function (u, o) { return new W('/no-such-worker.js', o); };
      C.prototype = W.prototype; window.Worker = C; })();"""],
    "refuse": [WRAP % """{ 'songtext.js': "self.FileReaderSync = function () { this.readAsDataURL = function () { throw new Error('refused'); }; };",
                          'draftstore.js': "if (self.indexedDB) self.indexedDB.open = function () { return {}; };" }"""],
    "silent": [WRAP % """{ 'songtext.js': "self.postMessage = function () {};" }"""],
}
TEXT_OF = {"Pad": "() => (typeof audioEl !== 'undefined' && audioEl && audioEl._draftData) || null",
           "Flip": "() => (typeof musicData !== 'undefined' && musicData) || null"}
SAVED = {"Pad": waits.PAD_MUSIC_SAVED, "Flip": waits.FLIP_MUSIC_SAVED}
STORED = """async (k) => { const r = await SkriblDraftStore.get(k).catch(() => null);
  if (!r || !r.blob) return null;
  const d = await crypto.subtle.digest('SHA-256', await r.blob.arrayBuffer());
  return { name: r.name, size: r.blob.size, digest: [...new Uint8Array(d)].map((x) => x.toString(16).padStart(2, '0')).join('') }; }"""


def run(b, name, path, key, case, text_ms=20000, saved_ms=25000):
    """One editor, one case: a song added by hand and a stroke drawn. What the
    page did itself, the text it keeps, and the record in the store."""
    c = b.new_context(viewport={"width": 1280, "height": 900})
    c.add_init_script(NO_EARS)
    c.add_init_script(COUNT)
    for js in CASES[case]:
        c.add_init_script(js)
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide()")
    browsing.pad_drawer(pg, "music")
    t0 = time.monotonic()
    pg.set_input_files("#musicInput", SONG)
    got_text = waits.until(pg, TEXT_OF[name] + " !== null", f"{name}'s song text", ms=text_ms)
    text_s = time.monotonic() - t0
    box = pg.locator("#canvas" if name == "Pad" else "#pad").bounding_box()
    pg.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.4); pg.mouse.down()
    for i in range(10):
        pg.mouse.move(box["x"] + box["width"] * 0.3 + i * 8, box["y"] + box["height"] * 0.4 + (i % 3) * 6)
    pg.mouse.up()
    saved = waits.until(pg, SAVED[name], f"{name}'s song kept", ms=saved_ms) if got_text else False
    out = {"text": pg.evaluate(TEXT_OF[name]), "text_s": text_s, "saved": saved,
           "count": pg.evaluate("() => window.__off"), "stored": pg.evaluate(STORED, key), "errs": errs}
    c.close()
    return out


def text_is_the_files(o):
    return o["text"] == TEXT


def stored_is_the_files(o):
    s = o["stored"]
    return bool(s) and s["name"] == SONG["name"] and s["size"] == len(SONG["buffer"]) and s["digest"] == DIGEST


def says(o, key):
    s = o["stored"]
    t = o["text"]
    return (f"page readAsDataURL x{o['count']['dataurl']}, page puts of {key} x{o['count']['puts'].get(key, 0)}, "
            f"workers made {o['count']['made']}; text {'the file' if t == TEXT else (len(t) if t else t)} "
            f"after {o['text_s']:.1f}s; kept {o['saved']}; stored "
            f"{'the file' if stored_is_the_files(o) else s}; errors {o['errs'][:2]}")


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for name, path, key in EDITORS:
        if "off" in MODES:
            print(f"\n{name}: A SONG ADDED, ITS TEXT AND ITS BYTES OFF THE PAGE")
            o = run(b, name, path, key, "off")
            check(f"{name}: a song added, its text made off the page (the page's FileReader not asked), the file's own data URL",
                  text_is_the_files(o) and o["count"]["dataurl"] == 0 and "songtext.js" in o["count"]["made"], says(o, key))
            check(f"{name}: ...and its bytes written off the page (the page's IndexedDB not asked to put '{key}'), the same file kept",
                  stored_is_the_files(o) and o["saved"] and o["count"]["puts"].get(key, 0) == 0
                  and "draftstore.js" in o["count"]["made"], says(o, key))
        if "none" in MODES:
            print(f"\n{name}: NO WORKER TO BE HAD")
            o = run(b, name, path, key, "none")
            check(f"{name}, no worker to be had: the page makes the song's text itself, the file's own data URL",
                  text_is_the_files(o) and o["count"]["dataurl"] >= 1, says(o, key))
            check(f"{name}, no worker to be had: ...and writes its bytes itself, the same file kept",
                  stored_is_the_files(o) and o["saved"] and o["count"]["puts"].get(key, 0) >= 1, says(o, key))
        if "404" in MODES:
            print(f"\n{name}: A WORKER WHOSE SCRIPT WILL NOT LOAD")
            o = run(b, name, path, key, "404")
            check(f"{name}, a worker whose script will not load: the song's text is made on the page, the file's own data URL",
                  text_is_the_files(o) and o["count"]["dataurl"] >= 1 and o["text_s"] < 10, says(o, key))
            check(f"{name}, a worker whose script will not load: ...and its bytes written on the page, the same file kept",
                  stored_is_the_files(o) and o["saved"] and o["count"]["puts"].get(key, 0) >= 1, says(o, key))
        if "refuse" in MODES:
            print(f"\n{name}: A WORKER THAT WILL NOT DO")
            o = run(b, name, path, key, "refuse")
            check(f"{name}, a worker that cannot make the text: the page makes it, the file's own data URL",
                  text_is_the_files(o) and o["count"]["dataurl"] >= 1 and o["text_s"] < 10, says(o, key))
            check(f"{name}, a worker whose store does not answer: the page writes the bytes itself, the same file kept",
                  stored_is_the_files(o) and o["saved"] and o["count"]["puts"].get(key, 0) >= 1, says(o, key))
    if "silent" in MODES and (not ONLY or ONLY == "Pad"):
        print("\nPad: A WORKER THAT NEVER ANSWERS")
        o = run(b, "Pad", "/", "pad:music", "silent", text_ms=35000)
        check("Pad, a worker that never answers: after its 20 s the page makes the song's text itself, the file's own data URL",
              text_is_the_files(o) and o["count"]["dataurl"] >= 1 and 18 <= o["text_s"] < 32, says(o, "pad:music"))
    b.close()

summarise_and_exit()
