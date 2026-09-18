#!/usr/bin/env python3
"""Is the free feed's implied volatility wrong, or just differently derived?

THE QUESTION
------------
On 15 September 2026 the free feed and Bloomberg agreed on option PRICES to within
half a bid-ask spread, and disagreed on IMPLIED VOLATILITY by one to two points
(see hypotheses/2026-09-12-h3-free-data-model-free.md). Two feeds cannot do that
unless they invert the same prices under different assumptions.

This re-inverts the free feed's own mid prices using Bloomberg's printed forward
and rate for that expiry, with Black-76, and compares three numbers per contract:

    A  Alpaca's own implied volatility, as recorded          (the vendor's convention)
    B  ours, from Alpaca's mid + Bloomberg's forward/rate     (same price, their convention)
    C  Bloomberg's IVM                                        (the benchmark)

If |B - C| is much smaller than |A - C|, the gap was convention, and the quotes are
fine. If B and A agree and both sit off C, the prices themselves disagree after all,
and H3's residual has a component this project cannot remove.

LIMITS, STATE THEM IN ANY WRITE-UP
----------------------------------
- Black-76 is European. US equity and ETF options are American, so this is only
  honest out of the money, where early exercise is worth little. Only OTM contracts
  are used, and cheap ones are dropped.
- Bloomberg's own IVM comes from its model, not this one. Perfect agreement is not
  expected; a large reduction in the gap is the signal.
- Bloomberg's terms restrict redistribution. Exports stay outside the repository and
  only aggregates are printed. Attribute any published figure to
  "Source: Bloomberg Finance L.P.".

USAGE
-----
  python3 tools/iv_convention.py --date 2026-09-15
  python3 tools/iv_convention.py --date 2026-09-15 --dir ~/Documents/volrec-bloomberg
"""
import argparse
import csv
import math
import os
import re
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bloomberg_compare import (ATTRIBUTION, ROOT, DEFAULT_DIR, read_sheet, num,   # noqa: E402
                               bloomberg_label, surface_rows)

MIN_MID = 0.20          # below this, one tick of rounding swamps the implied volatility
MIN_CONTRACTS = 20      # per symbol, before a median means anything


def norm_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def black76(kind, f, k, t, r, vol):
    """Forward-price option value. f is the forward, discounted at r."""
    if vol <= 0 or t <= 0:
        intrinsic = max(0.0, (f - k) if kind == "C" else (k - f))
        return math.exp(-r * t) * intrinsic
    v = vol * math.sqrt(t)
    d1 = (math.log(f / k) + v * v / 2) / v
    d2 = d1 - v
    if kind == "C":
        return math.exp(-r * t) * (f * norm_cdf(d1) - k * norm_cdf(d2))
    return math.exp(-r * t) * (k * norm_cdf(-d2) - f * norm_cdf(-d1))


def implied_vol(kind, price, f, k, t, r):
    """Invert Black-76 by bisection. Returns None when the price is unattainable."""
    lo, hi = 1e-4, 6.0
    if price <= black76(kind, f, k, t, r, lo) or price >= black76(kind, f, k, t, r, hi):
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if black76(kind, f, k, t, r, mid) < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def omon_block(path, expiry_label):
    """Bloomberg's forward, rate and per-contract IVM for one expiry block."""
    rows, block, fwd, rate, out = read_sheet(path), None, None, None, {}
    for r in rows:
        first = (r[0] if r else "") or ""
        if "CSize" in first:
            block = first.strip()
            if block.startswith(expiry_label):
                m = re.search(r"IFwd\s+([\d.]+)", block)
                fwd = float(m.group(1)) if m else None
                m = re.search(r"\bR\s+([\d.]+)", block)
                rate = float(m.group(1)) / 100 if m else None
        if not block or not block.startswith(expiry_label):
            continue
        if not re.match(r"^\d+(\.\d+)?$", first):
            continue
        for off, typ in ((0, "C"), (7, "P")):
            if len(r) >= off + 7 and num(r[off]) is not None:
                out[(typ, round(num(r[off]), 2))] = num(r[off + 5])
    return fwd, rate, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", required=True, help="trading day, YYYY-MM-DD")
    ap.add_argument("--dir", default=str(DEFAULT_DIR))
    a = ap.parse_args()

    folder = Path(os.path.expanduser(a.dir)).resolve()
    if ROOT in folder.parents or folder == ROOT:
        sys.exit("Refusing to read exports from inside the repository.")

    rows = surface_rows(a.date)
    print(f"Implied volatility: whose convention? {a.date}\n")
    print(f"{'':6}{'n':>5}{'expiry':>12}{'fwd':>9}{'spot':>9}"
          f"{'A-C vendor':>12}{'B-C ours':>11}{'B-A':>8}{'verdict':>26}")
    any_rows = False
    for path in sorted(folder.glob(f"*_OMON_{a.date}.xlsx")):
        symbol = path.name.split("_")[0]
        srows = [r for r in rows if r["symbol"] == symbol]
        if not srows:
            continue
        expiry = sorted({r["expiration"] for r in srows},
                        key=lambda e: abs(int(next(x["dte"] for x in srows if x["expiration"] == e)) - 30))[0]
        fwd, rate, ivm = omon_block(path, bloomberg_label(expiry))
        if not fwd or not ivm:
            print(f"{symbol:6}  no {bloomberg_label(expiry)} block, or no forward printed")
            continue
        t = int(next(x["dte"] for x in srows if x["expiration"] == expiry)) / 365
        ac, bc, ba = [], [], []
        for r in srows:
            if r["expiration"] != expiry:
                continue
            k, kind, mid, vend = num(r["strike"]), r["type"], num(r["mid"]), num(r["iv"])
            if None in (k, mid, vend) or mid < MIN_MID:
                continue
            if (kind == "C" and k <= fwd) or (kind == "P" and k >= fwd):
                continue                      # out of the money only: Black-76 is European
            bench = ivm.get((kind, round(k, 2)))
            if bench is None:
                continue
            ours = implied_vol(kind, mid, fwd, k, t, rate or 0.0)
            if ours is None:
                continue
            ac.append(vend * 100 - bench)
            bc.append(ours * 100 - bench)
            ba.append(ours * 100 - vend * 100)
        if len(ac) < MIN_CONTRACTS:
            print(f"{symbol:6}{len(ac):>5}{expiry:>12}{fwd:>9.2f}{num(srows[0]['spot']):>9.2f}"
                  f"{'':>12}{'':>11}{'':>8}{'too few contracts':>26}")
            continue
        any_rows = True
        m_ac, m_bc, m_ba = st.median(ac), st.median(bc), st.median(ba)
        shrink = 1 - abs(m_bc) / abs(m_ac) if m_ac else 0
        verdict = ("convention explains it" if shrink > 0.5 else
                   "partly convention" if shrink > 0.2 else "prices disagree too")
        print(f"{symbol:6}{len(ac):>5}{expiry:>12}{fwd:>9.2f}{num(srows[0]['spot']):>9.2f}"
              f"{m_ac:>+12.2f}{m_bc:>+11.2f}{m_ba:>+8.2f}{verdict:>26}")
    if not any_rows:
        print("\nNothing measurable. Widen the export's strike count and pull again.")
        return 1
    print("\nColumns are medians in volatility points, out-of-the-money contracts only.")
    print("A = Alpaca's implied volatility, B = ours from Alpaca's mid with Bloomberg's forward,")
    print("C = Bloomberg's IVM. A shrinking |B-C| against |A-C| means the gap was convention.")
    print(ATTRIBUTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
