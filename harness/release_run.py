#!/usr/bin/env python3
"""Aggregate release evidence across every suite, on one frozen tree.

WHY THIS EXISTS. `harness/LAST-RUN.txt` records ONE invocation. A full
single-invocation run hangs, so suites are named in batches — which means the
last batch overwrites the record of every earlier one, and `stamp_docs.py`
stamps whichever invocation happened last. The archive could therefore say
"421 assertions, 8 suites, all green" while saying nothing at all about the
29 suites that were also run and also passed. An external review read that
statement exactly as written and concluded, correctly, that it was evidence
for the latest feature batch and not for the release.

WHAT IT GUARANTEES. The tree hash is computed BEFORE the first batch and
re-verified before every subsequent one, so a source edit between batches is
caught rather than averaged away. Every suite in harness/ must appear in
exactly one batch or the run fails: a suite cannot be quietly dropped by being
left out of the list. Skips are counted separately from passes, because a skip
is not coverage.

    python3 harness/release_run.py                 # every suite, default batches
    python3 harness/release_run.py --dry-run       # check batch coverage only

Writes harness/RELEASE.md — the one document other docs should point at for
volatile release facts, so they stop being hand-typed.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"

# Excluded from the tree hash for the same reason run_harness.sh excludes them:
# they are written AFTER a run, so including them means recording a result
# changes the tree whose hash was just recorded. Kept in step by verify_docs.
GENERATED = {"harness/LAST-RUN.txt", "SHA256SUMS", "README.md",
             "harness/README.md", "docs/HANDOFF.md", "START-HERE.md",
             "harness/RELEASE.md",
             # v211: verify_postgres writes gunicorn logs beside itself; they
             # are run artefacts, not tree, and must not move the frozen hash
             # between batches (the F3 host log did exactly that once).
             "harness/.pg_gunicorn.log", "harness/.pg_f3_gunicorn.log"}

# Batches exist because a bare run hangs. Grouped so a browser batch stays
# small enough to finish, and so the server/security suites — which do not
# drive Chromium — are not held hostage to a browser batch timing out.
BATCHES = [
    # v210: verify_ux is 284 assertions and no longer finishes alongside three
    # other suites inside one sandbox invocation, so the checkpoint after
    # batch 1 was never written and every re-invoke restarted from the top.
    # It gets a batch of its own; the three it shared with move to batch 2.
    ["verify_ux.py"],
    # verify_tools.py holds the v213 tool work, split out of verify_ux when that
    # suite outgrew a single invocation. Its own batch for the same reason.
    ["verify_tools.py"],
    ["verify_move.py", "verify_pages.py"],
    # verify_hold times a real playback loop and asserts frame-pacing evenness,
    # so — like verify_player_isolation below — it must not share a batch with a
    # browser competing for the same CPU, or a contention spike reads as a
    # pacing failure. (Its own flake in the v264 release run.)
    ["verify_hold.py"],
    ["verify_review.py", "verify_help.py", "verify_tips.py"],
    ["verify_exportui.py", "verify_exopts.py", "verify_dots.py", "verify_fix.py"],
    ["verify_amber.py", "verify_posted.py", "verify_report.py", "verify_canvas.py"],
    ["verify_padcanvas.py", "verify_pressure.py", "verify_lib.py", "verify_docs.py",
     "verify_integration.py", "verify_scrub.py"],
    # Posts through the editor and then loads the share link, so it needs the
    # whole authoring path working; it also holds the ratchets on the player
    # split. Alone in a batch because it is slow and because a browser it shares
    # a batch with is a browser competing for the same CPU during a timing-
    # sensitive replay.
    ["verify_player_isolation.py"],
    # THE IN-POST PLAYER'S FOUR SUITES, spread rather than stacked. Each of them
    # records a real drawing in Pad and posts it — verify_inline authors three,
    # one carrying an audio loop — and then drives a browser through a replay
    # whose timing it asserts on. Sharing a batch means two browsers competing
    # for the same CPU during exactly that measurement, which is the flake
    # verify_hold and verify_player_isolation already have their own batches to
    # avoid. verify_sharecard is the cheap one (two posts, then bytes off the
    # card route) so it rides with the photo suite.
    ["verify_inline.py"],
    ["verify_compose.py"],
    # Server-side creation and server-side DELETION, the two host-facing Python
    # entry points. No browser and no harness server between them: each builds
    # its own Flask apps over its own temporary SQLite files, so neither counts
    # somebody else's posts and neither can be counted. They keep this batch to
    # themselves for that reason rather than for isolation from each other.
    #
    # verify_deletion is placed here rather than beside verify_deletion_foundation
    # despite the name: that suite sweeps orphans FOR REAL against a live media
    # root, and sharing a batch with it is what the note beside it warns off.
    # This one never touches a store.
    ["verify_createpost.py", "verify_deletion.py"],
    # The worked example, driven in a browser against its OWN server on its own
    # port and its own database. It shares nothing with the harness instance,
    # so it could batch with anything — but it is a browser suite recording a
    # real drawing, which is the kind that wants a quiet CPU.
    ["verify_example.py"],
    # Audio measured on the graph through an analyser tap, so it wants the same
    # quiet CPU verify_player_isolation and verify_hold get their own batch for.
    ["verify_audiosession.py"],
    ["verify_library.py"],
    ["verify_player_photo.py", "verify_sharecard.py"],
    ["verify_visual.py"],
    ["verify_flipmotion.py"],
    # v263: the playback bitmap cache. Browser-heavy (it plays loops on both
    # surfaces and times them), so it gets a batch of its own.
    ["verify_framecache.py"],
    ["verify_parity.py"],
    ["verify_audio.py", "verify_seam.py", "verify_loopcap.py", "verify_audiostate.py"],
    ["verify_gifenc.py", "verify_muxer.py", "verify_mp4.py", "verify_flipmeta.py"],
    ["verify_feed.py", "verify_media.py", "verify_storage.py", "verify_privacy.py",
     # Runs LAST in its batch and brings its own local-media server, on its own
     # port with an isolated media root, because it calls sweep_orphans with
     # dry_run=False. Pointed at a shared root it deletes other suites' media —
     # observed doing exactly that. It must never share a store with verify_media
     # or verify_storage, which is also why it cannot just take the ambient
     # backend: verify_storage asserts the default instance stores media INLINE.
     "verify_deletion_foundation.py"],
    ["verify_csp.py", "verify_csrf.py", "verify_race.py", "verify_prefix.py",
     "verify_delivery.py", "verify_surfaces.py"],
    ["verify_version.py", "verify_migrations.py", "verify_postgres.py"],
    # v199 suites. They were on disk and in no batch, which is the one thing
    # the coverage check refuses to let a release paper over — so the release
    # could not start at all until they were placed. Each brings its own server
    # on its own port with its own media root and database, so placement here is
    # about wall clock and CPU contention, not isolation.
    #
    # externalised and backfill each boot TWO instances and post through them.
    # They are kept out of verify_deletion_foundation's batch because that suite
    # sweeps orphans for real.
    ["verify_externalised.py", "verify_backfill.py", "verify_mediaauthz.py"],
    # Alone: eleven scenes, screenshotted against two stylesheets.
    ["verify_cssplit.py"],
    ["verify_keys.py", "verify_strokegroups.py", "verify_sheetfit.py",
     "verify_apiedges.py", "verify_txcontract.py", "verify_assetcache.py",
     "verify_mimeparity.py"],
    ["verify_jsstrip.py"],
    ["verify_s3.py"],
    # v219. Same story as the v199 suites above, and the coverage check caught it
    # the same way: verify_layout.py was written during the v219 build, the build
    # was never run, and so nothing ever noticed it belonged to no batch. The
    # first release run after it was added refused to start. That refusal is the
    # feature — a suite on disk and in no batch is a suite whose absence would
    # have read as an absence of failures.
    #
    # Alone, and deliberately: it measures rendered geometry at eight viewport
    # widths across both editors, and a browser sharing its batch is a browser
    # competing for CPU while it takes those measurements.
    ["verify_layout.py"],
    # Browser suite with deliberate multi-second settles (IndexedDB puts, a
    # ~7 MB decode) — like verify_layout it runs alone rather than compete
    # for CPU during timing-sensitive waits. Added v222 with the durability
    # work; the refusal above is what flagged it into this list.
    ["verify_drafts.py"],
    # v223. TEN suites were on disk and in no batch — verify_boot, flipdraft,
    # fuzz, liquify, pillfit, select, sharedrules, theme, tray, tween — so
    # RELEASE.md could not be regenerated at all and stayed frozen describing a
    # 64-suite tree at v222 while 74 suites were passing. Every other doc points
    # at RELEASE.md for volatile facts, so the authority was the stale one.
    #
    # That is the third time this has happened (v199, v219, now v223) and the
    # refusal worked every time; what fails is remembering to place a suite when
    # writing it. Adding a suite means adding a line here, and nothing but this
    # comment says so.
    #
    # Alone: it renders a 6x5 grid of in-betweens — thirty full canvas reads —
    # and shares nothing well while doing it.
    ["verify_tween.py"],
    # Alone for the same reason: liquify subdivides strokes and diffs the canvas
    # pixel by pixel.
    ["verify_liquify.py"],
    # sharedrules posts and then opens the PLAYER, so it needs the whole
    # authoring path; theme screenshots both stylesheets. Grouped with the two
    # small structural suites rather than the timing-sensitive ones.
    ["verify_sharedrules.py", "verify_theme.py", "verify_boot.py"],
  # v268: the shared name tab (Pad + Flip). Browser-driven but light — it drives
  # both editor headers and reads window.SkriblName, no pixel measurement.
  ["verify_nametab.py"],
    ["verify_tray.py", "verify_select.py", "verify_pillfit.py",
     "verify_flipdraft.py", "verify_fuzz.py"],
    # v224. Media resource limits (outside review #5). It drives a browser only
    # to BUILD fixtures — real PNG/JPEG/WebP out of Chromium's encoders and a
    # real GIF out of vendored gifenc — then does everything else against the
    # pure functions and the API, so it is fast and shares CPU well. It posts
    # four rejected payloads and one accepted one to the shared server, which is
    # why it stays away from verify_deletion_foundation's batch: that suite
    # sweeps orphans for real.
    ["verify_medialimits.py"],
    # v224. The orphan-sweep job (outside review #6). Entirely in-process
    # against a temp SQLite file and a temp media root — no server, no browser
    # — and it drives `python -m skribl.sweep` as a real subprocess so the exit
    # codes asserted are the ones cron would see. Isolated by construction, so
    # it shares a batch with the other cheap v224 suite.
    ["verify_sweepjob.py"],
    # v224. The four host seams from the outside review (#3 feed filter, #4
    # csrf=False, #7 visibility values, #8 author resolver). In-process
    # throwaway apps over one temp SQLite file, like verify_privacy — no
    # server, no browser, so it costs almost nothing to run.
    ["verify_hostseams.py"],
    # v224. The three configuration defects from the review's low list: the
    # title/caption limit stated in three disagreeing places, production
    # detection that only knew Render, and the per-process rate limiter behind
    # multiple workers. It boots app.py in eleven scrubbed subprocesses, which
    # is cheap, and posts a handful of payloads to the shared server.
    ["verify_hostconfig.py"],
    # v225. The translucent-stroke pixel regression (outside review R2). Draws
    # one Air-brush stroke, repaints it three ways and compares ALPHA profiles,
    # so it needs a browser and a quiet CPU: a repaint measured while another
    # Chromium competes is still correct, but the reason it is alone here is
    # that it reads the full canvas four times.
    ["verify_beading.py"],
    # v226. Page spans on Flip's strip. Browser-driven but cheap — it drives
    # the strip and reads array order rather than pixels — so it shares a batch
    # with nothing only because the two suites either side of it are already
    # alone for timing reasons.
    ["verify_pagespan.py"],
    # v226. The size class. It resizes the viewport repeatedly and asserts a
    # computed style on both sides of one pixel, so it wants a batch that is not
    # also running a second Chromium competing for the frame.
    ["verify_sizeclass.py"],
    # v227. Stage 4: the compact surface drops the page bar for a per-tile menu.
    # It resizes across the boundary and drives a keyboard through a popover, so
    # it wants the same quiet CPU verify_sizeclass does.
    ["verify_compactops.py"],
    # v230. Fill is its own batch for the same reason the others are: it drives
    # a real canvas and reads pixels back, which does not share a page well.
    ["verify_fill.py"],
    ["verify_input.py"],
    ["verify_smudgeblur.py"],
    # v238. Stamps drive a real canvas twice over — placements onto the pad and
    # a thumbnail render per shelf slot — so they get the same solitary batch
    # the other canvas suites do.
    ["verify_stamps.py"],
    # v239. Rasterises every tray glyph and measures its ink box, so it wants a
    # page to itself like the other canvas suites.
    ["verify_icons.py"],
]


#: A skip that some OTHER lane proves. Keyed by suite, valued by the CI job in
#: .github/workflows/harness.yml that runs it in an environment where it cannot
#: skip. Adding a suite here is a claim that the job exists and gates on it —
#: verify_docs.py checks the job name is really in the workflow.
SKIP_COVERAGE = {
    "verify_mp4.py": "mp4",
    "verify_postgres.py": "postgres",
}


def tree_files():
    out = subprocess.run(["find", ".", "-type", "f"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split("\n")
    keep = []
    for line in out:
        if not line:
            continue
        rel = line[2:] if line.startswith("./") else line
        if rel.startswith(".git/") or rel.startswith("instance/"):
            continue
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        if rel in GENERATED:
            continue
        keep.append(rel)
    return sorted(keep)


def tree_hash():
    inner = "".join(
        f"{hashlib.sha256((ROOT / f).read_bytes()).hexdigest()}  {f}\n"
        for f in tree_files())
    return hashlib.sha256(inner.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    # RESUME. A full aggregate takes ~25 minutes of wall clock. Some execution
    # environments — including the sandbox this is usually run in — cap a single
    # invocation well below that and do not let a background process survive
    # between invocations, so the run is killed part-way and no evidence is
    # produced at all. The tempting workaround is to run batches by hand and add
    # the numbers up, which is precisely the hand-typed total this whole file
    # exists to abolish.
    #
    # Instead the run checkpoints after every batch and can be re-invoked until
    # it completes. The guarantees are unchanged, and the tree-hash one is
    # actually STRONGER: the frozen hash is stored in the checkpoint and
    # re-verified on every resume, so an edit made BETWEEN invocations aborts
    # the run exactly as an edit between batches does.
    #
    # The state file lives outside the tree by default. Putting it inside would
    # mean a file written during the run changing the hash of the tree the run
    # is about to describe — the defect GENERATED exists to prevent.
    ap.add_argument("--state", default="/tmp/skribl-release-state.json",
                    help="checkpoint path (outside the tree by design)")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="seconds of wall clock before checkpointing and exiting "
                         "with 75 (incomplete); 0 means run to completion")
    ap.add_argument("--restart", action="store_true",
                    help="discard any existing checkpoint and start over")
    args = ap.parse_args()

    on_disk = sorted(p.name for p in HARNESS.glob("verify_*.py"))
    listed = [s for b in BATCHES for s in b]
    missing = [s for s in on_disk if s not in listed]
    unknown = [s for s in listed if s not in on_disk]
    dupes = sorted({s for s in listed if listed.count(s) > 1})
    if missing or unknown or dupes:
        print("BATCH COVERAGE IS WRONG — a release cannot proceed:")
        if missing:
            print("  in harness/ but in no batch :", ", ".join(missing))
        if unknown:
            print("  batched but not on disk     :", ", ".join(unknown))
        if dupes:
            print("  listed more than once       :", ", ".join(dupes))
        return 1
    print(f"batch coverage: all {len(on_disk)} suites appear exactly once")
    if args.dry_run:
        return 0

    frozen = tree_hash()
    state_path = pathlib.Path(args.state)
    rows, skipped, total, failed = [], [], 0, []
    diagnostics = []
    done = 0

    if args.restart and state_path.exists():
        state_path.unlink()
        print("checkpoint discarded (--restart)")

    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("frozen") != frozen:
            # Refuse rather than silently starting over: a resumed run that
            # quietly restarts on a different tree would report batches from
            # two trees under one hash, which is the exact claim this file
            # exists to make impossible.
            print(f"ABORT: the tree changed since the checkpoint was written "
                  f"({tree_hash()[:12]} != {state['frozen'][:12]}).\n"
                  f"       Release evidence must describe ONE tree. Re-run with "
                  f"--restart to begin a fresh run on the current tree.")
            return 1
        if state.get("batches") != [list(b) for b in BATCHES]:
            print("ABORT: the batch layout changed since the checkpoint was "
                  "written. Re-run with --restart.")
            return 1
        rows = [tuple(r) for r in state["rows"]]
        skipped = state["skipped"]
        total = state["total"]
        failed = state["failed"]
        diagnostics = state["diagnostics"]
        done = state["done"]
        print(f"resuming: {done}/{len(BATCHES)} batches already recorded "
              f"on tree {frozen[:12]}")

    print(f"frozen tree    : {frozen}\n")
    started = time.monotonic()

    def save(done_count):
        state_path.write_text(json.dumps({
            "frozen": frozen,
            "batches": [list(b) for b in BATCHES],
            "rows": [list(r) for r in rows],
            "skipped": skipped, "total": total, "failed": failed,
            "diagnostics": diagnostics, "done": done_count,
        }))

    def tail(text, lines=25, chars=2500):
        # Bounded on purpose: a full Chromium batch log is thousands of lines,
        # and an unbounded dump in a release document is not a diagnostic, it is
        # a place diagnostics go to hide. The end is where the failure is.
        t = "\n".join(text.strip().splitlines()[-lines:])
        return t[-chars:] if len(t) > chars else t

    for n, batch in enumerate(BATCHES, 1):
        if n <= done:
            continue
        if args.budget and time.monotonic() - started > args.budget:
            save(n - 1)
            print(f"\nBUDGET REACHED — checkpointed after batch {n - 1}/"
                  f"{len(BATCHES)}. Re-invoke to continue; the frozen tree is "
                  f"re-verified on resume.")
            return 75
        now = tree_hash()
        if now != frozen:
            print(f"ABORT: the tree changed before batch {n} ({now[:12]} != "
                  f"{frozen[:12]}). Release evidence must describe ONE tree.")
            return 1
        print(f"--- batch {n}/{len(BATCHES)}: {' '.join(batch)}")
        r = subprocess.run([str(HARNESS / "run_harness.sh")] + batch,
                           cwd=ROOT, capture_output=True, text=True)
        out = r.stdout
        reported_here = set()
        # `(\w+) — ` used to be the status pattern, which silently failed to
        # match run_harness.sh's own skip line:
        #   verify_mp4.py: SKIPPED (0 assertions) — no H.264 profile supported
        # The parenthetical breaks \w+, so a DECLARED skip with a stated reason
        # was recorded as "reported nothing" — turning the one thing the runner
        # explained into the one thing the report could not.
        for m in re.finditer(r"^  (verify_\S+): (.+?) — (.*)$", out, re.M):
            name, status, detail = m.group(1), m.group(2).strip(), m.group(3).strip()
            got = re.match(r"(\d+)/(\d+) passed", detail)
            if status.upper().startswith("SKIP"):
                skipped.append(name)
                rows.append((name, "skip", detail))
            elif status == "ok" and got:
                total += int(got.group(1))
                rows.append((name, "pass", detail))
            else:
                failed.append(name)
                rows.append((name, "FAIL", detail))
            reported_here.add(name)
            print(f"    {name:26} {status:6} {detail}")

        # A batch that dies before run_harness.sh emits its aggregate stanza
        # produces no rows at all, and the report would then say only that
        # these suites "reported nothing" — true, and useless. The exit code
        # and the tail of the child's output are what distinguish a missing
        # dependency from a hung browser from a genuine assertion failure.
        silent = [s for s in batch if s not in reported_here]
        if r.returncode != 0 or silent:
            diagnostics.append({
                "batch": n, "suites": batch, "silent": silent,
                "returncode": r.returncode,
                "stdout": tail(out), "stderr": tail(r.stderr),
            })
            print(f"    !! batch {n} exited {r.returncode}"
                  + (f"; no output from: {', '.join(silent)}" if silent else ""))
            if r.stderr.strip():
                print("    !! stderr tail: "
                      + r.stderr.strip().splitlines()[-1][:160])
        save(n)

    seen = {r[0] for r in rows}
    never = [s for s in on_disk if s not in seen]
    ok = not failed and not never

    lines = [
        "# Release evidence", "",
        "Generated by `harness/release_run.py`. Every fact here is computed, "
        "not typed — see the note at the top of that file for why.", "",
        f"    result           {'PASS' if ok else 'FAIL'}",
        f"    tree hash        {frozen}",
        f"    SKRIBL_VERSION   " + re.search(
            r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
            (ROOT / "skribl" / "core.py").read_text()).group(1),
        f"    python           {sys.version.split()[0]}",
        f"    suites on disk   {len(on_disk)}",
        f"    suites reported  {len(seen)}",
        f"    assertions       {total}",
        f"    skipped          {len(skipped)}" +
        (f"  ({', '.join(skipped)})" if skipped else ""),
        f"    generated        {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        "",
        "A skip is not coverage. Suites that skip are listed above by name so "
        "that an absence of failures is never read as an absence of gaps.", "",
        "The frozen tree hash above deliberately EXCLUDES the docs that carry "
        "generated counts (README.md, START-HERE.md, docs/HANDOFF.md, "
        "harness/README.md), this file, harness/LAST-RUN.txt and SHA256SUMS: "
        "each is written AFTER the run, so a hash covering them would describe "
        "a tree that no longer exists once they are stamped. Their final bytes "
        "are covered instead by `SHA256SUMS`, which is regenerated last, and "
        "`verify_docs.py` fails if any stamped count disagrees with this run. "
        "(Outside review of v263, M6.)", "",
    ]
    # Where a skip IS covered, say where — generated from the table below, not
    # typed into prose. The v224 outside review filed the MP4 skip as a finding
    # and recommended a CI lane with real H.264, which .github/workflows has run
    # since v103 and which FAILS if the suite merely skips. The lane shipped
    # inside the reviewed archive; nothing in the evidence pointed at it, so a
    # reader of this file had no way to know the gap was already closed. An
    # uncovered skip still says so, loudly.
    for name in skipped:
        lane = SKIP_COVERAGE.get(name)
        lines += [f"  * `{name}` — " + (
            f"covered by the `{lane}` CI job in .github/workflows/harness.yml, "
            "which installs the environment this one lacks and fails if the "
            "suite skips there too."
            if lane else
            "NOT covered anywhere. This is a real gap in the release.")]
    if skipped:
        lines += [""]
    lines += [
        "| suite | result | detail |", "| --- | --- | --- |",
    ]
    lines += [f"| `{n}` | {s} | {d} |" for n, s, d in sorted(rows)]
    if never:
        lines += ["", "**Suites that reported nothing:** " +
                  ", ".join(f"`{s}`" for s in never)]
    if diagnostics:
        lines += ["", "## Batch diagnostics", "",
                  "Exit codes and bounded output tails for every batch that "
                  "failed or went silent. A suite that reported nothing is not "
                  "evidence of anything until you can see why."]
        for d in diagnostics:
            lines += ["", f"### Batch {d['batch']} — exit {d['returncode']}", "",
                      f"Suites: {', '.join('`' + s + '`' for s in d['suites'])}"]
            if d["silent"]:
                lines.append("No output from: "
                             + ", ".join(f"`{s}`" for s in d["silent"]))
            if d["stderr"]:
                lines += ["", "stderr (tail):", "", "```", d["stderr"], "```"]
            if d["stdout"]:
                lines += ["", "stdout (tail):", "", "```", d["stdout"], "```"]
    (HARNESS / "RELEASE.md").write_text("\n".join(lines) + "\n")

    # LAST-RUN.txt is written by run_harness.sh, which this drives ONE BATCH AT
    # A TIME — so the record left behind described only the final batch, and
    # stamp_docs.py (invoked by the runner at the end of that batch) stamped the
    # docs from it. A completed 42-suite release therefore published README.md
    # saying "78 assertions across 2 suites" beside a RELEASE.md saying 1693
    # across 42. Both were machine-generated and they contradicted each other,
    # which is the exact defect the generated-not-typed rule exists to prevent —
    # it just moved from typed prose into a second generator.
    #
    # The whole run is the run. Rewrite the record to describe every batch, then
    # re-stamp from it so the docs agree with RELEASE.md.
    # The whole run is the run. Keep the RUN CONTEXT block the runner itself
    # wrote — every environment fact in it (Chromium build, SQLAlchemy version,
    # DATABASE_URL class) is machine-generated and would be invented if this
    # rewrote the header — and replace only the AGGREGATE with one covering
    # every batch. stamp_docs.py then reads the widened record.
    _lr = HARNESS / "LAST-RUN.txt"
    _prev = _lr.read_text(encoding="utf-8") if _lr.is_file() else ""
    _marker = "================ AGGREGATE"
    _header = _prev.split(_marker)[0] if _marker in _prev else ""
    _header = re.sub(r"^(Tree SHA-256\s+:\s*)\S+$", r"\g<1>" + frozen, _header,
                     flags=re.M)
    summary_lines = [f"  {n}: " + ("SKIPPED (0 assertions) — " + d
                                   if s == "skip" else
                                   ("ok — " if s == "pass" else "FAIL — ") + d)
                     for n, s, d in sorted(rows)]
    _lr.write_text(_header + "\n".join([
        "================ AGGREGATE (machine-generated) ================",
        f"# whole release run: {len(BATCHES)} batches recorded as one run",
        f"suites requested : {len(on_disk)}",
        *summary_lines,
        f"assertions passed: {total}   (skipped suites contribute 0)",
        f"suites skipped   : {len(skipped)}",
        f"suites with problems: {len(failed) + len(never)}",
        "",
    ]))
    # The final stamp is part of the release, not an afterthought: if it fails,
    # the docs keep the PREVIOUS run's counts while RELEASE.md carries this
    # one's, and nothing said so. (Outside review of v263, M7.) Surface it.
    _stamp = subprocess.run([sys.executable, str(HARNESS / "stamp_docs.py")],
                            cwd=str(ROOT), capture_output=True, text=True)
    if _stamp.returncode != 0:
        sys.exit("stamp_docs.py failed after the run — the docs were NOT "
                 "updated and the release is not sealed:\n"
                 + (_stamp.stderr or _stamp.stdout).strip())

    # The run is complete, so the checkpoint has served its purpose. Leaving it
    # behind would make the NEXT release silently resume a finished run and
    # report its batches again — a stale-state failure of exactly the kind that
    # has already cost this project a debugging cycle.
    if state_path.exists():
        state_path.unlink()

    print(f"\n{'PASS' if ok else 'FAIL'} — {total} assertions, "
          f"{len(seen)}/{len(on_disk)} suites reported, {len(skipped)} skipped")
    print(f"wrote {(HARNESS / 'RELEASE.md').relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
