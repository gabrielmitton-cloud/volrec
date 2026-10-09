"""H6 - does implied volatility forecast the next day's trading range better than a
technical-levels rule? See hypotheses/2026-10-08-h6-implied-vol-vs-technical-levels.md.
The specification there, with the details fixed in its adjustment log on 9 Oct BEFORE any data
was fetched, is frozen; this file implements it and nothing more.

Statistics are imported from analyze.py where they exist (newey_west, t_pvalue,
benjamini_hochberg, benjamini_yekutieli), so this sample runs the project's frozen code.
The pure functions below are unit-tested in tools/test_h6.py without the network.

Run:  ALPACA_KEY=... ALPACA_SECRET=... python samples/long/h6_range.py
(The keys live in GitHub secrets; .github/workflows/h6.yml runs it by hand.)
Output is aggregates only.
"""
import sys
from datetime import date
from math import log, pi, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import analyze                                    # noqa: E402  the frozen code

PAIRS = [("VIX", "SPY"), ("VXN", "QQQ"), ("RVX", "IWM"), ("VXD", "DIA"), ("OVX", "USO"),
         ("GVZ", "GLD"), ("VXSLV", "SLV"), ("VXEEM", "EEM"), ("EVZ", "FXE")]
START = date(2016, 1, 4)
ATR_N = 14
NW_LAG = 5
GAP_DAYS = 5                       # a next bar further away than this is a gap, not "next day"
SPIKE_LOOKBACK, SPIKE_PCT, SPIKE_WINDOW = 252, 0.90, 21
IV_TO_RANGE = sqrt(8 / pi) / sqrt(252)            # Parkinson (1980): E ln(H/L) = sqrt(8/pi) sigma sqrt(dt)


# ---------------- pure pieces (tested in tools/test_h6.py) ----------------
def wilder_atr(bars, n=ATR_N):
    """bars: [(date, high, low, close)] sorted. -> {date: ATR}. True range needs the previous close,
    so the first bar yields none; the first ATR is the mean of the first n true ranges, then
    ATR_t = ((n - 1) ATR_{t-1} + TR_t) / n (Wilder 1978)."""
    out, trs, atr = {}, [], None
    for i in range(1, len(bars)):
        d, h, l, _ = bars[i]
        pc = bars[i - 1][3]
        tr = max(h, pc) - min(l, pc)
        if atr is None:
            trs.append(tr)
            if len(trs) == n:
                atr = sum(trs) / n
                out[d] = atr
        else:
            atr = ((n - 1) * atr + tr) / n
            out[d] = atr
    return out


def rows_for_pair(index_close, bars):
    """-> [(date, target, f_iv, f_atr, f_pivot, index_level)] per the frozen rules."""
    from datetime import date as _d
    atr = wilder_atr(bars)
    out = []
    for i in range(len(bars) - 1):
        d, h, l, c = bars[i]
        nd, nh, nl, _ = bars[i + 1]
        if (_d.fromisoformat(nd) - _d.fromisoformat(d)).days > GAP_DAYS:
            continue
        lvl = index_close.get(d)
        if lvl is None or d not in atr or nh <= nl or h <= l or c <= 0 or lvl <= 0:
            continue
        out.append((d, log(nh / nl), IV_TO_RANGE * lvl / 100.0, atr[d] / c, (h - l) / c, lvl))
    return out


def loss(forecast, target):
    return (log(forecast) - log(target)) ** 2


def dm_hln(d, lag=NW_LAG):
    """Diebold-Mariano on a loss-differential series with a Newey-West(lag) variance and the
    Harvey-Leybourne-Newbold factor for h = 1. Returns (mean, statistic, two-sided p)."""
    T = len(d)
    mu, _se, t, _p = analyze.newey_west(d, lag)
    stat = t * sqrt((T - 1) / T)
    return mu, stat, analyze.t_pvalue(stat, T - 1)


def spike_flags(index_close):
    """{date: True if a spike day falls in the SPIKE_WINDOW index days ending at that date}. A
    spike day's close exceeds the SPIKE_PCT quantile of the previous SPIKE_LOOKBACK closes."""
    days = sorted(index_close)
    spike = []
    for i, d in enumerate(days):
        if i < SPIKE_LOOKBACK:
            spike.append(False)
            continue
        prev = sorted(index_close[x] for x in days[i - SPIKE_LOOKBACK:i])
        q = prev[int(SPIKE_PCT * (len(prev) - 1))]
        spike.append(index_close[d] > q)
    return {d: any(spike[max(0, i - SPIKE_WINDOW + 1):i + 1]) for i, d in enumerate(days)}


def welch(a, b):
    """Welch's t on two samples -> (difference of means, t, two-sided p)."""
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = sqrt(va / na + vb / nb)
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return ma - mb, t, analyze.t_pvalue(t, df)


# ---------------- the run ----------------
def main():
    end = date.today()
    print(f"H6 - implied volatility vs ATR({ATR_N}) for the next day's range. Sample A, {START} to "
          f"the last complete day. Specification: H6's file and its 9 Oct adjustment log.\n")
    vol = analyze.fetch_market_vol([p[0] for p in PAIRS])
    ohlc = analyze.fetch_ohlc([p[1] for p in PAIRS], START, end)

    print(f"{'pair':<11}{'N':>6}  {'MSLE IV':>8}{'MSLE ATR':>9}{'MSLE piv':>9}   {'d IV-ATR':>9}{'DM':>7}"
          f"{'p':>8}  IV lower?   {'d IV-piv':>9}{'p':>8}")
    per_pair, pvals, by_date, spike_by_date = {}, {}, {}, {}
    for idx, sym in PAIRS:
        bars = sorted((d, *v) for d, v in (ohlc.get(sym) or {}).items()
                      if not d.startswith("_") and d >= START.isoformat())
        ic = {d: v for d, v in (vol.get(idx) or {}).items() if not d.startswith("_")}
        rows = rows_for_pair(ic, bars)
        if len(rows) < 30:
            print(f"{idx}/{sym:<6} too few days ({len(rows)})")
            continue
        flags = spike_flags(ic)
        Liv = [loss(r[2], r[1]) for r in rows]
        Latr = [loss(r[3], r[1]) for r in rows]
        Lpiv = [loss(r[4], r[1]) for r in rows]
        d = [a - b for a, b in zip(Liv, Latr)]
        dp = [a - b for a, b in zip(Liv, Lpiv)]
        mu, st_, p = dm_hln(d)
        mup, _, pp = dm_hln(dp)
        key = f"{idx}/{sym}"
        per_pair[key] = (len(rows), mu, st_, p)
        pvals[key] = p
        for r, x in zip(rows, d):
            by_date.setdefault(r[0], []).append(x)
            spike_by_date[r[0]] = spike_by_date.get(r[0], False) or flags.get(r[0], False)
        print(f"{key:<11}{len(rows):>6}  {sum(Liv)/len(Liv):>8.4f}{sum(Latr)/len(Latr):>9.4f}"
              f"{sum(Lpiv)/len(Lpiv):>9.4f}   {mu:>+9.4f}{st_:>7.2f}{p:>8.4f}  {'yes' if mu < 0 else 'NO':>8}"
              f"   {mup:>+9.4f}{pp:>8.4f}")

    wins = [k for k, v in per_pair.items() if v[1] < 0]
    print(f"\n-- H6a: IV has the lower error in {len(wins)} of {len(per_pair)} pairs (registered: at least 7 of 9)")
    pooled = [sum(v) / len(v) for _, v in sorted(by_date.items())]
    mu, st_, p = dm_hln(pooled)
    print(f"   pooled, date-level mean d {mu:+.4f}  DM-HLN {st_:.2f}  p {p:.4f}  over {len(pooled)} dates "
          f"(registered: significant at 5%)")
    holds_a = len(wins) >= 7 and len(per_pair) == 9 and p < 0.05 and mu < 0
    print(f"   H6a {'HOLDS' if holds_a else 'FAILS'}")
    bh, _ = analyze.benjamini_hochberg(pvals)
    by, _ = analyze.benjamini_yekutieli(pvals)
    print(f"   per-pair DM p-values: {len(bh)} of {len(pvals)} survive BH at 5%, {len(by)} under BY "
          f"(either sign; reported beside, not part of the registered rule)")

    after = [sum(v) / len(v) for dd, v in sorted(by_date.items()) if spike_by_date.get(dd)]
    calm = [sum(v) / len(v) for dd, v in sorted(by_date.items()) if not spike_by_date.get(dd)]
    if len(after) > 2 and len(calm) > 2:
        diff, t, pw = welch(after, calm)
        holds_b = diff < 0 and pw < 0.05
        print(f"\n-- H6b: pooled mean d after a spike {sum(after)/len(after):+.4f} ({len(after)} dates) vs calm "
              f"{sum(calm)/len(calm):+.4f} ({len(calm)}); difference {diff:+.4f}, Welch t {t:.2f}, p {pw:.4f}")
        print(f"   H6b {'HOLDS' if holds_b else 'FAILS'} (registered: lower after spikes, p < 0.05)")
    print("\nNegative d means implied volatility forecast the range better. Losses are squared log errors.")


if __name__ == "__main__":
    main()
