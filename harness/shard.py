"""Which suites one CI shard runs: `python3 harness/shard.py 2/4` prints them.

Main's full battery ran as one job of 90-odd minutes, so a red main took an
afternoon to show and a green one took the evening. The sqlite and postgres
jobs now run as four shards each, side by side on standard runners (free on a
public repository), and each shard runs `run_harness.sh` with the names this
prints.

BALANCED BY WHAT A SUITE COSTS, without a table to keep: every suite's weight
is the fixed waiting written in it (its `wait_for_timeout` and `time.sleep`
calls) plus a little for its size, read from the source on every run, so a
suite that grows is weighed as it is now. Suites go heaviest first to the
lightest shard. The split is deterministic, so a re-run of a shard runs the
same suites.

PINNED: verify_postgres.py is always in shard 1, where the postgres job's
migration check and attestation run, and every shard together runs every
suite on disk exactly once -- `--check N` asserts that.
"""
import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
PINNED_FIRST = ("verify_postgres.py",)


def weight(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    waits = sum(int(n) for n in re.findall(r"wait_for_timeout\(\s*(\d+)\s*\)", text))
    sleeps = sum(float(n) * 1000 for n in re.findall(r"time\.sleep\(\s*([\d.]+)\s*\)", text))
    return waits + sleeps + len(text) / 20          # ms; ~1s per 20 KB of source


def shards(n):
    suites = sorted(HARNESS.glob("verify_*.py"))
    out = [[] for _ in range(n)]
    load = [0.0] * n
    for s in suites:
        if s.name in PINNED_FIRST:
            out[0].append(s.name)
            load[0] += weight(s)
    rest = sorted((s for s in suites if s.name not in PINNED_FIRST),
                  key=lambda s: (-weight(s), s.name))
    for s in rest:
        i = min(range(n), key=lambda k: (load[k], k))
        out[i].append(s.name)
        load[i] += weight(s)
    return [sorted(o) for o in out]


def main(argv):
    if len(argv) == 3 and argv[1] == "--check":
        n = int(argv[2])
        got = [s for part in shards(n) for s in part]
        disk = sorted(p.name for p in HARNESS.glob("verify_*.py"))
        ok = sorted(got) == disk and len(got) == len(set(got))
        print(f"{n} shards cover {len(got)} of {len(disk)} suites, each once: {ok}")
        return 0 if ok else 1
    m = re.fullmatch(r"(\d+)/(\d+)", argv[1] if len(argv) > 1 else "")
    if not m or not 1 <= int(m.group(1)) <= int(m.group(2)):
        print("usage: shard.py I/N   (or --check N)", file=sys.stderr)
        return 2
    i, n = int(m.group(1)), int(m.group(2))
    print(" ".join(shards(n)[i - 1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
