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
  - by side:         the snapshot gap S0s - S1s split into a put part and a call part, both orders
                     (H8-DRAFT item 7, 5 Nov 2026: descriptive, no bar, never part of the verdict)
and carries the equivalence test the registration will name (two one-sided tests against +/-bound,
Newey-West standard error, fixed-b one-sided p-values with t(T-1)'s beside, lag by `lag_for`; the
4 Nov 2026 decision, H8-DRAFT.md item 2). Nothing here is a verdict.

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
from analyze import fixed_b_null, newey_west, t_pvalue   # noqa: E402

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


def lag_for(T):
    """The Newey-West lag the registration fixes as a rule (decided 4 Nov 2026, H8-DRAFT.md item 2): the
    whole number nearest 1.3*sqrt(T), T = the fund's measured days (Lazarus, Lewis, Stock and Watson
    2018). 8 at T = 41, 7 at T = 30."""
    return math.floor(1.3 * math.sqrt(T) + 0.5)


H8_REPS = 200_000     # H8's own fixed-b draw count (4 Nov 2026, after Astra's review); same seed, and the
                      # shared default of 4,000 stays for every registered figure


def tost(d, bound, lag, reps=H8_REPS):
    """Equivalence by two one-sided tests: is the mean of d inside (-bound, +bound)?
    Newey-West (Bartlett) standard error. Each one-sided p is FIXED-b (decided 4 Nov 2026): the share
    of analyze.fixed_b_null's draws at this T and lag at or beyond the statistic, in the direction
    tested (Kiefer and Vogelsang 2005; iid Gaussian, seeded; at H8's 200,000 draws a p near 0.05 carries
    a simulation error of about 0.0005). t(T-1)'s one-sided p comes beside each, never in its place.
    Equivalent at 5% when BOTH fixed-b p are below 0.05.
    Returns (mean, se, p_lower, p_upper, equivalent, p_lower_t, p_upper_t)."""
    mu, se, _t, _p = newey_west(d, lag)
    # newey_west floors the variance at 1e-18, so a constant series gets se ~1e-9 and any bound
    # would pass. Real gaps always vary; a series that does not means the instrument is broken.
    if not (se and math.isfinite(se) and se > 1e-8):
        return mu, se, float("nan"), float("nan"), False, float("nan"), float("nan")
    T = len(d)
    t_lo = (mu + bound) / se            # H0: mu <= -bound, rejected when t_lo is large
    t_hi = (mu - bound) / se            # H0: mu >= +bound, rejected when t_hi is small
    null = fixed_b_null(T, lag, reps)
    p_lo = sum(x >= t_lo for x in null) / len(null)
    p_hi = sum(x <= t_hi for x in null) / len(null)
    pt_lo = t_pvalue(t_lo, T - 1) / 2 if t_lo > 0 else 1 - t_pvalue(t_lo, T - 1) / 2
    pt_hi = t_pvalue(t_hi, T - 1) / 2 if t_hi < 0 else 1 - t_pvalue(t_hi, T - 1) / 2
    return mu, se, p_lo, p_hi, (p_lo < 0.05 and p_hi < 0.05), pt_lo, pt_hi


# ---------------- one fund, one day ----------------
def priced(rows, opra, shift=timedelta(0), at=None):
    """The same contracts with OPRA's quote at (free quote time + shift) - or, with `at`, at that one
    moment for every contract (the snapshot minute) - or None for a contract
    OPRA has no record of within ore.MATCH_TOLERANCE_S. A blank OPRA bid is a zero bid (the
    free feed writes 0; Cboe and the registered rule treat both alike); no ask = no quote."""
    out = {}
    for r in rows:
        recs = opra.get(ore.compact(r["option_symbol"]))
        if not recs or not (at or r.get("quote_time")):
            continue
        hit = ore.nearest(recs, (at or ore.parse_ts(r["quote_time"])) + shift)
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
    # The user's view: the free snapshot as recorded (stale quotes and all) against OPRA at the
    # snapshot minute, on every contract OPRA quotes then. This adds the cost of staleness to the
    # cost of price; the quote-time match above isolates price alone.
    when = ore.snapshot_minute(band)
    at_s = priced(band, opra, at=when) if when else {}
    s = [x for x in band if x["option_symbol"] in at_s]
    v = lambda rows: (lambda g: g[0] if g else None)(modelfree.model_free_30d(rows, r) if rows else None)

    def mixed(side):
        """H8-DRAFT item 7: the snapshot contracts with OPRA's quotes on one side ("P" or "C") and the free
        feed's on the other. A row's side is the estimator's own rule: "C" is a call, anything else a put."""
        return v([at_s[x["option_symbol"]] if (x["type"] == "C") == (side == "C") else x for x in s])
    out = {"n_band": len(band), "n_match": len(a), "n_floor": len(b), "n_snap": len(s),
           "S0": v(band), "S0m": v(a), "S1": v([at_t[x["option_symbol"]] for x in a]),
           "S1b": v([at_t[x["option_symbol"]] for x in b]), "S1n": v([at_t1[x["option_symbol"]] for x in b]),
           "S0s": v(s), "S1s": v([at_s[x["option_symbol"]] for x in s]), "T": when,
           "MPs": mixed("P"), "MCs": mixed("C")}
    return out


def fund_days(sym, r):
    """[(day, day_pair reading)] for one fund, from every OPRA file on disk; days recorded after the close
    are left out (the 23 Sep rule). main() and tools/h8_index.py both read H8's days from here."""
    from panel_health import AFTER_CLOSE_DAYS
    from datetime import date
    out = []
    for f in sorted(ore.DATA_DIR.glob(f"OPRA_{sym}_*.csv")):
        day = f.stem.split("_")[-1]
        if date.fromisoformat(day) in AFTER_CLOSE_DAYS:
            continue
        band = [x for x in ore.recorded(day, sym) if x["_file"] == "surface.csv"]
        got = day_pair(band, ore.load_opra(f), r)
        if got:
            out.append((day, got))
    return out


# ---------------- the report ----------------
def sides(days):
    """H8-DRAFT item 7 (descriptive; no bar, never part of the verdict): the snapshot gap split by side, over
    the fund-days on which S0s, S1s, MPs and MCs all exist and are finite. Puts swapped first: put part
    S0s - MPs, call part MPs - S1s. Calls swapped first: call part S0s - MCs, put part MCs - S1s. Each order
    adds up to the gap exactly; the distance between the orders is the interaction, given to neither side.
    -> {"n", "gap", "puts_first": {"put", "call"}, "calls_first": {"call", "put"}}, each (mean, mean absolute)."""
    keep = [x for x in days if all(x.get(k) is not None and math.isfinite(x[k]) for k in ("S0s", "S1s", "MPs", "MCs"))]

    def two(xs):
        return (st.mean(xs), st.mean(abs(g) for g in xs)) if xs else (float("nan"), float("nan"))
    return {"n": len(keep), "gap": two([x["S0s"] - x["S1s"] for x in keep]),
            "puts_first": {"put": two([x["S0s"] - x["MPs"] for x in keep]),
                           "call": two([x["MPs"] - x["S1s"] for x in keep])},
            "calls_first": {"call": two([x["S0s"] - x["MCs"] for x in keep]),
                            "put": two([x["MCs"] - x["S1s"] for x in keep])}}


def side_line(days):
    """Item 7's report line: its own sample (all four estimates finite), its own count, and no minimum - so a
    fund with few quote-time pairs still shows its split (Astra, 5 Nov)."""
    by = sides(days)
    if not by["n"]:
        return f"  {'':5s} by side (item 7, descriptive): no fund-day with all four estimates finite"
    pf, cf = by["puts_first"], by["calls_first"]
    return (f"  {'':5s} by side (item 7, descriptive): puts first - put {pf['put'][0]:+.3f} (|.| {pf['put'][1]:.3f}), "
            f"call {pf['call'][0]:+.3f} (|.| {pf['call'][1]:.3f}); calls first - call {cf['call'][0]:+.3f} "
            f"(|.| {cf['call'][1]:.3f}), put {cf['put'][0]:+.3f} (|.| {cf['put'][1]:.3f}); "
            f"gap {by['gap'][0]:+.3f}  ({by['n']} days)")


def summarise(sym, days, lag):
    gaps = [x["S0m"] - x["S1"] for x in days if x["S0m"] is not None and x["S1"] is not None]
    snap = [x["S0s"] - x["S1s"] for x in days if x.get("S0s") is not None and x.get("S1s") is not None]
    floor = [x["S1n"] - x["S1b"] for x in days if x["S1n"] is not None and x["S1b"] is not None]
    if len(gaps) < 3:
        print(f"  {sym:5s} {len(gaps):3d} days - too few to summarise")
        print(side_line(days))
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
    if len(snap) >= 3:
        print(f"  {'':5s} at the snapshot minute (stale quotes included): mean {st.mean(snap):+.3f}  "
              f"mean|gap| {st.mean(abs(g) for g in snap):.3f}  sd {st.stdev(snap):.3f}  ({len(snap)} days)")
    print(side_line(days))


def main():
    lag = 3
    r = modelfree.risk_free()
    print(f"H8 instrument - BUILDING, NOT REGISTERED; nothing below is a verdict. r = {r:.3%} (DGS1MO). "
          f"OPRA from {ore.DATA_DIR}\n"
          "gap = free - OPRA on the same contracts (registered estimator, +/-30% band); "
          "floor = OPRA one minute later - OPRA now\n")
    for sym in FUNDS:
        if not any(ore.DATA_DIR.glob(f"OPRA_{sym}_*.csv")):
            print(f"  {sym:5s}   0 days - no OPRA files yet")
            continue
        summarise(sym, [got for _, got in fund_days(sym, r)], lag)
    print(f"\n{ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
