#!/usr/bin/env python3
"""lab/ - verify every lab purchase against the ledger and the plan (EXPLORATORY; 14 Oct 2026).

Why: a purchase can "succeed" and still be useless. On 14 Oct 2026 the audit found 15 files that
Databento charged for and the tool logged as bought, which hold only a header (half-day requests timed
after the 1 p.m. close). Nothing had flagged them. This checks, without trusting the buyer:
  1. every file parses: Databento's quote header (or the definition header), at least one data row,
     a final newline, and the right fund in its symbols;
  2. every quote/listing file has exactly one ledger row (same day, fund, kind), and no lab ledger row
     lacks a file - no unrecorded spend, no phantom spend;
  3. no lab ledger row is dated outside LAB_START..LAB_END;
  4. every planned day-time (entries, stress marks, weekly samples) has its two files, apart from
     skips the registration explains;
  5. lab spend is within the lab's cap.

  FRED_KEY=use-cache python lab/verify_purchases.py
"""
import collections
import csv
import importlib.util as iu
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

QUOTE_HEAD = ("ts_recv", "bid_px_00", "ask_px_00", "symbol")
DEF_HEAD = ("raw_symbol",)
EXPLAINED_SKIPS = {("2020-04-29", "USO")}          # USO's 1-for-8 split day: OPRA listed nothing (registration)


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def file_problem(path):
    """None if the file is a usable Databento CSV for its fund, else a short reason."""
    name = path.name
    kind, sym = ("def", name.split("_")[2]) if name.startswith("DEF_LAB_") else ("quote", name.split("_")[2])
    with open(path, "rb") as fh:
        head_bytes = fh.read(8192)                  # the header and first rows are enough, and fast
        fh.seek(0, 2)
        size = fh.tell()
        fh.seek(max(0, size - 1))
        last = fh.read(1)
    if last != b"\n":
        return "no final newline (truncated?)"
    lines = head_bytes.decode(errors="replace").splitlines()
    head = [c.strip() for c in lines[0].split(",")] if lines else []
    need = DEF_HEAD if kind == "def" else QUOTE_HEAD
    if not all(h in head for h in need):
        return f"unexpected header {head[:6]}"
    if len(lines) < 2:
        return "header only - no data rows"
    col = head.index("raw_symbol" if kind == "def" else "symbol")
    row = next(csv.reader([lines[1]]))
    if len(row) <= col or not row[col].strip().startswith(sym):
        return f"first symbol {row[col] if len(row) > col else '?'} is not {sym}"
    return None


def parse_name(name):
    """('quote'|'def', day, fund, hhmm or None)."""
    p = name[:-4].split("_")
    return ("def", p[3], p[2], None) if p[0] == "DEF" else ("quote", p[3], p[2], p[4])


def reconcile(file_names, ledger_rows, lab_tag="-lab", def_tag="-def-lab"):
    """Counts of files vs ledger rows per (kind, day, fund). Returns a list of mismatches."""
    have = collections.Counter((k, d, s) for k, d, s, _t in map(parse_name, file_names))
    paid = collections.Counter()
    for r in ledger_rows:
        tag = r.get("symbol", "")
        if tag.endswith(def_tag):
            paid[("def", r["date"], tag[:-len(def_tag)])] += 1
        elif tag.endswith(lab_tag):
            paid[("quote", r["date"], tag[:-len(lab_tag)])] += 1
    return [(key, have[key], paid[key]) for key in sorted(set(have) | set(paid)) if have[key] != paid[key]]


def main():
    fl, cal, bars = _load("fetch_lab"), _load("tradecal"), _load("bars")
    files = sorted(p for p in fl.LAB_DIR.glob("*.csv"))
    rows = fl.ledger_rows()
    lab_rows = [r for r in rows if r.get("symbol", "").endswith(fl.LAB_TAG)]
    problems = [(p.name, why) for p in files if (why := file_problem(p))]
    mism = reconcile([p.name for p in files], lab_rows)
    dated_out = [r for r in lab_rows if not fl.date_ok(r["date"])]
    days = sorted(bars.load()["SPY"])
    plan = ([(e, cal.slot(e, "14:30")) for e, _x in cal.entries(days)] + [(d, cal.slot(d, "15:55")) for d in cal.stress_days(days)]
            + [(d, cal.slot(d, "14:30")) for d in cal.weekly_days(days)])
    names = {p.name for p in files}
    missing = [(d, t, s) for d, t in plan for s in bars.FUNDS if (d, s) not in EXPLAINED_SKIPS and not (
        fl.lab_stem(s, d, t) + ".csv" in names and fl.def_stem(s, d) + ".csv" in names)]
    planned = {fl.lab_stem(s, d, t) + ".csv" for d, t in plan for s in bars.FUNDS} | {fl.def_stem(s, d) + ".csv" for d, _t in plan for s in bars.FUNDS}
    unplanned = sorted(n for n in names if n not in planned)
    spent = fl.spent_lab(rows)
    used_problems = [x for x in problems if x[0] in planned]
    print(f"lab/ purchase verification: {len(files)} files, {len(lab_rows)} lab ledger rows, ${spent:.2f} of ${fl.LAB_BUDGET_USD:.0f}")
    print(f"  unusable files: {len(problems)} ({len(used_problems)} of them are files the analysis uses)")
    for n, why in problems[:20]:
        print(f"    {n}: {why}{'  <- USED' if n in planned else ''}")
    print(f"  files without exactly one ledger row (or the reverse): {len(mism)}")
    for key, h, p in mism[:20]:
        print(f"    {key}: {h} file(s), {p} ledger row(s)")
    print(f"  ledger rows dated outside {fl.LAB_START}..{fl.LAB_END}: {len(dated_out)}")
    print(f"  planned day-times missing a file: {len(missing)}  (explained skips: {sorted(EXPLAINED_SKIPS)})")
    for m in missing[:10]:
        print(f"    {m}")
    print(f"  files outside the final plan (bought before a fix; not used): {len(unplanned)}")
    ok = not used_problems and not mism and not dated_out and not missing and spent <= fl.LAB_BUDGET_USD
    print(f"\nRESULT: {'VERIFIED' if ok else 'PROBLEMS - see above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
