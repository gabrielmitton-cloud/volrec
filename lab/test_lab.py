"""Known-answer tests for lab/ (the retail implementation audit, EXPLORATORY). No network, no
licensed data: fixtures in the providers' real formats. Run with the framework python:
    FRED_KEY=use-cache python lab/test_lab.py
"""
import importlib.util as iu
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools"), str(R / "lab")]
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def load(name):
    s = iu.spec_from_file_location(name, R / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


from iv_convention import black76          # noqa: E402

costs = load("costs")
print("=== costs ===")
check("the four cost cases are exactly as registered",
      costs.COST_CASES == {"mid": 0.0, "timed": 0.30, "retail": 0.80, "quoted": 1.00})
check("commissions are $0 and $0.65", costs.COMMISSIONS == (0.0, 0.65))
check("half-spread of 1.00 / 1.20 is 0.10", abs(costs.half_spread(1.00, 1.20) - 0.10) < 1e-12)
check("a blank bid is a zero bid: None / 0.10 -> 0.05", abs(costs.half_spread(None, 0.10) - 0.05) < 1e-12)
check("no ask is no quote", costs.half_spread(1.0, None) is None)
check("a crossed quote is no quote", costs.half_spread(1.2, 1.0) is None)
check("retail pays 80% of 0.10 = 0.08", abs(costs.charged(0.10, "retail") - 0.08) < 1e-12)
check("mid pays nothing", costs.charged(0.10, "mid") == 0.0)
check("straddle at quoted: call 2.00/2.10 + put 1.90/2.06 -> 0.05 + 0.08 = 0.13",
      abs(costs.straddle_cost((2.00, 2.10), (1.90, 2.06), "quoted") - 0.13) < 1e-12)
check("straddle with an unquoted leg is None", costs.straddle_cost((2.0, None), (1.9, 2.0), "quoted") is None)
check("0.13 per share over vega 0.26 per point = 0.5 points", abs(costs.vol_points(0.13, 0.26) - 0.5) < 1e-12)
check("zero vega gives no conversion", costs.vol_points(0.13, 0.0) is None)
check("3 contracts at $0.65 = $1.95", abs(costs.commission(3, 0.65) - 1.95) < 1e-12)

# A chain in the recorder's own format (as tools/test_h8.py builds it): two expiries, flat 30% vol.
D, S, SIG = "2018-02-05", 100.0, 0.30


def chain(spread_frac):
    rows = []
    for exp, dte in (("2018-03-02", 25), ("2018-03-30", 53)):          # bracket 30 days, as Cboe needs
        for K in range(70, 131, 5):
            for k in "CP":
                p = black76(k, S, float(K), dte / 365.0, 0.0, SIG)
                if p < 0.05:
                    continue
                b, a = p * (1 - spread_frac), p * (1 + spread_frac)
                rows.append({"date": D, "symbol": "XYZ", "spot": str(S), "expiration": exp, "dte": str(dte),
                             "type": k, "strike": str(float(K)), "option_symbol": f"XYZ{exp[2:4]}{exp[5:7]}{exp[8:]}{k}{K * 1000:08d}",
                             "bid": f"{b:.6f}", "ask": f"{a:.6f}", "mid": f"{(a + b) / 2:.6f}"})
    return rows


z = costs.strip_cost(chain(0.0), 0.0)
check(f"a zero spread costs the strip nothing ({z})", z is not None and abs(z) < 1e-9)
w = costs.strip_cost(chain(0.04), 0.0)
check(f"a 4% spread costs the strip a positive number of points ({w:.3f})", w is not None and w > 0)
check("a wider spread costs more", costs.strip_cost(chain(0.08), 0.0) > w)

integ = load("integrity")
from datetime import datetime, timezone    # noqa: E402
import opra_reference as ore               # noqa: E402
print("\n=== integrity ===")
check("registered thresholds", (integ.BAND, integ.PARITY_BAND, integ.MIN_STRIKES, integ.SANE_SHARE,
                                integ.PARITY_SHARE, integ.DIV_ALLOW) == (0.10, 0.05, 10, 0.95, 0.90, 0.005))
check("OSI with Databento's padding parses", integ.parse_osi("SPY   180216P00265000") == ("SPY", "2018-02-16", "P", 265.0))
check("OSI compact parses", integ.parse_osi("USO180316C00012500") == ("USO", "2018-03-16", "C", 12.5))
check("garbage is not an OSI symbol", integ.parse_osi("SPY") is None)

WHEN = datetime(2018, 2, 5, 19, 30, tzinfo=timezone.utc)


def opra_file(F=100.0, shift_call=0.0, drop=None, rel=0.02):
    """A Databento cbbo-1m CSV for one expiry, 39 days out, around the minute."""
    lines = ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
             "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
    for K in range(80, 121):
        for k in "CP":
            if drop and (K, k) == drop:
                continue
            p = black76(k, F, float(K), 39 / 365.0, 0.0, 0.25) + (shift_call if k == "C" else 0.0)
            b, a = max(p * (1 - rel), 0.0), p * (1 + rel) + 0.01
            bb = "" if b < 0.01 else f"{b:.4f}"            # Databento: no bid -> BLANK
            for mm in ("29", "30", "31"):
                lines.append(f"2018-02-05T19:{mm}:00.000000000Z,,193,30,1,N,,0,0,{bb},{a:.4f},1,1,1,1,"
                             f"XYZ   180316{k}{K * 1000:08d}")
    p = Path(__import__("tempfile").mkdtemp()) / "OPRA_LAB_XYZ_2018-02-05.csv"
    p.write_text("\n".join(lines) + "\n")
    return ore.load_opra(p)


ch = integ.chain_at(opra_file(), "2018-03-16", WHEN)
check(f"the chain holds 41 strikes with both sides ({len(ch)})", len(ch) == 41 and all(len(v) == 2 for v in ch.values()))
F = integ.forward(ch)
check(f"the implied forward is 100 to within a cent ({F:.4f})", abs(F - 100.0) < 0.01)
okd, det = integ.check_chain(ch)
check(f"band edges are inclusive: 90..110 is 21 strikes at a forward of 100 ({det['complete'][1]})",
      det["complete"][1].startswith("21 of 21"))
check(f"parity uses 95..105, 11 strikes ({det['parity'][1]})", "of 11 strikes" in det["parity"][1])
check(f"a consistent chain passes all three checks ({det})", okd)
okd2, det2 = integ.check_chain(integ.chain_at(opra_file(shift_call=0.50), "2018-03-16", WHEN))
check("a uniform 50-cent shift on every call moves the implied forward, not parity (still passes)", okd2)
bad = opra_file()
for s in list(bad):                                       # make every other call $1.50 rich
    p = integ.parse_osi(s)
    if p and p[2] == "C" and int(p[3]) % 2 == 0:
        bad[s] = [(t, (b or 0) + 1.5, a + 1.5) for t, b, a in bad[s]]
okd3, det3 = integ.check_chain(integ.chain_at(bad, "2018-03-16", WHEN))
check(f"a chain with alternate calls $1.50 rich fails parity ({det3.get('parity')})", not okd3 and not det3["parity"][0])
okd4, det4 = integ.check_chain(integ.chain_at(opra_file(drop=(100, "P")), "2018-03-16", WHEN))
check(f"a missing ATM put fails completeness ({det4.get('complete')})", not okd4 and not det4["complete"][0])
thin = {k: v for k, v in ch.items() if 97 <= k <= 103}
check("fewer than 10 strikes in the band fails completeness", not integ.check_chain(thin)[1]["complete"][0])
check("an empty chain fails", integ.check_chain({})[0] is False)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
