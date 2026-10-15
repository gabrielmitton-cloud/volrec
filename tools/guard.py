#!/usr/bin/env python3
"""The recorders' guard: confirm from the DATA, recover automatically, page only if that fails.

Built 15 Oct 2026 after a hand push rejected record.yml's snapshot at 14:30 New York. It was
saved only because a session happened to be open before the close. The guard does that by
itself, with two rules against false alarms (Gabriel: "many times we have skipped over
issues because of false positives"):

  1. A problem is confirmed from the data on main, never from a run's red X. A failed step
     whose rows landed anyway is silence; a green run that wrote nothing is a problem.
  2. Fix first, page second. A missing day before the close is re-run once (record.py and
     surface.py skip what is already recorded and refuse after the close, so a re-run can
     never duplicate a row or record a closed market). Only if the re-run also leaves the
     day missing does RED fire - once, on that re-run's completion.

When it runs (guard.yml): on the completion of every record / surface run, and on two
schedule slots after the trigger time (the "never ran at all" case). It commits nothing.

Decisions, one per panel:
  skip      not a trading day, or after the close (freshness.yml owns lost days)
  wait      too early to judge, or a run of that recorder is still in progress
  ok        the day is complete
  retry     incomplete and still time: re-run the recorder once (no alert)
  recovered complete, and this event is the guard's own re-run finishing: NOTICE
  red       re-run done (or no time left to re-run), nothing recorded, market still open: RED
  yellow    re-run done, only part of the day recorded, or too late to act: YELLOW

  python3 tools/guard.py                  # what the workflow runs
  python3 tools/guard.py --dry-run        # decide and print; dispatch nothing, send nothing
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import alert                                   # noqa: E402
import panel_health as ph                      # noqa: E402  (stdlib only; the one holiday list)

NY = ZoneInfo("America/New_York")
BOT = "github-actions[bot]"                    # the GITHUB_TOKEN's actor: the guard's own re-runs
PANELS = {                                     # panel: (workflow, data file, trigger minute NY, early-close trigger)
    "atm": ("record.yml", ROOT / "data" / "iv_history.csv", 14 * 60 + 30, 11 * 60 + 30),
    "surface": ("surface.yml", ROOT / "data" / "surface.csv", 14 * 60 + 40, 11 * 60 + 40),
}
JUDGE_AFTER_MIN = 25                           # a scheduled check judges 25 min after the trigger
LAST_RETRY_BEFORE_CLOSE_MIN = 15               # no re-run in the last 15 minutes
RED_BEFORE_CLOSE_MIN = 10                      # RED only while a human can still act
COMPLETE_SHARE = 0.9                           # of the previous day's symbols (ATM) / of EXPECTED (surface)


def clock(day):
    """(open, close) in NY minutes for a trading day."""
    return 9 * 60 + 30, (13 * 60 if day in ph.EARLY_CLOSES else 16 * 60)


def trading_day(day):
    return day.weekday() < 5 and day not in ph.US_MARKET_HOLIDAYS


def coverage(panel, path, day):
    """(symbols recorded today, symbols needed for 'complete')."""
    if not path.exists():
        return 0, 1
    by_day = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            if r.get("date") and r.get("symbol"):
                by_day.setdefault(r["date"], set()).add(r["symbol"])
    today = len(by_day.get(day.isoformat(), ()))
    if panel == "surface":
        base = len(ph.EXPECTED)
    else:
        prior = [d for d in by_day if d < day.isoformat()]
        base = len(by_day[max(prior)]) if prior else 1
    return today, max(1, int(base * COMPLETE_SHARE + 0.999))


def decide(panel, now_ny, have, need, runs, event):
    """The first decision, pure. runs: today's runs of this panel's workflow (dicts with id,
    status, actor), or None if GitHub's run list could not be read. event: {'kind':
    'schedule'|'workflow_run'|'manual', 'run_id', 'actor', 'run_event'} - for workflow_run,
    the run that just finished. Returns (skip|wait|ok|retry|red|yellow, why)."""
    day = now_ny.date()
    if not trading_day(day):
        return "skip", "not a trading day"
    mins = now_ny.hour * 60 + now_ny.minute
    _, close = clock(day)
    trig = PANELS[panel][3] if day in ph.EARLY_CLOSES else PANELS[panel][2]
    if mins >= close:
        return "skip", "after the close - freshness.yml reports a lost day"
    if event.get("kind") == "workflow_run" and event.get("actor") == BOT:
        return "skip", "the guard's own re-run; the guard that started it reports the outcome"
    finished_trigger = (event.get("kind") == "workflow_run" and event.get("run_event") == "workflow_dispatch"
                        and mins >= trig - 5)
    if mins < trig + JUDGE_AFTER_MIN and not finished_trigger and event.get("kind") != "manual":
        j = trig + JUDGE_AFTER_MIN
        return "wait", f"too early to judge (before {j // 60}:{j % 60:02d} New York)"
    if have >= need:
        return "ok", f"{have} symbols recorded"
    if runs is None:
        return "yellow", f"only {have} of {need} symbols, and the guard cannot see GitHub's runs to re-run safely"
    if any(r.get("status") != "completed" and r.get("id") != event.get("run_id") for r in runs):
        return "wait", "a run of this recorder is still in progress"
    if any(r.get("actor") == BOT for r in runs):
        return "wait", "already re-run once today; that guard reported the outcome"
    if mins < close - LAST_RETRY_BEFORE_CLOSE_MIN:
        return "retry", f"only {have} of {need} symbols; re-running once"
    return final(panel, now_ny, have, need, retried=False)


def final(panel, now_ny, have, need, retried=True):
    """The one alert, after the re-run (or with no time left for one). Pure."""
    if have >= need:
        return "recovered", f"the automatic re-run recorded the day ({have} symbols)"
    mins = now_ny.hour * 60 + now_ny.minute
    _, close = clock(now_ny.date())
    late = mins >= close - RED_BEFORE_CLOSE_MIN
    tried = "the automatic re-run did not fix it" if retried else "too close to the close to re-run"
    if have == 0 and not late:
        return "red", f"nothing recorded today, and {tried}"
    return "yellow", (f"only {have} of {need} symbols recorded; {tried}" if have
                      else f"nothing recorded today; {tried}")


def _gh(args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)


def todays_runs(workflow, day, repo):
    """Today's (New York) runs of a workflow, from the GitHub API."""
    p = _gh(["api", f"repos/{repo}/actions/workflows/{workflow}/runs?per_page=50&created=>={day - timedelta(days=1)}",
             "--jq", "[.workflow_runs[] | {id, status, created_at, actor: .triggering_actor.login, event}]"])
    if p.returncode != 0:
        raise RuntimeError(f"cannot list {workflow} runs: {p.stderr.strip()[:200]}")
    out = []
    for r in json.loads(p.stdout or "[]"):
        made = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(NY).date()
        if made == day:
            out.append(r)
    return out


def rerun_and_recheck(panel, wf, path, repo, poll_s=20, max_wait_s=12 * 60):
    """Start one re-run, wait for it in this job (nothing relies on workflow_run chaining),
    pull main's data/, and judge once more. Returns (verdict, why, have, need)."""
    import time
    started = datetime.now(timezone.utc)
    p = _gh(["workflow", "run", wf, "-R", repo, "--ref", "main"])
    if p.returncode != 0:
        now_ny = started.astimezone(NY)
        have, need = coverage(panel, path, now_ny.date())
        return "red", f"the automatic re-run could not be started ({p.stderr.strip()[:120]})", have, need
    print(f"re-run of {wf} requested; waiting for it")
    waited, run = 0, None
    while waited < max_wait_s:
        time.sleep(poll_s)
        waited += poll_s
        try:
            mine = [r for r in todays_runs(wf, started.astimezone(NY).date(), repo)
                    if r.get("actor") == BOT and r["created_at"] >= started.strftime("%Y-%m-%dT%H:%M")]
        except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError):
            continue
        run = mine[0] if mine else None
        if run and run.get("status") == "completed":
            break
    subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "--depth", "1", "origin", "main"], timeout=120)
    subprocess.run(["git", "-C", str(ROOT), "checkout", "-q", "FETCH_HEAD", "--", "data"], timeout=60)
    now_ny = datetime.now(timezone.utc).astimezone(NY)
    have, need = coverage(panel, path, now_ny.date())
    verdict, why = final(panel, now_ny, have, need)
    if verdict != "recovered" and not (run and run.get("status") == "completed"):
        why += f" (the re-run had not finished after {max_wait_s // 60} minutes)"
    return verdict, why, have, need


def message(panel, verdict, why, have, need, now_ny):
    wf = PANELS[panel][0]
    name = {"atm": "the ATM panel (record.yml)", "surface": "the strike surface (surface.yml)"}[panel]
    close = "1:00" if now_ny.date() in ph.EARLY_CLOSES else "4:00"
    if verdict == "red":
        return (f"{name} missed today", f"{why}. Before {close} pm New York: GitHub > volrec > Actions > "
                f"{wf} > Run workflow (or tell Claude). After the close the day cannot be recovered.")
    if verdict == "recovered":
        return (f"{name} recovered", f"The first run left the day incomplete; the guard re-ran it and {have} "
                f"symbols are now recorded. Nothing to do.")
    return (f"{name} incomplete today", f"{why} (need {need}). The guard already re-ran it once. "
            f"Tell Claude; the data that did land is kept.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="the recorders' guard")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--panel", choices=sorted(PANELS), action="append")
    a = ap.parse_args(argv)
    repo = os.environ.get("GITHUB_REPOSITORY", "gabrielmitton-cloud/volrec")
    now_ny = datetime.now(timezone.utc).astimezone(NY)
    if os.environ.get("GUARD_NOW"):                       # tests and drills only
        now_ny = datetime.fromisoformat(os.environ["GUARD_NOW"]).astimezone(NY)
    event = {"kind": os.environ.get("GUARD_EVENT", "manual"),
             "run_id": int(os.environ.get("GUARD_RUN_ID") or 0) or None,
             "actor": os.environ.get("GUARD_RUN_ACTOR", ""),
             "run_event": os.environ.get("GUARD_RUN_EVENT", ""),
             "workflow": Path(os.environ.get("GUARD_RUN_WORKFLOW", "")).name}
    url = os.environ.get("GUARD_RUN_URL")
    panels = a.panel or sorted(PANELS)
    if event["kind"] == "workflow_run":                   # judge only the recorder that just finished
        panels = [p for p in panels if PANELS[p][0] == event["workflow"]] or panels
    bad = 0
    for panel in panels:
        wf, path, _, _ = PANELS[panel]
        have, need = coverage(panel, path, now_ny.date())
        try:
            runs = todays_runs(wf, now_ny.date(), repo) if trading_day(now_ny.date()) else []
        except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as e:
            # Cannot see the runs: judge from the data alone, and never re-run blind.
            print(f"::warning::{e}")
            runs = None
        verdict, why = decide(panel, now_ny, have, need, runs, event)
        print(f"{panel}: {verdict} - {why} [{have}/{need} symbols, {now_ny:%H:%M} New York, event {event['kind']}]")
        if a.dry_run or verdict in ("skip", "wait", "ok"):
            continue
        if verdict == "retry":
            verdict, why, have, need = rerun_and_recheck(panel, wf, path, repo)
            now_ny = datetime.now(timezone.utc).astimezone(NY)
            print(f"{panel}: {verdict} - {why}")
        title, body = message(panel, verdict, why, have, need, now_ny)
        level = "notice" if verdict == "recovered" else verdict
        sent = alert.send(level, title, body, url)
        if verdict == "red" and not sent:
            bad = 1                                     # a red X on the guard emails, as a last resort
    return bad


if __name__ == "__main__":
    sys.exit(main())
