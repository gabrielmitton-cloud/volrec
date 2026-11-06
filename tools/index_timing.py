#!/usr/bin/env python3
"""The index-timing measurement: EXPLORATORY and descriptive - no test, no bar, no verdict.

Plan: docs/drafts/2026-11-04-index-timing-plan.md, written before any value of the data was opened, to be
registered (descriptive) about 10 Nov 2026, before either verdict. This reader was built 4 Nov 2026 and is
tested only on SYNTHETIC files in DBIX's recorded layout (tools/test_index_timing.py). It opens the sealed
files only once H5e's FINAL reading and H7's reading are both recorded in their hypothesis files.

Each registered gap splits exactly, with no order of steps:
    E - C = (E - I(T)) + (I(T) - C)
  E     a registered estimate: H5e's skip-only estimate of OVX from USO (the registered estimate beside
        it), and H7's OPRA and free-feed replicas of OVX (USO) and GVZ (GLD);
  T     opra_reference.snapshot_minute of the rows that estimate used;
  I(T)  the close of the last one-second bar whose second has ended by T (ts_event + 1 s <= T; Databento
        stamps a bar with the inclusive start of its second), from T's New York trading day, at or after
        09:31 there, and at most 60 s old (T - ts_event <= 60 s); otherwise the day is not measured, never
        filled;
  C     Cboe's published close, as the registered readings read it (analyze.fetch_market_vol).
Sensitivity, labelled as able to use a value printed after T: the bar nearest T within 15 s either side.
A day whose last DBIX value is more than 0.05 from C is flagged and kept.

Reads OVX and GVZ only: every other index's row is skipped before any of its fields is converted. Every
file's sha256 must match the seal in the private dbix/README.md before the file is read, and every day file
the seal lists must be there. Nothing is measured unless the readings rebuilt here give the recorded
verdicts' own days and numbers (H5e's FINAL gap by day, H7's counts and means) and H5e's days match
modelfree's registered output. Prints aggregates only: dates (of days not covered, not measured or flagged)
and each day's spread of quote times around T in seconds, never an index value.

  VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra python tools/index_timing.py
      # refuses until both verdicts are recorded, and while H7's OPRA days are not the ones they used
"""
import csv
import gzip
import hashlib
import io
import math
import os
import re
import statistics as st
import sys
from datetime import time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ["FRED_KEY"] = "use-cache"              # cache only, even over a real key: never today's rate

import opra_reference as ore                       # noqa: E402

DBIX_DIR = Path(os.environ.get("VOLREC_DBIX_DIR") or Path.home() / "Documents" / "volrec-licensed" / "dbix")
INDICES = ("OVX", "GVZ")
# DBIX's recorded layout (structure read 4 Nov 2026, never a value): Databento CSV, pretty timestamps and
# prices, symbols mapped; ohlcv-1s records carry rtype 32.
COLUMNS = ("ts_event", "rtype", "publisher_id", "instrument_id", "open", "high", "low", "close", "volume", "symbol")
RTYPE_1S = "32"
NY = ZoneInfo("America/New_York")
FIRST_PRINT = time(9, 31)
ONE_SECOND = timedelta(seconds=1)
MAX_AGE = timedelta(seconds=60)
NEAR = timedelta(seconds=15)
CLOSE_CHECK = 0.05
BEFORE = "before the data begins"                 # where most uncovered days sit (pay-per-use starts 21 Oct)
H5E_THROUGH = "2026-11-11"                         # the FINAL reading's last day (record_verdict.H5E_END)
CREDIT = "Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only."


# ---------------- the seal and the files (tools/test_index_timing.py checks each) ----------------
def seal(readme):
    """{file name: sha256} from the README's "## Seal (sha256)" block: indented lines, hash, two spaces, name."""
    parts = readme.split("## Seal (sha256)", 1)
    if len(parts) < 2:
        raise SystemExit("README.md has no seal block: nothing is read")
    out = {}
    for ln in parts[1].splitlines():
        if ln.startswith("#"):
            break
        m = re.match(r"^\s+([0-9a-f]{64})  (\S.*)$", ln)
        if m:
            out[m.group(2).strip()] = m.group(1)
    if not out:
        raise SystemExit("README.md's seal block lists no file: nothing is read")
    return out


def sealed_bytes(path, sealed):
    """The file's bytes, only if their sha256 is the one sealed for its name."""
    path = Path(path)
    raw = path.read_bytes()
    want = sealed.get(path.name)
    if want is None:
        raise SystemExit(f"{path.name} is not in the seal: not read")
    if hashlib.sha256(raw).hexdigest() != want:
        raise SystemExit(f"{path.name} does not match its sealed sha256: not read")
    return raw


DAY_FILE = re.compile(r"^DBIX_ohlcv-1s_(\d{4}-\d{2}-\d{2})\.csv\.gz$")


def day_files(folder, sealed):
    """{day: path} for every one-second day file the seal lists. Refuses when one is not on disk (a lost file
    would otherwise read as a day the data does not cover) or when a day file on disk is not in the seal."""
    folder = Path(folder)
    want = {m.group(1): name for name in sealed if (m := DAY_FILE.match(name))}
    if not want:
        raise SystemExit("the seal lists no one-second day file: nothing is read")
    gone = sorted(name for name in want.values() if not (folder / name).is_file())
    if gone:
        raise SystemExit(f"listed in the seal but not on disk: {', '.join(gone)} - nothing is read")
    extra = sorted(p.name for p in folder.glob("DBIX_ohlcv-1s_*.csv.gz") if p.name not in sealed)
    if extra:
        raise SystemExit(f"not in the seal: {', '.join(extra)} - nothing is read")
    return {day: folder / name for day, name in sorted(want.items())}


def bars(path, sealed, indices=INDICES):
    """{index: [(ts_event, close)]} for OVX and GVZ, in time order, from one sealed ohlcv-1s file. Only
    tools/h8_index.py passes other `indices`, for H8's own files (never this plan's sealed folder)."""
    text = gzip.decompress(sealed_bytes(path, sealed)).decode()
    rd = csv.DictReader(io.StringIO(text))
    if tuple(rd.fieldnames or ()) != COLUMNS:
        raise SystemExit(f"{Path(path).name}: columns {rd.fieldnames}, not DBIX's recorded {list(COLUMNS)}")
    out = {s: [] for s in indices}
    for r in rd:
        if r["symbol"] not in out:                  # every other index: skipped before any field is read
            continue
        if r["rtype"] != RTYPE_1S:
            raise SystemExit(f"{Path(path).name}: a {r['symbol']} record of rtype {r['rtype']}, not a one-second bar")
        out[r["symbol"]].append((ore.parse_ts(r["ts_event"]), float(r["close"])))
    for s in out:
        out[s].sort()
    return out


# ---------------- the index at the snapshot minute ----------------
def index_at(series, T):
    """I(T) as (close, None), or (None, why) when the day is not measured."""
    last = None
    for ts, close in series:
        if ts + ONE_SECOND <= T:                    # the bar's second has ended by T
            last = (ts, close)
        else:
            break
    if last is None:
        return None, "no bar had ended by the snapshot minute"
    ts, close = last
    if ts.astimezone(NY).date() != T.astimezone(NY).date():
        return None, "the last bar is from another day"
    if ts.astimezone(NY).time() < FIRST_PRINT:
        return None, "the last bar is before 09:31 New York"
    if T - ts > MAX_AGE:
        return None, "the last bar is more than 60 s old"
    if not math.isfinite(close):                    # the last eligible bar, never an earlier one instead
        return None, "the last bar's close is not a finite number"
    return close, None


def index_near(series, T):
    """The sensitivity: the close of the bar nearest T within 15 s either side, which may have been printed
    after T; a tie goes to the earlier bar. None when no bar is that close."""
    best = None
    for ts, close in series:
        d = abs(ts - T)
        if d <= NEAR and (best is None or d < best[0]):
            best = (d, close)
    return best[1] if best else None


def last_value(series, day):
    """The day's last print (New York date), for the check against Cboe's close."""
    vals = [c for ts, c in series if ts.astimezone(NY).date().isoformat() == day]
    return vals[-1] if vals else None


def close_flag(last, C):
    """True when the day's last DBIX value is more than 0.05 from Cboe's close (in either direction)."""
    return last is not None and round(abs(last - C), 9) > CLOSE_CHECK


# ---------------- the split and its aggregates ----------------
def split(E, I, C):
    """(E - C, E - I, I - C): the registered gap, the contemporaneous residual and the index's move."""
    return E - C, E - I, I - C


def corr(x, y):
    """Pearson correlation; nan with fewer than three points or no spread."""
    if len(x) < 3:
        return float("nan")
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx, syy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def describe(rows):
    """rows: [{"E", "I", "C"}] on the measured days -> the plan's aggregates (signed means that add up,
    mean absolute values, the residual-move correlation, and each series' persistence)."""
    from h8_quotes import ar1, n_eff
    parts = list(zip(*(split(r["E"], r["I"], r["C"]) for r in rows))) if rows else [(), (), ()]
    names = ("E - C", "E - I(T)", "I(T) - C")
    out = {"n": len(rows), "mean": {}, "mean_abs": {}, "persistence": {}}
    for name, x in zip(names, parts):
        x = list(x)
        out["mean"][name] = st.mean(x) if x else float("nan")
        out["mean_abs"][name] = st.mean(abs(v) for v in x) if x else float("nan")
        rho = ar1(x)
        out["persistence"][name] = (len(x), rho, n_eff(len(x), rho))
    out["sum_check"] = abs(out["mean"]["E - C"] - out["mean"]["E - I(T)"] - out["mean"]["I(T) - C"]) if rows else 0.0
    out["corr"] = corr(list(parts[1]), list(parts[2]))
    return out


def offsets(rows, T):
    """Seconds between each quote's own time and the designated minute T."""
    return [(ore.parse_ts(r["quote_time"]) - T).total_seconds() for r in rows if r.get("quote_time")]


GROUPS = (("H5e skip-only", "OVX"), ("H5e registered", "OVX"), ("H7 OPRA replica", "OVX"),
          ("H7 OPRA replica", "GVZ"), ("H7 free-feed replica", "OVX"), ("H7 free-feed replica", "GVZ"))
FIELDS = ("rows", "near", "missing", "uncovered", "spread")


def measure(readings, days, groups=()):
    """readings: [{"day", "reading", "index", "E", "C", "T", "offsets"}]; days: {day: {index: series}} from the
    sealed files. -> {(reading, index): {"rows", "near", "missing", "uncovered", "spread"}}; an uncovered day
    carries where it sits against the data, a spread its day. Every pair in `groups` is kept even with no
    reading, so the report shows it."""
    out = {key: {k: [] for k in FIELDS} for key in groups}
    first, last = (min(days), max(days)) if days else (None, None)
    for x in readings:
        g = out.setdefault((x["reading"], x["index"]), {k: [] for k in FIELDS})
        if x["day"] not in days:
            g["uncovered"].append((x["day"], BEFORE if first is None or x["day"] < first else
                                   "after the data ends" if x["day"] > last else "no file for that day"))
            continue
        series = days[x["day"]].get(x["index"])
        if not series:
            g["missing"].append((x["day"], f"the day's file has no {x['index']} bar"))
            continue
        I, why = index_at(series, x["T"])
        if I is None:
            g["missing"].append((x["day"], why))
        else:
            g["rows"].append({"day": x["day"], "E": x["E"], "I": I, "C": x["C"]})
            if x.get("offsets"):
                g["spread"].append((x["day"], st.median(x["offsets"]), min(x["offsets"]), max(x["offsets"])))
        J = index_near(series, x["T"])
        if J is not None:
            g["near"].append({"day": x["day"], "E": x["E"], "I": J, "C": x["C"]})
    return out


# ---------------- the registered readings' days (public panels; the registered code, imported) ----------------
def frozen_r():
    """The risk-free rate the registered readings use (a decimal), refused unless it is the frozen 3.910%: a
    missing FRED cache gives r = 0 without stopping anything."""
    import modelfree
    import record_verdict as rv
    r = modelfree.risk_free()
    if not rv.rate_ok(f"{100 * r:.3f}"):
        raise SystemExit(f"index_timing: risk-free rate {100 * r:.3f}% is not the frozen {rv.FROZEN_RATE_PCT:.3f}% "
                         "- nothing measured (is data/fred_cache.json missing? run tools/seed_frozen_rate.py)")
    return r


def verdicts_recorded():
    """True only when H5e's FINAL reading and H7's reading are both in their hypothesis files."""
    import record_verdict as rv
    return rv.MARK_H5E_FINAL in rv.H5.read_text() and rv.MARK_H7 in rv.H7.read_text()


def h5e_days(through=H5E_THROUGH):
    """H5e's counted days as modelfree.h5e_report counts them: USO from H5E_START through the FINAL reading's
    last day, after-close days dropped, with an OVX close and both estimates. Two readings a day."""
    import analyze
    import modelfree as mf
    from panel_health import AFTER_CLOSE_DAYS
    dropped = {d.isoformat() for d in AFTER_CLOSE_DAYS}
    sym, idx = mf.H5E_SYMBOL, mf.BENCH[mf.H5E_SYMBOL]
    reg = [x for x in csv.DictReader(mf.SURF.open(newline="")) if x["symbol"] == sym and x["date"] <= through]
    wide = [x for x in csv.DictReader(mf.SURF_WIDE.open(newline="")) if x["symbol"] == sym and x["date"] <= through]
    r = frozen_r()
    closes = analyze.fetch_market_vol([idx]).get(idx) or {}
    out = []
    for d in sorted({x["date"] for x in wide}):
        if d in dropped or d < mf.H5E_START:
            continue
        inner = [x for x in reg if x["date"] == d]
        outer = [x for x in wide if x["date"] == d]
        a, b = mf.model_free_30d(inner, r), mf.model_free_30d(inner + outer, r, "skip")
        cb = closes.get(d)
        if not (cb and a and b):
            continue
        for reading, est, rows in (("H5e skip-only", b[0], inner + outer), ("H5e registered", a[0], inner)):
            T = ore.snapshot_minute(rows)
            out.append({"day": d, "reading": reading, "index": idx, "E": est, "C": cb, "T": T,
                        "offsets": offsets(rows, T)})
    return out


def h5e_cross_check(readings, modelfree_out):
    """Every H5e reading here must equal the gap modelfree --wide prints for that day (to its two decimals),
    the two must count the same days, at least one, and modelfree must have used the frozen rate.
    -> a list of disagreements (empty when they agree)."""
    import record_verdict as rv
    try:
        rows, rf, _na = rv.parse_h5e(modelfree_out)
    except ValueError as e:
        return [f"modelfree's output: {e}"]
    if not rv.rate_ok(rf):
        return [f"modelfree's risk-free rate {rf}% is not the frozen {rv.FROZEN_RATE_PCT:.3f}%"]
    printed = {d: (reg, skip) for d, _ovx, reg, skip, counted in rows if counted}
    mine = {}
    for x in readings:
        if x["reading"].startswith("H5e"):
            mine.setdefault(x["day"], {})[x["reading"]] = x["E"] - x["C"]
    if not printed and not mine:
        return ["neither side counts an H5e day: nothing to compare"]
    bad = [f"{d}: counted by one and not the other" for d in sorted(set(printed) ^ set(mine))]
    for d in sorted(set(printed) & set(mine)):
        reg, skip = printed[d]
        if not all(math.isfinite(v) for v in mine[d].values()):          # nan > 0.0051 is False: never a pass
            bad.append(f"{d}: a gap here is not a finite number")
        elif (abs(round(mine[d]["H5e registered"], 2) - reg) > 0.0051
                or abs(round(mine[d]["H5e skip-only"], 2) - skip) > 0.0051):
            bad.append(f"{d}: the gaps differ from modelfree's")
    return bad


def h5e_recorded_check(readings, recorded):
    """H5e's skip-only days here must be the recorded FINAL reading's: the same days, each gap the one it prints
    (to two decimals). modelfree's own run reads today's Cboe file, as this does, so only the record shows a close
    revised or replaced since the verdict. -> a list of disagreements (empty when they agree)."""
    import record_verdict as rv
    i = recorded.find(rv.MARK_H5E_FINAL)
    if i < 0:
        return ["no recorded H5e FINAL reading to compare"]
    line = re.search(r"^- Skip-only gap by day: (.*)\.$", recorded[i:], re.M)
    if not line:
        return ["the recorded H5e FINAL reading lacks its gap-by-day line"]
    rec = {d: float(g) for d, g in re.findall(r"(\d{4}-\d{2}-\d{2}) ([+-]\d+\.\d+)", line.group(1))}
    mine = {x["day"]: x["E"] - x["C"] for x in readings if x["reading"] == "H5e skip-only"}
    if not rec and not mine:
        return ["neither side counts an H5e day: nothing to compare"]
    bad = [f"{d}: counted by one and not the other" for d in sorted(set(rec) ^ set(mine))]
    for d in sorted(set(rec) & set(mine)):
        if not math.isfinite(mine[d]):
            bad.append(f"{d}: the skip-only gap here is not a finite number")
        elif abs(round(mine[d], 2) - rec[d]) > 0.0051:
            bad.append(f"{d}: the skip-only gap differs from the recorded one")
    return bad


def h7_recorded_check(readings, recorded):
    """H7's days here must be the recorded H7 reading's and give every number it prints. Its days are H7's
    expected trading days less those it names as missing or not counted (the writer refuses while an expected
    day has no row); then each fund's day count and mean |free - OPRA| (H7a), GLD's mean |free - GVZ| (H7b) and
    USO's mean free - OVX (H7c), to its three decimals. The record holds aggregates only, so agreement is on
    days and those means, not day by day. An OPRA folder that is not the private, pulled one would otherwise
    drop H7's days without a word. A date accepted as a gap (panel_health.ACCEPTED_GAPS: a day one panel lost)
    is left out of the date comparison: H7 can still count it from the monthly legs, and the writer's coverage
    check skips it, so its date proves nothing either way; the counts and means still cover it.
    -> a list of disagreements (empty when they agree)."""
    import h7_reader as h7
    import panel_health as ph
    import record_verdict as rv
    i = recorded.find(rv.MARK_H7)
    if i < 0:
        return ["no recorded H7 reading to compare"]
    j = recorded.find(rv.DB_CREDIT, i)
    blk = recorded[i:j if j > 0 else len(recorded)]
    num = r"([+-]?[\d.]+|n/a) "
    a = re.search(r"at the same minute: USO " + num + r"over (\d+) days, GLD " + num + r"over (\d+) days", blk)
    b = re.search(r"a mean absolute " + num + r"points from GVZ's close over (\d+) days", blk)
    c = re.search(r"minus OVX's close averaged " + num + r"over (\d+) days", blk)
    if not (a and b and c):
        return ["the recorded H7 reading lacks its H7a, H7b or H7c line"]
    rec = {("USO", "a"): a.group(1, 2), ("GLD", "a"): a.group(3, 4), ("GLD", "b"): b.group(1, 2),
           ("USO", "c"): c.group(1, 2)}
    named = set(re.findall(r"(\d{4}-\d{2}-\d{2}) (USO|GLD)\b", "\n".join(
        ln for ln in blk.splitlines() if ln.startswith(("- Still missing at the", "- Also not counted")))))
    want = {sym: {d for d in rv.expected_days(rv.H7_START_DAY, rv.H7_END_DAY) if (d, sym) not in named}
            for sym in h7.INDEX}
    pairs = {}
    for x in readings:
        if x["reading"] in ("H7 OPRA replica", "H7 free-feed replica"):
            pairs.setdefault((x["index"], x["day"]), {})[x["reading"]] = x
    days = {ix: {d: (p["H7 free-feed replica"], p["H7 OPRA replica"]) for (k, d), p in pairs.items()
                 if k == ix and len(p) == 2} for ix in h7.INDEX.values()}
    if not any(days.values()) and all(n == "0" for _m, n in rec.values()):
        return ["neither side counts an H7 day: nothing to compare"]
    bad, differ = [], set()
    gaps = {d.isoformat() for d in ph.ACCEPTED_GAPS}                 # want leaves them out too (expected_days)
    for sym, ix in h7.INDEX.items():
        mine = set(days[ix]) - gaps
        if mine != want[sym]:
            differ.add(sym)
            bad.append(f"{sym}: counted by one and not the other: {', '.join(sorted(mine ^ want[sym]))}")
    what = {"a": ("mean |free - OPRA|", lambda f, o: abs(f["E"] - o["E"])),
            "b": ("mean |free - GVZ|", lambda f, o: abs(f["E"] - f["C"])),
            "c": ("mean free - OVX", lambda f, o: f["E"] - f["C"])}
    for (sym, part), (m, n) in rec.items():
        if sym in differ:
            continue
        got = list(days[h7.INDEX[sym]].values())
        name, term = what[part]
        val = sum(term(f, o) for f, o in got) / len(got) if got else None
        if len(got) != int(n):
            bad.append(f"{sym} H7{part}: {len(got)} days here, {n} in the recorded reading")
        elif got and not math.isfinite(val):                        # nan > 0.00051 is False: never a pass
            bad.append(f"{sym} H7{part}: the {name} here is not a finite number")
        elif got and (m == "n/a" or abs(round(val, 3) - float(m)) > 0.00051):
            bad.append(f"{sym} H7{part}: the {name} differs from the recorded one")
    return bad


def recorded():
    """The text of H5's and H7's hypothesis files, where the two verdicts are recorded."""
    import record_verdict as rv
    return rv.H5.read_text(), rv.H7.read_text()


def h7_days():
    """H7's counted days as tools/h7_reader.py counts them (its own functions, imported): the OPRA and
    free-feed replicas, each against its index's close."""
    import analyze
    import h7_reader as h7
    import ovx_replicate as O
    from panel_health import AFTER_CLOSE_DAYS
    dropped = {d.isoformat() for d in AFTER_CLOSE_DAYS}
    R = O.bey_to_continuous(frozen_r())
    vol = analyze.fetch_market_vol(sorted(h7.INDEX.values()))
    closes = {sym: {k: v for k, v in (vol.get(ix) or {}).items() if not k.startswith("_")} for sym, ix in h7.INDEX.items()}
    out = []
    for day, sym in ore.monthly_days():
        if not (h7.H7_START <= day <= h7.H7_END) or sym not in h7.INDEX or day in dropped:
            continue
        x = h7.day_reading(day, sym, R, ore.DATA_DIR)
        if not x or not h7.counted(x, closes):
            continue
        rows = ore.monthly_recorded(day, sym)
        T = ore.snapshot_minute(rows)
        for reading, key in (("H7 OPRA replica", "opra"), ("H7 free-feed replica", "free")):
            out.append({"day": day, "reading": reading, "index": h7.INDEX[sym], "E": x[key],
                        "C": closes[sym][day], "T": T, "offsets": offsets(rows, T)})
    return out


# ---------------- the report: aggregates only ----------------
def report(groups, flags):
    f = lambda v, sign=True: "n/a" if not math.isfinite(v) else (f"{v:+.3f}" if sign else f"{v:.3f}")  # noqa: E731
    lines = []
    for (reading, idx), g in sorted(groups.items()):
        if not (g["rows"] or g["missing"] or g["uncovered"]):
            lines.append(f"== {reading}, against {idx}: no counted day to measure")
            continue
        d = describe(g["rows"])
        covered = len(g["rows"]) + len(g["missing"])
        before = sorted(day for day, where in g["uncovered"] if where == BEFORE)
        lines.append(f"== {reading}, against {idx}: {len(g['rows'])} of {covered} covered days measured"
                     + (f"; {len(before)} counted days before the data begins ({before[0]} to {before[-1]})"
                        if before else ""))
        for day, where in g["uncovered"]:
            if where != BEFORE:
                lines.append(f"   not covered: {day} ({where})")
        for day, why in g["missing"]:
            lines.append(f"   not measured: {day} ({why})")
        if not g["rows"]:
            continue
        m, a = d["mean"], d["mean_abs"]
        lines.append(f"   signed means, points: E - C {f(m['E - C'])} = (E - I(T)) {f(m['E - I(T)'])} + "
                     f"(I(T) - C) {f(m['I(T) - C'])}   [adds up to {d['sum_check']:.1e}]")
        lines.append(f"   mean absolute: |E - C| {f(a['E - C'], False)}, |E - I(T)| {f(a['E - I(T)'], False)}, "
                     f"|I(T) - C| {f(a['I(T) - C'], False)}; corr(E - I(T), I(T) - C) {f(d['corr'])}")
        lines.append("   persistence (days, rho, n_eff): " + "; ".join(
            f"{k} {t}, {f(rho)}, {ne:.1f}" for k, (t, rho, ne) in d["persistence"].items()))
        if g["near"]:
            s = describe(g["near"])
            lines.append(f"   sensitivity, the bar nearest T within 15 s (may use a value printed after T), "
                         f"{s['n']} days: E - I {f(s['mean']['E - I(T)'])}, I - C {f(s['mean']['I(T) - C'])}")
        if g["spread"]:
            med = st.median(s[1] for s in g["spread"])
            lines.append(f"   quote times around T, seconds: each day's median (earliest to latest); the median "
                         f"of the daily medians {med:+.0f}")
            per = [f"{day} {m:+.0f} ({lo:+.0f} to {hi:+.0f})" for day, m, lo, hi in g["spread"]]
            lines += ["      " + "; ".join(per[i:i + 4]) for i in range(0, len(per), 4)]
    lines.append("close check (|last DBIX value - Cboe close| > 0.05, kept): "
                 + (", ".join(flags) if flags else "no day flagged"))
    lines.append(CREDIT)
    return "\n".join(lines)


def reference_output():
    """modelfree.py --wide through H5e's last day, cache only: (exit code, stdout, stderr)."""
    import subprocess
    p = subprocess.run([sys.executable, str(ROOT / "modelfree.py"), "--wide", "--through", H5E_THROUGH],
                       cwd=ROOT, capture_output=True, text=True, env=dict(os.environ, FRED_KEY="use-cache"))
    return p.returncode, p.stdout, p.stderr


def main(argv=()):
    if not verdicts_recorded():
        raise SystemExit("index_timing: the DBIX files stay sealed until H5e's FINAL reading and H7's reading are "
                         "both recorded (12-19 Nov 2026); nothing was read.")
    sealed = seal((DBIX_DIR / "README.md").read_text())
    days = {day: bars(p, sealed) for day, p in day_files(DBIX_DIR, sealed).items()}
    readings = h5e_days() + h7_days()
    code, out, err = reference_output()
    if code != 0:
        raise SystemExit(f"index_timing: modelfree.py --wide exited {code}, so its output is not accepted "
                         f"({(err.strip().splitlines() or ['no message'])[-1]})")
    bad = h5e_cross_check(readings, out)
    if bad:
        raise SystemExit("index_timing: H5e's days here do not match modelfree's registered reading: " + "; ".join(bad))
    h5_text, h7_text = recorded()
    bad = h5e_recorded_check(readings, h5_text)
    if bad:
        raise SystemExit("index_timing: H5e's days here do not match its recorded FINAL reading: " + "; ".join(bad))
    bad = h7_recorded_check(readings, h7_text)
    if bad:
        raise SystemExit("index_timing: H7's days here do not match its recorded reading: " + "; ".join(bad)
                         + f" - is VOLREC_DATABENTO_DIR ({ore.DATA_DIR}) the private, pulled OPRA folder?")
    flags = []
    for day in sorted(days):
        for x in {(r["index"], r["C"]) for r in readings if r["day"] == day}:
            if close_flag(last_value(days[day][x[0]], day), x[1]):
                flags.append(f"{day} {x[0]}")
    print(f"Index timing - EXPLORATORY, descriptive; no test, no verdict. DBIX days: {min(days)} to {max(days)} "
          f"({len(days)} files).\n")
    print(report(measure(readings, days, GROUPS), flags))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
