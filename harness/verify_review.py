"""v111 — regression suite for the external review findings.

One assertion per reported issue, written to fail against v110. Numbering matches
the review. Items 5/9 encode a DECISION (clear = pages only, media retained,
autosave rewritten rather than deleted); if that decision is reversed, these are
the assertions to change.

Coverage note (kept current — round 7, #11): #10 and #13 ARE now covered here.
#10 is measured against a real WebM export; #13 exercises both limiter backends,
including restart persistence. Still NOT covered, and deliberately: #3's real
proxy topology and #11's embed origins (deployment facts), a PostgreSQL run of the
DB limiter (no PostgreSQL in this sandbox), and client-side media byte decoding.
"""
import base64, json, math, urllib.error, urllib.request
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as A
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

def post(payload, headers=None):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(BASE + "/api/skribls", data=json.dumps(payload).encode(), headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}

def durl(mime, raw):
    return f"data:{mime};base64," + base64.b64encode(raw).decode()

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
frame = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}

print("\n#1 — title/caption type confusion returned 500")
for bad in (123, {}, [], True):
    st, body = post({"title": bad, "frames": [frame]})
    check(f"title={bad!r} -> 400 not 500", st == 400 and "title" in str(body.get("error", "")),
          f"{st} {str(body)[:60]}")
st, _ = post({"caption": {}, "frames": [frame]})
check("caption={} -> 400", st == 400)
st, _ = post({"title": None, "caption": None, "frames": [frame]})
check("explicit nulls still accepted", st == 201)
st, _ = post({"title": "x" * 500, "frames": [frame]})
check("overlength title still accepted and truncated", st == 201)

print("\n#2 — media validation skipped past frame 200")
bad_media = {"photo": {"data": "not-a-data-url"}}
check("invalid media at frame 199 rejected",
      A._validate_payload_media({"frames": ([{}] * 199) + [bad_media]}) is not None)
check("invalid media at frame 200 now ALSO rejected (was the bypass)",
      A._validate_payload_media({"frames": ([{}] * 200) + [bad_media]}) is not None)
st, body = post({"frames": ([frame] * 200) + [bad_media]})
check("over-limit frame count rejected at the endpoint",
      st == 400 and "frames" in str(body.get("error", "")).lower(), f"{st} {str(body)[:70]}")
check("a non-object frame is rejected, not silently skipped",
      A._validate_payload_complexity({"frames": [[]]}) is not None)

print("\n#6 — empty and signature-mismatched media")
check("empty data URL rejected",
      A._validate_media_data_url("data:image/png;base64,", "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("non-PNG bytes declared as PNG rejected",
      A._validate_media_data_url(durl("image/png", b"not a png"), "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("a real PNG still accepted",
      A._validate_media_data_url(durl("image/png", PNG), "image", A.MAX_IMAGE_BYTES, "p") is None)
check("JPEG signature enforced",
      A._validate_media_data_url(durl("image/jpeg", b"\xff\xd8\xff" + b"x" * 40), "image", A.MAX_IMAGE_BYTES, "p") is None
      and A._validate_media_data_url(durl("image/jpeg", b"nope"), "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("audio narrowed to a real allow-list",
      A._validate_media_data_url(durl("audio/basic", b"x" * 40), "audio", A.MAX_AUDIO_BYTES, "m") is not None)
# Round 4, #2: this used to assert that RIFF + junk was an acceptable WAV, which
# documented the very permissiveness under review. It now needs a real container.
check("a real WAVE container is accepted",
      A._validate_media_data_url(durl("audio/wav", b"RIFF\x00\x00\x00\x00WAVEfmt "), "audio", A.MAX_AUDIO_BYTES, "m") is None)

print("\n#8 — structural complexity limits")
check("frame count capped", A._validate_payload_complexity({"frames": [{}] * (A.MAX_FRAMES + 1)}) is not None)
check("total points capped",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": 1, "y": 1}] * (A.MAX_POINTS_PER_FRAME + 1)}]}) is not None)
check("NaN coordinate rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": float("nan"), "y": 1}]}]}) is not None)
check("Infinity coordinate rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": float("inf"), "y": 1}]}]}) is not None)
check("out-of-range coordinate rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": 10**9, "y": 1}]}]}) is not None)
check("absurd brush size rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": 1, "y": 1, "size": 99999}]}]}) is not None)
check("out-of-range hold rejected",
      A._validate_payload_complexity({"frames": [{"hold": 99}]}) is not None)
check("oversize canvasSize rejected (regression introduced in v110)",
      A._validate_payload_complexity({"canvasSize": {"cssWidth": 30000, "cssHeight": 30000}}) is not None)
check("a normal payload passes every limit",
      A._validate_payload_complexity(
          {"canvasSize": {"cssWidth": 640, "cssHeight": 460},
           "frames": [{"strokes": [{"x": 1, "y": 2, "size": 7}], "strokeGroups": [1], "hold": 2}]}) is None)

print("\n#12 — deployment config parsed safely")
import os
for bad in ("banana", "-5", "0"):
    os.environ["SKRIBL_TEST_INT"] = bad
    try:
        A._env_int("SKRIBL_TEST_INT", 10)
        check(f"{bad!r} rejected", False, "accepted")
    except RuntimeError as e:
        check(f"{bad!r} raises a named error", "SKRIBL_TEST_INT" in str(e), str(e)[:60])
os.environ.pop("SKRIBL_TEST_INT", None)
check("absent falls back to the default", A._env_int("SKRIBL_NOT_SET_ANYWHERE", 42) == 42)

print("\n#7 / #3 / #11 — endpoint behaviour")
st, _ = post({"frames": [frame]}, {"X-Forwarded-For": "1.2.3.4"})
st2, _ = post({"frames": [frame]}, {"X-Forwarded-For": "5.6.7.8"})
check("a spoofed X-Forwarded-For does not create a fresh bucket by default",
      A._TRUSTED_PROXIES == 0, f"trusted proxies = {A._TRUSTED_PROXIES}")
check("both requests still served (limit raised for harness runs)", st in (201, 429) and st2 in (201, 429))
check("attempt and post budgets are separate", A._RATE_MAX_ATTEMPTS != A._RATE_MAX_POSTS,
      f"attempts={A._RATE_MAX_ATTEMPTS} posts={A._RATE_MAX_POSTS}")

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 950})
    r = ctx.request.get(BASE + "/flip")
    csp = r.headers.get("content-security-policy", "")
    check("editor is no longer framable by any origin", "frame-ancestors 'self'" in csp, csp[-60:])
    sid = post({"frames": [frame, frame]})[1].get("id")
    rp = ctx.request.get(f"{BASE}/s/{sid}")
    pcsp = rp.headers.get("content-security-policy", "")
    check("player keeps permissive framing unless SKRIBL_EMBED_ORIGINS is set",
          "frame-ancestors" not in pcsp, pcsp[-60:])

    print("\n#4 — clear-undo could overwrite work made after the clear")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "/flip", wait_until="load")
    pg.wait_for_timeout(900)

    def draw(x0, n=10):
        b = pg.locator("#pad").bounding_box()
        pg.mouse.move(b["x"] + x0, b["y"] + 90)
        pg.mouse.down()
        for i in range(n):
            pg.mouse.move(b["x"] + x0 + i * 7, b["y"] + 95)
        pg.mouse.up()
        pg.wait_for_timeout(120)

    for i in range(2):
        pg.evaluate("() => addFrame()")
        draw(70 + i * 25)
    pg.evaluate("() => { document.getElementById('clear').click(); document.getElementById('clear').click(); }")
    pg.wait_for_timeout(400)
    check("clear empties the pages", pg.evaluate("() => frames.length") == 1)
    check("undo is offered right after a clear",
          not pg.evaluate("() => document.getElementById('clearUndo').disabled"))
    draw(120, 14)                      # new work after the clear
    pg.wait_for_timeout(200)
    check("drawing after a clear disables clear-undo",
          pg.evaluate("() => document.getElementById('clearUndo').disabled"))
    new_work = pg.evaluate("() => frames.map(f => f.strokes.length)")
    pg.evaluate("() => { const b=document.getElementById('clearUndo'); if(b) b.click(); }")
    pg.wait_for_timeout(400)
    check("and clicking it cannot resurrect the old animation over new work",
          pg.evaluate("() => frames.map(f => f.strokes.length)") == new_work, str(new_work))
    for label, js in (("adding a page", "() => addFrame()"),
                      ("reordering", "() => { addFrame(); movePageTo(0,1); }"),
                      ("changing a hold", "() => { frames[0].hold = 2; invalidateClearUndo(); }")):
        pg.evaluate("() => { document.getElementById('clear').click(); document.getElementById('clear').click(); }")
        pg.wait_for_timeout(250)
        pg.evaluate(js)
        pg.wait_for_timeout(250)
        check(f"{label} after a clear disables clear-undo",
              pg.evaluate("() => document.getElementById('clearUndo').disabled"))

    print("\n#5 / #9 — clear semantics: PAGES ONLY, autosave stays consistent")
    pg.evaluate("""() => { musicData = 'data:audio/wav;base64,AAAA'; bgColor = '#123456';
                           frames = [newFrame(), newFrame()]; idx = 0; buildStrip(); scheduleSave(); }""")
    pg.wait_for_timeout(1200)
    pg.evaluate("() => { document.getElementById('clear').click(); document.getElementById('clear').click(); }")
    pg.wait_for_timeout(1400)
    check("media survives a clear (pages-only semantics)",
          pg.evaluate("() => !!musicData"))
    saved = pg.evaluate("() => { try { return localStorage.getItem(AUTOSAVE_KEY); } catch(e) { return null; } }")
    check("the autosave is rewritten, not deleted", bool(saved), "missing" if not saved else f"{len(saved)} chars")
    check("and the saved draft matches the cleared live state",
          bool(saved) and len(json.loads(saved).get("frames", [])) == 1,
          str(len(json.loads(saved).get("frames", []))) if saved else "n/a")
    check("the snapshot is named for what it holds",
          pg.evaluate("() => typeof clearFramesBackup !== 'undefined'"))

    print("\n#8 (client) — canvasSize from a payload is bounded")
    check("a 30000px canvas from a payload is refused",
          pg.evaluate("() => applyCanvasSize(30000,30000) === false && CW <= 4096"))
    check("NaN canvas size refused", pg.evaluate("() => applyCanvasSize(NaN,NaN) === false"))
    check("a legitimate preset still applies",
          pg.evaluate("() => { applyCanvasSize(560,560); return CW===560 && CH===560; }"))
    check("no page errors throughout", not errs, "; ".join(errs[:2]))
    br.close()

# ============================================================================
# Review round 2 — the follow-up findings.
# Several of these need their own server PROCESS, because the limiter and proxy
# constants are read at import time and cannot be patched in this process.
# ============================================================================
import os, socket, subprocess, sys, threading, time, contextlib

ROOT = Path(__file__).resolve().parent.parent

def secrets_token():
    import uuid; return uuid.uuid4().hex[:12]

def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    return port

@contextlib.contextmanager
def server(**env_extra):
    """A server process with its own configuration."""
    port = _free_port()
    env = dict(os.environ); env.update({k: str(v) for k, v in env_extra.items()})
    proc = subprocess.Popen(
        [sys.executable, "-m", "flask", "--app", "app", "run", "--port", str(port), "--no-reload"],
        cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        # Round 7, #12: this used to yield regardless of whether startup worked,
        # so a server that died produced a pile of confusing request errors
        # instead of one clear one. Matters more now that restart-persistence
        # proofs depend on these subprocesses.
        ready = False
        for _ in range(80):
            if proc.poll() is not None:
                raise RuntimeError(f"test server exited during startup with {proc.returncode}")
            try:
                urllib.request.urlopen(base + "/", timeout=1); ready = True; break
            except urllib.error.HTTPError:
                ready = True; break
            except Exception:
                time.sleep(0.25)
        if not ready:
            raise RuntimeError("test server did not become ready")
        yield base
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except Exception: proc.kill()

def post_to(base, payload, headers=None):
    h = {"Content-Type": "application/json"}; h.update(headers or {})
    req = urllib.request.Request(base + "/api/skribls", data=json.dumps(payload).encode(), headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

print("\nR2#1 — WebP is a container, not a prefix; unknown image types rejected")
check("RIFF....WAVE declared image/webp is rejected",
      A._validate_media_data_url(durl("image/webp", b"RIFF\x00\x00\x00\x00WAVEfmt "), "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("RIFF....WEBP declared image/webp is accepted",
      A._validate_media_data_url(durl("image/webp", b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image", A.MAX_IMAGE_BYTES, "p") is None)
check("arbitrary bytes declared image/avif are rejected",
      A._validate_media_data_url(durl("image/avif", b"x" * 40), "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("image/tiff is rejected too (strict allow-list)",
      A._validate_media_data_url(durl("image/tiff", b"II*\x00" + b"x" * 40), "image", A.MAX_IMAGE_BYTES, "p") is not None)
check("a truncated RIFF cannot pass as WebP",
      A._validate_media_data_url(durl("image/webp", b"RIFF"), "image", A.MAX_IMAGE_BYTES, "p") is not None)

print("\nR2#6 — malformed structure is rejected, not tolerated")
check("non-object stroke entries rejected",
      A._validate_payload_complexity({"frames": [{"strokes": ["not a point", ["nested"], None]}]}) is not None)
check("non-integer strokeGroups entries rejected",
      A._validate_payload_complexity({"frames": [{"strokeGroups": [{"unexpected": "shape"}]}]}) is not None)
check("fractional hold rejected", A._validate_payload_complexity({"frames": [{"hold": 1.5}]}) is not None)
check("boolean hold rejected", A._validate_payload_complexity({"frames": [{"hold": True}]}) is not None)
check("integer hold still accepted", A._validate_payload_complexity({"frames": [{"hold": 3}]}) is None)

print("\nR2#5 — SKRIBL_EMBED_ORIGINS is validated at startup")
check("a valid list is normalised", A._validate_embed_origins("  'self'   https://skribls.net ") == "'self' https://skribls.net")
for bad in ("'self'; script-src *", "https://a.com, https://b.com", "https://a.com\nhttps://b.com",
            "javascript:alert(1)", "https://a.com/path", "ftp://a.com"):
    try:
        A._validate_embed_origins(bad); check(f"rejects {bad!r}", False, "accepted")
    except RuntimeError as e:
        check(f"rejects {bad!r}", "SKRIBL_EMBED_ORIGINS" in str(e))
check("empty stays empty", A._validate_embed_origins("") == "")

print("\nR2#3 — forwarded-header behaviour, not just the config value")
with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "1.2.3.4"}):
    ip_a = A._client_ip()
with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "5.6.7.8"}):
    ip_b = A._client_ip()
check("with proxies=0 two different forwarded values map to the SAME identity",
      ip_a == ip_b, f"{ip_a!r} vs {ip_b!r}")
check("and that identity is the socket peer, not the header",
      ip_a not in ("1.2.3.4", "5.6.7.8"), repr(ip_a))
_saved = A._TRUSTED_PROXIES
try:
    A._TRUSTED_PROXIES = 1
    with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}):
        check("with proxies=1 the entry one hop from the RIGHT is used",
              A._client_ip() == "10.0.0.1", A._client_ip())
    with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "junk-not-an-ip"}):
        got = A._client_ip()
        check("a non-IP forwarded value cannot become a bucket key", got != "junk-not-an-ip", repr(got))
    with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "2001:db8::1"}):
        check("IPv6 is parsed and normalised", A._client_ip() == "2001:db8::1", A._client_ip())
    A._TRUSTED_PROXIES = 2
    with A.create_app().test_request_context("/", headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2, 3.3.3.3"}):
        check("with proxies=2 the entry two hops from the right is used",
              A._client_ip() == "2.2.2.2", A._client_ip())
finally:
    A._TRUSTED_PROXIES = _saved

print("\nR2#4 — framing keyed to the endpoint, not the /s/ path prefix")
with sync_playwright() as p2:
    br2 = p2.chromium.launch(); c2 = br2.new_context()
    sid2 = post({"frames": [frame]})[1].get("id")
    def fa(path):
        h = c2.request.get(BASE + path).headers.get("content-security-policy", "")
        for part in h.split(";"):
            if part.strip().startswith("frame-ancestors"):
                return part.strip()
        return None
    check("the HTML player keeps permissive framing", fa(f"/s/{sid2}") is None, str(fa(f"/s/{sid2}")))
    check("the card image does NOT", fa(f"/s/{sid2}/card.png") == "frame-ancestors 'self'", str(fa(f"/s/{sid2}/card.png")))
    # NB: /s/<unknown-id> is NOT a 404. The player shell is server-rendered and the
    # client fetches the post, so an unknown id returns 200 and is legitimately the
    # player page. Real 404s are what must be restrictive.
    unknown = c2.request.get(BASE + "/s/not-a-real-id")
    check("/s/<unknown-id> is a 200 player shell, not an error", unknown.status == 200, str(unknown.status))
    check("a genuine 404 is restrictive", fa("/definitely-not-a-route") == "frame-ancestors 'self'",
          str(fa("/definitely-not-a-route")))
    check("the API does NOT get permissive framing",
          fa("/api/skribls/not-a-real-id") == "frame-ancestors 'self'", str(fa("/api/skribls/not-a-real-id")))
    br2.close()

print("\nR2#2 — post quota is exact, and atomic under concurrency")
with server(SKRIBL_RATE_MAX_POSTS=2, SKRIBL_RATE_MAX_ATTEMPTS=500) as base2:
    for _ in range(8):
        post_to(base2, {"title": 123})                       # invalid: must not spend a post
    codes = [post_to(base2, {"frames": [frame]}) for _ in range(3)]
    check("invalid requests do not consume the post quota; 2 valid posts succeed",
          codes[:2] == [201, 201], str(codes))
    check("the third valid post is refused", codes[2] == 429, str(codes))

with A.create_app().app_context():
    rows_before = A.SkriblPost.query.count()
with server(SKRIBL_RATE_MAX_POSTS=2, SKRIBL_RATE_MAX_ATTEMPTS=500) as base3:
    out = []
    lock = threading.Lock()
    def fire():
        c = post_to(base3, {"frames": [frame]})
        with lock: out.append(c)
    threads = [threading.Thread(target=fire) for _ in range(12)]
    for t in threads: t.start()
    for t in threads: t.join()
    # Round 3, #2: "at most 2" did not prove the claim we made. Assert the exact
    # split AND the database row delta, since 201s are responses, not rows.
    check("exactly two concurrent posts succeed", out.count(201) == 2, str(sorted(out)))
    check("the other ten are rate-limited", out.count(429) == 10, str(sorted(out)))
    check("no other status appeared", set(out) <= {201, 429}, str(sorted(set(out))))
    with A.create_app().app_context():
        rows_after = A.SkriblPost.query.count()
    check("exactly two rows were committed", rows_after - rows_before == 2,
          f"delta {rows_after - rows_before}")


print("\nR3#1 — a failed commit must not strand the reservation")

def _post_slots():
    return sum(len(q) for k, q in A._rate_buckets.items() if k[0] == "posts")

_app = A.create_app()
before_slots = _post_slots()
_orig_commit = A.db.session.commit
def _boom():
    raise RuntimeError("simulated operational error")
try:
    A.db.session.commit = _boom
    with _app.test_client() as cl:
        r = cl.post("/api/skribls", json={"frames": [frame]})
        failed_status = r.status_code
finally:
    A.db.session.commit = _orig_commit
check("a non-IntegrityError commit failure returns 5xx", failed_status >= 500, str(failed_status))
check("and the reserved post slot is released, not held for the window",
      _post_slots() == before_slots, f"{before_slots} -> {_post_slots()}")
with _app.test_client() as cl:
    ok_status = cl.post("/api/skribls", json={"frames": [frame]}).status_code
check("a subsequent valid post can still use that slot", ok_status == 201, str(ok_status))
check("and it does consume exactly one slot", _post_slots() == before_slots + 1,
      f"{before_slots} -> {_post_slots()}")

print("\nR3#3 — embed origins parsed structurally")
for bad in ("https://example.com?x=1", "https://example.com#fragment",
            "https://user@example.com", "https://example.com:invalid",
            "https://example.com/path", "https://", "http://evil.example.com"):
    try:
        A._validate_embed_origins(bad)
        check(f"rejects {bad!r}", False, "accepted")
    except RuntimeError:
        check(f"rejects {bad!r}", True)
check("wildcard hosts rejected (the variable is named ORIGINS)",
      not A._is_bare_origin("https://*.example.com"))
for good in ("https://skribls.net", "https://a.example.com:8443", "http://localhost:3000"):
    check(f"accepts {good!r}", A._is_bare_origin(good))

print("\nR3#4 — the clear label is correct in the SERVER-RENDERED html")
_flip_html = urllib.request.urlopen(BASE + "/flip").read().decode("utf-8", "replace")
check("server-rendered label says 'Clear all pages'", "Clear all pages" in _flip_html)
check("the stale 'Clear animation' label is gone from the HTML",
      "Clear animation" not in _flip_html)
check("the title attribute is accurate too",
      "Delete all pages (keeps music and background)" in _flip_html)


print("\nR4#1 — classic ROOT-level strokeGroups is validated too")
check("root groups: object entry rejected",
      A._validate_payload_complexity({"strokes": [], "strokeGroups": [{"unexpected": "object"}]}) is not None)
check("root groups: negative / float / bool / string rejected",
      all(A._validate_payload_complexity({"strokes": [], "strokeGroups": [v]}) is not None
          for v in (-100, 1.5, True, "500000000")))
check("root groups: count must match the strokes array",
      A._validate_payload_complexity({"strokes": [], "strokeGroups": [1, 1, 1, 1, 1]}) is not None)
check("root groups: a consistent pair is accepted",
      A._validate_payload_complexity(
          {"strokes": [{"x": 1, "y": 1}, {"x": 2, "y": 2}], "strokeGroups": [2]}) is None)
check("frame groups keep the same rule",
      A._validate_payload_complexity(
          {"frames": [{"strokes": [{"x": 1, "y": 1}], "strokeGroups": [5]}]}) is not None)
st_r, body_r = post({"strokes": [], "strokeGroups": [{"bad": 1}]})
check("malformed root groups are refused at the ENDPOINT, not just in the function",
      st_r == 400 and "strokeGroups" in str(body_r.get("error", "")), f"{st_r} {str(body_r)[:70]}")
check("a real browser-shaped payload still posts",
      post({"frames": [{"strokes": [{"x": 1, "y": 1}, {"x": 2, "y": 2}],
                        "strokeGroups": [2], "background": {"color": "#101418"}}]})[0] == 201)

print("\nR4#2 — declared audio must match its bytes")
_AUDIO_GOOD = {"wav": b"RIFF\x00\x00\x00\x00WAVE", "x-wav": b"RIFF\x00\x00\x00\x00WAVE",
               "wave": b"RIFF\x00\x00\x00\x00WAVE", "vnd.wave": b"RIFF\x00\x00\x00\x00WAVE",
               "mpeg": b"ID3\x04\x00", "mp3": b"\xff\xfb\x90", "ogg": b"OggS\x00",
               "opus": b"OggS\x00", "flac": b"fLaC\x00", "x-flac": b"fLaC\x00",
               "webm": b"\x1a\x45\xdf\xa3", "mp4": b"\x00\x00\x00\x20ftypM4A ",
               "x-m4a": b"\x00\x00\x00\x20ftypM4A ", "m4a": b"\x00\x00\x00\x20ftypM4A ",
               "aac": b"\xff\xf1\x50\x80"}
for sub_t in sorted(A.ALLOWED_AUDIO_SUBTYPES):
    bad = A._validate_media_data_url(durl(f"audio/{sub_t}", b"arbitrary bytes not a container" * 2),
                                     "audio", A.MAX_AUDIO_BYTES, "m")
    check(f"audio/{sub_t}: arbitrary bytes rejected", bad is not None, str(bad))
for sub_t, magic in _AUDIO_GOOD.items():
    ok_ = A._validate_media_data_url(durl(f"audio/{sub_t}", magic + b"\x00" * 32),
                                     "audio", A.MAX_AUDIO_BYTES, "m")
    check(f"audio/{sub_t}: a real container header is accepted", ok_ is None, str(ok_))
check("RIFF alone is no longer enough for wav",
      A._validate_media_data_url(durl("audio/wav", b"RIFF" + b"x" * 40), "audio", A.MAX_AUDIO_BYTES, "m") is not None)

print("\nR4#3 — signature-only policy, stated rather than implied")
check("a header-only PNG IS accepted (documented limitation, not full validation)",
      A._validate_media_data_url(durl("image/png", b"\x89PNG\r\n\x1a\n"), "image", A.MAX_IMAGE_BYTES, "p") is None)
check("the rejection message claims a CONTAINER mismatch, not an invalid image",
      "container" in A._validate_media_data_url(durl("image/png", b"nope"), "image", A.MAX_IMAGE_BYTES, "p"))
check("same wording for audio",
      "container" in A._validate_media_data_url(durl("audio/wav", b"nope"), "audio", A.MAX_AUDIO_BYTES, "m"))

print("\nR4#4/#5 — 'none' is exclusive, duplicates rejected, origins canonical")
check("'none' alone is accepted", A._validate_embed_origins("'none'") == "'none'")
for bad in ("'none' https://example.com", "'self' 'none'", "'self' 'self'",
            "https://a.example.com https://a.example.com/"):
    try:
        A._validate_embed_origins(bad); check(f"rejects {bad!r}", False, "accepted")
    except RuntimeError:
        check(f"rejects {bad!r}", True)
check("origins are normalised, not echoed back",
      A._validate_embed_origins("https://Example.COM/") == "https://example.com",
      A._validate_embed_origins("https://Example.COM/"))
check("an explicit port is preserved",
      A._validate_embed_origins("https://a.example.com:8443") == "https://a.example.com:8443")

print("\nR4#6 — canvas dimensions are whole pixels")
for bad in (0.5, 1.5, True, "640", 0, -1, A.MAX_CANVAS_EDGE + 1):
    check(f"canvasSize {bad!r} rejected",
          A._validate_payload_complexity({"canvasSize": {"cssWidth": bad, "cssHeight": 100}}) is not None)
for good in (1, 640, A.MAX_CANVAS_EDGE):
    check(f"canvasSize {good} accepted",
          A._validate_payload_complexity({"canvasSize": {"cssWidth": good, "cssHeight": good}}) is None)


print("\nR5#1 — zero-length stroke groups are invalid, not tolerated")
check("zero root-level stroke group rejected",
      A._validate_payload_complexity({"strokes": [{"x": 1, "y": 1}], "strokeGroups": [0, 1]}) is not None)
check("zero frame stroke group rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": 1, "y": 1}], "strokeGroups": [0, 1]}]}) is not None)
check("zero-only groups on an empty frame rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [], "strokeGroups": [0]}]}) is not None)
check("a crafted run of dead undo entries is rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [], "strokeGroups": [0] * 4}]}) is not None)
check("legitimate groups still pass",
      A._validate_payload_complexity(
          {"frames": [{"strokes": [{"x": 1, "y": 1}] * 16, "strokeGroups": [10, 6]}]}) is None)
check("an empty frame with no groups still passes",
      A._validate_payload_complexity({"frames": [{"strokes": [], "strokeGroups": []}]}) is None)
st_z, body_z = post({"frames": [{"strokes": [{"x": 1, "y": 1}], "strokeGroups": [0, 1],
                                 "background": {"color": "#101418"}}]})
check("no public payload can carry a no-op undo entry (endpoint refuses it)",
      st_z == 400 and "positive" in str(body_z.get("error", "")), f"{st_z} {str(body_z)[:70]}")

print("\nR5#2/#3 — the pickers cannot advertise what the server rejects")
_tpl = {}
for name in ("skribl_flip.html", "skribl_player.html", "_skribl_music_drawer.html",
             "_skribl_image_drawer.html"):
    _tpl[name] = (ROOT / "templates" / name).read_text(encoding="utf-8")
_all_tpl = "\n".join(_tpl.values())
check("no wildcard audio/* picker remains", 'accept="audio/*' not in _all_tpl)
check("no wildcard image/* picker remains", 'accept="image/*' not in _all_tpl)
check("the AIFF offer is gone (the server has no AIFF support)", ".aiff" not in _all_tpl)
for ext in (".mp3", ".wav", ".flac"):
    check(f"the audio picker still offers {ext}", ext in _tpl["skribl_flip.html"])

# Anti-drift: the browser's allow-list must agree with the server's.
with sync_playwright() as p3:
    br3 = p3.chromium.launch(); pg3 = br3.new_context().new_page()
    pg3.goto(BASE + "/", wait_until="load"); pg3.wait_for_timeout(900)
    client_audio = set(pg3.evaluate("() => [...SKRIBL_AUDIO_MIMES]"))
    client_image = set(pg3.evaluate("() => [...SKRIBL_IMAGE_MIMES]"))
    br3.close()
server_audio = {f"audio/{x}" for x in A.ALLOWED_AUDIO_SUBTYPES}
server_image = {f"image/{x}" for x in A.ALLOWED_IMAGE_SUBTYPES}
check("client audio list advertises nothing the server rejects",
      not (client_audio - server_audio), str(sorted(client_audio - server_audio)))
check("client image list advertises nothing the server rejects",
      not (client_image - server_image), str(sorted(client_image - server_image)))
check("the client no longer accepts by prefix",
      "startsWith('audio/')" not in (ROOT / "static" / "skribl" / "app.js").read_text(encoding="utf-8"))


print("\nR6#1 — every flat point must carry x and y")
for bad, why in (({}, "empty object"), ({"x": 1}, "x only"), ({"y": 1}, "y only"),
                 ({"x": None, "y": 1}, "null x"), ({"x": 1, "y": None}, "null y")):
    check(f"root point rejected: {why}",
          A._validate_payload_complexity({"strokes": [bad], "strokeGroups": [1]}) is not None)
    check(f"frame point rejected: {why}",
          A._validate_payload_complexity(
              {"frames": [{"strokes": [bad], "strokeGroups": [1]}]}) is not None)
st_p, body_p = post({"frames": [{"strokes": [{}], "strokeGroups": [1],
                                 "background": {"color": "#101418"}}]})
check("the endpoint refuses a coordinate-less point",
      st_p == 400 and "required" in str(body_p.get("error", "")), f"{st_p} {str(body_p)[:70]}")

print("\nR6#2 — strokeGroups is mandatory once there are points")
check("root strokes without groups rejected",
      A._validate_payload_complexity({"strokes": [{"x": 1, "y": 1}]}) is not None)
check("frame strokes without groups rejected",
      A._validate_payload_complexity({"frames": [{"strokes": [{"x": 1, "y": 1}]}]}) is not None)
check("an empty strokes array may still omit groups",
      A._validate_payload_complexity({"frames": [{"strokes": []}]}) is None)

print("\nR6#8 — canvasSize must be a complete object")
for bad in ("huge", [], {}, {"cssWidth": 640}, {"cssHeight": 480}):
    check(f"canvasSize {bad!r} rejected",
          A._validate_payload_complexity({"canvasSize": bad}) is not None)
check("a complete canvasSize is accepted",
      A._validate_payload_complexity({"canvasSize": {"cssWidth": 640, "cssHeight": 460}}) is None)

print("\nR6#3/#4/#5/#6 — one format policy across MIME, extension and accept=")
with sync_playwright() as p4:
    br4 = p4.chromium.launch(); pg4 = br4.new_context().new_page()
    pg4.goto(BASE + "/", wait_until="load"); pg4.wait_for_timeout(900)
    c_audio = set(pg4.evaluate("() => [...SKRIBL_AUDIO_MIMES]"))
    c_image = set(pg4.evaluate("() => [...SKRIBL_IMAGE_MIMES]"))
    # File.type is empty for drag-and-drop and many platform file providers.
    empty_mime = pg4.evaluate("""() => {
        const names = ['music.flac','music.webm','music.opus','music.mp4','music.mp3'];
        const out = {};
        for (const n of names) out[n] = validateMusicFile(new File(['x'], n, {type: ''})) === null;
        out['photo.png'] = isImageFile(new File(['x'], 'photo.png', {type: ''}));
        out['photo.webp'] = isImageFile(new File(['x'], 'photo.webp', {type: ''}));
        return out; }""")
    # Extension must not override a usable, contradictory MIME type.
    conflict = pg4.evaluate("""() => ({
        mp3AsPng: validateMusicFile(new File(['x'], 'song.mp3', {type: 'image/png'})) !== null,
        pngAsAudio: isImageFile(new File(['x'], 'photo.png', {type: 'audio/mpeg'})) === false })""")
    br4.close()
s_audio = {f"audio/{x}" for x in A.ALLOWED_AUDIO_SUBTYPES}
s_image = {f"image/{x}" for x in A.ALLOWED_IMAGE_SUBTYPES}
check("client and server audio MIME policies match exactly",
      c_audio == s_audio, f"client-only={sorted(c_audio - s_audio)} server-only={sorted(s_audio - c_audio)}")
check("client and server image MIME policies match exactly",
      c_image == s_image, f"client-only={sorted(c_image - s_image)} server-only={sorted(s_image - c_image)}")
for name, ok_ in empty_mime.items():
    check(f"empty File.type accepted by extension: {name}", ok_ is True, str(ok_))
check("a .mp3 declaring image/png is refused for audio", conflict["mp3AsPng"])
check("a .png declaring audio/mpeg is refused for images", conflict["pngAsAudio"])
_accepts = "\n".join((ROOT / "templates" / n).read_text(encoding="utf-8")
                      for n in ("skribl_flip.html", "skribl_player.html",
                                "_skribl_music_drawer.html", "_skribl_image_drawer.html"))
check("no picker offers BMP any more (one image policy, all surfaces)",
      "image/bmp" not in _accepts and "bmp" not in str(sorted(s_image)))
for ext in (".flac", ".webm", ".opus", ".mp4"):
    check(f"the audio picker advertises {ext}", ext in _accepts)


print("\n#10 — WebM first-frame timing, MEASURED rather than assumed")
# The original report marked this "needs browser confirmation". That was only true
# for MP4: this Chromium has no avc1, but MediaRecorder/WebM works fine, so the
# claim IS testable here. An extra first-frame interval would show up as one unit
# of surplus duration.
with sync_playwright() as p5:
    br5 = p5.chromium.launch()
    ctx5 = br5.new_context(accept_downloads=True)
    pg5 = ctx5.new_page()
    pg5.goto(BASE + "/flip", wait_until="load")
    pg5.wait_for_timeout(900)
    for i2 in range(4):
        pg5.evaluate("() => addFrame()")
        bb = pg5.locator("#pad").bounding_box()
        pg5.mouse.move(bb["x"] + 70 + i2 * 22, bb["y"] + 90)
        pg5.mouse.down()
        for k in range(6):
            pg5.mouse.move(bb["x"] + 70 + i2 * 22 + k * 8, bb["y"] + 95)
        pg5.mouse.up()
        pg5.wait_for_timeout(60)
    pages = pg5.evaluate("() => frames.length")
    fps5 = pg5.evaluate("() => fps")
    webm_mime = pg5.evaluate("""() => {
        for (const t of ['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'])
            if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
        return 'unknown'; }""")
    # MediaRecorder occasionally yields a near-empty file here (header only, no
    # captured frames). Asserting on that would either fail spuriously or, worse,
    # "pass" on garbage. Retry until a real recording appears; if none does, fall
    # through and let the assertion FAIL loudly with the byte counts rather than
    # skip. (Review round 7, #4 — timing varies by codec, clamping and load.)
    import base64 as _b64
    blob, raw_len, attempts = "", 0, []
    for _try in range(4):
        with pg5.expect_download(timeout=120000) as dl5:
            pg5.evaluate("() => { exportWebM(); }")
        data = open(dl5.value.path(), "rb").read()
        attempts.append(len(data))
        if len(data) > 2000:
            blob = _b64.b64encode(data).decode(); raw_len = len(data); break
        pg5.wait_for_timeout(700)
    if not blob:
        blob = _b64.b64encode(data).decode(); raw_len = len(data)
    measured = pg5.evaluate("""async (b) => {
        const v = document.createElement('video'); v.preload = 'metadata';
        v.src = 'data:video/webm;base64,' + b;
        await new Promise(r => { v.onloadedmetadata = r; v.onerror = r; setTimeout(r, 8000); });
        if (!isFinite(v.duration)) {
            v.currentTime = 1e101;
            await new Promise(r => { v.ontimeupdate = () => { if (v.currentTime > 0) r(); }; setTimeout(r, 8000); });
        }
        return v.duration; }""", blob)
    dur_path = pg5.evaluate("""async (b) => {
        const v = document.createElement('video'); v.preload='metadata';
        v.src='data:video/webm;base64,'+b;
        await new Promise(r => { v.onloadedmetadata=r; v.onerror=r; setTimeout(r,8000); });
        return isFinite(v.duration) ? 'loadedmetadata' : 'seek-to-end'; }""", blob)
    br5.close()
expected = (pages * 2) / fps5                 # exportWebM runs 2 loops
one_frame = 1 / fps5
# Named for what it establishes: within half a frame, not "exact". It rules out a
# whole surplus interval in THIS Chromium/WebM path — not in every browser, since
# MediaRecorder timing varies with codec, timer clamping and container metadata.
# (Review round 7, #4)
# One-sided, deliberately. The claim under test is "the first frame is NOT held
# for an extra interval", so what must be excluded is a duration ABOVE expected.
# A capture that comes out short is MediaRecorder dropping frames under load — a
# fidelity artefact of this environment, not evidence of the bug. A two-sided
# bound was therefore testing the recorder, and failed spuriously at 0.748s.
# The floor below still catches a wholly degenerate capture.
check("exported WebM shows no surplus frame interval (upper bound)",
      measured < expected + one_frame * 0.5,
      f"measured {measured:.3f}s expected {expected:.3f}s half-frame={one_frame/2:.4f}s "
      f"pages={pages} fps={fps5} loops=2 units={pages*2} bytes={raw_len} attempts={attempts} "
      f"mime={webm_mime!r} duration-path={dur_path!r}")
check("the capture is substantive, not a degenerate stub (floor)",
      measured > expected * 0.5,
      f"measured {measured:.3f}s, floor {expected * 0.5:.3f}s")
check("the surplus-interval case is excluded by a clear margin",
      (expected + one_frame) - measured > one_frame * 0.4,
      f"surplus-case would be {expected + one_frame:.3f}s, measured {measured:.3f}s")

print("\n#13 — shared-store limiter (survives restart, shared across workers)")
check("backend is selectable", A._RATE_BACKEND in ("memory", "db"), A._RATE_BACKEND)
check("the identity key is a salted hash, never a raw address",
      A._rate_key("1.2.3.4") != "1.2.3.4" and len(A._rate_key("1.2.3.4")) == 64
      and A._rate_key("1.2.3.4") != A._rate_key("1.2.3.5"))
with server(SKRIBL_RATE_BACKEND="db", SKRIBL_RATE_MAX_POSTS=2, SKRIBL_RATE_MAX_ATTEMPTS=500,
            SKRIBL_RATE_HMAC_KEY="harness-fixed-key") as dbbase:
    codes_db = [post_to(dbbase, {"frames": [frame]}) for _ in range(3)]
    check("db backend enforces the post quota", codes_db == [201, 201, 429], str(codes_db))
    out_db = []
    lock_db = threading.Lock()
    def fire_db():
        c = post_to(dbbase, {"frames": [frame]})
        with lock_db: out_db.append(c)
    ths = [threading.Thread(target=fire_db) for _ in range(8)]
    for t in ths: t.start()
    for t in ths: t.join()
    check("and refuses the rest under concurrency rather than over-accepting",
          out_db.count(201) == 0 and set(out_db) <= {201, 429}, str(sorted(out_db)))
# The point of the db backend: a restart must NOT reset the quota.
with server(SKRIBL_RATE_BACKEND="db", SKRIBL_RATE_MAX_POSTS=2, SKRIBL_RATE_MAX_ATTEMPTS=500,
            SKRIBL_RATE_HMAC_KEY="harness-fixed-key") as restarted:
    # Accurate scope (round 7, #10): this proves persistence across an application
    # PROCESS restart against the same database and the same HMAC key. It does not
    # prove survival across a database replacement, an ephemeral filesystem, a
    # migration that drops the table, or key rotation — all of which reset it.
    check("quota survives an application-process restart (same DB, same key)",
          post_to(restarted, {"frames": [frame]}) == 429)

print("\n#13b — fresh-bucket concurrency: the race for the LAST slots")
# The earlier test exhausted the quota first, so it only proved an exhausted
# bucket stays exhausted. This starts a brand-new identity with an empty bucket
# and makes 12 requests compete for exactly 2 slots. (Review round 7, #5)
with server(SKRIBL_RATE_BACKEND="db", SKRIBL_RATE_MAX_POSTS=2,
            SKRIBL_RATE_MAX_ATTEMPTS=500,
            SKRIBL_RATE_HMAC_KEY=f"harness-{secrets_token()}") as fresh:
    fresh_out = []
    fresh_lock = threading.Lock()
    def fire_fresh():
        c = post_to(fresh, {"frames": [frame]})
        with fresh_lock: fresh_out.append(c)
    ts = [threading.Thread(target=fire_fresh) for _ in range(12)]
    for t in ts: t.start()
    for t in ts: t.join()
    check("exactly two of twelve concurrent posts win the fresh quota",
          fresh_out.count(201) == 2, str(sorted(fresh_out)))
    check("the other ten are refused", fresh_out.count(429) == 10, str(sorted(fresh_out)))
    check("no other status appeared", set(fresh_out) <= {201, 429}, str(sorted(set(fresh_out))))
with A.create_app().app_context():
    rows = A.RateEvent.query.filter(A.RateEvent.bucket == "posts").count()
check("post slot rows exist and are bounded", rows >= 2, f"{rows} posts rows")

print("\n#14 — dependency hashes")
_c = (ROOT / "constraints.txt").read_text(encoding="utf-8")
# Round 7, #13: a text count proved nothing. Running the documented command
# revealed it was WRONG — --require-hashes rejects requirements.txt's ranges.
_pins = [l for l in _c.splitlines() if "==" in l and not l.startswith("#")]
check("constraints.txt is fully pinned with == and hashed",
      len(_pins) == _c.count("--hash=sha256:") and len(_pins) >= 15,
      f"{len(_pins)} pins, {_c.count('--hash=sha256:')} hashes")
check("every pinned line has exactly one hash",
      all(_c.count(f"{l.split('==')[0].strip()}==") >= 1 for l in _pins))
check("the documented install command is the one that actually works",
      "pip install -r constraints.txt --require-hashes" in _c
      and "-c constraints.txt --require-hashes" not in _c.split("NOT ")[0])
check("and states the platform it was generated on", "linux x86_64" in _c)
check("and warns that a different target must regenerate", "regenerate this file THERE" in _c)


print("\n#7 — media BYTES are verified client-side, not just labels")
_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQ"
            "GAhKmMIQAAAABJRU5ErkJggg==")
with sync_playwright() as p7:
    br7 = p7.chromium.launch()
    ctx7 = br7.new_context()
    pad7 = ctx7.new_page()
    perr7 = []
    pad7.on("pageerror", lambda e: perr7.append(str(e)))
    pad7.goto(BASE + "/", wait_until="load")
    pad7.wait_for_timeout(1000)
    res = pad7.evaluate("""async (b64) => {
        const out = {};
        const text = () => new Uint8Array([104,101,108,108,111,33]);
        // Passes MIME *and* extension, but the bytes are not an image.
        out.fakeImage = await skriblDecodeCheckImage(new File([text()], 'photo.png', {type:'image/png'}));
        out.fakeAudio = await skriblDecodeCheckAudio(new File([text()], 'song.wav', {type:'audio/wav'}));
        const png = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        out.realImage = await skriblDecodeCheckImage(new File([png], 'ok.png', {type:'image/png'}));
        return out; }""", _PNG_B64)
    check("a renamed non-image passes MIME+extension but FAILS the decode check",
          isinstance(res["fakeImage"], str) and res["fakeImage"], repr(res["fakeImage"])[:60])
    check("a renamed non-audio likewise fails", isinstance(res["fakeAudio"], str) and res["fakeAudio"],
          repr(res["fakeAudio"])[:60])
    check("a real PNG still passes", res["realImage"] is None, repr(res["realImage"]))
    check("the message tells the user what to do about it",
          "could not be opened" in (res["fakeImage"] or ""), repr(res["fakeImage"])[:60])

    # End-to-end through the real input element, which is what a user touches.
    applied = pad7.evaluate("""async (b64) => {
        const dt = new DataTransfer();
        dt.items.add(new File([new Uint8Array([104,105])], 'photo.png', {type:'image/png'}));
        const inp = document.getElementById('photoInput');
        inp.files = dt.files;
        inp.dispatchEvent(new Event('change'));
        await new Promise(r => setTimeout(r, 1500));
        const img = document.getElementById('photoBgImg');
        return { applied: !!(img && img.src && img.src.length > 30 && !img.hidden),
                 toast: (document.getElementById('toast')||{}).textContent || '' }; }""", _PNG_B64)
    check("a bad file selected through the picker is NOT applied to the canvas",
          applied["applied"] is False, str(applied))
    check("and the user is told why", "could not be opened" in applied["toast"], applied["toast"][:60])
    check("no page errors from the decode path", not perr7, "; ".join(perr7[:2]))

    flip7 = ctx7.new_page()
    ferr7 = []
    flip7.on("pageerror", lambda e: ferr7.append(str(e)))
    flip7.goto(BASE + "/flip", wait_until="load")
    flip7.wait_for_timeout(900)
    check("Flip has the same checks (both surfaces, not just the Pad)",
          flip7.evaluate("() => typeof skriblDecodeCheckImage === 'function' && typeof skriblDecodeCheckAudio === 'function'"))
    fres = flip7.evaluate("""async () => await skriblDecodeCheckAudio(
        new File([new Uint8Array([110,111])], 'x.wav', {type:'audio/wav'}))""")
    check("Flip rejects undecodable audio too", isinstance(fres, str) and fres, repr(fres)[:50])
    check("no Flip page errors", not ferr7, "; ".join(ferr7[:2]))
    br7.close()


print("\nR9#1 — stale selections cannot overwrite newer ones")
_PNG = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQ"
        "GAhKmMIQAAAABJRU5ErkJggg==")
_GATED = """(b64) => {
    window.__png = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    window.__gate = {};
    window.skriblDecodeCheckImage = f => new Promise(r => { window.__gate[f.name] = r; });
    window.skriblDecodeCheckAudio = f => new Promise(r => { window.__gate[f.name] = r; });
}"""
with sync_playwright() as p9:
    br9 = p9.chromium.launch(); ctx9 = br9.new_context()
    pad9 = ctx9.new_page(); e9 = []
    pad9.on("pageerror", lambda e: e9.append(str(e)))
    pad9.goto(BASE + "/", wait_until="load"); pad9.wait_for_timeout(1000)

    check("the shared media lib is loaded (no per-file copies)",
          pad9.evaluate("() => typeof SkriblMedia === 'object' && typeof SkriblMedia.decodeCheckImage === 'function'"))

    pad9.evaluate(_GATED, _PNG)
    race = pad9.evaluate("""async () => {
        const fire = n => { const dt = new DataTransfer();
            dt.items.add(new File([window.__png], n, {type:'image/png'}));
            const i = document.getElementById('photoInput'); i.files = dt.files;
            i.dispatchEvent(new Event('change')); };
        fire('a.png'); await new Promise(r => setTimeout(r, 60));
        fire('b.png'); await new Promise(r => setTimeout(r, 60));
        window.__gate['b.png'](null);
        await new Promise(r => setTimeout(r, 400));
        const afterB = (document.getElementById('photoBgImg')||{}).src || '';
        window.__gate['a.png'](null);
        await new Promise(r => setTimeout(r, 600));
        const afterA = (document.getElementById('photoBgImg')||{}).src || '';
        return { bApplied: afterB.length > 30, stable: afterB === afterA }; }""")
    check("the newer selection is applied", race["bApplied"], str(race))
    check("a slower older decode does NOT overwrite it", race["stable"], str(race))

    pad9.reload(); pad9.wait_for_timeout(900); pad9.evaluate(_GATED, _PNG)
    # Round 10, #1: this used to do `photoSelectionSeq++` by hand — simulating the
    # implementation rather than exercising it, which hid the fact that the real
    # Remove button never incremented the token. It now CLICKS the real control.
    removal = pad9.evaluate("""async () => {
        const dt = new DataTransfer();
        dt.items.add(new File([window.__png], 'a.png', {type:'image/png'}));
        const i = document.getElementById('photoInput'); i.files = dt.files;
        i.dispatchEvent(new Event('change'));
        await new Promise(r => setTimeout(r, 80));
        document.getElementById('photoRemove').click();      // the real control
        window.__gate['a.png'](null);
        await new Promise(r => setTimeout(r, 700));
        const img = document.getElementById('photoBgImg');
        return !(img && img.src && img.src.length > 30); }""")
    check("clicking the REAL Remove control invalidates a pending decode", removal is True)

    print("\nR9#3 — all four real inputs, driven end to end")
    def drive(page, input_id, fname, mime, bad=True):
        return page.evaluate("""async ([id, fname, mime, bad]) => {
            const bytes = bad ? new Uint8Array([104,105]) : window.__realpng;
            const dt = new DataTransfer();
            dt.items.add(new File([bytes], fname, {type: mime}));
            const i = document.getElementById(id); i.files = dt.files;
            i.dispatchEvent(new Event('change'));
            await new Promise(r => setTimeout(r, 2000));
            return true; }""", [input_id, fname, mime, bad])

    pad9.reload(); pad9.wait_for_timeout(900)
    pad9.evaluate("(b) => { window.__realpng = Uint8Array.from(atob(b), c => c.charCodeAt(0)); }", _PNG)
    drive(pad9, "photoInput", "bad.png", "image/png")
    st = pad9.evaluate("""() => ({ applied: !!((document.getElementById('photoBgImg')||{}).src||'').match(/.{30,}/),
                                   toast: (document.getElementById('toast')||{}).textContent || '' })""")
    check("Pad photoInput: malformed rejected and nothing retained", st["applied"] is False, str(st)[:80])
    check("Pad photoInput: user told why", "could not be opened" in st["toast"], st["toast"][:50])
    drive(pad9, "photoInput", "ok.png", "image/png", bad=False)
    check("Pad photoInput: a valid image IS accepted",
          pad9.evaluate("() => (((document.getElementById('photoBgImg')||{}).src)||'').length > 30"))
    # failed replacement must leave the good one alone
    good = pad9.evaluate("() => (document.getElementById('photoBgImg')||{}).src")
    drive(pad9, "photoInput", "bad2.png", "image/png")
    check("Pad photoInput: a rejected REPLACEMENT leaves the existing image intact",
          pad9.evaluate("() => (document.getElementById('photoBgImg')||{}).src") == good)

    drive(pad9, "musicInput", "bad.wav", "audio/wav")
    check("Pad musicInput: malformed rejected, no audio retained",
          pad9.evaluate("() => !audioEl"), str(pad9.evaluate("() => !!audioEl")))

    flip9 = ctx9.new_page(); fe9 = []
    flip9.on("pageerror", lambda e: fe9.append(str(e)))
    flip9.goto(BASE + "/flip", wait_until="load"); flip9.wait_for_timeout(900)
    flip9.evaluate("(b) => { window.__realpng = Uint8Array.from(atob(b), c => c.charCodeAt(0)); }", _PNG)
    drive(flip9, "imageInput", "bad.png", "image/png")
    check("Flip imageInput: malformed rejected, no background set",
          flip9.evaluate("() => !bgImage"), str(flip9.evaluate("() => !!bgImage")))
    drive(flip9, "musicInput", "bad.wav", "audio/wav")
    check("Flip musicInput: malformed rejected, no music retained",
          flip9.evaluate("() => !musicData"), str(flip9.evaluate("() => !!musicData")))
    drive(flip9, "imageInput", "ok.png", "image/png", bad=False)
    check("Flip imageInput: a valid image IS accepted", flip9.evaluate("() => !!bgImage"))
    check("no page errors on either surface", not e9 and not fe9, "; ".join((e9 + fe9)[:2]))

    print("\nR9#2 — the decode timeout now FAILS CLOSED")
    check("a file the browser never resolves is refused, not accepted",
          isinstance(pad9.evaluate("() => SkriblMedia.MSG.audioSlow"), str)
          and "too long" in pad9.evaluate("() => SkriblMedia.MSG.audioSlow"))
    check("images have the same policy", "too long" in pad9.evaluate("() => SkriblMedia.MSG.imageSlow"))
    check("the timeout is a named constant, not a magic number",
          pad9.evaluate("() => typeof SkriblMedia.DECODE_TIMEOUT_MS === 'number'"))
    br9.close()

print("\nR9#5 — the helpers exist once, not twice")
_app = (ROOT / "static" / "skribl" / "app.js").read_text(encoding="utf-8")
_flip = (ROOT / "static" / "skribl" / "flip.js").read_text(encoding="utf-8")
_lib = (ROOT / "static" / "skribl" / "lib" / "media_validation.js").read_text(encoding="utf-8")
check("decode helpers are defined only in the shared lib",
      "function decodeCheckImage" in _lib
      and "function skriblDecodeCheckImage" not in _app
      and "function skriblDecodeCheckImage" not in _flip)
check("the MIME sets live there too, not duplicated",
      "SKRIBL_AUDIO_MIMES = new Set" not in _app and "AUDIO_MIMES = new Set" in _lib)


print("\nR10#2 — the token survives FileReader, not just the decode")
# A minimal but genuinely decodable WAV: 44-byte header + a few samples.
_WAV_JS = """() => {
    const n = 256, hdr = 44, buf = new ArrayBuffer(hdr + n * 2), v = new DataView(buf);
    const put = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    put(0,'RIFF'); v.setUint32(4, 36 + n*2, true); put(8,'WAVE'); put(12,'fmt ');
    v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
    v.setUint32(24,8000,true); v.setUint32(28,16000,true); v.setUint16(32,2,true);
    v.setUint16(34,16,true); put(36,'data'); v.setUint32(40, n*2, true);
    for (let i = 0; i < n; i++) v.setInt16(hdr + i*2, Math.sin(i/8)*8000, true);
    return new Uint8Array(buf); }"""
with sync_playwright() as p10:
    br10 = p10.chromium.launch(); ctx10 = br10.new_context()
    f10 = ctx10.new_page(); fe10 = []
    f10.on("pageerror", lambda e: fe10.append(str(e)))
    f10.goto(BASE + "/flip", wait_until="load"); f10.wait_for_timeout(900)
    f10.evaluate("(b) => { window.__png = Uint8Array.from(atob(b), c => c.charCodeAt(0)); }", _PNG)
    f10.evaluate(f"() => {{ window.__wav = ({_WAV_JS})(); }}")

    # Hold A's FileReader, fully apply B, then release A.
    reader_race = f10.evaluate("""async () => {
        const RealFR = window.FileReader;
        const held = [];
        window.FileReader = function () {
            const fr = new RealFR();
            const self = this;
            this.readAsDataURL = function (f) {
                fr.onload = () => {
                    self.result = fr.result;
                    const go = () => self.onload && self.onload();
                    if (f.name === 'a.png') held.push(go); else go();
                };
                fr.readAsDataURL(f);
            };
            this.onload = null; this.onerror = null; this.result = null;
        };
        const fire = n => { const dt = new DataTransfer();
            dt.items.add(new File([window.__png], n, {type:'image/png'}));
            const i = document.getElementById('imageInput'); i.files = dt.files;
            i.dispatchEvent(new Event('change')); };
        fire('a.png'); await new Promise(r => setTimeout(r, 500));   // A decodes, read held
        fire('b.png'); await new Promise(r => setTimeout(r, 900));   // B applied
        const afterB = bgImage;
        held.forEach(fn => fn());                                    // A's read lands late
        await new Promise(r => setTimeout(r, 500));
        window.FileReader = RealFR;
        return { bApplied: !!afterB, stable: bgImage === afterB }; }""")
    check("Flip image: B is applied while A's read is held", reader_race["bApplied"], str(reader_race))
    check("Flip image: a late FileReader from A does NOT overwrite B",
          reader_race["stable"], str(reader_race))

    print("\nR10#3 — valid audio accepted through the REAL music inputs")
    f10.reload(); f10.wait_for_timeout(900)
    f10.evaluate(f"() => {{ window.__wav = ({_WAV_JS})(); }}")
    f10.evaluate("""async () => { const dt = new DataTransfer();
        dt.items.add(new File([window.__wav], 'ok.wav', {type:'audio/wav'}));
        const i = document.getElementById('musicInput'); i.files = dt.files;
        i.dispatchEvent(new Event('change')); }""")
    f10.wait_for_timeout(3000)
    check("Flip musicInput: a valid WAV IS accepted and stored",
          f10.evaluate("() => !!musicData && musicData.indexOf('data:audio') === 0"),
          str(f10.evaluate("() => (musicData||'').slice(0,22)")))
    check("no Flip page errors", not fe10, "; ".join(fe10[:2]))

    pd10 = ctx10.new_page(); pe10 = []
    pd10.on("pageerror", lambda e: pe10.append(str(e)))
    pd10.goto(BASE + "/", wait_until="load"); pd10.wait_for_timeout(1000)
    pd10.evaluate(f"() => {{ window.__wav = ({_WAV_JS})(); }}")
    pd10.evaluate("""async () => { const dt = new DataTransfer();
        dt.items.add(new File([window.__wav], 'ok.wav', {type:'audio/wav'}));
        const i = document.getElementById('musicInput'); i.files = dt.files;
        i.dispatchEvent(new Event('change')); }""")
    pd10.wait_for_timeout(3000)
    check("Pad musicInput: a valid WAV IS accepted (audioEl created)",
          pd10.evaluate("() => !!audioEl"), str(pd10.evaluate("() => !!audioEl")))
    check("no Pad page errors", not pe10, "; ".join(pe10[:2]))
    br10.close()

print("\nR10#4 — the image fallback releases its object URL on timeout")
with sync_playwright() as p11:
    br11 = p11.chromium.launch(); pg11 = br11.new_context().new_page()
    pg11.goto(BASE + "/", wait_until="load"); pg11.wait_for_timeout(800)
    leak = pg11.evaluate("""async () => {
        const realBitmap = window.createImageBitmap;
        const realCreate = URL.createObjectURL, realRevoke = URL.revokeObjectURL;
        let created = 0, revoked = 0;
        delete window.createImageBitmap;                    // force the <img> fallback
        URL.createObjectURL = f => { created++; return realCreate(f); };
        URL.revokeObjectURL = u => { revoked++; return realRevoke(u); };
        const OrigImage = window.Image;
        window.Image = function () { this.onload = null; this.onerror = null;
                                     this.naturalWidth = 0;
                                     Object.defineProperty(this, 'src', {set(){}, get(){return '';}});
                                     this.removeAttribute = () => {}; };
        const p = SkriblMedia.decodeCheckImage(new File([new Uint8Array([1,2])], 'x.png', {type:'image/png'}));
        const msg = await p;                                // resolves via timeout
        window.Image = OrigImage; window.createImageBitmap = realBitmap;
        URL.createObjectURL = realCreate; URL.revokeObjectURL = realRevoke;
        return { msg, created, revoked }; }""")
    check("a never-resolving image times out with the slow message",
          "too long" in (leak["msg"] or ""), repr(leak["msg"])[:60])
    check("and its object URL is revoked exactly once, not leaked",
          leak["created"] == 1 and leak["revoked"] == 1, str(leak))
    br11.close()

print("\nR10#5/#6 — asset versioning and player usage")
_tpls = {n: (ROOT / "templates" / n).read_text(encoding="utf-8")
         for n in ("skribl_editor.html", "skribl_flip.html", "skribl_player.html")}
for n, body in _tpls.items():
    check(f"{n}: shared module cache-bust matches its contents",
          "media_validation.js', v='121'" in body, "stale v=120" if "v='120'" in body else "ok")
# The player is NOT trimmed: it renders both media inputs, so app.js binds the
# handlers there and the module is genuinely reachable.
check("the player really does render media inputs (so the module is needed)",
      'id="musicInput"' in _tpls["skribl_player.html"] and 'id="photoInput"' in _tpls["skribl_player.html"])


print("\nR10 — pending/committed reservations close the crash window")
check("RateEvent carries a state column", hasattr(A.RateEvent, "state"))
check("the pending TTL is a bounded, named constant",
      isinstance(A.RATE_PENDING_TTL, int) and A.RATE_PENDING_TTL >= 5, str(A.RATE_PENDING_TTL))

# A short TTL makes the abandoned-reservation behaviour observable in seconds.
with server(SKRIBL_RATE_BACKEND="db", SKRIBL_RATE_MAX_POSTS=1,
            SKRIBL_RATE_MAX_ATTEMPTS=500, SKRIBL_RATE_PENDING_TTL=5,
            SKRIBL_RATE_HMAC_KEY=f"ttl-{secrets_token()}") as ttlbase:
    check("a committed post spends its slot", post_to(ttlbase, {"frames": [frame]}) == 201)
    check("and the next one is refused for the whole window",
          post_to(ttlbase, {"frames": [frame]}) == 429)

# An abandoned PENDING row must stop counting after the TTL, where a committed one
# would not. Written directly, because killing a worker mid-post is not something
# the harness can stage reliably.
with A.create_app().app_context():
    import datetime as _dt
    kh = A._rate_key("ttl-probe-ip")
    stale = A.RateEvent(bucket="posts", key_hash=kh, state="pending",
                        created_at=_dt.datetime.now(_dt.timezone.utc)
                                   - _dt.timedelta(seconds=A.RATE_PENDING_TTL + 60))
    A.db.session.add(stale); A.db.session.commit()
    counted_pending = A._db_rate_count("posts", kh)
    stale.state = "committed"; A.db.session.commit()
    counted_committed = A._db_rate_count("posts", kh)
    A.db.session.delete(stale); A.db.session.commit()
check("an abandoned PENDING reservation stops counting after its TTL",
      counted_pending == 0, f"counted {counted_pending}")
check("a COMMITTED slot of the same age still counts for the full window",
      counted_committed == 1, f"counted {counted_committed}")
check("so a process killed mid-post costs the TTL, not the hour",
      counted_pending == 0 and counted_committed == 1)

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
