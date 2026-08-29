"""/media/<key> honours the SAME visibility predicate as everything else,
and nothing authorisation-dependent is publicly cacheable by default.

TWO P0s FROM THE OUTSIDE REVIEW, pinned here:

  1. POLICY PARITY. Payload, card and player ask SkriblPost.visible_to(),
     which consults the host's set_visibility_policy(). The media route
     hard-coded public/unlisted/owner in SQL instead, so a host policy was
     honoured on three surfaces and ignored on the fourth — in BOTH
     directions: a granted host state ('draft') 404'd its own media, and a
     revoked one ('moderated') kept serving its media after the post itself
     was refused. The revoked direction is the leak.

  2. CACHE DEFAULTS. Visibility is revocable; shared caches do not re-run
     visible_to(). So `Cache-Control: public` on an authorisation-dependent
     response outlives a revocation. Default is private, no-store everywhere
     an authorisation check gates the bytes; `public` appears only behind the
     deployment's explicit opt-in (public_media_cache=True /
     SKRIBL_PUBLIC_MEDIA_CACHE=1). The opted-in behaviour is pinned by
     verify_storage.py; THIS suite pins the default.

In-process apps with SKRIBL_MEDIA_BACKEND=local so payloads externalise and
/media/<key> is actually on the serving path.
"""
import base64
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import skribl
import skribl.models
from skribl.storage import LocalDiskStore

_tmp = tempfile.mkdtemp()
_url = f"sqlite:///{_tmp}/mediaauthz.db"
_media_root = tempfile.mkdtemp()


def build_app(viewer, public_media_cache=False):
    a = Flask(__name__)
    a.config["SQLALCHEMY_DATABASE_URI"] = _url
    a.config["SECRET_KEY"] = "harness-mediaauthz"
    d = SQLAlchemy()
    d.init_app(a)
    skribl.init_skribl(
        a, session=lambda: d.session,
        current_user_id=(lambda: viewer),
        # v224: a closure, not a cookie — see the note in verify_s3.py.
        csrf=False,
        media_store=LocalDiskStore(_media_root,
                                   lambda key: f"/media/{key}"),
        public_media_cache=public_media_cache)
    skribl.models.attach_to_metadata(d.metadata)

    # Host-owned per-request commit, per the transaction ownership contract —
    # without this the posts this suite creates never become durable.
    @a.after_request
    def _commit(resp):
        if resp.status_code < 500:
            d.session.commit()
        return resp

    @a.teardown_request
    def _rollback(exc):
        d.session.rollback()
    return a


import struct
import zlib


def png_b64(rgb):
    """A distinct, valid 1x1 PNG per colour. DISTINCT MATTERS: the store is
    content-addressed, so two scenarios sharing bytes share ONE key — and then
    every referencing post from every scenario weighs on that key's
    authorisation and cache decision, which is correct behaviour and a broken
    test."""
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00" + bytes(rgb)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return base64.b64encode(data).decode()
FRAME = {"strokes": [], "strokeGroups": [], "background": {"color": "#101418"}}


def post_as(author, body):
    a = build_app(author)
    r = a.test_client().post("/api/skribls", json=body)
    return r.status_code, (r.get_json() or {})


def media_url_of(pid, viewer):
    # The GET envelope drops the thumbnail (the card route serves it), so the
    # discoverable externalised URL is the photo's.
    a = build_app(viewer)
    r = a.test_client().get(f"/api/skribls/{pid}")
    if r.status_code != 200:
        return None
    payload = (r.get_json() or {}).get("skribl") or {}
    photo = payload.get("photo") or {}
    u = photo.get("data")
    return u if isinstance(u, str) and u.startswith("/media/") else None


import sqlalchemy as sa
_eng = sa.create_engine(_url)
skribl.models.create_all(_eng)
_eng.dispose()

skribl.set_visibility_policy(None)

print("\nBASELINE — built-in rules, no policy installed")
st, body = post_as(1, {"visibility": "private", "frames": [FRAME],
                       "photo": {"data": f"data:image/png;base64,{png_b64((10, 0, 0))}", "fit": "fit"}})
check("a private post with media is created", st == 201, str(st))
private_pid = body.get("id")
private_media = media_url_of(private_pid, 1)
check("its media externalised to /media/<key>", bool(private_media),
      str(private_media))
r = build_app(1).test_client().get(private_media)
check("the author can fetch the blob", r.status_code == 200, str(r.status_code))
r = build_app(None).test_client().get(private_media)
check("an anonymous viewer gets 404", r.status_code == 404, str(r.status_code))

print("\nPOLICY PARITY — the media route asks visible_to, not its own SQL")
st, body = post_as(7, {"visibility": "draft", "frames": [FRAME],
                       "photo": {"data": f"data:image/png;base64,{png_b64((20, 0, 0))}", "fit": "fit"}})
if st != 201:
    # The API enforces VISIBILITIES on POST; a host adds states by writing
    # rows itself. Do the same here.
    with build_app(7).app_context():
        import sqlalchemy as _sa
        from skribl.models import SkriblPost as _P
        # Reuse the private post's payload shape by posting unlisted then
        # flipping the state to the host-defined one.
        st2, b2 = post_as(7, {"visibility": "unlisted", "frames": [FRAME],
                              "photo": {"data": f"data:image/png;base64,{png_b64((20, 0, 0))}", "fit": "fit"}})
        assert st2 == 201, st2
        draft_pid = b2["id"]
        eng = _sa.create_engine(_url)
        with eng.begin() as c:
            c.execute(_sa.text(
                "UPDATE skribl_posts SET visibility='draft' "
                "WHERE public_id=:p"), {"p": draft_pid})
        eng.dispose()
else:
    draft_pid = body.get("id")
draft_media = media_url_of(draft_pid, 7)
check("host-state ('draft') post exists with media", bool(draft_media),
      str(draft_media))

# No policy: 'draft' is unknown -> author-only. Both surfaces must agree.
r_post = build_app(None).test_client().get(f"/api/skribls/{draft_pid}")
r_med = build_app(None).test_client().get(draft_media)
check("without a policy, an unknown state is author-only on BOTH surfaces",
      r_post.status_code == 404 and r_med.status_code == 404,
      f"post {r_post.status_code}, media {r_med.status_code}")

# A policy GRANTING 'draft' to everyone: media must follow the grant.
skribl.set_visibility_policy(
    lambda post, viewer: True if post.visibility == "draft" else None)
try:
    r_post = build_app(None).test_client().get(f"/api/skribls/{draft_pid}")
    r_med = build_app(None).test_client().get(draft_media)
    check("a policy GRANT reaches the media route too",
          r_post.status_code == 200 and r_med.status_code == 200,
          f"post {r_post.status_code}, media {r_med.status_code}")
finally:
    skribl.set_visibility_policy(None)

# A policy REVOKING an unlisted post: media must follow the refusal. This is
# the leak direction — a moderated post's media staying up.
st, body = post_as(3, {"visibility": "unlisted", "frames": [FRAME],
                       "photo": {"data": f"data:image/png;base64,{png_b64((30, 0, 0))}", "fit": "fit"}})
check("an unlisted post with media is created", st == 201, str(st))
mod_pid = body.get("id")
mod_media = media_url_of(mod_pid, 3)
check("its media resolved", bool(mod_media), str(mod_media))
skribl.set_visibility_policy(
    lambda post, viewer: False if post.public_id == mod_pid else None)
try:
    r_post = build_app(None).test_client().get(f"/api/skribls/{mod_pid}")
    r_med = build_app(None).test_client().get(mod_media)
    check("a policy REVOCATION reaches the media route too",
          r_post.status_code == 404 and r_med.status_code == 404,
          f"post {r_post.status_code}, media {r_med.status_code}")
finally:
    skribl.set_visibility_policy(None)

print("\nBASESNAPSHOT — externalised and authorised like every other image")
st, body = post_as(1, {"visibility": "private", "frames": [FRAME],
                       "baseSnapshot": f"data:image/png;base64,{png_b64((50, 0, 0))}"})
check("a private post with a baseSnapshot is created", st == 201, str(st))
snap_pid = body.get("id")
a = build_app(1)
r = a.test_client().get(f"/api/skribls/{snap_pid}")
snap_url = ((r.get_json() or {}).get("skribl") or {}).get("baseSnapshot")
check("the baseSnapshot was externalised to /media/<key>",
      isinstance(snap_url, str) and snap_url.startswith("/media/"),
      str(snap_url)[:70])
if isinstance(snap_url, str) and snap_url.startswith("/media/"):
    r = build_app(None).test_client().get(snap_url)
    check("and the /media authorisation guards it: anonymous gets 404",
          r.status_code == 404, str(r.status_code))
    r = build_app(1).test_client().get(snap_url)
    check("while its author can fetch it", r.status_code == 200,
          str(r.status_code))
else:
    check("and the /media authorisation guards it: anonymous gets 404", False,
          "not externalised, nothing to guard")
    check("while its author can fetch it", False, "not externalised")

print("\nCACHE DEFAULTS — authorisation-dependent means private, no-store")
st, body = post_as(None, {"visibility": "public", "frames": [FRAME],
                          "photo": {"data": f"data:image/png;base64,{png_b64((40, 0, 0))}", "fit": "fit"}})
check("a public post with media is created", st == 201, str(st))
pub_pid = body.get("id")
pub_media = media_url_of(pub_pid, None)
r = build_app(None).test_client().get(pub_media)
cc = r.headers.get("Cache-Control", "")
check("public media WITHOUT the opt-in: private, no-store",
      "no-store" in cc and "public" not in cc, cc)
r = build_app(None).test_client().get(f"/s/{pub_pid}/card.png")
cc = r.headers.get("Cache-Control", "")
check("the share card WITHOUT the opt-in: never `public`",
      "public" not in cc, f"{r.status_code} {cc}")

opted = build_app(None, public_media_cache=True)
r = opted.test_client().get(pub_media)
cc = r.headers.get("Cache-Control", "")
check("WITH the opt-in, all-public media is public+immutable",
      "public" in cc and "immutable" in cc, cc)
r = opted.test_client().get(private_media)
check("...but the opt-in never publicises a blob a private post references",
      r.status_code == 404, str(r.status_code))
r = build_app(1, public_media_cache=True).test_client().get(private_media)
cc = r.headers.get("Cache-Control", "")
check("the author's copy of it stays private, no-store even opted in",
      r.status_code == 200 and "no-store" in cc and "public" not in cc,
      f"{r.status_code} {cc}")

# Opt-in + policy: a policy refusing the 'public' post must veto the public
# cache header, because the policy is part of the authorisation.
skribl.set_visibility_policy(
    lambda post, viewer: (False if (post.public_id == pub_pid
                                    and viewer is None) else None))
try:
    r = opted.test_client().get(pub_media)
    check("a policy refusing anonymous viewers vetoes public caching too",
          r.status_code == 404, str(r.status_code))
finally:
    skribl.set_visibility_policy(None)

print("\nSHARE CARD — an externalised thumbnail still renders the drawing")
st, body = post_as(None, {"visibility": "public", "frames": [FRAME],
                          "thumbnail": f"data:image/png;base64,{png_b64((60, 0, 0))}"})
check("a public post with a thumbnail is created", st == 201, str(st))
card_pid = body.get("id")
r = build_app(None).test_client().get(f"/s/{card_pid}/card.png")
check("the card serves the drawing's bytes, not the generic fallback",
      r.status_code == 200 and r.mimetype == "image/png"
      and b"IHDR" in r.get_data()[:64],
      f"{r.status_code} {r.mimetype} (a 302 here means the externalised "
      f"thumbnail fell through to the branded card)")
st, body = post_as(9, {"visibility": "private", "frames": [FRAME],
                       "thumbnail": f"data:image/png;base64,{png_b64((70, 0, 0))}"})
r = build_app(None).test_client().get(f"/s/{body.get('id')}/card.png")
check("...while a private post's card still falls back for strangers",
      r.status_code == 302, str(r.status_code))

print("\nPARSER PARITY — what validation accepts, storage externalises")
# v200 follow-up review, F4 / v199 F12: validation strips and lowercases;
# storage tested the RAW string and looked up the RAW MIME. A whitespace-
# padded data URL validated, then failed storage's is_data_url and stayed
# inline in payload_json with no association row; `Audio/WAV` validated as
# audio/wav and externalised as .bin/octet-stream.
_padded = "  data:image/png;base64," + png_b64((80, 0, 0)) + "  "
st, body = post_as(None, {"visibility": "public", "frames": [FRAME],
                          "photo": {"data": _padded, "fit": "fit"}})
check("a whitespace-padded valid data URL is accepted", st == 201, str(st))
if st == 201:
    r = build_app(None).test_client().get(f"/api/skribls/{body['id']}")
    _p = ((r.get_json() or {}).get("skribl") or {}).get("photo") or {}
    _u = _p.get("data")
    check("...and externalised — no inline media survives in the payload",
          isinstance(_u, str) and _u.startswith("/media/")
          and "base64" not in str(r.get_data())[:200000],
          str(_u)[:60])
else:
    check("...and externalised — no inline media survives in the payload",
          False, "post refused")
import base64 as _b64
_wav = ("data:Audio/X-WAV;base64," + _b64.b64encode(
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b"\x40\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00").decode())
st, body = post_as(None, {"visibility": "public", "frames": [FRAME],
                          "music": {"data": _wav}})
if st == 201:
    r = build_app(None).test_client().get(f"/api/skribls/{body['id']}")
    _m = ((r.get_json() or {}).get("skribl") or {}).get("music") or {}
    _u = str(_m.get("data") or "")
    check("mixed-case MIME externalises to the canonical extension, not .bin",
          _u.startswith("/media/") and _u.endswith(".wav"), _u[-30:])
    if _u.startswith("/media/"):
        rr = build_app(None).test_client().get(_u)
        check("...and serves back as canonical audio/wav",
              rr.status_code == 200 and rr.mimetype == "audio/wav",
              f"{rr.status_code} {rr.mimetype}")
    else:
        check("...and serves back as canonical audio/wav", False, "not external")
else:
    check("mixed-case MIME externalises to the canonical extension, not .bin",
          False, f"POST {st} {str(body)[:60]}")
    check("...and serves back as canonical audio/wav", False, "post refused")

print("\nIDEMPOTENCY — author-scoped: replays for the author, never across")
import uuid as _uuid
_k = str(_uuid.uuid4())
_h = {"Idempotency-Key": _k}
a7 = build_app(7)
r1 = a7.test_client().post("/api/skribls", json={"frames": [FRAME]}, headers=_h)
r2 = a7.test_client().post("/api/skribls", json={"frames": [FRAME]}, headers=_h)
check("the SAME author retrying the SAME key replays the same post",
      r1.status_code == 201 and r2.status_code == 200
      and (r2.get_json() or {}).get("id") == (r1.get_json() or {}).get("id"),
      f"{r1.status_code}/{r2.status_code}")
r3 = build_app(8).test_client().post("/api/skribls", json={"frames": [FRAME]},
                                     headers=_h)
check("a DIFFERENT author with the same key gets a different post",
      r3.status_code == 201
      and (r3.get_json() or {}).get("id") != (r1.get_json() or {}).get("id"),
      f"{r3.status_code}")

print("\nPER-APP SEAMS — one process, two apps, two policies, two budgets")
# The module-level setter used to be the ONLY policy seam, so the most
# recently configured app decided visibility for every app in the process.
appA = build_app(None)
appB = build_app(None)
skribl.set_visibility_policy(
    lambda post, viewer: True if post.visibility == "draft" else None,
    app=appA)
skribl.set_visibility_policy(None, app=appB)  # explicit app-local built-ins
rA = appA.test_client().get(f"/api/skribls/{draft_pid}")
rB = appB.test_client().get(f"/api/skribls/{draft_pid}")
check("app A's grant of 'draft' works in app A", rA.status_code == 200,
      str(rA.status_code))
check("...and does NOT leak into app B", rB.status_code == 404,
      str(rB.status_code))
appA.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 2
for _ in range(2):
    appA.test_client().post("/api/skribls", json={"frames": [FRAME]})
rA = appA.test_client().post("/api/skribls", json={"frames": [FRAME]})
rB = appB.test_client().post("/api/skribls", json={"frames": [FRAME]})
check("app A's own attempt budget exhausts app A", rA.status_code == 429,
      str(rA.status_code))
check("...while app B keeps the process default", rB.status_code == 201,
      str(rB.status_code))

print("\nv201 GATE PINS — F2/F3/F4/F5/F6")
# F2: exhausting app A's memory budget leaves app B's untouched (same IP).
appA2, appB2 = build_app(None), build_app(None)
appA2.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 2
appB2.config["SKRIBL_RATE_MAX_ATTEMPTS"] = 2
for _ in range(3):
    rA = appA2.test_client().post("/api/skribls", json={"frames": [FRAME]},
                                  environ_overrides={"REMOTE_ADDR": "7.7.7.7"})
rB = appB2.test_client().post("/api/skribls", json={"frames": [FRAME]},
                              environ_overrides={"REMOTE_ADDR": "7.7.7.7"})
check("F2: app A exhausted its own budget", rA.status_code == 429,
      str(rA.status_code))
check("F2: ...while app B's budget for the same IP is untouched",
      rB.status_code == 201, str(rB.status_code))

# F3: a bytes SECRET_KEY must hash, not AttributeError.
import skribl.ratelimit as _rl
appC = build_app(None)
appC.config["SECRET_KEY"] = b"bytes-secret-form"
with appC.app_context():
    try:
        h = _rl._rate_key("1.2.3.4")
        check("F3: bytes SECRET_KEY hashes (64 hex)", len(h) == 64, h[:12])
    except Exception as e:
        check("F3: bytes SECRET_KEY hashes (64 hex)", False, repr(e)[:60])

# F4: same author, same key, DIFFERENT body -> 409, never a silent replay.
_k4 = {"Idempotency-Key": "gate-f4-key"}
a4 = build_app(4)
r1 = a4.test_client().post("/api/skribls", json={"frames": [FRAME],
                                                 "title": "first"},
                           headers=_k4)
r2 = a4.test_client().post("/api/skribls", json={"frames": [FRAME],
                                                 "title": "second"},
                           headers=_k4)
check("F4: reused key with a different body is refused (409)",
      r1.status_code == 201 and r2.status_code == 409,
      f"{r1.status_code}/{r2.status_code}")
r3 = a4.test_client().post("/api/skribls", json={"frames": [FRAME],
                                                 "title": "first"},
                           headers=_k4)
check("F4: the ORIGINAL body still replays",
      r3.status_code == 200
      and (r3.get_json() or {}).get("id") == (r1.get_json() or {}).get("id"),
      str(r3.status_code))

# F5: an unknown field holding the SAME string as photo.data stays inline.
_du = f"data:image/png;base64,{png_b64((90, 0, 0))}"
st, body = post_as(None, {"visibility": "public", "frames": [FRAME],
                          "photo": {"data": _du, "fit": "fit"},
                          "hostExtensionEcho": _du})
check("F5: payload with a media-equal extension string is accepted",
      st == 201, str(st))
if st == 201:
    r = build_app(None).test_client().get(f"/api/skribls/{body['id']}")
    sk = (r.get_json() or {}).get("skribl") or {}
    check("F5: the media path was externalised",
          str((sk.get("photo") or {}).get("data", "")).startswith("/media/"))
    check("F5: ...but the equal NON-media string is byte-for-byte untouched",
          sk.get("hostExtensionEcho") == _du,
          str(sk.get("hostExtensionEcho"))[:50])
else:
    check("F5: the media path was externalised", False, "post refused")
    check("F5: ...but the equal NON-media string is byte-for-byte untouched",
          False, "post refused")

# F6: session=False fails CLOSED even with another app's global binding live.
bpF = skribl.create_blueprint(session=False)
appF = Flask("no-db")
appF.config["SECRET_KEY"] = "x"
appF.register_blueprint(bpF)
rF = appF.test_client().get("/api/skribls/zzzzzzzz")
check("F6: a session=False blueprint's query FAILS (5xx), never borrows "
      "another app's database", rF.status_code >= 500, str(rF.status_code))

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
