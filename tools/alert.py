#!/usr/bin/env python3
"""Phone alerts through Pushover, from the cloud (15 Oct 2026, Gabriel's choice).

Why: the iMessage path (tools/notify.py) sends from Gabriel's Mac, so a closed laptop
sends nothing - exactly when things break. This runs inside GitHub Actions instead.

Three levels, and only RED can wake him (Gabriel, 15 Oct):
  red     data is being lost and can still be saved. Pushover emergency priority: repeats
          every 2 minutes until acknowledged, for at most 1 hour.
  yellow  something is wrong, nothing is lost yet, or a loss that can no longer be fixed.
          High priority: one alert, sound, through quiet hours.
  notice  news worth a sound but not a problem (a verdict recorded, a day recovered).
  green   the daily all-clear. Low priority: no sound. Its ARRIVAL is the point - a day
          with no green means the alert pipe itself is broken.

Every caller must have CONFIRMED the problem from the data before calling this (see
tools/guard.py); a failed step alone is not a reason to page anyone.

Standard library only (freshness.yml installs nothing, on purpose). The keys come from the
environment (GitHub secrets PUSHOVER_TOKEN, PUSHOVER_USER) and are never printed. With no
keys it prints what it would have sent and returns False - it never crashes the job it is in.

  python3 tools/alert.py --level yellow --title "..." --message "..." [--url URL] [--dry-run]
  python3 tools/alert.py --test       # one TEST message at each level
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.pushover.net/1/messages.json"
MAX_MESSAGE, MAX_TITLE, MAX_URL = 1024, 250, 512           # Pushover's limits (pushover.net/api)
RED_RETRY_S, RED_EXPIRE_S = 120, 3600                      # every 2 min, for 1 hour (Gabriel)
LEVELS = {                                                 # level: (priority, title prefix)
    "red": (2, "\U0001F534 ACT NOW"),
    "yellow": (1, "\U0001F7E1 Look today"),
    "notice": (0, "\U0001F535 volrec"),
    "green": (-1, "✅ volrec"),
}
SEND_TRIES, SEND_WAIT_S = 3, 6                             # retry only 5xx / no reply, >= 5 s apart


def payload(level, title, message, url=None):
    """The form fields for one message, without the keys. Pure, so it can be tested."""
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}; use one of {sorted(LEVELS)}")
    prio, prefix = LEVELS[level]
    p = {"title": f"{prefix}: {title}"[:MAX_TITLE], "message": (message or "(no detail)")[:MAX_MESSAGE],
         "priority": str(prio)}
    if prio == 2:
        p["retry"], p["expire"] = str(RED_RETRY_S), str(RED_EXPIRE_S)
    if url:
        p["url"], p["url_title"] = url[:MAX_URL], "Open the run"
    return p


def _post(fields, opener=urllib.request.urlopen):
    """(http status, body). A connection failure is status None."""
    data = urllib.parse.urlencode(fields).encode()
    try:
        with opener(urllib.request.Request(API, data=data, method="POST"), timeout=15) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, ""


def send(level, title, message, url=None, dry_run=False, env=None, opener=urllib.request.urlopen,
         sleep=time.sleep):
    """Send one alert. True only if Pushover accepted it. Never raises on a network problem."""
    env = os.environ if env is None else env
    fields = payload(level, title, message, url)
    token, user = env.get("PUSHOVER_TOKEN", "").strip(), env.get("PUSHOVER_USER", "").strip()
    shown = f"[{level}] {fields['title']} | {fields['message']}"
    if dry_run:
        print(f"DRY RUN, not sent: {shown}")
        return False
    if not token or not user:
        print(f"::warning::Pushover keys are not set; NOT sent: {shown}")
        return False
    for i in range(SEND_TRIES):
        status, body = _post({**fields, "token": token, "user": user}, opener)
        if status == 200:
            print(f"sent: {shown}")
            return True
        if status is not None and 400 <= status < 500:
            # Pushover: never repeat a 4xx (bad key, bad input, quota) - repeating gets the IP blocked.
            errs = ""
            try:
                errs = "; ".join(json.loads(body).get("errors", []))
            except (ValueError, AttributeError):
                pass
            print(f"::error::Pushover refused the alert (HTTP {status}{': ' + errs if errs else ''}); NOT sent: {shown}")
            return False
        if i < SEND_TRIES - 1:
            sleep(SEND_WAIT_S)
    print(f"::error::Pushover did not answer after {SEND_TRIES} tries; NOT sent: {shown}")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--level", choices=sorted(LEVELS))
    ap.add_argument("--title", default="")
    ap.add_argument("--message", default="")
    ap.add_argument("--url")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", action="store_true", help="one TEST message at each level")
    a = ap.parse_args(argv)
    if a.test:
        ok = [send(lv, "TEST", f"Test of the {lv} level. Nothing is wrong. "
                   + ("Tap Acknowledge to stop the repeats." if lv == "red" else ""),
                   a.url, a.dry_run) for lv in ("green", "notice", "yellow", "red")]
        return 0 if all(ok) or a.dry_run else 1
    if not a.level or not a.title:
        ap.error("--level and --title are required (or use --test)")
    sent = send(a.level, a.title, a.message, a.url, a.dry_run)
    return 0 if sent or a.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
