#!/usr/bin/env bash
# Start Flask, run the named harness suite(s), tear down. Processes don't survive
# between tool calls in this sandbox, so server + test must share one invocation.
set -uo pipefail   # round 6, #10: a failing stage in the context-header
                   # pipelines must not silently yield a misleading value
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

# The posting suite needs the table to exist. A fresh unzip has no instance/ DB,
# so create it up front — idempotent, safe to repeat.
# Round 6, #9: every variable the app reads is exported BEFORE anything imports
# it, so the db-init process and the server cannot see different environments.
export SKRIBL_RATE_MAX_POSTS="${SKRIBL_RATE_MAX_POSTS:-100000}"


# --- provenance helpers -----------------------------------------------------
# The tree hash previously had two branches that hashed DIFFERENT FILE SETS:
# `git ls-files` lists tracked files INCLUDING harness/LAST-RUN.txt and
# SHA256SUMS, while the find fallback excluded them. Inside a checkout the hash
# therefore covered the very file this run is about to write, so it could never
# be reproduced. Both paths now apply the same exclusions.
_tree_files() {
  if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    # ls-files lists TRACKED files, and a repo that has committed __pycache__
    # tracks .pyc bytecode — which the find branch below excludes. That made the
    # comment above ("Both paths now apply the same exclusions") false: in such a
    # checkout this banner reported a different hash from harness/RELEASE.md,
    # which computes its own list with find. Worse, .pyc content varies by
    # machine and Python build, so the checkout's hash was not reproducible on
    # any other machine. Observed on a real repository with 40 tracked .pyc
    # files: banner b11ffcef..., RELEASE.md 70cf761b....
    # instance/ is excluded here for the same reason: a tracked local database
    # would put a file the app WRITES AT RUNTIME into the hash of the tree.
    git -C "$ROOT" ls-files \
      | grep -v -e '__pycache__/' -e '\.pyc$' -e '^instance/'
  else
    (cd "$ROOT" && find . -type f \
        -not -path './.git/*' -not -path './instance/*' \
        -not -path '*/__pycache__/*' -not -name '*.pyc' \
        | sed 's|^\./||')
  # Generated documents are excluded along with the run record itself.
  # stamp_docs.py rewrites a stanza in README.md, harness/README.md and
  # docs/HANDOFF.md *from* LAST-RUN.txt, i.e. AFTER the run — so including them
  # meant the act of recording a result changed the tree whose hash had just
  # been recorded. The hash could never match the shipped archive, which is
  # exactly what an external review found. Excluding them makes it reproducible.
  # START-HERE.md joined that list when it was brought under stamp_docs.py:
  # a stamped document is written AFTER the run, so leaving it in the hash
  # meant recording a result changed the tree whose hash had just been
  # recorded — the exact defect the three above were excluded for. Anything
  # added to stamp_docs.py's TARGETS must be added here in the same edit.
  fi | grep -vx -e 'harness/LAST-RUN.txt' -e 'SHA256SUMS' \
              -e 'README.md' -e 'harness/README.md' -e 'docs/HANDOFF.md' \
              -e 'START-HERE.md' -e 'harness/RELEASE.md' \
     | LC_ALL=C sort
}

_tree_hash() {
  _tree_files | (cd "$ROOT" && tr '\n' '\0' | xargs -0 sha256sum 2>/dev/null) \
    | sha256sum | cut -d" " -f1
}

# A commit SHA describes the tree only if the working copy is clean. An
# uncommitted edit reported under a clean-looking SHA is exactly the kind of
# claim this banner exists to prevent.
_git_commit() {
  local c
  c=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null) || {
    echo "(not a git checkout)"; return; }
  git -C "$ROOT" diff --quiet HEAD 2>/dev/null || c="$c-dirty"
  echo "$c"
}

# Isolated database per run (round 4, #7). This previously reused the repository
# instance/ DB, so row-delta assertions and "did this run start clean?" could not
# be answered honestly. SKRIBL_KEEP_DB=1 restores the old behaviour.
# A DATABASE_URL supplied by the caller used to be OVERWRITTEN unconditionally,
# so the only way to run the harness against PostgreSQL was SKRIBL_KEEP_DB=1 —
# which also gave up the fresh-database isolation. The banner then still printed
# "sqlite", so a Postgres run silently was not one. Isolation and engine choice
# are now independent: an explicit DATABASE_URL is honoured, and reset by
# dropping and recreating Skribl's tables rather than by making a new file.
if [ "${SKRIBL_KEEP_DB:-0}" = "1" ]; then
  DB_RESET="no (reusing existing DATABASE_URL)"
elif [ -n "${DATABASE_URL:-}" ]; then
  DB_RESET="yes (dropped and recreated Skribl's tables in the supplied DATABASE_URL)"
  python3 - <<'PYRESET' || exit 1
from app import app, db
try:
    from skribl.models import SkriblBase as _B
    md = _B.metadata
except ImportError:
    md = db.metadata
with app.app_context():
    md.drop_all(db.engine)
    md.create_all(db.engine)
PYRESET
else
  HARNESS_TMP="$(mktemp -d)"
  HARNESS_DB="$HARNESS_TMP/harness.db"
  export DATABASE_URL="sqlite:///$HARNESS_DB"
  DB_RESET="yes (fresh $HARNESS_DB)"
fi
python3 -c "from app import app, db; app.app_context().push(); db.create_all()" || exit 1

# The app rate-limits POST /api/skribls to 20/hour/IP. Several suites post, and
# together they sit just under that — so adding a few posting assertions anywhere
# starts producing mystery 429s instead of the real result. Raise the cap for
# harness runs (still overridable) so suites are deterministic and independent.
# COVERAGE NOTE (round 4, #8): this raises the cap on THIS shared server only, so
# nothing running against port 5001 exercises the limiter. That is no longer the
# whole story — verify_review.py launches its OWN server processes with small
# explicit quotas and DOES test quota sequencing, the attempt/post split and
# concurrent reservation. Don't delete those on the assumption it's untested.

# Reproducibility header (round 4, #7): a recorded run should state the conditions
# it was produced under, not only its results.
RUN_HEADER="$({
  echo "================ RUN CONTEXT ================"
  echo "UTC timestamp           : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Host                    : $(uname -sm)"
  echo "Tree SHA-256            : $(_tree_hash)"
  echo "Git commit              : $(_git_commit)"
  # SKRIBL_VERSION moved from app.py into the package when Skribl became a
  # blueprint. Look in both so the run header is never silently blank.
  echo "SKRIBL_VERSION          : $(grep -h -m1 "^SKRIBL_VERSION" "$ROOT/app.py" "$ROOT/skribl/core.py" 2>/dev/null | head -1 | cut -d'"' -f2)"
  echo "Python                  : $(python3 -c "import sys;print(sys.version.split()[0])")"
  echo "Flask                   : $(python3 -c "from importlib.metadata import version;print(version(\"flask\"))" 2>/dev/null || echo missing)"
  echo "SQLAlchemy              : $(python3 -c "from importlib.metadata import version;print(version(\"sqlalchemy\"))" 2>/dev/null || echo missing)"
  echo "Playwright              : $(python3 -c "from importlib.metadata import version;print(version(\"playwright\"))" 2>/dev/null || echo missing)"
  echo "Chromium                : $(python3 -c "from playwright.sync_api import sync_playwright
p=sync_playwright().start();b=p.chromium.launch();print(b.version);b.close();p.stop()" 2>/dev/null || echo unknown)"
  echo "DATABASE_URL class      : $(python3 -c "import os;print(os.environ.get('DATABASE_URL','sqlite (app default)').split(':')[0])")"
  echo "Database reset          : $DB_RESET"
  echo "SKRIBL_RATE_MAX_POSTS   : ${SKRIBL_RATE_MAX_POSTS}"
  echo "SKRIBL_RATE_MAX_ATTEMPTS: ${SKRIBL_RATE_MAX_ATTEMPTS:-(default)}"
  echo "SKRIBL_TRUSTED_PROXIES  : ${SKRIBL_TRUSTED_PROXIES:-(default 0)}"
  echo "SKRIBL_EMBED_ORIGINS    : ${SKRIBL_EMBED_ORIGINS:-(unset)}"
  echo "SKRIBL_CSP              : ${SKRIBL_CSP:-(default on)}"
  echo "Command                 : $0 $*"
  echo "============================================"
})"
printf '%s\n' "$RUN_HEADER"

# A timed-out or killed run leaves a server holding 5001. The next run then
# binds nothing, silently tests against the STALE TREE, and reports green — this
# cost a debugging cycle and produced three false failures. Refuse to proceed
# unless the port is genuinely ours.
if command -v fuser >/dev/null 2>&1; then
  fuser -k 5001/tcp 2>/dev/null || true
else
  pkill -f "flask --app app run --port 5001" 2>/dev/null || true
fi
sleep 1
if (command -v ss >/dev/null 2>&1 && ss -lnt 2>/dev/null | grep -q ":5001 "); then
  echo "Port 5001 is still held by another process. Refusing to run against a" >&2
  echo "server this script did not start — results would not describe this tree." >&2
  exit 1
fi

python3 -m flask --app app run --port 5001 --no-reload > /tmp/flask.log 2>&1 &
FLASK_PID=$!
cleanup() {
  kill "${FLASK_PID:-}" 2>/dev/null || true
  [ -n "${HARNESS_TMP:-}" ] && rm -rf "$HARNESS_TMP"      # round 5, #8
}
trap cleanup EXIT

READY=0
for _ in $(seq 1 40); do
  if ! kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "Flask exited during startup." >&2; cat /tmp/flask.log >&2; exit 1
  fi
  if curl -sf -o /dev/null http://127.0.0.1:5001/; then READY=1; break; fi
  sleep 0.5
done
# Round 5, #9: previously this fell through after 40 tries and turned a startup
# failure into a pile of misleading browser errors.
if [ "$READY" -ne 1 ]; then
  echo "Flask did not become ready on port 5001." >&2; cat /tmp/flask.log >&2; exit 1
fi

RC=0
cd "$ROOT/harness" || exit 1

# No arguments means EVERY suite, not "no suites".
#
# Both CI jobs invoked this with no arguments, and the loop below simply ran zero
# times: TOTAL=0, BAD=0, and the script printed "PASS — every requested suite
# exited 0" and exited 0, because every one of the zero requested suites did
# indeed pass. A green CI job that tested nothing, under a comment claiming CI
# runs the full harness rather than a reduced subset.
if [ "$#" -eq 0 ]; then
  set -- verify_*.py
  echo "No suites named; running all $# of them."
fi
if [ "$#" -eq 0 ]; then
  echo "No verify_*.py suites found in $ROOT/harness — refusing to report a" >&2
  echo "result for an empty run." >&2
  exit 1
fi
LOGDIR="$(mktemp -d)"
TOTAL=0
BAD=0
SKIPPED=0
SUMMARY=""

for suite in "$@"; do
  echo "================ $suite ================"
  log="$LOGDIR/${suite%.py}.log"
  set +e
  # `timeout 600` alone was not enough: it signals only its DIRECT child, and a
  # suite's Playwright browser processes keep the output pipe open, so the shell
  # blocks on the read even after python is gone. A full 26-suite invocation
  # stalled indefinitely this way — never noticed before because LAST-RUN.txt
  # shows the harness has only ever been run in batches, not all at once.
  #
  # setsid puts the suite in its own process group; -k sends KILL if TERM is
  # ignored; and on a timeout the whole group is torn down so nothing is left
  # holding the pipe or a port.
  setsid timeout -k 15 600 python3 "$suite" >"$log" 2>&1 &
  suite_pid=$!
  wait "$suite_pid"
  rc=$?
  if [ "$rc" -ge 124 ]; then
    kill -KILL -"$suite_pid" 2>/dev/null || true
    echo "  (suite exceeded its 600s budget and its process group was killed)" >>"$log"
  fi
  set -e
  cat "$log"
  echo "---- $suite exit=$rc ----"

  # Machine-generated accounting (round 7, #3). The previous aggregate was typed
  # by hand from grepped output, and a suite that CRASHED printed neither a
  # summary nor the word FAILED — so a hand-rolled "grep -c FAILED" reported zero
  # failures for a run containing a traceback. The total below is parsed from
  # each suite's own summary line, and a missing summary is itself an error.
  # `|| true` is load-bearing: with `set -e` active, a command substitution whose
  # command fails aborts the script. grep exits 1 when there is no summary line —
  # i.e. exactly when a suite CRASHED or SKIPPED — so without this the runner
  # silently stopped instead of reporting the very cases it exists to catch.
  # The `$` anchor here was wrong, and it hid real failures. Suites do not agree
  # on one summary format: some print
  #     32/33 passed  FAILURES: the verify command expects the real count
  # on a single line. That does not match an anchored pattern, so the runner
  # concluded NO SUMMARY and reported the suite as "crashed before reporting" —
  # the one classification that says nothing about what failed. A failing suite
  # and a suite killed mid-run became indistinguishable, and at least one real
  # assertion failure (verify_amber, in a batch, passing standalone) was written
  # off as a flake because of it. The counts are still anchored at the START of
  # the line so a mid-sentence "1/2 passed" cannot be mistaken for a summary.
  line="$(grep -E '^[0-9]+/[0-9]+ passed' "$log" | tail -1 || true)"

  # Exit 77 means the suite declined to run because a prerequisite was absent.
  # A SKIP contributes ZERO assertions and is reported separately: it must never
  # read as evidence that whatever it covers was actually tested.
  if [ "$rc" -eq 77 ]; then
    SKIPPED=$((SKIPPED + 1))
    reason="$(grep -m1 '^SUITE-SKIPPED:' "$log" | sed 's/^SUITE-SKIPPED: //' || true)"
    SUMMARY="$SUMMARY
  $suite: SKIPPED (0 assertions) — ${reason:-no reason given}"
    continue
  fi

  if [ "$rc" -ne 0 ] || [ -z "$line" ]; then
    BAD=$((BAD + 1)); RC=1
    if [ -z "$line" ]; then
      SUMMARY="$SUMMARY
  $suite: ERROR — exit $rc, NO assertion summary (crashed before reporting)"
    else
      SUMMARY="$SUMMARY
  $suite: FAIL — exit $rc, $line"
    fi
  else
    n="${line%%/*}"
    TOTAL=$((TOTAL + n))
    SUMMARY="$SUMMARY
  $suite: ok — $line"
  fi
done

echo

echo "================ AGGREGATE (machine-generated) ================"
echo "suites requested : $#"
printf '%s\n' "$SUMMARY" | sed '/^$/d'
echo "assertions passed: $TOTAL   (skipped suites contribute 0)"
echo "suites skipped   : $SKIPPED"
echo "suites with problems: $BAD"

# Write the run record. LAST-RUN.txt was previously assembled BY HAND from this
# script's stdout — which is why its tree hash could never be reproduced, and why
# three different assertion totals ended up in three different documents. It is
# generated here now, and harness/stamp_docs.py stamps the docs from it.
{
  printf '%s\n\n' "$RUN_HEADER"
  echo "================ AGGREGATE (machine-generated) ================"
  echo "suites requested : $#"
  printf '%s\n' "$SUMMARY" | sed '/^$/d'
  echo "assertions passed: $TOTAL   (skipped suites contribute 0)"
  echo "suites skipped   : $SKIPPED"
  echo "suites with problems: $BAD"
} > "$ROOT/harness/LAST-RUN.txt" 2>/dev/null || true

# Stamp the docs from the record we just wrote. verify_docs.py runs DURING the
# suite loop, so it can only ever validate the PREVIOUS run's record — and the
# runner then overwrote it, invalidating what had just passed. Stamping here
# closes that loop: after any run, the generated stanzas describe THAT run.
# The generated docs are excluded from the tree hash, so this cannot change the
# tree whose hash was recorded moments earlier.
python3 "$ROOT/harness/stamp_docs.py" >/dev/null 2>&1 || true
if [ "$BAD" -eq 0 ] && [ "$SKIPPED" -eq 0 ]; then
  echo "RESULT: PASS — every requested suite exited 0 and reported a summary."
elif [ "$BAD" -eq 0 ]; then
  echo "RESULT: PASS WITH SKIPS — $SKIPPED suite(s) did not run. Their coverage is"
  echo "        NOT demonstrated by this run; see the SKIPPED lines above."
else
  echo "RESULT: FAIL — $BAD suite(s) did not complete cleanly. Do NOT report this as green."
fi
rm -rf "$LOGDIR"
exit $RC
