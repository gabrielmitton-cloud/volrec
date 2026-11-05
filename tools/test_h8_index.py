"""Unit tests for H8's choice 6 reader (tools/h8_index.py). No network and no licensed data: every file here is
SYNTHETIC, written in DBIX's recorded layout as tools/test_index_timing.py writes it (Databento CSV, pretty
timestamps, symbols mapped, rtype 32 for one-second bars), with made-up values.
python tools/test_h8_index.py
"""
import contextlib
import gzip
import io
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
import h8_index as hi                              # noqa: E402
import index_timing as it                          # noqa: E402

fails = []
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
S = timedelta(seconds=1)
DBIX_HEADER = "ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol"
IID = {"OVX": 1001, "GVZ": 1002, "VIX": 1003, "VXAPL": 1004, "VXN": 1005, "RVX": 1006, "VXD": 1007}
D1, D2, D3 = "2026-12-01", "2026-12-02", "2026-12-03"
T1 = datetime(2026, 12, 1, 14, 42, tzinfo=NY).astimezone(UTC)      # a snapshot minute, as UTC like the code's
T2 = datetime(2026, 12, 2, 14, 42, tzinfo=NY).astimezone(UTC)


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def raises(fn, *a, **k):
    """The SystemExit message when fn refuses, else None."""
    try:
        fn(*a, **k)
    except SystemExit as e:
        return str(e)
    return None


def stamp(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S") + ".000000000Z"


def write_day(folder, day, prints, extra=()):
    """One gzipped ohlcv-1s file: prints = {symbol: [(utc time, close)]}, rows in time order across symbols."""
    rows = sorted((ts, s, c) for s, pts in prints.items() for ts, c in pts)
    lines = [DBIX_HEADER] + [f"{stamp(ts)},32,152,{IID[s]},{c:.9f},{c:.9f},{c:.9f},{c:.9f},0,{s}"
                             for ts, s, c in rows] + list(extra)
    p = Path(folder) / f"DBIX_ohlcv-1s_{day}.csv.gz"
    p.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode(), mtime=0))
    return p


def seal_folder(folder, paths):
    text = "# dbix-h8 (synthetic)\n\nBought during H8's window.\n\n## Seal (sha256)\n"
    for p in paths:
        text = hi.sealed_readme(text, p.name, p.read_bytes())
    (Path(folder) / "README.md").write_text(text)
    return text


def every_15s(T, values):
    """Prints every 15 s ending one second before T: values[-1] is the last bar whose second has ended by T."""
    n = len(values)
    return [(T - S - timedelta(seconds=15 * (n - 1 - i)), v) for i, v in enumerate(values)]


print("=== the pairs ===")
check("six pairs, each fund with the Cboe index on its own or its index's options",
      hi.PAIRS == {"USO": "OVX", "GLD": "GVZ", "AAPL": "VXAPL", "SPY": "VIX", "QQQ": "VXN", "IWM": "RVX"})
check("TSLA and NVDA have no index, so no pair", "TSLA" not in hi.PAIRS and "NVDA" not in hi.PAIRS)
check("the window is H8's: 1 Dec 2026 to 29 Jan 2027", hi.WINDOW == ("2026-12-01", "2027-01-29"))

print("\n=== the seal, written as files are bought and read back by the timing reader ===")
tmp = Path(tempfile.mkdtemp())
pa = write_day(tmp, D1, {"OVX": every_15s(T1, [30.0, 31.0])})
pb = write_day(tmp, D2, {"OVX": every_15s(T2, [32.0])})
text = seal_folder(tmp, [pa, pb])
got = it.seal(text)
check("index_timing.seal reads back every name the buyer sealed", set(got) == {pa.name, pb.name})
check("and each under its file's own sha256",
      got[pa.name] == __import__("hashlib").sha256(pa.read_bytes()).hexdigest())
check("a name already sealed is refused (never re-sealed under a new hash)",
      "already sealed" in (raises(hi.sealed_readme, text, pa.name, b"changed") or ""))
check("a README with no seal block seals nothing",
      "no seal block" in (raises(hi.sealed_readme, "# dbix-h8\n", pa.name, b"x") or ""))
check("a seal block followed by another section seals nothing (the reader would stop at that heading)",
      "not its last section" in (raises(hi.sealed_readme, text + "\n## Notes\n", "x.csv.gz", b"x") or ""))
check("an empty seal block takes its first line",
      hi.sealed_readme("## Seal (sha256)\n", pa.name, b"x").endswith(f"  {pa.name}\n"))
check("a name with a line break is refused", "not a file name" in (raises(hi.sealed_readme, text, "a\nb", b"x") or ""))

print("\n=== H8's own folder: six indices, sealed, never the timing plan's folder ===")
six = tempfile.mkdtemp()
p1 = write_day(six, D1, {"OVX": every_15s(T1, [30.0, 31.0]), "GVZ": every_15s(T1, [20.0]),
                         "VXAPL": every_15s(T1, [25.0]), "VIX": every_15s(T1, [17.0]), "VXN": every_15s(T1, [22.0]),
                         "RVX": every_15s(T1, [24.0])},
               extra=[f"{stamp(T1 - 5 * S)},32,152,1007,x,x,x,x,0,VXD"])
p2 = write_day(six, D2, {"OVX": every_15s(T2, [33.0]), "VIX": every_15s(T2, [18.0])})
seal_folder(six, [p1, p2])
days = hi.load_days(six)
check("both sealed days are read", set(days) == {D1, D2})
check("all six indices are kept", set(days[D1]) == set(hi.INDICES))
check("another index's row is skipped before any field is converted (a VXD close of 'x')",
      "VXD" not in days[D1])
check("the timing reader's own default still keeps OVX and GVZ only from the same file",
      set(it.bars(p1, it.seal((Path(six) / "README.md").read_text()))) == {"OVX", "GVZ"})
_was = it.DBIX_DIR
it.DBIX_DIR = Path(six)
check("the timing plan's sealed folder is refused before anything in it is opened",
      "timing plan's sealed folder" in (raises(hi.load_days, six) or ""))
it.DBIX_DIR = Path(tempfile.mkdtemp()) / "no-readme-here"
check("... even when that folder has no README to open", "timing plan's sealed folder" in
      (raises(hi.load_days, it.DBIX_DIR) or ""))
it.DBIX_DIR = _was
bad = Path(tempfile.mkdtemp())
q1 = write_day(bad, D1, {"OVX": every_15s(T1, [30.0])})
seal_folder(bad, [q1])
write_day(bad, D1, {"OVX": every_15s(T1, [99.0])})          # changed after it was sealed
check("a file changed after it was sealed is not read", "does not match its sealed sha256" in
      (raises(hi.load_days, bad) or ""))
gone = Path(tempfile.mkdtemp())
seal_folder(gone, [write_day(gone, D1, {"OVX": every_15s(T1, [30.0])})])
(gone / f"DBIX_ohlcv-1s_{D1}.csv.gz").unlink()
check("a sealed day file missing from disk stops the reading", "not on disk" in (raises(hi.load_days, gone) or ""))
extra = Path(tempfile.mkdtemp())
seal_folder(extra, [write_day(extra, D1, {"OVX": every_15s(T1, [30.0])})])
write_day(extra, D2, {"OVX": every_15s(T2, [30.0])})
check("a day file on disk but not in the seal stops the reading", "not in the seal" in
      (raises(hi.load_days, extra) or ""))

print("\n=== the reading: I(T), the same days for both feeds, nothing filled ===")
# the index at T: 21.0 printed at T - 1 s (its second has ended by T), 99.0 printed AT T (it has not)
idx = {D1: {"OVX": [(T1 - 16 * S, 20.0), (T1 - S, 21.0), (T1, 99.0)], "VIX": [(T1 - S, 17.0)],
            "GVZ": [(T1 - 61 * S, 19.0)]},
       D2: {"OVX": [(T2 - S, 22.0)], "VIX": [(T2 - S, 18.0)]},
       "2026-11-30": {"OVX": [(T1 - timedelta(days=1), 25.0)]}}


def rd(day, fund, T, free, opra):
    return {"day": day, "fund": fund, "index": hi.PAIRS[fund], "T": T, "free": free, "opra": opra}


g = hi.measure([rd(D1, "USO", T1, 23.0, 22.5), rd(D2, "USO", T2, 21.0, 22.5)], idx)
check(f"I(T) is the bar whose second has ended by T, never the one printed at T ({g['USO']['rows'][:1]})",
      g["USO"]["rows"][0] == (2.0, 1.5))
check("each day gives free - I and OPRA - I", g["USO"]["rows"] == [(2.0, 1.5), (-1.0, 0.5)])
s = hi.summary(g["USO"])
check(f"known answer: free mean +0.5, mean |.| 1.5; OPRA mean +1.0, mean |.| 1.0 ({s})",
      s["n"] == 2 and s["free"] == (0.5, 1.5) and s["opra"] == (1.0, 1.0))
g = hi.measure([rd(D1, "GLD", T1, 20.0, 20.0)], idx)
check("an index value more than 60 s old is not used: the day is not measured, once, with its reason",
      not g["GLD"]["rows"] and (D1, "the last bar is more than 60 s old") in g["GLD"]["missing"]
      and [d for d, _ in g["GLD"]["missing"]].count(D1) == 1)
g = hi.measure([rd(D1, "QQQ", T1, 22.0, 22.0)], idx)
check("a day file without the fund's index lists the day as not measured",
      g["QQQ"]["missing"][0] == (D1, "the day's file has no VXN bar") and not g["QQQ"]["rows"])
g = hi.measure([rd(D1, "SPY", T1, None, 17.5), rd(D2, "SPY", T2, 18.2, None)], idx)
check("a day with only the OPRA estimate is not measured: both feeds cover the same days",
      (D1, "no free estimate at the snapshot minute") in g["SPY"]["missing"] and not g["SPY"]["rows"])
check("a day with only the free estimate is not measured either",
      (D2, "no OPRA estimate at the snapshot minute") in g["SPY"]["missing"])
g = hi.measure([rd(D1, "SPY", None, None, None)], idx)
check("a day with neither estimate (no snapshot minute) is listed once, not filled",
      (D1, "neither feed has an estimate at the snapshot minute") in g["SPY"]["missing"] and not g["SPY"]["rows"]
      and [d for d, _ in g["SPY"]["missing"]].count(D1) == 1)
g = hi.measure([rd(D3, "USO", T1, 20.0, 20.0)], idx)
check("a window day with no index file is listed as not covered", g["USO"]["uncovered"] == [D3])
g = hi.measure([rd("2026-11-30", "USO", T1 - timedelta(days=1), 20.0, 20.0)], idx)
check("a fund-day before the window is left out entirely",
      not g["USO"]["rows"] and not g["USO"]["uncovered"] and all(d != "2026-11-30" for d, _ in g["USO"]["missing"]))
check("an index file before the window lists no day as not measured",
      all(d != "2026-11-30" for x in g.values() for d, _ in x["missing"]))
g = hi.measure([rd(D1, "USO", T1, 23.0, 22.5)], idx)
check("a window day with an index file but no fund-day from H8 is listed for each fund that lacks it",
      (D2, "no fund-day from H8's files") in g["USO"]["missing"]
      and all((D1, "no fund-day from H8's files") in g[f]["missing"] for f in ("GLD", "AAPL", "SPY", "QQQ", "IWM")))
check("a fund with no measured day says so rather than printing nan",
      "AAPL / VXAPL   0 days   no measured day" in hi.report(g))

print("\n=== every window trading day once per fund; finite values only (Astra, 5 Nov) ===")
check("the window's trading days come from the project's one calendar: 41 (22 in December, 19 in January)",
      len(hi.window_days()) == 41 and sum(d < "2027" for d in hi.window_days()) == 22
      and not {"2026-12-25", "2027-01-01", "2027-01-18"} & set(hi.window_days()))
g = hi.measure([rd(D1, "USO", T1, 23.0, 22.5), rd(D3, "USO", T1, 20.0, 20.0)], idx, calendar=[D1, D2, D3])
check("a trading day with neither a fund-day nor an index file is listed, not lost",
      (D3, "neither a fund-day from H8's files nor an index file") in g["GLD"]["missing"])
check("each expected day is in exactly one place for every fund (measured, not measured, or not covered)",
      all(len(x["rows"]) + len(x["missing"]) + len(x["uncovered"]) == 3 for x in g.values())
      and all(sorted([d for d, _ in x["missing"]] + x["uncovered"]) == sorted(set([d for d, _ in x["missing"]] + x["uncovered"]))
              for x in g.values()))
g = hi.measure([], idx)
check("with no fund-day at all, every fund lists all 41 window trading days, each once",
      all(len(x["missing"]) == 41 and len({d for d, _ in x["missing"]}) == 41 for x in g.values()))
g = hi.measure([rd(D1, "USO", T1, float("nan"), 22.5), rd(D2, "USO", T2, 21.0, float("inf"))], idx, calendar=[D1, D2])
check("an estimate that is not a finite number leaves the day not measured",
      not g["USO"]["rows"] and [w for _, w in g["USO"]["missing"]].count("an estimate is not a finite number") == 2)
nan_idx = {D1: {"OVX": [(T1 - 16 * S, 20.0), (T1 - S, float("nan"))]}}
g = hi.measure([rd(D1, "USO", T1, 23.0, 22.5)], nan_idx, calendar=[D1])
check("an index close at T that is not a finite number: not measured, and the earlier bar never stands in",
      not g["USO"]["rows"] and g["USO"]["missing"] == [(D1, "the last bar's close is not a finite number")])
nanf = Path(tempfile.mkdtemp())
seal_folder(nanf, [write_day(nanf, D1, {"OVX": [(T1 - S, float("nan"))]})])
g = hi.measure([rd(D1, "USO", T1, 23.0, 22.5)], hi.load_days(nanf), calendar=[D1])
check("... including a 'nan' close read from a sealed file",
      g["USO"]["missing"] == [(D1, "the last bar's close is not a finite number")])

print("\n=== H8's own fund-days, the gate and the printout ===")
calls = []
_fd, _rf = hi.h8q.fund_days, hi.modelfree.risk_free
hi.h8q.fund_days = lambda sym, r: (calls.append((sym, r)) or
                                   ([(D1, {"T": T1, "S0s": 23.0, "S1s": 22.5}), (D2, {"T": T2, "S0s": 21.0, "S1s": 22.5})]
                                    if sym == "USO" else
                                    [(D1, {"T": T1, "S0s": 17.25, "S1s": 17.5})] if sym == "SPY" else []))
hi.modelfree.risk_free = lambda: 0.0391
x = hi.readings(0.0391)
check("readings asks h8_quotes.fund_days for each of the six funds, at the rate it is given",
      calls == [(f, 0.0391) for f in hi.PAIRS])
check("and carries each fund-day's snapshot minute and both estimates",
      x[0] == {"day": D1, "fund": "USO", "index": "OVX", "T": T1, "free": 23.0, "opra": 22.5} and len(x) == 3)
_dir = hi.H8_DIR
hi.H8_DIR = Path(tempfile.mkdtemp()) / "not-there"
check("before the window closes, nothing is read (the folder is never opened)",
      "nothing was read" in (raises(hi.main, today=date(2027, 1, 29)) or ""))
hi.H8_DIR = Path(six)
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = hi.main(today=date(2027, 1, 30))
txt = out.getvalue()
hi.H8_DIR, hi.h8q.fund_days, hi.modelfree.risk_free = _dir, _fd, _rf
check("after the window, the reading runs", code == 0 and "DESCRIPTIVE" in txt and "never part of H8's verdict" in txt)
# the folder's OVX at T is 31.0 (1 Dec) and 33.0 (2 Dec); its VIX 17.0 (1 Dec): hand-computed below
check("each fund's line shows both feeds side by side (USO: 23.0, 21.0 free and 22.5, 22.5 OPRA against 31.0, 33.0)",
      "USO  / OVX     2 days   free - index: mean -10.000, mean |.| 10.000   OPRA - index: mean -9.500, mean |.| 9.500"
      in txt)
check("SPY against VIX at T: free 17.25 and OPRA 17.5 against 17.0 on its one day",
      "SPY  / VIX     1 days   free - index: mean +0.250, mean |.| 0.250   OPRA - index: mean +0.500, mean |.| 0.500"
      in txt)
check("no index value and no estimate is printed",
      not any(v in txt for v in ("31.0", "33.0", "17.25", "22.5", "23.0", "21.0", "18.0", "17.0")))
check("the credit line is printed", hi.CREDIT in txt and "Aggregates only." in txt)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
