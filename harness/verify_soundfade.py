"""No click where the sound starts or stops: Play, Stop and the sound switch
glide over 5ms (the owner: "All yes" to a 5 ms fade on Play, Stop and the
sound switch, in the editors, the link page and a post's box).

THE CLICK. A sound begun or ended mid-wave jumps from silence to the wave,
or from the wave to silence, in one sample, and a jump is a click. A loop's
start is mid-wave wherever the music is, and a Stop lands wherever it lands:
measured before this, a Stop at a random moment jumped more than a tenth of
the song's peak more than half the time. The loop's own join is not this
suite's: a smooth restart folds its end into its start, and Cut on silence
moves both ends to where they match (verify_musictimeline).

ASKED OF WHAT REACHES THE SPEAKERS. Installed before any page script, every
connection to a context's output is led through a recorder first, a
ScriptProcessorNode that passes the sound on unchanged and keeps a copy. So
what is measured is everything the page plays, after every gain, summed, as
the speakers get it, and not what any node says it was asked to do.

THE SONG IS A STEADY LEVEL, half of full scale on both channels, no crossfade:
whatever the moment, starting or stopping it unfaded is a jump of the whole
level, and a fade's length reads straight off the samples. At each edge, the
biggest one-sample step there (a fiftieth of the level at most: an unfaded
edge steps the whole level), and how long the sound takes to reach the level
or leave it (2 to 8ms: a glide, and a short one, never a slow fade).

THE SURFACES, each of what plays sound: the Pad and Flip editors (Hear the
loop: lib/audioloop.js engine; and pressed again and again), the link page
(app.js's player: Play, Pause and its sound switch, and the switch pressed
twice in a moment) and a post's box (inlineplayer.js: the same). The native
<audio> hand-off, for a context that never unlocks, is a fallback and is not
faded (an element's volume is not settable on an iPhone).

NOT TESTED HERE: an iPhone's or Safari's Web Audio (no WebKit here), and
whether a person hears it. What is pinned is the shape of the sound.
"""
import io
import json
import math
import os
import pathlib
import re
import struct
import sys
import wave
from assertions import make_check
import browsing
import playerready
import waits

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skribl.jsstrip import strip_comments  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                   # pragma: no cover
    print(f"SUITE-SKIPPED: playwright unavailable ({exc})")
    raise SystemExit(77)

results = []
check = make_check(results, with_detail=True)
LEVEL = 0.5


def steady(seconds, rate=44100):
    """Half of full scale, both channels, for `seconds`."""
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
    v = int(32767 * LEVEL)
    w.writeframes(struct.pack("<hh", v, v) * int(seconds * rate))
    w.close()
    return buf.getvalue()


SONG = {"name": "steady.wav", "mimeType": "audio/wav", "buffer": steady(6.0)}

# THE RECORDER. Every connect() to an AudioDestinationNode goes to the
# context's bus instead, which passes it on to the destination unchanged; an
# AudioWorklet on the bus keeps channel 0, block by block, with the audio
# thread's own frame count, so a record cannot miss a block unseen (a
# ScriptProcessorNode's blocks are the page's to deliver, and a busy page
# delays them; its playbackTime jitters by a block and cannot say). The
# worklet's script is a blob, which the page's script-src refuses, and a
# route cannot serve it at the page's origin (Playwright does not route a
# worklet's fetch): so these contexts bypass the page's CSP. This suite
# measures sound; verify_csp pins the policy. __cap.edges() reads what
# was kept since __cap.reset().
REC_JS = """class SkrRec extends AudioWorkletProcessor {
  constructor() { super(); this.buf = []; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    this.buf.push(ch ? new Float32Array(ch) : new Float32Array(128));
    if (this.buf.length >= 8) { this.port.postMessage({ f: currentFrame - 128 * (this.buf.length - 1), d: this.buf }); this.buf = []; }
    return true;
  }
}
registerProcessor('skr-rec', SkrRec);"""
TAP = """(() => {
  const oc = AudioNode.prototype.connect, buses = new Map();
  const url = URL.createObjectURL(new Blob([""" + json.dumps(REC_JS) + """], { type: 'application/javascript' }));
  const R = window.__rec = { chunks: [], sr: 0, ready: 0 };
  function bus(ctx) {
    let g = buses.get(ctx);
    if (g) return g;
    g = ctx.createGain(); buses.set(ctx, g); R.sr = ctx.sampleRate;
    oc.call(g, ctx.destination);
    ctx.audioWorklet.addModule(url).then(() => {
      const w = new AudioWorkletNode(ctx, 'skr-rec'), sink = ctx.createGain();
      sink.gain.value = 0;
      w.port.onmessage = (e) => { R.chunks.push(e.data); };
      oc.call(g, w); oc.call(w, sink); oc.call(sink, ctx.destination);
      R.ready++;
    });
    return g;
  }
  AudioNode.prototype.connect = function (d, ...rest) {
    if (typeof AudioDestinationNode !== 'undefined' && d instanceof AudioDestinationNode)
      return oc.call(this, bus(this.context), ...rest);
    return oc.call(this, d, ...rest);
  };
  // From the context's first moment, so the silence before a first sound is
  // on the record too.
  const Orig = window.AudioContext || window.webkitAudioContext;
  if (Orig) {
    const Rec = function (...a) { const c = new Orig(...a); bus(c); return c; };
    Rec.prototype = Orig.prototype;
    window.AudioContext = Rec; if (window.webkitAudioContext) window.webkitAudioContext = Rec;
  }
  window.__cap = {
    reset() { R.chunks = []; },
    edges() {
      const C = R.chunks; let n = 0, gaps = 0;
      for (let k = 0; k < C.length; k++) { n += C[k].d.length * 128; if (k && C[k].f !== C[k - 1].f + C[k - 1].d.length * 128) gaps++; }
      const x = new Float32Array(n), sr = R.sr || 44100;
      let o = 0; for (const c of C) for (const blk of c.d) { x.set(blk, o); o += blk.length; }
      let f = -1, l = -1;
      for (let i = 0; i < n; i++) if (Math.abs(x[i]) > 1e-3) { if (f < 0) f = i; l = i; }
      if (f < 0) return { n, sr, sound: false, gaps };
      const ms = (v) => Math.round(v / 1000 * sr);
      const step = (a, b) => { let m = 0; for (let i = Math.max(1, a); i < Math.min(n, b); i++) m = Math.max(m, Math.abs(x[i] - x[i - 1])); return m; };
      const level = (a, b) => { const v = []; for (let i = Math.max(0, a); i < Math.min(n, b); i++) v.push(Math.abs(x[i])); v.sort((p, q) => p - q); return v.length ? v[v.length >> 1] : 0; };
      const lin = level(f + ms(12), f + ms(40)), lout = level(l - ms(40), l - ms(12));
      let up = f; while (up < n && Math.abs(x[up]) < 0.9 * lin) up++;
      let down = l; while (down > 0 && Math.abs(x[down]) < 0.9 * lout) down--;
      return { n, sr, sound: true, first: f, last: l,
               startStep: +step(f - 2, f + ms(12)).toFixed(5), endStep: +step(l - ms(12), l + 3).toFixed(5),
               levelIn: +lin.toFixed(4), levelOut: +lout.toFixed(4),
               riseMs: +((up - f) / sr * 1000).toFixed(2), fallMs: +((l - down) / sr * 1000).toFixed(2),
               endsBefore: n - 1 - l, startsAfter: f, maxStep: +step(1, n).toFixed(5), gaps };
    }
  };
})();"""


def recorded(b, **kw):
    """A context whose pages record what reaches their speakers."""
    c = waits.instrument(b.new_context(bypass_csp=True, **kw))
    c.add_init_script(TAP)
    return c


SET = """(o) => { trimStart = o.s; trimEnd = o.e; loopCrossfadeMs = 0; if (typeof setCrossfadeUI === 'function') setCrossfadeUI();
  loopCutOnSilence = false; updateTrimUI(); }"""
PAGES = """() => { frames.length = 0;
  for (let k = 0; k < 3; k++) { const f = newFrame(); const pts = [];
    for (let j = 0; j < 12; j++) pts.push({ x: CW * (0.1 + 0.2 * k) + j * 6, y: CH * 0.3 + j * 12, color: '#7c5cff', size: 10, t: j * 5, start: j === 0 });
    f.strokes.push(...pts); f.strokeGroups.push(pts.length); f.hold = 8; frames.push(f); }
  fps = 12; idx = 0; buildStrip(); render(); updateToolState(); }"""
POST_PUBLIC = """async (title) => {
  const p = serializeSkribl();
  p.title = title;
  p.visibility = 'public';
  const r = await fetch(window.SKRIBL_API_BASE, {
    method: 'POST', headers: skriblPostHeaders(), body: JSON.stringify(p) });
  if (!r.ok) return { error: r.status + ' ' + (await r.text()).slice(0, 200) };
  return await r.json();
}"""


def ready(pg):
    """The recorder is on the context: its worklet loads once the context is made."""
    pg.wait_for_function("() => window.__rec && window.__rec.ready > 0", timeout=10000)


def captured(pg, act, wait=450, undo=None):
    """What reached the speakers around `act`: reset, 80ms of what was playing
    before it (the level an edge leaves from is read there), act, let it land.
    A record with a block missing (the audio thread fell behind, now and then
    here: a glitch for any listener, and not the edge's) cannot be read: the
    act is undone (by itself, a toggle, unless `undo` says otherwise) and
    tried again, three times at most, and a record still broken says so."""
    for _ in range(3):
        pg.evaluate("() => window.__cap.reset()")
        pg.wait_for_timeout(80)
        act()
        pg.wait_for_timeout(wait)
        e = pg.evaluate("() => window.__cap.edges()")
        if not e.get("gaps"):
            return e
        (undo or act)()
        pg.wait_for_timeout(500)
    return e


def say(e):
    if not e.get("sound"):
        return f"no sound in {e.get('n')} samples"
    return (f"{e['gaps']} BLOCKS OF THE RECORD MISSING; " if e.get("gaps") else "") + (f"steps {e['startStep']} in, {e['endStep']} out of a level of {e['levelIn']}/{e['levelOut']};"
            f" up in {e['riseMs']}ms, down in {e['fallMs']}ms; {e['startsAfter']} quiet samples first, {e['endsBefore']} after")


def glides_in(e):
    return (e.get("sound") and not e["gaps"] and e["startsAfter"] > 50 and e["levelIn"] > 0.3
            and e["startStep"] <= e["levelIn"] / 50 and 2 <= e["riseMs"] <= 8)


def glides_out(e):
    return (e.get("sound") and not e["gaps"] and e["endsBefore"] > 50 and e["levelOut"] > 0.3
            and e["endStep"] <= e["levelOut"] / 50 and 2 <= e["fallMs"] <= 8)


def steady(e):
    """Sound at the level by the end, and no one-sample step anywhere over a
    fiftieth of it."""
    return e.get("sound") and not e["gaps"] and e["levelOut"] > 0.3 and e["maxStep"] <= e["levelOut"] / 50


def scribble(pg):
    box = pg.evaluate("() => { const r = document.getElementById('canvas').getBoundingClientRect(); return { x: r.x, y: r.y }; }")
    pg.mouse.move(box["x"] + 80, box["y"] + 80); pg.mouse.down()
    for k in range(60):
        pg.mouse.move(box["x"] + 80 + k * 4, box["y"] + 80 + (k % 10) * 6); pg.wait_for_timeout(40)
    pg.mouse.up(); pg.wait_for_timeout(300)


def editor(b, name, path):
    c = recorded(b, viewport={"width": 1280, "height": 900})
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    browsing.goto(pg, BASE, path)
    pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} window.SkriblHints && window.SkriblHints.hide && window.SkriblHints.hide(); }")
    if name == "Pad":
        scribble(pg)
        pg.click("#recordBtn"); pg.wait_for_timeout(700)
    else:
        pg.evaluate(PAGES)
    browsing.pad_drawer(pg, "music")
    pg.set_input_files("#musicInput", SONG)
    pg.wait_for_function("() => document.getElementById('musicUploadBtn').classList.contains('loaded') && !!currentAudioBuffer"
                         " && Math.abs(audioDuration - 6) < 0.2", timeout=20000)
    waits.settle(pg, 800)
    pg.evaluate(SET, {"s": 1.0, "e": 4.0})
    pg.wait_for_timeout(300)
    return c, pg, errs


def block(path):
    """The glide block (FADE_MS to the end of fadeOut) as served, comments
    gone, spaces one; None where a file has none."""
    s = strip_comments((ROOT / path).read_text(encoding="utf-8"))
    a = s.find("var FADE_MS = 5")
    z = s.find("function fadeOut", a)
    b = s.find("\n  }\n", z)
    if a < 0 or z < 0 or b < 0:
        return None
    return re.sub(r"\s+", " ", s[a:b + 4]).strip()


print("\nONE GLIDE, TWO COPIES")
_lib, _box = block("skribl/static/lib/audioloop.js"), block("skribl/static/inlineplayer.js")
check("a post's box carries lib/audioloop.js's glide, fadeIn and fadeOut word for word",
      _lib is not None and _lib == _box,
      "no glide block in " + " or ".join(n for n, v in (("lib/audioloop.js", _lib), ("inlineplayer.js", _box)) if v is None)
      if _lib is None or _box is None else f"{len(_lib)} and {len(_box)} characters" + ("" if _lib == _box else
      f"; they part at character {next((i for i, (x, y) in enumerate(zip(_lib, _box)) if x != y), min(len(_lib), len(_box)))}"))

# A GLIDE CUT SHORT BY ANOTHER, on the link page's own context, the second
# begun 2ms into the first: it must go on from where the first had got to.
# The page clock moves 9 to 12ms a step here, so two presses rarely land
# inside one glide, so this asks it outright.
CUT = """() => new Promise((res) => {
  const L = window.SkriblAudioLoop, c = audioCtx;
  if (!L.glide) return res();
  const s = c.createConstantSource(); s.offset.value = 0.5;
  const g = c.createGain(); g.gain.value = 0; s.connect(g); g.connect(c.destination); s.start();
  const t = c.currentTime + L.LEAD;
  L.glide(c, g.gain, 1, t); L.glide(c, g.gain, 0, t + 0.002);
  setTimeout(() => { s.stop(); s.disconnect(); g.disconnect(); res(); }, 200); })"""

# THE FIRST START AFTER THE SOUND WAKES UP, which is every first Play: the
# engine wakes its context in the gesture and starts once it runs. Just
# woken, the audio can be made ahead of the clock the page reads, so a glide
# begun at "now" lands on audio already made, over before it began: with no
# lead, 3 starts in 52 here jumped the whole level, and 27 in 76 beside
# another suite. Now and then, not every time, so it is asked 80 times, each
# on a context of its own, recorded by its own recorder from before it wakes;
# one with a block of its record missing is set aside, 60 read at least.
WAKE = """async ([rec, n]) => {
  const L = window.SkriblAudioLoop, out = [];
  if (!L || !L.fadeIn) return out;
  const url = URL.createObjectURL(new Blob([rec], { type: 'application/javascript' }));
  for (let k = 0; k < n; k++) {
    const c = new AudioContext();
    await c.suspend();
    await c.audioWorklet.addModule(url);
    const w = new AudioWorkletNode(c, 'skr-rec'), sink = c.createGain(), bus = c.createGain(), C = [];
    w.port.onmessage = (e) => C.push(e.data);
    sink.gain.value = 0; bus.connect(c.destination); bus.connect(w); w.connect(sink); sink.connect(c.destination);
    await c.resume();
    const s = c.createConstantSource(); s.offset.value = 0.5;
    const g = L.fadeIn(c, s, bus); s.start(g.at);
    await new Promise((r) => setTimeout(r, 120));
    await c.close();
    let gaps = 0, m = 0, f = -1, prev = 0, i = 0;
    C.forEach((ch, j) => { if (j && ch.f !== C[j - 1].f + C[j - 1].d.length * 128) gaps++;
      for (const b of ch.d) for (const v of b) { if (i) m = Math.max(m, Math.abs(v - prev)); if (f < 0 && Math.abs(v) > 1e-3) f = i; prev = v; i++; } });
    out.push({ m: +m.toFixed(5), f, gaps });
  }
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    print("\nTHE EDITORS — Hear the loop (lib/audioloop.js engine)")
    for name, path in (("Pad", "/skribl-pad"), ("Flip", "/flip")):
        c, pg, errs = editor(b, name, path)
        pg.evaluate("() => document.getElementById('previewLoopBtn').scrollIntoView({ block: 'center' })")
        pg.wait_for_timeout(300)
        # Once round first: the editor makes its sound's context on the first
        # press, and a context begun with its first sound has no silence on
        # the record before it.
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(500)
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(400)
        ready(pg)
        on = captured(pg, lambda: pg.click("#previewLoopBtn"), 700)
        check(f"{name}: Hear the loop begins from silence, gliding up over about 5ms", glides_in(on), say(on))
        pg.wait_for_timeout(300)
        off = captured(pg, lambda: pg.click("#previewLoopBtn"))
        check(f"{name}: ...and Stop glides it down to silence the same way", glides_out(off), say(off))
        # Again at once, the second while the first's fade is still going:
        # Play, then Stop 2ms in, then Play.
        quick = captured(pg, lambda: pg.evaluate("""() => new Promise((res) => {
          const b = document.getElementById('previewLoopBtn'); b.click();
          setTimeout(() => { b.click(); setTimeout(() => { b.click(); res(); }, 30); }, 2); })"""), 700,
          undo=lambda: pg.click("#previewLoopBtn"))
        check(f"{name}: ...and pressed again and again, nothing jumps", steady(quick),
              f"the biggest step anywhere {quick.get('maxStep')}; " + say(quick))
        pg.click("#previewLoopBtn"); pg.wait_for_timeout(200)
        check(f"{name}: no page errors", not errs, "; ".join(errs[:2]))
        c.close()

    print("\nTHE LINK PAGE — Play, Pause and the sound switch (app.js)")
    pc = b.new_context(viewport={"width": 1280, "height": 900})
    pp = pc.new_page()
    perrs = []
    pp.on("pageerror", lambda e: perrs.append(str(e)))
    browsing.goto(pp, BASE, "/skribl-pad")
    pp.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    scribble(pp)
    for _ in range(2):
        scribble(pp)
    pp.click("#recordBtn"); pp.wait_for_timeout(700)
    browsing.pad_drawer(pp, "music")
    pp.set_input_files("#musicInput", SONG)
    pp.wait_for_function("() => !!currentAudioBuffer && Math.abs(audioDuration - 6) < 0.2", timeout=20000)
    waits.settle(pp, 800)
    pp.evaluate(SET, {"s": 1.0, "e": 4.0})
    pp.wait_for_timeout(300)
    res = pp.evaluate(POST_PUBLIC, "Harness fixture: a steady level")
    pc.close()
    sid = res.get("id") if isinstance(res, dict) else None
    check("a drawing with the steady song posts", bool(sid), json.dumps(res)[:200])

    if sid:
        lc = recorded(b, viewport={"width": 1280, "height": 900})
        lp = lc.new_page()
        lerrs = []
        lp.on("pageerror", lambda e: lerrs.append(str(e)))
        lp.goto(BASE + "/s/" + sid, wait_until="load")
        playerready.await_player(lp)
        lp.wait_for_timeout(1200)
        ready(lp)
        on = captured(lp, lambda: lp.click("#playerPlayBtn"), 900)
        check("the link page: Play begins the song from silence, gliding up over about 5ms", glides_in(on), say(on))
        mute = captured(lp, lambda: lp.click("#playerMuteBtn"))
        check("...the sound switch glides it down to silence", glides_out(mute), say(mute))
        unmute = captured(lp, lambda: lp.click("#playerMuteBtn"))
        check("...and back up again", glides_in(unmute), say(unmute))
        # Twice in a moment: the second glide begins inside the first, which
        # is where a glide that read the gain's own (lagging) value would jump.
        twice = captured(lp, lambda: lp.evaluate("""() => new Promise((res) => {
          const b = document.getElementById('playerMuteBtn'); b.click(); setTimeout(() => { b.click(); res(); }, 2); })"""),
          undo=lambda: None)
        check("...and pressed twice in a moment, nothing jumps", steady(twice),
              f"the biggest step anywhere {twice.get('maxStep')}; " + say(twice))
        off = captured(lp, lambda: lp.click("#playerPlayBtn"))
        check("...and Pause glides it down to silence", glides_out(off), say(off))
        cut = captured(lp, lambda: lp.evaluate(CUT), undo=lambda: None)
        check("a glide cut short 2ms in by another goes on from where it had got to",
              cut.get("sound") and not cut["gaps"] and 0 < cut["maxStep"] <= 0.5 / 50,
              f"the biggest step anywhere {cut.get('maxStep')} (a fiftieth of the level is 0.01); " + say(cut))
        check("the link page: no page errors", not lerrs, "; ".join(lerrs[:2]))
        lc.close()

        print("\nA POST'S BOX — play, pause and the sound switch (inlineplayer.js)")
        fc = recorded(b, viewport={"width": 620, "height": 900})
        fp = fc.new_page()
        ferrs = []
        fp.on("pageerror", lambda e: ferrs.append(str(e)))
        browsing.goto(fp, BASE, "/feed")
        BOXSEL = f'[data-skribl-id="{sid}"]'
        fp.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", BOXSEL)
        fp.wait_for_timeout(400)
        fp.evaluate("() => window.SkriblInline.setSoundOn(true)")
        # Once round first: the box makes its sound's context on its first
        # play, after fetching and decoding the post.
        fp.evaluate("(s) => document.querySelector(s).click()", BOXSEL); fp.wait_for_timeout(1500)
        fp.evaluate("(s) => document.querySelector(s).click()", BOXSEL); fp.wait_for_timeout(400)
        ready(fp)
        on = captured(fp, lambda: fp.evaluate("(s) => document.querySelector(s).click()", BOXSEL), 700)
        check("a post's box: play begins the song from silence, gliding up over about 5ms", glides_in(on), say(on))
        MUTE = f"""() => {{ const el = document.querySelector('{BOXSEL}');
          const line = el.nextElementSibling && el.nextElementSibling.querySelector('.skribl-inline-mute');
          (el.querySelector('.skribl-inline-mute') || line || document.querySelector('.skribl-inline-mute')).click(); }}"""
        mute = captured(fp, lambda: fp.evaluate(MUTE))
        check("...the sound switch glides it down to silence", glides_out(mute), say(mute))
        unmute = captured(fp, lambda: fp.evaluate(MUTE))
        check("...and back up again", glides_in(unmute), say(unmute))
        twice = captured(fp, lambda: fp.evaluate("() => new Promise((res) => { (" + MUTE + ")(); setTimeout(() => { (" + MUTE + ")(); res(); }, 2); })"),
                         undo=lambda: None)
        check("...and pressed twice in a moment, nothing jumps", steady(twice),
              f"the biggest step anywhere {twice.get('maxStep')}; " + say(twice))
        off = captured(fp, lambda: fp.evaluate("(s) => document.querySelector(s).click()", BOXSEL))
        check("...and pause glides it down to silence", glides_out(off), say(off))
        check("a post's box: no page errors", not ferrs, "; ".join(ferrs[:2]))
        fc.close()

    print("\nTHE FIRST START AFTER THE SOUND WAKES UP (lib/audioloop.js fadeIn)")
    wc = b.new_context(bypass_csp=True)
    wp = wc.new_page()
    werrs = []
    wp.on("pageerror", lambda e: werrs.append(str(e)))
    wp.goto(BASE + "/feed", wait_until="load")
    wp.add_script_tag(url=BASE + "/static/skribl/lib/audioloop.js")
    woke = wp.evaluate(WAKE, [REC_JS, 80])
    read = [w for w in woke if not w["gaps"] and w["f"] >= 0]
    jumped = [w["m"] for w in read if w["m"] > LEVEL / 50]
    check("80 first starts, each just after its sound wakes up: none jumps",
          len(read) >= 60 and not jumped,
          f"{len(jumped)} of {len(read)} read jumped" + (f" (by {', '.join(str(j) for j in jumped[:4])})" if jumped else "")
          + f"; the biggest step {max((w['m'] for w in read), default=None)} (a fiftieth of the level is {LEVEL / 50})"
          + (f"; {len(woke) - len(read)} not read" if len(read) < len(woke) else ""))
    check("...and no page errors", not werrs, "; ".join(werrs[:2]))
    wc.close()
    b.close()

passed = sum(1 for r in results if r[0])
print(f"\n{'=' * 62}\n{passed}/{len(results)} passed")
if passed != len(results):
    print("FAILURES: " + ", ".join(r[1] for r in results if not r[0]))
    raise SystemExit(1)
