#!/usr/bin/env bash
# Recreate the local test environment in a fresh container, the way CI does it,
# and leave a server up for suites that are driven directly.
#
#   harness/bootstrap.sh [VENV_DIR] [PORT]        defaults: /tmp/skribl-venv  5001
#
# It mirrors .github/workflows/harness.yml and the preamble of run_harness.sh:
#
#   1. a venv on the interpreter .python-version pins — verify_docs.py fails the
#      whole run on any other, because evidence produced on a different
#      interpreter from the deployed one describes nothing;
#   2. the hash-locked install from constraints.txt, then harness/requirements.txt
#      for the two test-only packages (Playwright and Pillow — read that file
#      before "fixing" either; Pillow's absence makes one suite report a tidy
#      near-pass while several of its assertions silently do not run);
#   3. the tables, created on a FRESH sqlite database exactly as run_harness.sh
#      creates them before every suite. The first draft of this script skipped
#      that step, passed verify_boot, and answered 500 to every post: a front
#      page that renders proves nothing about the database. The readiness probe
#      is therefore GET /api/skribls, which reads a table, not GET /;
#   4. the posting rate limit raised to run_harness.sh's default, so suites do
#      not throttle each other into 429s that read like validation failures;
#   5. the app booted in the background on PORT, proven to answer.
#
# It stops nothing and seals nothing. Stop the server BY PORT — `ss` is not
# installed in the remote container, and a `pgrep -f` pattern typed on the same
# command line matches its own shell:
#
#   fuser -k $PORT/tcp          or          kill $(lsof -ti :$PORT)
#
# Every suite reads SKRIBL_BASE (36 of them hardcoded 127.0.0.1:5001 until the
# efficiency pass), so a server on any port serves any suite, and several can run
# side by side: harness/run_parallel.py boots its own, one per worker.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
VENV=${1:-/tmp/skribl-venv}
PORT=${2:-5001}

# --- 1. the pinned interpreter ---------------------------------------------
PIN=$(tr -d '[:space:]' < .python-version)
PY=$(command -v "python$PIN" || true)
if [ -z "$PY" ] && python3 -c "import sys; raise SystemExit(0 if '%d.%d' % sys.version_info[:2] == '$PIN' else 1)" 2>/dev/null; then
  PY=$(command -v python3)
fi
[ -n "$PY" ] || { echo "python$PIN not found; the repo pins $PIN (.python-version) and the lock is built for it"; exit 2; }

# --- 2. the install ----------------------------------------------------------
# A venv this script makes carries a mark from before it exists until both
# installs have finished. A run cut off part way (a turn boundary reaps it, a
# pip fails) leaves the mark, and the next run installs again: the first draft
# skipped every venv that had a python3, so an interrupted install stayed
# interrupted and the next run booted nothing ("No module named 'flask'").
# A venv somebody else made (README-OFFLINE's, from the wheels, with no
# package network) has no mark and is used as it is.
PENDING="$VENV/.bootstrap-installing"
if [ ! -x "$VENV/bin/python3" ]; then
  mkdir -p "$VENV"
  : > "$PENDING"
  "$PY" -m venv "$VENV"
fi
if [ -e "$PENDING" ]; then
  "$VENV/bin/python3" -m pip install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r constraints.txt --require-hashes
  "$VENV/bin/pip" install --quiet -r harness/requirements.txt
  rm -f "$PENDING"
fi
echo "venv:     $("$VENV/bin/python3" --version) at $VENV"
echo "playwright: $("$VENV/bin/python3" -c 'from importlib.metadata import version; print(version("playwright"))' 2>/dev/null || echo 'not installed')"

# Chromium. A container that ships one has PLAYWRIGHT_BROWSERS_PATH pointing at
# it and downloads disabled; fetch only when nothing is there. The build number
# printed here has to be the one the installed playwright drives — a mismatch
# fails later with an executable-not-found error that reads like a missing
# browser (harness/requirements.txt explains the coupling). Fetching needs
# Playwright itself: an environment built from the offline wheels
# (harness/tools/wheelhouse.py) has none, and stopping here stopped the app
# booting too, which is the half that needs neither (v322).
BROWSERS="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
if [ -z "$(ls -d "$BROWSERS"/chromium* 2>/dev/null)" ] && "$VENV/bin/python3" -c "import playwright" 2>/dev/null; then
  "$VENV/bin/python3" -m playwright install chromium
fi
FOUND=$(ls -d "$BROWSERS"/chromium-* 2>/dev/null | xargs -rn1 basename | tr '\n' ' ' || true)
echo "chromium: ${FOUND:-none -- the app boots; the browser suites need Playwright and Chromium}"

# --- 3 + 4. a fresh database with tables, and the harness's rate limit -------
# The port is in the name: servers booted in the same second (run_parallel.py
# starts several at once) shared one file, and all but one failed with
# "database is locked".
DB="/tmp/skribl-fresh-$PORT-$(date +%s).db"
export DATABASE_URL="sqlite:///$DB"
export SKRIBL_RATE_MAX_POSTS="${SKRIBL_RATE_MAX_POSTS:-100000}"
"$VENV/bin/python3" -c "from app import app, db; app.app_context().push(); db.create_all()" \
  || { echo "could not create the tables in $DB"; exit 1; }

# --- 5. boot, and prove it ----------------------------------------------------
LOG="/tmp/skribl-server-$PORT.log"
nohup "$VENV/bin/python3" -m flask --app app run --port "$PORT" --no-reload > "$LOG" 2>&1 &
code=""
for _ in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/skribls" || true)
  [ "$code" = "200" ] && break
  sleep 0.5
done
[ "$code" = "200" ] || { echo "GET /api/skribls answered '$code' on :$PORT; see $LOG"; exit 1; }
echo "server:   http://127.0.0.1:$PORT/   db: $DB   log: $LOG"
echo "suites:   SKRIBL_BASE=http://127.0.0.1:$PORT $VENV/bin/python3 harness/verify_<x>.py"
echo "stop:     fuser -k $PORT/tcp"
