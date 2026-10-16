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
        prior = sorted(d for d in by_day if d < day.isoformat())[-5:]
        # The best of the last 5 recorded days (security review, 16 Oct): with yesterday alone, a partial
        # day would lower today's bar and the check would ratchet down with the failure it exists to catch.
        base = max(len(by_day[d]) for d in prior) if prior else 1
    # Floor, not ceiling (16 Oct review): 90% of the surface's 8 is 7, so one underlying the feed
    # legitimately lacks is not an "incomplete" day; ATM: 90% of yesterday's 109 is 98.
    return today, max(1, int(base * COMPLETE_SHARE))


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
    if (event.get("kind") == "workflow_run" and event.get("actor") == BOT
            and event.get("workflow") in ("", None, PANELS[panel][0])):
        # Only the panel whose recorder the guard re-ran (ultrareview, 16 Oct): with one queue, this event
        # may have replaced a pending guard for the OTHER recorder, so that panel is still judged here.
        return "skip", "the guard's own re-run; the guard that started it reports the outcome"
    # 16 Oct (engineer review): ANY recorder run finishing after this panel's trigger + 5 minutes is a
    # judging event - the trigger, the other recorder, or a GitHub backup that stood aside. GitHub's own
    # crons run 2-7 h late here, so the guard's schedule slots alone would land after the close.
    # (A dispatched trigger run is judged from its own slot - the hard floor below guarantees mins >= trig;
    # any other recorder run from 5 minutes after the slot, so an early backup cannot trigger a re-run.)
    finished_trigger = event.get("kind") == "workflow_run" and (
        event.get("run_event") == "workflow_dispatch" or mins >= trig + 5)
    if mins < trig:
        # 16 Oct review: NOTHING may start a recorder before its own trigger slot - a manual or
        # mis-timed run (e.g. a cron-job.org job saved in UTC) would record the day at the wrong time,
        # and the real trigger would then skip it as already recorded.
        return "wait", f"before the {trig // 60}:{trig % 60:02d} New York trigger slot - never re-run early"
    if mins < trig + JUDGE_AFTER_MIN and not finished_trigger and event.get("kind") != "manual":
        j = trig + JUDGE_AFTER_MIN
        return "wait", f"too early to judge (before {j // 60}:{j % 60:02d} New York)"
    if have >= need:
        return "ok", f"{have} symbols recorded"
    if runs is None:                              # unreadable even after retries (main() tries 3 times)
        late = mins >= close - RED_BEFORE_CLOSE_MIN
        why = "the guard cannot read GitHub's run list, so it did not re-run automatically"
        if have == 0 and not late:
            return "red", f"nothing recorded today, and {why}"
        return "yellow", f"only {have} of {need} symbols recorded; {why}"
    if any(r.get("status") != "completed" and r.get("id") != event.get("run_id") for r in runs):
        return "wait", "a run of this recorder is still in progress"
    if any(r.get("actor") == BOT for r in runs):
        return "wait", "already re-run once today; that run's guard reported the outcome"
    dispatches = [r for r in runs if r.get("event") == "workflow_dispatch"]
    if len(dispatches) >= 2:
        # A cap that needs no login (16 Oct reviews): a normal day has one workflow_dispatch (the trigger);
        # two mean it was already re-run (by a human, or by a guard whose login GitHub reports differently).
        # Never re-run a third time, never go silent - and alert ONCE: on the completion of the newest
        # dispatch run itself; every other event waits (ultrareview, 16 Oct: no repeated REDs).
        newest = max(r["id"] for r in dispatches)
        if event.get("kind") == "workflow_run" and event.get("run_id") == newest:
            return final(panel, now_ny, have, need, retried=True)
        return "wait", "already re-run today; the alert goes out once, when that re-run finishes"
    if mins < close - LAST_RETRY_BEFORE_CLOSE_MIN:
        return "retry", f"only {have} of {need} symbols; re-running once"
    return final(panel, now_ny, have, need, retried=False)


def final(panel, now_ny, have, need, retried=True, rerun_clean=False, other_empty=False):
    """The one alert, after the re-run (or with no time left for one). Pure. rerun_clean: the re-run
    finished with success yet the day is still empty; other_empty: the OTHER recorder also has nothing
    today. Both together are independent evidence of a closed market or an empty feed."""
    if have >= need:
        return "recovered", f"the automatic re-run recorded the day ({have} symbols)"
    if retried and rerun_clean and other_empty and have == 0:
        # 16 Oct review: a recorder that runs cleanly and records nothing is what an unscheduled market
        # closure (or an empty feed) looks like - re-running by hand would not help, so it must not page RED.
        return "yellow", ("the re-run finished cleanly but recorded nothing - most likely an unscheduled "
                          "market closure or an empty feed; check whether the market is open")
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
             "--jq", "[.workflow_runs[] | {id, status, conclusion, created_at, actor: .triggering_actor.login, event}]"])
    if p.returncode != 0:
        raise RuntimeError(f"cannot list {workflow} runs: {p.stderr.strip()[:200]}")
    out = []
    for r in json.loads(p.stdout or "[]"):
        made = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(NY).date()
        if made == day:
            out.append(r)
    return out


def _git(args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=120)


def _start_failed(panel, now_ny, have, need, err):
    """The re-run could not be started: RED only while nothing is recorded and a human can act."""
    v, _ = final(panel, now_ny, have, need)
    why = f"the automatic re-run could not be started ({err[:120]})"
    return ("red" if v == "red" else "yellow" if v != "recovered" else "recovered"), why


def rerun_and_recheck(panel, wf, path, repo, poll_s=20, max_wait_s=12 * 60, gh=None, git=None,
                      sleep=None, now=None, runs_fn=None, cov_fn=None):
    """Start one re-run, wait for it in this job (nothing relies on workflow_run chaining), pull
    main's data/, and judge once more. Returns (verdict, why, have, need). Every dependency is
    injectable so tools/test_guard.py can drive each path."""
    import time
    gh, git, cov_fn = gh or _gh, git or _git, cov_fn or coverage
    sleep, now, runs_fn = sleep or time.sleep, now or (lambda: datetime.now(timezone.utc)), runs_fn or todays_runs
    started = now()
    try:                                               # runs that exist before we dispatch are not ours
        before = {r["id"] for r in runs_fn(wf, started.astimezone(NY).date(), repo)}
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError):
        before = None                                  # unknown: fail closed below (security review, 16 Oct)
    since = started.strftime("%Y-%m-%dT%H:%M:%S")
    p = gh(["workflow", "run", wf, "-R", repo, "--ref", "main"])
    if p.returncode != 0:
        now_ny = started.astimezone(NY)
        have, need = cov_fn(panel, path, now_ny.date())
        v, why = _start_failed(panel, now_ny, have, need, p.stderr.strip())
        return v, why, have, need
    print(f"re-run of {wf} requested; waiting for it (up to {max_wait_s // 60} min)")
    waited, run = 0, None
    while waited < max_wait_s:
        sleep(poll_s)
        waited += poll_s
        try:
            # Ours = a workflow_dispatch run that did not exist before we dispatched (16 Oct review: no
            # reliance on the bot login, and no minute-truncated time match against another guard's run).
            mine = [r for r in runs_fn(wf, started.astimezone(NY).date(), repo)
                    if r.get("event") == "workflow_dispatch" and r.get("created_at", "") >= since
                    and (before is None or r["id"] not in before)]
        except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError):
            continue
        run = min(mine, key=lambda r: r["id"]) if mine else None     # the oldest new one is ours
        if run and run.get("status") == "completed":
            break
    # Read main again. If that fails, never page RED on stale data (16 Oct, engineer review).
    fetched = False
    for _ in range(2):
        f = git(["fetch", "-q", "--depth", "1", "origin", "main"])
        if f.returncode == 0 and git(["checkout", "-q", "FETCH_HEAD", "--", "data"]).returncode == 0:
            fetched = True
            break
        sleep(10)
    now_ny = now().astimezone(NY)
    have, need = cov_fn(panel, path, now_ny.date())
    if not fetched:
        return ("yellow", "the re-run was started but the guard could not read main afterwards to confirm it - "
                "check the data by hand before the close", have, need)
    done = bool(run and run.get("status") == "completed")
    if run:
        print(f"re-run {run['id']}: status {run.get('status')}, conclusion {run.get('conclusion')}, "
              f"triggering actor {run.get('actor')!r} (guard.BOT expects {BOT!r})")
    other = "surface" if panel == "atm" else "atm"
    other_have, _ = cov_fn(other, PANELS[other][1], now_ny.date())
    o_trig = PANELS[other][3] if now_ny.date() in ph.EARLY_CLOSES else PANELS[other][2]
    # The other recorder's emptiness is evidence only once its own run has had time to land (ultrareview,
    # 16 Oct): at 14:36 the surface's 14:40 trigger has simply not run yet, which proves nothing.
    other_due = now_ny.hour * 60 + now_ny.minute >= o_trig + 10
    # Fail closed: without a trustworthy baseline the run we found may not be ours, so no downgrade.
    clean = done and before is not None and run.get("conclusion") == "success"
    verdict, why = final(panel, now_ny, have, need, rerun_clean=clean, other_empty=other_due and other_have == 0)
    if verdict != "recovered" and not done:
        why += f" (the re-run had not finished after {max_wait_s // 60} minutes; it may still land)"
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
    return (f"{name} needs a look", f"{why} (need {need}). Tell Claude; any data that did land is kept.")


def run_panels(panels, now_ny, event, repo, url, dry_run=False, runs_fn=None, rerun_fn=None,
               send_fn=None, sleep=None, monotonic=None, cov_fn=None, now_fn=None):
    """Judge each panel once and act. Returns 1 when a RED could not be delivered (the red X on the
    guard run then emails, as a last resort), else 0. Every dependency is injectable for the tests."""
    import time
    runs_fn, rerun_fn = runs_fn or todays_runs, rerun_fn or rerun_and_recheck
    send_fn, sleep = send_fn or alert.send, sleep or time.sleep
    monotonic, cov_fn = monotonic or time.monotonic, cov_fn or coverage
    now_fn = now_fn or (lambda: datetime.now(timezone.utc).astimezone(NY))
    bad = 0
    deadline = monotonic() + 16 * 60                     # both panels share one budget (guard.yml: 30 min)
    for panel in panels:
        wf, path, _, _ = PANELS[panel]
        have, need = cov_fn(panel, path, now_ny.date())
        runs = [] if not trading_day(now_ny.date()) else None
        for attempt in range(3 if runs is None else 0):
            try:
                runs = runs_fn(wf, now_ny.date(), repo)
                break
            except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as e:
                print(f"::warning::{e}")                 # never re-run blind; decide() pages instead
                if attempt < 2:
                    sleep(10)
        verdict, why = decide(panel, now_ny, have, need, runs, event)
        print(f"{panel}: {verdict} - {why} [{have}/{need} symbols, {now_ny:%H:%M} New York, event {event['kind']}]")
        if dry_run or verdict in ("skip", "wait", "ok"):
            continue
        if verdict == "retry":
            left = int(deadline - monotonic())
            verdict, why, have, need = rerun_fn(panel, wf, path, repo, max_wait_s=max(60, min(12 * 60, left)))
            now_ny = now_fn()
            print(f"{panel}: {verdict} - {why}")
        title, body = message(panel, verdict, why, have, need, now_ny)
        level = "notice" if verdict == "recovered" else verdict
        sent = send_fn(level, title, body, url)
        if verdict == "red" and not sent:
            bad = 1
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="the recorders' guard")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--panel", choices=sorted(PANELS), action="append")
    a = ap.parse_args(argv)
    repo = os.environ.get("GITHUB_REPOSITORY", "gabrielmitton-cloud/volrec")
    now_fn = lambda: datetime.now(timezone.utc).astimezone(NY)   # noqa: E731
    if os.environ.get("GUARD_NOW"):                       # tests and drills only: a fixed clock throughout
        now_fn = lambda: datetime.fromisoformat(os.environ["GUARD_NOW"]).astimezone(NY)   # noqa: E731
    now_ny = now_fn()
    event = {"kind": os.environ.get("GUARD_EVENT", "manual"),
             "run_id": int(os.environ.get("GUARD_RUN_ID") or 0) or None,
             "actor": os.environ.get("GUARD_RUN_ACTOR", ""),
             "run_event": os.environ.get("GUARD_RUN_EVENT", ""),
             "workflow": Path(os.environ.get("GUARD_RUN_WORKFLOW", "")).name}
    # Both panels on every event: one recorder's completion is the other's timer (16 Oct).
    return run_panels(a.panel or sorted(PANELS), now_ny, event, repo, os.environ.get("GUARD_RUN_URL"), a.dry_run,
                      now_fn=now_fn)


if __name__ == "__main__":
    sys.exit(main())
