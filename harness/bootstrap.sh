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
# About a third of the suites ignore SKRIBL_BASE and hardcode 127.0.0.1:5001
# (`grep -L SKRIBL_BASE harness/verify_*.py` lists every suite that does not read
# it), so the default port is the one to keep for a shared server.
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
if [ ! -x "$VENV/bin/python3" ]; then
  "$PY" -m venv "$VENV"
  "$VENV/bin/python3" -m pip install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r constraints.txt --require-hashes
  "$VENV/bin/pip" install --quiet -r harness/requirements.txt
fi
echo "venv:     $("$VENV/bin/python3" --version) at $VENV"
echo "playwright: $("$VENV/bin/python3" -c 'from importlib.metadata import version; print(version("playwright"))' 2>/dev/null || echo 'not installed')"

# Chromium. A container that ships one has PLAYWRIGHT_BROWSERS_PATH pointing at
# it and downloads disabled; fetch only when nothing is there. The build number
# printed here has to be the one the installed playwright drives — a mismatch
# fails later with an executable-not-found error that reads like a missing
# browser (harness/requirements.txt explains the coupling).
BROWSERS="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
if [ -z "$(ls -d "$BROWSERS"/chromium* 2>/dev/null)" ]; then
  "$VENV/bin/python3" -m playwright install chromium
fi
echo "chromium: $(ls -d "$BROWSERS"/chromium-* 2>/dev/null | xargs -n1 basename | tr '\n' ' ')"

# --- 3 + 4. a fresh database with tables, and the harness's rate limit -------
DB="/tmp/skribl-fresh-$(date +%s).db"
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
[ "$PORT" = "5001" ] || echo "note: suites that hardcode 127.0.0.1:5001 will not find this server; use the default port for them"
