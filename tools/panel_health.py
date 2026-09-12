#!/usr/bin/env python3
"""Did the data actually arrive? Read-only. No credentials, no network.

`pressure_test.py` checks that the CODE is right. This checks that the DATA
turned up, which is a different question and the one that fails quietly.

A surface run can be green and commit nothing. Its no-data guard exits 0 with a
message, so from the Actions tab a market holiday and a total collection
failure look identical. Nothing else in the repo would notice, because
freshness.yml historically watched only the ATM panel.

  python tools/panel_health.py

The exit code is the notification: GitHub emails on a failed run and says
nothing about a green one. So anything worth interrupting someone for must exit
non-zero, and anything merely worth reading is printed as WARN and leaves the
exit code alone. Resist the urge to promote warnings; an alert that fires on
ordinary days stops being read.
"""
import ast
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATM = ROOT / "data" / "iv_history.csv"
SURFACE = ROOT / "data" / "surface.csv"


def watchlist():
    """surface.py's SURFACE list, read from the source rather than imported.

    Importing it would pull in record.py and therefore requests, which is an
    absurd dependency for reading eight ticker symbols and would mean a new
    import anywhere in that chain silently breaks the daily health check.
    ast.literal_eval parses without executing, so this stays true to the real
    config with no import side effects and no third-party packages at all.
    """
    tree = ast.parse((ROOT / "surface.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "SURFACE" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("surface.py no longer defines SURFACE at module level; "
                     "panel_health cannot tell which underlyings to expect.")


EXPECTED = watchlist()

# Matches the threshold freshness.yml has always used for the ATM panel. It is
# deliberately loose: the recorders are delayed by GitHub, and a long weekend
# plus a market holiday is four days with no data and nothing wrong.
STALE_DAYS = 5

# surface.yml's first scheduled run. Before this, an absent surface.csv is
# correct rather than broken, and must not fail the check.
SURFACE_START = date(2026, 9, 15)

# Grace after that first run before a missing file counts as a failure. The
# surface job is scheduled 15:40 UTC but GitHub delays it to ~18:45, which is
# after this check's own 17:00 slot, so same-day absence proves nothing.
SURFACE_GRACE_DAYS = 1

fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    warns.append(msg)
    print(f"  WARN  {msg}")


def rows_of(path):
    if not path.exists():
        return None
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def day_span(rows):
    """Sorted distinct dates, and how many days old the newest one is."""
    days = sorted({date.fromisoformat(r["date"]) for r in rows if r.get("date")})
    return days, ((date.today() - days[-1]).days if days else None)


def check_atm():
    print("ATM panel  data/iv_history.csv")
    rows = rows_of(ATM)
    if rows is None:
        return fail("iv_history.csv is missing. This is the irreplaceable panel.")
    if not rows:
        return fail("iv_history.csv has no rows at all.")

    days, age = day_span(rows)
    print(f"  {len(rows)} rows, {len(days)} days, newest {days[-1]} ({age}d old)")
    if age > STALE_DAYS:
        return fail(f"STALE: no ATM snapshot in {age} days. The recorder has "
                    f"stopped. Check the Actions tab - GitHub disables "
                    f"scheduled workflows silently after 60 days of inactivity.")
    print("  OK    fresh")


def check_surface():
    print("\nSurface panel  data/surface.csv")
    rows = rows_of(SURFACE)
    today = date.today()

    if rows is None:
        due = SURFACE_START.toordinal() + SURFACE_GRACE_DAYS
        if today.toordinal() <= due:
            print(f"  PEND  not collected yet; first run due {SURFACE_START}")
            return
        return fail(
            f"surface.csv still does not exist, {(today - SURFACE_START).days} "
            f"days after the first scheduled run on {SURFACE_START}. A green "
            f"surface run that commits nothing looks exactly like this: the "
            f"no-data guard exits 0. Check whether surface.py wrote a file, "
            f"not whether the run was green.")

    if not rows:
        return fail("surface.csv exists but has no rows.")

    days, age = day_span(rows)
    syms = sorted({r["symbol"] for r in rows if r.get("symbol")})
    print(f"  {len(rows)} rows, {len(days)} days, {len(syms)} symbols, "
          f"newest {days[-1]} ({age}d old)")

    if age > STALE_DAYS:
        fail(f"STALE: no surface rows in {age} days.")

    # A contract may legitimately appear on many days, but never twice on one.
    keys = [(r["date"], r["option_symbol"]) for r in rows]
    if len(keys) != len(set(keys)):
        fail(f"{len(keys) - len(set(keys))} duplicate (date, option_symbol) "
             f"rows. The append guard has regressed.")

    # Coverage is judged on the newest day only. Older days may predate a
    # watchlist change and are not evidence of anything breaking now.
    latest = {r["symbol"] for r in rows if r["date"] == days[-1].isoformat()}
    missing = [s for s in EXPECTED if s not in latest]
    if len(latest) * 2 < len(EXPECTED):
        fail(f"only {len(latest)} of {len(EXPECTED)} underlyings on "
             f"{days[-1]}; missing {', '.join(missing)}")
    elif missing:
        warn(f"{days[-1]} is missing {', '.join(missing)}. One quiet name is "
             f"normal; a name absent for several days is not.")

    # H4 needs two consecutive trading days of surface data. Say so plainly,
    # because that milestone is the reason this panel exists at all.
    if len(days) < 2:
        print(f"  INFO  {len(days)} day collected; H4 needs 2 consecutive")
    else:
        gap = (days[-1] - days[-2]).days
        print(f"  INFO  {len(days)} days; newest pair {days[-2]} -> {days[-1]} "
              f"({gap}d apart)" + ("  H4 is testable" if gap <= 4 else
                                   "  gap too wide to be consecutive"))


def main():
    print(f"panel health  {date.today()}\n")
    check_atm()
    check_surface()

    print()
    if fails:
        print(f"UNHEALTHY: {len(fails)} problem(s), {len(warns)} warning(s)")
        return 1
    print(f"HEALTHY ({len(warns)} warning(s))" if warns else "HEALTHY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
