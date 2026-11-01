"""Which suites one CI shard runs: `python3 harness/shard.py 2/6` prints them.

Main's full battery ran as one job of 90-odd minutes, so a red main took an
afternoon to show and a green one took the evening. The sqlite and postgres
jobs now run as six shards each, side by side on standard runners (free on a
public repository), and each shard runs `run_harness.sh` with the names this
prints.

BALANCED BY MEASURED TIME. A first split weighed each suite by the waiting
written in its source; its four shards took 30, 15, 24 and 25 minutes, because
a sleep inside a loop runs many times and a page load is not a sleep at all.
So every suite that takes half a minute or more carries its seconds on CI
(87 of 167 on Oct 29), and every other suite counts as SMALL, their average.
The table from Oct 11 had drifted: one shard took 53 to 55 of its 60 minutes
while the others took 31 to 39, because the contrast census had grown to
1,406 s (sqlite) and 1,461 s (postgresql) against its 900, and 35 suites
counted as SMALL took 28 to 180 s.
Re-weighed from that run, the split puts each shard at 39 to 41 minutes.
Suites go slowest first to the shard with the least so far, and the split is
deterministic, so a re-run of a shard runs the same suites.

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

# Seconds on CI (Oct 29, run 40809932689 on 92bc060: the slower of the sqlite
# and postgresql shards), to the nearest ten.
MEASURED = {
    "verify_a11y.py": 380, "verify_a11ypages.py": 200, "verify_amber.py": 260, "verify_ask.py": 40,
    "verify_audio.py": 50, "verify_audiosession.py": 100, "verify_audiostate.py": 90,
    "verify_bigcanvas.py": 160, "verify_book.py": 130, "verify_cardfade.py": 30,
    "verify_clouddrafts.py": 150, "verify_compose.py": 110, "verify_contrast.py": 1460,
    "verify_cssplit.py": 100, "verify_dots.py": 50, "verify_drafts.py": 230,
    "verify_drawfull.py": 70, "verify_drawtiles.py": 100, "verify_fix.py": 60,
    "verify_flipbeat.py": 180, "verify_flipedges.py": 70, "verify_flipmeta.py": 100,
    "verify_flipspeed.py": 60, "verify_fullfade.py": 180, "verify_fullsmart.py": 80,
    "verify_galib.py": 210, "verify_gallery.py": 160, "verify_hello.py": 110, "verify_help.py": 40,
    "verify_helpclaims.py": 130, "verify_helpdemos.py": 150, "verify_hold.py": 70,
    "verify_identity.py": 60, "verify_inline.py": 190, "verify_jsstrip.py": 100,
    "verify_layout.py": 270, "verify_learncard.py": 110, "verify_library.py": 180,
    "verify_liquify.py": 40, "verify_loopui.py": 30, "verify_menu.py": 140, "verify_motion.py": 40,
    "verify_move.py": 30, "verify_music.py": 170, "verify_musicbeat.py": 340,
    "verify_musicclick.py": 140, "verify_musicdoors.py": 530, "verify_musicears.py": 160,
    "verify_musiclane.py": 100, "verify_musicsnap.py": 260, "verify_musictall.py": 140,
    "verify_musictempo.py": 210, "verify_musicthree.py": 190, "verify_musictimeline.py": 570,
    "verify_musicundo.py": 300, "verify_offline.py": 40, "verify_onefull.py": 80,
    "verify_onepill.py": 380, "verify_padedges.py": 60, "verify_padrepeat.py": 170,
    "verify_pages.py": 40, "verify_parity.py": 520, "verify_pillfit.py": 40,
    "verify_player_isolation.py": 60, "verify_pointerpad.py": 50, "verify_posted.py": 190,
    "verify_recolor.py": 110, "verify_recolorplay.py": 40, "verify_replayspeed.py": 210,
    "verify_review.py": 80, "verify_select.py": 40, "verify_sheetfit.py": 40,
    "verify_sheetswipe.py": 200, "verify_sizeclass.py": 30, "verify_smudgeblur.py": 60,
    "verify_soundfade.py": 60, "verify_stamps.py": 50, "verify_tappause.py": 120,
    "verify_theme.py": 160, "verify_tips.py": 70, "verify_tools.py": 220, "verify_tray.py": 70,
    "verify_ux.py": 470, "verify_videoexport.py": 90, "verify_viewedges.py": 30,
    "verify_visual.py": 30, "verify_watchfull.py": 110,
    # Not yet measured on CI: the local run, Nov 1, to the nearest ten. CI's
    # own figure replaces it at the next re-measure.
    "verify_letters.py": 110,
}
SMALL = 11          # every other suite: the rest averaged 11 seconds


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
