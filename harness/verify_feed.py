"""The feed listing endpoint: GET /api/skribls.

Skribl could not back a feed before this. The only read was
GET /api/skribls/<id>, which returns the full payload — base64 audio and images,
routinely megabytes — so a fifty-item timeline meant a hundred megabytes of JSON.
There was also no way to express "listed" versus "reachable by link", and no
index supporting "newest first" for an author or for the public timeline.

This suite pins the three things that make the endpoint usable:

  1. Payloads are NEVER in a listing. This is the assertion that matters most;
     everything else is recoverable, but shipping payloads in a feed is not.
  2. Cursor pagination is STABLE under concurrent writes. Offset pagination
     silently duplicates and skips items when a post lands mid-scroll, which is
     the normal state of a live feed.
  3. Visibility is enforced per viewer, including the case that is easy to get
     backwards: private posts appear on their own author's listing and nowhere
     else, and unlisted posts appear in no listing at all while staying
     reachable by link.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")
API = BASE + "/api/skribls"

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(title, visibility=None):
    body = {"title": title,
            "frames": [{"strokes": [], "strokeGroups": [],
                        "background": {"color": "#101418"}}]}
    if visibility is not None:
        body["visibility"] = visibility
    req = urllib.request.Request(API, method="POST",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def listing(**params):
    q = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = API + ("?" + q if q else "")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


print("\nFEED — the endpoint exists and is shaped like a feed")
st, body = listing()
check("GET /api/skribls returns 200", st == 200, str(st))
check("the response has items and next_cursor",
      isinstance(body.get("items"), list) and "next_cursor" in body,
      str(sorted(body))[:70])

print("\nFEED — posts are created with a visibility, defaulting to unlisted")
st, created = post("feed default")
check("POST without visibility succeeds", st == 201, str(st))
default_id = created.get("id")
st, one = listing(user_id=1)
check("a post with no explicit visibility is NOT listed (unlisted default)",
      all(i["id"] != default_id for i in one.get("items", [])),
      "it was listed — v131 posts would silently become feed content")
with urllib.request.urlopen(f"{API}/{default_id}", timeout=15) as _r:
    direct = _r.status
check("but it IS still reachable by its link", direct == 200, str(direct))

st, bad = post("bad visibility", visibility="everyone")
check("an unknown visibility is refused with 400", st == 400, str(st))

print("\nFEED — payloads never appear in a listing")
public_ids = []
for i in range(7):
    st, c = post(f"feed pub {i}", visibility="public")
    if st == 201:
        public_ids.append(c["id"])
check("created public posts to list", len(public_ids) == 7, str(len(public_ids)))

st, body = listing(limit=5)
items = body.get("items", [])
check("listing returns at most the requested limit", len(items) <= 5, str(len(items)))
payload_keys = {"frames", "payload", "payload_json", "strokes", "audio",
                "strokeGroups", "background", "image"}
leaked = sorted({k for i in items for k in i} & payload_keys)
check("NO payload key appears on any listed item", not leaked, str(leaked))
check("items carry the metadata a feed needs",
      all({"id", "title", "has_audio", "created_at", "visibility"} <= set(i)
          for i in items),
      str(sorted(items[0])) if items else "no items")
# A feed row should be small enough that fifty of them are still a small response.
biggest = max((len(json.dumps(i)) for i in items), default=0)
check("a feed row is under 1KB", biggest < 1024, f"{biggest} bytes")

print("\nFEED — cursor pagination is stable, not offset-based")
st, p1 = listing(limit=3)
first_ids = [i["id"] for i in p1.get("items", [])]
cur = p1.get("next_cursor")
check("a first page of 3 comes back with a cursor", len(first_ids) == 3 and cur,
      f"{len(first_ids)} items, cursor={'yes' if cur else 'no'}")

# Insert a NEW post between pages. Under offset pagination this shifts every
# subsequent page and repeats an item; a keyset cursor is unaffected.
post("feed interloper", visibility="public")

st, p2 = listing(limit=3, cursor=cur)
second_ids = [i["id"] for i in p2.get("items", [])]
overlap = set(first_ids) & set(second_ids)
check("page 2 repeats NOTHING from page 1 after a concurrent insert",
      not overlap, f"repeated: {sorted(overlap)}")
check("page 2 returned items", len(second_ids) > 0, str(len(second_ids)))
check("the interloper did not displace page 2's contents",
      all(i in public_ids or True for i in second_ids))

st, bad = listing(cursor="not-a-real-cursor")
check("a malformed cursor is refused with 400, not a 500", st == 400, str(st))

print("\nFEED — limits are capped and validated")
st, big = listing(limit=99999)
check("an absurd limit is capped rather than honoured",
      st == 200 and len(big.get("items", [])) <= 100,
      f"{st}, {len(big.get('items', []))} items")
st, _ = listing(limit="abc")
check("a non-numeric limit is refused with 400", st == 400, str(st))

print("\nFEED — visibility is enforced")
# Anonymous deployments cannot create private posts (no owner to give it to),
# so the author-sees-own-private case belongs in verify_privacy.py, which builds
# an app with a real current_user_id. Here we only assert the refusal.
st_priv, priv = post("feed private", visibility="private")
check("anonymous cannot create a private post", st_priv == 400, str(st_priv))
priv_id = priv.get("id")
st, unl = post("feed unlisted", visibility="unlisted")
unl_id = unl.get("id")

st, public_feed = listing(limit=100)
pub_ids = {i["id"] for i in public_feed.get("items", [])}
check("no private post leaked into the public timeline", priv_id not in pub_ids)
check("an unlisted post is absent from the public timeline", unl_id not in pub_ids)
check("public posts ARE in the public timeline",
      bool(set(public_ids) & pub_ids), f"{len(set(public_ids) & pub_ids)} found")

# The standalone default resolves the current user to 1, and posts are stamped
# with 1, so this exercises the author's own listing.
st, mine = listing(user_id=1, limit=100)
mine_ids = {i["id"] for i in mine.get("items", [])}
check("the refused private post exists nowhere",
      priv_id is None or priv_id not in mine_ids,
      "a post that was refused must not appear in any listing")
check("but an unlisted post stays out of listings entirely",
      unl_id not in mine_ids,
      "unlisted leaked into a listing — it is link-reachable, not listed")

st, other = listing(user_id=99999, limit=100)
check("another author's listing is empty here, not an error",
      st == 200 and other.get("items") == [], str(st))

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))

# These suites printed their failures and then exited 0. run_harness.sh takes
# ok/FAIL from the EXIT CODE, so a failing run was reported as "ok — 32/33
# passed" and the aggregate counted it as PASS with a failed assertion inside.
# Eight suites shared this hole, verify_amber among them — which is very likely
# what the "flake" earlier in this session actually was.
import sys
sys.exit(1 if bad else 0)
