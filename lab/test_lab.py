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
check("registered thresholds (MIN_LISTED replaced the 10-strike minimum, 12 Oct, after the test day)",
      (integ.BAND, integ.PARITY_BAND, integ.MIN_LISTED, integ.SANE_SHARE, integ.PARITY_SHARE, integ.DIV_ALLOW)
      == (0.10, 0.05, 3, 0.95, 0.90, 0.005))
check("OSI with Databento's padding parses", integ.parse_osi("SPY   180216P00265000") == ("SPY", "2018-02-16", "P", 265.0))
check("OSI compact parses", integ.parse_osi("USO180316C00012500") == ("USO", "2018-03-16", "C", 12.5))
check("garbage is not an OSI symbol", integ.parse_osi("SPY") is None)

WHEN = datetime(2018, 2, 5, 19, 30, tzinfo=timezone.utc)


def opra_file(F=100.0, shift_call=0.0, drop=None, rel=0.02, strikes=None, vol=0.25):
    """A Databento cbbo-1m CSV for one expiry, 39 days out, around the minute."""
    lines = ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
             "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
    for K in (strikes or [float(x) for x in range(80, 121)]):
        for k in "CP":
            if drop and (K, k) == drop:
                continue
            p = black76(k, F, float(K), 39 / 365.0, 0.0, vol) + (shift_call if k == "C" else 0.0)
            b, a = max(p * (1 - rel), 0.0), p * (1 + rel) + 0.01
            bb = "" if b < 0.01 else f"{b:.4f}"            # Databento: no bid -> BLANK
            for mm in ("29", "30", "31"):
                lines.append(f"2018-02-05T19:{mm}:00.000000000Z,,193,30,1,N,,0,0,{bb},{a:.4f},1,1,1,1,"
                             f"XYZ   180316{k}{int(round(K * 1000)):08d}")
    p = Path(__import__("tempfile").mkdtemp()) / "OPRA_LAB_XYZ_2018-02-05.csv"
    p.write_text("\n".join(lines) + "\n")
    return ore.load_opra(p)


ch = integ.chain_at(opra_file(), "2018-03-16", WHEN)
check(f"the chain holds 41 strikes with both sides ({len(ch)})", len(ch) == 41 and all(len(v) == 2 for v in ch.values()))
F = integ.forward(ch)
check(f"the implied forward is 100 to within a cent ({F:.4f})", abs(F - 100.0) < 0.01)
LISTED = {float(x) for x in range(80, 121)}
okd, det = integ.check_chain(ch, LISTED)
check(f"band edges are inclusive: 90..110 is 21 strikes at a forward of 100 ({det['complete'][1]})",
      det["complete"][1].startswith("21 of 21"))
check(f"parity uses 95..105, 11 strikes ({det['parity'][1]})", "of 11 strikes" in det["parity"][1])
check(f"a consistent chain passes all three checks ({det})", okd)
okd2, det2 = integ.check_chain(integ.chain_at(opra_file(shift_call=0.50), "2018-03-16", WHEN), LISTED)
check("a uniform 50-cent shift on every call moves the implied forward, not parity (still passes)", okd2)
bad = opra_file()
for s in list(bad):                                       # make every other call $1.50 rich
    p = integ.parse_osi(s)
    if p and p[2] == "C" and int(p[3]) % 2 == 0:
        bad[s] = [(t, (b or 0) + 1.5, a + 1.5) for t, b, a in bad[s]]
okd3, det3 = integ.check_chain(integ.chain_at(bad, "2018-03-16", WHEN), LISTED)
check(f"a chain with alternate calls $1.50 rich fails parity ({det3.get('parity')})", not okd3 and not det3["parity"][0])
okd4, det4 = integ.check_chain(integ.chain_at(opra_file(drop=(100.0, "P")), "2018-03-16", WHEN), LISTED)
check(f"a missing ATM put fails completeness ({det4.get('complete')})", not okd4 and not det4["complete"][0])
check("a listed strike missing from the file fails completeness",
      not integ.check_chain(ch, LISTED | {100.5})[1]["complete"][0])
check("strikes listed outside the band do not matter", integ.check_chain(ch, LISTED | {150.0})[0])
check("fewer than 3 listed strikes in the band fails completeness",
      not integ.check_chain(ch, {100.0, 101.0})[1]["complete"][0])
check("an empty chain fails", integ.check_chain({}, LISTED)[0] is False)
grid = [x / 2 for x in range(6, 47)]                     # $3 to $23 in $0.50 steps, as USO in Feb 2018
uso = integ.chain_at(opra_file(F=12.81, strikes=grid, vol=0.35, rel=0.03), "2018-03-16", WHEN)
okU, detU = integ.check_chain(uso, set(grid))
check(f"a $12.81 fund on a $0.50 grid, every listed strike quoted, passes ({detU['complete'][1]})", okU)
dfile = Path(__import__("tempfile").mkdtemp()) / "DEF_LAB_XYZ_2018-02-05.csv"
dfile.write_text("ts_recv,ts_event,rtype,publisher_id,instrument_id,raw_symbol,security_update_action,expiration\n"
                 "2018-02-05T10:30:00Z,2018-02-05T10:30:00Z,19,30,1,XYZ   180316C00012500,A,2018-03-16T00:00:00Z\n"
                 "2018-02-05T10:30:00Z,2018-02-05T10:30:00Z,19,30,2,XYZ   180316P00012500,A,2018-03-16T00:00:00Z\n"
                 "2018-02-05T10:30:00Z,2018-02-05T10:30:00Z,19,30,3,XYZ   180316P00013000,A,2018-03-16T00:00:00Z\n"
                 "2018-02-05T10:30:00Z,2018-02-05T10:30:00Z,19,30,4,XYZ   180420P00013000,A,2018-04-20T00:00:00Z\n")
check("listed strikes are read from Databento's definition file, one expiry only",
      integ.listed_strikes(dfile, "2018-03-16") == {12.5, 13.0})

mg = load("margin")
print("\n=== margin (Cboe Margin Manual, 30 Nov 2021, worked examples) ===")
check("registered rates", mg.RATES == {"SPY": (0.15, 0.10), "QQQ": (0.15, 0.10), "IWM": (0.15, 0.10),
                                       "GLD": (0.20, 0.10), "USO": (0.20, 0.10)} and mg.BROKER == (0.40, 0.35))
check("short Sep 80 put at 2, underlying 95, 20%/10%: $1,000.00",
      abs(mg.short_put(2.00, 95.0, 80.0, 0.20, 0.10) * 100 - 1000.00) < 0.005)
check("short Jan 20 put at 1.50, underlying 19.50: $540.00",
      abs(mg.short_put(1.50, 19.50, 20.0, 0.20, 0.10) * 100 - 540.00) < 0.005)
check("short Oct 410 put at .10, broad index 445.35, 15%/10%: $4,110.00",
      abs(mg.short_put(0.10, 445.35, 410.0, 0.15, 0.10) * 100 - 4110.00) < 0.005)
check("short Nov 120 call at 8.40, underlying 128.50: $3,410.00",
      abs(mg.short_call(8.40, 128.50, 120.0, 0.20, 0.10) * 100 - 3410.00) < 0.005)
check("short Feb 30 call at .05, underlying 26.38: $268.80",
      abs(mg.short_call(0.05, 26.38, 30.0, 0.20, 0.10) * 100 - 268.80) < 0.005)
check("short Dec 90 call at 7 + put at 3.70, underlying 92.63: $2,922.60",
      abs(mg.short_straddle(7.00, 3.70, 92.63, 90.0, 90.0, 0.20, 0.10) * 100 - 2922.60) < 0.005)
check("short Nov 435 put at 7.20 + call at 5.50, broad index 433.35: $7,770.25",
      abs(mg.short_straddle(5.50, 7.20, 433.35, 435.0, 435.0, 0.15, 0.10) * 100 - 7770.25) < 0.005)
P45 = black76("P", 100.0, 100.0, 45 / 365.0, 0.05, 0.20)
check(f"Santa-Clara & Saretto: ATM 45-day put, S=100, 20% vol, 5% rate -> $17.80 ({mg.short_put(P45, 100.0, 100.0, 0.15, 0.10):.2f})",
      abs(mg.short_put(P45, 100.0, 100.0, 0.15, 0.10) - 17.80) < 0.03)

fl = load("fetch_lab")
print("\n=== fetch_lab (no network) ===")
check("registered cap, tags and dates", (fl.LAB_BUDGET_USD, fl.LAB_TAG, fl.DEF_TAG, fl.LAB_START, fl.LAB_END)
      == (90.00, "-lab", "-def-lab", "2015-08-01", "2026-08-31"))
check("listings file stem", fl.def_stem("USO", "2018-02-05") == "DEF_LAB_USO_2018-02-05")
check("31 Aug 2026 is allowed, 1 Sep 2026 is not", fl.date_ok("2026-08-31") and not fl.date_ok("2026-09-01"))
check("1 Aug 2015 is allowed, 31 Jul 2015 is not", fl.date_ok("2015-08-01") and not fl.date_ok("2015-07-31"))
check("H7's window (9 Oct 2026) is refused", not fl.date_ok("2026-10-09"))
check("14:30 New York in winter is 19:30 UTC (5 Feb 2018)",
      fl.ny_minute("2018-02-05").isoformat() == "2018-02-05T19:30:00+00:00")
check("14:30 New York in summer is 18:30 UTC (5 Aug 2024)",
      fl.ny_minute("2024-08-05").isoformat() == "2024-08-05T18:30:00+00:00")
check("file stem", fl.lab_stem("SPY", "2018-02-05", "14:30") == "OPRA_LAB_SPY_2018-02-05_1430")
rows = [{"symbol": "SPY", "usd": "0.50"}, {"symbol": "SPY-h8", "usd": "0.25"}, {"symbol": "USO-lab", "usd": "1.25"},
        {"symbol": "USO-def-lab", "usd": "0.10"}]
check("lifetime spend counts every row", abs(fl.spent_all(rows) - 2.10) < 1e-12)
check("lab spend counts quotes and listings (-lab rows) only", abs(fl.spent_lab(rows) - 1.35) < 1e-12)
check("within the lab cap", fl.lab_budget_ok(0.20, 89.70)[0])
check("over the lab cap is refused", not fl.lab_budget_ok(0.20, 89.90)[0])
check("the lab's data folder is outside the public repo", not ore.inside_repo(fl.LAB_DIR))

bars = load("bars")
print("\n=== bars ===")
check("the five funds", bars.FUNDS == ("SPY", "QQQ", "IWM", "GLD", "USO"))
_bp = Path(__import__("tempfile").mkdtemp()) / "bars.csv"
n = bars.write_csv(_bp, {"USO": {"2020-04-28": 2.14, "2020-04-29": 18.01}},
                         {"USO": {"2020-04-28": 17.12, "2020-04-29": 18.01}})
check("two rows written", n == 2)
_b = bars.load(_bp)
check("raw and adjusted read back separately (USO's 1-for-8 split, 29 Apr 2020)",
      _b["USO"]["2020-04-28"] == (2.14, 17.12) and _b["USO"]["2020-04-29"] == (18.01, 18.01))
check("the bars file lives outside the public repo", not ore.inside_repo(bars.BARS_FILE))

cal = load("tradecal")
print("\n=== calendar ===")
from datetime import date as _d, timedelta as _td   # noqa: E402
_days = [(_d(2016, 1, 4) + _td(i)).isoformat() for i in range(0, 3900)
         if (_d(2016, 1, 4) + _td(i)).weekday() < 5]
_hol = {"2016-01-18", "2016-02-15", "2019-04-19", "2026-07-03"}  # MLK, Presidents' Day, Good Friday, July 4th observed
_trd = [x for x in _days if x not in _hol and x <= "2026-08-31"]
check("third Friday of Jan 2016 is the 15th", cal.third_friday(2016, 1) == _d(2016, 1, 15))
check("April 2019 expiry moves to Thursday the 18th (Good Friday)", cal.monthly_expiry(2019, 4, set(_trd)) == "2019-04-18")
_e = cal.entries(_trd)
check(f"first pair: enter 19 Jan 2016 (after MLK Day), expire 19 Feb ({_e[0]})", _e[0] == ("2016-01-19", "2016-02-19"))
check(f"last pair ends by 31 Aug 2026: enter 20 Jul, expire 21 Aug ({_e[-1]})", _e[-1] == ("2026-07-20", "2026-08-21"))
_g = [(_d.fromisoformat(b) - _d.fromisoformat(a)).days for a, b in _e]
check(f"every holding period is 24-32 days ({min(_g)}-{max(_g)})", min(_g) >= 24 and max(_g) <= 32)
check(f"about 127 trades ({len(_e)})", 125 <= len(_e) <= 128)
check("pairs never overlap", all(_e[i][1] < _e[i + 1][0] for i in range(len(_e) - 1)))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
