#!/usr/bin/env python3
"""Refuse a hand push to main while the recorders commit. Called by tools/hooks/pre-push.

WHY (31 Oct 2026): on 15 Oct 2026 a hand push rejected record.yml's snapshot. The rule that followed - no
hand pushes 14:15-15:15 New York on weekdays - lived only in the docs, and its UTC form (18:15-19:15) goes
wrong at the 1 Nov clock change. The window is read from record.py's own slots, in New York time: from 15
min before the ATM trigger to 35 min after the surface trigger (14:15-15:15; 11:15-12:15 on NYSE's early
closes). A rescue push inside it: git push --no-verify, and say why in the commit message.

USAGE
-----
  python3 tools/push_window.py      # exit 1 inside the window (and say until when), 0 outside
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import record  # noqa: E402

NY = ZoneInfo("America/New_York")


def window(now_utc=None):
    """(start, end) in New York time when now falls inside the recorders' commit window, else None."""
    ny = (now_utc or datetime.now(timezone.utc)).astimezone(NY)
    if ny.weekday() >= 5:
        return None
    h, m = record.EARLY_TRIGGER_NY if ny.date() in record.EARLY_CLOSES else record.TRIGGER_NY
    start = ny.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(minutes=15)
    end = start + timedelta(hours=1)
    return (start, end) if start <= ny < end else None


if __name__ == "__main__":
    w = window()
    if w:
        print(f"pre-push: push BLOCKED - {w[0]:%H:%M}-{w[1]:%H:%M} New York is when the recorders commit "
              f"(15 Oct 2026: a hand push rejected a snapshot). Push after {w[1]:%H:%M} New York, or "
              f"git push --no-verify with a reason to rescue a recorder.")
        sys.exit(1)
