"""The CSRF seam on POST /api/skribls.

v131 has no CSRF protection, and that is the RIGHT call there: the API is
unauthenticated, so there is no session for a cross-origin form to ride. Nothing
is gained by making a victim's browser post a drawing as nobody.

The moment a host authenticates this endpoint with a cookie — which is exactly
what dropping Skribl into a social platform does — any page on the internet can
post as the logged-in user. The vulnerability is CREATED BY the integration, so
the seam has to exist and be proven before the integration, not after.

The seam is deliberately optional: `create_blueprint(csrf=...)` takes an
(issue, validate) pair, so a host with its own CSRF machinery passes that, a
host with none passes `skribl.security.double_submit_csrf()`, and passing None
reproduces v131 byte for byte. The standalone app opts IN, so every harness run
exercises the path rather than leaving it untested until it matters.
"""
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 5008
BASE = f"http://127.0.0.1:{PORT}"
API = BASE + "/api/skribls"
HEADER = "X-Skribl-CSRF"
COOKIE = "skribl_csrf"

# Boots its OWN instance with CSRF on, rather than asking the shared harness
# server to enable it. Turning CSRF on globally makes every other suite's
# token-less POST a 403 — which is correct behaviour and a broken test run.
_tmp = tempfile.mkdtemp()
_env = dict(os.environ, SKRIBL_CSRF_PROTECT="1",
            DATABASE_URL=f"sqlite:///{_tmp}/csrf.db",
            SKRIBL_RATE_MAX_POSTS="100000",
            SKRIBL_RATE_MAX_ATTEMPTS="100000",
            SECRET_KEY="harness-csrf-suite")
subprocess.run([sys.executable, "-c",
                "from app import app, db; app.app_context().push(); db.create_all()"],
               cwd=ROOT, env=_env, check=True, capture_output=True)
_proc = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app", "run",
                          "--port", str(PORT), "--no-reload"],
                         cwd=ROOT, env=_env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
_deadline = time.time() + 25
while time.time() < _deadline:
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.5):
            break
    except OSError:
        time.sleep(0.3)
else:
    _proc.kill()
    sys.exit(f"SKIP: CSRF instance did not start on port {PORT}.")

import atexit
atexit.register(lambda: (_proc.terminate(), _proc.wait(timeout=10)))

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

BODY = json.dumps({"frames": [{"strokes": [], "strokeGroups": [],
                               "background": {"color": "#101418"}}]}).encode()


def raw_post(headers=None, opener=None):
    req = urllib.request.Request(API, method="POST", data=BODY,
                                 headers={"Content-Type": "application/json",
                                          **(headers or {})})
    try:
        send = (opener.open if opener else urllib.request.urlopen)
        with send(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


# Is CSRF actually switched on in this deployment? If the host wired nothing,
# these assertions describe v131's behaviour instead, and saying so is more
# useful than pretending the protection exists.
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
with opener.open(BASE + "/flip", timeout=15) as r:
    page = r.read().decode("utf-8", "replace")
token = next((c.value for c in jar if c.name == COOKIE), None)

print("\nCSRF — the token is issued and reaches the client")
check("the server sets a CSRF cookie", bool(token),
      "no cookie — the seam is not wired in this deployment")
if not token:
    print("SUITE-SKIPPED: CSRF is not enabled here (csrf=None).")
    raise SystemExit(77)

check("the cookie is readable by script (double-submit needs it)",
      not any(c.name == COOKIE and getattr(c, "_rest", {}).get("HttpOnly")
              for c in jar))
check("the cookie is SameSite=Lax at minimum",
      any(c.name == COOKIE for c in jar))
check("the page injects the token for the client to echo",
      "SKRIBL_CSRF_TOKEN" in page)
check("the injected token is not empty",
      f'window.SKRIBL_CSRF_TOKEN = "{token}"' in page
      or token in page, "token absent from the page")

print("\nCSRF — a forged cross-origin post is refused")
# The attacker case: the victim's browser WILL send the cookie, because that is
# what cookies do. What it cannot do is read the cookie to set the header.
check("cookie present but NO header is refused with 403",
      raw_post(opener=opener) == 403, str(raw_post(opener=opener)))
check("a wrong header value is refused with 403",
      raw_post({HEADER: "not-the-token"}, opener=opener) == 403)
check("a header of the right shape but wrong value is still refused",
      raw_post({HEADER: "x" * len(token)}, opener=opener) == 403,
      "a length-only comparison would have let this through")
check("no cookie and no header is refused with 403",
      raw_post({HEADER: token}) == 403,
      "the header alone must not be sufficient")

print("\nCSRF — the legitimate client still works")
st = raw_post({HEADER: token}, opener=opener)
check("cookie AND matching header posts successfully", st == 201, str(st))

print("\nCSRF — reads are unaffected")
with opener.open(BASE + "/flip", timeout=15) as r:
    check("GET pages need no token", r.status == 200, str(r.status))
try:
    with opener.open(API + "?limit=1", timeout=15) as r:
        check("the feed listing needs no token", r.status == 200, str(r.status))
except urllib.error.HTTPError as e:
    check("the feed listing needs no token", False, str(e.code))

print("\nCSRF — the token is stable across requests")
with opener.open(BASE + "/", timeout=15) as r:
    r.read()
again = next((c.value for c in jar if c.name == COOKIE), None)
check("the same token is reused rather than rotated per request",
      again == token,
      "rotating per response breaks any client that cached the first one")

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
