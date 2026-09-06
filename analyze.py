#!/usr/bin/env python3
"""
analyze.py - volatility risk premium analysis for data/iv_history.csv

Implements HANDOFF.md section 4, including the three corrections that section
insists on, because the obvious version of this analysis returns a confidently
wrong answer:

  (a) SIGNIFICANCE. Daily sampling with ~30-day forward windows means
      consecutive observations share ~29 days of the same realized path, and
      every ticker on a given day shares a market factor. A pooled t-test over
      all rows finds "significance" on pure noise most of the time. Three tests
      are reported instead, and the honest one throws away ~95% of the rows.
  (b) HORIZON. The realized window is each row's actual `dte`, not a fixed 30,
      because the IV term structure is sloped and a fixed window turns that
      slope into a dte-varying bias.
  (c) SMALL-SAMPLE BIAS. sqrt(252*mean(r^2)) reads about 1.2% low over a 21-day
      window, which is a spurious POSITIVE spread of ~0.24 vol points at 20%
      vol - against a single-stock premium the literature puts near 1.5. It
      flatters the hypothesis, so it is divided out by c4(n).

Returns are NOT demeaned: the variance-swap payoff is the un-demeaned sum of
squared log returns, so mean(r^2) dividing by n is correct, and c4 is the
zero-mean form with n degrees of freedom.

Usage:
    python analyze.py                 # the analysis (needs ALPACA_KEY/SECRET)
    python analyze.py --simulate      # validate the statistics under a true null
    python analyze.py --status        # how far off is the analysis?
"""

import csv, json, os, random, sys, time
from datetime import date, datetime, timedelta
from math import erf, exp, lgamma, sqrt, isfinite
from pathlib import Path

DATA_URL = "https://data.alpaca.markets"
CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"

# The market volatility term structure, published free by Cboe with no API key
# and no rate limit, back to 1990. This is not decoration: HANDOFF section 4.2(a)
# names the shared market factor as the thing that makes a pooled test reject a
# true null 63.8% of the time. VIX *is* that factor, measured. Removing a
# confound the design already identifies is not data mining.
MARKET_VOL = ["VIX9D", "VIX", "VIX3M", "VIX6M"]

# One-to-one benchmarks, fixed in advance - the Cboe index for that exact
# underlying. Not a net cast over a small sample.
BENCH = {"QQQ": "VXN", "IWM": "RVX", "USO": "OVX", "GLD": "GVZ"}
HERE = Path(__file__).parent
CSV = HERE / "data" / "iv_history.csv"
PRICE_CACHE = HERE / "data" / "prices.json"
VOL_CACHE = HERE / "data" / "market_vol.json"
TRADING_DAYS = 252
MIN_DAYS_FOR_ANALYSIS = 40      # section 4: ~40 trading days before this is worth running
NONOVERLAP_STRIDE = 21          # one independent episode per ~month

INDEX_ETFS = {"SPY", "DIA", "QQQ", "IWM", "MDY", "EEM", "EFA", "FXI"}
SECTOR_ETFS = {"XLK","XLF","XLE","XLV","XLP","XLU","XLI","XLY","XLB","XRT","XLC","XLRE",
               "SMH","XBI","KRE","GDX","XHB","XOP"}
NON_EQUITY = {"GLD","SLV","TLT","IEF","USO","UNG","FXE","LQD","HYG","IBIT"}


# ---------------------------------------------------------------- statistics
def c4(n):
    """Bias factor for the un-demeaned vol estimator with n squared returns.
    sqrt(252*mean(r^2)) is biased LOW by (1-c4); divide by c4 to correct."""
    if n < 2:
        return float("nan")
    return sqrt(2.0 / n) * exp(lgamma((n + 1) / 2) - lgamma(n / 2))


def realized_vol(rets):
    """Annualised realised volatility, bias-corrected. Not demeaned - see module docstring."""
    n = len(rets)
    if n < 2:
        return None
    return sqrt(TRADING_DAYS * sum(r * r for r in rets) / n) / c4(n)


def log_returns(closes):
    from math import log
    return [log(closes[i] / closes[i - 1])
            for i in range(1, len(closes)) if closes[i] > 0 and closes[i - 1] > 0]


def _norm_sf(z):
    return 0.5 * (1.0 - erf(abs(z) / sqrt(2.0)))


def _betacf(a, b, x, itmax=200, eps=3e-12):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-30: d = 1e-30
    d = 1.0 / d; h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < eps: break
    return h


def _betai(a, b, x):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lb = exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * __import__("math").log(x)
             + b * __import__("math").log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return lb * _betacf(a, b, x) / a
    return 1.0 - lb * _betacf(b, a, 1.0 - x) / b


def t_pvalue(t, df):
    """Two-sided p-value for Student's t. Exact - matters when df is ~6."""
    if df <= 0 or not isfinite(t): return float("nan")
    return _betai(0.5 * df, 0.5, df / (df + t * t))


def mean(x):
    return sum(x) / len(x) if x else float("nan")


def newey_west(x, lag):
    """Mean of x with a Newey-West HAC standard error (Bartlett kernel).
    Use on the DAILY CROSS-SECTIONAL MEAN series, never on pooled rows."""
    T = len(x)
    if T < 3: return (mean(x), float("nan"), float("nan"), float("nan"))
    mu = mean(x)
    d = [v - mu for v in x]
    lag = max(0, min(lag, T - 1))
    g0 = sum(v * v for v in d) / T
    var = g0
    for j in range(1, lag + 1):
        gj = sum(d[t] * d[t - j] for t in range(j, T)) / T
        var += 2.0 * (1.0 - j / (lag + 1.0)) * gj
    var = max(var, 1e-18)
    se = sqrt(var / T)
    t = mu / se if se > 0 else float("nan")
    return (mu, se, t, t_pvalue(t, T - 1))


def plain_t(x):
    T = len(x)
    if T < 2: return (mean(x), float("nan"), float("nan"), float("nan"))
    mu = mean(x)
    s = sqrt(sum((v - mu) ** 2 for v in x) / (T - 1))
    se = s / sqrt(T)
    t = mu / se if se > 0 else float("nan")
    return (mu, se, t, t_pvalue(t, T - 1))


def sign_test(x):
    """Distribution-free: how often is the spread positive? Exact binomial."""
    pos = sum(1 for v in x if v > 0); n = sum(1 for v in x if v != 0)
    if n == 0: return (0, 0, float("nan"))
    from math import comb
    def tail(k):
        return sum(comb(n, i) for i in range(k, n + 1)) / (2.0 ** n)
    p = 2.0 * min(tail(pos), 1.0 - tail(pos + 1) + (comb(n, pos) / 2.0 ** n))
    return (pos, n, min(1.0, max(0.0, p)))


# ------------------------------------------------------------------ the data
def load_rows():
    if not CSV.exists(): sys.exit(f"{CSV} not found.")
    with CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        f = float(v)
        return f if isfinite(f) else None
    except (TypeError, ValueError):
        return None


def group_of(sym):
    if sym in INDEX_ETFS: return "index ETF"
    if sym in NON_EQUITY: return "non-equity"
    if sym in SECTOR_ETFS: return "sector ETF"
    return "single name"


def fetch_closes(symbols, start, end):
    """Daily closes from Alpaca, cached on disk. Free tier serves stock bars."""
    import requests
    cache = json.loads(PRICE_CACHE.read_text()) if PRICE_CACHE.exists() else {}
    key, sec = os.environ.get("ALPACA_KEY"), os.environ.get("ALPACA_SECRET")
    need = [s for s in symbols if s not in cache or cache[s].get("_end", "") < end.isoformat()]
    if need:
        if not key or not sec:
            sys.exit("ALPACA_KEY / ALPACA_SECRET not set - needed to fetch daily closes.")
        s = requests.Session()
        s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec,
                          "accept": "application/json"})
        for i in range(0, len(need), 50):
            batch = need[i:i + 50]
            token, got = None, {b: {} for b in batch}
            while True:
                p = dict(symbols=",".join(batch), timeframe="1Day", feed="iex",
                         start=start.isoformat(), end=end.isoformat(), limit=10000,
                         adjustment="all")
                if token: p["page_token"] = token
                r = s.get(f"{DATA_URL}/v2/stocks/bars", params=p, timeout=30)
                r.raise_for_status()
                j = r.json()
                for sym, bars in (j.get("bars") or {}).items():
                    for b in bars:
                        got.setdefault(sym, {})[b["t"][:10]] = b["c"]
                token = j.get("next_page_token")
                if not token: break
                time.sleep(0.4)
            for sym in batch:
                d = got.get(sym, {}); d["_end"] = end.isoformat(); cache[sym] = d
            print(f"  fetched closes for {', '.join(batch[:4])}"
                  f"{'...' if len(batch) > 4 else ''} ({i+len(batch)}/{len(need)})")
            time.sleep(0.4)
        PRICE_CACHE.write_text(json.dumps(cache))
    return cache


def fetch_market_vol(series=None):
    """Cboe daily closes for the market volatility indices. Free, no key.
    Returns {index_name: {"YYYY-MM-DD": close}}."""
    import requests
    series = series or (MARKET_VOL + sorted(set(BENCH.values())))
    cache = json.loads(VOL_CACHE.read_text()) if VOL_CACHE.exists() else {}
    need = [x for x in series if x not in cache]
    for name in need:
        r = requests.get(f"{CBOE}/{name}_History.csv", timeout=30)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        head = [h.strip().upper() for h in lines[0].split(",")]
        ci = head.index("CLOSE") if "CLOSE" in head else len(head) - 1
        out = {}
        for ln in lines[1:]:
            c = ln.split(",")
            if len(c) <= ci:
                continue
            try:
                mm, dd, yy = c[0].split("/")
                out[f"{yy}-{mm}-{dd}"] = float(c[ci])
            except (ValueError, IndexError):
                continue
        cache[name] = out
        print(f"  {name}: {len(out)} daily closes, {min(out)} to {max(out)}")
        time.sleep(0.2)
    if need:
        VOL_CACHE.write_text(json.dumps(cache))
    return cache


def market_slope(vol, day):
    """Market term-structure slope in vol points: VIX3M - VIX9D. Positive is the
    normal upward-sloping curve; negative means near-term fear exceeds
    longer-term, which is what a stressed or event-driven tape looks like."""
    a = (vol.get("VIX9D") or {}).get(day)
    b = (vol.get("VIX3M") or {}).get(day)
    return None if a is None or b is None else b - a


def build_panel(rows, closes, vol=None):
    """One record per usable snapshot row. Drops rows whose forward window is
    not fully covered by available prices - never pads, never annualises a
    partial window."""
    panel, dropped = [], {"no prices": 0, "window incomplete": 0, "too few returns": 0,
                          "no iv": 0}
    for r in rows:
        sym, iv = r["symbol"], num(r.get("iv"))
        if iv is None: dropped["no iv"] += 1; continue
        series = closes.get(sym)
        if not series: dropped["no prices"] += 1; continue
        d0 = date.fromisoformat(r["date"])
        dte = int(num(r.get("dte")) or 0)
        end = d0 + timedelta(days=dte)                       # (b) actual dte, not 30
        avail = sorted(k for k in series if k != "_end")
        if not avail or avail[-1] < end.isoformat():
            dropped["window incomplete"] += 1; continue
        win = [series[k] for k in avail if d0.isoformat() <= k <= end.isoformat()]
        rets = log_returns(win)
        if len(rets) < 5: dropped["too few returns"] += 1; continue
        rv = realized_vol(rets)                              # (c) c4-corrected
        rec = dict(date=r["date"], symbol=sym, group=group_of(sym), iv=iv,
                   realized=rv, spread=iv - rv, dte=dte, n=len(rets),
                   vega=num(r.get("vega")), bid=num(r.get("bid")), ask=num(r.get("ask")),
                   mid=num(r.get("mid")), put_iv=num(r.get("put_iv")),
                   far_iv=num(r.get("far_iv")), far_dte=num(r.get("far_dte")))
        # the ticker's own term-structure slope, per day of maturity. Dividing by
        # the maturity gap carries the sign: the far leg is the FURTHEST expiry,
        # which for a minority of tickers is shorter-dated. See record.py.
        if rec["far_iv"] is not None and rec["far_dte"] and rec["far_dte"] != dte:
            rec["slope"] = (rec["far_iv"] - iv) / (rec["far_dte"] - dte)
        else:
            rec["slope"] = None
        if vol:
            rec["vix"] = (vol.get("VIX") or {}).get(r["date"])
            rec["mkt_slope"] = market_slope(vol, r["date"])
            bs = BENCH.get(sym)
            rec["bench"] = (vol.get(bs) or {}).get(r["date"]) if bs else None
            rec["bench_name"] = bs
        panel.append(rec)
    return panel, dropped


def cost_adjusted(rec, fraction):
    """Half the quoted spread converted to vol points via vega. `fraction` is how
    much of the quoted spread you assume you cross: 0 = mid, 0.25, 1.0 = full."""
    v, b, a = rec["vega"], rec["bid"], rec["ask"]
    if not v or b is None or a is None or v <= 0: return None
    return rec["spread"] - fraction * ((a - b) / 2.0) / v


# ------------------------------------------------------------------- reports
def daily_means(panel):
    by = {}
    for r in panel: by.setdefault(r["date"], []).append(r["spread"])
    return [(d, mean(by[d])) for d in sorted(by)]


def report(panel):
    vp = 100.0                                    # report in volatility points
    dm = daily_means(panel)
    days = [d for d, _ in dm]; xs = [v * vp for _, v in dm]
    avg_dte = mean([r["dte"] for r in panel])
    win_td = max(2, int(round(avg_dte * 252 / 365)))
    lag = 2 * win_td

    print("=" * 74); print("VOLATILITY RISK PREMIUM  (iv - realized, volatility points)")
    print("=" * 74)
    ntk = len({r["symbol"] for r in panel})
    print(f"rows {len(panel)}   tickers {ntk}   "
          f"days {len(days)}   mean dte {avg_dte:.1f}")
    print(f"\n~T/21 independent episodes is the real sample size: "
          f"about {max(1,len(days)//max(NONOVERLAP_STRIDE,win_td))} draw(s) of the market factor.\n")

    print("-- (1) PRIMARY: daily cross-sectional mean, Newey-West "
          f"lag {lag} (2x {win_td} trading days)")
    mu, se, t, p = newey_west(xs, lag)
    print(f"   mean {mu:+.3f} vol pts   se {se:.3f}   t {t:+.2f}   p {p:.4f}")
    print("   Over-rejects ~3x even so. Treat p as an UPPER BOUND on significance.")

    print(f"\n-- (2) CONFIRMATORY: every {stride}th trading day only (the honest test)")
    stride = max(NONOVERLAP_STRIDE, win_td)   # never shorter than the window itself
    sub = xs[::stride]
    mu2, se2, t2, p2 = plain_t(sub)
    print(f"   n {len(sub)} of {len(xs)} days   mean {mu2:+.3f}   t {t2:+.2f}   p {p2:.4f}"
          if len(sub) > 1 else f"   n {len(sub)} - not enough independent episodes yet")

    print("\n-- (3) DESCRIPTIVE: sign test on non-overlapping episodes")
    pos, n, p3 = sign_test(sub)
    print(f"   {pos}/{n} positive   p {p3:.4f}" if n else "   not enough episodes")

    print("\n-- BY GROUP (daily cross-sectional mean within group, Newey-West)")
    print(f"   {'group':14s} {'rows':>6s} {'mean':>9s} {'t':>7s} {'p':>8s}")
    for g in ("index ETF", "sector ETF", "non-equity", "single name"):
        sel = [r for r in panel if r["group"] == g]
        if not sel: continue
        gd = daily_means(sel); gx = [v * vp for _, v in gd]
        m_, s_, t_, p_ = newey_west(gx, lag)
        print(f"   {g:14s} {len(sel):6d} {m_:+9.3f} {t_:+7.2f} {p_:8.4f}")
    idx = [r for r in panel if r["group"] == "index ETF"]
    sn = [r for r in panel if r["group"] == "single name"]
    if idx and sn:
        di = mean([v for _, v in daily_means(idx)]) * vp
        ds = mean([v for _, v in daily_means(sn)]) * vp
        print(f"\n   index minus single-name: {di-ds:+.3f} vol pts "
              f"(literature: ~3.3 vs ~1.5, so expect ~+1.8)")

    print("\n-- COSTS (half-spread converted to vol points via vega)")
    for label, frac in (("mid (no cost)", 0.0), ("25% of quoted spread", 0.25),
                        ("full quoted spread", 1.0)):
        vals = [c for c in (cost_adjusted(r, frac) for r in panel) if c is not None]
        if not vals: print(f"   {label:22s} n/a"); continue
        byd = {}
        for r, c in zip(panel, (cost_adjusted(r, frac) for r in panel)):
            if c is not None: byd.setdefault(r["date"], []).append(c)
        series = [mean(byd[d]) * vp for d in sorted(byd)]
        m_, s_, t_, p_ = newey_west(series, lag)
        print(f"   {label:22s} {m_:+7.3f} vol pts   t {t_:+6.2f}   p {p_:.4f}")

    # ---- the market factor, measured and removed ----
    dmv = [(d, v) for d, v in dm if any(r["date"] == d and r.get("vix") for r in panel)]
    if dmv:
        vix_by_day, ms_by_day = {}, {}
        for r in panel:
            if r.get("vix"): vix_by_day[r["date"]] = r["vix"]
            if r.get("mkt_slope") is not None: ms_by_day[r["date"]] = r["mkt_slope"]
        days_v = [d for d, _ in dm if d in vix_by_day]
        if len(days_v) >= 6:
            y = [dict(dm)[d] * vp for d in days_v]
            x = [vix_by_day[d] for d in days_v]
            xb, yb = mean(x), mean(y)
            sxx = sum((v - xb) ** 2 for v in x)
            beta = (sum((x[i] - xb) * (y[i] - yb) for i in range(len(x))) / sxx) if sxx else 0.0
            alpha = yb - beta * xb
            resid = [y[i] - (alpha + beta * x[i]) for i in range(len(x))]
            sy = sqrt(sum((v - yb) ** 2 for v in y) / max(len(y) - 1, 1))
            sr = sqrt(sum(v * v for v in resid) / max(len(resid) - 2, 1))
            r2 = max(0.0, 1 - (sr * sr) / (sy * sy)) if sy > 0 else float("nan")
            print("\n-- MARKET FACTOR (Cboe VIX, free; section 4.2a names this as the confound)")
            print(f"   VIX over the sample: {min(x):.2f} to {max(x):.2f}, mean {xb:.2f}")
            print(f"   daily mean spread on VIX level:  beta {beta:+.3f} vol pts per VIX pt, "
                  f"R^2 {r2:.2f}")
            print(f"   -> {100*r2:.0f}% of the day-to-day swing in the premium is the market,")
            print(f"      not the individual names.")
            mr, sr_, tr, pr = newey_west([v + yb for v in resid], lag)
            print(f"   premium AFTER removing the market factor: {mr:+.3f} vol pts  "
                  f"t {tr:+.2f}  p {pr:.4f}")
            print(f"   (raw was {mu:+.3f}. If the premium survives here it is not just beta")
            print(f"    to the market, which is the harder and more interesting claim.)")
        if ms_by_day:
            inv = sum(1 for d in ms_by_day if ms_by_day[d] < 0)
            print(f"\n   market term structure inverted (VIX3M < VIX9D) on "
                  f"{inv}/{len(ms_by_day)} days - a stressed or event-driven tape")

    # ---- each ticker's own curve shape ----
    sl = [r for r in panel if r.get("slope") is not None]
    if sl:
        print("\n-- TERM STRUCTURE (the ticker's own curve, from the far leg)")
        invr = [r for r in sl if r["slope"] < 0]
        print(f"   rows with a usable slope: {len(sl)}/{len(panel)}   inverted: {len(invr)}")
        for label, sel in (("inverted curve", invr), ("upward curve", [r for r in sl if r["slope"] >= 0])):
            if not sel: continue
            byd = {}
            for r in sel: byd.setdefault(r["date"], []).append(r["spread"])
            v = [mean(byd[d]) * vp for d in sorted(byd)]
            m_, s_, t_, p_ = newey_west(v, lag)
            print(f"   {label:16s} n {len(sel):5d}   premium {m_:+7.3f} vol pts   t {t_:+6.2f}")
        print("   An inverted curve means near-term uncertainty exceeds longer-term -")
        print("   the signature of an event dated inside the near leg. If the premium")
        print("   differs across these two groups, that is the event effect.")
        bench = [r for r in sl if r.get("bench")]
        if bench:
            print(f"\n   matched Cboe benchmarks available on {len(bench)} rows "
                  f"({', '.join(sorted({r['symbol']+'/'+r['bench_name'] for r in bench}))})")

    print("\n-- SANITY (section 4.4)")
    print("   expect roughly +2 to +4 vol pts for equity index ETFs, +1 to +2 single names.")
    print("   far outside that band means a regime effect in a short sample, or a bug:")
    print("   check annualisation and dividend handling first.")
    print("\n   A null result is a real result. Carr & Wu find the single-stock premium")
    print("   significant for only 21 of 35 stocks, so a null there matches published work.")


# ---------------------------------------------------------------- validation
def simulate(reps=400, n_tickers=109, T=120, H=21, rho=0.0, seed=1):
    """Validate the three tests under a TRUE NULL.

    Construction: each ticker has a constant true vol sigma_i, and iv is set to
    sigma_i exactly - a perfect forecast, so the true premium is zero by
    construction. realized is the sample vol over the forward window, so the
    spread is pure estimation error. Consecutive windows overlap by H-1 days,
    which is the whole point: that is what breaks the pooled test.
    """
    rng = random.Random(seed)
    rej = {"pooled": 0, "per-ticker": 0, "newey-west": 0, "non-overlap": 0}
    sig = [0.10 + 0.60 * (i / n_tickers) for i in range(n_tickers)]
    for _ in range(reps):
        # daily returns with an optional common market factor
        mkt = [rng.gauss(0, 1) for _ in range(T + H + 1)]
        rets = []
        for i in range(n_tickers):
            sd = sig[i] / sqrt(TRADING_DAYS)
            rets.append([sd * (sqrt(rho) * mkt[t] + sqrt(1 - rho) * rng.gauss(0, 1))
                         for t in range(T + H + 1)])
        pooled, by_day, by_tkr = [], {}, {}
        for t in range(T):
            for i in range(n_tickers):
                rv = realized_vol(rets[i][t:t + H])
                sp = (sig[i] - rv) * 100.0
                pooled.append(sp)
                by_day.setdefault(t, []).append(sp)
                by_tkr.setdefault(i, []).append(sp)
        if plain_t(pooled)[3] < 0.05: rej["pooled"] += 1
        if plain_t([mean(v) for v in by_tkr.values()])[3] < 0.05: rej["per-ticker"] += 1
        dm = [mean(by_day[t]) for t in range(T)]
        if newey_west(dm, 2 * H)[3] < 0.05: rej["newey-west"] += 1
        sub = dm[::H]          # stride == window length => strictly non-overlapping
        if len(sub) > 1 and plain_t(sub)[3] < 0.05: rej["non-overlap"] += 1
    return {k: 100.0 * v / reps for k, v in rej.items()}


def status():
    rows = load_rows()
    days = sorted({r["date"] for r in rows})
    print(f"trading days collected : {len(days)}  ({days[0]} -> {days[-1]})")
    print(f"rows                   : {len(rows)}")
    print(f"columns                : {len(rows[0])}")
    need = MIN_DAYS_FOR_ANALYSIS - len(days)
    if need > 0:
        print(f"\nNOT READY: {need} more trading days (~{round(need*7/5)} calendar days).")
        print(f"Independent episodes at that point: ~{MIN_DAYS_FOR_ANALYSIS//NONOVERLAP_STRIDE}.")
        print("Run `python analyze.py --simulate` meanwhile - it validates the")
        print("statistics under a true null and needs no market data.")
    else:
        print(f"\nREADY: {len(days)} trading days. Run `python analyze.py`.")


def main():
    a = sys.argv[1:]
    if "--status" in a: return status()
    if "--simulate" in a:
        reps = 400
        print("Validating the three tests under a TRUE NULL (premium = 0 by construction).")
        print("Section 4.2(a) predicts the pooled test rejects most of the time and the")
        print("non-overlapping test sits near its nominal 5%.\n")
        for label, rho in (("no market factor", 0.0), ("with market factor (rho=0.5)", 0.5)):
            r = simulate(reps=reps, rho=rho)
            print(f"-- {label}   ({reps} replications, nominal 5%)")
            for k in ("pooled", "per-ticker", "newey-west", "non-overlap"):
                flag = "  <-- honest" if k == "non-overlap" else ""
                print(f"     {k:12s} rejects {r[k]:5.1f}% of the time{flag}")
            print()
        return
    rows = load_rows()
    days = sorted({r["date"] for r in rows})
    if len(days) < MIN_DAYS_FOR_ANALYSIS and "--force" not in a:
        status()
        sys.exit("\nRefusing to run: too few days. Pass --force to override.")
    syms = sorted({r["symbol"] for r in rows})
    start = date.fromisoformat(days[0]) - timedelta(days=5)
    end = date.today()
    print(f"fetching daily closes for {len(syms)} symbols, {start} -> {end}")
    closes = fetch_closes(syms, start, end)
    print("fetching the market volatility term structure from Cboe (free, no key)")
    try:
        vol = fetch_market_vol()
    except Exception as e:
        print(f"  Cboe fetch failed ({e}) - continuing without the market factor")
        vol = {}
    panel, dropped = build_panel(rows, closes, vol)
    print(f"\nusable rows: {len(panel)} of {len(rows)}")
    for k, v in dropped.items():
        if v: print(f"  dropped, {k}: {v}")
    if not panel: sys.exit("Nothing analysable yet.")
    report(panel)


if __name__ == "__main__":
    main()
