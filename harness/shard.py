"""Which suites one CI shard runs: `python3 harness/shard.py 2/6` prints them.

Main's full battery ran as one job of 90-odd minutes, so a red main took an
afternoon to show and a green one took the evening. The sqlite and postgres
jobs now run as six shards each, side by side on standard runners (free on a
public repository), and each shard runs `run_harness.sh` with the names this
prints.

BALANCED BY MEASURED TIME. A first split weighed each suite by the waiting
written in its source; its four shards took 30, 15, 24 and 25 minutes, because
a sleep inside a loop runs many times and a page load is not a sleep at all.
So the thirty suites that take a minute or more carry their seconds on CI,
and every other suite counts as SMALL: within a minute of a perfect split,
for a table a quarter the size of the battery. Suites go slowest first to the
shard with the least so far, and the split is deterministic, so a re-run of a
shard runs the same suites.

WHEN A SHARD RUNS LONG, re-measure: run_harness.sh ends every run with the
seconds each suite took (console only), so the last lines of each shard's log
are the new table. A new suite counts as SMALL until it is measured.

PINNED: verify_postgres.py is always in shard 1, where the postgres job's
migration check and attestation run, and every shard together runs every
suite on disk exactly once -- `--check N` asserts that, and that every
measured name is still a suite.
"""
import re
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
PINNED_FIRST = ("verify_postgres.py",)

# Seconds on CI (Oct 11, run 38190196594: the slower of the sqlite and
# postgresql shards), to the nearest ten.
MEASURED = {
    "verify_a11y.py": 360, "verify_a11ypages.py": 210, "verify_amber.py": 280, "verify_audiosession.py": 70,
    "verify_audiostate.py": 80, "verify_clouddrafts.py": 120, "verify_compose.py": 120,
    "verify_cssplit.py": 90, "verify_drafts.py": 100, "verify_flipmeta.py": 90,
    "verify_flipspeed.py": 60, "verify_galib.py": 100, "verify_gallery.py": 130,
    "verify_helpclaims.py": 90, "verify_helpdemos.py": 120, "verify_inline.py": 130,
    "verify_jsstrip.py": 60, "verify_layout.py": 150, "verify_library.py": 160,
    "verify_onepill.py": 340, "verify_parity.py": 430, "verify_posted.py": 130,
    "verify_replayspeed.py": 70, "verify_padrepeat.py": 150, "verify_review.py": 70, "verify_sheetswipe.py": 170,
    "verify_smudgeblur.py": 60, "verify_tappause.py": 100, "verify_hello.py": 70, "verify_recolor.py": 200, "verify_drawtiles.py": 200, "verify_musicdoors.py": 260, "verify_musicbeat.py": 450, "verify_musicclick.py": 126, "verify_musictall.py": 140, "verify_musiclane.py": 110, "verify_musicthree.py": 200, "verify_musictempo.py": 300, "verify_musictimeline.py": 400, "verify_musicears.py": 150, "verify_bigcanvas.py": 200, "verify_drawfull.py": 60, "verify_soundfade.py": 60, "verify_flipbeat.py": 120, "verify_recolorplay.py": 150, "verify_menu.py": 120, "verify_contrast.py": 900, "verify_learncard.py": 60, "verify_ask.py": 70, "verify_book.py": 60, "verify_glide.py": 40, "verify_theme.py": 90,
    "verify_tools.py": 180, "verify_tray.py": 60, "verify_ux.py": 420,
}
SMALL = 15          # every other suite: the rest averaged 14 seconds


def weight(name):
    return MEASURED.get(name, SMALL)


def shards(n):
    suites = sorted(p.name for p in HARNESS.glob("verify_*.py"))
    out = [[] for _ in range(n)]
    load = [0] * n
    for s in suites:
        if s in PINNED_FIRST:
            out[0].append(s)
            load[0] += weight(s)
    rest = sorted((s for s in suites if s not in PINNED_FIRST), key=lambda s: (-weight(s), s))
    for s in rest:
        i = min(range(n), key=lambda k: (load[k], k))
        out[i].append(s)
        load[i] += weight(s)
    return [sorted(o) for o in out]


def main(argv):
    if len(argv) == 3 and argv[1] == "--check":
        n = int(argv[2])
        got = [s for part in shards(n) for s in part]
        disk = sorted(p.name for p in HARNESS.glob("verify_*.py"))
        gone = sorted(set(MEASURED) - set(disk))
        ok = sorted(got) == disk and len(got) == len(set(got)) and not gone
        print(f"{n} shards cover {len(got)} of {len(disk)} suites, each once: {ok}"
              + (f"; measured but no longer on disk: {', '.join(gone)}" if gone else ""))
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
