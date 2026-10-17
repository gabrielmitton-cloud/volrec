#!/usr/bin/env python3
"""H7's reading - the free feed, run through Cboe's own rules, against OPRA and the index.
See hypotheses/2026-10-08-h7-free-feed-cboe-replica.md (registered 8 Oct 2026, before the first
monthly-leg row existed). This file implements its specification and nothing more.

Cboe's rules come from tools/ovx_replicate.py (cboe_sigma2, blend30, minutes_to, chain_at), the
same functions the 8 Oct replication validated (GVZ within a median 0.07 points) and the pressure
test pins with known answers. Nothing is re-implemented here.

Per (date, symbol) in data/surface_monthly.csv, 9 Oct - 11 Nov 2026, after-close days dropped:
  free  = Cboe's index computed from the free feed's monthly-leg quotes at their snapshot minute;
  opra  = the same, from Databento OPRA at that minute (OPRA_M_<sym>_<date>.csv, bought for H7);
  close = Cboe's published close (OVX for USO, GVZ for GLD).
H7a: mean |free - opra| <= 0.25 points, USO and GLD each. H7b: GLD mean |free - GVZ| <= 0.30.
H7c: USO free - OVX, descriptive. Minimum 10 days with both readings and an index close.

Run: VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra FRED_KEY=use-cache python tools/h7_reader.py
Output is aggregates only.
"""
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")

import modelfree                                   # noqa: E402
import opra_reference as ore                       # noqa: E402
import ovx_replicate as O                          # noqa: E402

H7_START, H7_END = "2026-10-09", "2026-11-11"
MIN_DAYS = 10
BAR_A, BAR_B = 0.25, 0.30
INDEX = {"USO": "OVX", "GLD": "GVZ"}


def quotes_from_rows(rows):
    """surface_monthly rows -> {expiry date: {(strike, 'C'|'P'): (bid, ask)}}, each quote through
    O.cboe_quote - the same reading the OPRA side gets in O.chain_at, so the two feeds' different
    ways of writing "no bid" (the free feed 0, Databento a blank) cannot open a gap between them."""
    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    out = {}
    for r in rows:
        e = date.fromisoformat(r["expiration"])
        out.setdefault(e, {})[(float(r["strike"]), r["type"])] = O.cboe_quote(num(r["bid"]), num(r["ask"]))
    return out


def replica(chains, exps, when, R):
    """Cboe's 30-day index from two expiries' quotes at `when`, or None if either term fails."""
    if len(exps) != 2:
        return None
    terms = []
    for e in exps:
        mins = O.minutes_to(e, when)
        got = O.cboe_sigma2(chains.get(e, {}), R, mins / O.MIN365) if mins > 0 else None
        if not got:
            return None
        terms.append((mins, got[0]))
    (m1, s1), (m2, s2) = terms
    return O.blend30(m1, s1, m2, s2)


def match_chain(opra_chain, free_chain):
    """The OPRA chain cut to the (strike, type) pairs the free file holds, expiry by expiry. Added 17 Oct
    2026 for the COMPANION reading (verdict-code review, Gabriel approved): the free monthly file stops at
    +/-60% of spot while OPRA lists every strike, so the registered free-minus-OPRA gap also measures
    coverage. On matched strikes the two replicas integrate the same contracts. Pure."""
    return {e: {k: q for k, q in opra_chain.get(e, {}).items() if k in free_chain.get(e, {})}
            for e in opra_chain}


def edge_limited(free_chain):
    """Expiries where Cboe's walk would run off the free file's recorded edge with live bids still there:
    the highest call or the lowest put carries a bid above zero. Pure."""
    out = []
    for e, q in sorted(free_chain.items()):
        calls = sorted(k for k, t in q if t == "C")
        puts = sorted(k for k, t in q if t == "P")
        hi = q.get((calls[-1], "C")) if calls else None
        lo = q.get((puts[0], "P")) if puts else None
        if (hi and hi[0] and hi[0] > 0) or (lo and lo[0] and lo[0] > 0):
            out.append(e)
    return out


def day_reading(day, symbol, R, opra_dir):
    rows = ore.monthly_recorded(day, symbol)
    when = ore.snapshot_minute(rows)
    if not rows or not when:
        return None
    exps = sorted({date.fromisoformat(r["expiration"]) for r in rows})
    fchain = quotes_from_rows(rows)
    free = replica(fchain, exps, when, R)
    path = Path(opra_dir) / f"OPRA_M_{symbol}_{day}.csv"
    ochain = O.chain_at(ore.load_opra(path), when, symbol) if path.exists() else None
    opra = replica(ochain, exps, when, R) if ochain is not None else None
    # The companion (17 Oct): the same replica on OPRA cut to the free file's strikes. The registered
    # reading ("opra") is computed exactly as before and never reads this.
    opra_m = replica(match_chain(ochain, fchain), exps, when, R) if ochain is not None else None
    return {"day": day, "symbol": symbol, "free": free, "opra": opra, "legs": [(e - when.date()).days for e in exps],
            "opra_matched": opra_m, "edge": [(e - when.date()).days for e in edge_limited(fchain) if e in exps]}


def summarise(readings, closes):
    """-> {symbol: {"a": (n, mean |free-opra|), "b": (n, mean |free-close|), "c": (n, mean free-close)}}.
    A day counts only with both readings AND the index close (the registered minimum's wording)."""
    out = {}
    for sym in INDEX:
        rs = [x for x in readings if x["symbol"] == sym and x["free"] is not None and x["opra"] is not None
              and closes.get(sym, {}).get(x["day"]) is not None]
        n = len(rs)
        if not n:
            out[sym] = {"a": (0, None), "b": (0, None), "c": (0, None)}
            continue
        cl = closes[sym]
        out[sym] = {"a": (n, sum(abs(x["free"] - x["opra"]) for x in rs) / n),
                    "b": (n, sum(abs(x["free"] - cl[x["day"]]) for x in rs) / n),
                    "c": (n, sum(x["free"] - cl[x["day"]] for x in rs) / n)}
    return out


def verdicts(s):
    """Registered reading. H7a needs BOTH symbols at the minimum; H7b is GLD only."""
    a_ok = all(s[k]["a"][0] >= MIN_DAYS for k in INDEX)
    b_ok = s["GLD"]["b"][0] >= MIN_DAYS
    h7a = None if not a_ok else ("HOLDS" if all(s[k]["a"][1] <= BAR_A for k in INDEX) else "FAILS")
    h7b = None if not b_ok else ("HOLDS" if s["GLD"]["b"][1] <= BAR_B else "FAILS")
    return h7a, h7b


def main():
    import analyze
    from panel_health import AFTER_CLOSE_DAYS
    dropped = {d.isoformat() for d in AFTER_CLOSE_DAYS}
    r = modelfree.risk_free()
    R = O.bey_to_continuous(r)
    vol = analyze.fetch_market_vol(sorted(INDEX.values()))
    closes = {sym: {k: v for k, v in (vol.get(ix) or {}).items() if not k.startswith("_")} for sym, ix in INDEX.items()}
    print(f"H7 - the free feed through Cboe's own rules, {H7_START} to {H7_END}; r = {r:.3%} (DGS1MO)\n")
    print(f"{'date':<11}{'sym':<5}{'free':>8}{'OPRA':>8}{'close':>8}{'free-OPRA':>11}{'free-close':>11}  legs")
    readings, waiting = [], []
    for day, sym in ore.monthly_days():
        if not (H7_START <= day <= H7_END) or sym not in INDEX or day in dropped:
            continue
        x = day_reading(day, sym, R, ore.DATA_DIR)
        if not x:
            continue
        readings.append(x)
        c = closes[sym].get(day)
        # 9 Oct 2026: OPRA for day D is served historically only about a day later and Cboe's
        # closes can lag, so the verdict writer waits while any day in the window lacks either.
        if not (Path(ore.DATA_DIR) / f"OPRA_M_{sym}_{day}.csv").exists():
            waiting.append(f"{day} {sym} OPRA")
        if c is None:
            waiting.append(f"{day} {sym} {INDEX[sym]} close")
        f = lambda v: f"{v:8.2f}" if v is not None else "     n/a"
        d = lambda a, b: f"{a - b:+11.2f}" if a is not None and b is not None else "        n/a"
        print(f"{day:<11}{sym:<5}{f(x['free'])}{f(x['opra'])}{f(c)}{d(x['free'], x['opra'])}{d(x['free'], c)}  {x['legs']}")
    s = summarise(readings, closes)
    print()
    for sym in INDEX:
        n, m = s[sym]["a"]
        print(f"H7a {sym}: n={n} mean |free - OPRA| {'n/a' if m is None else f'{m:.3f}'} (bar {BAR_A})")
    n, m = s["GLD"]["b"]
    print(f"H7b GLD: n={n} mean |free - GVZ| {'n/a' if m is None else f'{m:.3f}'} (bar {BAR_B})")
    n, m = s["USO"]["c"]
    print(f"H7c USO: n={n} mean free - OVX {'n/a' if m is None else f'{m:+.3f}'} (descriptive)")
    h7a, h7b = verdicts(s)
    print(f"H7a {h7a or f'NOT YET (minimum {MIN_DAYS} days each)'}; H7b {h7b or f'NOT YET (minimum {MIN_DAYS} days)'}")
    print(f"H7 waiting on: {', '.join(waiting) if waiting else 'nothing'}")
    if "--matched" in sys.argv:
        print_companion(readings)
    print(f"\n{ore.ATTRIBUTION}")


def print_companion(readings):
    """The COMPANION reading (17 Oct 2026): beside, never instead of, the registered H7a above."""
    print("\n-- COMPANION (dated 17 Oct 2026; NOT the registered H7a): OPRA cut to the free file's strikes")
    print(f"{'date':<11}{'sym':<5}{'free':>8}{'OPRA':>8}{'matched':>9}{'free-matched':>14}  walk ends at the free edge")
    for x in readings:
        f = lambda v: f"{v:8.2f}" if v is not None else "     n/a"   # noqa: E731
        dm = (f"{x['free'] - x['opra_matched']:+14.2f}" if x["free"] is not None and x.get("opra_matched") is not None
              else "           n/a")
        print(f"{x['day']:<11}{x['symbol']:<5}{f(x['free'])}{f(x['opra'])} {f(x.get('opra_matched'))}{dm}  "
              f"{'legs ' + str(x['edge']) if x.get('edge') else '-'}")
    for sym in INDEX:
        rs = [x for x in readings if x["symbol"] == sym and x["free"] is not None and x.get("opra_matched") is not None]
        m = sum(abs(x["free"] - x["opra_matched"]) for x in rs) / len(rs) if rs else None
        e = sum(1 for x in rs if x.get("edge"))
        print(f"companion H7a {sym}: n={len(rs)} mean |free - OPRA on matched strikes| "
              f"{'n/a' if m is None else f'{m:.3f}'} (registered bar {BAR_A}, for comparison only); "
              f"walk ran off the free edge on {e} of {len(rs)} days")


if __name__ == "__main__":
    main()
