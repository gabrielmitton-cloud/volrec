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
# 28 Oct 2026 (outside review M02): the fixed-portfolio cost.
import modelfree as _mf   # noqa: E402
_c4 = chain(0.04)
_z2, _w2, _w8 = costs.strip_cost_fixed(chain(0.0), 0.0), costs.strip_cost_fixed(_c4, 0.0), costs.strip_cost_fixed(chain(0.08), 0.0)
check(f"fixed strip: a zero spread costs nothing, 4% costs more than 0, 8% more again ({_z2}, {_w2:.3f}, {_w8:.3f})",
      abs(_z2) < 1e-12 and 0 < _w2 < _w8)
_byx = {}
for _x in [x for x in _c4 if float(x["bid"]) > 0]:
    _byx.setdefault(_x["expiration"], []).append(_x)
check("fixed strip: its mid variance is the registered estimator's own, expiry by expiry",
      all(abs(costs._basket_one_expiry(v, 0.0)[0] - _mf.variance_one_expiry(v, 0.0)[0]) < 1e-12 for v in _byx.values()))
_itm = [dict(x) for x in _c4]
_p85 = next(float(x["bid"]) for x in _c4 if x["type"] == "P" and float(x["strike"]) == 85.0 and x["dte"] == _c4[0]["dte"])
for _x in _itm:            # the review's case: ONE in-the-money call (not held by the strip) gets the 85 put's bid,
    if _x["type"] == "C" and float(_x["strike"]) == 85.0 and _x["dte"] == _c4[0]["dte"]:   # its mid unchanged
        m_ = float(_x["mid"]); _x["bid"], _x["ask"] = f"{_p85:.6f}", f"{2 * m_ - _p85:.6f}"
_old_moves = abs(costs.strip_cost(_itm, 0.0) - costs.strip_cost(_c4, 0.0))
check(f"fixed strip: a quote the strip does not hold cannot move its cost ({costs.strip_cost_fixed(_itm, 0.0):.6f} vs "
      f"{_w2:.6f}), while the old re-run moved by {_old_moves:.3f} points on it",
      abs(costs.strip_cost_fixed(_itm, 0.0) - _w2) < 1e-12 and _old_moves > 0.5)

_crossed = [dict(x) for x in _c4]
for _x in _crossed:        # Astra, 28 Oct: a HELD out-of-the-money put with a positive bid above its ask (crossed)
    if _x["type"] == "P" and float(_x["strike"]) == 90.0 and _x["dte"] == _c4[0]["dte"]:
        _x["bid"], _x["ask"] = _x["ask"], _x["bid"]
check("fixed strip: a crossed quote on a held leg makes the cost unavailable (None), never a zero cost",
      costs.strip_cost_fixed(_crossed, 0.0) is None)

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
_calls, _real_call, _real_sleep = [], ore.call, ore._sleep
def _flaky(endpoint, data, key, method="post", _fn=None):
    _calls.append(1)
    if len(_calls) < 3:
        raise SystemExit(f"Databento {endpoint} returned 504: <html>Gateway Time-out</html>")
    return "ok"
ore.call, ore._sleep = _flaky, (lambda s: None)
try:
    check("a gateway 504 that outlasts ore.call's retries is waited out, not fatal", fl._call("x", {}, "k") == "ok" and len(_calls) == 3)
    ore.call = lambda *a, **k: (_ for _ in ()).throw(SystemExit("Databento x returned 402: insufficient funds"))
    try:
        fl._call("x", {}, "k"); _stopped = False
    except SystemExit:
        _stopped = True
    check("a 402 (money) still stops at once", _stopped)
    ore.call = lambda *a, **k: (_ for _ in ()).throw(SystemExit('Databento x returned 422: {"detail":{"case":"symbology_invalid_request"}}'))
    try:
        fl._call("x", {}, "k"); _kind = "none"
    except fl.Unresolvable:
        _kind = "skip"
    except SystemExit:
        _kind = "stop"
    check("a 422 'cannot resolve the symbol' is a skip, not a stop", _kind == "skip")
    import requests as _rq
    _calls.clear()
    def _broken(*a, **k):
        _calls.append(1)
        if len(_calls) < 2:
            raise _rq.exceptions.ChunkedEncodingError("Connection broken: IncompleteRead")
        return "ok"
    ore.call = _broken
    check("a connection broken mid-download is retried", fl._call("x", {}, "k") == "ok" and len(_calls) == 2)
finally:
    ore.call, ore._sleep = _real_call, _real_sleep

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
check("registered stress months", cal.STRESS_MONTHS == ("2015-08", "2018-02", "2018-12", "2020-03", "2022-06", "2024-08", "2025-04"))
_sd = cal.stress_days(_trd)
check(f"stress days: every trading day of those months, Aug 2015 from weekdays ({len(_sd)})",
      "2015-08-24" in _sd and "2020-03-16" in _sd and "2018-02-05" in _sd
      and all(x[:7] in cal.STRESS_MONTHS for x in _sd) and 140 <= len(_sd) <= 150)
check("NYSE 1 p.m. closes 2015-2026: Christmas Eve 2018, July 3rd 2019, day after Thanksgiving 2020",
      {"2018-12-24", "2019-07-03", "2020-11-27", "2025-12-24"} <= cal.EARLY_CLOSES and "2021-12-24" not in cal.EARLY_CLOSES)
check("an entry on a half-day moves to 11:30 (the recorder's early-close time)", cal.slot("2018-12-24", "14:30") == "11:30")
check("a daily mark on a half-day moves to 12:55", cal.slot("2018-12-24", "15:55") == "12:55")
check("a normal day keeps its time", cal.slot("2018-12-21", "14:30") == "14:30" and cal.slot("2018-12-21", "15:55") == "15:55")
_wd = cal.weekly_days(_trd)
check(f"weekly samples: trading Wednesdays, 2016-01-06 to 2026-08-26 ({len(_wd)})",
      _wd[0] == "2016-01-06" and _wd[-1] == "2026-08-26" and all(_d.fromisoformat(x).weekday() == 2 for x in _wd)
      and 545 <= len(_wd) <= 560)

tr = load("trades")
print("\n=== trades ===")
check("index pairs", tr.INDEX == {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"} and tr.R2_REF == 20.0)
_bars = {"USO": {"2020-04-28": (2.14, 17.12)}}
check("settlement uses the RAW close (2.14), never the split-adjusted one", tr.settle(_bars, "USO", "2020-04-28") == 2.14)
check("call intrinsic", tr.intrinsic("C", 100, 104) == 4 and tr.intrinsic("C", 100, 96) == 0)
check("put intrinsic", tr.intrinsic("P", 100, 96) == 4 and tr.intrinsic("P", 100, 104) == 0)
prem, pnl = tr.leg(2.00, 2.20, "C", 100, 103, "mid")
check(f"short call at mid 2.10, expires 3 in the money: P&L -0.90 ({pnl:.2f})", abs(prem - 2.10) < 1e-12 and abs(pnl + 0.90) < 1e-12)
_, pnlr = tr.leg(2.00, 2.20, "C", 100, 103, "retail")
check(f"retail sells 0.08 below mid: P&L -0.98 ({pnlr:.2f})", abs(pnlr + 0.98) < 1e-12)
_ch = {95.0: {"C": (6.0, 6.2), "P": (1.0, 1.1)}, 100.0: {"C": (3.0, 3.2), "P": (2.9, 3.1)},
       105.0: {"C": (1.0, 1.1), "P": (5.9, 6.1)}, 101.0: {"C": (2.5, 2.6)}}
check("ATM picks the nearest TWO-SIDED strike (101 has no put)", tr.nearest_strike(_ch, 100.9) == 100.0)
st_ = tr.position(_ch, 100.0, 100.0, "mid")
check(f"straddle at 100 settling at 100: premium 6.10, keeps it all ({st_})",
      abs(st_["premium"] - 6.10) < 1e-12 and abs(st_["pnl"] - 6.10) < 1e-12 and abs(st_["ret"] - 1.0) < 1e-12)
sg = tr.position(_ch, 100.0, 90.0, "mid", kind="strangle")
check(f"strangle 95/105 settling at 90: premium 2.10, loses 5 on the put ({sg})",
      sg["K_put"] == 95.0 and sg["K_call"] == 105.0 and abs(sg["pnl"] - (2.10 - 5.0)) < 1e-12)
_F, _K, _T, _v = 100.0, 100.0, 30 / 365, 0.25
_num = (black76("C", _F, _K, _T, 0.0, _v + 1e-4) - black76("C", _F, _K, _T, 0.0, _v - 1e-4)) / 2e-4 / 100
check(f"vega per point matches the numerical derivative ({tr.vega76(_F, _K, _T, _v):.5f} vs {_num:.5f})",
      abs(tr.vega76(_F, _K, _T, _v) - _num) < 1e-6)
w = tr.rule_weights(25.0, 15.0, 22.0, 24.0)
check(f"rules, calm contango, index above realised: all trade, R2 = 20/25 ({w})", w == {"R0": 1.0, "R1": 1.0, "R2": 0.8, "R3": 1.0})
w2 = tr.rule_weights(25.0, 30.0, 30.0, 27.0)
check(f"index below realised and inverted VIX: R1 and R3 stand aside ({w2})", w2["R1"] == 0.0 and w2["R3"] == 0.0 and w2["R0"] == 1.0)
check("no realised volatility yet: R1 does not trade", tr.rule_weights(25.0, None, 22.0, 24.0)["R1"] == 0.0)
check("R2 sizes above 1 when the index is below 20 (registered, uncapped): 20/12.5 = 1.6",
      tr.rule_weights(12.5, 10.0, 12.0, 14.0)["R2"] == 1.6)
check("no index level that day: R1 and R2 stand aside, nothing crashes",
      tr.rule_weights(None, 15.0, 22.0, 24.0) == {"R0": 1.0, "R1": 0.0, "R2": 0.0, "R3": 1.0})
_ch2 = {100.0: {"C": (0.0, 3.2), "P": (2.9, 3.1)}, 101.0: {"C": (2.5, 2.6), "P": (3.4, 3.6)}}
check("a strike with no call bid cannot be sold, so it is not chosen", tr.nearest_strike(_ch2, 100.0) == 101.0)
_ch3 = {100.0: {"C": (3.3, 3.2), "P": (2.9, 3.1)}, 101.0: {"C": (2.5, 2.6), "P": (3.4, 3.6)}}
check("a crossed quote is not chosen either", tr.nearest_strike(_ch3, 100.0) == 101.0)
check("a crossed leg gives no P&L rather than a crash", tr.leg(3.3, 3.2, "C", 100, 100, "retail") is None)

mp = load("margin_path")
print("\n=== margin path ===")
_m = {"K": 100.0, "C0": 3.0, "P0": 3.0, "half0": 0.10, "S0": 100.0, "days": [(100.0, 3.0, 3.0)] * 3, "settle": 0.0}
r0 = mp.simulate(_m, 0.05, set(), 0.15, 0.10)
check(f"no frictions, expires worthless: keeps the whole 5% premium ({r0})", abs(r0["ret"] - 0.05) < 1e-12 and r0["liquidations"] == 0)
r1 = mp.simulate(dict(_m, settle=12.0), 0.05, set(), 0.15, 0.10)
check(f"no frictions, settles 12 on 6 of premium: loses 5% x (6-12)/6 = -5% ({r1['ret']:+.4f})", abs(r1["ret"] + 0.05) < 1e-12)
rs = mp.simulate(_m, 0.05, {"spreads"}, 0.15, 0.10)
check(f"spreads: sells 0.08 under mid on n = 0.05/6, so 5% - 0.08 x n ({rs['ret']:.6f})",
      abs(rs["ret"] - (0.05 - 0.08 * 0.05 / 6)) < 1e-12)
rc = mp.simulate(_m, 0.05, {"commissions"}, 0.15, 0.10)
check(f"commissions: 2 legs x 0.0065 x n ({rc['ret']:.6f})", abs(rc["ret"] - (0.05 - 2 * 0.0065 * 0.05 / 6)) < 1e-12)
big = mp.simulate(_m, 2.0, {"limits"}, 0.15, 0.10)
req = mg.short_straddle(3.0, 3.0, 100.0, 100.0, 100.0, 0.15, 0.10)
check(f"limits cut a 200% target to margin due <= 90% of capital (w_eff {big['w_eff']:.3f})",
      abs(big["w_eff"] - 6.0 * 0.9 / (req - 6.0)) < 1e-9)
crash = dict(_m, days=[(100.0, 3.0, 3.0), (60.0, 0.0, 40.0), (60.0, 0.0, 40.0)], settle=40.0)
nl = mp.simulate(crash, 0.20, {"limits"}, 0.15, 0.10)
lq = mp.simulate(crash, 0.20, {"limits", "liquidation"}, 0.15, 0.10)
check(f"a 40% crash triggers a margin call and a forced liquidation ({lq['liquidations']})", lq["liquidations"] >= 1 and nl["liquidations"] == 0)
check("with no call, the month's loss is the settlement loss", abs(nl["ret"] - nl["w_eff"] * (6.0 - 40.0) / 6.0) < 1e-9)
calm = mp.simulate(_m, 0.05, {"limits", "liquidation"}, 0.15, 0.10)
check("a quiet month at 5% never calls", calm["liquidations"] == 0 and abs(calm["ret"] - 0.05) < 1e-12)

lm = load("leakmap")
print("\n=== Leak Map attribution ===")
_add = {"spreads": 1.0, "limits": 2.0, "liquidation": 3.0, "commissions": 0.5}
v_add = lambda s: 10.0 - sum(_add[p] for p in s)
sh = lm.shapley(v_add)
check(f"additive frictions: each leak is its own effect, the same in every order ({sh})",
      all(abs(sh[p][0] - _add[p]) < 1e-12 and abs(sh[p][1] - sh[p][2]) < 1e-12 for p in _add))
v_int = lambda s: 10.0 - (4.0 if {"spreads", "liquidation"} <= s else 0.0)
si = lm.shapley(v_int)
check(f"an interaction is split evenly between the two, 2 and 2 ({si['spreads'][0]}, {si['liquidation'][0]})",
      abs(si["spreads"][0] - 2.0) < 1e-12 and abs(si["liquidation"][0] - 2.0) < 1e-12)
check("...and its range across orders is 0 to 4", si["spreads"][1] == 0.0 and si["spreads"][2] == 4.0)
check("a friction that changes nothing gets zero", si["commissions"][0] == 0.0 and si["limits"][0] == 0.0)
check("the leaks sum to paper minus kept", abs(sum(v[0] for v in sh.values()) - (v_add(frozenset()) - v_add(frozenset(_add)))) < 1e-12)

sx = load("stress")
print("\n=== stress lab ===")
import random as _r        # noqa: E402
_g = _r.Random(1)
_wn = [_g.gauss(0, 1) for _ in range(600)]
_ar, _p = [], 0.0
for _ in range(600):
    _p = 0.5 * _p + _g.gauss(0, 1); _ar.append(_p)
bw, ba = sx.ppw_block(_wn), sx.ppw_block(_ar)
check(f"PPW block length: white noise near 1 ({bw:.2f}), AR(1) rho=0.5 clearly longer ({ba:.2f})", bw < 2.0 and ba > 3.0)
_paths = sx.stationary_paths(_wn, 3.0, 4000, 120, 7)
_m = sum(sum(p) / len(p) for p in _paths) / len(_paths)
check(f"the bootstrap preserves the sample mean ({_m:+.4f} vs {sum(_wn) / len(_wn):+.4f})", abs(_m - sum(_wn) / len(_wn)) < 0.02)
check("paths have the requested length and are reproducible from the seed",
      all(len(p) == 120 for p in _paths[:5]) and sx.stationary_paths(_wn, 3.0, 3, 10, 7) == sx.stationary_paths(_wn, 3.0, 3, 10, 7))
_bl = sx.stationary_paths(list(range(100)), 50.0, 200, 20, 3)
_runs = sum(1 for p in _bl for i in range(1, len(p)) if p[i] == (p[i - 1] + 1) % 100) / sum(len(p) - 1 for p in _bl)
check(f"blocks keep neighbours together: with mean block 50, ~98% of steps continue a block ({_runs:.2f})", _runs > 0.9)
check("max drawdown of +10%, -50%, +20% is 50%", abs(sx.max_drawdown([0.10, -0.50, 0.20]) - 0.50) < 1e-12)
check("expected shortfall at 90% of 1..10 is the worst one, 1", sx.expected_shortfall(list(range(1, 11)), 0.90) == 1)
check("ruin: a path that halves counts, one that does not, does not",
      sx.ruin_prob([[-0.6], [0.1, -0.2]], 0.5) == 0.5)

be = load("breakeven")
print("\n=== Break-Even VIX statistics ===")
_x = [float(v) for v in range(10, 41)]
_y = [0.2 * v - 4.0 for v in _x]                       # crosses zero at 20
a_, b_ = be.ols(_x, _y)
check(f"OLS recovers an exact line: intercept -4, slope 0.2 ({a_:.6f}, {b_:.6f})", abs(a_ + 4) < 1e-9 and abs(b_ - 0.2) < 1e-9)
check("the crossing of that line is at 20", abs(be.crossing(a_, b_, 10, 40) - 20.0) < 1e-9)
check("a crossing outside the observed range is not reported", be.crossing(a_, b_, 25, 40) is None)
check("a flat line has no crossing", be.crossing(1.0, 0.0, 10, 40) is None)
bb = be.bins(list(range(10)), [2 * v for v in range(10)], 5)
check(f"quintile bins of 10 points: 5 bins of 2, means right ({bb})", len(bb) == 5 and all(c == 2 for *_, c in bb) and bb[0][:2] == (0.5, 1.0))
_g2 = _r.Random(5)
_yn = [0.2 * v - 4.0 + _g2.gauss(0, 0.5) for v in _x * 4]
s_, lo_, hi_ = be.slope_ci(_x * 4, _yn, 4)
check(f"a real positive slope has an interval above zero ({lo_:.3f}..{hi_:.3f})", lo_ > 0 and lo_ < s_ < hi_)
_flat = [_g2.gauss(0, 1) for _ in _x * 4]
s2, lo2, hi2 = be.slope_ci(_x * 4, _flat, 4)
check(f"pure noise: the interval covers zero ({lo2:.3f}..{hi2:.3f})", lo2 < 0 < hi2)
cr, out_ = be.boot_crossing(_x * 4, _yn, 1.0, 300, 11, 10, 40)
cr.sort()
check(f"bootstrapped crossings cluster at 20 (median {cr[len(cr) // 2]:.2f}, {out_} out of range)",
      abs(cr[len(cr) // 2] - 20.0) < 1.0 and out_ == 0)

eng = load("engine")
print("\n=== trust engine ===")
check("pilot calibration carried from H8-DRAFT (SPY gap 0.055, floor 0.010, ratio 2.07)", eng.PILOT["SPY"] == (0.055, 0.010, 2.07))


def _chain(day="2026-10-13", S=100.0, sig=0.25, frac=0.02, zero_wings=False, stale=False, step=2):
    rows = []
    for e, dte in (("2026-11-06", 24), ("2026-11-20", 38)):
        for K in range(70, 131, step):
            for k in "CP":
                p = black76(k, S, float(K), dte / 365.0, 0.0, sig)
                b, a = max(p * (1 - frac), 0.01), p * (1 + frac) + 0.02
                if zero_wings and abs(K - S) >= 20:
                    b = 0.0
                qt = "2026-10-13T15:02:00Z" if (stale and K % 10 == 0) else "2026-10-13T18:40:00Z"
                rows.append({"date": day, "symbol": "SPY", "spot": str(S), "quote_time": qt, "expiration": e,
                             "dte": str(dte), "type": k, "strike": str(float(K)), "moneyness": str(K / S),
                             "option_symbol": f"SPY{e[2:4]}{e[5:7]}{e[8:]}{k}{K * 1000:08d}",
                             "bid": f"{b:.4f}", "ask": f"{a:.4f}", "mid": f"{(a + b) / 2:.4f}", "vega": ""})
    return rows


hist = [r for d in ("2026-10-08", "2026-10-09") for r in _chain(day=d)]
g = eng.read(_chain(), hist)
check(f"a clean chain reads near its 25% and raises no flags ({g['vol']:.2f}, {g['flags']})", abs(g["vol"] - 25.0) < 1.5 and g["flags"] == [])
check(f"the error bar is SPY's pilot gap plus floor, 0.065 ({g['err']})", abs(g["err"] - 0.065) < 1e-12)
check("the corrected cost is the raw cost over SPY's free/OPRA ratio", abs(g["cost_corrected"] - g["cost_raw"] / 2.07) < 1e-12)
check("the straddle cost in vol points is 0.8 x the median leg half-spread / vega - no factor of 2",
      abs(g["cost_raw"] - 0.8 * eng.atm_halfspread_pts(_chain())) < 1e-12)
check("zero-bid wings are flagged", "zero-bid wings" in eng.read(_chain(zero_wings=True), hist)["flags"])
check("stale quotes are flagged", "stale quotes" in eng.read(_chain(stale=True), hist)["flags"])
check("a thin chain is flagged", "thin chain" in eng.read(_chain(step=15), hist)["flags"])
check("spreads wider than this fund's 90th percentile are flagged", "wide spreads" in eng.read(_chain(frac=0.10), hist)["flags"])
check("an empty chain reads nothing", eng.read([], hist)["vol"] is None)

print("\n=== contract adjustments (28 Oct 2026, outside review M03) ===")
_bars = {"USO": {"2020-04-20": (3.70, 0.0), "2020-05-15": (22.40, 0.0)}, "SPY": {"2020-05-15": (290.0, 0.0)}}
check("a USO contract opened before the 29 Apr 2020 split settles on OCC's USO1 = 0.125 x USO (memo #46881)",
      abs(tr.settle(_bars, "USO", "2020-05-15", opened="2020-04-20") - 2.80) < 1e-12)
check("a contract opened after the split, or a fund without an event, settles on the raw close",
      tr.settle(_bars, "USO", "2020-05-15", opened="2020-05-01") == 22.40
      and tr.settle(_bars, "SPY", "2020-05-15", opened="2020-04-20") == 290.0
      and tr.settle(_bars, "USO", "2020-05-15") == 22.40)
_t0 = datetime(2020, 4, 27, 18, 30, tzinfo=timezone.utc)
_mixed = {"USO   200515C00002000": [(_t0, 0.1, 0.2)], "USO1  200515C00002000": [(_t0, 14.0, 14.2)]}
try:
    integ.chain_at(_mixed, "2020-05-15", _t0)
    check("two option roots for one expiry are refused, never silently overwritten", False)
except ValueError:
    check("two option roots for one expiry are refused, never silently overwritten", True)

vp = load("verify_purchases")
print("\n=== purchase verification ===")
_vd = Path(__import__("tempfile").mkdtemp())
_qh = "ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol\n"
(_vd / "OPRA_LAB_SPY_2018-02-05_1430.csv").write_text(_qh + "2018-02-05T19:30:00Z,,193,30,1,N,,0,0,1.0,1.1,1,1,1,1,SPY   180316C00265000\n")
(_vd / "OPRA_LAB_QQQ_2018-12-24_1430.csv").write_text(_qh)
(_vd / "OPRA_LAB_IWM_2018-02-05_1430.csv").write_text(_qh + "2018-02-05T19:30:00Z,,193,30,1,N,,0,0,1.0,1.1,1,1,1,1,IWM   180316C00150")
(_vd / "DEF_LAB_GLD_2018-02-05.csv").write_text("ts_recv,raw_symbol\n2018-02-05T10:30:00Z,SPY   180316C00265000\n")
check("a good quote file passes", vp.file_problem(_vd / "OPRA_LAB_SPY_2018-02-05_1430.csv") is None)
check("a header-only file is caught (the 14 Oct false positive)", vp.file_problem(_vd / "OPRA_LAB_QQQ_2018-12-24_1430.csv") == "header only - no data rows")
check("a truncated file is caught", "truncated" in vp.file_problem(_vd / "OPRA_LAB_IWM_2018-02-05_1430.csv"))
check("another fund's data under this fund's name is caught", "is not GLD" in vp.file_problem(_vd / "DEF_LAB_GLD_2018-02-05.csv"))
_files = ["OPRA_LAB_SPY_2018-02-05_1430.csv", "OPRA_LAB_SPY_2018-02-06_1555.csv", "DEF_LAB_SPY_2018-02-05.csv"]
_led = [{"date": "2018-02-05", "symbol": "SPY-lab"}, {"date": "2018-02-05", "symbol": "SPY-def-lab"}, {"date": "2018-02-07", "symbol": "QQQ-lab"}]
_mm = vp.reconcile(_files, _led)
check(f"a file with no ledger row and a ledger row with no file are both caught ({_mm})",
      (("quote", "2018-02-06", "SPY"), 1, 0) in _mm and (("quote", "2018-02-07", "QQQ"), 0, 1) in _mm and len(_mm) == 2)
check("a matched set reconciles clean", vp.reconcile(_files[:1] + _files[2:], _led[:2]) == [])

vt = load("vault")
print("\n=== the sealed vault ===")
_o, _s = vt.split()
check(f"the vault's split still matches the fingerprint sealed on 14 Oct ({vt.fingerprint()[:12]}...)", vt.fingerprint() == vt.FINGERPRINT)
check("43 quarters, 2016Q1-2026Q3, each in exactly one half", len(_o) + len(_s) == 43 and not set(_o) & set(_s))
check("the stress quarters are split evenly (3 and 3)", len(set(vt.STRESS) & set(_s)) == 3 and len(set(vt.STRESS) & set(_o)) == 3)
check("COVID's quarter is sealed, the 2025 tariff crash is open", vt.is_sealed("2020-03-16") and not vt.is_sealed("2025-04-07"))
check("the split is the same every time it is drawn", vt.split() == (_o, _s))

rp = load("report")
print("\n=== the Lab page (report.py) ===")
check("figures use a true minus, a plus on request, and never '-0.0'",
      rp.num(-1.25) == "−1.2" and rp.num(2, 0, True) == "+2" and rp.num(-0.04) == "0.0" and rp.num(0.319, 3, True) == "+0.319")
check("y ticks cover the data in whole steps", rp.ticks(-1.77, 2.15) == [-2, -1, 0, 1, 2, 3])
check("x ticks step by 5 over a 20-point range", rp.ticks(10.7, 30.4) == [10, 15, 20, 25, 30, 35])
check("the pilot ratios are read from engine.py's own PILOT",
      rp.pilot_ratios() == {k: v[2] for k, v in eng.PILOT.items()})


import copy as _copy        # noqa: E402
import csv as _csv          # noqa: E402
import html as _html        # noqa: E402
import json as _json        # noqa: E402


def _stop(fn, *a):
    """The message a refusal stops with, or None when fn returns: each refusal test names the guard it expects, so
    a stop from some other guard cannot pass it."""
    try:
        fn(*a)
    except SystemExit as e:
        return str(e)
    return None


def _page(*a):
    """rp.page's output, or the error it stopped or crashed with: a broken guard then fails its own check instead of
    ending the run."""
    try:
        return rp.page(*a)
    except (SystemExit, Exception) as e:
        return f"[{type(e).__name__}: {e}]"


def _lw(paper, sp, cm, lim=0.0, liq=0.0, called=0):
    """One weight in leak_summary.json's layout. Shapley values add up, so kept is the paper return less the four
    leaks; each leak is [value, min, max] over the 24 orders, the margin pair spread around its value."""
    rng = lambda v: [v, min(0.5 * v, 1.5 * v), max(0.5 * v, 1.5 * v)]
    return {"paper": paper, "kept": paper - (sp + lim + liq + cm), "called": called,
            "leaks": {"spreads": [sp, sp, sp], "limits": rng(lim), "liquidation": rng(liq), "commissions": [cm, cm, cm]}}


# The fixture holds the facts the page's sentences rest on (report.py's premises and the logged verdicts): only GLD
# lacks a paper profit; SPY, QQQ and IWM keep over 85 cents, USO 58 with the widest spreads; at 20% forced
# liquidation leads on SPY and QQQ, while on IWM it cut a growing loss, so more is kept than the paper trade made.
_PAPER = {"SPY": 0.004, "QQQ": 0.004, "IWM": 0.004, "GLD": -0.002, "USO": 0.004}
_SPREAD = {"SPY": 0.00012, "QQQ": 0.0002, "IWM": 0.00028, "GLD": 0.0001, "USO": 0.0016}
_RUIN = {"SPY": 0.02, "QQQ": 0.03, "IWM": 0.12, "GLD": 0.2, "USO": 0.15}
_CALLED = {"SPY": 31, "QQQ": 30, "IWM": 40, "GLD": 20, "USO": 45}
_N = {"SPY": 127, "QQQ": 127, "IWM": 127, "GLD": 123, "USO": 125}


def _fund(s):
    p, w5 = _PAPER[s], _lw(_PAPER[s], _SPREAD[s], 0.00008)
    w20 = _lw(4 * p, 0.0064 if s == "USO" else 0.0002, 0.0001, -0.0016, -0.0032 if s == "IWM" else 0.0032, _CALLED[s])
    return {"weights": {"0.025": w5, "0.05": w5, "0.1": w5, "0.2": w20},
            "stress": {"block": 1.0, "dd50": 0.2, "dd95": 0.45, "dd99": 0.6, "es95": -0.05, "ruin": _RUIN[s], "worst": -0.25}}


def _be1(s):
    counts = {127: [25, 25, 25, 26, 26], 123: [24, 25, 25, 24, 25], 125: [25] * 5}[_N[s]]
    xs = [12.0, 15.0, 18.0, 21.0, 30.0]
    # SPY's groups average onto one line, net = -0.1 x (VIX - 18): its middle three sit off it by amounts that cancel
    # in the count-weighted mean (25 x 2.6 - 25 x 5.2 + 26 x 2.5 = 0), so the fit is still known - slope -0.1,
    # crossing 18 - while the groups swing by points from one to the next, as the page says they do.
    net = ([-0.1 * (x - 18.0) + dy for x, dy in zip(xs, (0.0, 2.6, -5.2, 2.5, 0.0))] if s == "SPY"
           else [0.5, -1.0, 1.5, 0.2, -0.4])
    peak = {"USO": 1.5, "GLD": 0.3}.get(s, 0.09)
    d = {"index": {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}[s],
         "net_bins": [[x, y, n] for x, y, n in zip(xs, net, counts)],
         "cost_bins": [[x + 0.1, peak * f, n] for x, f, n in zip(xs, (0.2, 0.3, 0.5, 0.7, 1.0), (100, 101, 100, 101, 102))],
         "crossing": 9.7 if s == "GLD" else 18.0, "ci": [12.1, 27.6] if s == "SPY" else [12.0, 30.0],
         "out": 100 if s == "IWM" else 200, "n_month": _N[s], "n_week": 504, "range": [9.4, 66.0],
         "p4_slope": [2e-4, 1e-4, 3e-4] if s == "GLD" else [1e-5, -1e-5, 3e-5]}
    if s == "SPY":
        d["vix_axis"] = {"slope": -0.1, "crossing": 18.0}
    return d


_leak = {s: _fund(s) for s in rp.FUNDS}
_be = {s: _be1(s) for s in rp.FUNDS}
_ADDED = {"GLD": {"n": 127, "0.05": _lw(-0.0025, 0.0001, 0.00008), "0.2": _lw(-0.01, 0.0002, 0.0001, -0.0016, 0.0032, 22)},
          "USO": {"n": 127, "0.05": _lw(0.0039, 0.0016, 0.00008), "0.2": _lw(0.0156, 0.0064, 0.0001, -0.0016, 0.0032, 46)}}
_ADD_STRESS = {"GLD": {"n": 127, "block": 1.0, "dd50": 0.3, "dd95": 0.6, "ruin": 0.35, "worst": -0.3},
               "USO": {"n": 127, "block": 1.0, "dd50": 0.22, "dd95": 0.5, "ruin": 0.16, "worst": -0.28}}
_COVID = {"SPY": -0.1, "QQQ": -0.09, "IWM": -0.12, "GLD": -0.03, "USO": -0.11}
_RATIO = {"SPY": (3.0, 3.4, 3.2), "QQQ": (2.8, 2.9, 3.0), "IWM": (2.6, 2.7, 2.8), "GLD": (1.9, 2.1, 2.0), "USO": (2.4, 2.6, 2.5)}
_trades = []
for _s in rp.FUNDS:
    _ret, (_lo, _, _hi) = {"GLD": "-0.04", "USO": "0.07"}.get(_s, "0.05"), sorted(_RATIO[_s])
    for (_e, _x), _r in zip((("2016-01-19", "2016-02-19"), ("2021-06-21", "2021-07-16"), ("2026-07-20", "2026-08-21")), _RATIO[_s]):
        _trades.append({"entry": _e, "expiry": _x, "symbol": _s, "registered": "1", "straddle_mid_ret": _ret,
                        "strip_cost_fixed_pts": f"{0.5 * _r:.4f}", "atm_cost_pts": "0.5"})
    # The rest of the fund's registered months (every input counts the same months, _N), inside that span and 28 days
    # long; half at the fund's lowest strip ratio and half at its highest, so the median is still the middle trade's
    # and one excluded month's ratio would move it.
    for _i in range(_N[_s] - 3):
        _e = _d(2016 + (2 + _i) // 12, (2 + _i) % 12 + 1, 10)
        _trades.append({"entry": _e.isoformat(), "expiry": (_e + _td(28)).isoformat(), "symbol": _s, "registered": "1",
                        "straddle_mid_ret": _ret, "strip_cost_fixed_pts": f"{0.5 * (_lo if _i % 2 else _hi):.4f}",
                        "atm_cost_pts": "0.5"})
    # Excluded months, before the registered span, strip ratio 1. GLD's four and USO's two can still be traded (both
    # added-back samples hold all 127 months); one more of USO's cannot, nor can the equity funds' one each.
    for _i, _v in enumerate({"GLD": ["-0.16"] * 4, "USO": ["0.20", "0.20", ""]}.get(_s, [""])):
        _trades.append({"entry": f"2015-0{_i + 1}-05", "expiry": f"2015-0{_i + 2}-02", "symbol": _s, "registered": "0",
                        "straddle_mid_ret": _v, "strip_cost_fixed_pts": "0.5", "atm_cost_pts": "0.5"})


def _p3text(leak, added, add_stress, covid):
    """lab-out/report-plan3.txt in run_leak.py's form - every line shape copied from the real file, the numbers
    this fixture's: a [registered] and an [added back] block per fund, the stress lab, the crash replays."""
    pc, lc = (lambda v: f"{100 * v:+.3f}"), (lambda v: f"{100 * v:+.4f}")
    out = ["lab/ margin, Leak Map, stress (EXPLORATORY). Short ATM straddle (R9), held to expiry.", ""]

    def block(s, kind, n, ws, broker):
        w5, w20 = ws["0.05"], ws["0.2"]
        c = f"  {100 * w5['kept'] / w5['paper']:.1f} cents per $1" if w5["paper"] > 0 else "   not defined (paper <= 0)"
        out.append(f"{s} [{kind}] n={n}  paper {pc(w5['paper'])}%/mo  kept {pc(w5['kept'])}%/mo  ->{c};  largest leak: spreads")
        out.extend(f"      {k:<12} {lc(w5['leaks'][k][0])}%/mo  (orders: {lc(w5['leaks'][k][1])} to {lc(w5['leaks'][k][2])})"
                   for k in rp.LEAKS)
        for w, d in (("2.5", w5), ("10", w5), ("20", w20)):
            out.append(f"      at w {w}%: paper {pc(d['paper'])} kept {pc(d['kept'])}%/mo; leaks " + ", ".join(
                f"{k} {lc(d['leaks'][k][0])} ({lc(d['leaks'][k][1])}..{lc(d['leaks'][k][2])})" for k in rp.LEAKS))
        out.append(f"      margin: w 2.5%: eff 1.25%, called in 0  w 5%: eff 2.50%, called in {w5['called']}  "
                   f"w 10%: eff 5.00%, called in 2  w 20%: eff 10.00%, called in {w20['called']}")
        if broker is not None:
            out.append(f"      broker 25%/15%{broker}: kept {pc(w5['kept'])}%/mo, called in 0 at w 5%")

    for s in rp.FUNDS:
        block(s, "registered", _N[s], leak[s]["weights"], "")
        if s in added:
            block(s, "added back", added[s]["n"], added[s], " [added back]")
        else:
            block(s, "added back", _N[s], leak[s]["weights"], None)
        out.append("")

    def sline(x):
        return (f"block {x['block']:.1f}  maxDD median {100 * x['dd50']:.1f}% p95 {100 * x['dd95']:.1f}% p99 61.0%  "
                f"ES95 -5.00%  ES99 -7.50%  ruin(<$0.50) {100 * x['ruin']:.1f}%  worst month {100 * x['worst']:+.2f}%")

    sens = "block sensitivity: b1: ruin 2.0%  b2: ruin 2.1%  b3: ruin 2.2%  b12: ruin 1.9%"
    out.append("== stress lab: kept monthly returns at w = 5%, stationary bootstrap, 10,000 ten-year paths ==")
    for s in rp.FUNDS:
        st = leak[s]["stress"]
        out += [f"  {s} {sline(st)} (x1.5: {150 * st['worst']:+.2f}%)", f"       {sens}"]
        if s in add_stress:
            out += [f"       [added back, n={add_stress[s]['n']}] {sline(add_stress[s])}", f"       [added back] {sens}"]
        else:
            out.append("       [added back] no excluded month to add back - identical to the registered sample")
    out += ["", "== crash replays: kept return at w = 5% of every trade HELD during a stress month ==",
            "  2018-02: " + "  ".join(f"{s} 01-22->02-16 -1.50%  {s} 02-20->03-16 +0.80%" for s in rp.FUNDS),
            "  2020-03: " + "  ".join(f"{s} 02-24->03-20 {100 * v:+.2f}%  {s} 03-23->04-17 -2.00%" for s, v in covid.items())
            + "   | added back: USO 03-23->04-17 +5.00%",
            "", "Data provided by Databento (OPRA consolidated NBBO). Aggregates only. Cboe index levels: Cboe Global Markets."]
    return "\n".join(out) + "\n"


_sens = rp.sensitivity(_trades)
check(f"the excluded-months sensitivity averages registered months, then all tradeable months, never USO's "
      f"untradeable one ({_sens})", abs(_sens["GLD"][0] + 4.0) < 1e-9 and abs(_sens["USO"][0] - 7.0) < 1e-9
      and abs(_sens["GLD"][1] - 100 * (123 * -0.04 + 4 * -0.16) / 127) < 1e-9
      and abs(_sens["USO"][1] - 100 * (125 * 0.07 + 2 * 0.20) / 127) < 1e-9)
_r3 = rp.strip_ratios(_trades)
check(f"P3's medians use the registered trades only, never an excluded month's ratio of 1 ({_r3['SPY']:.2f}, {_r3['GLD']:.2f})",
      all(abs(_r3[s] - sorted(_RATIO[s])[1]) < 1e-12 for s in rp.FUNDS))
check("the trade's span is the registered trades': first and last entry, last expiry, 25 to 32 days held",
      rp.span(_trades) == (_d(2016, 1, 19), _d(2026, 7, 20), _d(2026, 8, 21), 25, 32))

_txt = _p3text(_leak, _ADDED, _ADD_STRESS, _COVID)
_p3 = rp.plan3(_txt, _leak)
check("the Plan 3 report parses: GLD and USO come back with all 127 months, USO keeping 56.9 cents; the others "
      "have nothing to add back", sorted(_p3["added"]) == ["GLD", "USO"] and _p3["added"]["USO"]["n"] == 127
      and abs(_p3["added"]["USO"]["0.05"]["paper"] - 0.0039) < 1e-9 and _p3["added"]["USO"]["0.05"]["cents"] == 56.9
      and _p3["added"]["GLD"]["0.2"]["called"] == 22 and sorted(_p3["stress"]) == ["GLD", "USO"]
      and abs(_p3["stress"]["GLD"]["ruin"] - 0.35) < 1e-12)
check("...and the COVID trade is each fund's first one held through March 2020 (24 Feb to 20 Mar), never the "
      "second or the added-back one", _p3["covid"]["SPY"][:2] == ((2, 24), (3, 20))
      and all(abs(_p3["covid"][s][2] - _COVID[s]) < 1e-12 for s in rp.FUNDS))
for _why, _old, _new, _want in (
        ("a registered line that no longer matches leak_summary.json (a stale report)",
         "SPY [registered] n=127  paper +0.400", "SPY [registered] n=127  paper +0.410", "registered SPY line at w = 0.05"),
        ("a stress line that no longer matches it", "ruin(<$0.50) 2.0%", "ruin(<$0.50) 3.0%", "registered SPY stress line"),
        ("a missing block", "QQQ [added back]", "QQQ [added]", "added back block for QQQ is missing"),
        ("added-back figures that differ though no month was excluded",
         "SPY [added back] n=127  paper +0.400", "SPY [added back] n=127  paper +0.401", "SPY has no excluded month"),
        ("an added-back sample smaller than the registered one", "USO [added back] n=127", "USO [added back] n=120", "smaller"),
        ("added-back figures that do not add up", "USO [added back] n=127  paper +0.390%/mo  kept +0.222",
         "USO [added back] n=127  paper +0.390%/mo  kept +0.232", "USO added back, w = 0.05: kept plus the four leaks"),
        ("added-back cents that do not follow from its returns", "56.9 cents", "58.9 cents", "cents kept do not follow"),
        ("a crash replay without one fund's COVID trade", "GLD 02-24->03-20", "GLD 02-25->03-20", "March 2020 crash replay"),
        ("a block printed twice, whose lines would mix with the first's", "QQQ [registered]", "SPY [registered]",
         "registered block for SPY appears twice"),
        ("a stress line printed twice", "  QQQ block 1.0", "  SPY block 1.0", "registered stress line for SPY appears twice")):
    _bad = _txt.replace(_old, _new, 1)
    check(f"the report is refused for {_why}", _bad != _txt and _want in (_stop(rp.plan3, _bad, _leak) or ""))
_bad = _txt.replace("       [added back] no excluded month to add back - identical to the registered sample\n", "", 1)
check("...and for a fund with nothing to add back whose stress lab does not say so",
      _bad != _txt and "SPY has no excluded month" in (_stop(rp.plan3, _bad, _leak) or ""))
_t126 = _txt.replace("SPY [registered] n=127", "SPY [registered] n=126").replace("SPY [added back] n=127", "SPY [added back] n=126")
_p126 = rp.plan3(_t126, _leak) if _stop(rp.plan3, _t126, _leak) is None else None
check("Plan 3, the break-even summary and trades.csv must count the same months: a report whose two SPY blocks both "
      "say 126 parses, and the page refuses it", _p126 is not None and _p126["n"]["SPY"] == 126
      and "SPY: the inputs count different months" in (_stop(rp.page, _leak, _be, _trades, _p126) or ""))
check("...and refuses a trades.csv missing one registered month",
      "QQQ: the inputs count different months" in (_stop(rp.page, _leak, _be, [t for t in _trades if not (
          t["symbol"] == "QQQ" and t["entry"] == "2021-06-21")], _p3) or ""))
check("...and one with a tradeable excluded month on a fund the report says has nothing to add back",
      "SPY: the inputs count different months" in (_stop(rp.page, _leak, _be, _trades + [dict(
          _trades[0], entry="2015-03-02", expiry="2015-03-20", registered="0")], _p3) or ""))

_pg = rp.page(_leak, _be, _trades, _p3)
check("known answer: paper 0.4%, spreads 0.012% and commissions 0.008% -> 95.0 cents kept, 3.0 and 2.0 leaked, "
      "each part its true share of the bar's width", '<span class="lm-v">95.0¢</span>' in _pg
      and 'style="width:95.00%"' in _pg and 'style="width:3.00%"' in _pg and 'style="width:2.00%"' in _pg)
check("the bar names its parts for a screen reader", 'aria-label="SPY, premium 5% of the account: 95.0¢ kept; '
      '3.0¢ spreads; 2.0¢ commissions; +0.400% paper return a month"' in _pg)
check("a fund with no paper profit is listed, never drawn, and its table rows say why", "no paper dollar to keep" in _pg
      and _pg.count('class="lm-row"') == 4 and _pg.count("no paper profit, so nothing kept to share out") == 4)
check("at 20% each margin share shows its range over the 24 orders: limits -10.0 (-15.0 to -5.0), "
      "liquidation +20.0 (+10.0 to +30.0)", "−10.0 <span class=\"rg\">(−15.0 to −5.0)</span>" in _pg
      and "+20.0 <span class=\"rg\">(+10.0 to +30.0)</span>" in _pg)
check("the excluded months come back beneath GLD and USO in both leak tables and the stress table, and the "
      "Leak Map's caption says what they change", _pg.count("GLD, all 127 months") == 3
      and _pg.count("USO, all 127 months") == 3 and "With its 2 excluded months added back, USO keeps 56.9 cents." in _pg
      and "With its 4 excluded months added back, GLD still has no paper profit." in _pg
      and "with its 4 gold-rally months back" in _pg)
check("at 20% the text names where forced liquidation leads (SPY and QQQ) and where it left more than the paper "
      "trade made (IWM, 128 cents)", "forced liquidation became the largest leak on SPY and QQQ." in _pg
      and 'On IWM the same rule cut losses that kept growing, so the seller kept <span class="m">128</span>' in _pg)
check("the COVID sentence names the three largest losses, in fund order",
      'cost SPY <span class="m">10.0%</span>, IWM <span class="m">12.0%</span> and USO <span class="m">11.0%</span> '
      "of the account" in _pg and "(24 February to 20 March 2020)" in _pg)
check("the trade's dates on the page are the registered trades' own",
      "The first entry was on 19 January 2016, the last on 20 July 2026, expiring 21 August 2026." in _pg
      and "(25 to 32 days)" in _pg)
check("SPY's fitted line is the one its months give (slope -0.1 through 18) and is drawn",
      abs(rp.fit_slope("SPY", _be["SPY"]) + 0.1) < 1e-12 and _pg.count('class="fit"') == 5)
check("a crossing outside its own interval is said to be, and one beyond the axis is written at its edge",
      "Crosses zero at 9.7, outside its own interval" in _pg and ">← 9.7</text>" in _pg)
check("the predictions table carries each claim word for word, the logged verdicts and the evidence",
      all(_html.escape(c[0].upper() + c[1:]) in _pg for c in rp.CLAIMS.values()) and _pg.count("Tested, fails") == 2
      and "No fund keeps under 50 cents" in _pg and "5 of 5 funds, 2.0 to 3.2 times" in _pg
      and "Rises on 1 of 5 (GLD)" in _pg and "SPY 95 highest, USO 58 lowest" in _pg)
_b5 = _copy.deepcopy(_be)
_b5["SPY"]["p4_slope"] = [-2e-4, -3e-4, -1e-4]
_p4n = _page(_leak, _b5, _trades, _p3)
check("P4's evidence states the registered test and claims no proportional widening: with the others' intervals "
      "around zero it says so; a significantly falling slope leaves the verdict alone and is not called flat",
      "lies wholly above zero only there; on the others it includes zero" in _pg and "in step" not in _pg
      and "Rises on 1 of 5 (GLD)" in _p4n and "the others do not pass it" in _p4n and "includes zero" not in _p4n)
check("the equity funds' spread cost is bounded without overstating: its peak is 0.09, so 'at or below 0.09', "
      "never 'under'", 'stays at or below <span class="m">0.09</span> of a point' in _pg and "stays under" not in _pg)
_bn = _copy.deepcopy(_be)
_bn["SPY"]["ci"], _bn["QQQ"]["crossing"] = None, None
_pn = _page(_leak, _bn, _trades, _p3)
check("on the page, a crossing without an interval and an interval without a crossing each render as what they "
      "are, and the text counts only the intervals there are",
      "<b>SPY</b> on VIX (9.4 to 66.0 in the data). Crosses zero at 18.0; no interval;" in _pn
      and "<b>QQQ</b> on VXN (9.4 to 66.0 in the data). No crossing inside the data; 90% interval 12.0 to 30.0;" in _pn
      and ('crosses zero for 4 of 5 funds, but its 90% interval is <span class="m">18</span> index points wide '
           "(SPY has no interval)") in _pn and _pn.count('class="fit"') == 4)
check("every section with a figure credits Databento, and the page marks itself in the navigation",
      all(rp.CREDIT in p for p in _pg.split("<figure")[1:]) and 'here: "lab"' in _pg and '["Lab", "lab.html", "lab"]' in _pg)

_m = _copy.deepcopy(_leak)
_m["SPY"]["weights"]["0.05"] = _lw(0.004, 0.00012, 0.00008, liq=0.0001)
check("a margin leak at 5% stops the Leak Map rather than draw a bar that is not one paper dollar",
      "a liquidation leak at w = 5%" in (_stop(rp.leak_map, _m, {}) or ""))
_m["SPY"]["weights"]["0.05"] = _lw(0.004, 0.00012, 0.00008)
_m["SPY"]["weights"]["0.05"]["leaks"]["limits"] = [0.0, -0.0001, 0.0001]
check("...and so does a margin leak that is zero on average but not in every order",
      "a limits leak at w = 5%" in (_stop(rp.leak_map, _m, {}) or ""))
_m["SPY"]["weights"]["0.05"] = _lw(0.004, 0.00012, 0.00008, called=1)
check("...and a margin call at 5%", "a margin call at w = 5%" in (_stop(rp.leak_map, _m, {}) or ""))
_m["SPY"]["weights"]["0.05"] = _lw(0.004, 0.005, 0.00008)
check("...and a negative part (kept, when the spreads exceed the paper return)", "a negative part" in (_stop(rp.leak_map, _m, {}) or ""))
_m["SPY"]["weights"]["0.05"] = _lw(0.004, 0.00012, 0.00008)
_m["SPY"]["weights"]["0.05"]["kept"] += 1e-6
check("...and parts that do not add up to the paper return", "is not the paper return" in (_stop(rp.leak_map, _m, {}) or ""))
_m = _copy.deepcopy(_leak)
_m["SPY"]["weights"]["0.05"]["leaks"]["spreads"] = [0.00012, 0.0001, 0.00014]
check("...and spreads whose share changes with the order, which the caption says cannot happen at this size",
      "the spreads share differs across the 24 orders" in (_stop(rp.leak_map, _m, {}) or ""))
_m = _copy.deepcopy(_leak)
_m["GLD"]["weights"]["0.05"] = _lw(-0.002, 0.0001, 0.00008, liq=0.0001)
check("...and a margin leak on the fund with no paper profit, which is listed, not drawn, but which the caption "
      "covers too", "GLD: a liquidation leak at w = 5%" in (_stop(rp.leak_map, _m, {}) or ""))
_a = _copy.deepcopy(_p3["added"])
_a["USO"]["0.05"]["called"] = 1
check("...and a margin call in an added-back sample, shown in the figure's own table",
      "USO added back: a margin call at w = 5%" in (_stop(rp.leak_map, _leak, _a) or ""))
_k5 = {s: 100 * _leak[s]["weights"]["0.05"]["kept"] / _leak[s]["weights"]["0.05"]["paper"] for s in rp.FUNDS if s != "GLD"}
check("the fixture gives the logged verdicts (P1 fails, P2 and P3 hold, P4 fails, P5 holds)",
      _stop(rp.predictions, _leak, _be, _k5, _r3) is None)
check("summaries that would turn P5 (USO no longer lowest) stop the page: the logged verdict stands",
      "judge P5 differently" in (_stop(rp.predictions, _leak, _be, {**_k5, "USO": 99.0}, _r3) or ""))
_b4 = _copy.deepcopy(_be)
for _s in rp.FUNDS:
    _b4[_s]["p4_slope"] = [2e-4, 1e-4, 3e-4]
check("...and so do summaries that would turn P4", "judge P4 differently" in (_stop(rp.predictions, _leak, _b4, _k5, _r3) or ""))
_p3b = _copy.deepcopy(_p3)
_p3b["stress"]["GLD"]["ruin"] = 0.25
check("summaries that no longer fit a sentence stop the page and name the sentence",
      "materially worse" in (_stop(rp.premises, _leak, _be, _k5, _p3b, _sens) or ""))
_l20 = _copy.deepcopy(_leak)
_l20["SPY"]["weights"]["0.2"]["called"] = 12
check("...margin calls in fewer than one month in ten at 20% are not 'often'",
      "margin calls came often" in (_stop(rp.premises, _l20, _be, _k5, _p3, _sens) or ""))
_bf = _copy.deepcopy(_be)
_bf["SPY"]["net_bins"][2][1] = 1.5
check("...and SPY's middle groups less than two points apart do not 'swing by several volatility points'",
      "swings by several volatility points" in (_stop(rp.premises, _leak, _bf, _k5, _p3, _sens) or ""))
_bs = _copy.deepcopy(_be["SPY"])
_bs["vix_axis"]["slope"] += 1e-6
check("a stored VIX fit the quintile table does not give stops the chart",
      "is not the stored fit" in (_stop(rp.fit_slope, "SPY", _bs) or ""))
_bs = dict(_be["SPY"], n_month=128)
check("...and so does a quintile table that does not hold every month traded",
      "not the 128 traded" in (_stop(rp.fit_slope, "SPY", _bs) or ""))
check("a crossing without an interval keeps its point estimate",
      "Crosses zero at 18.0; no interval; 10% of resamples" in rp.be_caption("SPY", dict(_be["SPY"], ci=None)))
check("an interval without a crossing is still reported, and no crossing is invented",
      "No crossing inside the data; 90% interval 12.1 to 27.6; 10% of resamples"
      in rp.be_caption("SPY", dict(_be["SPY"], crossing=None))
      and "No crossing inside the data; no interval; 10% of resamples" in rp.be_caption("SPY", dict(_be["SPY"], crossing=None, ci=None)))

_od, _real_out = Path(__import__("tempfile").mkdtemp()), rp.OUT_DIR
rp.OUT_DIR = _od
try:
    check("with no summaries on the machine (a fresh clone, CI) there is nothing to render", rp.render() is None)
    (_od / "leak_summary.json").write_text(_json.dumps(_leak))
    check("some summaries without the rest is a broken setup, not a fresh clone: it stops and names what is missing",
          "missing breakeven_summary.json, trades.csv, report-plan3.txt" in (_stop(rp.render) or ""))
    (_od / "breakeven_summary.json").write_text(_json.dumps(_be))
    with open(_od / "trades.csv", "w", newline="") as _f:
        _w = _csv.DictWriter(_f, fieldnames=list(_trades[0]))
        _w.writeheader()
        _w.writerows(_trades)
    (_od / "report-plan3.txt").write_text(_txt)
    check("from the four files on disk, render() gives exactly the page the parts give", rp.render() == _pg)
finally:
    rp.OUT_DIR = _real_out

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
