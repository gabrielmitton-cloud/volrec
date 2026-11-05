"""Unit tests for the index-timing reader (tools/index_timing.py). No network and no licensed data: every file
here is SYNTHETIC, written in DBIX's recorded layout (Databento CSV, pretty timestamps, symbols mapped,
rtype 32 for one-second bars; read 4 Nov 2026 as structure only), with made-up values.
python tools/test_index_timing.py
"""
import contextlib
import gzip
import hashlib
import importlib.util as iu
import io
import math
import os
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
_s = iu.spec_from_file_location("index_timing", R / "tools/index_timing.py")
it = iu.module_from_spec(_s); _s.loader.exec_module(it)
fails = []
UTC = timezone.utc
S = timedelta(seconds=1)
# Typed here from Databento's documented OHLCV field order (map_symbols adds `symbol` last), not taken from the
# reader, so the fixtures do not borrow the code's own assumption. If both were wrong the same way, the reader
# still refuses the first real file whose header differs (checked below), rather than misreading it.
DBIX_HEADER = "ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol"


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def raises(fn, *a):
    """The SystemExit message when fn refuses, else None."""
    try:
        fn(*a)
    except SystemExit as e:
        return str(e)
    return None


def stamp(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + ".000000000Z"


def write_day(folder, day, prints, extra=()):
    """One gzipped ohlcv-1s file: prints = {symbol: [(utc time, close)]}, rows in time order across symbols."""
    iid = {"OVX": 1001, "GVZ": 1002, "VIX": 1003, "VXAPL": 1004}
    rows = sorted((ts, s, c) for s, pts in prints.items() for ts, c in pts)
    lines = [DBIX_HEADER] + [f"{stamp(ts)},32,152,{iid[s]},{c:.9f},{c:.9f},{c:.9f},{c:.9f},0,{s}"
                                       for ts, s, c in rows] + list(extra)
    p = Path(folder) / f"DBIX_ohlcv-1s_{day}.csv.gz"
    p.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode(), mtime=0))
    return p


def readme(paths, extra_names=()):
    lines = ["# dbix/ - synthetic", "", "## Seal (sha256)"]
    lines += [f"    {hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in paths]
    lines += [f"    {'0' * 64}  {n}" for n in extra_names]
    return "\n".join(lines + ["", "## Afterwards", "    " + "f" * 64 + "  not-a-seal-line.csv.gz"]) + "\n"


def every_15s(day_utc_open, until, value):
    """Prints every 15 s from an opening UTC time to `until`, the value a function of the step."""
    out, ts, k = [], day_utc_open, 0
    while ts <= until:
        out.append((ts, value(k)))
        ts += timedelta(seconds=15)
        k += 1
    return out


tmp = Path(tempfile.mkdtemp())
# 3 Nov 2026 is EST (UTC-5): 09:31 New York = 14:31 UTC, 14:30 New York = 19:30 UTC.
OPEN_EST = datetime(2026, 11, 3, 14, 31, tzinfo=UTC)
ovx = every_15s(OPEN_EST, datetime(2026, 11, 3, 21, 2, tzinfo=UTC), lambda k: 60.0 + 0.01 * k)
gvz = every_15s(OPEN_EST, datetime(2026, 11, 3, 21, 2, tzinfo=UTC), lambda k: 25.0 - 0.001 * k)
vix_garbage = [f"{stamp(OPEN_EST)},32,152,1003,x,x,x,x,0,VIX", f"{stamp(OPEN_EST)},99,152,1004,?,?,?,?,0,VXAPL"]
f1 = write_day(tmp, "2026-11-03", {"OVX": ovx, "GVZ": gvz}, vix_garbage)

print("=== the seal ===")
sealed = it.seal(readme([f1], ["samples/sample_OVX_ohlcv-1d.csv.gz"]))
check("the seal block is read: the day file and a samples/ entry, nothing after the next heading",
      set(sealed) == {f1.name, "samples/sample_OVX_ohlcv-1d.csv.gz"})
check("a README with no seal block reads nothing", "no seal block" in (raises(it.seal, "# dbix\n") or ""))
check("a file whose bytes match its sealed hash is read", it.sealed_bytes(f1, sealed) == f1.read_bytes())
bad = Path(tmp) / "tampered"
bad.mkdir()
fb = write_day(bad, "2026-11-03", {"OVX": ovx[:-1], "GVZ": gvz})
check("a file changed since the seal is refused before anything is parsed",
      "does not match its sealed sha256" in (raises(it.bars, fb, sealed) or ""))
f_new = write_day(bad, "2026-11-04", {"OVX": ovx})
check("a file the seal does not list is refused", "not in the seal" in (raises(it.bars, f_new, sealed) or ""))

print("\n=== the files, in DBIX's recorded layout ===")
check("the reader expects exactly the header typed here from Databento's documentation",
      it.COLUMNS == tuple(DBIX_HEADER.split(",")))
b = it.bars(f1, sealed)
check("only OVX and GVZ are kept", set(b) == {"OVX", "GVZ"} and len(b["OVX"]) == len(ovx))
check("the other indices' rows are skipped before any field is converted (a VIX close of 'x', a VXAPL rtype 99)",
      raises(it.bars, f1, sealed) is None)
check("timestamps are parsed as UTC instants (09:31 New York on 3 Nov = 14:31 UTC)", b["OVX"][0][0] == OPEN_EST)
check("values come through unchanged, in time order", b["OVX"][3][1] == 60.03 and b["OVX"] == sorted(b["OVX"]))
wrong = Path(tmp) / "wrongcols"
wrong.mkdir()
pw = wrong / "DBIX_ohlcv-1s_2026-11-03.csv.gz"
pw.write_bytes(gzip.compress(b"ts_event,rtype,publisher_id,instrument_id,open,high,low,volume,symbol\n", mtime=0))
check("a file without DBIX's recorded columns is refused",
      "not DBIX's recorded" in (raises(it.bars, pw, it.seal(readme([pw]))) or ""))
pr = write_day(Path(tmp) / "wrongcols", "2026-11-02", {}, [f"{stamp(OPEN_EST)},33,152,1001,60,60,60,60,0,OVX"])
check("an OVX record that is not a one-second bar (rtype 33, one-minute) is refused",
      "not a one-second bar" in (raises(it.bars, pr, it.seal(readme([pr]))) or ""))

print("\n=== the index at the snapshot minute: ts_event + 1 s <= T ===")
T = datetime(2026, 11, 3, 19, 30, tzinfo=UTC)                     # 14:30 New York, EST
ser = [(T - 16 * S, 10.0), (T - S, 11.0), (T, 12.0), (T + 14 * S, 13.0)]
check("a bar stamped T - 1 s ends exactly at T and is used", it.index_at(ser, T) == (11.0, None))
check("the bar stamped T itself ends at T + 1 s and is never used", it.index_at([(T - 16 * S, 10.0), (T, 12.0)], T)
      == (10.0, None))
check("a bar 60 s old is used", it.index_at([(T - 60 * S, 9.0)], T) == (9.0, None))
check("a bar 61 s old is not: the day is not measured, never filled",
      it.index_at([(T - 61 * S, 9.0)], T) == (None, "the last bar is more than 60 s old"))
check("no bar before T: not measured", it.index_at([(T, 12.0)], T)[0] is None)
prev = [(datetime(2026, 11, 2, 20, 59, 59, tzinfo=UTC), 8.0)]
check("a value from the previous trading day is not used", it.index_at(prev, datetime(2026, 11, 3, 14, 31, 30, tzinfo=UTC))
      == (None, "the last bar is from another day"))
T_edt = datetime(2026, 10, 21, 14, 0, 30, tzinfo=UTC)              # 10:00:30 New York on 21 Oct (EDT, UTC-4)
check("21 Oct (EDT): a bar at 14:00 UTC is 10:00 New York, inside the session",
      it.index_at([(datetime(2026, 10, 21, 14, 0, tzinfo=UTC), 7.0)], T_edt) == (7.0, None))
T_est = datetime(2026, 11, 3, 14, 0, 30, tzinfo=UTC)               # 09:00:30 New York on 3 Nov (EST)
check("3 Nov (EST): the same UTC time is 09:00 New York, before 09:31, so not used",
      it.index_at([(datetime(2026, 11, 3, 14, 0, tzinfo=UTC), 7.0)], T_est)
      == (None, "the last bar is before 09:31 New York"))
check("on the synthetic day, I(14:30 New York) is the 14:29:45 print, not the one stamped 14:30:00",
      it.index_at(b["OVX"], T) == ([c for ts, c in b["OVX"] if ts == T - 15 * S][0], None)
      and any(ts == T for ts, _ in b["OVX"]))

print("\n=== the sensitivity: nearest bar within 15 s either side ===")
check("a bar 5 s AFTER T beats one 10 s before (it may use a value printed after T)",
      it.index_near([(T - 10 * S, 1.0), (T + 5 * S, 2.0)], T) == 2.0)
check("a tie goes to the earlier bar", it.index_near([(T - 5 * S, 1.0), (T + 5 * S, 2.0)], T) == 1.0)
check("nothing within 15 s gives no value", it.index_near([(T - 16 * S, 1.0), (T + 16 * S, 2.0)], T) is None)

print("\n=== the close check ===")
check("the day's last print is found by its New York date", it.last_value(b["OVX"], "2026-11-03") == b["OVX"][-1][1])
check("0.05 from the close is not flagged (62.74 against 62.69)", not it.close_flag(62.74, 62.69))
check("0.06 is flagged, in either direction", it.close_flag(62.75, 62.69) and it.close_flag(62.63, 62.69))
check("no print that day: nothing to flag", not it.close_flag(None, 62.69))

print("\n=== the split: E - C = (E - I(T)) + (I(T) - C), exactly ===")
g, res, mv = it.split(1.0 + 60.0, 60.0, 61.5)
check("the plan's example: a residual of +1 and a move of -1.5 give a registered gap of -0.5",
      (res, mv) == (1.0, -1.5) and abs(g - (-0.5)) < 1e-12)
rng = random.Random(20261104)
trip = [(rng.uniform(20, 90), rng.uniform(20, 90), rng.uniform(20, 90)) for _ in range(200)]
check("200 random triples: the parts add up to the gap within 1e-12",
      max(abs(a - (b_ + c)) for a, b_, c in (it.split(*t) for t in trip)) < 1e-12)
rows = [{"E": 10 + k, "I": 10.0, "C": 10.0 - 2 * k} for k in (1, 2, 3)]   # residual 1,2,3; move 2,4,6
d = it.describe(rows)
check("signed means: E - C 6 = residual 2 + move 4", (d["mean"]["E - C"], d["mean"]["E - I(T)"], d["mean"]["I(T) - C"])
      == (6.0, 2.0, 4.0) and d["sum_check"] < 1e-12)
check("residual and move moving together: correlation +1", abs(d["corr"] - 1.0) < 1e-12)
d2 = it.describe([{"E": 10 + k, "I": 10.0, "C": 10.0 + 2 * k - 8} for k in (1, 2, 3)])
check("moving against each other: correlation -1 (offsetting)", abs(d2["corr"] + 1.0) < 1e-12)
d3 = it.describe([{"E": 11.0, "I": 10.0, "C": 10.0}, {"E": 9.0, "I": 10.0, "C": 10.0}])
check("mean absolute values are taken part by part (residuals +1 and -1: mean 0, mean absolute 1)",
      d3["mean"]["E - I(T)"] == 0.0 and d3["mean_abs"]["E - I(T)"] == 1.0 and d2["mean_abs"]["I(T) - C"] == 4.0)
check("persistence uses H8's AR(1) and n_eff (T, rho, n_eff)", d["persistence"]["E - C"][0] == 3)

print("\n=== measure: covered, measured and not measured days ===")
days = {"2026-11-03": b}
readings = [
    {"day": "2026-11-03", "reading": "H5e skip-only", "index": "OVX", "E": 61.0, "C": 61.2, "T": T,
     "offsets": [-30.0, 10.0, 50.0]},
    {"day": "2026-11-03", "reading": "H7 OPRA replica", "index": "GVZ", "E": 24.0,
     "C": 24.9, "T": datetime(2026, 11, 3, 14, 31, tzinfo=UTC), "offsets": []},
    {"day": "2026-10-20", "reading": "H5e skip-only", "index": "OVX", "E": 55.0, "C": 55.5, "T": T, "offsets": []},
]
m = it.measure(readings, days)
h5 = m[("H5e skip-only", "OVX")]
I_T = it.index_at(b["OVX"], T)[0]
check("a covered day is measured with I(T) from the sealed file", h5["rows"] == [{"day": "2026-11-03", "E": 61.0,
                                                                                   "I": I_T, "C": 61.2}])
check("a counted day before the data begins is listed as uncovered, not filled", h5["uncovered"]
      == [("2026-10-20", "before the data begins")])
check("a snapshot at 09:31:00 has no bar ended by then: not measured, with the reason",
      m[("H7 OPRA replica", "GVZ")]["missing"] == [("2026-11-03", "no bar had ended by the snapshot minute")])
check("the quote-time spread around T is kept per day, with its date (median, min, max)",
      h5["spread"] == [("2026-11-03", 10.0, -30.0, 50.0)])
rep = it.report(m, ["2026-11-03 OVX"])
check("the report prints aggregates and dates, never an index value",
      f"{I_T:.3f}" not in rep and "2026-11-03 OVX" in rep and it.CREDIT in rep and "not measured: 2026-11-03" in rep)
check("each day's quote-time spread is printed with its date, and no 'widest day' is pieced together from two days",
      "2026-11-03 +10 (-30 to +50)" in rep and "widest" not in rep
      and "1 counted days before the data begins (2026-10-20 to 2026-10-20)" in rep)
days2 = {"2026-10-21": b, "2026-10-23": b}
rd2 = [dict(readings[0], day=dd) for dd in ("2026-11-04", "2026-10-22", "2026-10-20")]
m2 = it.measure(rd2, days2)
check("an uncovered day says where it sits: after the data, a day with no file inside it, before it",
      m2[("H5e skip-only", "OVX")]["uncovered"] == [("2026-11-04", "after the data ends"),
                                                    ("2026-10-22", "no file for that day"),
                                                    ("2026-10-20", "before the data begins")])
rep2 = it.report(m2, [])
check("the report names each uncovered day that is not simply before the data, with where it sits",
      "not covered: 2026-11-04 (after the data ends)" in rep2 and "not covered: 2026-10-22 (no file for that day)"
      in rep2 and "1 counted days before the data begins (2026-10-20 to 2026-10-20)" in rep2)
m3 = it.measure([dict(readings[0], index="GVZ")], {"2026-11-03": {"OVX": b["OVX"], "GVZ": []}})
check("a day whose file has no bar for the index is not measured, with that reason",
      m3[("H5e skip-only", "GVZ")]["missing"] == [("2026-11-03", "the day's file has no GVZ bar")])

print("\n=== every day file the seal lists, and no other ===")
fold = Path(tmp) / "folder"
fold.mkdir()
fa, fz = write_day(fold, "2026-10-21", {"OVX": ovx}), write_day(fold, "2026-10-22", {"OVX": ovx})
s2 = it.seal(readme([fa, fz], ["samples/sample_OVX_ohlcv-1d.csv.gz"]))
check("the day files are found by the seal's own names (a samples/ entry is not a day file)",
      it.day_files(fold, s2) == {"2026-10-21": fa, "2026-10-22": fz})
fz.unlink()
check("a day file the seal lists but the folder lacks is refused, never read as a day the data does not cover",
      "listed in the seal but not on disk: DBIX_ohlcv-1s_2026-10-22.csv.gz" in (raises(it.day_files, fold, s2) or ""))
write_day(fold, "2026-10-22", {"OVX": ovx})
write_day(fold, "2026-10-23", {"OVX": ovx})
check("a day file on disk that the seal does not list is refused",
      "not in the seal: DBIX_ohlcv-1s_2026-10-23.csv.gz" in (raises(it.day_files, fold, s2) or ""))
check("a seal that lists no day file reads nothing",
      "no one-second day file" in (raises(it.day_files, fold, it.seal(readme([], ["samples/x.csv.gz"]))) or ""))

print("\n=== H5e's days must be modelfree's own ===")
block = ("risk-free (DGS1MO): 3.910%\n\n-- H5e: USO, wide strikes, zero bids SKIPPED, against OVX (registered 23 Sep; "
         "judged from 2026-09-23)\n   date            OVX  registered     gap  wide skip     gap  counted\n"
         "   2026-11-02    62.69       60.10   -2.59      61.00   -1.69  yes\n"
         "   2026-11-03    61.20       60.70   -0.50      61.00   -0.20  yes\n")
mine = [{"day": "2026-11-02", "reading": "H5e registered", "E": 60.10, "C": 62.69},
        {"day": "2026-11-02", "reading": "H5e skip-only", "E": 61.00, "C": 62.69},
        {"day": "2026-11-03", "reading": "H5e registered", "E": 60.70, "C": 61.20},
        {"day": "2026-11-03", "reading": "H5e skip-only", "E": 61.00, "C": 61.20}]
check("the same days and gaps agree", it.h5e_cross_check(mine, block) == [])
off = [dict(x, E=x["E"] + (0.02 if x["day"] == "2026-11-03" and "skip" in x["reading"] else 0)) for x in mine]
check("a gap 0.02 off is caught", it.h5e_cross_check(off, block) == ["2026-11-03: the gaps differ from modelfree's"])
check("a day only one side counts is caught", it.h5e_cross_check(mine[:2], block)
      == ["2026-11-03: counted by one and not the other"])
check("modelfree's output at a rate other than the frozen 3.910% is refused",
      it.h5e_cross_check(mine, block.replace("3.910%", "0.000%"))
      == ["modelfree's risk-free rate 0.000% is not the frozen 3.910%"])
head = block.split("   2026-11-02")[0]
check("two empty sides are not agreement", it.h5e_cross_check([], head)
      == ["neither side counts an H5e day: nothing to compare"])
check("modelfree counting no day while this side counts two is caught, day by day", it.h5e_cross_check(mine, head)
      == ["2026-11-02: counted by one and not the other", "2026-11-03: counted by one and not the other"])
check("output without modelfree's H5e block is a disagreement, not a crash",
      it.h5e_cross_check(mine, "risk-free (DGS1MO): 3.910%\n") == ["modelfree's output: no H5e block in modelfree output"])

print("\n=== the frozen rate, and a cache-only key ===")
import modelfree as _mf                            # noqa: E402
_rf0 = _mf.risk_free
try:
    _mf.risk_free = lambda: 0.0
    r0msg = raises(it.frozen_r)
    _mf.risk_free = lambda: 0.0391
    r_ok = it.frozen_r()
finally:
    _mf.risk_free = _rf0
check("r = 0 (a missing FRED cache) stops the reader before any reading is rebuilt",
      "risk-free rate 0.000% is not the frozen 3.910%" in (r0msg or ""))
check("the frozen 3.91% is accepted", r_ok == 0.0391)
os.environ["FRED_KEY"] = "a-real-looking-key"
_k = iu.module_from_spec(_s); _s.loader.exec_module(_k)
check("loading the reader sets the cache-only key even over a real one, so nothing can fetch today's rate",
      os.environ["FRED_KEY"] == "use-cache")

print("\n=== main, end to end on synthetic files with the reference run stubbed ===")
it_m = iu.module_from_spec(_s); _s.loader.exec_module(it_m)
mfold = Path(tmp) / "main"
mfold.mkdir()
f_m = write_day(mfold, "2026-11-03", {"OVX": ovx, "GVZ": gvz})
(mfold / "README.md").write_text(readme([f_m]))
it_m.DBIX_DIR, it_m.verdicts_recorded, it_m.h7_days = mfold, (lambda: True), (lambda: [])
it_m.h5e_days = lambda: [dict(x, index="OVX", T=T - (timedelta(days=1) if x["day"] == "2026-11-02" else timedelta(0)),
                              offsets=[-30.0, 10.0, 50.0]) for x in mine]


def run_main(ref):
    it_m.reference_output = lambda: ref
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return it_m.main([]), buf.getvalue()
    except SystemExit as e:
        return "refused", str(e)


c1, o1 = run_main((1, block, "Traceback (most recent call last):\nValueError: boom\n"))
check("a reference run that exits non-zero is refused, though its printed table matches",
      c1 == "refused" and "exited 1" in o1 and "ValueError: boom" in o1)
c2, o2 = run_main((0, block, ""))
check("the whole path runs: the covered day measured, the earlier counted day listed as before the data",
      c2 == 0 and "== H5e skip-only, against OVX: 1 of 1 covered days measured; 1 counted days before the data "
      "begins (2026-11-02 to 2026-11-02)" in o2 and "2026-11-03 +10 (-30 to +50)" in o2)
c3, o3 = run_main((0, block.replace("3.910%", "0.000%"), ""))
check("a reference run at another rate is refused", c3 == "refused" and "not the frozen 3.910%" in o3)

print("\n=== nothing is read before both verdicts are recorded ===")
it_guard = iu.module_from_spec(_s); _s.loader.exec_module(it_guard)
it_guard.verdicts_recorded = lambda: False
it_guard.DBIX_DIR = Path(tmp) / "absent"
try:
    it_guard.main([])
    msg = None
except BaseException as e:                         # a refusal is a SystemExit; anything else is a failure here
    msg = f"{type(e).__name__}: {e}"
check("main refuses while either verdict is missing, before it opens the folder",
      msg is not None and msg.startswith("SystemExit") and "sealed" in msg)
import record_verdict as _rv                       # noqa: E402
vt = Path(tmp) / "verdicts"
vt.mkdir()
_H5, _H7, gate = _rv.H5, _rv.H7, {}
try:
    _rv.H5, _rv.H7 = vt / "h5.md", vt / "h7.md"
    for name, a5, a7 in (("neither", "", ""), ("H5e only", _rv.MARK_H5E_FINAL, ""), ("H7 only", "", _rv.MARK_H7),
                         ("both", _rv.MARK_H5E_FINAL, _rv.MARK_H7)):
        _rv.H5.write_text(f"# H5\n\n{a5} (synthetic)\n")
        _rv.H7.write_text(f"# H7\n\n{a7} (synthetic)\n")
        gate[name] = it.verdicts_recorded()
finally:
    _rv.H5, _rv.H7 = _H5, _H7
check("the real gate, on the writer's own markers: shut with neither reading, with only H5e's FINAL and with only "
      "H7's; open with both", gate == {"neither": False, "H5e only": False, "H7 only": False, "both": True})

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
