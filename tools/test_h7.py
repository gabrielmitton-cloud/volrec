"""Unit tests for H7's reader (tools/h7_reader.py). No network, no licensed data: synthetic chains.
python tools/test_h7.py
"""
import importlib.util as iu
import math
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
_s = iu.spec_from_file_location("h7", R / "tools/h7_reader.py")
h7 = iu.module_from_spec(_s); _s.loader.exec_module(h7)
from calibrate import black76                      # noqa: E402
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


WHEN = datetime(2026, 10, 9, 18, 42, tzinfo=timezone.utc)
E1, E2 = date(2026, 10, 16), date(2026, 11, 20)


def chain(sig, S=80.0):
    out = {}
    for e in (E1, E2):
        T = h7.O.minutes_to(e, WHEN) / h7.O.MIN365
        q = {}
        for K in range(40, 121):
            for k in "CP":
                p = black76(k, S, float(K), T, 0.0, sig)
                q[(float(K), k)] = (round(p * 0.99, 6), round(p * 1.01, 6)) if p > 0.005 else (0.0, 0.01)
        out[e] = q
    return out


print("=== the replica on a known chain ===")
v = h7.replica(chain(0.45), [E1, E2], WHEN, 0.0)
check(f"a flat 45% chain reads ~45 points ({v:.2f})", v is not None and abs(v - 45.0) < 0.6)
check("identical free and OPRA quotes give identical readings",
      h7.replica(chain(0.45), [E1, E2], WHEN, 0.0) == h7.replica(chain(0.45), [E1, E2], WHEN, 0.0))
check("one expiry is not enough", h7.replica(chain(0.45), [E1], WHEN, 0.0) is None)

print("\n=== rows -> quotes ===")
rows = [{"expiration": "2026-10-16", "strike": "80.0", "type": "C", "bid": "1.2", "ask": "1.3"},
        {"expiration": "2026-10-16", "strike": "80.0", "type": "P", "bid": "", "ask": "0.9"},
        {"expiration": "2026-10-16", "strike": "81.0", "type": "P", "bid": "", "ask": ""}]
q = h7.quotes_from_rows(rows)
check("numbers parse; a blank bid beside an ask is a ZERO bid (Cboe); no quote at all stays null",
      q[E1][(80.0, "C")] == (1.2, 1.3) and q[E1][(80.0, "P")] == (0.0, 0.9) and q[E1][(81.0, "P")] == (None, None))

print("\n=== end to end on synthetic files (monthly rows + an OPRA_M file) ===")
tmp = Path(tempfile.mkdtemp())
ch = chain(0.30)
# A stray far bid BEYOND the two-zero-bid stop (as OPRA's wings carry): Cboe's walk never reaches
# it. Databento writes a no-bid as a BLANK and the free feed as 0; both must stop the walk there.
for e in ch:
    ch[e][(40.0, "P")] = (0.01, 0.05)
mrows, lines = [], ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
                    "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
for e, qq in ch.items():
    for (K, k), (b, a) in qq.items():
        osym = f"USO{e:%y%m%d}{k}{int(K * 1000):08d}"
        mrows.append({"date": "2026-10-09", "symbol": "USO", "expiration": e.isoformat(), "strike": str(K),
                      "type": k, "bid": str(b), "ask": str(a), "quote_time": "2026-10-09T18:42:10Z"})
        occ = f"USO   {e:%y%m%d}{k}{int(K * 1000):08d}"
        bb = "" if b == 0 else b                     # Databento's own form: no bid -> blank
        lines.append(f"2026-10-09T18:42:00.000000000Z,,193,30,1,N,,0,0,{bb},{a},1,1,1,1,{occ}")
(tmp / "OPRA_M_USO_2026-10-09.csv").write_text("\n".join(lines) + "\n")
h7.ore.monthly_recorded = lambda d, s: mrows if (d, s) == ("2026-10-09", "USO") else []
x = h7.day_reading("2026-10-09", "USO", 0.0, tmp)
check(f"free and OPRA agree when the quotes are the same ({x['free']:.3f} vs {x['opra']:.3f})",
      x and x["free"] is not None and x["opra"] is not None and abs(x["free"] - x["opra"]) < 1e-9)
check("the legs are the two monthlies, 7 and 42 days out", x["legs"] == [7, 42])
check("the blank-bid OPRA file really carries blanks (the case this test exists for)",
      ",,0.01," in (tmp / "OPRA_M_USO_2026-10-09.csv").read_text())
h7.O.ABSENT_AS_ZERO = False                          # the 8 Oct reading: blank = null
old = h7.day_reading("2026-10-09", "USO", 0.0, tmp)
h7.O.ABSENT_AS_ZERO = True
check(f"read as null, the blank bids let the walk past the stop and the feeds disagree ({old['opra']:.3f} vs {old['free']:.3f})",
      old["opra"] is not None and old["opra"] - old["free"] > 0.01)
y = h7.day_reading("2026-10-09", "USO", 0.0, tmp / "missing")
check("no OPRA file -> opra is None, never a guess", y["opra"] is None and y["free"] is not None)

print("\n=== summary and verdict rules ===")
def mk(sym, n, df, dc, start=1):
    return [{"day": f"2026-10-{start + i:02d}", "symbol": sym, "free": 40.0 + df, "opra": 40.0} for i in range(n)], \
           {f"2026-10-{start + i:02d}": 40.0 + df - dc for i in range(n)}
ru, cu = mk("USO", 10, 0.20, 0.5)
rg, cg = mk("GLD", 10, 0.10, 0.20)
s = h7.summarise(ru + rg, {"USO": cu, "GLD": cg})
check("H7a mean |free - OPRA| per symbol", abs(s["USO"]["a"][1] - 0.20) < 1e-9 and abs(s["GLD"]["a"][1] - 0.10) < 1e-9)
check("H7b GLD mean |free - close|", abs(s["GLD"]["b"][1] - 0.20) < 1e-9)
check("H7c USO signed mean, descriptive", abs(s["USO"]["c"][1] - 0.5) < 1e-9)
check("both under their bars at 10 days: H7a HOLDS, H7b HOLDS", h7.verdicts(s) == ("HOLDS", "HOLDS"))
ru2, cu2 = mk("USO", 10, 0.26, 0.5)
check("one symbol over 0.25 fails H7a for both", h7.verdicts(h7.summarise(ru2 + rg, {"USO": cu2, "GLD": cg}))[0] == "FAILS")
check("exactly on the bar holds (<= 0.25)",
      h7.verdicts(h7.summarise(mk("USO", 10, 0.25, 0)[0] + rg, {"USO": mk("USO", 10, 0.25, 0)[1], "GLD": cg}))[0] == "HOLDS")
ru9, cu9 = mk("USO", 9, 0.0, 0.0)
check("9 days is below the minimum: no H7a verdict", h7.verdicts(h7.summarise(ru9 + rg, {"USO": cu9, "GLD": cg}))[0] is None)
nc = {"USO": {}, "GLD": cg}
check("a day without its index close does not count", h7.summarise(ru + rg, nc)["USO"]["a"][0] == 0)

# 28 Oct 2026 (outside review R8, R5): non-finite values never count as days, and an uncounted day is named.
_nan, _inf = float("nan"), float("inf")
rgn = [dict(x) for x in rg]
rgn[0]["opra"] = _nan
cgn = dict(cg)
cgn[rg[1]["day"]] = _inf
sn = h7.summarise(ru + rgn, {"USO": cu, "GLD": cgn})
check("R8: a NaN OPRA reading and an infinite close do not count (GLD 8 days, not 10) and the means stay finite",
      sn["GLD"]["a"][0] == 8 and sn["GLD"]["b"][0] == 8 and all(map(h7._ok, (sn["GLD"]["a"][1], sn["GLD"]["b"][1]))))
check("R8: so GLD is below its minimum - no verdict, never a FAILS from comparing NaN",
      h7.verdicts(sn) == (None, None))
rgf = [dict(x) for x in rg]
rgf[2]["free"] = None
_nc = h7.not_counted(ru + rgn + rgf[2:3], {"USO": cu, "GLD": cgn})
check(f"R5: every day with a row that does not count is named with its reason ({_nc})",
      _nc == [f"{rg[0]['day']} GLD (OPRA reading not finite)", f"{rg[1]['day']} GLD (index close not finite)",
              f"{rg[2]['day']} GLD (no free reading)"])
_xg = {"day": "2026-10-20", "symbol": "GLD", "free": 22.0, "opra": float("nan")}
check("R5: an OPRA file giving a NaN reading, and an infinite close, are WAITED on (the writer holds), not just listed",
      h7.waits_for(_xg, float("inf"), True) == ["2026-10-20 GLD OPRA unusable", "2026-10-20 GLD GVZ close unusable"]
      and h7.waits_for(dict(_xg, opra=None), None, False) == ["2026-10-20 GLD OPRA", "2026-10-20 GLD GVZ close"]
      and h7.waits_for(dict(_xg, opra=22.1), 22.3, True) == [])
check("R5: a day already named as waiting is not named twice",
      h7.not_counted(rgf[2:3], {"GLD": cg}, waiting=[f"{rg[2]['day']} GLD OPRA unusable"]) == [])

print("\n" + "=" * 52)

print("\n=== the matched-strike COMPANION (17 Oct 2026; never the registered reading) ===")
from datetime import date as _D
_e = _D(2026, 12, 18)
_free = {_e: {(50.0, "P"): (0.5, 0.6), (60.0, "C"): (0.4, 0.5), (55.0, "C"): (1.0, 1.1)}}
_opra = {_e: {(50.0, "P"): (0.5, 0.6), (60.0, "C"): (0.4, 0.5), (55.0, "C"): (1.0, 1.1),
              (120.0, "C"): (0.02, 0.05), (20.0, "P"): (0.01, 0.03)}}
_m = h7.match_chain(_opra, _free)
check("match_chain keeps only the strikes the free file holds (the far wings OPRA alone has are cut)",
      set(_m[_e]) == {(50.0, "P"), (60.0, "C"), (55.0, "C")})
check("match_chain never invents a quote: an OPRA-only expiry comes back empty",
      h7.match_chain({_D(2027, 1, 15): {(50.0, "P"): (1, 2)}}, _free) == {_D(2027, 1, 15): {}})
check("edge_limited flags an expiry whose highest call still has a live bid (the walk runs off the edge)",
      h7.edge_limited(_free) == [_e])
_closed = {_e: {(50.0, "P"): (0.0, 0.05), (60.0, "C"): (0.0, 0.05), (55.0, "C"): (1.0, 1.1)}}
check("edge_limited stays quiet when both outermost strikes have no bid (Cboe's stop is inside the file)",
      h7.edge_limited(_closed) == [])
_src = (Path(__file__).resolve().parent / "h7_reader.py").read_text()
check("the registered reading never reads the companion (opra is computed from the full chain, as before)",
      "opra = replica(ochain, exps, when, R)" in _src and "if \"--matched\" in sys.argv:" in _src)

print(f"RESULT: {len(fails)} failure(s)" + (f": {fails}" if fails else ""))
sys.exit(1 if fails else 0)
