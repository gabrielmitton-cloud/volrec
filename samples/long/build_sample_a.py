"""Sample A - the long validation sample. Tests H1.

See hypotheses/2026-09-06-h1-vrp-long-sample.md. The specification there is
frozen; this file implements it and nothing more.

The point of Sample A is NOT discovery. The volatility risk premium is well
documented on exactly this data. The point is to show the method recovers a
known result on ~127 non-overlapping episodes per pair before anyone reads what
it says about Sample B's ~6.

Everything statistical is IMPORTED from analyze.py rather than reimplemented.
That is deliberate and it is the whole argument: the two samples must run the
same frozen code, or "my method finds the known result on ten years of history"
means nothing.

Run:  ALPACA_KEY=... ALPACA_SECRET=... python samples/long/build_sample_a.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import analyze                                   # noqa: E402  the frozen code

# (Cboe index, underlying ETF, class). See H1 for the index-vs-ETF proxy caveat
# on the first four: those indices are computed on SPX/NDX/RUT/DJIA.
PAIRS = [
    ("VIX",   "SPY", "equity index"),
    ("VXN",   "QQQ", "equity index"),
    ("RVX",   "IWM", "equity index"),
    ("VXD",   "DIA", "equity index"),
    ("OVX",   "USO", "commodity"),
    ("GVZ",   "GLD", "commodity"),
    ("VXSLV", "SLV", "commodity"),
    ("VXGDX", "GDX", "equity sector"),
    ("VXXLE", "XLE", "equity sector"),
    ("VXEEM", "EEM", "equity intl"),
    ("EVZ",   "FXE", "currency"),
]

H = 21                  # forward horizon, trading days. Matches Sample B.
START = date(2016, 1, 1)
MAX_SPAN = 45           # calendar days a 21-trading-day window may span.
                        # Wider means the window crossed a gap; drop it.


def observations(iv_series, closes, dates):
    """Non-overlapping (IV, RV) pairs. Steps H trading days, never H=1.

    Overlapping daily windows are the failure mode section 4.2(a) names. They
    are not used for the headline test, here or anywhere.
    """
    out, i = [], 0
    while i + H < len(dates):
        t = dates[i]
        iv = iv_series.get(t)
        if iv is None:
            i += 1
            continue
        window = dates[i:i + H + 1]
        span = (date.fromisoformat(window[-1]) - date.fromisoformat(t)).days
        if span > MAX_SPAN:        # crossed a delisting gap - never bridge it
            i += 1
            continue
        rv = analyze.realized_vol(analyze.log_returns([closes[d] for d in window]))
        if rv is not None:
            out.append((t, iv / 100.0, rv, iv / 100.0 - rv))
        i += H                     # <- non-overlapping
    return out


def main():
    end = date.today()
    names = sorted({p[0] for p in PAIRS} | {"VIX9D", "VIX3M"})
    print(f"Sample A: {START} to {end}, horizon {H} trading days, "
          f"non-overlapping.\n")
    vol = analyze.fetch_market_vol(names)
    closes_all = analyze.fetch_closes([p[1] for p in PAIRS], START, end, feed="sip")

    print(f"\n{'pair':<14}{'N':>5}{'mean prem':>11}{'t':>8}{'p':>9}"
          f"{'pos%':>7}  window")
    print("-" * 74)

    results, by_class = {}, {}
    for idx, sym, klass in PAIRS:
        ivs = vol.get(idx) or {}
        cl = {k: v for k, v in (closes_all.get(sym) or {}).items()
              if not k.startswith("_")}
        dates = sorted(d for d in cl if d >= START.isoformat())
        if len(dates) < H + 2 or not ivs:
            print(f"{idx}/{sym:<8}  no data")
            continue
        obs = observations(ivs, cl, dates)
        if len(obs) < 5:
            print(f"{idx}/{sym:<8}  only {len(obs)} observations, skipped")
            continue
        prem = [o[3] for o in obs]
        mu, se, t, p = analyze.plain_t(prem)
        pos, n_sign, p_sign = analyze.sign_test(prem)
        results[f"{idx}/{sym}"] = (mu, t, p, len(obs))
        by_class.setdefault(klass, []).extend(prem)
        print(f"{idx}/{sym:<8}{len(obs):>5}{mu*100:>10.2f}p{t:>8.2f}{p:>9.4f}"
              f"{100*pos/max(n_sign,1):>6.0f}%  {obs[0][0]} to {obs[-1][0]}")

    # ---- H1a: is the premium positive at all?
    print("\n-- H1a  premium positive")
    wins = [k for k, (mu, t, p, n) in results.items() if mu > 0 and p < 0.05]
    print(f"   {len(wins)} of {len(results)} pairs significantly positive "
          f"at p<0.05: {', '.join(wins) if wins else 'none'}")

    # Eleven tests at p<0.05 give ~43% odds of at least one false positive if
    # every null were true, and the registered headline is a COUNT of how many
    # came back positive - exactly the claim that count is exposed to. So the
    # false discovery rate is controlled alongside it. This is reported BESIDE
    # the registered number and does not replace it: H1's specification froze the
    # per-pair t-test, and a frozen specification is not re-cut because a better
    # control was added later.
    rejected, adj = analyze.benjamini_hochberg(
        {k: v[2] for k, v in results.items()}, q=0.05)
    print(f"\n   Benjamini-Hochberg, FDR controlled at q=0.05 across "
          f"{len(results)} pairs:")
    print(f"   {'pair':<14}{'raw p':>9}{'BH adj p':>11}{'survives':>10}")
    for k, (_mu, _t, p, _n) in sorted(results.items(), key=lambda kv: kv[1][2]):
        print(f"   {k:<14}{p:>9.4f}{adj[k]:>11.4f}"
              f"{'yes' if k in rejected else 'no':>10}")
    survivors = [k for k in wins if k in rejected]
    print(f"   {len(survivors)} of {len(wins)} raw-significant pairs survive "
          f"FDR control.")
    if len(survivors) < len(wins):
        print(f"   LOST to the correction: "
              f"{', '.join(k for k in wins if k not in rejected)}")
        print("   Report the corrected count as the headline, not the raw one.")

    # ---- H1b: equity indices should show a LARGER premium than commodity/FX
    print("\n-- H1b  equity index premium > commodity / currency")
    for klass in ("equity index", "equity sector", "equity intl",
                  "commodity", "currency"):
        v = by_class.get(klass)
        if v:
            mu, se, t, p = analyze.plain_t(v)
            print(f"   {klass:<15} n={len(v):>4}  mean {mu*100:>6.2f} vol pts"
                  f"  t={t:>6.2f}")
    eq, other = by_class.get("equity index", []), (
        by_class.get("commodity", []) + by_class.get("currency", []))
    if eq and other:
        verdict = "HOLDS" if analyze.mean(eq) > analyze.mean(other) else "FAILS"
        print(f"   predicted direction: {verdict}")

    # ---- H1c: term-structure slope
    print("\n-- H1c  market term-structure slope (VIX3M - VIX9D)")
    slopes = {d: vol["VIX3M"][d] - vol["VIX9D"][d]
              for d in (vol.get("VIX3M") or {})
              if d in (vol.get("VIX9D") or {}) and d >= START.isoformat()}
    if slopes:
        inv = sum(1 for v in slopes.values() if v < 0)
        print(f"   slope positive on {100*(len(slopes)-inv)/len(slopes):.1f}% "
              f"of {len(slopes)} days, mean {analyze.mean(list(slopes.values())):+.2f} pts")
        spy = observations(vol["VIX"], {k: v for k, v in closes_all["SPY"].items()
                                        if not k.startswith("_")},
                           sorted(d for d in closes_all["SPY"]
                                  if not d.startswith("_") and d >= START.isoformat()))
        norm = [o[3] for o in spy if slopes.get(o[0], 0) >= 0]
        instr = [o[3] for o in spy if slopes.get(o[0], 0) < 0]
        for lab, v in (("normal curve", norm), ("inverted", instr)):
            if len(v) >= 2:
                mu, se, t, p = analyze.plain_t(v)
                print(f"   VIX/SPY {lab:<14} n={len(v):>3}  mean {mu*100:>6.2f} vol pts")
        if len(norm) >= 2 and len(instr) >= 2:
            print(f"   predicted (inverted smaller): "
                  f"{'HOLDS' if analyze.mean(instr) < analyze.mean(norm) else 'FAILS'}")

    print("\nSample A is a DIFFERENT ESTIMAND from data/iv_history.csv: these are")
    print("variance-swap-style indices integrating the whole strike surface;")
    print("the panel records at-the-money implied vol. Measured gap on four")
    print("matched pairs, 4 Sep 2026: +3.61 vol points. Never splice them.")


if __name__ == "__main__":
    main()
