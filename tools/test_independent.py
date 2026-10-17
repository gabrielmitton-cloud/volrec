"""Known-answer tests for tools/independent_replica.py - on its own terms, not by agreeing with the project
(tools/independent_check.py does that). Synthetic chains only; nothing here reads recorded or licensed data.

  python tools/test_independent.py
"""
import csv
import math
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import NormalDist

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / "tools")]
import independent_replica as IR   # noqa: E402

fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


_N = NormalDist().cdf


def bs(S, K, T, r, s, cp):
    d1 = (math.log(S / K) + (r + s * s / 2) * T) / (s * math.sqrt(T))
    d2 = d1 - s * math.sqrt(T)
    return S * _N(d1) - K * math.exp(-r * T) * _N(d2) if cp == "C" else K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)


def bs_rows(S, r, s, dtes, lo, hi, step):
    """A Black-Scholes chain at flat vol s: bid/ask 2% either side of the model price, so the mid is exact."""
    rows = []
    for d in dtes:
        k = lo
        while k <= hi + 1e-9:
            for cp in "CP":
                m = bs(S, k, d / 365, r, s, cp)
                rows.append({"expiration": f"E{d:03d}", "dte": str(d), "strike": str(k), "type": cp,
                             "bid": repr(0.98 * m), "ask": repr(1.02 * m), "option_symbol": f"X{d}{cp}{k}"})
            k = round(k + step, 6)
    return rows


print("=== part 1: Cboe's variance sum recovers a known volatility ===")
dense = IR.h3_day(bs_rows(100, 0.039, 0.30, (23, 37), 30, 300, 0.5), [], 0.039)
check(f"flat 30% vol, dense strikes (0.5 apart, 30-300): reads 30.00 within 0.05 (got {dense['reg']:.4f})",
      abs(dense["reg"] - 30.0) < 0.05)
check("with every bid live, the registered rule and Cboe's rule read the same", abs(dense["reg"] - dense["reg_cboe"]) < 1e-12)
coarse = IR.h3_day(bs_rows(100, 0.039, 0.30, (23, 37), 60, 160, 2.5), [], 0.039)["reg"]
check(f"coarser, narrower strikes move further from 30 (discretisation; got {coarse:.4f})", abs(coarse - 30) > abs(dense["reg"] - 30))
lo_vol = IR.h3_day(bs_rows(100, 0.039, 0.15, (23, 37), 30, 300, 0.5), [], 0.039)["reg"]
check(f"flat 15% vol reads 15.00 within 0.05 (got {lo_vol:.4f})", abs(lo_vol - 15.0) < 0.05)
one = IR.h3_day(bs_rows(100, 0.039, 0.30, (31, 38), 30, 300, 0.5), [], 0.039)
check(f"no expiry at or under 30 days: the nearest (31d) alone, scaled (legs {one['legs']}, {one['reg']:.3f})",
      one["legs"] == [31] and abs(one["reg"] - 30.0) < 0.05)

print("\n=== part 1: the expiry pair ===")
check("pair: last at or under 30, first over - {21, 28, 35} -> 28 and 35",
      IR.pick_pair({"a": 21, "b": 28, "c": 35}) == ("b", "c"))
check("pair: exactly 30 counts as 'at or under'", IR.pick_pair({"a": 30, "b": 37}) == ("a", "b"))
check("pair: none under 30 -> the single nearest", IR.pick_pair({"a": 31, "b": 38}) == ("a",))

print("\n=== part 1: the three quote rules (60% vol, so the wings carry weight) ===")
base = bs_rows(100, 0.039, 0.60, (23, 37), 50, 160, 1)
PAIR = ("E023", "E037")


def with_put(rows, strike, bid, ask, dte=23):
    out = [dict(r) for r in rows]
    for r in out:
        if r["type"] == "P" and float(r["strike"]) == strike and r["dte"] == str(dte):
            r["bid"], r["ask"] = bid, ask
    return out


def read(rows, rule):
    return IR.vol30(*IR.quotes(rows), PAIR, 0.039, rule)


# Put wing on the 23-day leg: zero-bid stubs (ask 3.00) at 80 and 79, live quotes from 78 down.
stub = with_put(with_put(base, 80.0, "0", "3.00"), 79.0, "0", "3.00")
v = {rule: read(stub, rule) for rule in ("reg", "skip", "cboe")}
check(f"reg counts the stubs at half their ask, so it reads highest: reg {v['reg']:.3f} - skip {v['skip']:.3f} > 0.2",
      v["reg"] - v["skip"] > 0.2)
check(f"Cboe's rule stops at the two zero bids and drops 78 and below: skip {v['skip']:.3f} - cboe {v['cboe']:.3f} > 0.2",
      v["skip"] - v["cboe"] > 0.2)
check(f"skipping two interior strikes on a smooth chain barely moves it (skip {v['skip']:.3f} vs 60 within 0.05)",
      abs(v["skip"] - 60) < 0.05)
far = with_put(stub, 55.0, "1.00", "1.10")
check("a strike beyond the stop (55) moves 'skip' but never Cboe's rule",
      abs(read(far, "skip") - v["skip"]) > 1e-4 and read(far, "cboe") == v["cboe"])
dear = with_put(stub, 80.0, "0", "6.00")
check("a zero-bid stub's ask moves 'reg' but never 'skip'",
      abs(read(dear, "reg") - v["reg"]) > 1e-4 and read(dear, "skip") == v["skip"])
check("ONE zero bid does not stop Cboe's walk (only two in a row do)",
      read(with_put(base, 80.0, "0", "3.00"), "cboe") - v["cboe"] > 0.2)

band = bs_rows(100, 0.039, 0.60, (23, 37), 75, 130, 1)
wide_rows = [r for r in bs_rows(100, 0.039, 0.60, (23, 37), 30, 250, 1) if not 75 <= float(r["strike"]) <= 130]
for r in wide_rows:
    r["option_symbol"] = "W" + r["option_symbol"]
lift = IR.h3_day(band, wide_rows, 0.039)
check(f"a band cut at 75-130 reads low (truncated tails: {lift['reg']:.3f} < 59.5)", lift["reg"] < 59.5)
check(f"adding the wide strikes restores it: wide {lift['wide_reg']:.3f} within 0.05 of 60", abs(lift["wide_reg"] - 60) < 0.05)

print("\n=== part 2: H7's clock, rate and quotes ===")
check("settlement 16:00 New York in daylight time: 16 Oct 2026 -> 20:00 UTC",
      IR.settle_utc(date(2026, 10, 16)) == datetime(2026, 10, 16, 20, tzinfo=timezone.utc))
check("in standard time: 20 Nov 2026 -> 21:00 UTC", IR.settle_utc(date(2026, 11, 20)) == datetime(2026, 11, 20, 21, tzinfo=timezone.utc))
check("the switch: 31 Oct 2026 still daylight, 1 Nov 2026 (first Sunday) standard",
      IR.settle_utc(date(2026, 10, 31)).hour == 20 and IR.settle_utc(date(2026, 11, 1)).hour == 21)
check("spring: 7 Mar 2026 standard, 8 Mar 2026 (second Sunday) daylight",
      IR.settle_utc(date(2026, 3, 7)).hour == 21 and IR.settle_utc(date(2026, 3, 8)).hour == 20)
check("BEY 3.91% -> continuous 2 ln(1.01955) = 0.0387227 (by hand)", abs(IR.bey_to_continuous(0.0391) - 0.0387227) < 1e-7)
check("quotes: both sides -> mid; one side missing or zero -> 'zero'; neither -> 'none'",
      IR.cboe_quote(1.0, 2.0) == 1.5 and IR.cboe_quote(0.0, 1.0) == "zero" and IR.cboe_quote(None, 1.0) == "zero"
      and IR.cboe_quote(1.0, 0.0) == "zero" and IR.cboe_quote(None, None) == "none")

print("\n=== part 2: Cboe's 30-day index on a minute clock ===")
when = datetime(2026, 10, 14, 18, 30, tzinfo=timezone.utc)
e1, e2 = date(2026, 11, 6), date(2026, 11, 20)
chains = {}
for e in (e1, e2):
    T = (IR.settle_utc(e) - when).total_seconds() / 60 / IR.N365
    ch, k = {}, 30.0
    while k <= 300:
        for cp in "CP":
            m = bs(100, k, T, IR.bey_to_continuous(0.0391), 0.25, cp)
            ch[(k, cp)] = IR.cboe_quote(0.98 * m, 1.02 * m)
        k += 0.5
    chains[e] = ch
ix = IR.index30(chains, [e1, e2], when, IR.bey_to_continuous(0.0391))
check(f"flat 25% vol, minutes to settlement across the DST switch: reads 25.00 within 0.05 (got {ix:.4f})", abs(ix - 25) < 0.05)
check("one term only -> no index", IR.index30(chains, [e1], when, 0.04) is None)

print("\n=== part 2: reading a Databento cbbo-1m file ===")
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "OPRA_M_GLD_2026-10-14.csv"
    cols = ["ts_recv", "bid_px_00", "ask_px_00", "symbol"]
    recs = [("2026-10-14T18:29:00.000000000Z", "1.00", "1.10", "GLD   261106C00400000"),
            ("2026-10-14T18:30:00.000000000Z", "1.20", "1.30", "GLD   261106C00400000"),
            ("2026-10-14T18:30:00.000000000Z", "", "0.05", "GLD   261106P00300000"),
            ("2026-10-14T18:30:00.000000000Z", "2.00", "2.10", "GLDM  261106C00040000"),
            ("2026-10-14T18:35:00.000000000Z", "3.00", "3.10", "GLD   261106C00410000")]
    with p.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        wr.writerows(recs)
    ch = IR.opra_chain(p, when, "GLD").get(date(2026, 11, 6), {})
    check("the record nearest the snapshot minute wins (18:30 over 18:29)", ch.get((400.0, "C")) == 1.25)
    check("Databento's BLANK bid is a zero bid, not a missing quote", ch.get((300.0, "P")) == "zero")
    check("root GLD does not swallow GLDM", (40.0, "C") not in ch)
    check("a record more than 120 s away is ignored", (410.0, "C") not in ch)
rows = [{"quote_time": t} for t in ("2026-10-14T18:29:59Z", "2026-10-14T18:30:20.5Z", "2026-10-14T18:31:40Z")]
check("snapshot minute = the median quote's minute", IR.snapshot_minute(rows) == when)

print("\n=== discipline ===")
import ast  # noqa: E402
_tree = ast.parse((R / "tools/independent_replica.py").read_text())
_mods = {a.name.split(".")[0] for n in ast.walk(_tree) if isinstance(n, ast.Import) for a in n.names}
_mods |= {n.module.split(".")[0] for n in ast.walk(_tree) if isinstance(n, ast.ImportFrom) and n.module}
check(f"standard library only - nothing from the project can be shared (imports: {sorted(_mods)})",
      _mods <= {"csv", "math", "os", "sys", "collections", "datetime", "pathlib"})

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
