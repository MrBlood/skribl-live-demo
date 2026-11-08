"""A fabricated ?v= buys no work: strip/gzip run only for the real bust.

THE DoS (outside review, P0-adjacent, self-inflicted). Every previously-unseen
?v= value used to be honoured as a cache key: ~90 ms of lexing app.js plus a
level-6 gzip, cached under (path, fake_value), with the 128-entry caches
clearing wholesale when full. A loop of fabricated busts therefore forced the
full lex+compress on every request — a CPU DoS assembled from our own
optimisation. And the caches were module globals: cross-application state, one
app's eviction emptying the other's cache.

NOW: a ?v= is honoured only when it equals the file's REAL current content
bust (the digest asset_url() emits). Anything else — fabricated, or a stale
bust for a since-changed file — serves the ordinary un-busted way: correct
bytes, comments intact, no immutable header, no cache entry, no lex. And the
caches live in app.extensions["skribl"], one set per application.

In-process, so the caches can be inspected directly; cache-size and byte-length
assertions rather than wall-clock ones, because a timing threshold on shared CI
is a flake generator.
"""
import pathlib
import re
import sys
import tempfile
from assertions import make_check

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

results = []


check = make_check(results, with_detail=True)


from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import skribl
import skribl.security as _sec


def build_app():
    a = Flask(__name__)
    _tmp = tempfile.mkdtemp()
    a.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{_tmp}/assetcache.db"
    a.config["SECRET_KEY"] = "harness-assetcache"
    d = SQLAlchemy()
    d.init_app(a)
    skribl.init_skribl(a, session=lambda: d.session)
    return a


app = build_app()
c = app.test_client()
GZIP = {"Accept-Encoding": "gzip"}

# The real bust, read off the editor page the way a browser gets it.
page = c.get("/skribl-pad").get_data(as_text=True)
m = re.search(r"/static/skribl/(app\.js)\?v=([0-9a-f]{8})", page)
assert m, "app.js with a bust not found on the editor page"
NAME, REAL = m.group(1), m.group(2)
DISK = (ROOT / "skribl" / "static" / NAME).read_bytes()


def caches():
    ext = app.extensions["skribl"]
    return ext.setdefault("strip_cache", {}), ext.setdefault("gzip_cache", {})


print("\nREAL BUST — the optimisation still works where it is safe")
strip_cache, gzip_cache = caches()
strip_cache.clear(); gzip_cache.clear()
r = c.get(f"/static/skribl/{NAME}?v={REAL}")
check("the real bust gets the immutable header",
      "immutable" in r.headers.get("Cache-Control", ""),
      r.headers.get("Cache-Control", ""))
check("and the stripped body (smaller than disk)",
      len(r.get_data()) < len(DISK),
      f"{len(r.get_data())} vs {len(DISK)} on disk")
check("and one strip-cache entry", len(strip_cache) == 1, str(len(strip_cache)))
c.get(f"/static/skribl/{NAME}?v={REAL}", headers=GZIP)
check("and one gzip-cache entry", len(gzip_cache) == 1, str(len(gzip_cache)))

print("\nFAKE BUSTS — no work, no cache, no immutable promise")
strip_cache.clear(); gzip_cache.clear()
for i in range(40):
    r = c.get(f"/static/skribl/{NAME}?v={i:08d}", headers=GZIP)
check("forty fabricated busts insert ZERO strip-cache entries",
      len(strip_cache) == 0, f"{len(strip_cache)} entries")
check("...and ZERO gzip-cache entries",
      len(gzip_cache) == 0, f"{len(gzip_cache)} entries")
r = c.get(f"/static/skribl/{NAME}?v=deadbeef")
check("a fake bust is served the un-busted way: comments intact",
      len(r.get_data()) == len(DISK),
      f"{len(r.get_data())} vs {len(DISK)} on disk")
check("and WITHOUT the immutable header",
      "immutable" not in r.headers.get("Cache-Control", ""),
      r.headers.get("Cache-Control", ""))
r = c.get(f"/static/skribl/{NAME}?v={REAL}")
check("the real bust still works right after the flood",
      "immutable" in r.headers.get("Cache-Control", "")
      and len(r.get_data()) < len(DISK))
check("(and repopulated exactly one strip entry)", len(strip_cache) == 1,
      str(len(strip_cache)))

print("\nAPP-LOCAL — two applications, two caches")
app2 = build_app()
s2 = app2.extensions["skribl"].setdefault("strip_cache", {})
g2 = app2.extensions["skribl"].setdefault("gzip_cache", {})
s2.clear(); g2.clear()
check("app B starts with empty caches while app A's are warm",
      len(s2) == 0 and len(strip_cache) >= 1,
      f"B strip {len(s2)}, A strip {len(strip_cache)}")
app2.test_client().get(f"/static/skribl/{NAME}?v={REAL}", headers=GZIP)
check("app B warming its cache leaves app A's untouched",
      len(s2) == 1 and len(strip_cache) == 1,
      f"B strip {len(s2)}, A strip {len(strip_cache)}")

print("\nEVERY PAGE'S FILES STAY CACHED — the caps sit above what the app ships")
# THE THRASH (after #798). The caps were 128, from when an editor pulled 25
# files, and both caches empty WHOLESALE when full. The Pad alone now asks for
# 123 scripts and styles and Flip for 117, so opening one and then the other
# emptied the strip cache, and the next open re-lexed every file it had lexed a
# minute before (the Pad again after Flip: 1.5 s of a worker on this box against
# 0.1 s kept; all CPU, so more threads could not help). Pinned twice, as the rows can
# fail apart: the visitor's path through the pages, and the property that keeps
# it true when files are added (a drawer's script fetched on demand is on no
# page, so the page census alone would miss it).
import mimetypes
PAGES = ("/skribl-pad", "/flip", "/feed", "/skribl-pad?compose=1",
         "/flip?compose=1", "/skribl-pad?letters=1", "/library", "/gallery")
BUSTED = re.compile(r"""(/static/skribl/[^"'\s?]+)\?v=([0-9a-f]{8})""")
asked = {pg: set(BUSTED.findall(c.get(pg).get_data(as_text=True))) for pg in PAGES}
lexed = {k for k in set().union(*asked.values()) if k[0].endswith((".js", ".css"))}
zipped = set()


def serve(keys):
    for path, v in sorted(keys):
        if c.get(f"{path}?v={v}", headers=GZIP).headers.get("Content-Encoding") == "gzip":
            zipped.add((path, v))


strip_cache.clear(); gzip_cache.clear()
serve(asked["/skribl-pad"])
pad = {k: (strip_cache.get(k), gzip_cache.get(k)) for k in asked["/skribl-pad"]}
for pg in PAGES[1:]:
    serve(asked[pg])
check(f"every page's scripts and styles stay stripped together ({len(lexed)} files, "
      f"{len(PAGES)} pages): nothing emptied",
      set(strip_cache) == lexed,
      f"{len(set(strip_cache) & lexed)} of {len(lexed)} kept, cap {_sec._STRIP_CACHE_MAX}")
check(f"...and every file sent compressed stays compressed ({len(zipped)} files)",
      bool(zipped) and zipped <= set(gzip_cache),
      f"{len(zipped & set(gzip_cache))} of {len(zipped)} kept, cap {_sec._GZIP_CACHE_MAX}")
serve(asked["/skribl-pad"])
redone = sorted(k[0].rsplit("/", 1)[-1] for k, (s0, g0) in pad.items()
                if strip_cache.get(k) is not s0 or gzip_cache.get(k) is not g0)
check("the Pad again, after every other page: not one of its files stripped or compressed twice",
      not redone, f"{len(redone)} redone: {', '.join(redone[:6])}")
STATIC = ROOT / "skribl" / "static"
on_disk = [f for f in STATIC.rglob("*") if f.is_file()]
n_lex = sum(1 for f in on_disk if f.suffix in (".js", ".css"))
n_zip = sum(1 for f in on_disk if _sec._COMPRESSIBLE.match(mimetypes.guess_type(f.name)[0] or ""))
check(f"each cap sits above every file it could hold ({n_lex} scripts and styles, "
      f"{n_zip} compressible): a real bust is one entry per file, so a running server never empties them",
      _sec._STRIP_CACHE_MAX > n_lex and _sec._GZIP_CACHE_MAX > n_zip,
      f"strip cap {_sec._STRIP_CACHE_MAX}, gzip cap {_sec._GZIP_CACHE_MAX}")

bad = [(n, d) for ok, n, d in results if not ok]
print("\n" + "=" * 62)
print(f"{len(results) - len(bad)}/{len(results)} passed"
      + (("  FAILURES: " + "; ".join(f"{n} ({d})" for n, d in bad)) if bad else ""))
sys.exit(1 if bad else 0)
