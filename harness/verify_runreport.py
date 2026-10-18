"""The parallel runner keeps its first red.

THE OUTSIDE REVIEWER OF v325 (QA-001): harness/run_parallel.py re-runs a
suite that MEASURES alone when it goes red beside others, and the alone answer
replaced the red one. The packet's own run read "14/16" for verify_videoexport,
then "16/16" alone, then "19/19 suites ok" and exit 0, and the red log was
written over by the re-run. That red had found a real defect (a video with no
frame called a success), and survived only because it was copied off the
terminal. A suite red beside others and green alone is INTERMITTENT now: both
counts, listed apart, not counted as ok, its red failures said again, exit 3.

No browser and no server: the runner's reporting is driven with results built
here, and its re-run step with a stand-in for the suite it would run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assertions import make_check  # noqa: E402
import run_parallel as rp  # noqa: E402

results = []
check = make_check(results)


def res(suite, code, a=None, b=None, fails=(), secs=42.0):
    return {"suite": suite, "code": code, "counts": (str(a), str(b)) if b is not None else None,
            "fails": list(fails), "skip": None, "secs": secs, "log": ""}


print("RUN_PARALLEL — a red beside others stays on the record")
RED = "[FAIL] Flip: a silent WebM carries its frames — 0 tracks, 0 frames"
ok = res("verify_docs.py", 0, 138, 138)
red = res("verify_videoexport.py", 1, 14, 16, [RED])
calls = []


def green_alone(suite):
    calls.append(suite)
    return res(suite, 0, 16, 16)


plain_red = res("verify_jsstrip.py", 1, 33, 34, ["[FAIL] something real"])
got = rp.rerun_alone([ok, red, plain_red], {"verify_videoexport.py"}, green_alone)
check("only the suite that measures, and only once, runs again alone",
      calls == ["verify_videoexport.py"], str(calls))
again = got[1]
check("...and its red run rides along on the new result, not thrown away",
      again.get("first") is red, str(again.get("first")))
check("a suite red beside others and green alone is INTERMITTENT, not ok",
      rp.verdict(again) == "intermittent", rp.verdict(again))
ln = rp.line(again)
check("...its line carries both counts", "INTERMITTENT" in ln and "14/16 passed beside others" in ln
      and "16/16 alone" in ln, ln)
text, code = rp.report([ok, again], 1.0)
head = text.strip().splitlines()[0]
check("...the summary does not count it as ok", head.startswith("1/2 suites ok"), head)
check("...it is named apart, as intermittent", "1 INTERMITTENT" in text
      and "verify_videoexport.py" in text.split("1 INTERMITTENT", 1)[-1], text)
check("...the failures it had beside others are said again", f"beside others, green alone | {RED}" in text, text)
check("...and the run's exit is 3, not 0", code == 3, str(code))

red_again = rp.rerun_alone([res("verify_videoexport.py", 1, 14, 16, [RED])], {"verify_videoexport.py"},
                           lambda s: res(s, 1, 15, 16, ["[FAIL] still red alone"]))[0]
_, code_fail = rp.report([ok, red_again], 1.0)
check("red beside others and red alone is a failure, exit 1",
      rp.verdict(red_again) == "fail" and code_fail == 1, f"{rp.verdict(red_again)} {code_fail}")
_, code_both = rp.report([ok, again, plain_red], 1.0)
check("a failure outranks an intermittent: exit 1", code_both == 1, str(code_both))
text_ok, code_ok = rp.report([ok, res("verify_seam.py", 0, 402, 402)], 1.0)
check("all green is exit 0, and says so", code_ok == 0 and "2/2 suites ok" in text_ok, text_ok)
skipped = res("verify_mp4.py", 77)
skipped["skip"] = "no H.264 here"
text_skip, code_skip = rp.report([ok, skipped], 1.0)
check("a skip is said apart and does not fail the run", code_skip == 0 and "1 skipped" in text_skip, text_skip)
check("the re-run alone writes its own log, so the red run's is never written over",
      rp.log_path("verify_x.py").name == "verify_x.log"
      and rp.log_path("verify_x.py", "alone").name == "verify_x.alone.log", str(rp.log_path("verify_x.py", "alone")))

passed = sum(1 for ok_, _ in results if ok_)
bad = [n for ok_, n in results if not ok_]
print(f"\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(bad)))
sys.exit(1 if bad else 0)
