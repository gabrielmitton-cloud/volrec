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
from datetime import date, datetime, timedelta, timezone
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
check("a last eligible close that is not a finite number is not measured, and no earlier bar stands in (5 Nov)",
      it.index_at([(T - 16 * S, 10.0), (T - S, float("nan"))], T) == (None, "the last bar's close is not a finite number")
      and it.index_at([(T - S, float("inf"))], T)[0] is None)
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
nan5 = [dict(x, C=float("nan")) if x["day"] == "2026-11-03" else x for x in mine]
check("a close here that is not a finite number is a disagreement, never a silent pass (Astra, 6 Nov)",
      it.h5e_cross_check(nan5, block) == ["2026-11-03: a gap here is not a finite number"])

print("\n=== H5e's days must be its recorded FINAL reading's (a close revised since the verdict) ===")
import record_verdict as _rv                       # noqa: E402
rows5, rf5, na5 = _rv.parse_h5e(block)
sc5 = _rv.h5e_score(rows5, last=_rv.H5E_END)
first5 = _rv.block_h5e(dict(sc5, days=[("2026-09-23", 60.0, -1.0, 1.31, True)]), rf5, [], date(2026, 10, 7), False)
final5 = _rv.block_h5e(sc5, rf5, na5, date(2026, 11, 12), True, "FAILS")
h5txt = f"# H5\n\n## Result\n\n{first5}\n\n{final5}\n"
check("the writer's own FINAL block agrees with the same days and gaps; the FIRST verdict's gap line above it is "
      "not read", "2026-09-23 +1.31" in h5txt and it.h5e_recorded_check(mine, h5txt) == [])
moved = [dict(x, C=x["C"] - 0.02) if x["day"] == "2026-11-03" else x for x in mine]
check("a close revised by 0.02 since the verdict is caught, though modelfree's live run would agree",
      it.h5e_recorded_check(moved, h5txt) == ["2026-11-03: the skip-only gap differs from the recorded one"])
nudged = [dict(x, E=x["E"] + 0.004) if x["day"] == "2026-11-03" else x for x in mine]
check("a difference inside the printed two decimals is not a disagreement", it.h5e_recorded_check(nudged, h5txt) == [])
check("a day only one side counts is caught", it.h5e_recorded_check(mine[:2], h5txt)
      == ["2026-11-03: counted by one and not the other"])
check("a gap here that is not a finite number is a disagreement, never a silent pass",
      it.h5e_recorded_check(nan5, h5txt) == ["2026-11-03: the skip-only gap here is not a finite number"])
check("no FINAL reading in the file: nothing to compare (the FIRST verdict is not taken instead)",
      it.h5e_recorded_check(mine, f"# H5\n\n## Result\n\n{first5}\n") == ["no recorded H5e FINAL reading to compare"])
check("a FINAL reading without its gap-by-day line is a disagreement, not a crash",
      it.h5e_recorded_check(mine, h5txt.replace("- Skip-only gap by day: 2026-11-02", "- 2026-11-02"))
      == ["the recorded H5e FINAL reading lacks its gap-by-day line"])
empty5 = _rv.block_h5e(dict(sc5, days=[]), rf5, na5, date(2026, 11, 12), True)
check("two empty sides are not agreement", it.h5e_recorded_check([], f"# H5\n\n## Result\n\n{empty5}\n")
      == ["neither side counts an H5e day: nothing to compare"])

print("\n=== H7's days must give every number the recorded H7 reading prints (an absent OPRA folder) ===")


def h7_pair(day, index, free, opra, close):
    """The two readings h7_days builds for one fund-day: the OPRA and free-feed replicas against one close."""
    base = {"day": day, "index": index, "C": close, "T": T, "offsets": [-20.0, 0.0, 20.0]}
    return [dict(base, reading="H7 OPRA replica", E=opra), dict(base, reading="H7 free-feed replica", E=free)]


H7_DAYS = _rv.expected_days(_rv.H7_START_DAY, _rv.H7_END_DAY)


def h7_record(v, counted):
    """The writer's own H7 block, naming every expected fund-day outside `counted` as not counted, as the real
    writer must (it refuses while any expected day has no row)."""
    nc = [f"{d} {s} (no OPRA reading)" for d in H7_DAYS for s in ("USO", "GLD") if (d, s) not in counted]
    return f"# H7\n\n## Result\n\n{_rv.block_h7(v, date(2026, 11, 12), (), nc)}\n"


# USO's free replica sits +0.30 over OVX every day and 0.10 from OPRA on 13 Oct, which is the mean, so dropping
# 13 Oct leaves every mean as it was: only the days can see it.
DAYS3 = ("2026-10-13", "2026-10-14", "2026-11-03")
h7_in = (h7_pair("2026-10-13", "OVX", 61.00, 61.10, 60.70) + h7_pair("2026-10-13", "GVZ", 24.00, 24.30, 24.20)
         + h7_pair("2026-10-14", "OVX", 62.00, 61.80, 61.70) + h7_pair("2026-10-14", "GVZ", 25.00, 24.90, 25.10)
         + h7_pair("2026-11-03", "OVX", 60.50, 60.50, 60.20) + h7_pair("2026-11-03", "GVZ", 24.80, 24.60, 24.75))
# The recorded numbers, worked by hand: USO |free - OPRA| 0.10, 0.20, 0.00; GLD 0.30, 0.10, 0.20;
# GLD |free - GVZ| 0.20, 0.10, 0.05; USO free - OVX +0.30 each day.
v7 = {"USO_a": (3, 0.10), "GLD_a": (3, 0.20), "GLD_b": (3, 0.35 / 3), "USO_c": (3, 0.30)}
both3 = {(d, s) for d in DAYS3 for s in ("USO", "GLD")}
h7txt = h7_record(v7, both3)
check("the writer's own H7 block agrees with the same days and numbers, its 21 uncounted days a fund named",
      len(H7_DAYS) == 24 and it.h7_recorded_check(h7_in, h7txt) == [])
check("one USO day missing, every mean unchanged: caught by its date",
      it.h7_recorded_check([x for x in h7_in if (x["day"], x["index"]) != ("2026-10-13", "OVX")], h7txt)
      == ["USO: counted by one and not the other: 2026-10-13"])
check("a day counted here in place of a recorded one, the count and every mean unchanged: caught by the dates "
      "(Astra, 6 Nov)", it.h7_recorded_check([dict(x, day="2026-10-15") if (x["day"], x["index"])
                                              == ("2026-10-13", "OVX") else x for x in h7_in], h7txt)
      == ["USO: counted by one and not the other: 2026-10-13, 2026-10-15"])
check("a later note under H7's result is not read as the verdict's own list of days not counted",
      it.h7_recorded_check(h7_in, h7txt + "\n**A later note**\n\n- Also not counted, as an example: 2026-10-13 USO.\n")
      == [])
check("a record whose count disagrees with its own day lists (a drop list changed since the verdict): caught "
      "by the count", it.h7_recorded_check(h7_in, h7_record(dict(v7, USO_a=(4, 0.10), USO_c=(4, 0.30)), both3))
      == ["USO H7a: 3 days here, 4 in the recorded reading", "USO H7c: 3 days here, 4 in the recorded reading"])
check("no H7 day here while the record counts three a fund (an OPRA folder that is not the private one): caught",
      it.h7_recorded_check(mine, h7txt) == [f"{s}: counted by one and not the other: {', '.join(DAYS3)}"
                                            for s in ("USO", "GLD")])


def gld_opra_13oct(value):
    return [dict(x, E=value) if (x["day"], x["index"], x["reading"]) == ("2026-10-13", "GVZ", "H7 OPRA replica")
            else x for x in h7_in]


check("a GLD mean 0.003 off is caught", it.h7_recorded_check(gld_opra_13oct(24.309), h7txt)
      == ["GLD H7a: the mean |free - OPRA| differs from the recorded one"])
check("a difference inside the printed three decimals (0.0004) is not a disagreement",
      it.h7_recorded_check(gld_opra_13oct(24.3012), h7txt) == [])
check("a reading that is not a finite number is a disagreement, never a silent pass (Astra, 6 Nov)",
      it.h7_recorded_check(gld_opra_13oct(float("nan")), h7txt)
      == ["GLD H7a: the mean |free - OPRA| here is not a finite number"])
gvz7 = [dict(x, C=24.95) if (x["day"], x["index"]) == ("2026-11-03", "GVZ") else x for x in h7_in]
check("a GVZ close revised since the verdict is caught (H7b)", it.h7_recorded_check(gvz7, h7txt)
      == ["GLD H7b: the mean |free - GVZ| differs from the recorded one"])
ovx7 = [dict(x, C=61.50) if (x["day"], x["index"]) == ("2026-10-14", "OVX") else x for x in h7_in]
check("an OVX close revised since the verdict is caught (H7c)", it.h7_recorded_check(ovx7, h7txt)
      == ["USO H7c: the mean free - OVX differs from the recorded one"])
check("no recorded H7 reading: nothing to compare", it.h7_recorded_check(h7_in, "# H7\n\n## Result\n")
      == ["no recorded H7 reading to compare"])
check("a recorded reading without its H7a line is a disagreement, not a crash",
      it.h7_recorded_check(h7_in, h7txt.replace("at the same minute", "at one minute"))
      == ["the recorded H7 reading lacks its H7a, H7b or H7c line"])
d12 = H7_DAYS[:12]
r12 = [y for k, dd in enumerate(d12) for y in h7_pair(dd, "OVX", 60 + 0.1 * k, 60.05 + 0.1 * k, 59.8 + 0.1 * k)
       + h7_pair(dd, "GVZ", 24 + 0.1 * k, 23.9 + 0.1 * k, 24.5 + 0.1 * k)]
v12 = {"USO_a": (12, 0.05), "GLD_a": (12, 0.10), "GLD_b": (12, 0.50), "USO_c": (12, 0.20)}
t12 = h7_record(v12, {(d, s) for d in d12 for s in ("USO", "GLD")})
check("the wording the writer uses at its minimum and above (H7a HOLDS, H7b FAILS here) is read the same way",
      "**H7a HOLDS:**" in t12 and "**H7b FAILS:**" in t12 and it.h7_recorded_check(r12, t12) == [])
v0 = {"USO_a": (0, None), "GLD_a": (0, None), "GLD_b": (0, None), "USO_c": (0, None)}
check("two empty sides are not agreement", it.h7_recorded_check([], h7_record(v0, set()))
      == ["neither side counts an H7 day: nothing to compare"])
vg = dict(v7, USO_a=(0, None), USO_c=(0, None))
vgtxt = h7_record(vg, {(d, "GLD") for d in DAYS3})
gld_only = [x for x in h7_in if x["index"] == "GVZ"]
check("a fund the record reads as n/a over 0 days, with none here, is no disagreement (and no crash)",
      it.h7_recorded_check(gld_only, vgtxt) == [])
# An accepted gap is a date one panel lost (panel_health.ACCEPTED_GAPS). H7 reads the monthly legs, so it can still
# count that date, and the writer's coverage check skips it either way: its date proves nothing, but the counts and
# means still cover it (Astra's follow-up, 6 Nov). 14 Oct is counted on both sides here.
_gap = date(2026, 10, 14)
_rv._ph.ACCEPTED_GAPS[_gap] = "test only: the ATM panel lost the day; the monthly legs were recorded"
try:
    check("a day both sides count, on a date accepted as a gap (before the verdict or after it), agrees",
          it.h7_recorded_check(h7_in, h7txt) == [])
    check("an accepted-gap day the record counts and this side does not is still caught, by the count",
          it.h7_recorded_check([x for x in h7_in if (x["day"], x["index"]) != ("2026-10-14", "OVX")], h7txt)
          == ["USO H7a: 2 days here, 3 in the recorded reading", "USO H7c: 2 days here, 3 in the recorded reading"])
    lost = [f"{d} {s} (no OPRA reading)" for d in H7_DAYS for s in ("USO", "GLD") if d not in DAYS3]
    v2 = {"USO_a": (2, 0.05), "GLD_a": (2, 0.25), "GLD_b": (2, 0.125), "USO_c": (2, 0.30)}
    check("an accepted-gap day this side counts and the record never printed is still caught, by the count",
          it.h7_recorded_check(h7_in, f"# H7\n\n## Result\n\n{_rv.block_h7(v2, date(2026, 11, 12), (), lost)}\n")
          == [f"{s} H7{p}: 3 days here, 2 in the recorded reading" for s, p in (("USO", "a"), ("GLD", "a"),
                                                                               ("GLD", "b"), ("USO", "c"))])
finally:
    del _rv._ph.ACCEPTED_GAPS[_gap]

print("\n=== every reading the report must show, even with no day (Astra, 6 Nov) ===")
check("the six (reading, index) pairs are kept with no reading at all, so none can vanish from the report",
      len(it.GROUPS) == 6 and set(it.measure([], {}, it.GROUPS)) == set(it.GROUPS))
check("a reading with no counted day says so in the report",
      "== H7 OPRA replica, against OVX: no counted day to measure" in it.report(it.measure([], {}, it.GROUPS), []))

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
it_m.DBIX_DIR, it_m.verdicts_recorded, it_m.h7_days = mfold, (lambda: True), (lambda: h7_in)
it_m.h5e_days = lambda: [dict(x, index="OVX", T=T - (timedelta(days=1) if x["day"] == "2026-11-02" else timedelta(0)),
                              offsets=[-30.0, 10.0, 50.0]) for x in mine]
it_m.recorded = lambda: (h5txt, h7txt)


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
      "begins (2026-11-02 to 2026-11-02)" in o2 and "2026-11-03 +10 (-30 to +50)" in o2
      and "== H7 OPRA replica, against GVZ: 1 of 1 covered days measured; 2 counted days before the data begins "
      "(2026-10-13 to 2026-10-14)" in o2)
c3, o3 = run_main((0, block.replace("3.910%", "0.000%"), ""))
check("a reference run at another rate is refused", c3 == "refused" and "not the frozen 3.910%" in o3)
it_m.h7_days = lambda: []
c4, o4 = run_main((0, block, ""))
check("no H7 day here while the record counts some (an absent or wrong OPRA folder) is refused, naming the setting",
      c4 == "refused" and "H7's days here do not match its recorded reading" in o4 and "VOLREC_DATABENTO_DIR" in o4)
it_m.h7_days = lambda: h7_in
it_m.recorded = lambda: (h5txt.replace("2026-11-03 -0.20", "2026-11-03 -0.18"), h7txt)
c5, o5 = run_main((0, block, ""))
check("a close revised since the FINAL reading is refused, though modelfree's live run agrees",
      c5 == "refused" and "H5e's days here do not match its recorded FINAL reading" in o5)
it_m.h7_days, it_m.recorded = (lambda: gld_only), (lambda: (h5txt, vgtxt))
c6, o6 = run_main((0, block, ""))
check("a fund whose record holds no counted day still gets its lines in the report, saying so",
      c6 == 0 and "== H7 OPRA replica, against OVX: no counted day to measure" in o6
      and "== H7 free-feed replica, against OVX: no counted day to measure" in o6)
it_m.h7_days, it_m.recorded = (lambda: h7_in), (lambda: (h5txt, h7txt))

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
    both_text = it.recorded()
finally:
    _rv.H5, _rv.H7 = _H5, _H7
check("the real gate, on the writer's own markers: shut with neither reading, with only H5e's FINAL and with only "
      "H7's; open with both", gate == {"neither": False, "H5e only": False, "H7 only": False, "both": True})
check("the records the days are checked against are the writer's own two files, H5's and H7's",
      both_text == (f"# H5\n\n{_rv.MARK_H5E_FINAL} (synthetic)\n", f"# H7\n\n{_rv.MARK_H7} (synthetic)\n"))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
