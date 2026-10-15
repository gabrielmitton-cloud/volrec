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
check("GitHub's run list unreadable, day incomplete -> yellow, never a blind re-run",
      d(f"{THU}T15:10", 0, None, SCHED) == "yellow")
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

print("\n=== coverage reads the data, not the run's colour ===")
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "iv.csv"
    p.write_text("date,symbol,x\n2026-10-14,A,1\n2026-10-14,B,1\n2026-10-14,C,1\n2026-10-14,D,1\n"
                 "2026-10-15,A,1\n2026-10-15,B,1\n")
    have, need = guard.coverage("atm", p, at(f"{THU}T15:00").date())
    check("ATM: 2 symbols today against 4 yesterday -> have 2, need 4 (90%, rounded up)", (have, need) == (2, 4))
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
