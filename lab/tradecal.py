"""lab/ - the trade calendar (EXPLORATORY). Standard monthly options expire on the third Friday,
or the trading day before it when that Friday is a holiday (Good Friday). Each trade enters on the
first trading day after a monthly expiry and holds to the next one."""
from datetime import date, timedelta

FIRST_ENTRY, LAST_EXPIRY = "2016-01-19", "2026-08-31"


def third_friday(y, m):
    d = date(y, m, 1)
    d += timedelta((4 - d.weekday()) % 7)
    return d + timedelta(14)


def monthly_expiry(y, m, trading):
    d = third_friday(y, m)
    while d.isoformat() not in trading:
        d -= timedelta(1)
    return d.isoformat()


def entries(trading_days):
    trading = set(trading_days)
    days = sorted(trading)
    out = []
    y, m = int(days[0][:4]), int(days[0][5:7])
    while True:
        e0 = monthly_expiry(y, m, trading) if third_friday(y, m).isoformat() >= days[0] else None
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        if third_friday(y2, m2).isoformat() > days[-1]:
            return out
        if e0:
            nxt = [x for x in days if x > e0]
            e1 = monthly_expiry(y2, m2, trading)
            if nxt and nxt[0] >= FIRST_ENTRY and e1 <= LAST_EXPIRY:
                out.append((nxt[0], e1))
        y, m = y2, m2


# Registered stress months (crash replays and real daily marks for the margin path). August 2015
# predates the daily closes (Alpaca sip starts 4 Jan 2016), so its days are its weekdays - there
# were no market holidays that August.
STRESS_MONTHS = ("2015-08", "2018-02", "2018-12", "2020-03", "2022-06", "2024-08", "2025-04")


def stress_days(trading_days):
    trading = sorted(trading_days)
    out = [d for d in trading if d[:7] in STRESS_MONTHS]
    d = date(2015, 8, 1)
    while d.month == 8:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(1)
    return sorted(out)


def weekly_days(trading_days):
    """Every trading Wednesday from the first trade to the last expiry (Break-Even VIX samples)."""
    return [d for d in sorted(trading_days)
            if "2016-01-06" <= d <= LAST_EXPIRY and date.fromisoformat(d).weekday() == 2]


# NYSE 1 p.m. early closes, 2015-2026 (the day after Thanksgiving; Christmas Eve and July 3rd when
# they fall on a trading weekday). Added 14 Oct 2026 AFTER the first run: 24 Dec 2018's 14:30 entry
# found no quotes, which dropped December 2018 - a crash month - for all five funds.
EARLY_CLOSES = {
    "2015-11-27", "2015-12-24", "2016-11-25", "2017-07-03", "2017-11-24", "2018-07-03", "2018-11-23",
    "2018-12-24", "2019-07-03", "2019-11-29", "2019-12-24", "2020-11-27", "2020-12-24", "2021-11-26",
    "2022-11-25", "2023-07-03", "2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24", "2025-07-03",
    "2025-11-28", "2025-12-24", "2026-11-27", "2026-12-24"}


def slot(day, hhmm):
    """The New York time actually used: on a half-day, entries and weekly samples at 11:30 (as the
    recorder does) and daily marks at 12:55 (five minutes before the 1 p.m. close)."""
    if day not in EARLY_CLOSES:
        return hhmm
    return "12:55" if hhmm == "15:55" else "11:30"
