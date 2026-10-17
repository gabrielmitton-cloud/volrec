#!/usr/bin/env python3
"""A SECOND, INDEPENDENT implementation of the numbers behind the registered readings (17 Oct 2026).

Written from the published method text alone - Cboe's "Volatility Index Mathematics Methodology"
(s3: forward, K0, the out-of-the-money walk, the variance sum, the 30-day blend), H3's registered quote
rule, H5e's skip rule, and Cboe's ETF-index rules for H7 - without reading the project's estimator code.
It imports NOTHING from this project: standard library only, which a pressure-test lint enforces, so a
mistake in modelfree.py or tools/ovx_replicate.py cannot be shared by this file.

tools/independent_check.py runs both, value by value at full precision, and reports how many agree.
First run, 17 Oct 2026: H3/H5e 544 of 544 values agree; H7 22 of 22 readings agree (largest difference
0.00005 points). That agreement is the paper's reproducibility claim (section 5); this file is the
evidence.

KNOWN DIFFERENCE, documented rather than hidden: when two strikes tie EXACTLY on |call - put|, the
strike that sets the forward is chosen by floating-point noise in both versions, and they can pick
different ones. Seen once in 184 band readings to 16 Oct (IWM, 8 Oct 2026, 29-day leg, strikes 277 and
279, both 0.99 apart): 21.4942 here against 21.4950, i.e. 0.0008 vol points. No verdict reads IWM.

  PART 1 - H3 and H5e, from data/surface.csv (+ data/surface_wide.csv). Whole days over 365, one rate.
    rule "reg"   H3's registered quote rule: a quote counts when its mid is positive, so a zero-bid stub
                 counts at half its ask.
    rule "skip"  H5e (registered 23 Sep 2026): every out-of-the-money zero-bid quote skipped, no stop.
    rule "cboe"  Cboe's rule: zero bids skipped, and nothing beyond two consecutive zero bids.
    Expiries: the last at or under 30 days and the first over it (else the nearest, scaled).
  PART 2 - H7, from data/surface_monthly.csv and OPRA cbbo-1m files (licensed; read from a directory
    given on the command line, never copied). Minutes to the 16:00 New York settlement over a
    525,600-minute year; a quote missing either side is a zero bid, one missing both is no quote;
    the rate a bond-equivalent yield converted to continuous.

  python tools/independent_replica.py h3 [--rate 3.910]
  python tools/independent_replica.py h7 OPRA_DIR [--rate 3.910]
Output is aggregates only (index levels). Data provided by Databento (OPRA consolidated NBBO) for part 2.
"""
import csv
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = 30
FROZEN_RATE_PCT = 3.910          # DGS1MO on 10 Sep 2026, the rate of record (an INPUT, shared on purpose)


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _var_sum(used, F, K0, T, R):
    """Cboe s3: sigma^2 = (2/T) sum dK/K^2 e^(RT) Q(K) - (1/T)(F/K0 - 1)^2, dK over the strikes used."""
    ks = sorted(used)
    if len(ks) < 3:
        return None
    tot = 0.0
    for i, k in enumerate(ks):
        dk = ks[1] - ks[0] if i == 0 else ks[-1] - ks[-2] if i == len(ks) - 1 else (ks[i + 1] - ks[i - 1]) / 2
        tot += dk / k ** 2 * math.exp(R * T) * used[k]
    return 2 / T * tot - (F / K0 - 1) ** 2 / T


# ------------------------------------------------ PART 1: H3 / H5e ------------------------------------------------
def quotes(rows):
    """rows -> ({expiry: {strike: {'C'|'P': (bid, mid)}}}, {expiry: dte}). Mid is (bid + ask)/2, bid 0 if blank."""
    book, dte = defaultdict(lambda: defaultdict(dict)), {}
    for r in rows:
        ask = _f(r["ask"])
        if ask is None:
            continue
        bid = _f(r["bid"]) or 0.0
        book[r["expiration"]][float(r["strike"])][r["type"]] = (bid, (bid + ask) / 2)
        dte[r["expiration"]] = int(r["dte"])
    return book, dte


def sigma2(book, T, R, rule):
    """One expiry's variance under `rule` ('reg', 'skip' or 'cboe' - see the module text)."""
    both = [k for k, s in book.items() if "C" in s and "P" in s and s["C"][1] > 0 and s["P"][1] > 0]
    if not both:
        return None
    kf = min(both, key=lambda k: abs(book[k]["C"][1] - book[k]["P"][1]))
    F = kf + math.exp(R * T) * (book[kf]["C"][1] - book[kf]["P"][1])
    below = [k for k in book if k <= F]
    if not below:
        return None
    K0 = max(below)
    used = {}
    for side, walk in (("P", sorted((k for k in book if k < K0), reverse=True)), ("C", sorted(k for k in book if k > K0))):
        zeros = 0
        for k in walk:
            s = book[k].get(side)
            if s is None:
                continue
            bid, mid = s
            if rule == "reg":
                if mid > 0:
                    used[k] = mid
            elif bid > 0:
                zeros = 0
                used[k] = mid
            elif rule == "cboe":
                zeros += 1
                if zeros >= 2:
                    break
    ok = (lambda s: s[1] > 0) if rule == "reg" else (lambda s: s[0] > 0)
    at = [book[K0][s][1] for s in ("C", "P") if s in book[K0] and ok(book[K0][s])]
    if at:
        used[K0] = sum(at) / len(at)
    return _var_sum(used, F, K0, T, R)


def pick_pair(dte):
    """The last expiry at or under 30 days and the first over it; else the single nearest."""
    under = sorted((e for e in dte if dte[e] <= TARGET), key=lambda e: dte[e])
    over = sorted((e for e in dte if dte[e] > TARGET), key=lambda e: dte[e])
    if under and over:
        return under[-1], over[0]
    near = min(dte, key=lambda e: abs(dte[e] - TARGET)) if dte else None
    return (near,) if near else ()


def vol30(book, dte, pair, R, rule):
    """30-day vol in points: the two legs blended in total variance, or one leg scaled if no bracket."""
    if len(pair) == 1:
        s = sigma2(book[pair[0]], dte[pair[0]] / 365, R, rule)
        return 100 * math.sqrt(s) if s and s > 0 else None
    if len(pair) != 2:
        return None
    (e1, e2), (d1, d2) = pair, (dte[pair[0]], dte[pair[1]])
    s1, s2 = sigma2(book[e1], d1 / 365, R, rule), sigma2(book[e2], d2 / 365, R, rule)
    if s1 is None or s2 is None:
        return None
    v = (d1 / 365 * s1 * (d2 - TARGET) / (d2 - d1) + d2 / 365 * s2 * (TARGET - d1) / (d2 - d1)) * 365 / TARGET
    return 100 * math.sqrt(v) if v > 0 else None


def h3_day(band_rows, wide_rows, R):
    """One (date, symbol): the band reading under 'reg' and 'cboe', and - when wide rows exist - the wide
    reading (band + wide contracts, on the band's own pair) under 'reg', 'skip' and 'cboe'. Points."""
    book, dte = quotes(band_rows)
    pair = pick_pair(dte)
    out = {"reg": vol30(book, dte, pair, R, "reg"), "reg_cboe": vol30(book, dte, pair, R, "cboe"),
           "legs": [dte[e] for e in pair]}
    if wide_rows:
        seen = {r["option_symbol"] for r in band_rows}
        wbook, wdte = quotes(list(band_rows) + [r for r in wide_rows if r["option_symbol"] not in seen])
        for rule in ("reg", "skip", "cboe"):
            out["wide_" + rule] = vol30(wbook, wdte, pair, R, rule)
    return out


def h3_all(R, through=None):
    """{(date, symbol): h3_day(...)} over every recorded band day (after-close days included - this is
    arithmetic, not a reading; the readers drop them)."""
    band, wide = defaultdict(list), defaultdict(list)
    for r in csv.DictReader((ROOT / "data/surface.csv").open(newline="")):
        if not through or r["date"] <= through:
            band[(r["date"], r["symbol"])].append(r)
    p = ROOT / "data/surface_wide.csv"
    if p.exists():
        for r in csv.DictReader(p.open(newline="")):
            if not through or r["date"] <= through:
                wide[(r["date"], r["symbol"])].append(r)
    return {k: h3_day(v, wide.get(k, []), R) for k, v in sorted(band.items())}


# ------------------------------------------------ PART 2: H7 ------------------------------------------------
N30, N365 = TARGET * 1440, 365 * 1440


def bey_to_continuous(bey):
    """Cboe s2.1: bond-equivalent yield -> APY = (1 + BEY/2)^2 - 1 -> continuous ln(1 + APY)."""
    return 2 * math.log(1 + bey / 2)


def settle_utc(e):
    """16:00 New York on expiry date e, in UTC. US daylight time: 2nd Sunday of March to 1st Sunday of November."""
    def sunday(y, m, n):
        d = date(y, m, 1)
        return d + timedelta(days=(6 - d.weekday()) % 7, weeks=n - 1)
    dst = sunday(e.year, 3, 2) <= e < sunday(e.year, 11, 1)
    return datetime(e.year, e.month, e.day, 20 if dst else 21, tzinfo=timezone.utc)


def cboe_quote(bid, ask):
    """'none' when neither side quotes; 'zero' when either side is missing or zero; else the mid."""
    b = bid if bid is not None and bid > 0 else None
    a = ask if ask is not None and ask > 0 else None
    if b is None and a is None:
        return "none"
    if b is None or a is None:
        return "zero"
    return (b + a) / 2


def cboe_sigma2(chain, T, R):
    """chain {(strike, 'C'|'P'): cboe_quote(...)} -> one term's variance under Cboe's own rules."""
    calls = {k: v for (k, t), v in chain.items() if t == "C"}
    puts = {k: v for (k, t), v in chain.items() if t == "P"}
    both = sorted(k for k in calls if k in puts and isinstance(calls[k], float) and isinstance(puts[k], float))
    if not both:
        return None
    ks = min(both, key=lambda k: abs(calls[k] - puts[k]))
    F = ks + math.exp(R * T) * (calls[ks] - puts[ks])
    strikes = sorted(set(calls) | set(puts))
    below = [k for k in strikes if k <= F]
    if not below:
        return None
    K0 = below[-1]
    used = {}
    for book, walk in ((puts, [k for k in reversed(strikes) if k < K0]), (calls, [k for k in strikes if k > K0])):
        zeros = 0
        for k in walk:
            v = book.get(k, "none")
            if v == "none":
                continue
            if v == "zero":
                zeros += 1
                if zeros >= 2:
                    break
                continue
            zeros = 0
            used[k] = v
    at = [b[K0] for b in (calls, puts) if isinstance(b.get(K0), float)]
    if at:
        used[K0] = sum(at) / len(at)
    return _var_sum(used, F, K0, T, R)


def index30(chains, exps, when, R):
    """Cboe's 30-day index (points) from exactly two terms, minutes to settlement, blended in total variance."""
    if len(exps) != 2:
        return None
    terms = []
    for e in exps:
        m = (settle_utc(e) - when).total_seconds() / 60
        s = cboe_sigma2(chains.get(e, {}), m / N365, R) if m > 0 else None
        if s is None:
            return None
        terms.append((m, s))
    (m1, s1), (m2, s2) = terms
    v = (m1 / N365 * s1 * (m2 - N30) / (m2 - m1) + m2 / N365 * s2 * (N30 - m1) / (m2 - m1)) * N365 / N30
    return 100 * math.sqrt(v) if v > 0 else None


def _ts(s):
    s = s.rstrip("Z")
    if "." in s:
        a, b = s.split(".")
        return datetime.strptime(a + "." + b[:6], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def snapshot_minute(rows):
    """The minute of the median recorded quote time - the snapshot the OPRA reference is read at."""
    t = sorted(_ts(r["quote_time"]) for r in rows if r.get("quote_time"))
    return t[len(t) // 2].replace(second=0, microsecond=0) if t else None


def opra_chain(path, when, root):
    """{expiry: {(strike, type): cboe_quote}} from a Databento cbbo-1m file, each contract's record
    nearest `when` (within 120 s). OSI symbols: root padded to 6, yymmdd, C/P, strike x 1000."""
    best = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            osi = r["symbol"]
            if osi[:6].strip() != root:
                continue
            gap = abs((_ts(r["ts_recv"]) - when).total_seconds())
            if gap <= 120 and (osi not in best or gap < best[osi][0]):
                best[osi] = (gap, r)
    out = defaultdict(dict)
    for osi, (_, r) in best.items():
        rest = osi[6:]
        e = datetime.strptime(rest[:6], "%y%m%d").date()
        out[e][(int(rest[7:]) / 1000, rest[6])] = cboe_quote(_f(r["bid_px_00"]), _f(r["ask_px_00"]))
    return out


def h7_day(rows, opra_path, R):
    """(free, opra) for one (date, symbol) of surface_monthly rows; opra is None without its file."""
    when = snapshot_minute(rows)
    if not rows or not when:
        return None, None
    exps = sorted({date.fromisoformat(r["expiration"]) for r in rows})
    free = defaultdict(dict)
    for r in rows:
        free[date.fromisoformat(r["expiration"])][(float(r["strike"]), r["type"])] = cboe_quote(_f(r["bid"]), _f(r["ask"]))
    sym = rows[0]["symbol"]
    opra = index30(opra_chain(opra_path, when, sym), exps, when, R) if opra_path and os.path.exists(opra_path) else None
    return index30(free, exps, when, R), opra


def h7_all(opra_dir, R, through=None, symbols=("USO", "GLD")):
    by = defaultdict(list)
    p = ROOT / "data/surface_monthly.csv"
    if not p.exists():
        return {}
    for r in csv.DictReader(p.open(newline="")):
        if r["symbol"] in symbols and (not through or r["date"] <= through):
            by[(r["date"], r["symbol"])].append(r)
    return {(d, s): h7_day(rs, os.path.join(opra_dir, f"OPRA_M_{s}_{d}.csv") if opra_dir else None, R)
            for (d, s), rs in sorted(by.items())}


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    rate = FROZEN_RATE_PCT
    if "--rate" in a:
        i = a.index("--rate")
        rate = float(a[i + 1])
        del a[i:i + 2]
    if a[:1] == ["h3"]:
        R = rate / 100
        print(f"independent H3/H5e values, r = {rate:.3f}% (vol points)\ndate        sym      reg   reg_cboe  wide_reg  wide_skip  wide_cboe")
        for (d, s), v in h3_all(R).items():
            cell = lambda k: f"{v[k]:9.4f}" if v.get(k) is not None else "      n/a"
            print(f"{d}  {s:<5}{cell('reg')}  {cell('reg_cboe')}  {cell('wide_reg')}  {cell('wide_skip')}  {cell('wide_cboe')}")
        return 0
    if a[:1] == ["h7"] and len(a) >= 2:
        R = bey_to_continuous(rate / 100)
        print(f"independent H7 values, r = {rate:.3f}% BEY (index points)\ndate        sym      free     OPRA")
        for (d, s), (fv, ov) in h7_all(a[1], R).items():
            print(f"{d}  {s:<5}{fv:9.4f}" if fv else f"{d}  {s:<5}      n/a", f"{ov:9.4f}" if ov else "      n/a")
        print("\nData provided by Databento (OPRA consolidated NBBO). Aggregates only.")
        return 0
    print("usage: independent_replica.py h3 [--rate PCT] | h7 OPRA_DIR [--rate PCT]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
