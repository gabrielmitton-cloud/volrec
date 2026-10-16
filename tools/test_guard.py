"""Unit tests for the phone alerts (tools/alert.py) and the recorders' guard (tools/guard.py).
No network: Pushover is replaced by a fake opener, GitHub's run list by plain dicts.

  python tools/test_guard.py
"""
import contextlib
import io
import sys
import urllib.error
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "tools"))
import alert   # noqa: E402
import guard   # noqa: E402

NY = ZoneInfo("America/New_York")
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def at(s):
    return datetime.fromisoformat(s).replace(tzinfo=NY)


SCHED = {"kind": "schedule"}
TRIGGER_DONE = {"kind": "workflow_run", "run_id": 7, "actor": "gabrielmitton-cloud", "run_event": "workflow_dispatch"}
BACKUP_DONE = {"kind": "workflow_run", "run_id": 8, "actor": "gabrielmitton-cloud", "run_event": "schedule"}
BOT_DONE = {"kind": "workflow_run", "run_id": 9, "actor": guard.BOT, "run_event": "workflow_dispatch"}
DONE = {"id": 7, "status": "completed", "actor": "gabrielmitton-cloud"}
RUNNING = {"id": 11, "status": "in_progress", "actor": "gabrielmitton-cloud"}
BOT_RUN = {"id": 9, "status": "completed", "actor": guard.BOT}
THU = "2026-10-15"                      # a Thursday, a normal session

print("=== the guard's first decision ===")
d = lambda now, have, runs, ev, panel="atm", need=99: guard.decide(panel, at(now), have, need, runs, ev)[0]
check("complete day -> ok, whatever the event", d(f"{THU}T15:10", 109, [DONE], SCHED) == "ok")
check("15 Oct's case: the trigger run finished at 14:32 with nothing on main -> retry at once",
      d(f"{THU}T14:32", 0, [DONE], TRIGGER_DONE) == "retry")
check("a scheduled check before 14:55 waits (the recorder may simply not have run yet)",
      d(f"{THU}T14:40", 0, [], SCHED) == "wait")
check("the GitHub-cron backup finishing early (it stands aside before 14:45) is NOT judged",
      d(f"{THU}T11:05", 0, [DONE], BACKUP_DONE) == "wait")
SURF_DONE = {"kind": "workflow_run", "run_id": 12, "actor": "gabrielmitton-cloud", "run_event": "workflow_dispatch"}
BOT_REC = {**BOT_DONE, "workflow": "record.yml"}
check("ultrareview: the guard's own record re-run finishing still lets the SURFACE be judged (one queue)",
      d(f"{THU}T14:50", 0, [DONE], BOT_REC, "surface", need=7) == "retry"
      and d(f"{THU}T14:50", 0, [BOT_RUN], BOT_REC) == "skip")
check("16 Oct fix: the surface run finishing at 14:42 is the ATM panel's timer -> ATM missing is re-run",
      d(f"{THU}T14:42", 0, [], SURF_DONE) == "retry")
check("16 Oct fix: the ATM run finishing at 14:33 does not judge the surface yet (its trigger is 14:40)",
      d(f"{THU}T14:33", 0, [], TRIGGER_DONE, "surface", need=8) == "wait")
check("16 Oct fix: a GitHub backup that stood aside, finishing at 14:39, judges the ATM panel",
      d(f"{THU}T14:39", 0, [], BACKUP_DONE) == "retry")
MANUAL = {"kind": "manual"}
check("16 Oct: a manual or mis-timed run BEFORE the 14:30 trigger never re-runs the recorder (no off-time snapshot)",
      d(f"{THU}T10:00", 0, [], MANUAL) == "wait" and d(f"{THU}T11:00", 0, [], SCHED) == "wait")
check("16 Oct: the cron-job.org guard at 15:00 (manual) judges at once", d(f"{THU}T15:00", 0, [DONE], MANUAL) == "retry")
check("16 Oct: early close - a manual run at 11:00, before the 11:30 trigger, waits", d("2026-12-24T11:00", 0, [], MANUAL) == "wait")
TWO_DISPATCH = [DONE, {"id": 13, "status": "completed", "actor": "an-unexpected-login", "event": "workflow_dispatch"}]
DONE_D = {**DONE, "event": "workflow_dispatch"}
check("two workflow_dispatch runs today, a later event -> no third re-run and no repeat alert (wait)",
      d(f"{THU}T15:10", 0, [DONE_D, TWO_DISPATCH[1]], SCHED) == "wait")
SECOND_DONE = {"kind": "workflow_run", "run_id": 13, "actor": "an-unexpected-login", "run_event": "workflow_dispatch"}
check("...but the completion of that second dispatch itself pages ONCE (never silent)",
      d(f"{THU}T15:10", 0, [DONE_D, TWO_DISPATCH[1]], SECOND_DONE) == "red")
check("one dispatch (the trigger) alone does not block the re-run", d(f"{THU}T15:10", 0, [DONE_D], SCHED) == "retry")
check("16 Oct: the surface is complete at 7 of 8 (90% rounded down) - one missing underlying is not a false alarm",
      d(f"{THU}T15:10", 7, [DONE], SCHED, "surface", need=int(len(guard.ph.EXPECTED) * guard.COMPLETE_SHARE)) == "ok")
check("never ran at all, 15:05 scheduled check -> retry", d(f"{THU}T15:05", 0, [], SCHED) == "retry")
check("a run still in progress -> wait, no double re-run", d(f"{THU}T15:05", 0, [RUNNING], SCHED) == "wait")
check("already re-run once today -> wait (that guard reported; no second alert)",
      d(f"{THU}T15:25", 0, [DONE, BOT_RUN], SCHED) == "wait")
check("the guard's own re-run finishing -> skip (its starter reports the outcome)",
      d(f"{THU}T15:10", 0, [BOT_RUN], BOT_DONE) == "skip")
check("too late to re-run (15:46), nothing recorded -> red at once",
      d(f"{THU}T15:46", 0, [DONE], SCHED) == "red")
check("too late to re-run, part of the day recorded -> yellow, not red",
      d(f"{THU}T15:46", 60, [DONE], SCHED) == "yellow")
check("after the close -> skip (freshness owns a lost day; never wake anyone for it)",
      d(f"{THU}T16:05", 0, [DONE], SCHED) == "skip")
check("a Saturday -> skip", d("2026-10-17T15:10", 0, [], SCHED) == "skip")
check("a market holiday (Thanksgiving) -> skip", d("2026-11-26T15:10", 0, [], SCHED) == "skip")
check("an early close (24 Dec): 12:47 is past the 13:00 close minus 15 -> no re-run, red",
      d("2026-12-24T12:47", 0, [DONE], SCHED) == "red")
check("an early close: 12:52 is inside the last 10 minutes -> yellow", d("2026-12-24T12:52", 0, [DONE], SCHED) == "yellow")
check("an early close: judged from 11:55, so 11:40 waits", d("2026-12-24T11:40", 0, [], SCHED) == "wait")
check("GitHub's run list unreadable after retries, nothing recorded, market open -> red (a human can act), never a blind re-run",
      d(f"{THU}T15:10", 0, None, SCHED) == "red")
check("GitHub's run list unreadable, part of the day recorded -> yellow", d(f"{THU}T15:10", 60, None, SCHED) == "yellow")
check("GitHub's run list unreadable inside the last 10 minutes -> yellow", d(f"{THU}T15:52", 0, None, SCHED) == "yellow")
check("GitHub's run list unreadable, day complete -> ok", d(f"{THU}T15:10", 109, None, SCHED) == "ok")
check("surface: complete only with the expected underlyings",
      d(f"{THU}T15:10", len(guard.ph.EXPECTED), [DONE], SCHED, "surface", need=len(guard.ph.EXPECTED)) == "ok"
      and d(f"{THU}T15:10", 0, [DONE], SCHED, "surface", need=len(guard.ph.EXPECTED)) == "retry")

print("\n=== the one alert after the re-run ===")
f = lambda now, have, need=99: guard.final("atm", at(now), have, need)[0]
check("the re-run recorded the day -> recovered (a NOTICE, not an alarm)", f(f"{THU}T14:40", 109) == "recovered")
check("the re-run left nothing, market open -> red", f(f"{THU}T14:40", 0) == "red")
check("the re-run left part of the day -> yellow", f(f"{THU}T14:40", 50) == "yellow")
check("nothing, but within 10 minutes of the close -> yellow (no one can act in time)",
      f(f"{THU}T15:52", 0) == "yellow")

print("\n=== the re-run path, driven end to end with fake GitHub and git ===")
import tempfile as _tf  # noqa: E402
from datetime import timezone as _tz  # noqa: E402
from types import SimpleNamespace as _NS  # noqa: E402


def _drive(start_ok=True, run_done=True, fetch_ok=True, lands=True, when="2026-10-15T14:40:00", prior=4, today=0,
           conclusion="success", others=(), other_have=8):
    """others: runs that already exist before the guard dispatches (e.g. another guard's re-run)."""
    with _tf.TemporaryDirectory() as td:
        p = Path(td) / "iv.csv"
        rows = "date,symbol,x\n" + "".join(f"2026-10-14,S{i},1\n" for i in range(prior)) \
            + "".join(f"2026-10-15,S{i},1\n" for i in range(today))
        p.write_text(rows)
        t0 = datetime.fromisoformat(when).replace(tzinfo=NY).astimezone(_tz.utc)
        state = {"dispatched": False}

        def gh(args):
            state["dispatched"] = start_ok
            return _NS(returncode=0 if start_ok else 1, stdout="", stderr="" if start_ok else "HTTP 403")

        def runs(wf, day, repo):
            out = list(others)
            if state["dispatched"]:
                out.append({"id": 99, "status": "completed" if run_done else "queued", "conclusion":
                            conclusion if run_done else None, "actor": "some-unexpected-login",
                            "event": "workflow_dispatch", "created_at": t0.strftime("%Y-%m-%dT%H:%M:30Z")})
            return out

        def git(args):
            if args[0] == "checkout" and fetch_ok and lands:
                p.write_text(rows + "".join(f"2026-10-15,S{i},1\n" for i in range(prior)))
            return _NS(returncode=0 if fetch_ok else 1, stdout="", stderr="")
        cov = lambda panel, path, day: guard.coverage(panel, path, day) if panel == "atm" else (other_have, 7)  # noqa: E731
        return guard.rerun_and_recheck("atm", "record.yml", p, "r/r", poll_s=1, max_wait_s=3, gh=gh, git=git,
                                       sleep=lambda s: None, now=lambda: t0, runs_fn=runs, cov_fn=cov)


check("re-run lands the day -> recovered (a NOTICE)", _drive()[0] == "recovered")
check("re-run FAILED and the day is still empty, market open -> red", _drive(lands=False, conclusion="failure")[0] == "red")
v = _drive(fetch_ok=False)
check("main cannot be read after the re-run -> yellow 'could not confirm', never a RED on stale data",
      v[0] == "yellow" and "could not read main" in v[1])
check("re-run cannot be started, nothing recorded, market open -> red", _drive(start_ok=False)[0] == "red")
check("re-run cannot be started, part of the day recorded -> yellow (RED only for nothing at all)",
      _drive(start_ok=False, today=2)[0] == "yellow")
check("re-run cannot be started within 10 min of the close -> yellow",
      _drive(start_ok=False, when="2026-10-15T15:55:00")[0] == "yellow")
v = _drive(run_done=False, lands=False)
check("re-run still queued after the wait and the day empty -> red that says it may still land",
      v[0] == "red" and "may still land" in v[1])
check("the guard recognises its own re-runs by GitHub's bot login", guard.BOT == "github-actions[bot]")
check("16 Oct: its own re-run is found WITHOUT relying on the bot login (an unexpected login still works)",
      _drive()[0] == "recovered")
check("16 Oct: a re-run that existed before the dispatch (another guard's) is never mistaken for ours",
      _drive(run_done=False, lands=False, others=[{"id": 50, "status": "completed", "conclusion": "success",
             "actor": guard.BOT, "event": "workflow_dispatch", "created_at": "2026-10-15T18:40:10Z"}])[0] == "red")
v = _drive(lands=False, conclusion="success")
check("a clean re-run that recorded nothing, but the OTHER recorder has data -> still RED (no independent evidence)",
      v[0] == "red")
check("a re-run that FAILED and recorded nothing -> still RED", _drive(lands=False, conclusion="failure")[0] == "red")
v = _drive(lands=False, conclusion="success", other_have=0, when="2026-10-15T15:00:00")
check("end to end: clean empty re-run at 15:00 and the surface (due since 14:50) also empty -> YELLOW 'closure?'",
      v[0] == "yellow" and "closure" in v[1])
check("ultrareview: at 14:36 the surface's 14:40 slot has not run - its emptiness is NOT evidence -> RED",
      _drive(lands=False, conclusion="success", other_have=0, when="2026-10-15T14:36:00")[0] == "red")
check("clean re-run, nothing recorded, AND the other recorder also empty -> YELLOW 'unscheduled closure?'",
      guard.final("atm", at(f"{THU}T15:00"), 0, 98, rerun_clean=True, other_empty=True)[0] == "yellow")
check("clean re-run alone (other recorder has data) -> RED", guard.final("atm", at(f"{THU}T15:00"), 0, 98, rerun_clean=True)[0] == "red")

print("\n=== run_panels: the loop main() runs, with fakes ===")


def _panels(now, cov, runs_seq, rerun=None, sent_ok=True, dry=False, ev=None):
    sent, calls = [], {"runs": 0}

    def runs_fn(wf, day, repo):
        calls["runs"] += 1
        r = runs_seq.pop(0) if runs_seq else []
        if isinstance(r, Exception):
            raise r
        return r
    rc = guard.run_panels(["atm", "surface"], at(now), ev or SCHED, "r/r", None, dry_run=dry, runs_fn=runs_fn,
                          rerun_fn=rerun or (lambda *a, **k: ("recovered", "fake", 9, 9)),
                          send_fn=lambda lv, t, b, u: sent.append(lv) or sent_ok, sleep=lambda s: None,
                          monotonic=lambda: 0.0, cov_fn=lambda panel, path, day: cov[panel], now_fn=lambda: at(now))
    return rc, sent, calls


rc, sent, _ = _panels(f"{THU}T15:10", {"atm": (109, 98), "surface": (8, 7)}, [[DONE], [DONE]])
check("both panels complete -> no alert, exit 0", rc == 0 and sent == [])
rc, sent, calls = _panels(f"{THU}T15:10", {"atm": (0, 98), "surface": (8, 7)},
                          [RuntimeError("api"), RuntimeError("api"), RuntimeError("api"), [DONE]])
check("run list fails 3 times -> RED for the empty panel, 3 tries made, the other panel still judged",
      sent == ["red"] and calls["runs"] == 4)
rc, sent, _ = _panels(f"{THU}T15:10", {"atm": (0, 98), "surface": (8, 7)},
                      [RuntimeError("a"), RuntimeError("a"), RuntimeError("a"), [DONE]], sent_ok=False)
check("a RED that cannot be delivered -> exit 1 (the guard's red X emails, last resort)", rc == 1)
rc, sent, _ = _panels(f"{THU}T15:10", {"atm": (0, 98), "surface": (0, 7)}, [[DONE], [DONE]])
check("both panels empty -> both re-run, two NOTICEs on recovery", sent == ["notice", "notice"])
rc, sent, _ = _panels(f"{THU}T15:10", {"atm": (0, 98), "surface": (0, 7)}, [[DONE], [DONE]], dry=True)
check("dry run decides but never re-runs or sends", sent == [] and rc == 0)

print("\n=== coverage reads the data, not the run's colour ===")
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "iv.csv"
    p.write_text("date,symbol,x\n2026-10-14,A,1\n2026-10-14,B,1\n2026-10-14,C,1\n2026-10-14,D,1\n"
                 "2026-10-15,A,1\n2026-10-15,B,1\n")
    have, need = guard.coverage("atm", p, at(f"{THU}T15:00").date())
    check("ATM: 2 symbols today against 4 yesterday -> have 2, need 3 (90%, rounded DOWN since 16 Oct)", (have, need) == (2, 3))
    p2 = Path(td) / "iv2.csv"
    p2.write_text("date,symbol,x\n" + "".join(f"2026-10-13,S{i},1\n" for i in range(10))
                  + "".join(f"2026-10-14,S{i},1\n" for i in range(3)))
    check("ATM bar = best of the last 5 days: a partial yesterday (3) cannot lower today's need below 9 of 10",
          guard.coverage("atm", p2, at(f"{THU}T15:00").date())[1] == 9)
    have, _ = guard.coverage("atm", Path(td) / "missing.csv", at(f"{THU}T15:00").date())
    check("a missing file counts as nothing recorded", have == 0)

print("\n=== Pushover payloads ===")
p = alert.payload("red", "x", "y", "https://example.org")
check("red is emergency priority 2, repeating every 120 s for 3600 s (Gabriel, 15 Oct)",
      p["priority"] == "2" and p["retry"] == "120" and p["expire"] == "3600")
check("Pushover's limits respected: retry >= 30 s, expire <= 10800 s",
      alert.RED_RETRY_S >= 30 and alert.RED_EXPIRE_S <= 10800)
check("yellow is high priority 1 (through quiet hours), with no repeats",
      alert.payload("yellow", "x", "y")["priority"] == "1" and "retry" not in alert.payload("yellow", "x", "y"))
check("green is quiet (-1): no sound", alert.payload("green", "x", "y")["priority"] == "-1")
check("only red repeats", [lv for lv in alert.LEVELS if "retry" in alert.payload(lv, "t", "m")] == ["red"])
check("message and title are cut to Pushover's limits",
      len(alert.payload("green", "t" * 400, "m" * 5000)["message"]) == 1024
      and len(alert.payload("green", "t" * 400, "m")["title"]) == 250)
try:
    alert.payload("purple", "x", "y")
    check("an unknown level is refused", False)
except ValueError:
    check("an unknown level is refused", True)


class Fake:
    def __init__(self, codes):
        self.codes, self.calls, self.bodies = list(codes), 0, []

    def __call__(self, req, timeout=None):
        self.calls += 1
        self.bodies.append(req.data.decode())
        code = self.codes.pop(0)
        if code is None:
            raise urllib.error.URLError("down")
        if code != 200:
            raise urllib.error.HTTPError(req.full_url, code, "x", {}, io.BytesIO(b'{"status":0,"errors":["user key is invalid"]}'))
        r = io.BytesIO(b'{"status":1}')
        r.status = 200
        r.__enter__ = lambda *a: r
        r.__exit__ = lambda *a: False
        return contextlib.nullcontext(r)


KEYS = {"PUSHOVER_TOKEN": "a" * 30, "PUSHOVER_USER": "u" * 30}
print("\n=== sending ===")
fk = Fake([200])
out = io.StringIO()
with contextlib.redirect_stdout(out):
    okd = alert.send("yellow", "t", "m", env=KEYS, opener=fk, sleep=lambda s: None)
check("a 200 is a send", okd and fk.calls == 1)
check("the keys are never printed", "a" * 30 not in out.getvalue() and "u" * 30 not in out.getvalue())
check("the keys do go to Pushover in the request body", "token=" + "a" * 30 in fk.bodies[0])
fk = Fake([400, 200])
with contextlib.redirect_stdout(io.StringIO()):
    okd = alert.send("yellow", "t", "m", env=KEYS, opener=fk, sleep=lambda s: None)
check("a 4xx is never repeated (Pushover blocks IPs that repeat bad requests)", not okd and fk.calls == 1)
fk = Fake([500, None, 200])
waits = []
with contextlib.redirect_stdout(io.StringIO()):
    okd = alert.send("yellow", "t", "m", env=KEYS, opener=fk, sleep=waits.append)
check("a 5xx or no reply is retried, at least 5 s apart, and then succeeds",
      okd and fk.calls == 3 and all(w >= 5 for w in waits))
fk = Fake([500, 500, 500, 200])
with contextlib.redirect_stdout(io.StringIO()):
    okd = alert.send("yellow", "t", "m", env=KEYS, opener=fk, sleep=lambda s: None)
check("at most 3 tries, then it reports failure (never loops)", not okd and fk.calls == 3)
fk = Fake([200])
with contextlib.redirect_stdout(io.StringIO()):
    okd = alert.send("red", "t", "m", env={}, opener=fk, sleep=lambda s: None)
check("no keys: nothing sent, returns False, never crashes", not okd and fk.calls == 0)

print("\n=== messages say what to do ===")
t, b = guard.message("atm", "red", "nothing recorded today", 0, 99, at(f"{THU}T15:00"))
check("red names the workflow and the deadline", "record.yml" in b and "4:00 pm New York" in b)
t, b = guard.message("atm", "red", "x", 0, 99, at("2026-12-24T12:00"))
check("on an early close the deadline is 1:00", "1:00 pm New York" in b)
check("the guard and the sender use only the standard library",
      all("import requests" not in (R / "tools" / n).read_text() for n in ("guard.py", "alert.py")))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
