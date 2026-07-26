#!/usr/bin/env bash
# Start Flask, run the named harness suite(s), tear down. Processes don't survive
# between tool calls in this sandbox, so server + test must share one invocation.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

# The posting suite needs the table to exist. A fresh unzip has no instance/ DB,
# so create it up front — idempotent, safe to repeat.
python3 -c "from app import app, db; app.app_context().push(); db.create_all()" || exit 1

# The app rate-limits POST /api/skribls to 20/hour/IP. Several suites post, and
# together they sit just under that — so adding a few posting assertions anywhere
# starts producing mystery 429s instead of the real result. Raise the cap for
# harness runs (still overridable) so suites are deterministic and independent.
# Consequence: the rate limiter itself is NOT under test here.
export SKRIBL_RATE_MAX_POSTS="${SKRIBL_RATE_MAX_POSTS:-100000}"

python3 -m flask --app app run --port 5001 --no-reload > /tmp/flask.log 2>&1 &
FLASK_PID=$!
trap 'kill $FLASK_PID 2>/dev/null' EXIT

for _ in $(seq 1 40); do
  curl -sf -o /dev/null http://127.0.0.1:5001/ && break
  sleep 0.5
done

RC=0
cd "$ROOT/harness" || exit 1
for suite in "$@"; do
  echo "================ $suite ================"
  timeout 600 python3 "$suite"
  rc=$?
  [ $rc -ne 0 ] && RC=$rc
  echo "---- $suite exit=$rc ----"
done
exit $RC
