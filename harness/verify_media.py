"""v105 — server-side media validation on POST /api/skribls (INTEGRATION §7).

The post endpoint is public and unauthenticated, and all media arrives as base64
data URLs inside payload_json. The only previous limit was MAX_CONTENT_LENGTH on
the whole request, so one post could carry ~24 MB of arbitrary blob — any type,
valid base64 or not — into the JSON column. At the current rate limit that is
roughly 480 MB/hour/IP into a free-tier Postgres.

Two failure modes this suite guards in both directions:
  REJECT  — wrong top-level type, SVG, malformed base64, oversize, non-data-URL.
  ACCEPT  — everything the real client actually posts. A validator that breaks
            legitimate posts is worse than none, so the accept cases matter more
            than the reject cases. verify_audio.py / verify_loopcap.py post real
            browser-generated payloads and are the broader regression check.

No browser needed — this drives the API directly, so it is the fastest suite.
"""
import base64
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5001"

results = []
def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(payload):
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200].decode("utf-8", "replace")}


# v111: the validator now checks magic numbers, so synthetic all-zero bytes are
# (correctly) rejected. Fixtures carry a real signature for their declared type.
_SIGS = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
    "image/gif": b"GIF89a",
    "image/webp": b"RIFF\x00\x00\x00\x00WEBP",   # v111: fourcc at offset 8 now required
    "image/bmp": b"BM",
    # v114: audio is container-checked now, so fixtures need real headers.
    "audio/wav": b"RIFF\x00\x00\x00\x00WAVE",
    "audio/mpeg": b"ID3\x04\x00",
}


def durl(mime, nbytes=64):
    head = _SIGS.get(mime, b"")
    body = head + b"\x00" * max(1, nbytes - len(head))
    return f"data:{mime};base64," + base64.b64encode(body).decode()


def frame(**kw):
    f = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}
    f.update(kw)
    return f


print("\nACCEPT — everything the real client posts must still go through")
cases_ok = [
    ("a plain drawing with no media", {"frames": [frame()]}),
    ("a WAV loop on frame 0 (the v102+ shape)",
     {"frames": [frame(music={"data": durl("audio/wav", 2048), "trimStart": 0, "trimEnd": 8})]}),
    ("an mp3 upload (subtypes are deliberately open)",
     {"frames": [frame(music={"data": durl("audio/mpeg", 4096)})]}),
    ("a background photo",
     {"frames": [frame(photo={"data": durl("image/jpeg", 4096), "fit": "cover"})]}),
    ("a webp photo (what the client re-encodes to)",
     {"frames": [frame(photo={"data": durl("image/webp", 2048)})]}),
    ("a share-card thumbnail", {"frames": [frame()], "thumbnail": durl("image/png", 8192)}),
    ("a settings-only music dict with no data", {"frames": [frame(music={"enabled": True})]}),
    ("legacy top-level media (pre-frame-format posts)",
     {"music": {"data": durl("audio/wav", 1024)}, "photo": {"data": durl("image/png", 1024)}}),
    ("explicit nulls", {"frames": [frame(music=None, photo=None)], "thumbnail": None}),
    ("audio just under the 12 MB cap",
     {"frames": [frame(music={"data": durl("audio/wav", 11_500_000)})]}),
]
for name, payload in cases_ok:
    payload.setdefault("title", "harness")
    status, body = post(payload)
    check(f"accepts {name}", status == 201 and "id" in body,
          f"{status} {str(body)[:90]}")

print("\nREJECT — with a readable message the composer can surface")
cases_bad = [
    ("SVG as a photo (the one image type that carries script)",
     {"frames": [frame(photo={"data": "data:image/svg+xml;base64," +
                                      base64.b64encode(b"<svg/>").decode()})]}, "SVG"),
    ("text/html smuggled into music.data",
     {"frames": [frame(music={"data": "data:text/html;base64,PGI+"})]}, "audio/*"),
    ("an image in the audio slot",
     {"frames": [frame(music={"data": durl("image/png")})]}, "audio/*"),
    ("a javascript: URL", {"frames": [frame(photo={"data": "javascript:alert(1)"})]}, "data URL"),
    ("a bare http URL", {"frames": [frame(photo={"data": "http://evil.example/x.png"})]}, "data URL"),
    ("malformed base64",
     {"frames": [frame(photo={"data": "data:image/png;base64,!!!not-base64!!!"})]}, "base64"),
    ("oversize audio (over the 12 MB cap)",
     {"frames": [frame(music={"data": durl("audio/wav", 13_000_000)})]}, "too large"),
    ("oversize thumbnail (over the 2 MB card cap)",
     {"frames": [frame()], "thumbnail": durl("image/png", 2_500_000)}, "too large"),
    ("a non-string data value", {"frames": [frame(photo={"data": 12345})]}, "data URL"),
]
for name, payload, expect in cases_bad:
    payload.setdefault("title", "harness")
    status, body = post(payload)
    err = str(body.get("error", ""))
    check(f"rejects {name}", status == 400 and expect.lower() in err.lower(),
          f"{status} {err[:80]}")

print("\nCOVERAGE — the walker reaches media wherever it lives")
status, body = post({"title": "harness",
                     "frames": [frame(), frame(), frame(photo={"data": durl("image/svg+xml")})]})
check("media on a later frame is still checked, not just frame 0",
      status == 400 and "SVG" in str(body.get("error", "")), f"{status} {str(body)[:80]}")
status, body = post({"title": "harness", "frames": [frame()],
                     "thumbnail": "data:image/svg+xml;base64,PHN2Zy8+"})
check("the thumbnail slot is checked too",
      status == 400 and "SVG" in str(body.get("error", "")), f"{status} {str(body)[:80]}")
status, body = post({"title": "harness", "music": {"data": durl("text/plain")}})
check("legacy top-level media is checked",
      status == 400, f"{status} {str(body.get('error',''))[:60]}")

print("\nCONTRACT — the error shape the composer already reads")
status, body = post({"frames": [frame(photo={"data": "data:image/svg+xml;base64,PHN2Zy8+"})]})
check("rejection is a 4xx with a JSON {error} string",
      status == 400 and isinstance(body.get("error"), str) and body["error"],
      f"{status} {str(body)[:70]}")
check("the message names the offending field",
      "photo" in str(body.get("error", "")).lower(), str(body.get("error", ""))[:70])

ok = sum(1 for o, _ in results if o)
print("\n" + "=" * 60)
print(f"{ok}/{len(results)} passed")
for o, n in results:
    if not o:
        print(f"  FAILED: {n}")
raise SystemExit(0 if ok == len(results) else 1)
