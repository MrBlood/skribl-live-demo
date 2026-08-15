"""API edge pins: refusals that exist, and one pair of numbers that must move together.

Two kinds of assertion live here, and they fail for opposite reasons:

  1. REFUSALS. Empty frames lists, out-of-band fps, NaN coordinates, zero-point
     stroke groups, hold 0, unknown visibility. Each is pinned at the endpoint —
     not the validator function — because the endpoint is what an attacker or a
     buggy client actually reaches. If one of these starts returning 201, a
     server-side check was lost.

  2. THE CAPTION PAIR. The UI caps captions at 280; the server truncates at 300.
     Captions of length 281-300 are accepted BY DESIGN (documented in
     skribl_flip.html): the gap is deliberate slack so the two numbers can be
     changed independently without a deploy-order dance. This suite pins the gap
     so nobody "fixes" one number to match the other without seeing this fail.

fps rationale, mirrored from skribl/validation.py: the player reads
payload.fps || 12, so a hostile fps does not crash anything — a negative or
zero fps silently freezes the post on page one forever. Flip's editor only
produces 6/12/24; the server accepts 1..60, bools and strings excluded.
"""
import base64
import json
import math
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5001"

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(payload, headers=None):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(), headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def get(path):
    try:
        with urllib.request.urlopen(BASE + path) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


frame = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}


print("\nFRAMES — the empty list no editor produces")
st, body = post({"frames": []})
check("frames=[] is refused", st == 400 and "frame" in str(body.get("error", "")),
      f"{st} {str(body)[:70]}")
st, _ = post({"frames": [frame]})
check("one frame still accepted", st == 201, f"{st}")
st, _ = post({})
check("absent frames key still accepted (a classic Pad payload)", st == 201, f"{st}")

print("\nFPS — the band is 1..60, numbers only")
for good in (1, 60, 12, 24.0):
    st, body = post({"frames": [frame], "fps": good})
    check(f"fps={good!r} accepted", st == 201, f"{st} {str(body)[:60]}")
for bad in (0.5, 61, -3, float("nan"), True, "12"):
    st, body = post({"frames": [frame], "fps": bad})
    check(f"fps={bad!r} refused", st == 400 and "fps" in str(body.get("error", "")),
          f"{st} {str(body)[:70]}")
st, _ = post({"frames": [frame], "fps": None})
check("fps=null accepted (player falls back to 12)", st == 201, f"{st}")

print("\nEXISTING REFUSALS — pinned so they stay refusals")
# The stroke schema is FLAT: "strokes" is a list of point objects and
# "strokeGroups" carries per-stroke point counts. A nested {"points": [...]}
# shape is refused too, but for the wrong reason — these pins must hit the
# finiteness and strictly-positive-group checks specifically.
st, body = post({"strokes": [{"x": float("nan"), "y": 5}]})
check("NaN coordinate refused", st == 400 and "finite" in str(body.get("error", "")),
      f"{st} {str(body)[:70]}")
st, body = post({"strokes": [{"x": 1, "y": 2}], "strokeGroups": [0, 1]})
check("zero-point stroke group refused", st == 400
      and "strokeGroups" in str(body.get("error", "")), f"{st} {str(body)[:70]}")
st, body = post({"frames": [dict(frame, hold=0)]})
check("hold=0 refused", st == 400 and "hold" in str(body.get("error", "")),
      f"{st} {str(body)[:70]}")
st, body = post({"frames": [frame], "visibility": "everyone"})
check("unknown visibility refused", st == 400, f"{st} {str(body)[:70]}")

print("\nBASESNAPSHOT — the media slot nothing used to walk")
# Pad serialises the pre-recording canvas into payload.baseSnapshot, and the
# frame format reserves the slot per frame. It was the ONE media slot outside
# _iter_media_items: neither validated, capped, nor externalised. These pin
# that it now goes through the same image rules as everything else.
st, body = post({"frames": [frame],
                 "baseSnapshot": "data:image/png;base64,AAAAAAAAAAAA"})
check("a root baseSnapshot with a bogus image signature is refused",
      st == 400 and "baseSnapshot" in str(body.get("error", "")),
      f"{st} {str(body)[:80]}")
st, body = post({"frames": [dict(frame,
                 baseSnapshot="data:image/png;base64,AAAAAAAAAAAA")]})
check("so is a per-frame one, with its frame named",
      st == 400 and "frames[0].baseSnapshot" in str(body.get("error", "")),
      f"{st} {str(body)[:80]}")
st, _ = post({"frames": [dict(frame, baseSnapshot=None)]})
check("Flip's explicit baseSnapshot:null still accepted", st == 201, f"{st}")

print("\nCAPTION — 280 and 300 are different numbers ON PURPOSE")
# skribl_flip.html documents the pair: the UI caps input at 280, the server
# truncates at 300. 281-300 therefore passes the server untouched. If either
# assertion here fails, someone changed one number without the other.
cap290 = "c" * 290
st, body = post({"frames": [frame], "caption": cap290})
check("caption of 290 (past the UI cap) accepted by the server", st == 201, f"{st}")
if st == 201:
    st2, fetched = get(f"/api/skribls/{body['id']}")
    check("and stored untruncated", st2 == 200 and fetched.get("caption") == cap290,
          f"stored len {len(fetched.get('caption') or '')}")
else:
    check("and stored untruncated", False, "post failed, nothing to fetch")
cap350 = "d" * 350
st, body = post({"frames": [frame], "caption": cap350})
check("caption of 350 accepted (server truncates, does not refuse)", st == 201, f"{st}")
if st == 201:
    st2, fetched = get(f"/api/skribls/{body['id']}")
    check("truncated to exactly 300", st2 == 200
          and (fetched.get("caption") or "") == "d" * 300,
          f"stored len {len(fetched.get('caption') or '')}")
else:
    check("truncated to exactly 300", False, "post failed, nothing to fetch")

print("\nTIMEZONE — createdAt leaves the API labelled as the UTC it is")
st, body = post({"frames": [frame]})
check("probe post created", st == 201, f"{st}")
stc, got = get(f"/api/skribls/{body['id']}")
created = (got or {}).get("createdAt") or ""
check("createdAt carries an explicit UTC offset",
      created.endswith("+00:00") or created.endswith("Z"),
      f"{created!r} — a naive ISO string is parsed as LOCAL time by Date()")

print("\nIDEMPOTENCY — a retried POST resolves to the same post")
import uuid
K = {"Idempotency-Key": str(uuid.uuid4())}
st1, b1 = post({"frames": [frame], "title": "idem"}, headers=K)
check("first POST with a key creates (201)", st1 == 201, f"{st1}")
st2, b2 = post({"frames": [frame], "title": "idem"}, headers=K)
check("the retry replays (200) rather than creating",
      st2 == 200 and b2.get("idempotentReplay") is True, f"{st2} {str(b2)[:70]}")
check("and names the SAME post", b1.get("id") == b2.get("id"),
      f"{b1.get('id')} vs {b2.get('id')}")
st3, b3 = post({"frames": [frame], "title": "idem"})
check("without the header, an identical body is a NEW post",
      st3 == 201 and b3.get("id") != b1.get("id"), f"{st3} {b3.get('id')}")
st4, b4 = post({"frames": [frame]}, headers={"Idempotency-Key": "x" * 300})
check("an oversized key is ignored, not stored", st4 == 201, f"{st4}")

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
