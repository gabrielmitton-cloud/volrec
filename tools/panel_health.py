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
import re
import sys
from datetime import date, datetime, timedelta, timezone
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

# A quote carried forward from hours earlier is still a quote, and the feed hands
# it over without comment. One contract in a thousand is noise; a tenth of the
# panel means the hedged gain is measuring a different interval than the spot move
# it is hedged against. Measured 0.4% beyond 5 minutes on 14-15 Sep 2026, so this
# has real headroom and should stay quiet unless something changes.
STALE_QUOTE_MIN = 15
STALE_QUOTE_PCT = 2.0

# US equity-market closures. The single list in this repo: tools/model_gap.py
# imports it rather than keeping a second copy, and pressure_test.py checks that
# it stays that way. Columbus Day and Veterans Day are deliberately absent
# because the stock market trades on both.
US_MARKET_HOLIDAYS = {
    date(2026, 11, 26), date(2026, 12, 25), date(2027, 1, 1), date(2027, 1, 18),
    date(2027, 2, 15), date(2027, 4, 2), date(2027, 5, 31), date(2027, 6, 18),
    date(2027, 7, 5), date(2027, 9, 6), date(2027, 11, 25), date(2027, 12, 24),
    date(2028, 1, 17), date(2028, 2, 21), date(2028, 4, 14), date(2028, 5, 29),
    date(2028, 6, 19), date(2028, 7, 4), date(2028, 9, 4), date(2028, 11, 23),
    date(2028, 12, 25), date(2029, 1, 1),
}

# surface.yml's first scheduled run. Before this, an absent surface.csv is
# correct rather than broken, and must not fail the check.
SURFACE_START = date(2026, 9, 14)

# The hour (UTC) by which a weekday's surface rows should have landed. The job
# is scheduled 15:40 but GitHub delays it to ~18:45 in practice, so before this
# hour a same-day absence proves nothing and must not fail. freshness.yml runs
# twice daily for exactly this reason: 17:00 is too early to judge the surface
# and 21:00 is late enough.
SURFACE_LANDED_HOUR_UTC = 20


def now_utc():
    """Single clock seam. Everything derives from this, so the checker behaves
    identically on a UTC runner and on a laptop in California, and so the tests
    can pin a moment without touching the system clock."""
    return datetime.now(timezone.utc)

fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    warns.append(msg)
    print(f"  WARN  {msg}")


def _quote_minutes(stamp):
    """Minutes past midnight UTC for an RFC-3339 stamp, or None if unparseable.

    The feed writes nanoseconds, which datetime cannot parse, so they are trimmed
    to microseconds rather than the whole field being discarded.
    """
    if not stamp:
        return None
    t = stamp.strip().replace("Z", "+00:00")
    t = re.sub(r"\.(\d{6})\d+", r".\1", t)
    try:
        d = datetime.fromisoformat(t).astimezone(timezone.utc)
    except ValueError:
        return None
    return d.hour * 60 + d.minute + d.second / 60.0


def session_bounds_utc(day):
    """(open, close) of the US equity session on `day`, in UTC minutes.

    Cron is UTC and the session is not: 13:30-20:00 UTC under DST, 14:30-21:00
    from the first Sunday in November. Hard-coding either one means a check that
    is correct for half the year, which is worse than no check, so the shift is
    read from the zone database rather than assumed. Returns None if the zone
    database is unavailable, and every caller treats that as "cannot judge".
    """
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        return None
    out = []
    for hh, mm in ((9, 30), (16, 0)):
        u = datetime(day.year, day.month, day.day, hh, mm, tzinfo=et).astimezone(timezone.utc)
        out.append(u.hour * 60 + u.minute)
    return tuple(out)


# A trading day that is gone, and that has been accepted as gone. Without this the
# missed-day check below fails on every run, forever, over a day nobody can bring
# back - and an alarm that fires every day stops being read, which is how the next
# real miss gets ignored. Adding a date here is a decision about irreplaceable data,
# so each one carries the reason it was accepted and who accepted it.
ACCEPTED_GAPS = {
    date(2026, 9, 16): ("GitHub dropped both scheduled runs. The cron was edited at "
                        "15:49 UTC, after the old slot had passed and before the new "
                        "one took effect, so the day fell between schedules. Accepted "
                        "by Gabriel the same evening rather than dispatching after the "
                        "close, which would have written a non-comparable snapshot into "
                        "the panel."),
}


def report_missed(kind, missed):
    """Fail on trading days lost silently; note the ones already accepted.

    An accepted gap stays visible on every run - it is still missing data, and the
    write-up has to say so - but it does not fail the check, so the daily alarm keeps
    meaning "something happened today".
    """
    for d in missed:
        if d in ACCEPTED_GAPS:
            print(f"  INFO  {d.isoformat()} has no {kind} data. Accepted: {ACCEPTED_GAPS[d]}")
    unexplained = [d for d in missed if d not in ACCEPTED_GAPS]
    if unexplained:
        fail(f"{len(unexplained)} trading day(s) with no {kind} data: "
             f"{', '.join(d.isoformat() for d in unexplained)}. Every trading day is "
             f"irreplaceable and by the close it is gone. A scheduled trigger that "
             f"GitHub drops leaves NO failed run and no trace in the Actions tab, "
             f"so this check is the only thing that notices. If the market is "
             f"still open, dispatch the workflow by hand now. If the day is already "
             f"lost, record it in ACCEPTED_GAPS with the reason.")


def missed_trading_days(newest, floor=None):
    """Trading days after `newest` that have had their chance to land and did not.

    THE FAILURE THIS EXISTS FOR
    ---------------------------
    On 16 September 2026 no recorder ran at all - the scheduled trigger was
    dropped - and this file reported HEALTHY, because the newest day was one day
    old and STALE_DAYS is five. A silent miss is the worst failure mode there is:
    every trading day is irreplaceable, and by the close it is gone.

    So a missed trading day FAILS rather than warns. GitHub only emails on a
    failed run, so a warning would reach nobody, and a miss is both rare and
    actionable - from November the early freshness slot runs an hour before the
    close, which is enough time to dispatch the recorder by hand. If this turns
    out to fire on ordinary days it should be relaxed to a warning, but it has
    not fired on an ordinary day yet.

    Today counts only once SURFACE_LANDED_HOUR_UTC has passed, because before
    that an absence proves nothing.
    """
    now = now_utc()
    today = now.date()
    out, d = [], newest + timedelta(days=1)
    while d <= today:
        if (d.weekday() < 5 and d not in US_MARKET_HOLIDAYS
                and (floor is None or d >= floor)
                and (d < today or now.hour >= SURFACE_LANDED_HOUR_UTC)):
            out.append(d)
        d += timedelta(days=1)
    return out


def check_landing(rows, days):
    """When did the day's snapshot actually land, and is that inside the session?

    The cron is fixed; GitHub's delay is not. Over six days it ran 3h06m to
    4h24m, which once put a snapshot six minutes before the close. A snapshot
    taken after the close is closing quotes filed under a mid-session label, and
    nothing downstream can tell. That is worth an email, so it FAILS; ordinary
    drift only warns.
    """
    newest = [r for r in rows if r["date"] == days[-1].isoformat()]
    stamps = sorted(t for t in (_quote_minutes(r.get("quote_time")) for r in newest)
                    if t is not None)
    if len(stamps) < 10:
        return
    mid = stamps[len(stamps) // 2]
    print(f"  INFO  landed {int(mid)//60:02d}:{int(mid)%60:02d} UTC "
          f"(median quote time on {days[-1]})")

    bounds = session_bounds_utc(days[-1])
    if bounds:
        o, c = bounds
        if mid < o or mid > c:
            where = "before the open" if mid < o else "AFTER THE CLOSE"
            fail(f"{days[-1]} landed {int(mid)//60:02d}:{int(mid)%60:02d} UTC, "
                 f"{where} ({o//60:02d}:{o%60:02d}-{c//60:02d}:{c%60:02d} UTC "
                 f"that day). Those are not mid-session quotes and nothing "
                 f"downstream can tell. Move the cron inside the window both "
                 f"DST regimes share - see record.yml.")
        elif c - mid < 20:
            warn(f"{days[-1]} landed {c - int(mid)} min before the close. The "
                 f"delay is drifting; check the cron before it lands outside.")

    # Drift against the days already collected, which is what breaks comparability.
    prior = []
    for d in days[:-1]:
        ts = sorted(t for t in (_quote_minutes(r.get("quote_time"))
                                for r in rows if r["date"] == d.isoformat())
                    if t is not None)
        if ts:
            prior.append(ts[len(ts) // 2])
    if prior:
        ref = sorted(prior)[len(prior) // 2]
        if abs(mid - ref) > 60:
            warn(f"{days[-1]} landed {abs(int(mid - ref))} min "
                 f"{'later' if mid > ref else 'earlier'} than the median of the "
                 f"{len(prior)} prior day(s). A drifting snapshot time is a "
                 f"comparability problem; the date-clustered tests absorb it, "
                 f"the pooled ones do not.")


def rows_of(path):
    if not path.exists():
        return None
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def day_span(rows):
    """Sorted distinct dates, and how many days old the newest one is."""
    days = sorted({date.fromisoformat(r["date"]) for r in rows if r.get("date")})
    return days, ((now_utc().date() - days[-1]).days if days else None)


def check_atm():
    print("ATM panel  data/iv_history.csv")
    rows = rows_of(ATM)
    if rows is None:
        return fail("iv_history.csv is missing. This is the irreplaceable panel.")
    if not rows:
        return fail("iv_history.csv has no rows at all.")

    days, age = day_span(rows)
    print(f"  {len(rows)} rows, {len(days)} days, newest {days[-1]} ({age}d old)")
    check_landing(rows, days)
    report_missed("ATM", missed_trading_days(days[-1], floor=None))
    if age > STALE_DAYS:
        return fail(f"STALE: no ATM snapshot in {age} days. The recorder has "
                    f"stopped. Check the Actions tab - GitHub disables "
                    f"scheduled workflows silently after 60 days of inactivity.")
    print("  OK    fresh")


def check_surface():
    print("\nSurface panel  data/surface.csv")
    rows = rows_of(SURFACE)
    now = now_utc()
    today = now.date()

    if rows is None:
        # Judge only once the day's run has had time to land. Before the first
        # scheduled run, and before the landing hour on the day itself, an
        # absent file is the expected state rather than evidence of anything.
        undue = (today < SURFACE_START or
                 (today == SURFACE_START and now.hour < SURFACE_LANDED_HOUR_UTC))
        if undue:
            print(f"  PEND  not collected yet; first run due {SURFACE_START} "
                  f"(judged from {SURFACE_LANDED_HOUR_UTC:02d}:00 UTC)")
            return
        late = (today - SURFACE_START).days
        return fail(
            f"surface.csv still does not exist, "
            f"{'later the same day as' if late == 0 else f'{late} days after'} "
            f"the first scheduled run on {SURFACE_START}. A green surface run "
            f"that commits nothing looks exactly like this: the no-data guard "
            f"exits 0. Check whether surface.py wrote a file, not whether the "
            f"run was green.")

    if not rows:
        return fail("surface.csv exists but has no rows.")

    days, age = day_span(rows)
    syms = sorted({r["symbol"] for r in rows if r.get("symbol")})
    print(f"  {len(rows)} rows, {len(days)} days, {len(syms)} symbols, "
          f"newest {days[-1]} ({age}d old)")
    check_landing(rows, days)
    report_missed("surface", missed_trading_days(days[-1], floor=SURFACE_START))

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

    # Within one day, every contract should carry nearly the same quote time.
    # The across-day spread is pressure_test.py's warning; this is the other half.
    newest = [r for r in rows if r["date"] == days[-1].isoformat()]
    stamps = [_quote_minutes(r.get("quote_time")) for r in newest]
    stamps = [t for t in stamps if t is not None]
    if len(stamps) >= 10:
        mid = sorted(stamps)[len(stamps) // 2]
        stale = [t for t in stamps if mid - t > STALE_QUOTE_MIN]
        pct = 100.0 * len(stale) / len(stamps)
        worst = (mid - min(stamps)) if stamps else 0
        print(f"  INFO  quote times on {days[-1]}: {pct:.1f}% more than "
              f"{STALE_QUOTE_MIN} min behind the median, worst {worst:.0f} min")
        if pct > STALE_QUOTE_PCT:
            warn(f"{pct:.1f}% of {days[-1]} rows are stale by over "
                 f"{STALE_QUOTE_MIN} min (worst {worst:.0f} min). A hedged gain "
                 f"on a stale quote measures a different interval than the spot "
                 f"move hedging it. Check whether it concentrates in the "
                 f"low-volume tercile before trusting H4c.")

    # The wide band (added 17 Sep 2026) is a SENSITIVITY dataset, not part of the
    # registered study, so it can only warn - never fail. But it must not be able
    # to go quiet silently either: that is precisely how 16 Sep was lost.
    wide = ROOT / "data" / "surface_wide.csv"
    if wide.exists():
        wrows = rows_of(wide) or []
        wdays = sorted({r["date"] for r in wrows if r.get("date")})
        if wdays and wdays[-1] < days[-1].isoformat():
            warn(f"surface_wide.csv stops at {wdays[-1]} but the registered surface "
                 f"reaches {days[-1]}. The wide pass is failing quietly; check the "
                 f"surface run's log for 'wide pass failed'.")
        elif wdays:
            print(f"  INFO  wide band: {len(wrows)} rows over {len(wdays)} day(s), "
                  f"newest {wdays[-1]}")
    elif days[-1] >= date(2026, 9, 18):
        warn("surface_wide.csv does not exist, but the wide pass has been live "
             "since 18 Sep 2026. It should appear on any day a high-volatility "
             "name needed widening.")

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
    print(f"panel health  {now_utc():%Y-%m-%d %H:%M} UTC\n")
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
