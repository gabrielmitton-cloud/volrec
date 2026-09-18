"""Record the option strike surface for a small set of names.

WHY THIS EXISTS
---------------
`record.py` already fetches every strike within +/-8% of spot, calls and puts,
for all 109 tickers, every day. It then keeps ONE contract per ticker and
discards the rest. That discarded data is the strike surface, and it is the
thing a volatility study actually needs in order to say anything about *where*
the premium lives rather than only how big it is at the money.

On 11 Sep 2026 a finance professor advised collecting raw option prices and
volume across roughly twenty strikes within about ten percent of spot, daily,
rather than treating implied volatility as the primary quantity. Bloomberg was
suggested as the source. That turned out to be impossible: Bloomberg holds only
the last 90 calendar days of historical equity option data via OMON's "As of"
field (University of Manchester and University of Iowa library guides, verified
11 Sep 2026), and OptionMetrics via WRDS is restricted to faculty, staff and
doctoral students at Pepperdine.

So the surface gets collected here instead, from the feed already in use, at
zero additional cost, starting the day the decision was made. Every day not
recorded is a day that cannot be recovered.

WHAT IT DOES NOT DO
-------------------
It does not touch `data/iv_history.csv`, `record.py`, or `record.yml`. It writes
only to `data/surface.csv`. The daily ATM panel is the irreplaceable artifact
and nothing here is allowed to put it at risk.

DESIGN NOTES
------------
- TWO expiries per ticker per day, bracketing 30 days where both exist. This
  is not decoration: Cboe's model-free variance calculation uses a near and a
  next term and interpolates between them to a constant 30 days. Recording one
  expiry would leave a maturity mismatch permanently baked into any comparison
  against the published indices, and that mismatch would be impossible to
  separate from the gaps the comparison is meant to measure. Two expiries is
  the same API call and roughly twice the rows.
- Strikes are chosen on a MONEYNESS GRID, not by taking the N nearest to spot.
  Strike density varies enormously by underlying: SPY has dollar strikes, so
  the twenty nearest span barely 1.3% of spot, while GLD's twenty span the whole
  band. Measured 12 Sep 2026, nearest-N gave SPY strikes 755-774 on a 764 spot
  and GLD 389-408 on 398 - one is a point, the other is a smile, and they are
  not comparable. A moneyness grid fixes the economic location of each strike
  so the same row means the same thing across every underlying.
- `volume` is recorded per contract and is the point of the exercise. Standard
  variance measures like VIX weight every strike by a fixed mathematical rule
  regardless of whether anyone traded it.
- Contracts recorded on the previous day are CARRIED FORWARD if they are still
  inside the DTE window, on top of whatever the moneyness grid selects today.
  Without this the grid recentres on each day's spot, so a contract silently
  drops out when the underlying drifts, and any measure that needs a contract
  observed on consecutive days - delta-hedged profit and loss, most obviously -
  loses the run at that point. Carrying forward costs nothing: the chain request
  already returns those contracts. It is bounded naturally, because a contract
  leaves the window once it falls under the minimum DTE.
- `open_interest` comes from a different endpoint, since the snapshot does not
  carry it. It is fetched in bulk, filtered to the same strikes and expiries, so
  it costs two extra requests per ticker rather than one per contract. Volume is
  flow and open interest is stock, and a liquidity story needs both. It is
  published with a lag, so `open_interest_date` is recorded beside it: never
  assume it is same-day.

Run:  ALPACA_KEY=... ALPACA_SECRET=... python surface.py
"""
import csv
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # importable from anywhere
import record as R

# Names to collect. Deliberately small: the file grows every trading day and
# lives in a public git repo. TSLA is here because it is the name the professor
# named and because its option market went from nothing in 2010 to one of the
# most heavily retail-traded in the market, which makes it the closest thing to
# a natural experiment available.
# Five of these have a Cboe model-free index published against them, which is
# the point: SPY/VIX, QQQ/VXN, IWM/RVX, GLD/GVZ, USO/OVX. Those pairs let the
# estimator built from this file be checked against the authoritative number for
# the same underlying on the same day. TSLA, NVDA and AAPL have no published
# index and are carried for the single-name work.
SURFACE = ["SPY", "QQQ", "IWM", "GLD", "USO", "TSLA", "NVDA", "AAPL"]

TARGET_DTE = 30
DTE_WINDOW = (21, 45)
# Measured against Cboe's published indices on 2026-09-11, comparing the
# model-free estimate built from this file against VIX/VXN/RVX/GVZ/OVX:
#
#     band x strikes    mean |gap|   worst    rows/day   MB/yr
#     +/-10% x 20          3.97      -12.37      532       23
#     +/-20% x 30          1.31       -4.39      846       36
#     +/-30% x 40          0.59       -1.84     1158       50
#
# The advice was +/-10% and twenty strikes. That truncates badly, and it
# truncates WORST where volatility is highest: a +/-10% band is about 2.2
# standard deviations on a 16-vol name but only 0.6 on a 59-vol name like USO,
# which is why oil was 12 points light. Cboe integrates until it sees two
# consecutive zero bids, which reaches far further into the tails.
#
# At +/-30% the estimate matches the published index to 0.01 points on SPY and
# 0.59 on average. That accuracy is the whole basis of the comparison study, so
# it is worth the storage.
STRIKE_BAND = 0.30
STRIKE_COUNT = 40
# Target moneyness levels, evenly spaced across the band. The nearest available
# strike to each target is kept, so coverage is comparable across underlyings
# regardless of how finely that underlying's strikes are spaced.
MONEYNESS_GRID = [1 - STRIKE_BAND + i * (2 * STRIKE_BAND) / (STRIKE_COUNT - 1)
                  for i in range(STRIKE_COUNT)]
PACE = 1.0                  # slower than record.py: this may run alongside it
OUT = Path(__file__).parent / "data" / "surface.csv"

FIELDS = [
    "date", "symbol", "spot", "quote_time",
    "expiration", "dte", "type", "strike", "moneyness", "option_symbol",
    "bid", "ask", "mid", "volume", "open_interest", "open_interest_date",
    "iv", "delta", "gamma", "theta", "vega", "rho",
]


def chain(s, symbol, spot, today, kind):
    """One side of the chain inside the strike band and DTE window."""
    p = dict(
        feed=R.OPTION_FEED, limit=1000, type=kind,
        expiration_date_gte=(today + timedelta(days=DTE_WINDOW[0])).isoformat(),
        expiration_date_lte=(today + timedelta(days=DTE_WINDOW[1])).isoformat(),
        strike_price_gte=round(spot * (1 - STRIKE_BAND), 2),
        strike_price_lte=round(spot * (1 + STRIKE_BAND), 2))
    out = {}
    for _ in range(R.MAX_PAGES):
        j = R.get(s, f"{R.DATA}/v1beta1/options/snapshots/{symbol}", **p)
        page = j.get("snapshots") or {}
        out.update(page)
        token = j.get("next_page_token")
        if not token or not page:
            break
        p["page_token"] = token
        time.sleep(PACE)
    return out


def previous_contracts(symbol, today):
    """Option symbols recorded for `symbol` on the most recent earlier date.

    Returns an empty set on the first run, or if the file is unreadable. This is
    an enhancement to continuity, never a precondition for recording.
    """
    if not OUT.exists():
        return set()
    try:
        seen = {}
        with OUT.open(newline="") as f:
            for row in csv.DictReader(f):
                if row.get("symbol") != symbol:
                    continue
                d = row.get("date", "")
                if d and d < today.isoformat():
                    seen.setdefault(d, set()).add(row["option_symbol"])
        return seen[max(seen)] if seen else set()
    except Exception:
        return set()


def open_interest(s, symbol, spot, today):
    """{option_symbol: (open_interest, as_of_date)} for the same query window.

    The snapshot endpoint does not carry open interest; the contracts endpoint
    does, and returns contracts in bulk rather than one per request. Failure
    here is non-fatal: the surface is still worth recording without it.
    """
    out = {}
    p = dict(
        underlying_symbols=symbol, limit=10000,
        expiration_date_gte=(today + timedelta(days=DTE_WINDOW[0])).isoformat(),
        expiration_date_lte=(today + timedelta(days=DTE_WINDOW[1])).isoformat(),
        strike_price_gte=round(spot * (1 - STRIKE_BAND), 2),
        strike_price_lte=round(spot * (1 + STRIKE_BAND), 2))
    for _ in range(R.MAX_PAGES):
        j = R.get(s, f"{R.TRADING}/v2/options/contracts", **p)
        got = j.get("option_contracts") or []
        for c in got:
            oi = c.get("open_interest")
            if oi not in (None, ""):
                out[c["symbol"]] = (oi, c.get("open_interest_date", ""))
        token = j.get("next_page_token")
        if not token or not got:
            break
        p["page_token"] = token
        time.sleep(PACE)
    return out


def rows_for(s, symbol, spot, today):
    """Every contract at the chosen expiry, both types, nearest STRIKE_COUNT."""
    snaps = chain(s, symbol, spot, today, "call")
    time.sleep(PACE)
    snaps.update(chain(s, symbol, spot, today, "put"))
    if not snaps:
        raise RuntimeError("no contracts in the strike/expiry window")
    time.sleep(PACE)
    try:
        oi_map = open_interest(s, symbol, spot, today)
    except Exception as e:
        print(f"    (open interest unavailable for {symbol}: {type(e).__name__})")
        oi_map = {}

    parsed = []
    for osym, snap in snaps.items():
        try:
            exp, strike, kind = R.parse_occ(osym)
        except ValueError:
            continue
        dte = (exp - today).days
        if DTE_WINDOW[0] <= dte <= DTE_WINDOW[1]:
            parsed.append((exp, dte, strike, kind, osym, snap))
    if not parsed:
        raise RuntimeError("nothing inside the DTE window")

    # Two expiries bracketing TARGET_DTE, so the pair can be interpolated to a
    # constant 30 days the way Cboe does. Prefer one below and one above; if the
    # window only offers expiries on one side, take the two nearest to the
    # target. Sorted deterministically so the choice cannot flip between runs.
    expiries = sorted({(e, d) for e, d, _, _, _, _ in parsed}, key=lambda x: x[1])
    below = [x for x in expiries if x[1] <= TARGET_DTE]
    above = [x for x in expiries if x[1] > TARGET_DTE]
    if below and above:
        picks = [below[-1][0], above[0][0]]
    else:
        picks = [e for e, _ in sorted(expiries, key=lambda x: abs(x[1] - TARGET_DTE))[:2]]
    at_exp = [p for p in parsed if p[0] in set(picks)]

    # Walk the moneyness grid and keep the nearest available strike to each
    # target. A strike may be nearest to two adjacent targets when the
    # underlying's strikes are sparse; the set collapses those, so sparse names
    # simply yield fewer rows rather than duplicates.
    keep = {}
    for e in set(picks):
        available = sorted({p[2] for p in at_exp if p[0] == e})
        if not available:
            continue
        ks = set()
        for m in MONEYNESS_GRID:
            ks.add(min(available, key=lambda k: abs(k - spot * m)))
        keep[e] = ks

    # Anything recorded yesterday that is still quotable today stays in, whatever
    # the grid says. This is what preserves per-contract runs across days.
    carried = previous_contracts(symbol, today)

    out = []
    for exp, dte, strike, kind, osym, snap in parsed:
        on_grid = exp in keep and strike in keep[exp]
        if not (on_grid or osym in carried):
            continue
        q = snap.get("latestQuote") or {}
        g = snap.get("greeks") or {}
        bid, ask = q.get("bp"), q.get("ap")
        mid = (bid + ask) / 2 if (bid is not None and ask is not None) else None
        day = snap.get("dailyBar") or {}
        out.append({
            "date": today.isoformat(), "symbol": symbol, "spot": round(spot, 4),
            "quote_time": q.get("t", ""),
            "expiration": exp.isoformat(), "dte": dte,
            "type": kind, "strike": strike,
            "moneyness": round(strike / spot, 6) if spot else "",
            "option_symbol": osym,
            "bid": bid, "ask": ask,
            "mid": round(mid, 6) if mid is not None else "",
            "volume": day.get("v", ""),
            "open_interest": oi_map.get(osym, ("", ""))[0],
            "open_interest_date": oi_map.get(osym, ("", ""))[1],
            "iv": snap.get("impliedVolatility", ""),
            "delta": g.get("delta", ""), "gamma": g.get("gamma", ""),
            "theta": g.get("theta", ""), "vega": g.get("vega", ""),
            "rho": g.get("rho", ""),
        })
    return sorted(out, key=lambda r: (r["expiration"], r["type"], r["strike"]))


# --- the WIDE band, recorded to a SEPARATE file --------------------------------
# On 17 Sep 2026 H3 found the fixed +/-30% band covers 11 standard deviations on
# SPY but only 2 on USO, and USO carried 78% of H3's error. Cboe integrates the
# whole chain. So high-volatility names are ALSO recorded out to WIDE_SIGMAS of
# their own 30-day move, into data/surface_wide.csv, so that H3c - truncation
# bias scales with volatility - can be TESTED rather than asserted.
#
# It is a separate file and a separate pass so the registered surface cannot be
# affected by it in any way:
#   - surface.csv is written by the code above, unchanged, BEFORE any of this runs
#   - H3 and H4 read surface.csv only, so every registered number is reproducible
#   - any failure below is caught and cannot fail the run. That matters more than
#     it looks: a non-zero exit skips the workflow's commit step, so a crash here
#     would lose surface.csv even though it had already been written.
# The fetch and row-building are duplicated from chain() and rows_for() rather
# than shared. Sharing them would mean editing the registered path, and that
# path is irreplaceable: Alpaca's free feed serves only the present.
#
# WIDE_SIGMAS is set where the names that ALREADY track Cboe sit: SPY 8.1, QQQ
# 6.3, IWM 6.1, GLD 4.6 sigmas on the upside, all within 0.35 points of the index.
WIDE_SIGMAS = 5.0
WIDE_CAP = 0.60             # beyond this, listed strikes are sparse and bids zero
WIDE_OUT = Path(__file__).parent / "data" / "surface_wide.csv"


def wide_band(atm_iv, dte):
    """Half-width of the wide band, as a moneyness fraction. Never below the
    registered band, never above WIDE_CAP."""
    try:
        atm_iv, dte = float(atm_iv), float(dte)
    except (TypeError, ValueError):
        return STRIKE_BAND
    if atm_iv <= 0 or dte <= 0:
        return STRIKE_BAND
    return max(STRIKE_BAND, min(WIDE_CAP, WIDE_SIGMAS * atm_iv * (dte / 365.0) ** 0.5))


def wide_targets(band):
    """Moneyness targets strictly OUTSIDE the registered band, at its spacing."""
    step = (2 * STRIKE_BAND) / (STRIKE_COUNT - 1)
    out, m = [], 1 - STRIKE_BAND - step
    while m >= 1 - band - 1e-9:
        out.append(m)
        m -= step
    m = 1 + STRIKE_BAND + step
    while m <= 1 + band + 1e-9:
        out.append(m)
        m += step
    return out


def wide_chain(s, symbol, spot, today, kind, band):
    """chain(), with the band as a parameter instead of the registered constant."""
    p = dict(
        feed=R.OPTION_FEED, limit=1000, type=kind,
        expiration_date_gte=(today + timedelta(days=DTE_WINDOW[0])).isoformat(),
        expiration_date_lte=(today + timedelta(days=DTE_WINDOW[1])).isoformat(),
        strike_price_gte=round(spot * (1 - band), 2),
        strike_price_lte=round(spot * (1 + band), 2))
    out = {}
    for _ in range(R.MAX_PAGES):
        j = R.get(s, f"{R.DATA}/v1beta1/options/snapshots/{symbol}", **p)
        page = j.get("snapshots") or {}
        out.update(page)
        token = j.get("next_page_token")
        if not token or not page:
            break
        p["page_token"] = token
        time.sleep(PACE)
    return out


def wide_select(inner, spot, available_by_expiry, band):
    """{expiry: {strikes}} beyond the registered band, at the inner expiries.

    Pure function, so it can be tested without the network. A strike is kept only
    if it lies strictly outside +/-STRIKE_BAND and was not already recorded in the
    registered file at that expiry, so the two files never overlap.
    """
    inner_at = {}
    for r in inner:
        inner_at.setdefault(r["expiration"], set()).add(float(r["strike"]))
    targets = wide_targets(band)
    keep = {}
    for e in sorted(inner_at):
        avail = sorted(available_by_expiry.get(e, ()))
        if not avail or not targets:
            continue
        ks = set()
        for m in targets:
            k = min(avail, key=lambda x: abs(x - spot * m))
            if abs(k / spot - 1) > STRIKE_BAND and k not in inner_at[e]:
                ks.add(k)
        if ks:
            keep[e] = ks
    return keep


def wide_rows_for(s, symbol, spot, today, inner):
    """Rows beyond the registered band for one symbol. Returns (rows, band)."""
    ivs = []
    for r in inner:
        try:
            if abs(float(r["moneyness"]) - 1) < 0.03 and r["iv"] not in ("", None):
                ivs.append(float(r["iv"]))
        except (TypeError, ValueError, KeyError):
            continue
    if not ivs:
        return [], STRIKE_BAND
    ivs.sort()
    # Sigma on the 30-day horizon, because that is what H3's estimate and Cboe's
    # index both target. NOT the longest expiry present: inner rows include
    # contracts carried forward from earlier days, sometimes at a stale expiry,
    # and sizing on those inflated the band on the first attempt at this.
    band = wide_band(ivs[len(ivs) // 2], TARGET_DTE)
    if band <= STRIKE_BAND + 1e-9:
        return [], band

    snaps = wide_chain(s, symbol, spot, today, "call", band)
    time.sleep(PACE)
    snaps.update(wide_chain(s, symbol, spot, today, "put", band))
    # The two expiries nearest TARGET_DTE: the pair H3 interpolates. A third
    # expiry present only through carry-forward is not extended.
    by_exp = {}
    for r in inner:
        by_exp[r["expiration"]] = int(r["dte"])
    wanted = set(sorted(by_exp, key=lambda e: abs(by_exp[e] - TARGET_DTE))[:2])
    inner = [r for r in inner if r["expiration"] in wanted]
    parsed, avail = [], {}
    for osym, snap in snaps.items():
        try:
            exp, strike, kind = R.parse_occ(osym)
        except ValueError:
            continue
        e = exp.isoformat()
        if e not in wanted:
            continue
        parsed.append((exp, (exp - today).days, strike, kind, osym, snap))
        avail.setdefault(e, set()).add(strike)
    keep = wide_select(inner, spot, avail, band)

    out = []
    for exp, dte, strike, kind, osym, snap in parsed:
        if strike not in keep.get(exp.isoformat(), ()):
            continue
        q = snap.get("latestQuote") or {}
        g = snap.get("greeks") or {}
        bid, ask = q.get("bp"), q.get("ap")
        mid = (bid + ask) / 2 if (bid is not None and ask is not None) else None
        day = snap.get("dailyBar") or {}
        out.append({
            "date": today.isoformat(), "symbol": symbol, "spot": round(spot, 4),
            "quote_time": q.get("t", ""),
            "expiration": exp.isoformat(), "dte": dte,
            "type": kind, "strike": strike,
            "moneyness": round(strike / spot, 6) if spot else "",
            "option_symbol": osym,
            "bid": bid, "ask": ask,
            "mid": round(mid, 6) if mid is not None else "",
            "volume": day.get("v", ""),
            "open_interest": "", "open_interest_date": "",
            "iv": snap.get("impliedVolatility", ""),
            "delta": g.get("delta", ""), "gamma": g.get("gamma", ""),
            "theta": g.get("theta", ""), "vega": g.get("vega", ""),
            "rho": g.get("rho", ""),
        })
    return sorted(out, key=lambda r: (r["expiration"], r["type"], r["strike"])), band


def append_wide(rows, today):
    """append(), for the wide file. Idempotent per (date, option_symbol)."""
    WIDE_OUT.parent.mkdir(parents=True, exist_ok=True)
    new = not WIDE_OUT.exists() or WIDE_OUT.stat().st_size == 0
    seen = set()
    if not new:
        with WIDE_OUT.open(newline="") as f:
            rd = csv.DictReader(f)
            if rd.fieldnames != FIELDS:
                print("    (wide: header mismatch, not appending)")
                return 0
            seen = {(r["date"], r["option_symbol"]) for r in rd}
    fresh = [r for r in rows if (r["date"], r["option_symbol"]) not in seen]
    with WIDE_OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(fresh)
    return len(fresh)


def record_wide(s, spots, rows, today):
    """The wide pass. NEVER raises and never exits: see the note above WIDE_SIGMAS."""
    try:
        by_sym = {}
        for r in rows:
            by_sym.setdefault(r["symbol"], []).append(r)
        wide = []
        for sym in sorted(by_sym):
            try:
                got, band = wide_rows_for(s, sym, spots[sym], today, by_sym[sym])
                if got:
                    wide.extend(got)
                    print(f"  {sym:6s} wide band +/-{band:.0%}: {len(got)} more contracts")
            except Exception as e:
                print(f"  {sym:6s} wide pass failed, registered file unaffected: "
                      f"{type(e).__name__}: {e}")
            time.sleep(PACE)
        if wide:
            n = append_wide(wide, today)
            print(f"Wrote {n} wide row(s) to {WIDE_OUT}")
    except (Exception, SystemExit) as e:
        print(f"Wide pass abandoned, registered file unaffected: {type(e).__name__}: {e}")


def already_recorded(today):
    if not OUT.exists():
        return set()
    with OUT.open(newline="") as f:
        return {r["symbol"] for r in csv.DictReader(f)
                if r.get("date") == today.isoformat()}


def append(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new = not OUT.exists() or OUT.stat().st_size == 0
    if not new:
        with OUT.open(newline="") as f:
            header = next(csv.reader(f), None)
        if header and header != FIELDS:
            sys.exit(f"Refusing to append: {OUT.name} header does not match "
                     f"FIELDS. Resolve by hand rather than writing misaligned "
                     f"rows.")
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)


def main():
    today = date.today()
    if today.weekday() >= 5:
        print(f"{today} is a weekend - nothing to record.")
        return
    done = already_recorded(today)
    todo = [s for s in SURFACE if s not in done]
    for s in [x for x in SURFACE if x in done]:
        print(f"  {s:6s} already recorded for {today}, skipping")
    if not todo:
        print("Nothing to do.")
        return

    s = R.session()
    if not R.is_trading_day(s, today):
        print(f"{today} is a market holiday - nothing to record.")
        return

    try:
        spots = R.spot_prices(s, todo)
    except Exception as e:
        sys.exit(f"Could not fetch spot prices: {e}")

    rows, failed = [], []
    for sym in todo:
        try:
            if sym not in spots:
                raise RuntimeError("no price returned")
            r = rows_for(s, sym, spots[sym], today)
            rows.extend(r)
            vol = sum(int(x["volume"]) for x in r if str(x["volume"]).isdigit())
            exps = sorted({x["expiration"] for x in r})
            oi_n = sum(1 for x in r if str(x["open_interest"]).strip() != "")
            prev = previous_contracts(sym, today)
            kept = len({x["option_symbol"] for x in r} & prev) if prev else 0
            print(f"  {sym:6s} spot {spots[sym]:>9.2f}  {len(r):>3d} contracts  "
                  f"exp {'/'.join(exps)}  volume {vol:,}  oi {oi_n}/{len(r)}"
                  + (f"  carried {kept}/{len(prev)}" if prev else ""))
        except Exception as e:
            failed.append(sym)
            print(f"  {sym:6s} FAILED: {e}")
        time.sleep(PACE)

    if rows:
        append(rows)
        print(f"\nWrote {len(rows)} row(s) to {OUT}")
        # Only after the registered file is safely on disk.
        record_wide(s, spots, rows, today)
    if failed:
        print(f"Failed: {', '.join(failed)} - a gap is not fatal.")


if __name__ == "__main__":
    main()
