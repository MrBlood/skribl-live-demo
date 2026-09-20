"""v280 — the operator's door, for posts nobody else can withdraw.

THE FINDING, from an adversarial audit of v279. The v279 capability is minted
at creation, so every row that predates the migration holds NULL and
`_token_matches()` refuses NULL on purpose — an empty token matching an empty
hash would make the whole anonymous back-catalogue deletable by anybody. The
consequence is that those authors have no self-service route at all, and the
audit's fix was explicit: do NOT invent a cryptographic one (possession of the
share URL is possession of the thing the author gave away, so it proves the
opposite of ownership), and instead provide an administrative path built on the
`require_author=False` that already existed with nothing to invoke it.

`python -m skribl.takedown` is that path. This suite is the proof it works and,
just as importantly, the proof of what it REFUSES.

The rule this suite follows, borrowed from verify_sweepjob: drive the CLI as a
real subprocess, so the exit codes asserted are the ones an operator's runbook
would actually see rather than the ones the source implies.

Runs in-process against a temp SQLite file. No server, no browser.
"""
import os
import subprocess
import sys
import tempfile
from assertions import make_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB_DIR = tempfile.mkdtemp()
MEDIA_ROOT = tempfile.mkdtemp()
DB_URL = f"sqlite:///{DB_DIR}/takedown.db"

results = []


check = make_check(results, detail_on_pass=False)


ENV = dict(os.environ, DATABASE_URL=DB_URL, SKRIBL_MEDIA_BACKEND="local",
           SKRIBL_MEDIA_ROOT=MEDIA_ROOT, SECRET_KEY="harness-takedown")
os.environ.update(ENV)

from app import create_app                                        # noqa: E402
from skribl.deletion import hash_delete_token                     # noqa: E402
from skribl.models import SkriblPost, session                     # noqa: E402

app = create_app()
with app.app_context():
    import app as _app_module
    _app_module.db.create_all()

PAYLOAD = {"v": 1, "canvas": {"w": 100, "h": 100}, "strokes": []}


def plant(public_id, *, user_id=None, token=None, visibility="unlisted"):
    with app.app_context():
        s = session()
        s.add(SkriblPost(public_id=public_id, title=public_id,
                         payload_json=PAYLOAD, visibility=visibility,
                         user_id=user_id,
                         delete_token_hash=hash_delete_token(token) if token else None))
        s.commit()


def exists(public_id):
    with app.app_context():
        return (session().query(SkriblPost)
                .filter(SkriblPost.public_id == public_id).one_or_none()) is not None


def visibility_of(public_id):
    with app.app_context():
        p = (session().query(SkriblPost)
             .filter(SkriblPost.public_id == public_id).one_or_none())
        return p.visibility if p else None


def cli(*args):
    p = subprocess.run([sys.executable, "-m", "skribl.takedown",
                        "--app", "app:create_app", *args],
                       cwd=ROOT, env=ENV, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


# ── the census the audit asked to be run against production ─────────────────
print("\nORPHANS — the query that decides whether the finding has victims")
plant("legacy-a")                                   # no owner, no key: an orphan
plant("legacy-b")                                   # ditto
plant("owned-1", user_id="user-7")                  # ownership authorises it
plant("keyed-1", token="a-real-recovery-key")       # a capability authorises it

code, out, err = cli("--list-orphans")
check("--list-orphans exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("it counts exactly the posts nobody can revoke", "2 post(s)" in out,
      out.strip().splitlines()[0] if out.strip() else "(no output)")
check("it names them", "legacy-a" in out and "legacy-b" in out)
# THE NEGATIVE HALF, and the one that would rot silently: a post with an owner
# or a key is NOT an orphan, and a census that over-counts turns a closed
# finding into a permanent false alarm.
check("a post with an owner is not counted", "owned-1" not in out,
      "ownership authorises deletion, so its author is not stranded")
check("a post with a capability is not counted", "keyed-1" not in out,
      "its author holds the key; counting it inflates the finding")
check("it tells the operator what to do about them", "--delete" in out,
      "a census with no next step is a number, not a runbook")

# ── refusing to guess ───────────────────────────────────────────────────────
print("\nREFUSALS — an operator tool is judged by what it will not do")
code, out, err = cli("no-such-post", "--delete")
check("an unknown public id exits 1, distinctly from 'could not run'", code == 1,
      f"exit {code} — a runbook cannot alert on a code it shares with bad flags")
check("...and says so on stderr", "no post with public id" in err, err.strip()[:120])

code, out, err = cli("legacy-a", "--delete", "--visibility", "private")
check("--delete with --visibility is refused, not silently resolved", code == 2,
      f"exit {code} — two different outcomes asked for at once")
check("legacy-a survived that refusal", exists("legacy-a"))

code, out, err = cli("--delete")
check("a wet flag with no public id is refused", code == 2, f"exit {code}")

# ── dry by default ──────────────────────────────────────────────────────────
print("\nDRY RUN — the default, as in skribl.sweep")
code, out, err = cli("legacy-a")
check("a bare run exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("it says it was a rehearsal", "DRY RUN" in out, out.strip()[-80:])
check("THE POST IS STILL THERE", exists("legacy-a"),
      "a tool that deletes without a wet flag is one typo from a takedown")
# The confirmation step: an operator holding only a public id from a support
# mail has no other way to know they have the right post.
check("it identifies the post before offering to act", "title" in out and "legacy-a" in out,
      out.strip()[:120])
check("and states plainly that this one has no key",
      "none" in out and "this tool exists" in out, out.strip()[:200])

# ── the wet flags ───────────────────────────────────────────────────────────
print("\nACTING — the two things an operator is asked for")
code, out, err = cli("legacy-a", "--delete")
check("--delete exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("the post is gone", not exists("legacy-a"))
check("it says the bytes are not", "sweep" in out,
      "an operator who thinks the media went with it will not run the sweeper")
check("and it did not touch the other orphan", exists("legacy-b"),
      "acting on more than the id given is the failure mode of an operator tool")

code, out, err = cli("legacy-b", "--visibility", "private")
check("--visibility exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("the post survives", exists("legacy-b"),
      "revoke and delete are different products — see deletion.py")
check("and is now private", visibility_of("legacy-b") == "private",
      repr(visibility_of("legacy-b")))

# ── it works on posts that are NOT orphans, deliberately ────────────────────
print("\nSCOPE — the same door covers moderation and a lost key, not just legacy")
code, out, err = cli("keyed-1", "--delete")
check("an owner-held post can still be taken down by an operator", code == 0,
      f"exit {code} — a takedown request does not stop being valid because "
      "the author could also have done it")
check("it is gone", not exists("keyed-1"))

code, out, err = cli("owned-1", "--visibility", "private")
check("so can a post belonging to a host's user", code == 0, f"exit {code}")
check("it is private now", visibility_of("owned-1") == "private")

# ── the report queue (v304) ─────────────────────────────────────────────────
print("\nREPORTS — the gallery's queue lands at the operator's door")
from skribl.models import SkriblReport                             # noqa: E402


def report(public_id, who, reason="spam", note=None, state="open"):
    with app.app_context():
        s = session()
        post = s.query(SkriblPost).filter(SkriblPost.public_id == public_id).one()
        s.add(SkriblReport(post_id=post.id, reason=reason, note=note,
                           reporter_hash=who, state=state))
        s.commit()


def open_count(public_id):
    with app.app_context():
        s = session()
        post = s.query(SkriblPost).filter(SkriblPost.public_id == public_id).one_or_none()
        if post is None:
            return None
        return s.query(SkriblReport).filter(SkriblReport.post_id == post.id,
                                            SkriblReport.state == "open").count()


def all_reports_for(public_id):
    with app.app_context():
        s = session()
        post = s.query(SkriblPost).filter(SkriblPost.public_id == public_id).one_or_none()
        return None if post is None else s.query(SkriblReport).filter(
            SkriblReport.post_id == post.id).count()


plant("flagged-2", visibility="public")
plant("flagged-1", visibility="public")
plant("quiet-1", visibility="public")
report("flagged-2", "h1", "spam", note="an advert")
report("flagged-2", "h2", "abuse")
report("flagged-1", "h3", "other")
report("quiet-1", "h4", "spam", state="closed")          # resolved already: not in the queue

code, out, err = cli("--reports")
check("--reports exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("it counts the posts with OPEN reports", "2 post(s)" in out,
      out.strip().splitlines()[0] if out.strip() else "(no output)")
check("the most-reported post is listed first",
      out.find("flagged-2") != -1 and out.find("flagged-2") < out.find("flagged-1"), out[:300])
check("each post carries its count and reasons", "2 report(s)" in out and "abuse x1" in out and "spam x1" in out)
check("a note travels with it", "an advert" in out)
check("a post whose reports were resolved is not in the queue", "quiet-1" not in out,
      "a closed report is a closed report")
check("it tells the operator the three answers", "--resolve" in out and "--delete" in out and "--visibility private" in out)

# --resolve closes the rows and touches nothing else; it is a wet flag.
code, out, err = cli("flagged-2")
check("a dry run on a reported post says how many reports are open", code == 0 and "2 open" in out, out[-200:])
check("...and changed nothing", open_count("flagged-2") == 2)
code, out, err = cli("flagged-2", "--resolve")
check("--resolve exits 0", code == 0, f"exit {code} — {err.strip()[:160]}")
check("the post's open reports are closed", open_count("flagged-2") == 0)
check("the rows are kept, closed, not deleted", all_reports_for("flagged-2") == 2)
check("the post itself is untouched", exists("flagged-2") and visibility_of("flagged-2") == "public")
code, out, err = cli("--reports")
check("the queue no longer lists it", "flagged-2" not in out and "1 post(s)" in out)
code, out, err = cli("flagged-1", "--resolve", "--delete")
check("--resolve with --delete is refused", code == 2, f"exit {code}")
check("...and nothing happened", open_count("flagged-1") == 1 and exists("flagged-1"))
# Deleting a post takes its reports with it — SQLite does not cascade for us.
code, out, err = cli("flagged-1", "--delete")
check("deleting a reported post exits 0", code == 0, f"exit {code}")


def reports_with_reason(reason):
    with app.app_context():
        return session().query(SkriblReport).filter(SkriblReport.reason == reason).count()


check("its reports went with it", not exists("flagged-1") and reports_with_reason("other") == 0,
      "a report row pointing at a deleted post is an orphan the queue would list as nothing")

bad = [r for r in results if not r[0]]
print(f"\n{'=' * 62}\n{len(results) - len(bad)}/{len(results)} passed"
      + (f"  FAILURES: {'; '.join(n for ok, n in results if not ok)}" if bad else ""))
raise SystemExit(1 if bad else 0)
