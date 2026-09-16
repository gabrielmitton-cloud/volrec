#!/usr/bin/env python3
"""Which model assumption produces the 1.7-point implied-volatility gap?

THE QUESTION THIS CLOSES
------------------------
`tools/bloomberg_compare.py` found the free feed's prices matching Bloomberg's to
within half a bid-ask spread while implied volatilities differed by about 1.7
points. `tools/iv_convention.py` then showed the gap survives re-inverting
Bloomberg's OWN quotes with this project's Black-76, so it is a difference between
models and not between data sources. It did not say WHICH assumption differs.

This does. Black-76 has exactly four inputs behind a price: the forward, the rate,
the strike, and the time to expiry. The strike is printed. The rate is printed. The
forward is printed, and can also be recovered from Bloomberg's own call and put mids
by put-call parity. That leaves time, which is never printed as a year fraction -
only as a day count - and which each vendor annualises by its own convention.

So invert the question. Instead of asking what volatility reproduces Bloomberg's
price, ask what TIME reproduces Bloomberg's own printed volatility from Bloomberg's
own printed price:

    solve T*  such that  Black76(F, K, T*, r, IVM) = Bloomberg's mid

and then report T* two ways: as a divisor over calendar days, and as a divisor over
business days. A convention shows up as a divisor that is STABLE ACROSS MATURITIES.
One that drifts with maturity is not the explanation.

WHAT IT FOUND, 16 September 2026
--------------------------------
The business-day divisor is stable at ~251 and the calendar-day divisor is not
(338 at one month, 345 at two). Re-inverting on business days over 252 collapses
the gap from +1.80 to +0.08 volatility points on TSLA. Bloomberg's IVM is on a
252 business-day clock; Alpaca's, and therefore this project's, is on a 365
calendar-day clock. Neither is wrong. They are different conventions, and the whole
1.7 points is the difference between them.

The `--american` column is the other candidate named in HANDOFF 17, priced as a
Cox-Ross-Rubinstein tree on spot with the carry implied by the printed forward. It
is reported so the comparison is on the record, not because it explains anything:
it moves TSLA's one-month gap by 0.00 points, which it must, because an American
call on a name with no dividend is a European call.

LIMITS, STATE THEM IN ANY WRITE-UP
----------------------------------
- Out-of-the-money contracts only, and cheap ones dropped: Black-76 is European.
- Two symbols, two expiries, one day. The divisor is estimated, not read off a
  Bloomberg document. It is consistent with 252 and inconsistent with any fixed
  calendar divisor; that is the claim, and it is as far as this data goes.
- Bloomberg's terms restrict redistribution. Exports stay outside the repository,
  only aggregates are printed, and any published figure carries
  "Source: Bloomberg Finance L.P.".

USAGE
-----
  python3 tools/model_gap.py --date 2026-09-15
  python3 tools/model_gap.py --date 2026-09-15 --american      # adds the tree column
"""
import argparse
import math
import os
import re
import statistics as st
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bloomberg_compare import ROOT, DEFAULT_DIR, read_sheet, num, surface_rows  # noqa: E402
from iv_convention import black76, implied_vol, MIN_MID                          # noqa: E402

BUSINESS_YEAR = 252.0
CALENDAR_YEAR = 365.0
MIN_CONTRACTS = 20

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

# US equity-market closures. Only the ones that can fall inside a window this tool
# is pointed at; Columbus Day and Veterans Day are deliberately absent because the
# stock market trades on both.
HOLIDAYS = {
    date(2026, 11, 26), date(2026, 12, 25), date(2027, 1, 1), date(2027, 1, 18),
    date(2027, 2, 15), date(2027, 4, 2), date(2027, 5, 31), date(2027, 6, 18),
    date(2027, 7, 5), date(2027, 9, 6), date(2027, 11, 25), date(2027, 12, 24),
}


def expiry_date(label):
    """'16-Oct-26' -> date(2026, 10, 16)."""
    d, m, y = label.split("-")
    return date(2000 + int(y), _MONTHS[m], int(d))


def business_days(start, end):
    """Trading days after `start` up to and including `end`."""
    n, cur = 0, start + timedelta(days=1)
    while cur <= end:
        if cur.weekday() < 5 and cur not in HOLIDAYS:
            n += 1
        cur += timedelta(days=1)
    return n


def omon_blocks(path):
    """Every expiry block: label -> {dte, rate, fwd, quotes}.

    Block headers look like
        16-Oct-26 (31d); CSize 100; R 4.26; IFwd 358.17
    and are followed by strike rows carrying calls on the left, puts on the right.
    """
    out, cur = {}, None
    for r in read_sheet(path):
        first = (r[0] if r else "") or ""
        if "CSize" in first:
            m = re.match(r"(\d{1,2}-\w{3}-\d{2})\s*\((\d+)d\);.*?\bR\s+([\d.]+)"
                         r".*?IFwd\s+([\d.]+)", first.strip())
            cur = m.group(1) if m else None
            if m:
                out[cur] = {"dte": int(m.group(2)), "rate": float(m.group(3)) / 100,
                            "fwd": float(m.group(4)), "quotes": {}}
            continue
        if not cur or not re.match(r"^\d+(\.\d+)?$", first):
            continue
        for off, typ in ((0, "C"), (7, "P")):
            if len(r) < off + 7:
                continue
            k = num(r[off])
            if k is None:
                continue
            out[cur]["quotes"][(typ, round(k, 2))] = {
                "bid": num(r[off + 2]), "ask": num(r[off + 3]), "ivm": num(r[off + 5])}
    return out


def solve_time(kind, price, f, k, r, vol):
    """Year fraction that makes Black-76 at `vol` reproduce `price`. Bisection."""
    lo, hi = 1e-5, 20.0
    if black76(kind, f, k, lo, r, vol) >= price or black76(kind, f, k, hi, r, vol) <= price:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if black76(kind, f, k, mid, r, vol) < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def parity_forward(quotes, f_hint, r, t):
    """Forward implied by Bloomberg's own call and put mids, near the money."""
    out = []
    for (typ, k) in quotes:
        if typ != "C":
            continue
        c, p = quotes.get(("C", k)), quotes.get(("P", k))
        if not c or not p or None in (c["bid"], c["ask"], p["bid"], p["ask"]):
            continue
        cm, pm = (c["bid"] + c["ask"]) / 2, (p["bid"] + p["ask"]) / 2
        if min(cm, pm) < MIN_MID or abs(k - f_hint) / f_hint > 0.10:
            continue
        out.append(k + (cm - pm) * math.exp(r * t))
    return st.median(out) if out else None


def crr(kind, s, k, t, r, q, vol, steps=300):
    """American option on spot by a Cox-Ross-Rubinstein tree."""
    dt = t / steps
    u = math.exp(vol * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    if not 0.0 < p < 1.0:
        return None
    disc = math.exp(-r * dt)
    v = [max(0.0, (s * u ** j * d ** (steps - j) - k) if kind == "C"
             else (k - s * u ** j * d ** (steps - j))) for j in range(steps + 1)]
    for i in range(steps - 1, -1, -1):
        for j in range(i + 1):
            v[j] = disc * (p * v[j + 1] + (1 - p) * v[j])
            sp = s * u ** j * d ** (i - j)
            v[j] = max(v[j], (sp - k) if kind == "C" else (k - sp))
    return v[0]


def crr_iv(kind, price, s, k, t, r, q):
    lo, hi = 0.05, 3.0
    a, b = crr(kind, s, k, t, r, q, lo), crr(kind, s, k, t, r, q, hi)
    if a is None or b is None or not a < price < b:
        return None
    for _ in range(35):
        mid = (lo + hi) / 2
        pm = crr(kind, s, k, t, r, q, mid)
        if pm is None:
            return None
        if pm < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", required=True, help="trading day, YYYY-MM-DD")
    ap.add_argument("--dir", default=str(DEFAULT_DIR))
    ap.add_argument("--american", action="store_true",
                    help="also invert under a CRR American tree (slow)")
    a = ap.parse_args()

    folder = Path(os.path.expanduser(a.dir)).resolve()
    if ROOT in folder.parents or folder == ROOT:
        sys.exit("Refusing to read exports from inside the repository.")

    rows = surface_rows(a.date)
    spot = {r["symbol"]: float(r["spot"]) for r in rows if r["spot"]}
    asof = date.fromisoformat(a.date)

    print(f"What time base reproduces Bloomberg's own volatility? {a.date}\n")
    head = (f"{'sym':6}{'expiry':11}{'cal':>4}{'bus':>4}{'n':>4}{'IVM':>7}"
            f"{'gap 365':>9}{'gap 252':>9}{'gap 252+F':>11}{'cal div':>9}{'bus div':>9}")
    if a.american:
        head += f"{'gap Amer':>10}"
    print(head)

    seen = False
    for path in sorted(folder.glob(f"*_OMON_{a.date}.xlsx")):
        symbol = path.name.split("_")[0]
        s = spot.get(symbol)
        if s is None:
            print(f"{symbol:6}  not in the recorded surface for {a.date}")
            continue
        for label, blk in sorted(omon_blocks(path).items(), key=lambda x: x[1]["dte"]):
            f_print, r, dte = blk["fwd"], blk["rate"], blk["dte"]
            t_cal = dte / CALENDAR_YEAR
            nbus = business_days(asof, expiry_date(label))
            t_bus = nbus / BUSINESS_YEAR
            f_par = parity_forward(blk["quotes"], f_print, r, t_cal) or f_print
            carry = r - math.log(f_print / s) / t_cal

            g365, g252, g252f, cdiv, bdiv, ivm, gamer = [], [], [], [], [], [], []
            for (typ, k), q in sorted(blk["quotes"].items()):
                if None in (q["bid"], q["ask"], q["ivm"]) or q["ivm"] <= 0:
                    continue
                mid = (q["bid"] + q["ask"]) / 2
                if mid < MIN_MID:
                    continue
                if (typ == "C" and k <= f_print) or (typ == "P" and k >= f_print):
                    continue                     # out of the money only
                bench = q["ivm"]
                iv = implied_vol(typ, mid, f_print, k, t_cal, r)
                if iv is None:
                    continue
                ivm.append(bench)
                g365.append(iv * 100 - bench)
                for tt, ff, box in ((t_bus, f_print, g252), (t_bus, f_par, g252f)):
                    x = implied_vol(typ, mid, ff, k, tt, r)
                    if x is not None:
                        box.append(x * 100 - bench)
                ts = solve_time(typ, mid, f_print, k, r, bench / 100)
                if ts:
                    cdiv.append(dte / ts)
                    bdiv.append(nbus / ts)
                if a.american:
                    av = crr_iv(typ, mid, s, k, t_cal, r, carry)
                    if av:
                        gamer.append(av * 100 - bench)

            if len(g365) < MIN_CONTRACTS:
                continue
            seen = True
            m = lambda x: st.median(x) if x else float("nan")   # noqa: E731
            line = (f"{symbol:6}{label:11}{dte:>4}{nbus:>4}{len(g365):>4}{m(ivm):>7.1f}"
                    f"{m(g365):>+9.2f}{m(g252):>+9.2f}{m(g252f):>+11.2f}"
                    f"{m(cdiv):>9.1f}{m(bdiv):>9.1f}")
            if a.american:
                line += f"{m(gamer):>+10.2f}"
            print(line)

    if not seen:
        print("\nNothing measurable. Widen the export's strike count and pull again.")
        return 1
    print("\nGaps are medians in volatility points, ours minus Bloomberg's IVM,")
    print("out-of-the-money contracts only. '252+F' also swaps the printed forward")
    print("for the one implied by Bloomberg's own call and put mids.")
    print("'cal div' and 'bus div' are the annualisation divisors implied by the")
    print("solved time. A convention is the one whose divisor holds across maturities.")
    print("Bloomberg figures: Source: Bloomberg Finance L.P.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
