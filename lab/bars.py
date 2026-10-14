#!/usr/bin/env python3
"""lab/ - daily closes for the five funds (EXPLORATORY). RAW closes settle options (listed strikes
are never back-adjusted: USO's 1-for-8 reverse split on 29 Apr 2020); ADJUSTED closes give realised
volatility, as analyze.py does. Fetched only inside GitHub Actions (.github/workflows/lab_bars.yml)
so the Alpaca keys stay in GitHub's secrets; the CSV is kept outside every repository.

  python lab/bars.py --start 2016-01-01 --end 2026-08-31 --out lab_bars.csv     (CI only)
"""
import argparse
import csv
import os
import sys
from pathlib import Path

FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
BARS_FILE = Path(os.environ.get("VOLREC_LAB_BARS") or
                 Path.home() / "Documents" / "volrec-licensed" / "lab-bars" / "lab_bars.csv")
DATA_URL = "https://data.alpaca.markets"


def fetch(symbols, start, end, adjustment, key, secret, feed="sip"):
    import requests
    s = requests.Session()
    s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "accept": "application/json"})
    out, token = {x: {} for x in symbols}, None
    while True:
        p = dict(symbols=",".join(symbols), timeframe="1Day", feed=feed, start=start, end=end,
                 limit=10000, adjustment=adjustment)
        if token:
            p["page_token"] = token
        r = s.get(f"{DATA_URL}/v2/stocks/bars", params=p, timeout=30)
        r.raise_for_status()
        j = r.json()
        for sym, bs in (j.get("bars") or {}).items():
            for b in bs:
                out[sym][b["t"][:10]] = b["c"]
        token = j.get("next_page_token")
        if not token:
            return out


def write_csv(path, raw, adj):
    rows = sorted((d, sym, raw[sym][d], adj[sym].get(d)) for sym in raw for d in raw[sym])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "symbol", "raw_close", "adj_close"])
        w.writerows(rows)
    return len(rows)


def load(path=BARS_FILE):
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["symbol"], {})[r["date"]] = (float(r["raw_close"]), float(r["adj_close"]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key, sec = os.environ.get("ALPACA_KEY"), os.environ.get("ALPACA_SECRET")
    if not key or not sec:
        sys.exit("ALPACA_KEY / ALPACA_SECRET not set")
    raw = fetch(list(FUNDS), a.start, a.end, "raw", key, sec)
    adj = fetch(list(FUNDS), a.start, a.end, "all", key, sec)
    n = write_csv(a.out, raw, adj)
    print(f"{n} rows; first/last per fund: " + "; ".join(
        f"{s} {min(raw[s])}..{max(raw[s])} ({len(raw[s])})" for s in FUNDS if raw[s]))


if __name__ == "__main__":
    main()
