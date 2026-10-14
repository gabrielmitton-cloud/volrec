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
