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

# Isolated database per run (round 4, #7). This previously reused the repository
# instance/ DB, so row-delta assertions and "did this run start clean?" could not
# be answered honestly. SKRIBL_KEEP_DB=1 restores the old behaviour.
if [ "${SKRIBL_KEEP_DB:-0}" != "1" ]; then
  HARNESS_TMP="$(mktemp -d)"
  HARNESS_DB="$HARNESS_TMP/harness.db"
  export DATABASE_URL="sqlite:///$HARNESS_DB"
  DB_RESET="yes (fresh $HARNESS_DB)"
else
  DB_RESET="no (reusing existing DATABASE_URL)"
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
{
  echo "================ RUN CONTEXT ================"
  echo "UTC timestamp           : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Host                    : $(uname -sm)"
  echo "Tree SHA-256            : $(cd "$ROOT" && { git ls-files -z 2>/dev/null || find . -type f -not -path './.git/*' -not -path './instance/*' -not -path './harness/LAST-RUN.txt' -not -path './SHA256SUMS' -not -path '*/__pycache__/*' -not -name '*.pyc' -print0; } | sort -z | xargs -0 sha256sum 2>/dev/null | sha256sum | cut -d" " -f1)"
  echo "Git commit              : $(cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "(not a git checkout)")"
  echo "SKRIBL_VERSION          : $(grep -m1 "^SKRIBL_VERSION" "$ROOT/app.py" | cut -d'"' -f2)"
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
}

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
LOGDIR="$(mktemp -d)"
TOTAL=0
BAD=0
SKIPPED=0
SUMMARY=""

for suite in "$@"; do
  echo "================ $suite ================"
  log="$LOGDIR/${suite%.py}.log"
  set +e
  timeout 600 python3 "$suite" >"$log" 2>&1
  rc=$?
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
  line="$(grep -E '^[0-9]+/[0-9]+ passed$' "$log" | tail -1 || true)"

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
