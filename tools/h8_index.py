#!/usr/bin/env python3
"""H8's choice 6: a secondary, DESCRIPTIVE reading - no bar, no test, never part of H8's verdict.

Decided 4 Nov 2026 (H8-DRAFT.md, item 6; Gabriel approved it that day). Built 5 Nov 2026 and tested only on
SYNTHETIC files (tools/test_h8_index.py). It reads H8's index files only after the window has closed.

For each fund with a Cboe index built on options, both feeds' estimates at the snapshot minute against Cboe's
own index at that minute:
  free, OPRA  h8_quotes.day_pair's S0s and S1s: the same contracts, the free snapshot as recorded and OPRA's
              quote at opra_reference.snapshot_minute (matched within 120 s), through the registered
              estimator - H8's own fund-days, from h8_quotes.fund_days;
  I(T)        the timing plan's rule, read by its reader (tools/index_timing.py: seal, file inventory, bar
              parser and index_at): the close of the last one-second bar whose second has ended by T, from
              T's New York trading day, at or after 09:31 there, at most 60 s old, and a finite number;
              otherwise the fund-day is not measured, never filled, and listed with its reason.
Pairs: USO/OVX, GLD/GVZ, AAPL/VXAPL (built on the same fund's or stock's options); SPY/VIX, QQQ/VXN, IWM/RVX
(built on SPX, NDX and RUT options, so the index-versus-fund difference is part of any gap). TSLA and NVDA
have no Cboe index. A fund-day counts only when both feeds' estimates and I(T) are there and finite, so the two
columns cover the same days; every window trading day (panel_health's calendar) is accounted for, once per
fund. Per fund: mean and mean absolute (estimate - index), free and OPRA side by side.

Caveat: this project's estimator (weekly expiries, a +/-30% band, whole-day time) is not Cboe's, so a gap here
mixes method with data; H8's free-versus-OPRA test stays the only clean data comparison.

Reads only H8's own folder (VOLREC_DBIX_H8_DIR, default ~/Documents/volrec-licensed/dbix-h8), never the timing
plan's sealed one. Each file is sealed as it is bought (sealed_readme, below, is the buyer's side of the seal):
its sha256 must match the seal in that folder's README.md before it is read, and every day file the seal
lists must be there. Prints aggregates only - counts, means and the dates of days not measured - never an
index value or an estimate.

  VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra python tools/h8_index.py    # refuses until 30 Jan 2027
"""
import hashlib
import math
import os
import statistics as st
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ["FRED_KEY"] = "use-cache"              # cache only, as H8's documented run and the timing reader take it

import h8_quotes as h8q                            # noqa: E402
import index_timing as it                          # noqa: E402
import modelfree                                   # noqa: E402
import opra_reference as ore                       # noqa: E402
from panel_health import US_MARKET_HOLIDAYS        # noqa: E402  the project's one market calendar

H8_DIR = Path(os.environ.get("VOLREC_DBIX_H8_DIR") or Path.home() / "Documents" / "volrec-licensed" / "dbix-h8")
PAIRS = {"USO": "OVX", "GLD": "GVZ", "AAPL": "VXAPL", "SPY": "VIX", "QQQ": "VXN", "IWM": "RVX"}
INDICES = tuple(PAIRS.values())
WINDOW = ("2026-12-01", ore.H8_END)                # H8's 41 trading days: 22 in December, 19 in January
SEAL = "## Seal (sha256)"
CREDIT = ("Data provided by Databento (OPRA consolidated NBBO; Core Indices). Index values: Cboe Global Markets. "
          "Aggregates only.")


# ---------------- the seal, written as each file is bought (the private buyer calls this) ----------------
def sealed_readme(text, name, raw):
    """The README with one more seal line, `    <sha256>  <name>`, at the end of its seal block, which must be
    its last section (index_timing.seal stops at the next heading). A name already sealed is refused: a file
    is sealed once, under the hash it was bought with."""
    if SEAL not in text:
        raise SystemExit("README.md has no seal block: nothing sealed")
    if any(ln.startswith("#") for ln in text.split(SEAL, 1)[1].splitlines()):
        raise SystemExit("README.md's seal block is not its last section: nothing sealed")
    if not name or name != name.strip() or "\n" in name:
        raise SystemExit(f"{name!r} is not a file name: nothing sealed")
    try:
        have = it.seal(text)
    except SystemExit:                              # an empty block, before the first purchase
        have = {}
    if name in have:
        raise SystemExit(f"{name} is already sealed: not sealed again")
    return text + ("" if text.endswith("\n") else "\n") + f"    {hashlib.sha256(raw).hexdigest()}  {name}\n"


# ---------------- H8's index files ----------------
def load_days(folder):
    """{day: {index: [(ts_event, close)]}} for the six indices, from H8's own sealed folder only."""
    folder = Path(folder)
    if folder.resolve() == it.DBIX_DIR.resolve():
        raise SystemExit("h8_index: that is the timing plan's sealed folder; H8 reads only its own - nothing was read")
    sealed = it.seal((folder / "README.md").read_text())
    return {day: it.bars(p, sealed, indices=INDICES) for day, p in it.day_files(folder, sealed).items()}


def in_window(day):
    return WINDOW[0] <= day <= WINDOW[1]


def window_days():
    """H8's trading days: weekdays in the window that are not market holidays (the private buyer reads this too)."""
    d, end, out = date.fromisoformat(WINDOW[0]), date.fromisoformat(WINDOW[1]), []
    while d <= end:
        if d.weekday() < 5 and d not in US_MARKET_HOLIDAYS:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def readings(r):
    """[{"day", "fund", "index", "T", "free", "opra"}]: every fund-day H8 itself reads, for the six funds."""
    return [{"day": day, "fund": sym, "index": ix, "T": got["T"], "free": got["S0s"], "opra": got["S1s"]}
            for sym, ix in PAIRS.items() for day, got in h8q.fund_days(sym, r)]


# ---------------- the reading ----------------
def measure(readings, days, calendar=None):
    """-> {fund: {"index", "rows": [(free - I, OPRA - I)], "missing": [(day, why)], "uncovered": [day]}}, over
    the window only. Every window trading day (window_days, or `calendar`) and every window day with an index
    file is accounted for exactly once per fund: measured, not measured with its reason, or not covered."""
    out = {f: {"index": ix, "rows": [], "missing": [], "uncovered": []} for f, ix in PAIRS.items()}
    seen = set()
    for x in readings:
        if not in_window(x["day"]):
            continue
        g = out[x["fund"]]
        seen.add((x["fund"], x["day"]))
        if x["day"] not in days:
            g["uncovered"].append(x["day"])
            continue
        if x["free"] is None or x["opra"] is None:
            g["missing"].append((x["day"], "neither feed has an estimate at the snapshot minute"
                                 if x["free"] is None and x["opra"] is None else
                                 "no free estimate at the snapshot minute" if x["free"] is None else
                                 "no OPRA estimate at the snapshot minute"))
            continue
        if not (math.isfinite(x["free"]) and math.isfinite(x["opra"])):
            g["missing"].append((x["day"], "an estimate is not a finite number"))
            continue
        series = days[x["day"]].get(x["index"])
        if not series:
            g["missing"].append((x["day"], f"the day's file has no {x['index']} bar"))
            continue
        I, why = it.index_at(series, x["T"])
        if I is None:
            g["missing"].append((x["day"], why))
            continue
        g["rows"].append((x["free"] - I, x["opra"] - I))
    expected = set(window_days() if calendar is None else calendar) | set(days)
    for f, g in out.items():
        for day in sorted(expected):
            if in_window(day) and (f, day) not in seen:
                g["missing"].append((day, "no fund-day from H8's files" if day in days else
                                     "neither a fund-day from H8's files nor an index file"))
    return out


def summary(g):
    """{"n", "free": (mean, mean absolute), "opra": (mean, mean absolute)} of estimate - index."""
    def two(xs):
        return (st.mean(xs), st.mean(abs(v) for v in xs)) if xs else (float("nan"), float("nan"))
    return {"n": len(g["rows"]), "free": two([a for a, _ in g["rows"]]), "opra": two([b for _, b in g["rows"]])}


def report(groups):
    lines = []
    for f, g in groups.items():
        s = summary(g)
        head = f"  {f:4s} / {g['index']:5s} {s['n']:3d} days"
        lines.append(head + ("   no measured day" if not s["n"] else
                             f"   free - index: mean {s['free'][0]:+.3f}, mean |.| {s['free'][1]:.3f}"
                             f"   OPRA - index: mean {s['opra'][0]:+.3f}, mean |.| {s['opra'][1]:.3f}"))
        why = {}
        for day, w in g["missing"]:
            why.setdefault(w, []).append(day)
        for w, ds in sorted(why.items()):
            lines.append(f"      not measured ({w}): {len(ds)} - {', '.join(sorted(ds))}")
        if g["uncovered"]:
            lines.append(f"      no index file for the day: {len(g['uncovered'])} - {', '.join(sorted(g['uncovered']))}")
    lines.append("  TSLA, NVDA: no Cboe index - not part of this reading.")
    return "\n".join(lines)


def main(argv=(), today=None):
    today = today or date.today()
    if today.isoformat() <= WINDOW[1]:
        raise SystemExit(f"h8_index: H8's index files are read only after the window closes ({WINDOW[1]}); "
                         "nothing was read.")
    days = load_days(H8_DIR)
    groups = measure(readings(modelfree.risk_free()), days)
    print(f"H8 choice 6 - a secondary, DESCRIPTIVE reading; no bar, no test, never part of H8's verdict.\n"
          f"Window {WINDOW[0]} to {WINDOW[1]}; index files {min(days)} to {max(days)} ({len(days)}). Estimate - "
          "index at the snapshot minute, in volatility points; this project's estimator is not Cboe's, so a gap "
          "mixes method with data.\n")
    print(report(groups))
    print(f"\n{CREDIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
