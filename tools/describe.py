#!/usr/bin/env python3
"""Descriptive statistics BESIDE the registered verdicts (decided 16 Oct 2026, after a cold review).

A registered verdict is a pass/fail against a fixed bar. A reader also wants to know how sure that
answer is. This tool adds, for each verdict's daily series, never in place of it:
  T, the mean, the lag-1 autocorrelation rho, n_eff = T(1-rho)/(1+rho) (PROTOCOL.md, 10 Oct), a 95%
  interval, and a one-sided p-value against the bar - using the house method: Newey-West (Bartlett)
  with FIXED-b critical values (Kiefer & Vogelsang 2005; analyze.fixed_b_pvalue), lag
  floor(1.3 sqrt(T)) (Lazarus, Lewis, Stock & Watson 2018).
Plus a Holm adjustment for the whole project's count of tests (the section 5 table).

Everything it prints is labelled "added after registration, descriptive". No bar, window or
verdict is read from or written to by this tool: it reads the registered readers' OUTPUT.

  python tools/describe.py --h5e FILE   # FILE = saved output of `modelfree.py --wide`
  python tools/describe.py --h7 FILE    # FILE = saved output of `tools/h7_reader.py` (licensed run)
  python tools/describe.py --count-only --h5e FILE   # plumbing check: day counts, no statistics

Discipline (16 Oct): built and tested on synthetic series BEFORE the verdicts; run on the real
series once, after them (12-19 Nov). --count-only is for checking the plumbing without looking.
"""
import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from analyze import newey_west, fixed_b_null as _fixed_b_null   # noqa: E402
from h8_quotes import ar1, n_eff                     # noqa: E402
import record_verdict as rv                          # noqa: E402  (registered constants, read-only)

LABEL = "added after registration, descriptive - the registered verdict is the pass/fail above"
SEED, REPS = 20261016, 4000


def lag_rule(T):
    """Lazarus et al. (2018): floor(1.3 sqrt(T)); at least 1, at most T-1."""
    return max(1, min(T - 1, int(1.3 * math.sqrt(T))))


def fixed_b_null(T, lag, reps=REPS, seed=SEED):
    """Sorted simulated Newey-West t-statistics under the null at this T and lag - analyze.fixed_b_null
    (the one copy the registered readers' fixed-b p also uses), kept whole so intervals and one-sided
    p come from it."""
    return sorted(_fixed_b_null(T, lag, reps, seed))


def quantile(sorted_x, q):
    i = min(len(sorted_x) - 1, max(0, int(math.ceil(q * len(sorted_x))) - 1))
    return sorted_x[i]


def describe(x, bar=None, side="below", reps=REPS):
    """Descriptive summary of one daily series. side='below': the registered claim is mean < bar
    (H0: mean >= bar); 'above': mean > bar; None: two-sided around 0 (a descriptive series)."""
    T = len(x)
    if T < 3:
        return {"T": T, "enough": False}
    lag = lag_rule(T)
    mu, se, _t, _p = newey_west(x, lag)
    null = fixed_b_null(T, lag, reps)
    crit = quantile(sorted(abs(v) for v in null), 0.95)
    rho = ar1(x)
    sd = math.sqrt(sum((v - mu) ** 2 for v in x) / (T - 1))
    out = {"T": T, "enough": True, "mean": mu, "sd": sd, "rho": rho, "n_eff": n_eff(T, rho),
           "lag": lag, "se": se, "crit": crit, "lo": mu - crit * se, "hi": mu + crit * se}
    if bar is not None and side in ("below", "above") and se > 0:
        t = (mu - bar) / se
        frac_le = sum(1 for v in null if v <= t) / len(null)
        out["bar"], out["side"] = bar, side
        out["p_bar"] = frac_le if side == "below" else 1.0 - frac_le   # one-sided, fixed-b
    return out


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, same order as given. None, NaN or infinite entries are not
    tests and pass through as None (a NaN would make the sort order undefined)."""
    idx = [i for i, p in enumerate(pvals) if p is not None and math.isfinite(p)]
    m = len(idx)
    adj = [None] * len(pvals)
    running = 0.0
    for k, i in enumerate(sorted(idx, key=lambda i: pvals[i])):
        running = max(running, min(1.0, (m - k) * pvals[i]))
        adj[i] = running
    return adj


# ---------------- adapters: the registered readers' printed output -> daily series ----------------
def h5e_series(modelfree_out):
    """Counted H5e days from H5E_START (rv.h5e_score's own rule): (|gap of the wide-skip estimate|,
    closer-than-registered as 0/1). Reads rv.parse_h5e, so it judges exactly the verdict's days."""
    rows, _rf, _na = rv.parse_h5e(modelfree_out)
    judged = [r for r in rows if r[4] and r[0] >= rv.H5E_START and r[0] <= rv.H5E_END]
    return ([r[0] for r in judged], [abs(r[3]) for r in judged],
            [1.0 if abs(r[3]) < abs(r[2]) else 0.0 for r in judged])


_H7_ROW = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(USO|GLD)\s+([\d.]+|n/a)\s+([\d.]+|n/a)\s+([\d.]+|n/a)"
                     r"\s+([+-][\d.]+|n/a)\s+([+-][\d.]+|n/a)", re.M)


def h7_series(h7_out):
    """h7_reader's per-day rows -> {'USO_a': [|free-OPRA|...], 'GLD_a': ..., 'GLD_b': [|free-GVZ|],
    'USO_c': [free-OVX]} - the same quantities its summary lines average."""
    s = {"USO_a": [], "GLD_a": [], "GLD_b": [], "USO_c": []}
    for m in _H7_ROW.finditer(h7_out):
        sym, fo, fc = m.group(2), m.group(6), m.group(7)
        # 28 Oct 2026 (outside review M04): a day counts only with the free reading, the OPRA reading AND the
        # close, exactly as h7_reader.summarise counts it - the intervals describe the registered sample.
        if "n/a" in (m.group(3), m.group(4), m.group(5), fo, fc):
            continue
        s[f"{sym}_a"].append(abs(float(fo)))
        if sym == "GLD":
            s["GLD_b"].append(abs(float(fc)))
        else:
            s["USO_c"].append(float(fc))
    return s


def fmt(name, d, unit="pts"):
    if not d.get("enough"):
        return f"{name}: T={d.get('T', 0)} - too few days for an interval"
    line = (f"{name}: T={d['T']}, mean {d['mean']:.3f} {unit}, 95% interval [{d['lo']:.3f}, {d['hi']:.3f}] "
            f"(Newey-West, lag {d['lag']}, fixed-b critical value {d['crit']:.2f}); rho {d['rho']:.2f}, "
            f"n_eff {d['n_eff']:.1f}")
    if "p_bar" in d:
        line += f"; one-sided p against the bar {d['bar']} ({'mean below' if d['side'] == 'below' else 'mean above'}) {d['p_bar']:.3f}"
    return line


def main(argv=None):
    ap = argparse.ArgumentParser(description="descriptive statistics beside the registered verdicts")
    ap.add_argument("--h5e", type=Path)
    ap.add_argument("--h7", type=Path)
    ap.add_argument("--count-only", action="store_true", help="day counts only - check the plumbing without looking")
    a = ap.parse_args(argv)
    if not (a.h5e or a.h7):
        ap.error("give --h5e and/or --h7")
    print(f"[{LABEL}]\n")
    if a.h5e:
        days, gaps, closer = h5e_series(a.h5e.read_text())
        if a.count_only:
            print(f"H5e: {len(days)} counted days ({days[0] if days else '-'} to {days[-1] if days else '-'})")
        else:
            print(fmt("H5e mean |gap| to OVX (registered bar 0.5)", describe(gaps, rv.H5E_BAR, "below")))
            print(fmt("H5e share of days closer than registered (registered: a majority)",
                      describe(closer, 0.5, "above"), unit="share"))
    if a.h7:
        s = h7_series(a.h7.read_text())
        if a.count_only:
            print("H7: " + ", ".join(f"{k} {len(v)} days" for k, v in s.items()))
        else:
            print(fmt("H7a USO mean |free - OPRA| (bar 0.25)", describe(s["USO_a"], rv.H7_BAR_A, "below")))
            print(fmt("H7a GLD mean |free - OPRA| (bar 0.25)", describe(s["GLD_a"], rv.H7_BAR_A, "below")))
            print(fmt("H7b GLD mean |free - GVZ| (bar 0.30)", describe(s["GLD_b"], rv.H7_BAR_B, "below")))
            print(fmt("H7c USO mean free - OVX (descriptive, no bar)", describe(s["USO_c"], None, None)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
