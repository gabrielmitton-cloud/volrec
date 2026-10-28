#!/usr/bin/env python3
"""The frozen H3 scorer (specified 17 Oct 2026, before the reading of record after Wed 11 Nov).

Why it exists (verdict-code review, 16 Oct; Gabriel approved): H3's registered statistics were computed
nowhere in code - modelfree.py prints signed means, and figures like "0.40 over 80" were worked out by
hand. A verdict needs one scorer, fixed before the reading it judges.

What it scores, from hypotheses/2026-09-12-h3-free-data-model-free.md (registered 12 Sep; BH added 16 Sep):
  H3a  the mean absolute gap, POOLED over every (underlying, day) reading of the five benchmarked
       underlyings (SPY/VIX, QQQ/VXN, IWM/RVX, GLD/GVZ, USO/OVX), is UNDER 1.0 volatility point.
       ("across the five benchmarked underlyings, over the collected series"; the file's own running
       readings have been pooled since 17 Sep.)
  H3b  the pooled mean gap (ours minus Cboe) is NEGATIVE.
  H3c  regressing the absolute gap on the Cboe index level gives a POSITIVE, SIGNIFICANT slope.
  BH   per-underlying p-values with Benjamini-Hochberg at q = 0.05 across the five; the corrected count
       is the one quoted.

Two choices the registration leaves open, fixed HERE (17 Oct 2026, written before the reading of record,
but while the daily series was visible - disclosed as such in the H3 file's log). Both are PROTOCOL.md's
house methods, not chosen to suit a number:
  - Per-underlying tests: Newey-West with fixed-b critical values on that underlying's daily series, lag
    floor(1.3 sqrt(T)). H3a: one-sided, H0 mean |gap| >= 1.0. H3c: the slope of |gap| on the index level,
    one-sided, H0 slope <= 0.
  - The pooled H3c slope: a wild cluster bootstrap with Webb's six-point weights, clusters = the five
    underlyings. 6^5 = 7,776 weight vectors, every one ENUMERATED (exact, no seed; PROTOCOL asks for at
    least 9,999 random draws, and enumeration is the exact limit of that). One-sided p, H0 slope <= 0.
  "Significant" = p < 0.05.

Reads modelfree.py's REGISTERED output (run WITHOUT --wide), days from the series start to 11 Nov.
Prints; writes nothing. No bar, band, window or estimator changes.

  python tools/h3_scorer.py                 # runs modelfree.py (FRED_KEY=use-cache) and scores
  python tools/h3_scorer.py --file F        # scores a saved modelfree.py output
"""
import argparse
import itertools
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import analyze                                      # noqa: E402
from describe import describe, lag_rule, fixed_b_null   # noqa: E402

BENCH = ("GLD", "IWM", "QQQ", "SPY", "USO")          # the five with a Cboe index (modelfree.BENCH)
H3A_BAR, ALPHA, BH_Q = 1.0, 0.05, 0.05
THROUGH = "2026-11-11"                               # the reading of record is the one after Wed 11 Nov
WEBB = (-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5))
LABEL = "frozen H3 scorer (specified 17 Oct 2026, before the reading of record)"

_ROW = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+([A-Z]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+([+-][\d.]+)\s", re.M)


def parse(out, through=THROUGH):
    """modelfree.py's registered per-day rows -> [(date, symbol, cboe, gap)] for the five, date <= through.
    Rows with 'n/a' (no Cboe close), 'too thin' and dropped days do not match and are not readings."""
    if "SENSITIVITY ONLY" in out or "WIDE SENSITIVITY" in out:
        raise SystemExit("this is --wide output (the sensitivity estimate) - H3 is scored on the REGISTERED run")
    rows = []
    for m in _ROW.finditer(out):
        d, sym, _ours, cb, gap = m.groups()
        if sym in BENCH and d <= through:
            rows.append((d, sym, float(cb), float(gap)))
    return rows


def ols(x, y):
    """(slope, intercept, residuals)."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx if sxx > 0 else float("nan")
    a0 = my - b * mx
    return b, a0, [c - a0 - b * a for a, c in zip(x, y)]


def nw_slope(x, y, lag=None):
    """Newey-West (Bartlett) slope, its HAC standard error and lag, for a single time series (in date order)."""
    T = len(x)
    lag = lag_rule(T) if lag is None else lag
    b, _a, e = ols(x, y)
    mx = sum(x) / T
    u = [(a - mx) * r for a, r in zip(x, e)]
    s = sum(v * v for v in u) / T
    for j in range(1, lag + 1):
        s += 2.0 * (1 - j / (lag + 1.0)) * sum(u[t] * u[t - j] for t in range(j, T)) / T
    sxx = sum((a - mx) ** 2 for a in x) / T
    se = math.sqrt(max(s, 1e-18) / T) / sxx if sxx > 0 else float("nan")
    return b, se, lag


def fixed_b_p_upper(t, T, lag):
    """One-sided p for H0 'parameter <= 0' (or <= bar): share of the fixed-b null at or above t."""
    null = fixed_b_null(T, lag)
    return sum(1 for v in null if v >= t) / len(null)


def cluster_t(x, y, groups):
    """OLS slope t-statistic with a CR1 cluster-robust standard error."""
    b, _a, e = ols(x, y)
    n, mx = len(x), sum(x) / len(x)
    sxx = sum((a - mx) ** 2 for a in x)
    G = sorted(set(groups))
    meat = sum(sum((x[i] - mx) * e[i] for i in range(n) if groups[i] == g) ** 2 for g in G)
    c = (len(G) / (len(G) - 1)) * ((n - 1) / (n - 2)) if len(G) > 1 and n > 2 else 1.0
    se = math.sqrt(c * meat) / sxx if sxx > 0 else float("nan")
    return b, (b / se if se > 0 else float("nan"))


def wild_cluster_p(x, y, groups):
    """One-sided p for H0 slope <= 0: Webb six-point weights, restricted (null-imposed) residuals, every
    one of the 6^G weight vectors enumerated. Returns (slope, t, p, draws)."""
    b, t = cluster_t(x, y, groups)
    my = sum(y) / len(y)
    e0 = [c - my for c in y]                      # residuals under the null slope = 0
    G = sorted(set(groups))
    idx = {g: k for k, g in enumerate(G)}
    hits = draws = 0
    for w in itertools.product(WEBB, repeat=len(G)):
        ys = [my + w[idx[g]] * r for g, r in zip(groups, e0)]
        _b, ts = cluster_t(x, ys, groups)
        draws += 1
        hits += ts >= t or not math.isfinite(ts)   # 28 Oct 2026 (review R1): an undefined draw counts AGAINST rejection
    return b, t, hits / draws, draws


UNRESOLVED = "UNRESOLVED (within display rounding of the bar)"
UNSCORED = "UNSCORED (the statistic is undefined)"


def _side(lo, hi, holds_if_below):
    """A verdict only when the whole interval [lo, hi] the true value can lie in is on one side of the bar."""
    if holds_if_below(hi) and holds_if_below(lo):
        return "HOLDS"
    if not holds_if_below(hi) and not holds_if_below(lo):
        return "FAILS"
    return UNRESOLVED


def bh_family(per, key):
    """The registered BH family: all five pairs; an untestable one enters at p = 1 (review R4, 28 Oct 2026)."""
    return {s: (per[s][key] if per.get(s) and per[s][key] is not None and math.isfinite(per[s][key]) else 1.0)
            for s in BENCH}


def score(rows, half_ulp=0.0):
    """Every registered H3 statistic from the readings. Pure.
    half_ulp (28 Oct 2026, review R3): modelfree.py prints each gap to 0.01, so a printed gap is within 0.005 of
    the true one; main() passes 0.005. A verdict is given only when it holds for every true value the printed ones
    allow, otherwise UNRESOLVED (read it at full precision by hand). 0.0 = exact inputs (the tests)."""
    if not rows:
        return None
    ab = [abs(g) for _, _, _, g in rows]
    out = {"n": len(rows), "days": len({d for d, *_ in rows}),
           "h3a_mean_abs": sum(ab) / len(ab), "h3b_mean": sum(g for *_, g in rows) / len(rows)}
    h = half_ulp
    out["h3a"] = _side(out["h3a_mean_abs"] - h, out["h3a_mean_abs"] + h, lambda m: m < H3A_BAR)
    out["h3b"] = _side(out["h3b_mean"] - h, out["h3b_mean"] + h, lambda m: m < 0)
    x, y, grp = [c for _, _, c, _ in rows], ab, [s for _, s, _, _ in rows]
    b, t, p, draws = wild_cluster_p(x, y, grp)
    mx = sum(x) / len(x)
    sxx = sum((a - mx) ** 2 for a in x)
    slack = h * sum(abs(a - mx) for a in x) / sxx if sxx > 0 else float("inf")   # most rounding can move the slope
    if not (math.isfinite(b) and math.isfinite(t)):
        h3c = UNSCORED                     # 28 Oct 2026 (review R1): a NaN t once compared as p = 0 and read HOLDS
    elif p >= ALPHA:
        h3c = "FAILS"
    else:
        h3c = _side(b - slack, b + slack, lambda v: v > 0)
    out.update(h3c_slope=b, h3c_t=t, h3c_p=p, h3c_draws=draws, h3c=h3c)
    per = {}
    for sym in BENCH:
        sub = sorted((d, c, g) for d, s, c, g in rows if s == sym)
        if len(sub) < 3:
            per[sym] = None
            continue
        a_abs = [abs(g) for _, _, g in sub]
        da = describe(a_abs, H3A_BAR, "below")
        bs, se, lag = nw_slope([c for _, c, _ in sub], a_abs)
        ts = bs / se if se and se > 0 else float("nan")
        per[sym] = {"T": len(sub), "mean_abs": da["mean"], "p_h3a": da.get("p_bar"),
                    "slope": bs, "p_h3c": fixed_b_p_upper(ts, len(sub), lag) if math.isfinite(ts) else None}
    syms = [s for s in BENCH if per[s]]
    for key in ("p_h3a", "p_h3c"):
        # 28 Oct 2026 (review R4): the registered family is all FIVE pairs. An untestable pair stays in it at p = 1
        # (it can never be rejected) instead of leaving, which would shrink the family and ease every rejection.
        fam = bh_family(per, key)
        rejected, _adj = analyze.benjamini_hochberg(fam, BH_Q)     # (set of survivors, adjusted p)
        for s in syms:
            per[s][key + "_bh"] = s in rejected
    out["per"] = per
    out["bh_h3a_k"] = sum(per[s]["p_h3a_bh"] for s in syms)
    out["bh_h3c_k"] = sum(per[s]["p_h3c_bh"] for s in syms)
    out["n_syms"] = len(syms)
    return out


def report(sc, through=THROUGH):
    if not sc:
        return "H3: no readings"
    L = [f"[{LABEL}; readings to {through}]",
         f"H3a {sc['h3a']}: pooled mean |gap| {sc['h3a_mean_abs']:.3f} vs bar under {H3A_BAR} "
         f"({sc['n']} readings over {sc['days']} days)",
         f"H3b {sc['h3b']}: pooled mean gap {sc['h3b_mean']:+.3f} (registered: negative)",
         f"H3c {sc['h3c']}: pooled slope of |gap| on the index level {sc['h3c_slope']:+.4f} per point, "
         f"t {sc['h3c_t']:.2f}, one-sided p {sc['h3c_p']:.4f} (wild cluster bootstrap, Webb weights, "
         f"{sc['h3c_draws']} weight vectors enumerated; registered: positive and significant)",
         f"BH (q {BH_Q}) across the {len(BENCH)} registered underlyings ({sc['n_syms']} testable): H3a tracks (mean |gap| "
         f"under {H3A_BAR}) on {sc['bh_h3a_k']} of {len(BENCH)}; H3c slope positive on {sc['bh_h3c_k']} of {len(BENCH)}"]
    for s, v in sc["per"].items():
        if v:
            L.append(f"   {s:<4} T={v['T']:>3}  mean |gap| {v['mean_abs']:.3f}  p(H3a) {v['p_h3a']:.4f}"
                     f"{' *' if v['p_h3a_bh'] else '  '}  slope {v['slope']:+.4f}  p(H3c) "
                     f"{v['p_h3c'] if v['p_h3c'] is None else format(v['p_h3c'], '.4f')}{' *' if v['p_h3c_bh'] else ''}")
        else:
            L.append(f"   {s:<4} fewer than 3 readings")
    L.append("   (* = rejected under Benjamini-Hochberg; Newey-West, fixed-b, per underlying)")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="the frozen H3 scorer")
    ap.add_argument("--file", type=Path, help="a saved modelfree.py (registered, not --wide) output")
    ap.add_argument("--through", default=THROUGH)
    a = ap.parse_args(argv)
    if a.file:
        out = a.file.read_text()
    else:
        p = subprocess.run([sys.executable, str(ROOT / "modelfree.py"), "--precise"], cwd=ROOT, capture_output=True, text=True,
                           env=dict(os.environ, FRED_KEY="use-cache"))
        if p.returncode != 0:
            raise SystemExit(f"modelfree.py failed ({p.returncode}): {p.stderr[-500:]}")
        out = p.stdout
    rf = re.search(r"risk-free \(DGS1MO\): ([\d.]+)%", out)
    if not rf or abs(float(rf.group(1)) - 3.910) > 0.0005:
        raise SystemExit(f"risk-free rate {rf.group(1) if rf else '?'}% is not the frozen 3.910% - refusing to score")
    # 28 Oct 2026 (outside review R3, and Astra's follow-up the same day): the reading of record is scored at full
    # precision (modelfree.py --precise, 6 decimals), so the means, the slope AND the p-values all use the estimator's
    # own numbers. A saved 2-decimal output (--file) is still judged with its 0.005 slack, but its significance
    # cannot be protected the same way, so it is refused for H3c and the BH counts.
    precise = "--precise: per-day estimates" in out
    if not precise:
        print("NOTE: this output was printed to 2 decimals - H3a/H3b judged with the 0.005 slack; H3c and the BH counts "
              "are NOT given (re-run with modelfree.py --precise)")
    sc = score(parse(out, a.through), half_ulp=0.0000005 if precise else 0.005)
    if not precise:
        sc["h3c"] = UNRESOLVED
        sc["bh_h3a_k"] = sc["bh_h3c_k"] = "n/a"
    print(report(sc, a.through))
    return 0


if __name__ == "__main__":
    sys.exit(main())
