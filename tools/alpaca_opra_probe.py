"""Does Alpaca's free plan serve OPRA data once it is older than 15 minutes? (added 9 Oct 2026)

The 9 Oct research report quoted Alpaca's own pages against each other: one says "Data older
than 15 minutes is accessible on all feeds", another that OPRA "is only available to subscribed
users". This asks the API directly, for one USO call from the free chain on the previous trading day,
and prints ONLY status codes, record counts and aggregate agreement - never a price, because the
Actions log of a public repository is publication (Alpaca's terms forbid republishing its data).

    ALPACA_KEY=... ALPACA_SECRET=... python tools/alpaca_opra_probe.py [--day YYYY-MM-DD]

ANSWER (run 38015882270, 10 Oct 2026): the historical bars and trades endpoints reject any `feed`
parameter (HTTP 400) and serve a single source; latest quotes and snapshots refuse feed=opra with
HTTP 403 "OPRA agreement is not signed". There is no historical quotes endpoint, so the free plan
offers no OPRA quote reference. Databento remains the reference (HANDOFF 18).
"""
import argparse
import os
import sys
from datetime import date, timedelta

import requests

DATA = "https://data.alpaca.markets"


def prev_weekday(d):
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def call(s, path, **params):
    r = s.get(f"{DATA}{path}", params=params, timeout=30)
    try:
        j = r.json()
    except ValueError:
        j = {}
    return r.status_code, j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", help="trading day to ask about (default: previous weekday)")
    a = ap.parse_args()
    key, sec = os.environ.get("ALPACA_KEY"), os.environ.get("ALPACA_SECRET")
    if not key or not sec:
        sys.exit("ALPACA_KEY / ALPACA_SECRET not set")
    s = requests.Session()
    s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
    day = date.fromisoformat(a.day) if a.day else prev_weekday(date.today())

    # one contract that exists, from the free chain (the symbol is not market data)
    st, j = call(s, "/v1beta1/options/snapshots/USO", feed="indicative", type="call", limit=200)
    snaps = j.get("snapshots") or {}
    if st != 200 or not snaps:
        sys.exit(f"chain lookup failed: HTTP {st}")
    syms = sorted(snaps)
    sym = syms[len(syms) // 2]
    print(f"contract: {sym}   day asked about: {day}")

    start, end = f"{day}T13:30:00Z", f"{day}T20:00:00Z"
    results = {}
    for feed in ("indicative", "opra", None):
        for kind, path, extra in (("bars", "/v1beta1/options/bars", {"timeframe": "1Min"}),
                                  ("trades", "/v1beta1/options/trades", {})):
            p = dict(symbols=sym, start=start, end=end, limit=10000, **extra)
            if feed:
                p["feed"] = feed
            st, j = call(s, path, **p)
            rows = (j.get(kind) or {}).get(sym, []) if st == 200 else []
            results[(feed, kind)] = rows
            msg = j.get("message", "") if st != 200 else ""
            print(f"  {kind:6s} feed={feed or '(none)':10s} HTTP {st}  records {len(rows):5d}  {msg}")
    for feed in ("indicative", "opra"):  # real-time endpoints: expected to refuse OPRA on a free plan
        for kind, path in (("latest quote", "/v1beta1/options/quotes/latest"),
                           ("snapshot", "/v1beta1/options/snapshots")):
            st, j = call(s, path, symbols=sym, feed=feed)
            msg = j.get("message", "") if st != 200 else ""
            print(f"  {kind:12s} feed={feed:10s} HTTP {st}  {msg}")

    # aggregate comparison only: do the "opra" bars differ from the indicative ones?
    for kind, field in (("bars", "c"), ("trades", "p")):
        ind, opr = results[("indicative", kind)], results[("opra", kind)]
        if ind and opr:
            ki = {r["t"]: r.get(field) for r in ind}
            ko = {r["t"]: r.get(field) for r in opr}
            both = set(ki) & set(ko)
            same = sum(ki[t] == ko[t] for t in both)
            print(f"  {kind}: indicative {len(ki)}, opra {len(ko)}, same timestamps {len(both)}, "
                  f"identical {field} on {same} of them")


if __name__ == "__main__":
    main()
