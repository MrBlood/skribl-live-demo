"""Somebody has to read main's battery. This is the somebody.

WHY IT EXISTS. Pull requests run the smoke job; the full three-job battery runs
on pushes to main, after the merge. Nothing read that result. main sat red for
about five hours after #221 and again after the v311 merge, and both were found
by accident -- the v311 and v312 entries in DECISIONS.md say so and deliberately
proposed no fix, because where the reader goes was the owner's call. The owner
chose (v314): a GitHub issue, because GitHub already notifies the owner about
issues on their phone, and a red main is exactly the thing worth a notification.

WHAT IT DOES, run by the `main-watch` job after the three battery jobs:
  - any job FAILED            -> open an issue titled with MARKER, or comment on
                                 the one already open (one issue per red spell,
                                 not one per push);
  - every job SUCCEEDED       -> close any open MARKER issue, saying which commit
                                 went green;
  - anything else (cancelled) -> do nothing. A cancelled run verified nothing,
                                 so it can neither raise nor clear the alarm.

`decide()` is pure and is what verify_docs drives, with every case and its
mutation. `main()` is the thin part that talks to the REST API with the job's
own GITHUB_TOKEN (issues: write, nothing else); it is exercised for real the
first time main goes red, and its failure is loud because the job goes red.

    python3 harness/tools/mainwatch.py        # in CI; reads the env below
"""
import json
import os
import sys
import urllib.request

MARKER = "main is red"


def decide(results, open_issues, sha, run_url):
    """What to do, as a list of (verb, issue_number_or_None, body).

    results      {job: 'success' | 'failure' | 'cancelled' | 'skipped'}
    open_issues  [{'number': int, 'title': str}, ...] -- the repo's OPEN issues
    """
    ours = [i["number"] for i in open_issues if i.get("title", "").startswith(MARKER)]
    failed = sorted(j for j, r in results.items() if r == "failure")
    short = sha[:7]
    if failed:
        body = (f"The full battery failed on main at `{short}`: "
                + ", ".join(f"`{j}`" for j in failed)
                + f".\n\nRun: {run_url}\n\nThis issue closes itself when a later "
                "push to main is green on every job.")
        if ours:
            return [("comment", n, body) for n in ours]
        return [("open", None, body)]
    if results and all(r == "success" for r in results.values()):
        return [("close", n, f"main is green again at `{short}` on every job. Run: {run_url}")
                for n in ours]
    return []


def _api(method, path, token, payload=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else None


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    sha = os.environ["GITHUB_SHA"]
    run_url = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}"
               f"/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    results = json.loads(os.environ["JOB_RESULTS"])
    issues = _api("GET", f"/repos/{repo}/issues?state=open&per_page=100", token) or []
    issues = [i for i in issues if "pull_request" not in i]
    actions = decide(results, issues, sha, run_url)
    print(f"results: {results}")
    for verb, number, body in actions:
        if verb == "open":
            made = _api("POST", f"/repos/{repo}/issues", token,
                        {"title": f"{MARKER} at {sha[:7]}", "body": body})
            print(f"opened #{made['number']}")
        elif verb == "comment":
            _api("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})
            print(f"commented on #{number}")
        elif verb == "close":
            _api("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})
            _api("PATCH", f"/repos/{repo}/issues/{number}", token,
                 {"state": "closed", "state_reason": "completed"})
            print(f"closed #{number}")
    if not actions:
        print("nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
