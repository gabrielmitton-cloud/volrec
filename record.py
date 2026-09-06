#!/usr/bin/env python3
"""
record.py - daily options snapshot recorder (Alpaca)

Finds the at-the-money call ~30 days out for each ticker in WATCHLIST and
appends one row per ticker per day to data/iv_history.csv.

Historical implied-vol data is the expensive part of options research.
This buys it with time instead of money: run it once a day, and in six
months you have six months of it.

Setup:
    1. Free account at alpaca.markets - paper trading, no brokerage
       application, no funding, no SSN
    2. Dashboard -> switch to Paper Trading -> generate API keys
    3. export ALPACA_KEY="your_key"
       export ALPACA_SECRET="your_secret"
    4. pip install requests
    5. python record.py

Skips weekends and, via Alpaca's market calendar, exchange holidays.

Debugging:
    python record.py --probe SPY    dumps the raw API response so you can
                                    see the actual field names
"""

import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

DATA = "https://data.alpaca.markets"
TRADING = "https://paper-api.alpaca.markets"
WATCHLIST = [
    # broad index ETFs, ascending volatility
    "SPY", "DIA", "QQQ", "IWM", "MDY",
    # non-equity asset classes - volatility driven by different forces
    "GLD", "SLV", "TLT", "IEF", "USO", "UNG", "FXE", "EEM", "EFA",
    # sector ETFs - regime coverage without single-name noise
    "XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLY", "XLB", "XRT",
    # mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    # high-vol growth and speculative
    "NVDA", "TSLA", "AMD", "PLTR", "COIN", "MSTR", "SMCI",
    # low-vol defensives - anchors the bottom of the vol range
    "JNJ", "PG", "KO", "PEP", "WMT", "MCD", "VZ",
    # financials
    "JPM", "BAC", "GS",
    # energy and industrials
    "XOM", "CVX", "CAT", "BA",
    # healthcare and staples
    "UNH", "COST",
    # --- added 2026-09-05, screened live for populated IV/greeks and quotes
    #     tighter than 60% of mid. Original 52 above are unchanged. ---
    # credit and international - vol driven by spreads and geography
    "LQD", "HYG", "FXI",
    # completes the 11 GICS sector SPDRs
    "XLC", "XLRE",
    # industry ETFs - regimes the sector SPDRs do not isolate
    "SMH", "XBI", "KRE", "GDX", "IBIT", "XHB", "XOP",
    # tech and semis single names
    "AVGO", "ORCL", "CRM", "ADBE", "INTC", "MU", "QCOM", "TSM", "NFLX", "CSCO", "TXN",
    # financials
    "MS", "WFC", "C", "AXP", "SCHW",
    # healthcare
    "LLY", "ABBV", "PFE", "MRK", "TMO",
    # consumer
    "HD", "NKE", "TGT", "LOW", "DIS",
    # industrials
    "GE", "DE", "LMT", "UPS", "RTX",
    # energy
    "COP", "SLB", "OXY",
    # utilities and communication
    "NEE", "DUK", "T", "CMCSA",
    # high-vol and speculative - anchors the top of the vol range
    "RIVN", "SOFI", "HOOD", "MARA", "RBLX", "SNOW", "CRWD",
]
TARGET_DTE = 30
DTE_WINDOW = (21, 45)
STRIKE_BAND = 0.08          # only pull strikes within +/-8% of spot
OPTION_FEED = "indicative"  # free feed; "opra" needs a paid subscription
STOCK_FEED = "iex"          # free feed; "sip" needs a paid subscription
MAX_PAGES = 10             # safety cap; one page holds 1000 contracts
PACE = 0.40                # 150 req/min. The documented cap is 200/min and it
                           # is undocumented whether the data and trading APIs
                           # share one bucket, so leave real headroom.
OUT = Path(__file__).parent / "data" / "iv_history.csv"

FIELDS = [
    "date", "symbol", "spot", "expiration", "dte", "strike", "moneyness",
    "option_symbol", "bid", "ask", "mid", "iv", "delta", "gamma", "theta",
    "vega", "rho",
    # added 2026-09-05. quote_time detects stale quotes; volume is a liquidity
    # filter; the put at the SAME strike lets you average call and put IV, which
    # cancels the dividend/borrow error that biases call IV down on its own.
    "quote_time", "volume",
    "put_symbol", "put_bid", "put_ask", "put_mid", "put_iv",
    # added 2026-09-06. A SECOND expiry, already inside the response the near
    # leg is paid for - zero extra requests. Two points make a term-structure
    # slope, which a single expiry cannot see and which cannot be reconstructed
    # later: there is no historical option-quote endpoint at any price.
    #
    # The far leg is the expiry FURTHEST from the near one inside DTE_WINDOW,
    # which for a minority of tickers is SHORTER-dated, not longer. So never
    # read the sign of (far_iv - iv) directly. Always divide by the maturity
    # gap, which carries the sign for you:
    #     slope per day = (far_iv - iv) / (far_dte - dte)
    # A positive slope is then an upward-sloping curve in every case.
    "far_symbol", "far_expiration", "far_dte", "far_strike",
    "far_bid", "far_ask", "far_mid", "far_iv",
]


def session():
    key, secret = os.environ.get("ALPACA_KEY"), os.environ.get("ALPACA_SECRET")
    if not key or not secret:
        sys.exit("ALPACA_KEY / ALPACA_SECRET not set. Generate paper-trading "
                 "keys at app.alpaca.markets, then:\n"
                 '  export ALPACA_KEY="..."\n  export ALPACA_SECRET="..."')
    s = requests.Session()
    s.headers.update({
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "accept": "application/json",
    })
    return s


def get(s, url, **params):
    for attempt in range(4):
        r = s.get(url, params=params, timeout=25)
        if r.status_code != 429:
            break
        wait = 2 ** attempt
        print(f"    rate limited, waiting {wait}s")
        time.sleep(wait)
    if r.status_code == 401:
        raise RuntimeError("401 - keys rejected. Check you copied the PAPER keys.")
    if r.status_code == 403:
        raise RuntimeError(f"403 - feed not available on your plan "
                           f"(trying '{OPTION_FEED}'/'{STOCK_FEED}')")
    r.raise_for_status()
    return r.json()


def parse_occ(sym):
    """SPY260220C00640000 -> (date(2026,2,20), 640.0, 'C'). Strike is x1000."""
    i = 0
    while i < len(sym) and not sym[i].isdigit():
        i += 1
    body = sym[i:]
    if len(body) < 15:
        raise ValueError(f"unparseable option symbol: {sym}")
    d = datetime.strptime(body[:6], "%y%m%d").date()
    return d, int(body[7:15]) / 1000.0, body[6].upper()


def spot_prices(s, symbols):
    j = get(s, f"{DATA}/v2/stocks/snapshots",
            symbols=",".join(symbols), feed=STOCK_FEED)
    snaps = j.get("snapshots", j)      # endpoint has returned both shapes
    out = {}
    for sym, snap in snaps.items():
        if not isinstance(snap, dict):
            continue
        px = ((snap.get("latestTrade") or {}).get("p")
              or (snap.get("dailyBar") or {}).get("c")
              or (snap.get("prevDailyBar") or {}).get("c"))
        if px:
            out[sym] = float(px)
    return out


def snapshot(s, symbol, spot, today):
    params = dict(
        feed=OPTION_FEED, limit=1000,
        expiration_date_gte=(today + timedelta(days=DTE_WINDOW[0])).isoformat(),
        expiration_date_lte=(today + timedelta(days=DTE_WINDOW[1])).isoformat(),
        strike_price_gte=round(spot * (1 - STRIKE_BAND), 2),
        strike_price_lte=round(spot * (1 + STRIKE_BAND), 2))
    def chain(kind):
        """One side of the chain. Calls and puts are fetched separately and
        type-filtered so each response stays inside a single 1000-contract
        page; the paging loop below is a safety net, not the normal path.
        A truncated response would not error - it would silently hide the
        true at-the-money contract and record the wrong one."""
        out, p = {}, dict(params, type=kind)
        for _ in range(MAX_PAGES):
            j = get(s, f"{DATA}/v1beta1/options/snapshots/{symbol}", **p)
            page = j.get("snapshots") or {}
            out.update(page)
            token = j.get("next_page_token")
            if not token or not page:
                break
            p["page_token"] = token
            time.sleep(PACE)
        return out

    snaps = chain("call")
    if not snaps:
        raise RuntimeError("no contracts returned in the strike/expiry window")
    time.sleep(PACE)          # keep the two-request burst inside the rate limit
    puts = chain("put")

    best = None
    for osym, snap in snaps.items():
        try:
            exp, strike, kind = parse_occ(osym)
        except ValueError:
            continue
        if kind != "C":
            continue
        dte = (exp - today).days
        if not (DTE_WINDOW[0] <= dte <= DTE_WINDOW[1]):
            continue
        # prefer the expiry nearest TARGET_DTE, then the strike nearest spot
        score = (abs(dte - TARGET_DTE), abs(strike - spot))
        if best is None or score < best[0]:
            best = (score, osym, snap, exp, strike, dte)
    if best is None:
        raise RuntimeError("no call contracts matched after filtering")

    _, osym, snap, exp, strike, dte = best

    # The far leg: the expiry furthest from the near one still inside
    # DTE_WINDOW, at the strike nearest spot. Same response, no extra request.
    far = None
    for osym2, snap2 in snaps.items():
        try:
            exp2, strike2, kind2 = parse_occ(osym2)
        except ValueError:
            continue
        if kind2 != "C" or exp2 == exp:
            continue
        dte2 = (exp2 - today).days
        if not (DTE_WINDOW[0] <= dte2 <= DTE_WINDOW[1]):
            continue
        # furthest expiry from the near leg, then - to break the symmetric tie
        # deterministically - the LONGER side, then the strike nearest spot.
        # Without the tie-break, an expiry pair straddling the near leg at equal
        # distance would be picked by dict order and the far leg could flip
        # between runs, silently corrupting the slope series.
        score2 = (-abs(dte2 - dte), -dte2, abs(strike2 - spot))
        if far is None or score2 < far[0]:
            far = (score2, osym2, snap2, exp2, strike2, dte2)

    q = snap.get("latestQuote") or {}
    g = snap.get("greeks") or {}
    bid, ask = q.get("bp"), q.get("ap")
    mid = (round((bid + ask) / 2, 4)
           if bid is not None and ask is not None else None)

    # the put at the same strike and expiry, if it came back in the same pages
    psym = osym.replace(f"{exp:%y%m%d}C", f"{exp:%y%m%d}P", 1)
    put = puts.get(psym) or {}
    pq = put.get("latestQuote") or {}
    pbid, pask = pq.get("bp"), pq.get("ap")
    pmid = (round((pbid + pask) / 2, 4)
            if pbid is not None and pask is not None else None)

    return {
        "date": today.isoformat(), "symbol": symbol, "spot": round(spot, 4),
        "expiration": exp.isoformat(), "dte": dte, "strike": strike,
        "moneyness": round(strike / spot, 4), "option_symbol": osym,
        "bid": bid, "ask": ask, "mid": mid,
        "iv": snap.get("impliedVolatility"),
        "delta": g.get("delta"), "gamma": g.get("gamma"),
        "theta": g.get("theta"), "vega": g.get("vega"), "rho": g.get("rho"),
        "quote_time": q.get("t"),
        "volume": (snap.get("dailyBar") or {}).get("v"),
        "put_symbol": psym if put else None,
        "put_bid": pbid, "put_ask": pask, "put_mid": pmid,
        "put_iv": put.get("impliedVolatility") if put else None,
        **_far_fields(far),
    }


def _far_fields(far):
    """Columns for the second expiry. All None when the underlying has only one
    expiry in the window - MDY, FXE and XLRE lack weeklies, so they legitimately
    have no far leg and the slope is simply unavailable for them."""
    if far is None:
        return {k: None for k in ("far_symbol", "far_expiration", "far_dte",
                                  "far_strike", "far_bid", "far_ask",
                                  "far_mid", "far_iv")}
    _, fsym, fsnap, fexp, fstrike, fdte = far
    fq = fsnap.get("latestQuote") or {}
    fbid, fask = fq.get("bp"), fq.get("ap")
    return {
        "far_symbol": fsym, "far_expiration": fexp.isoformat(), "far_dte": fdte,
        "far_strike": fstrike, "far_bid": fbid, "far_ask": fask,
        "far_mid": (round((fbid + fask) / 2, 4)
                    if fbid is not None and fask is not None else None),
        "far_iv": fsnap.get("impliedVolatility"),
    }


def is_trading_day(s, day):
    """True if `day` is a US equity trading day.

    Alpaca's calendar lists only trading days, so an empty response means the
    market was closed - a holiday the weekday check cannot see.

    Fails OPEN on error: a stray holiday row can be dropped in analysis, but a
    real trading day missed is gone for good.
    """
    try:
        j = get(s, f"{TRADING}/v2/calendar",
                start=day.isoformat(), end=day.isoformat())
    except Exception as e:
        print(f"  calendar check failed ({e}) - recording anyway")
        return True
    if not isinstance(j, list):
        print("  calendar returned an unexpected shape - recording anyway")
        return True
    return any(d.get("date") == day.isoformat() for d in j)


def already_recorded(today):
    if not OUT.exists():
        return set()
    with OUT.open() as f:
        return {r["symbol"] for r in csv.DictReader(f)
                if r.get("date") == today.isoformat()}


def migrate_header():
    """Bring an existing data file up to the current FIELDS.

    Appending rows whose columns do not match the file's header silently
    writes misaligned data - the kind of corruption you only notice months
    later. So check first, and handle the two cases differently:

      - columns only ADDED: rewrite the header and pad existing rows with
        empty values. Every existing value is preserved; nothing is rewritten
        in place. A one-time backup is left beside the file.
      - columns REMOVED or RENAMED: refuse and exit. That would destroy data,
        and no schema change is worth losing the one artifact that cannot be
        rebuilt.
    """
    if not OUT.exists() or OUT.stat().st_size == 0:
        return
    with OUT.open(newline="") as f:
        header = next(csv.reader(f), None)
    if not header or header == FIELDS:
        return

    dropped = [c for c in header if c not in FIELDS]
    if dropped:
        sys.exit(f"Refusing to touch {OUT.name}: the file has column(s) "
                 f"{dropped} that FIELDS no longer declares. Migrating would "
                 f"discard recorded data. Resolve this by hand.")

    added = [c for c in FIELDS if c not in header]
    with OUT.open(newline="") as f:
        old_rows = list(csv.DictReader(f))
    backup = OUT.with_name(f"{OUT.stem}.pre-{len(header)}col{OUT.suffix}")
    if not backup.exists():
        backup.write_bytes(OUT.read_bytes())
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in old_rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"  migrated {OUT.name}: added {added}; "
          f"{len(old_rows)} existing row(s) padded, no values changed. "
          f"Backup at {backup.name}.")


def append(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    migrate_header()
    new = not OUT.exists() or OUT.stat().st_size == 0
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)


def probe(sym):
    s = session()
    today = date.today()
    spots = spot_prices(s, [sym])
    print(f"--- stock snapshot ---\nspot: {spots}\n")
    spot = spots.get(sym, 100.0)
    j = get(s, f"{DATA}/v1beta1/options/snapshots/{sym}",
            feed=OPTION_FEED, type="call", limit=3,
            expiration_date_gte=(today + timedelta(days=DTE_WINDOW[0])).isoformat(),
            expiration_date_lte=(today + timedelta(days=DTE_WINDOW[1])).isoformat(),
            strike_price_gte=round(spot * .98, 2),
            strike_price_lte=round(spot * 1.02, 2))
    print("--- raw option snapshot (first 3) ---")
    print(json.dumps(j, indent=2)[:3000])


def main():
    if "--probe" in sys.argv:
        i = sys.argv.index("--probe")
        probe(sys.argv[i + 1] if len(sys.argv) > i + 1 else "SPY")
        return

    today = date.today()
    if today.weekday() >= 5:
        print(f"{today} is a weekend - markets closed, nothing to record.")
        return

    done = already_recorded(today)
    todo = [s for s in WATCHLIST if s not in done]
    for s in [x for x in WATCHLIST if x in done]:
        print(f"  {s:6s} already recorded for {today}, skipping")
    if not todo:
        print("Nothing to do.")
        return

    s = session()
    if not is_trading_day(s, today):
        print(f"{today} is a market holiday - nothing to record.")
        return

    try:
        spots = spot_prices(s, todo)
    except Exception as e:
        sys.exit(f"Could not fetch stock prices: {e}")

    rows, failed = [], []
    for sym in todo:
        try:
            if sym not in spots:
                raise RuntimeError("no price returned")
            row = snapshot(s, sym, spots[sym], today)
            rows.append(row)
            iv = row["iv"]
            iv_s = f"{iv:.4f}" if isinstance(iv, (int, float)) else "MISSING"
            print(f"  {sym:6s} spot {row['spot']:>9.2f}  "
                  f"strike {row['strike']:>8.2f}  {row['dte']:>2d}d  iv {iv_s}")
        except Exception as e:
            failed.append(sym)
            print(f"  {sym:6s} FAILED: {e}")
        time.sleep(PACE)   # see PACE: headroom under the 200/min free-tier cap

    if rows:
        append(rows)
        print(f"\nWrote {len(rows)} row(s) to {OUT}")
        if all(r["iv"] is None for r in rows):
            print("WARNING: every iv came back empty. Run with --probe SPY "
                  "to see the raw response.")
    if failed:
        print(f"Failed: {', '.join(failed)} - a gap day is not fatal.")


if __name__ == "__main__":
    main()
