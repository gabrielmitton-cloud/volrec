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
