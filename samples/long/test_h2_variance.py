"""Tests H2 - the variance formulation, per Carr & Wu (2009).

See hypotheses/2026-09-09-h2-variance-formulation.md. Registered before this
was run; this file only executes what is written there.

This does NOT replace the volatility formulation anywhere. It computes the
variance and log-variance forms alongside it so the three can be compared, and
so Friday is a conversation about results rather than intentions.

SIGN CONVENTION: this project uses IV - RV, positive when insurance was
overpriced. Carr & Wu use RV - SW, negative for the same thing. Do not compare
a number here with one from the paper without flipping it.
"""
import sys
from datetime import date
from math import log
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import analyze                                            # noqa: E402
from build_sample_a import PAIRS, H, START, observations   # noqa: E402


def autocorr(x, lag=1):
    n = len(x)
    if n <= lag + 2:
        return float("nan")
    mu = analyze.mean(x)
    d = [v - mu for v in x]
    den = sum(v * v for v in d)
    if den <= 0:
        return float("nan")
    return sum(d[t] * d[t - lag] for t in range(lag, n)) / den


def corr(x, y):
    n = min(len(x), len(y))
    if n < 3:
        return float("nan")
    mx, my = analyze.mean(x[:n]), analyze.mean(y[:n])
    dx = [v - mx for v in x[:n]]
    dy = [v - my for v in y[:n]]
    dn = (sum(v * v for v in dx) * sum(v * v for v in dy)) ** 0.5
    return sum(a * b for a, b in zip(dx, dy)) / dn if dn > 0 else float("nan")


def main():
    end = date.today()
    names = sorted({p[0] for p in PAIRS})
    vol = analyze.fetch_market_vol(names)
    closes = analyze.fetch_closes([p[1] for p in PAIRS], START, end, feed="sip")

    print("\nH2 - variance vs volatility formulation, Sample A, "
          f"{H}-day non-overlapping\n")
    print("Premium under three definitions. Positive = insurance was overpriced.")
    print("  vol      IV - RV                  (current, volatility points)")
    print("  var      IV^2 - RV^2              (Carr & Wu's quantity)")
    print("  logvar   ln(IV^2) - ln(RV^2)      (their 'closer to independent' form)\n")

    print(f"{'pair':<13}{'N':>4} | {'vol mean':>9}{'t':>7} | {'var mean':>10}{'t':>7} | "
          f"{'logvar':>8}{'t':>7}")
    print("-" * 78)

    agg = {"vol": [], "var": [], "logvar": []}
    ivs_all = {"vol": [], "var": [], "logvar": []}
    eq = {"vol": [], "var": [], "logvar": []}

    for idx, sym, klass in PAIRS:
        iv_series = vol.get(idx) or {}
        cl = {k: v for k, v in (closes.get(sym) or {}).items() if not k.startswith("_")}
        dates = sorted(d for d in cl if d >= START.isoformat())
        if len(dates) < H + 2 or not iv_series:
            continue
        obs = observations(iv_series, cl, dates)
        if len(obs) < 5:
            continue
        rec = {"vol": [], "var": [], "logvar": []}
        ivl = []
        for _, iv, rv, _ in obs:
            if iv <= 0 or rv <= 0:
                continue
            rec["vol"].append(iv - rv)
            rec["var"].append(iv * iv - rv * rv)
            rec["logvar"].append(2.0 * (log(iv) - log(rv)))
            ivl.append(iv)
        if len(rec["vol"]) < 5:
            continue
        out = []
        for k in ("vol", "var", "logvar"):
            mu, se, t, p = analyze.plain_t(rec[k])
            agg[k].extend(rec[k])
            ivs_all[k].extend(ivl)
            if klass == "equity index":
                eq[k].extend(rec[k])
            scale = 100 if k == "vol" else (10000 if k == "var" else 100)
            out.append((mu * scale, t))
        print(f"{idx}/{sym:<8}{len(rec['vol']):>4} | {out[0][0]:>9.2f}{out[0][1]:>7.2f} | "
              f"{out[1][0]:>10.1f}{out[1][1]:>7.2f} | {out[2][0]:>8.1f}{out[2][1]:>7.2f}")

    print("\n-- H2a  is the variance form significant on equity indices?")
    for k in ("vol", "var", "logvar"):
        mu, se, t, p = analyze.plain_t(eq[k])
        scale = 100 if k == "vol" else (10000 if k == "var" else 100)
        print(f"   {k:<7} n={len(eq[k]):>4}  mean {mu*scale:>9.2f}  t={t:>6.2f}  p={p:.2e}")
    print("   Carr & Wu found this strongly negative under RV-SW, i.e. strongly")
    print("   POSITIVE under our IV-RV. Same direction = implementation is sane.")

    print("\n-- H2b  is the log form closer to an independent series?")
    print("   The paper's claim: the premium correlates with the swap rate level")
    print("   in dollar terms, less so in log terms. Lower |corr| is better.\n")
    print(f"   {'form':<9}{'corr(premium, IV level)':>26}{'lag-1 autocorr':>17}")
    for k in ("vol", "var", "logvar"):
        c = corr(agg[k], ivs_all[k])
        a = autocorr(agg[k])
        print(f"   {k:<9}{c:>26.3f}{a:>17.3f}")
    cl_, cv, cg = (abs(corr(agg[k], ivs_all[k])) for k in ("vol", "var", "logvar"))
    print()
    if cg < cv:
        print(f"   VERDICT: log form IS less correlated with the level "
              f"({cg:.3f} vs {cv:.3f}). H2b supported.")
    else:
        print(f"   VERDICT: log form is NOT less correlated ({cg:.3f} vs {cv:.3f}). "
              f"H2b NOT supported on this sample.")

    print("\nNothing here replaces the volatility formulation. H2 stays registered")
    print("and unadopted until the 11 Sep meeting confirms the choice.")


if __name__ == "__main__":
    main()
