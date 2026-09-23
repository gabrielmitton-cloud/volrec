"""Delta-hedged profit and loss per contract, from the recorded strike surface.

WHY THIS EXISTS — read HANDOFF section 14.2 first
--------------------------------------------------
The obvious way to ask "where in the strike surface is the premium largest" is
to compute IV(K)^2 minus realised variance at each strike and compare strikes.
That does not work. Realised variance is one number shared by every strike on a
given day, so

    premium(K1) - premium(K2) = IV(K1)^2 - IV(K2)^2

and the realised term cancels exactly. What survives is the shape of the
implied volatility surface, which is the volatility smile, which Bollen & Whaley
published in the Journal of Finance in 2004.

The fix the literature uses is a STRIKE-SPECIFIC realised outcome. This file
implements the standard one: the delta-hedged gain of Bakshi & Kapadia (2003,
RFS 16(2) 527-566). Buy the option, hedge the directional exposure by shorting
delta shares, rebalance daily, and see what is left. The hedging path depends on
the contract's own gamma, so it does not cancel across strikes.

THE ECONOMICS, so the sign is not misread
-----------------------------------------
If an option is priced at an implied volatility higher than what the underlying
subsequently realises, a delta-hedged LONG position loses money: the buyer paid
for more movement than arrived. So

    delta-hedged gain < 0   <=>   a POSITIVE variance risk premium

Bakshi & Kapadia found delta-hedged gains significantly negative on index
options, which is the premium seen from the buyer's side. A gain reported here
that is negative is the expected direction, not a bug.

THE DISCRETISATION
------------------
Over consecutive observed days n = 0..N-1, for one contract:

    PI = C_N - C_0
         - SUM_n  delta_n * (S_{n+1} - S_n)          hedge rebalanced daily
         - SUM_n  r * (C_n - delta_n * S_n) * (1/365) financing the position

Daily rebalancing is coarse. Bakshi & Kapadia rebalance more often and note the
discretisation error; with one snapshot per day this is the finest available and
the residual is a known limitation to state, not to hide.

WHAT BREAKS IT
--------------
A contract must be observed on consecutive trading days. `surface.py` selects
strikes on a moneyness grid recentred on each day's spot, so a contract can drop
out when spot drifts, and the run ends there. `surface.py` carries forward
previously recorded contracts to mitigate this; the coverage report below says
how well that is working, and it should be read every time.

Run:  FRED_KEY=... python hedged.py
"""
import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import analyze                                     # noqa: E402
from panel_health import US_MARKET_HOLIDAYS        # noqa: E402  one list, owned there
SURF = HERE / "data" / "surface.csv"

MIN_RUN = 2          # need at least two observations to hedge anything
MONEYNESS_BUCKETS = [
    ("deep OTM put",  0.00, 0.90),
    ("OTM put",       0.90, 0.97),
    ("at the money",  0.97, 1.03),
    ("OTM call",      1.03, 1.10),
    ("deep OTM call", 1.10, 9.99),
]


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def skipped_trading_day(prev, here):
    """True if a US trading day falls strictly between two observation dates."""
    d = prev + timedelta(days=1)
    while d < here:
        if d.weekday() < 5 and d not in US_MARKET_HOLIDAYS:
            return True
        d += timedelta(days=1)
    return False


def runs_for_contract(obs):
    """Split one contract's observations into consecutive-trading-day runs.

    `obs` is a list of rows for a single option_symbol, sorted by date. A run breaks
    whenever a trading day passes with the contract unobserved, so a weekend or a
    holiday weekend joins while a missed session does not.

    Until 23 Sep 2026 this used "within four calendar days" as a proxy for
    consecutive. That spliced 15 -> 17 Sep across the lost 16 Sep, and any contract
    that dropped off the grid for a day, into two-trading-day hedges: 1,395 runs,
    which moved H4's date-level mean from about -1.1bp to -8.56bp. H4's specification
    says consecutive trading days; see H4's adjustment log (strike 1 of 3).
    """
    out, cur = [], []
    for row in obs:
        if not cur:
            cur = [row]
            continue
        prev = date.fromisoformat(cur[-1]["date"])
        here = date.fromisoformat(row["date"])
        if not skipped_trading_day(prev, here):
            cur.append(row)
        else:
            if len(cur) >= MIN_RUN:
                out.append(cur)
            cur = [row]
    if len(cur) >= MIN_RUN:
        out.append(cur)
    return out


def hedged_gain(run, r_annual, delta_of=None):
    """Delta-hedged P&L over one run. Returns a dict, or None if unusable.

    `delta_of` optionally replaces the recorded delta with a callable taking a row
    and returning a delta, so the identical runs can be re-hedged under a different
    model. The recorded delta is the vendor's, and the vendor's model is the one
    `tools/iv_convention.py` found disagreeing with this project's; see
    `tools/delta_model.py`. Default is None, which is the recorded delta unchanged.
    """
    C, S, D = [], [], []
    for row in run:
        c, s = _f(row["mid"]), _f(row["spot"])
        d = _f(row["delta"]) if delta_of is None else delta_of(row)
        if c is None or s is None or d is None or c <= 0 or s <= 0:
            return None
        C.append(c); S.append(s); D.append(d)
    n = len(C)
    if n < MIN_RUN:
        return None

    hedge = sum(D[i] * (S[i + 1] - S[i]) for i in range(n - 1))
    financing = sum(r_annual * (C[i] - D[i] * S[i]) / 365.0 for i in range(n - 1))
    pnl = (C[-1] - C[0]) - hedge - financing

    first = run[0]
    return {
        "symbol": first["symbol"],
        "option_symbol": first["option_symbol"],
        "type": first["type"],
        "start": first["date"], "end": run[-1]["date"], "days": n - 1,
        "moneyness": _f(first["moneyness"]),
        "strike": _f(first["strike"]),
        "iv0": _f(first["iv"]),
        "volume": _i(first["volume"]) or 0,
        "open_interest": _i(first["open_interest"]) or 0,
        "pnl": pnl,
        # Scaled by the underlying, which is how Bakshi & Kapadia report it, so
        # contracts on a $700 index and a $30 ETF are comparable.
        "scaled": pnl / S[0],
    }


def bucket_of(m):
    for name, lo, hi in MONEYNESS_BUCKETS:
        if lo <= m < hi:
            return name
    return "other"


def report(results):
    if not results:
        print("\nNo completed runs yet. A contract must be observed on at least")
        print("two consecutive trading days before it can be hedged.")
        return

    print(f"\n{len(results)} hedged runs across "
          f"{len({r['option_symbol'] for r in results})} contracts, "
          f"{len({r['symbol'] for r in results})} underlyings\n")

    print("-- delta-hedged gain by moneyness bucket")
    print("   negative = the option buyer lost = a POSITIVE variance premium\n")
    print(f"   {'bucket':<16}{'n':>5}{'mean scaled':>14}{'t':>8}{'% neg':>8}")
    by = defaultdict(list)
    for r in results:
        if r["moneyness"] is not None:
            by[bucket_of(r["moneyness"])].append(r)
    for name, _, _ in MONEYNESS_BUCKETS:
        v = by.get(name)
        if not v:
            continue
        x = [q["scaled"] * 10000 for q in v]          # basis points of spot
        mu, se, t, p = analyze.plain_t(x) if len(x) > 1 else (x[0], 0, 0, 1)
        neg = 100.0 * sum(1 for q in x if q < 0) / len(x)
        print(f"   {name:<16}{len(v):>5}{mu:>13.2f}bp{t:>8.2f}{neg:>7.0f}%")

    print("\n-- by where the volume is (terciles of contract volume)")
    print("   the question: does the premium sit where people actually trade?\n")
    vols = sorted(r["volume"] for r in results)
    if len(vols) >= 6 and vols[-1] > 0:
        lo, hi = vols[len(vols) // 3], vols[2 * len(vols) // 3]
        tiers = {"low volume": [], "mid volume": [], "high volume": []}
        for r in results:
            k = ("low volume" if r["volume"] <= lo
                 else "high volume" if r["volume"] > hi else "mid volume")
            tiers[k].append(r)
        print(f"   {'tier':<16}{'n':>5}{'mean scaled':>14}{'t':>8}{'med vol':>10}")
        for k in ("low volume", "mid volume", "high volume"):
            v = tiers[k]
            if not v:
                continue
            x = [q["scaled"] * 10000 for q in v]
            mu, se, t, p = analyze.plain_t(x) if len(x) > 1 else (x[0], 0, 0, 1)
            mv = sorted(q["volume"] for q in v)[len(v) // 2]
            print(f"   {k:<16}{len(v):>5}{mu:>13.2f}bp{t:>8.2f}{mv:>10,}")
    else:
        print("   not enough volume spread yet")

    print("\n-- pooled")
    x = [r["scaled"] * 10000 for r in results]
    mu, se, t, p = analyze.plain_t(x) if len(x) > 1 else (x[0], 0, 0, 1)
    print(f"   n={len(x)}  mean {mu:+.2f}bp of spot  t={t:.2f}  p={p:.4f}")
    honest_units(results)

    print("\n   CAUTION: these runs overlap in calendar time and share")
    print("   underlyings, so they are NOT independent observations. This t is")
    print("   descriptive. Any inferential claim needs the cross-section demeaned")
    print("   by date and standard errors clustered on date. See HANDOFF 14.3.")


def honest_units(results):
    """The same gains, at units that are plausibly independent. HANDOFF 14.3.

    `report` above prints a t over contracts because that is what H4 registered and
    what the first run recorded. `analyze.py --simulate-surface` measures what that
    t does when there is nothing there: it rejects a true null 46% of the time with
    no market factor and 64-73% with one, and more days make it worse rather than
    better, because they add correlated rows and not independent ones.

    So the same numbers are printed again at three coarser units:

      underlying-day  one observation per underlying per day. Honest only when
                      underlyings do not move together; the simulation puts its
                      false-rejection rate at 23-30% once they do.
      date            one observation per day, the unit HANDOFF 14.3 prescribes for
                      a LEVEL claim like H4a. Honest at 4-5% in every sweep.
      volume contrast the top volume tercile minus the bottom, differenced INSIDE
                      each underlying-day so the shared shock cancels. This is H4c's
                      claim and it is honest at any sample length.

    None of this changes a threshold, a bucket or a tercile rule. It reports the
    registered quantities at units whose error bars mean something.
    """
    print("\n-- the same gains at units that are plausibly independent (HANDOFF 14.3)")
    print("   run `python analyze.py --simulate-surface` for what each unit costs\n")
    print(f"   {'unit':<22}{'n':>5}{'mean scaled':>14}{'t':>8}{'p':>9}")

    def line(label, x):
        if len(x) < 2:
            print(f"   {label:<22}{len(x):>5}{'':>14}{'':>8}{'needs >= 2':>9}")
            return
        mu, _, t, p = analyze.plain_t(x)
        print(f"   {label:<22}{len(x):>5}{mu:>13.2f}bp{t:>8.2f}{p:>9.4f}")

    line("contract", [r["scaled"] * 10000 for r in results])

    cells = defaultdict(list)
    for r in results:
        cells[(r["symbol"], r["start"])].append(r)
    line("underlying-day", [sum(q["scaled"] for q in v) / len(v) * 10000
                            for v in cells.values()])

    by_date = defaultdict(list)
    for r in results:
        by_date[r["start"]].append(r)
    line("date", [sum(q["scaled"] for q in v) / len(v) * 10000
                  for v in by_date.values()])

    # H4c's contrast, differenced within each underlying-day using the pooled cuts.
    vols = sorted(r["volume"] for r in results)
    if len(vols) >= 6 and vols[-1] > 0:
        lo, hi = vols[len(vols) // 3], vols[2 * len(vols) // 3]
        diffs = []
        for v in cells.values():
            low = [q["scaled"] for q in v if q["volume"] <= lo]
            high = [q["scaled"] for q in v if q["volume"] > hi]
            if low and high:
                diffs.append((sum(high) / len(high) - sum(low) / len(low)) * 10000)
        line("volume contrast hi-lo", diffs)
        print("\n   H4c predicted that contrast NEGATIVE (high volume more negative).")
    print("\n   Until the date row has enough dates to be a test, every row above is")
    print("   descriptive. No claim should be made from the contract row at any length.")


def _quote_dt(stamp):
    """Parse the feed's RFC-3339 stamp, trimming nanoseconds datetime cannot take."""
    import re
    from datetime import datetime, timezone
    if not stamp:
        return None
    t = re.sub(r"\.(\d{6})\d+", r".\1", stamp.strip().replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(t).astimezone(timezone.utc)
    except ValueError:
        return None


def intervals(rows):
    """The real elapsed time between snapshots, which is not 24 hours.

    The cron is fixed and GitHub's delay is not, so a "day" here is whatever
    interval separated two snapshots. Over 14-15 September that was 23.2 hours.
    It matters less than it looks: the interval is the same for every contract on
    a given date, so the date-clustered rows in `honest_units` absorb it entirely
    and only the contract-level number is exposed. Putting the financing term on
    the true elapsed time rather than a flat 1/365 moves the pooled mean by
    0.003bp of 2.21, which is not worth breaking a registered specification over
    - but it is worth being able to see, because a drift that grows is a real
    comparability problem. `panel_health.py` raises the alarm; this just shows it.
    """
    stamps = defaultdict(list)
    for r in rows:
        t = _quote_dt(r.get("quote_time"))
        if t:
            stamps[r["date"]].append(t)
    if len(stamps) < 2:
        return
    mids = {d: sorted(v)[len(v) // 2] for d, v in stamps.items()}
    days = sorted(mids)
    print("\n-- the interval a 'day' actually was")
    print(f"   {'from':<12}{'to':<12}{'hours':>8}{'vs 24h':>9}")
    for a, b in zip(days, days[1:]):
        h = (mids[b] - mids[a]).total_seconds() / 3600.0
        print(f"   {a:<12}{b:<12}{h:>8.2f}{h - 24:>+9.2f}")


def coverage(rows):
    """How well contracts persist day to day. Read this before the results."""
    by_day = defaultdict(set)
    for r in rows:
        by_day[r["date"]].add(r["option_symbol"])
    days = sorted(by_day)
    print("-- contract continuity (a run needs a contract on consecutive days)")
    if len(days) < 2:
        print(f"   only {len(days)} day(s) recorded; continuity needs at least two")
        return
    print(f"   {'date':<12}{'contracts':>11}{'carried over':>14}{'retained':>10}")
    for i, d in enumerate(days):
        if i == 0:
            print(f"   {d:<12}{len(by_day[d]):>11}{'-':>14}{'-':>10}")
            continue
        prev = by_day[days[i - 1]]
        keep = len(by_day[d] & prev)
        print(f"   {d:<12}{len(by_day[d]):>11}{keep:>14}"
              f"{100.0*keep/max(len(prev),1):>9.0f}%")


def main():
    if not SURF.exists():
        sys.exit(f"No {SURF.name} yet. The surface workflow writes it on the "
                 f"first weekday run.")
    rows = list(csv.DictReader(SURF.open(newline="")))
    if not rows:
        sys.exit("surface.csv is empty.")

    import modelfree
    r = modelfree.risk_free()
    print(f"risk-free (DGS1MO): {r*100:.3f}%\n")

    coverage(rows)
    intervals(rows)

    by_contract = defaultdict(list)
    for row in rows:
        by_contract[row["option_symbol"]].append(row)

    results = []
    for osym, obs in by_contract.items():
        obs.sort(key=lambda x: x["date"])
        for run in runs_for_contract(obs):
            g = hedged_gain(run, r)
            if g:
                results.append(g)
    report(results)


if __name__ == "__main__":
    main()
