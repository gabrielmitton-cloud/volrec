#!/usr/bin/env python3
"""Match a Bloomberg OMON export against the free feed, contract by contract.

WHAT THIS IS FOR
----------------
`data/surface.csv` records the strike surface from Alpaca's free, indicative,
non-OPRA feed. Bloomberg is the authoritative quote. Matching the two on the same
contracts, at nearly the same minute, is the only way to separate two things that
look identical in the H3 residual:

  1. FEED QUALITY - are the free quotes themselves wrong?
  2. DERIVED VALUES - are the prices fine while the implied volatilities differ,
     because the two sides make different forward, rate and dividend assumptions?

The first comparison (15 Sep 2026) found prices agreeing to within half a percent
while implied volatilities differed by one to two points. That distinction matters:
`modelfree.py` integrates PRICES, not implied volatilities, so a difference in the
IV convention does not flow into the model-free estimate.

LICENCE, READ THIS BEFORE CHANGING THE OUTPUT
---------------------------------------------
Bloomberg's terms restrict redistribution. Exports live OUTSIDE the repository, in
~/Documents/volrec-bloomberg, and this script refuses to write per-contract
Bloomberg values anywhere inside it. Only aggregates - counts, medians, spreads -
reach stdout or the summary file. The licensing question was SETTLED on 17 Sep 2026:
derived aggregates may be published with "Source: Bloomberg Finance L.P.", and raw
Bloomberg data may never enter an open repository. Every run ends with that line.
There is no network call here and nothing is fetched.

USAGE
-----
  python3 tools/bloomberg_compare.py                       # newest export per symbol
  python3 tools/bloomberg_compare.py --date 2026-09-15
  python3 tools/bloomberg_compare.py --dir ~/somewhere/else --json out.json

Exit code is 0 when every check passes, 1 when a check fails. The checks are the
point: a comparison run against mismatched times or a handful of contracts would
produce a number, and the number would be meaningless.
"""
import argparse
import csv
import json
import os
import re
import statistics as st
import sys
import zipfile
# Stdlib XML, deliberately: these files come from the user's own terminal, and
# ElementTree does not process DTDs at all, so entity-expansion attacks do not apply.
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURFACE = ROOT / "data" / "surface.csv"
DEFAULT_DIR = Path.home() / "Documents" / "volrec-bloomberg"

# Required beside any published Bloomberg-derived figure. Confirmed 17 Sep 2026 by
# Marc Vinyard, who administers Pepperdine's subscription: "You can publish an
# article that cites Bloomberg data as the source of your information, but you
# cannot add the raw Bloomberg data to an open access repository."
ATTRIBUTION = "Bloomberg figures: Source: Bloomberg Finance L.P."

# Rigorous-validation thresholds. A run that trips one of these is reported as a
# failure rather than quietly averaged away.
MAX_QUOTE_GAP_MIN = 30      # minutes between the two snapshots
MIN_MATCHED = 20            # matched contracts per symbol
MIN_MID_FOR_PCT = 0.50      # below this a one-cent tick is a huge percentage; report, do not gate
# The gate on price agreement is relative to the market's own bid-ask. Two feeds
# whose mids sit closer together than half the quoted spread are quoting the same
# thing; a fixed cent or percent threshold just measures how cheap the option is.
MAX_MID_VS_SPREAD = 0.5

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_sheet(path):
    """Rows of an .xlsx, without a third-party library."""
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    rows = []
    for name in sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)):
        for row in ET.fromstring(z.read(name)).iter("{%s}row" % NS["m"]):
            vals = []
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                x = v.text if v is not None else ""
                if c.get("t") == "s" and x:
                    x = shared[int(x)]
                vals.append(x or "")
            rows.append(vals)
    return rows


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def parse_omon(path, expiry_label):
    """{(type, strike): {bid, ask, iv, volume}} for one expiry block of an OMON export.

    The sheet stacks one block per expiry, each introduced by a header row like
    "16-Oct-26 (31d); CSize 100; R 4.26; IFwd 358.17", then strike rows carrying
    calls on the left and puts on the right.
    """
    out, block, forward = {}, None, None
    for r in read_sheet(path):
        first = (r[0] if r else "") or ""
        if "CSize" in first:
            block = first.strip()
            m = re.search(r"IFwd\s+([\d.]+)", block)
            if block.startswith(expiry_label) and m:
                forward = float(m.group(1))
        if not block or not block.startswith(expiry_label):
            continue
        if not re.match(r"^\d+(\.\d+)?$", first):
            continue
        for off, typ in ((0, "C"), (7, "P")):
            if len(r) < off + 7:
                continue
            k = num(r[off])
            if k is None:
                continue
            out[(typ, round(k, 2))] = {
                "bid": num(r[off + 2]), "ask": num(r[off + 3]),
                "iv": num(r[off + 5]), "volume": num(r[off + 6]),
            }
    return out, forward


def parse_ts(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    s = re.sub(r"\.(\d{6})\d+", r".\1", s)     # trim nanoseconds python cannot parse
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def bloomberg_label(iso_date):
    """2026-10-16 -> 16-Oct-26, the label Bloomberg writes in the block header."""
    d = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{d.day:d}-{d.strftime('%b')}-{d.strftime('%y')}"


def surface_rows(date):
    if not SURFACE.exists():
        sys.exit("data/surface.csv does not exist yet; nothing to compare against.")
    rows = [r for r in csv.DictReader(SURFACE.open(newline="")) if r["date"] == date]
    if not rows:
        sys.exit(f"data/surface.csv has no rows for {date}.")
    return rows


def compare(symbol, export, rows, fails, notes):
    """One symbol: match every Bloomberg contract to the free feed and measure."""
    # The expiry to compare is the one the recorder chose closest to 30 days.
    exps = sorted({r["expiration"] for r in rows}, key=lambda e: abs(int(
        next(x["dte"] for x in rows if x["expiration"] == e)) - 30))
    expiry = exps[0]
    bbg, forward = parse_omon(export, bloomberg_label(expiry))
    if not bbg:
        fails.append(f"{symbol}: the export has no {bloomberg_label(expiry)} block")
        return None

    free = {(r["type"], round(float(r["strike"]), 2)): r for r in rows if r["expiration"] == expiry}
    iv, mid, cents, ratio, sp_free, sp_bbg, strikes = [], [], [], [], [], [], []
    vol_free = vol_bbg = 0.0
    for (typ, strike), b in bbg.items():
        f = free.get((typ, strike))
        if not f or b["iv"] is None:
            continue
        fi, fm, fb, fa = num(f["iv"]), num(f["mid"]), num(f["bid"]), num(f["ask"])
        if fi is None:
            continue
        strikes.append(strike)
        iv.append(fi * 100 - b["iv"])                       # volatility points, free minus Bloomberg
        bm = (b["bid"] + b["ask"]) / 2 if None not in (b["bid"], b["ask"]) else None
        if fm and bm:
            cents.append(abs(fm - bm) * 100)
            if b["ask"] - b["bid"] > 0:
                ratio.append(abs(fm - bm) / (b["ask"] - b["bid"]))
            if bm >= MIN_MID_FOR_PCT:
                mid.append(100 * (fm - bm) / bm)
            sp_bbg.append(100 * (b["ask"] - b["bid"]) / bm)
        if fm and fb is not None and fa is not None:
            sp_free.append(100 * (fa - fb) / fm)
        fv = num(f["volume"])
        if fv is not None and b["volume"] is not None:
            vol_free += fv
            vol_bbg += b["volume"]

    if len(iv) < MIN_MATCHED:
        fails.append(f"{symbol}: only {len(iv)} matched contracts, need {MIN_MATCHED}")
    med_mid = st.median([abs(x) for x in mid]) if mid else None
    med_cents = st.median(cents) if cents else None
    med_ratio = st.median(ratio) if ratio else None
    if med_ratio is not None and med_ratio > MAX_MID_VS_SPREAD:
        fails.append(f"{symbol}: the mids differ by {med_ratio:.2f} of a bid-ask spread, over "
                     f"{MAX_MID_VS_SPREAD}; that is a feed disagreement, not rounding")

    free_strikes = sorted(float(r["strike"]) for r in rows if r["expiration"] == expiry)
    if strikes and (min(strikes) < free_strikes[0] or max(strikes) > free_strikes[-1]):
        notes.append(f"{symbol}: the export reaches strikes the recorder does not cover")
    if strikes and free_strikes[0] < min(strikes) * 0.97:
        notes.append(f"{symbol}: the recorder reaches {free_strikes[0]:.0f} but the export stops at "
                     f"{min(strikes):.0f}; widen the strike count for the tails")

    p90 = sorted(abs(x) for x in iv)[max(0, int(0.9 * len(iv)) - 1)] if iv else None
    return {
        "symbol": symbol, "expiry": expiry, "matched": len(iv),
        "strikes": [min(strikes), max(strikes)] if strikes else None,
        "free_strikes": [free_strikes[0], free_strikes[-1]],
        "iv_median": st.median(iv) if iv else None,
        "iv_mean": sum(iv) / len(iv) if iv else None,
        "iv_p90_abs": p90,
        "mid_median_pct": st.median(mid) if mid else None,
        "mid_median_cents": med_cents,
        "mid_vs_spread": med_ratio,
        "spread_free_pct": st.median(sp_free) if sp_free else None,
        "spread_bbg_pct": st.median(sp_bbg) if sp_bbg else None,
        "volume_free": vol_free, "volume_bbg": vol_bbg,
        "forward_bbg": forward, "spot_free": num(rows[0]["spot"]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=str(DEFAULT_DIR), help="folder holding the OMON exports")
    ap.add_argument("--date", help="trading day to compare, YYYY-MM-DD; default is the newest matched")
    ap.add_argument("--json", help="write the aggregate summary here (never per-contract values)")
    ap.add_argument("--pull-time", help="UTC time the export was pulled, HH:MM. The file's own "
                                        "timestamp is when it reached this machine, which is later.")
    a = ap.parse_args()

    folder = Path(os.path.expanduser(a.dir)).resolve()
    if ROOT in folder.parents or folder == ROOT:
        sys.exit("Refusing to read exports from inside the repository. Bloomberg's licence "
                 "restricts redistribution; keep them in ~/Documents/volrec-bloomberg.")

    exports = {}
    for p in sorted(folder.glob("*_OMON_*.xlsx")):
        m = re.match(r"([A-Z.]+)_OMON_(\d{4}-\d{2}-\d{2})\.xlsx$", p.name)
        if m and (a.date is None or m.group(2) == a.date):
            exports.setdefault(m.group(2), {})[m.group(1)] = p
    if not exports:
        sys.exit(f"No exports named SYMBOL_OMON_YYYY-MM-DD.xlsx in {folder}")
    date = a.date or max(exports)
    day = exports[date]

    rows = surface_rows(date)
    fails, notes, results = [], [], []

    free_ts = max((parse_ts(r["quote_time"]) for r in rows if r.get("quote_time")), default=None)
    stated = None
    if a.pull_time:
        h, m = (int(x) for x in a.pull_time.split(":"))
        stated = datetime.strptime(date, "%Y-%m-%d").replace(hour=h, minute=m, tzinfo=timezone.utc)
    file_ts = min((datetime.fromtimestamp(p.stat().st_mtime, timezone.utc) for p in day.values()), default=None)
    bbg_ts = stated or file_ts
    gap = abs((free_ts - bbg_ts).total_seconds()) / 60 if free_ts and bbg_ts else None
    if gap is None:
        notes.append("could not establish both snapshot times; state the times by hand in any write-up")
    elif stated is None and gap > MAX_QUOTE_GAP_MIN:
        notes.append(f"the export file is {gap:.0f} minutes from the recorder's snapshot, but that is the "
                     f"file's save time. Pass --pull-time HH:MM with the real pull time to judge this.")
        gap = None
    elif gap > MAX_QUOTE_GAP_MIN:
        fails.append(f"snapshots are {gap:.0f} minutes apart, over the {MAX_QUOTE_GAP_MIN} minute limit; "
                     f"a difference this measures is a time gap, not a feed gap")

    print(f"Bloomberg against the free feed, {date}")
    print(f"  free feed snapshot   {free_ts:%H:%M:%S} UTC" if free_ts else "  free feed snapshot   unknown")
    print(f"  export file written  {bbg_ts:%H:%M:%S} UTC (file time, not the pull time)" if bbg_ts else "")
    print(f"  gap                  {gap:.0f} min\n" if gap is not None else "")
    head = (f"{'':6}{'matched':>8}{'expiry':>12}{'IV med':>8}{'IV mean':>9}{'IV p90':>8}"
            f"{'mid %':>8}{'mid c':>7}{'of sprd':>9}{'sprd free':>10}{'sprd bbg':>9}{'vol free':>10}{'vol bbg':>9}")
    print(head)
    for symbol in sorted(day):
        sym_rows = [r for r in rows if r["symbol"] == symbol]
        if not sym_rows:
            fails.append(f"{symbol}: the recorder captured no rows on {date}")
            continue
        r = compare(symbol, day[symbol], sym_rows, fails, notes)
        if not r:
            continue
        results.append(r)
        f = lambda v, w, d=2: (f"{v:>{w}.{d}f}" if v is not None else f"{'n/a':>{w}}")
        print(f"{symbol:6}{r['matched']:>8}{r['expiry']:>12}{f(r['iv_median'],8)}{f(r['iv_mean'],9)}"
              f"{f(r['iv_p90_abs'],8)}{f(r['mid_median_pct'],8)}{f(r['mid_median_cents'],7,1)}{f(r['mid_vs_spread'],9)}{f(r['spread_free_pct'],10,1)}"
              f"{f(r['spread_bbg_pct'],9,1)}{r['volume_free']:>10.0f}{r['volume_bbg']:>9.0f}")
        if r["strikes"]:
            print(f"      strikes {r['strikes'][0]:.0f}-{r['strikes'][1]:.0f} matched; "
                  f"the recorder covers {r['free_strikes'][0]:.0f}-{r['free_strikes'][1]:.0f}")

    print("\nIV columns are volatility points, free feed minus Bloomberg. Mid is a signed percent "
          "difference\non contracts worth 50c or more, then the same gap in cents, then as a "
          "fraction of the\nquoted bid-ask spread, which is the one the checks gate on.")
    for n in notes:
        print(f"  NOTE  {n}")
    for f_ in fails:
        print(f"  FAIL  {f_}")
    print(f"\n{ATTRIBUTION}")

    if a.json:
        out = Path(os.path.expanduser(a.json)).resolve()
        if ROOT in out.parents or out == ROOT:
            # The licence question was answered on 17 Sep 2026: derived results may
            # be published with citation, raw Bloomberg data may not enter an open
            # repository. This summary is aggregated, so it is not raw - but a
            # machine-readable dump is one careless edit away from per-contract
            # values, so it is still kept outside the repository by default.
            sys.exit("Refusing to write the summary inside the repository. Derived "
                     "figures may be PUBLISHED with attribution; a data dump stays out.")
        out.write_text(json.dumps({"date": date, "gap_minutes": gap, "results": results,
                                   "failures": fails, "notes": notes,
                                   "attribution": ATTRIBUTION}, indent=2))
        print(f"\nwrote {out}")

    print(f"\n{'PASS' if not fails else 'FAIL'}: {len(results)} symbol(s), {len(fails)} failed check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
