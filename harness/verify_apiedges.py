"""API edge pins: refusals that exist, and one pair of numbers that must move together.

Two kinds of assertion live here, and they fail for opposite reasons:

  1. REFUSALS. Empty frames lists, out-of-band fps, NaN coordinates, zero-point
     stroke groups, hold 0, unknown visibility. Each is pinned at the endpoint —
     not the validator function — because the endpoint is what an attacker or a
     buggy client actually reaches. If one of these starts returning 201, a
     server-side check was lost.

  2. THE CAPTION LIMIT. One number since v224 — the UI's 280 and the server's
     silent truncation at 300 were the same defect from two ends.
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
import os
import sys
import urllib.error
import urllib.request
from assertions import make_check

# On the path so the caption limit can be READ from core.py rather than typed
# here — a suite that hard-codes the number it is checking cannot notice the
# number moving, which is the exact failure this section used to encode.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:5001"

results = []


check = make_check(results, with_detail=True)


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

print("\nCAPTION — one limit now, and over it is an error")
# BEHAVIOUR CHANGE, v224, FLAGGED. This block used to be headed "280 and 300 are
# different numbers ON PURPOSE" and asserted that a 350-character caption was
# ACCEPTED and silently truncated to 300. The outside review called the split a
# defect and it is right: the UI's 280 meant a caption between 281 and 300 could
# not be typed but could be posted, and the server's truncation meant anything
# longer came back 201 with text quietly missing. Nothing told the caller.
#
# There is one number now (core.MAX_CAPTION_CHARS, which is also the column
# width and the rendered maxlength), and over it is a 400. The old assertions
# are gone rather than adjusted, because what they pinned was the drift itself.
# verify_hostconfig.py holds the replacement contract in full.
from skribl.core import MAX_CAPTION_CHARS as _CAP   # noqa: E402

cap290 = "c" * 290
st, body = post({"frames": [frame], "caption": cap290})
check("a 290-character caption is accepted — inside the single limit",
      st == 201, f"{st}")
if st == 201:
    st2, fetched = get(f"/api/skribls/{body['id']}")
    check("and stored untruncated", st2 == 200 and fetched.get("caption") == cap290,
          f"stored len {len(fetched.get('caption') or '')}")
else:
    check("and stored untruncated", False, "post failed, nothing to fetch")

st, body = post({"frames": [frame], "caption": "d" * _CAP})
check(f"exactly {_CAP} is accepted", st == 201, f"{st}")
st, body = post({"frames": [frame], "caption": "d" * 350})
check("a 350-character caption is REFUSED, not quietly shortened",
      st == 400, f"{st} {str(body)[:80]}")
check("…and the refusal names the field and the limit",
      "caption" in str(body) and str(_CAP) in str(body), str(body)[:100])

print("\nTIMEZONE — createdAt leaves the API labelled as the UTC it is")
st, body = post({"frames": [frame]})
check("probe post created", st == 201, f"{st}")
stc, got = get(f"/api/skribls/{body['id']}")
created = (got or {}).get("createdAt") or ""
check("createdAt carries an explicit UTC offset",
      created.endswith("+00:00") or created.endswith("Z"),
      f"{created!r} — a naive ISO string is parsed as LOCAL time by Date()")

print("\nIDEMPOTENCY — anonymous callers get NO shared replay namespace")
# v200 follow-up review, F2: v200 scoped every anonymous client to one literal
# namespace, so two strangers sending the same key resolved to the SAME post —
# the second received the first's id and share URL (a disclosure for unlisted
# posts). This server is anonymous, so these two "different clients" are
# distinguishable only by their key reuse — which is exactly the attack shape:
# same key, different payloads, and the second MUST NOT see the first's post.
# The authenticated replay path (where a real author scope exists) is pinned
# in verify_mediaauthz.py.
import uuid
K = {"Idempotency-Key": str(uuid.uuid4())}
st1, b1 = post({"frames": [frame], "title": "client one"}, headers=K)
check("an anonymous POST with a key still creates (201)", st1 == 201, f"{st1}")
st2, b2 = post({"frames": [frame], "title": "client two"}, headers=K)
check("a second anonymous client reusing the key gets its OWN post",
      st2 == 201 and b2.get("id") != b1.get("id")
      and not b2.get("idempotentReplay"),
      f"{st2} {b2.get('id')} vs {b1.get('id')}")
st4, b4 = post({"frames": [frame]}, headers={"Idempotency-Key": "x" * 300})
check("an oversized key is ignored, not stored", st4 == 201, f"{st4}")

print("\nIDEMPOTENCY — a client capability scopes an anonymous replay (SK-AUD-001)")
# Acquisition audit of v302: the F2 rule above left an anonymous lost-response
# retry duplicating the post, and the lost response also carried the ONLY copy
# of the revocation key. Two client-minted secrets close both halves without
# reopening F2: X-Skribl-Client is the identity the namespace was missing (a
# random secret only that browser holds), and X-Skribl-Delete-Token is the key
# the client holds BEFORE the answer, so the answer can be lost. Both sides of
# every boundary: the same client replays, a different client does not, a
# malformed client id gets no namespace, a well-formed token is honoured, a
# malformed one is ignored and the server mints.
import secrets as _secrets
C1 = {"X-Skribl-Client": _secrets.token_urlsafe(32)}
C2 = {"X-Skribl-Client": _secrets.token_urlsafe(32)}
K2 = {"Idempotency-Key": str(uuid.uuid4())}
T1 = _secrets.token_urlsafe(32)
body_a = {"frames": [frame], "title": "client capability"}
st1, b1 = post(body_a, headers={**K2, **C1, "X-Skribl-Delete-Token": T1})
check("an anonymous POST with a client id and a key creates (201)", st1 == 201, f"{st1} {b1}")
check("...and the deleteToken it returns is the one the client minted",
      b1.get("deleteToken") == T1, f"{str(b1.get('deleteToken'))[:12]}… vs {T1[:12]}…")
st2, b2 = post(body_a, headers={**K2, **C1})
check("the SAME client retrying the SAME body replays to the SAME post (200)",
      st2 == 200 and b2.get("idempotentReplay") is True and b2.get("id") == b1.get("id"),
      f"{st2} {b2.get('id')} vs {b1.get('id')} replay={b2.get('idempotentReplay')}")
st3, b3 = post(body_a, headers={**K2, **C2})
check("a DIFFERENT client reusing the key gets its OWN post (F2 holds)",
      st3 == 201 and b3.get("id") != b1.get("id") and not b3.get("idempotentReplay"),
      f"{st3} {b3.get('id')} vs {b1.get('id')}")
st5, b5 = post(body_a, headers={**K2, "X-Skribl-Client": "short"})
check("a malformed client id gets no namespace: a fresh post, no replay",
      st5 == 201 and b5.get("id") not in (b1.get("id"), b3.get("id")), f"{st5} {b5.get('id')}")
st6, b6 = post({"frames": [frame]}, headers={"X-Skribl-Delete-Token": "too-short"})
check("a malformed client token is ignored and the server mints its own",
      st6 == 201 and b6.get("deleteToken") and b6.get("deleteToken") != "too-short"
      and len(b6.get("deleteToken", "")) >= 32, f"{st6} {str(b6.get('deleteToken'))[:16]}")
# The client-minted key is a real key: it takes the post down.
_dreq = urllib.request.Request(f"{BASE}/api/skribls/{b1.get('id')}", method="DELETE",
                               data=json.dumps({"deleteToken": T1}).encode(),
                               headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(_dreq) as _dr:
        _dst = _dr.status
except urllib.error.HTTPError as _e:
    _dst = _e.code
check("...and the client-minted key deletes the post it was created under",
      _dst in (200, 204), f"DELETE -> {_dst}")
_gst, _ = get(f"/api/skribls/{b1.get('id')}")
check("...which is then gone", _gst == 404, f"GET -> {_gst}")

# --- what the schema does NOT know ------------------------------------------
# The media caps bound four slots and the complexity check bounds points,
# frames, groups, hold and canvasSize. EVERY OTHER KEY used to ride into
# payload_json verbatim, bounded only by MAX_CONTENT_LENGTH. Gzip makes that an
# amplifier: 23 KB on the wire inflated to a 24 MB row, at 20 posts/hour/IP,
# anonymously. The figure the media caps are justified by -- ~480 MB/hour/IP
# into a free-tier Postgres -- was still exactly achievable by using a key the
# schema had never heard of.
#
# THE CAP IS ON THE REMAINDER, NOT ON THE PAYLOAD, and the assertions below are
# in pairs for that reason. MAX_TOTAL_POINTS is 200,000 and a point serialises
# to ~87 bytes, so a VALID drawing reaches ~14.5 MB: any whole-payload cap that
# admits real work is far too loose to stop this. Each rejection below is
# therefore paired with an acceptance that would fail under a naive size limit.
_JUNK = "A" * 2_000_000
st5, b5 = post({"strokes": [], "junk": _JUNK})
check("an unknown key cannot carry an unbounded blob",
      st5 == 400 and "extra content" in str(b5.get("error", "")),
      f"{st5} {b5.get('error')} — 2 MB under a key the schema does not know")

# `background` is type-checked as a dict and then walked by nothing, which is
# the same defect baseSnapshot had before it was added to the media walk.
st6, b6 = post({"strokes": [], "background": {"data": _JUNK}})
check("...and neither can a known key that nothing walks", st6 == 400,
      f"{st6} {b6.get('error')} — background.data is validated by no one")

# Splitting the payload across many keys must not get under the limit.
st7, b7 = post({"strokes": [], **{f"k{i}": "y" * 30_000 for i in range(20)}})
check("...nor can many medium keys add up to the same thing", st7 == 400,
      f"{st7} {b7.get('error')}")

# THE PAIRED ACCEPTANCES. Without these the three above are satisfied by any
# cap at all, including one that breaks the product.
_pt = lambda i: {"x": i % 800 * 1.0, "y": i % 600 * 1.0, "size": 6,
                 "color": "#ffffff", "erase": False, "t": i}
st8, b8 = post({"strokes": [_pt(i) for i in range(20000)],
                "strokeGroups": [20000], "fps": 12,
                "canvasSize": {"cssWidth": 800, "cssHeight": 600},
                "title": "a real drawing"})
check("a 20,000-point drawing still posts", st8 == 201,
      f"{st8} {b8.get('error')} — ~1.7 MB of legitimate stroke data, which a "
      f"naive payload-size cap would reject")

st9, b9 = post({"frames": [{"strokes": [_pt(i) for i in range(500)],
                            "strokeGroups": [500], "hold": 1}
                           for _ in range(100)], "fps": 24})
check("...and so does a 100-page flipbook", st9 == 201,
      f"{st9} {b9.get('error')}")

# Forward compatibility is the reason unknown keys are preserved at all, so a
# client version bump must still ride along.
st10, b10 = post({"strokes": [], "someFutureField": {"a": 1, "b": [1, 2, 3]}})
check("a small unknown key still rides along, as it is meant to", st10 == 201,
      f"{st10} {b10.get('error')} — rejecting unknown keys outright would make "
      f"every client change need a server release")

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
