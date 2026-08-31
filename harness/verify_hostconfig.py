"""v224 — the three configuration defects from the outside review's low list.

They look unrelated and are the same mistake three times: a number or a policy
stated in more than one place, where only one of the copies could actually
enforce anything.

  TITLE AND CAPTION LENGTH. Three statements, no two agreeing: the columns are
  String(80)/String(300), the create endpoint silently TRUNCATED to [:80]/[:300],
  and the editors' maxlength attributes said 60/280. A 90-character title posted
  through the API came back 201 with half a sentence stored and nothing said;
  the same title could not be typed into the editor at all. core.py now holds
  the two numbers, the columns are declared from them, the endpoint REJECTS with
  the limit in the message, and the templates render maxlength from them.

  PRODUCTION DETECTION. `RENDER or FLASK_ENV=production` is two names for one
  platform and one convention. Everywhere else — Fly, Heroku, Cloud Run, App
  Service, ECS, Kubernetes, a plain gunicorn on a VM — silently got an EPHEMERAL
  SECRET_KEY, different in every worker. Nothing announces that; it surfaces as
  sessions that drop, CSRF tokens rejected by whichever worker did not mint
  them, and a rate limiter whose identity HMAC differs per process.

  RATE LIMITER BACKEND. The library defaults to the in-memory limiter, which is
  per-PROCESS: two gunicorn workers are two independent limiters granting twice
  the configured budget, resetting on every deploy. The library keeps that
  default deliberately — it is right for a single-process dev run and changing
  it would alter existing deployments — so choosing for a DEPLOYMENT is the
  host's job. app.py now makes that choice where it looks like production.

Detection runs as SUBPROCESSES because it happens at import time: `app = 
create_app()` at module scope is what a WSGI server actually executes, and a
check that reached inside create_app() would not be testing the thing that runs.
"""
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BASE = os.environ.get("SKRIBL_BASE", "http://127.0.0.1:5001")

from skribl.core import MAX_CAPTION_CHARS, MAX_TITLE_CHARS   # noqa: E402
from skribl.models import SkriblPost                          # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


def post(payload):
    import json
    req = urllib.request.Request(BASE + "/api/skribls",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200].decode("utf-8", "replace")}


def get_text(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


print("\nONE SOURCE — the limit, the column and the markup are the same number")
_cols = SkriblPost.__table__.c
check("the title column is declared from MAX_TITLE_CHARS",
      _cols.title.type.length == MAX_TITLE_CHARS,
      f"column {_cols.title.type.length}, constant {MAX_TITLE_CHARS}")
check("the caption column is declared from MAX_CAPTION_CHARS",
      _cols.caption.type.length == MAX_CAPTION_CHARS,
      f"column {_cols.caption.type.length}, constant {MAX_CAPTION_CHARS}")

for path, label in (("/", "Pad"), ("/flip", "Flip")):
    html = get_text(path)
    lengths = [int(v) for v in re.findall(r'maxlength="(\d+)"', html)]
    # Every length in these pages belongs to a title, a caption, or the zoom
    # box; what matters is that no page states 60 or 280 any more, and that both
    # real limits are present exactly as the constants define them.
    check(f"{label} renders maxlength from the constants",
          MAX_TITLE_CHARS in lengths and MAX_CAPTION_CHARS in lengths,
          f"maxlength values in the page: {sorted(set(lengths))}")
    check(f"{label} no longer hard-codes the old 60/280",
          60 not in lengths and 280 not in lengths, str(sorted(set(lengths))))

# No source-text assertion here on purpose. The first draft grepped routes.py
# for "[:80]" and failed against the COMMENT explaining why the slice was
# removed — a test of the file's prose, not its behaviour. What actually pins
# this is the pair below: over-length is a 400, and exactly-at-the-limit
# round-trips whole. Truncation cannot satisfy both.


print("\nREJECT, DON'T TRUNCATE — an over-length title is an error, not a haircut")
base = {"strokes": [], "strokeGroups": []}
st, body = post(dict(base, title="A" * (MAX_TITLE_CHARS + 1)))
check("a title one character over the limit is refused", st == 400, f"HTTP {st}")
check("…and the message names the limit and the length",
      str(MAX_TITLE_CHARS) in str(body) and str(MAX_TITLE_CHARS + 1) in str(body),
      str(body)[:120])

st, body = post(dict(base, title="ok", caption="C" * (MAX_CAPTION_CHARS + 1)))
check("an over-length caption is refused", st == 400, f"HTTP {st}")
check("…and names the caption, not the title", "caption" in str(body), str(body)[:100])

st, body = post(dict(base, title="T" * MAX_TITLE_CHARS,
                     caption="C" * MAX_CAPTION_CHARS))
check("EXACTLY at the limit is accepted — the cap is a ceiling, not a fence",
      st == 201, f"HTTP {st} {str(body)[:100]}")
_pid = body.get("id") if st == 201 else None
if _pid:
    import json
    with urllib.request.urlopen(f"{BASE}/api/skribls/{_pid}", timeout=30) as r:
        stored = json.loads(r.read())
    check("and it comes back whole, not shortened",
          len(stored["title"]) == MAX_TITLE_CHARS
          and len(stored["caption"] or "") == MAX_CAPTION_CHARS,
          f"title {len(stored['title'])}, caption {len(stored['caption'] or '')}")

st, _ = post(dict(base, title="  " + "T" * MAX_TITLE_CHARS + "  "))
check("whitespace is stripped BEFORE the length check, not after",
      st == 201, f"HTTP {st} — a padded title that fits must not be a 400")


print("\nPRODUCTION DETECTION — every platform, not just the one we deploy to")
# Each case imports app.py in a clean interpreter with a scrubbed environment.
# Importing is the test: `app = create_app()` at module scope is exactly what a
# WSGI server executes, so this is the code path a deployment actually takes.
SCRUB = ("SECRET_KEY", "RENDER", "FLASK_ENV", "SKRIBL_ENV", "DYNO",
         "SERVER_SOFTWARE", "SKRIBL_ALLOW_EPHEMERAL_SECRET",
         "SKRIBL_RATE_BACKEND", "FLY_APP_NAME", "K_SERVICE",
         "KUBERNETES_SERVICE_HOST", "WEBSITE_SITE_NAME",
         "ECS_CONTAINER_METADATA_URI", "AWS_EXECUTION_ENV")

PROBE = (
    "import app;"
    "print('BACKEND=' + repr(app.app.config.get('SKRIBL_RATE_BACKEND')))"
)


def boot(**env):
    e = {k: v for k, v in os.environ.items() if k not in SCRUB}
    e.update(env)
    p = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=e,
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


PLATFORMS = [
    ("Render", {"RENDER": "true"}),
    ("Heroku", {"DYNO": "web.1"}),
    ("Fly.io", {"FLY_APP_NAME": "skribl"}),
    ("Cloud Run", {"K_SERVICE": "skribl"}),
    ("Azure App Service", {"WEBSITE_SITE_NAME": "skribl"}),
    ("Kubernetes", {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}),
    ("AWS ECS", {"ECS_CONTAINER_METADATA_URI": "http://169.254.170.2/v3"}),
    ("gunicorn on a VM", {"SERVER_SOFTWARE": "gunicorn/21.2.0"}),
    ("uWSGI on a VM", {"SERVER_SOFTWARE": "uWSGI/2.0.21"}),
    ("an explicit SKRIBL_ENV", {"SKRIBL_ENV": "production"}),
    ("the old FLASK_ENV convention", {"FLASK_ENV": "production"}),
]
for label, env in PLATFORMS:
    code, out, err = boot(**env)
    check(f"{label} without SECRET_KEY refuses to boot", code != 0,
          f"exit {code} — {out.strip()[:80]}")
    check(f"…and {label} says why, and how to proceed",
          "SECRET_KEY" in err and "SKRIBL_ALLOW_EPHEMERAL_SECRET" in err,
          err.strip().splitlines()[-1][:110] if err.strip() else "(no stderr)")

# The mutation check for the whole block: if a scrubbed environment ALSO
# refused, every assertion above would be passing for the wrong reason.
code, out, err = boot()
check("MUTATION — with no marker at all it boots on an ephemeral key",
      code == 0, f"exit {code} — {err.strip()[-100:]}")
check("…which is what keeps `flask run` and one-off scripts working", code == 0)

code, out, err = boot(RENDER="true", SECRET_KEY="a-real-key")
check("supplying SECRET_KEY is all a real deployment needs", code == 0,
      f"exit {code} — {err.strip()[-100:]}")
code, out, err = boot(RENDER="true", SKRIBL_ALLOW_EPHEMERAL_SECRET="1")
check("and a deliberate single-process deployment can opt out", code == 0,
      f"exit {code} — {err.strip()[-100:]}")

# OUTSIDE REVIEW OF v263, H2. An EMPTY SECRET_KEY was refused; the KNOWN
# PLACEHOLDER was not. `.env.example` shipped `SECRET_KEY=change-me`, and
# copied verbatim that is a publicly-known signing key that passed the
# `if not secret_key` guard and booted — session and CSRF forgery for anyone
# who has read this repo. Production must refuse the placeholders too.
for ph in ("change-me", "CHANGE-ME", "changeme", "'change-me'", "placeholder"):
    code, out, err = boot(RENDER="true", SECRET_KEY=ph)
    check(f"a production boot refuses the placeholder SECRET_KEY {ph!r}",
          code != 0, f"exit {code} — booted on a known key")
    check(f"…and says why for {ph!r}",
          "SECRET_KEY" in err, err.strip().splitlines()[-1][:90] if err.strip() else "")
# NO FALSE POSITIVE: a real key that merely contains a placeholder word is fine.
code, out, err = boot(RENDER="true", SECRET_KEY="change-me-NOT-" + "x" * 30)
check("a real key that is not exactly a placeholder still boots", code == 0,
      f"exit {code} — the check is an exact-value blocklist, not a substring ban")
# And the opt-out still overrides even a placeholder, for a real throwaway.
code, out, err = boot(RENDER="true", SECRET_KEY="change-me",
                      SKRIBL_ALLOW_EPHEMERAL_SECRET="1")
check("the ephemeral opt-out still overrides a placeholder", code == 0,
      f"exit {code}")


print("\nRATE LIMITER — a deployment gets the shared backend, not a per-worker one")
code, out, err = boot(RENDER="true", SECRET_KEY="a-real-key")
check("a production boot defaults to the durable db limiter",
      "BACKEND='db'" in out, out.strip()[:80])
code, out, err = boot(RENDER="true", SECRET_KEY="k", SKRIBL_RATE_BACKEND="memory")
check("an EXPLICIT memory backend is still honoured", "BACKEND=None" in out,
      f"{out.strip()[:60]} — the host chooses a default, it does not overrule")
code, out, err = boot()
check("a local boot is left on the library default",
      "BACKEND=None" in out, out.strip()[:60])
# And the reason any of this matters, asserted rather than asserted-about: the
# library's own default really is the per-process one.
import skribl.ratelimit as _rl  # noqa: E402
check("the library default really is 'memory' — this is what the host overrides",
      _rl._RATE_BACKEND == "memory", _rl._RATE_BACKEND)


bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
sys.exit(1 if bad else 0)
