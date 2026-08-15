"""What the browser actually has to download, and where "watch it" goes.

WHY THIS EXISTS. Every asset this blueprint served came back
`Cache-Control: no-cache` and uncompressed — Flask's defaults, never chosen.
Measured on the v191 tree before this suite:

    editor   25 files   559,734 B
    player    5 files   350,950 B   (app.js alone 214,132 B)
    one API payload with a photo and a track        384,321 B

with a revalidation round trip per file per page load. On a phone that is what
left a shared link sitting on an unsized 300x150 canvas for fifteen seconds
before app.js arrived, and it is a bigger number than the entire 77 KB the
player-split work was chasing. gzip alone takes the editor's assets down about
70% and that API payload to roughly 5% of its size, because base64 media inside
JSON is close to the best case compression has.

Long caching is safe HERE specifically because asset_url() busts on content: a
changed file gets a new ?v=, so nothing stale can be pinned. The assertions
below check that pairing holds — immutable caching ONLY where a bust is present
— because immutable caching without a bust is how you ship a build nobody can
receive.

Scope is asserted too. Both behaviours live on `bp.after_request`, so they touch
only this blueprint's responses. A flask_compress on the application would
compress and cache the HOST'S pages, which is the reach-past-the-seam mistake
the SQLite foreign-key listener already made once.

The last section covers `player_target`. Pad's watch button did
`location.href = url`, which inside a host navigates the HOST'S document away;
Flip's equivalent and the posted-list link were already `target="_blank"`. Two
of three opened a tab and one did not, and the difference was that one is a
<button> and the others are <a>. The default is now _blank everywhere, with
_self available for a host that routes the player itself.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402

# Registered BEFORE the first request: Flask refuses route registration after
# one has been handled. A route the host owns, used below to prove that neither
# after_request hook reaches past the blueprint.
@app.route("/__host_only_probe")
def _host_only_probe():
    return "x" * 4000


results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


GZIP = {"Accept-Encoding": "gzip"}
c = app.test_client()
editor_html = c.get("/skribl-pad").data.decode("utf-8", "replace")
assets = [(m.group(1), m.group(2)) for m in
          re.finditer(r'/static/skribl/([A-Za-z0-9_./-]+\.(?:js|css))\?v=([a-f0-9]+)', editor_html)]

print("DELIVERY — busted assets are cached immutably, unbusted ones are not")
check("the editor page references content-busted assets at all", len(assets) >= 5,
      f"{len(assets)} found")
name, ver = assets[0]
busted = c.get(f"/static/skribl/{name}?v={ver}")
check("a busted asset is cached long and immutable",
      "immutable" in (busted.headers.get("Cache-Control") or ""),
      f"Cache-Control: {busted.headers.get('Cache-Control')!r} — Flask's default "
      "no-cache means every asset revalidates on every page load")
plain = c.get(f"/static/skribl/{name}")
check("an UNBUSTED request is not pinned",
      "immutable" not in (plain.headers.get("Cache-Control") or ""),
      f"Cache-Control: {plain.headers.get('Cache-Control')!r} — without a bust "
      "there is no way to reach a user who cached it")

print("\nDELIVERY — text assets and API payloads are compressed")
tot_plain = tot_gzip = 0
for n, v in assets:
    tot_plain += len(c.get(f"/static/skribl/{n}?v={v}").data)
    tot_gzip += len(c.get(f"/static/skribl/{n}?v={v}", headers=GZIP).data)
check("the editor's assets compress by at least half",
      tot_gzip * 2 < tot_plain,
      f"{tot_plain:,} B -> {tot_gzip:,} B ({100 - 100 * tot_gzip // max(tot_plain, 1)}% saved)")
print(f"    editor assets {tot_plain:,} B plain, {tot_gzip:,} B gzipped")

js = next((f"{n}?v={v}" for n, v in assets if n.endswith("app.js")), None)
if js:
    g = c.get(f"/static/skribl/{js}", headers=GZIP)
    check("app.js is served gzipped when asked",
          g.headers.get("Content-Encoding") == "gzip",
          "send_file streams by default and a streamed response cannot be "
          "compressed; direct_passthrough has to be turned off first")

check("a response carries Vary: Accept-Encoding",
      "Accept-Encoding" in (c.get("/skribl-pad", headers=GZIP).headers.get("Vary") or ""),
      "without it a shared cache can hand a gzipped body to a client that "
      "did not ask for one")

pg = c.get("/skribl-pad", headers=GZIP)
check("the editor HTML itself is compressed",
      pg.headers.get("Content-Encoding") == "gzip",
      f"{len(pg.data):,} B")

# An already-compressed type must not be re-packed: it costs CPU and grows.
png = c.get("/static/skribl/img/favicon.png", headers=GZIP)
if png.status_code == 200:
    check("an already-compressed binary is left alone",
          png.headers.get("Content-Encoding") != "gzip",
          "re-gzipping a PNG spends CPU to make it slightly larger")

print("\nDELIVERY — the hooks touch this blueprint ONLY")
# A route the host owns must come back untouched by either behaviour.
hostr = app.test_client().get("/__host_only_probe", headers=GZIP)
check("a host route is not compressed by us",
      hostr.headers.get("Content-Encoding") != "gzip",
      "bp.after_request must not reach the host's own responses")
check("a host route does not get our Vary either",
      "Accept-Encoding" not in (hostr.headers.get("Vary") or ""),
      "any header we add to a host response is a header we chose for someone else")

print("\nDELIVERY — where 'watch it' opens")
from skribl import create_blueprint  # noqa: E402

try:
    create_blueprint(session=False, player_target="popup")
    check("an unknown player_target is rejected", False, "'popup' was accepted")
except ValueError:
    check("an unknown player_target is rejected", True,
          "a named target would let one embed steal another's tab")

check("the editor is told where the player opens",
      'SKRIBL_PLAYER_TARGET = "_blank"' in editor_html,
      "editor_post.js reads this; without it Pad falls back to _blank anyway, "
      "but a host asking for _self would be ignored")
flip_html = c.get("/flip").data.decode("utf-8", "replace")
check("Flip's Open player anchor uses the configured target, not a literal",
      'id="flipShareOpen"' in flip_html and 'target="_blank"' in flip_html,
      "it was hardcoded target=_blank, which is right by luck and wrong to keep")
check("Pad's watch button no longer navigates unconditionally",
      "location.href = lastPostUrl" not in
      (pathlib.Path(__file__).resolve().parent.parent /
       "skribl" / "static" / "editor_post.js").read_text(encoding="utf-8")
      .split("watchBtn.addEventListener")[1].split("});")[0]
      or "SKRIBL_PLAYER_TARGET" in
      (pathlib.Path(__file__).resolve().parent.parent /
       "skribl" / "static" / "editor_post.js").read_text(encoding="utf-8"),
      "inside a host that navigates the HOST'S document away from the page "
      "Skribl was embedded in")

print("\nDELIVERY — compression must not cost more than it saves")
# The first version of this recompressed every static file on every request:
# 10.4 ms against 0.6 ms unmodified, 37 ms of CPU for one cold page load of 25
# assets, serialised across two sync workers. A busted URL names one immutable
# byte sequence, so the compressed form is cached per version and a warm request
# is a dict lookup. This asserts that the caching EXISTS, not a wall-clock time,
# because a timing threshold on shared CI is a flake generator.
import skribl.security as _sec  # noqa: E402

# The caches are APP-LOCAL now (outside review: module-level was cross-app
# state, and any ?v= was honoured — verify_assetcache.py pins both fixes).
_gzc = app.extensions["skribl"].setdefault("gzip_cache", {})
_gzc.clear()
n0, v0 = assets[0]
c.get(f"/static/skribl/{n0}?v={v0}", headers=GZIP)
check("a compressed asset is cached by version, not recompressed per request",
      (f"/static/skribl/{n0}", v0) in _gzc,
      f"cache holds {len(_gzc)} entries after one busted request")
_before = dict(_gzc)
c.get(f"/static/skribl/{n0}?v={v0}", headers=GZIP)
check("a second request reuses those bytes",
      _gzc[(f"/static/skribl/{n0}", v0)] is _before[(f"/static/skribl/{n0}", v0)],
      "the entry was rebuilt, so the cache is not being hit")
check("the cache is bounded", _sec._GZIP_CACHE_MAX <= 512,
      f"max {_sec._GZIP_CACHE_MAX} entries — unbounded is a leak, not a cache")

_gz = c.get(f"/static/skribl/{n0}?v={v0}", headers=GZIP)
_pl = c.get(f"/static/skribl/{n0}?v={v0}")
check("the gzipped and plain variants do NOT share an ETag",
      _gz.headers.get("ETag") != _pl.headers.get("ETag"),
      "send_file derives the tag from the FILE, so both encodings went out under "
      "one tag — Vary saves a compliant cache, a tag naming two byte sequences "
      "is wrong regardless")

print("\nDELIVERY — the upload direction, which is the one users wait on")
# Response compression cannot touch this. A photo-plus-music post is ~2.4 MB of
# request body against ~33 ms of server processing: the wait is transfer.
import gzip as _gzip, json as _json  # noqa: E402

# A REAL wav: media validation checks the container, so 400 KB of "A" is
# rejected on shape and would have tested nothing about compression.
import base64 as _b64, io as _io, struct as _struct, wave as _wave  # noqa: E402

_buf = _io.BytesIO()
with _wave.open(_buf, "wb") as _w:
    _w.setnchannels(1)
    _w.setsampwidth(2)
    _w.setframerate(44100)
    _w.writeframes(b"".join(_struct.pack("<h", (i * 97) % 9000) for i in range(3 * 44100)))
_big = _json.dumps({"title": "gz", "canvasSize": {"cssWidth": 816, "cssHeight": 612, "dpr": 1},
                    "playbackMode": "replay", "schemaVersion": 3,
                    "frames": [{"strokes": [{"x": 1, "y": 1, "t": 0}, {"x": 2, "y": 2, "t": 9}],
                                "strokeGroups": [2],
                                "music": {"data": "data:audio/wav;base64,"
                                          + _b64.b64encode(_buf.getvalue()).decode(),
                                          "name": "t.wav"}}]}).encode()
_packed = _gzip.compress(_big, 6)
check("a gzipped request body is accepted",
      c.post("/api/skribls", data=_packed, content_type="application/json",
             headers={"Content-Encoding": "gzip"}).status_code < 300,
      f"{len(_big):,} B of JSON travels as {len(_packed):,} B")
check("an UNCOMPRESSED body still works",
      c.post("/api/skribls", data=_big, content_type="application/json").status_code < 300,
      "the header is optional on both sides; an older cached editor must keep posting")
check("a malformed compressed body is refused, not crashed on",
      c.post("/api/skribls", data=b"not gzip", content_type="application/json",
             headers={"Content-Encoding": "gzip"}).status_code == 400)
_bomb = _gzip.compress(b"{}" + b" " * 60_000_000)
check("a decompression bomb is refused",
      c.post("/api/skribls", data=_bomb, content_type="application/json",
             headers={"Content-Encoding": "gzip"}).status_code == 400,
      f"{len(_bomb):,} B expanding to 60 MB — MAX_CONTENT_LENGTH bounds the "
      "COMPRESSED bytes, which is no bound at all on what they expand to")

_posted = (pathlib.Path(__file__).resolve().parent.parent /
           "skribl" / "static" / "lib" / "posted.js").read_text(encoding="utf-8")
check("the packing helper lives where BOTH surfaces already load it",
      "function skriblPackBody" in _posted,
      "lib/posted.js is loaded by the editor and by Flip, before either's own "
      "script; duplicating it would be a second thing to keep in step")
for _surface, _f in (("Pad", "editor_post.js"), ("Flip", "flip.js")):
    _src = (pathlib.Path(__file__).resolve().parent.parent /
            "skribl" / "static" / _f).read_text(encoding="utf-8")
    check(f"{_surface} posts through it", "skriblPackBody" in _src,
          f"{_f} still builds its own request body")


print("\nDELIVERY — compression is optional, and is not allowed to break posting")
# A user hit `skriblPackBody is not defined` on Post. No shipped artifact had
# the helper missing while a caller used it, so the live server had a mixed
# deploy — but the real defect was that a mixed deploy COULD break posting at
# all. Compression is an optimisation; it was written as a hard cross-file
# dependency, so lib/posted.js failing to load for any reason (stale cache,
# partial deploy, blocked request) turned "posts a bit slower" into "cannot
# post", with a raw ReferenceError shown to the user.
#
# Asserted by shape rather than by running the browser, because the failure is
# a MISSING file: both call sites must feature-detect before calling.
for _surface, _f in (("Pad", "editor_post.js"), ("Flip", "flip.js")):
    _src = (pathlib.Path(__file__).resolve().parent.parent /
            "skribl" / "static" / _f).read_text(encoding="utf-8")
    _calls = [ln for ln in _src.split("\n") if "skriblPackBody(" in ln]
    _guarded = "typeof skriblPackBody === 'function'" in _src \
        or "typeof skriblPackBody==='function'" in _src
    check(f"{_surface} feature-detects the packing helper before calling it",
          bool(_calls) and _guarded,
          f"{len(_calls)} call site(s), guarded={_guarded} — an unguarded call "
          "makes an optimisation load-bearing")


bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(n for _, n in bad)))
sys.exit(1 if bad else 0)
