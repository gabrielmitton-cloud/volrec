"""H8's instrument - BUILDING, NOT REGISTERED (started 10 Oct 2026; scope B, Gabriel 10 Oct).

The paper's question is whether free options data loses precision through its QUOTES or through
the choices made turning quotes into a volatility number. H8 isolates the quotes: for each of the
eight surface funds, the SAME contracts at the SAME moment are priced twice - once from the free
feed, once from OPRA's consolidated NBBO - and both go through the same registered estimator
(`modelfree.model_free_30d`, the +/-30% band). The daily difference is what the free quotes alone
cost, in volatility points.

Per PROTOCOL.md this file exists BEFORE any registration: it measures, on data already bought,
  - the gap:         S0m - S1   (free vs OPRA, contracts matched within 120 s of the free quote)
  - the noise floor: S1 - S1n   (OPRA against OPRA ONE MINUTE LATER, same contracts): how far two
                     readings land when nothing is wrong but the clock
  - the arithmetic:  T, day-to-day autocorrelation, n_eff = T(1-rho)/(1+rho), and the smallest
                     effect found 80% of the time, about 2.8 sd/sqrt(n_eff)
and carries the equivalence test the registration will name (two one-sided tests against +/-bound,
Newey-West standard error). Nothing here is a verdict.

    VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra FRED_KEY=use-cache python tools/h8_quotes.py

Aggregates only. Data provided by Databento (OPRA consolidated NBBO).
"""
import math
import os
import statistics as st
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")

import modelfree                                   # noqa: E402
import opra_reference as ore                       # noqa: E402
from analyze import newey_west, t_pvalue           # noqa: E402

FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO", "TSLA", "NVDA", "AAPL")   # surface.py's SURFACE
NEXT_MINUTE = timedelta(seconds=60)


# ---------------- pure statistics (tools/test_h8.py checks each against a known answer) ----------------
def ar1(x):
    """Lag-1 autocorrelation (the usual biased estimator: lag-1 autocovariance over variance)."""
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    d = [v - m for v in x]
    den = sum(v * v for v in d)
    return sum(d[i] * d[i - 1] for i in range(1, n)) / den if den > 0 else float("nan")


def n_eff(T, rho):
    """Effective number of independent observations under AR(1): T(1-rho)/(1+rho), floored at 1.
    Negative rho is treated as 0 (no credit for anti-persistence)."""
    if T <= 0 or not math.isfinite(rho):
        return float("nan")
    r = min(max(rho, 0.0), 0.999)
    return max(1.0, T * (1 - r) / (1 + r))


def mde(sd, neff):
    """Smallest mean effect found 80% of the time at 5% two-sided: (1.96 + 0.84) sd / sqrt(n_eff)."""
    return 2.8 * sd / math.sqrt(neff) if neff and neff > 0 else float("nan")


def tost(d, bound, lag):
    """Equivalence by two one-sided tests: is the mean of d inside (-bound, +bound)?
    Newey-West (Bartlett) standard error; one-sided p from t(T-1). Equivalent at 5% when BOTH
    one-sided p are below 0.05. Returns (mean, se, p_lower, p_upper, equivalent)."""
    mu, se, _t, _p = newey_west(d, lag)
    # newey_west floors the variance at 1e-18, so a constant series gets se ~1e-9 and any bound
    # would pass. Real gaps always vary; a series that does not means the instrument is broken.
    if not (se and math.isfinite(se) and se > 1e-8):
        return mu, se, float("nan"), float("nan"), False
    T = len(d)
    t_lo = (mu + bound) / se            # H0: mu <= -bound
    t_hi = (mu - bound) / se            # H0: mu >= +bound
    p_lo = t_pvalue(t_lo, T - 1) / 2 if t_lo > 0 else 1 - t_pvalue(t_lo, T - 1) / 2
    p_hi = t_pvalue(t_hi, T - 1) / 2 if t_hi < 0 else 1 - t_pvalue(t_hi, T - 1) / 2
    return mu, se, p_lo, p_hi, (p_lo < 0.05 and p_hi < 0.05)


# ---------------- one fund, one day ----------------
def priced(rows, opra, shift=timedelta(0)):
    """The same contracts with OPRA's quote at (free quote time + shift), or None for a contract
    OPRA has no record of within ore.MATCH_TOLERANCE_S. A blank OPRA bid is a zero bid (the
    free feed writes 0; Cboe and the registered rule treat both alike); no ask = no quote."""
    out = {}
    for r in rows:
        recs = opra.get(ore.compact(r["option_symbol"]))
        if not recs or not r.get("quote_time"):
            continue
        hit = ore.nearest(recs, ore.parse_ts(r["quote_time"]) + shift)
        if hit and hit[2] is not None:
            b = hit[1] or 0.0
            out[r["option_symbol"]] = dict(r, bid=str(b), ask=str(hit[2]), mid=str((b + hit[2]) / 2.0))
    return out


def day_pair(band, opra, r):
    """band: one fund's surface.csv rows for one day. Returns the day's readings or None."""
    if not band:
        return None
    at_t = priced(band, opra)
    at_t1 = priced(band, opra, NEXT_MINUTE)
    a = [x for x in band if x["option_symbol"] in at_t]
    b = [x for x in a if x["option_symbol"] in at_t1]
    v = lambda rows: (lambda g: g[0] if g else None)(modelfree.model_free_30d(rows, r) if rows else None)
    out = {"n_band": len(band), "n_match": len(a), "n_floor": len(b),
           "S0": v(band), "S0m": v(a), "S1": v([at_t[x["option_symbol"]] for x in a]),
           "S1b": v([at_t[x["option_symbol"]] for x in b]), "S1n": v([at_t1[x["option_symbol"]] for x in b])}
    return out


# ---------------- the report ----------------
def summarise(sym, days, lag):
    gaps = [x["S0m"] - x["S1"] for x in days if x["S0m"] is not None and x["S1"] is not None]
    floor = [x["S1n"] - x["S1b"] for x in days if x["S1n"] is not None and x["S1b"] is not None]
    if len(gaps) < 3:
        print(f"  {sym:5s} {len(gaps):3d} days - too few to summarise")
        return
    sd = st.stdev(gaps)
    rho = ar1(gaps)
    ne = n_eff(len(gaps), rho)
    match = sum(x["n_match"] for x in days) / max(1, sum(x["n_band"] for x in days))
    fl = st.mean(abs(f) for f in floor) if floor else float("nan")
    mu, se, *_ = newey_west(gaps, lag)
    print(f"  {sym:5s} {len(gaps):3d} days  matched {match:4.0%}  gap mean {mu:+.3f} (NW se {se:.3f})  "
          f"mean|gap| {st.mean(abs(g) for g in gaps):.3f}  sd {sd:.3f}  rho {rho:+.2f}  n_eff {ne:4.1f}  "
          f"MDE {mde(sd, ne):.3f}  floor mean|OPRA t+1 - t| {fl:.3f}")


def main():
    from panel_health import AFTER_CLOSE_DAYS
    from datetime import date
    lag = 3
    r = modelfree.risk_free()
    print(f"H8 instrument - BUILDING, NOT REGISTERED; nothing below is a verdict. r = {r:.3%} (DGS1MO). "
          f"OPRA from {ore.DATA_DIR}\n"
          "gap = free - OPRA on the same contracts (registered estimator, +/-30% band); "
          "floor = OPRA one minute later - OPRA now\n")
    for sym in FUNDS:
        files = sorted(ore.DATA_DIR.glob(f"OPRA_{sym}_*.csv"))
        days = []
        for f in files:
            day = f.stem.split("_")[-1]
            if date.fromisoformat(day) in AFTER_CLOSE_DAYS:      # the 23 Sep rule: recorded after the close
                continue
            band = [x for x in ore.recorded(day, sym) if x["_file"] == "surface.csv"]
            got = day_pair(band, ore.load_opra(f), r)
            if got:
                days.append(got)
        if not files:
            print(f"  {sym:5s}   0 days - no OPRA files yet")
            continue
        summarise(sym, days, lag)
    print(f"\n{ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
