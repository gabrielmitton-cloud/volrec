#!/usr/bin/env python3
"""The public page's Bloomberg figures, against what the reader prints from the exports today.

WHY THIS EXISTS (11 Nov 2026)
-----------------------------
On 17 Oct the Bloomberg-export reader was fixed (it had dropped the put of any row whose implied-volatility
cell Bloomberg left out of the file). The hypothesis files and the page's H5 row were corrected that day; the
page's table, its day-count sentence, its 21-month sentence and one narrative sentence were not, and for 25
days index.html kept figures the fixed reader no longer prints. Nothing compared the page with the reader.

This does, figure by figure: the "Checked against Bloomberg" table, the second-expiry note, the far-wing
lifts, the day-count sentence and the 21-month sentence, each against tools/bloomberg_compare.py or
tools/model_gap.py run on the exports as they are. A figure missing on either side is a difference.

The exports are licensed and live outside the repository (~/Documents/volrec-bloomberg), on Gabriel's Mac
only. Where that folder does not exist the check is a SKIP; where it exists but lacks a file it FAILS, since
a half-present folder is a broken setup, not a fresh clone. It reads the exports through the two tools,
links (never duplicates) the 15 and 16 Sep files into a temporary folder for the pooled run, writes nothing,
and prints aggregates only - the ones the page already publishes.

What is checked against what. The 47 figures in LABELS are checked against the EXPORTS, through the two tools,
each under its own identity: the day, the underlying and the expiry the page names (a report for another expiry
with the same numbers is a difference). H5a's and H5b's pooled figures have no maintained tool; page_vs_record()
checks them against the RECORD, the H5 file's corrected reading of 17 Oct, in the page's narrative and in its
hypothesis table, and runs everywhere (no export needed). The tools always run with the fixed reader: the switch
that reproduces the pre-17-Oct reading (VOLREC_BBG_POSITIONAL) is never passed on to them.

  python3 tools/site_bloomberg.py            # VERIFIED / MISMATCH / SKIP
"""
import argparse
import html as _html
import os
import re
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "index.html"
DEFAULT_DIR = Path.home() / "Documents" / "volrec-bloomberg"
ATTRIBUTION = "Bloomberg figures: Source: Bloomberg Finance L.P."

# The page's table, row by row: (day as printed, underlying). SPY's 15 Sep export matched 14 contracts and is
# not on the page. Far strikes were recorded from 18 Sep, so the 15 Sep rows show a dash.
DAYS = {"15 Sep": "2026-09-15", "18 Sep": "2026-09-18", "22 Sep": "2026-09-22", "23 Sep": "2026-09-23"}
ROWS = (("15 Sep", "TSLA"), ("15 Sep", "USO"), ("18 Sep", "USO"), ("22 Sep", "USO"), ("22 Sep", "TSLA"),
        ("23 Sep", "USO"), ("23 Sep", "TSLA"))
CELLS = ("contracts", "inside", "far puts", "far calls")
# The table's own headings, in order: a figure under the wrong heading is a wrong figure (Astra, 12 Nov 2026).
HEADERS = ("Day", "Underlying", "Contracts inside ±30%", "Inside ±30%", "Far puts", "Far calls")
SECOND, LONG = "2026-09-23_30Oct", "2026-09-23_long"      # the 23 Sep second expiry; the 21-month expiry
# The expiry each table row, lift and note is about (H5 file, the three matched wing days; H3 file, 21 months).
EXPIRY = {"15 Sep": "2026-10-16", "18 Sep": "2026-10-16", "22 Sep": "2026-10-16", "23 Sep": "2026-10-23"}
SECOND_EXPIRY = "2026-10-30"
LONG_BLOCK = ("TSLA", "16-Jun-28")
# The ten blocks the day-count sentence pools (H3 file: the 15 Sep table's six and the 16 Sep table's four).
POOL_BLOCKS = frozenset(
    [("2026-09-15", s, e) for s in ("SPY",) for e in ("16-Oct-26", "30-Oct-26")]
    + [("2026-09-15", s, e) for s in ("TSLA", "USO") for e in ("16-Oct-26", "20-Nov-26")]
    + [("2026-09-16", "SPY", "16-Oct-26"), ("2026-09-16", "TSLA", "16-Oct-26"), ("2026-09-16", "TSLA", "20-Nov-26"),
       ("2026-09-16", "USO", "16-Oct-26")])
POOL = ("2026-09-15", "2026-09-16")                       # the day-count sentence's two days
LIFT_DAYS = ("18 Sep", "23 Sep")                          # USO's far-wing lifts
NEEDED = (tuple(f"{s}_OMON_{d}.xlsx" for d in POOL for s in ("SPY", "TSLA", "USO"))
          + ("USO_OMON_2026-09-18.xlsx", "TSLA_OMON_2026-09-22.xlsx", "USO_OMON_2026-09-22.xlsx",
             "TSLA_OMON_2026-09-23.xlsx", "USO_OMON_2026-09-23.xlsx",
             f"{SECOND}/TSLA_OMON_2026-09-23.xlsx", f"{SECOND}/USO_OMON_2026-09-23.xlsx",
             f"{LONG}/TSLA_OMON_2026-09-23.xlsx"))

LABELS = tuple(
    [f"table {day} {sym} {cell}" for day, sym in ROWS for cell in CELLS]
    + ["second expiry, both underlyings"]
    + [f"lift {day} {rule}, {feed}" for day in LIFT_DAYS for rule in ("as registered", "Cboe rule")
       for feed in ("free", "Bloomberg")]
    + ["day count blocks", "day count underlyings", "day count contracts", "day count gap, calendar clock",
       "day count gap, trading-day clock", "day count slope", "day count standard error", "day count R2"]
    + ["21 months gap, trading-day clock", "21 months contracts"])

WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen".split())}
COMPARE_HEAD = "matched expiry IV med IV mean IV p90 mid % mid c of sprd sprd free sprd bbg vol free vol bbg"


# ---------------- the page ----------------
def section(page):
    """The Bloomberg section's markup. Raises when the page has none: no section is not 'no figures'."""
    m = re.search(r'<section class="section" id="bloomberg">(.*?)</section>', page, re.S)
    if not m:
        raise ValueError("the page has no Bloomberg section")
    return m.group(1)


def text(markup):
    """Markup as a reader sees it: tags gone, entities resolved, whitespace collapsed, a real minus sign."""
    t = _html.unescape(re.sub(r"<[^>]+>", "", markup)).replace("−", "-")
    return re.sub(r"\s+", " ", t)


def site_figures(page):
    """{label: value as printed} for every figure of the page's Bloomberg section this check compares. The table's
    headings must be the six this check reads, in order: its cells are told apart by their column."""
    sec = section(page)
    head = re.search(r"<thead><tr>(.*?)</tr></thead>", sec, re.S)
    got = tuple(_html.unescape(h) for h in re.findall(r"<th>(.*?)</th>", head.group(1))) if head else ()
    if got != HEADERS:
        raise ValueError(f"the page's Bloomberg table is headed {list(got)}, not {list(HEADERS)}")
    out = {}
    for day, sym, n, inside, puts, calls in re.findall(
            r"<tr><td>(\d{1,2} \w{3})</td><td>([A-Z]+)</td><td>(\d+)</td><td>([\d.]+)\*?</td>"
            r"<td>([\d.]+\*?|–)</td><td>([\d.]+\*?|–)</td></tr>", sec):
        for cell, v in zip(CELLS, (n, inside, puts, calls)):
            label = f"table {day} {sym} {cell}"
            if label in out:
                raise ValueError(f"the page's table lists {day} {sym} twice")
            out[label] = v.rstrip("*")
    t = text(sec)
    m = re.search(r"its second expiry agrees \(([\d.]+) for both underlyings\)", t)
    if m:
        out["second expiry, both underlyings"] = m.group(1)
    a = re.search(r"lifted it by ([\d.]+) volatility points on the free feed and ([\d.]+) on Bloomberg's own "
                  r"prices on 18 September", t)
    b = re.search(r"Under Cboe's rule of discarding such quotes the lifts were ([\d.]+) and ([\d.]+)\.", t)
    c = re.search(r"On 23 September, [^.]*?: ([\d.]+) and ([\d.]+) points as registered, ([\d.]+) and ([\d.]+) "
                  r"under Cboe's rule", t)
    for day, rule, got in (("18 Sep", "as registered", a and a.groups()), ("18 Sep", "Cboe rule", b and b.groups()),
                           ("23 Sep", "as registered", c and c.groups()[:2]), ("23 Sep", "Cboe rule", c and c.groups()[2:])):
        if got:
            out[f"lift {day} {rule}, free"], out[f"lift {day} {rule}, Bloomberg"] = got
    d = re.search(r"Across (\w+) expiry blocks on 15 and 16 September \((\w+) underlyings, (\d+) contracts\) the "
                  r"median gap was ([+-][\d.]+) points on the calendar clock and ([+-][\d.]+) on the trading-day "
                  r"clock, [^.]*?: slope ([\d.]+) \(standard error ([\d.]+)\), R² ([\d.]+)\.", t)
    if d:
        blocks, unders = (WORDS.get(w.lower(), w) for w in d.groups()[:2])
        for label, v in zip(LABELS[-10:-2], (blocks, unders) + d.groups()[2:]):
            out[label] = v
    e = re.search(r"It does not: ([+-][\d.]+) points remain on the trading-day clock \((\d+) contracts\)", t)
    if e:
        out["21 months gap, trading-day clock"], out["21 months contracts"] = e.groups()
    return out


def record_h5(h5_text):
    """(H5b's count, H5a's pooled median, the median where both feeds bid) from the H5 file's corrected reading
    of 17 Oct 2026 - that bullet, not the first reading above it. Raises when the bullet or a figure is gone."""
    t = re.sub(r"\s+", " ", h5_text)
    i = t.find("**Corrected reading, 17 October 2026")
    if i < 0:
        raise ValueError("the H5 file has no corrected reading of 17 October 2026")
    end = t.find(" - **", i + 10)
    blk = t[i:end if end > 0 else len(t)]
    a = re.search(r"\*\*H5a:\*\* pooled median \*\*([\d.]+)\*\*", blk)
    both = re.search(r"on the \*\*\d+\*\* contracts both feeds bid, \*\*([\d.]+)\*\*", blk)
    b = re.search(r"\*\*H5b:\*\* \*\*(\d+) of (\d+)\*\*", blk)
    if not (a and both and b):
        raise ValueError("the H5 file's corrected reading no longer states H5a's medians and H5b's count")
    return f"{b.group(1)} of {b.group(2)}", a.group(1), both.group(1)


def page_vs_record(page, h5_text):
    """Problems, as sentences: H5b's count and H5a's two medians, in the page's narrative AND in its hypothesis
    table, against the H5 file's corrected reading. Needs no export. The record is the reference, so putting both
    passages back to the first reading together still fails (Astra, 11 Nov 2026). A missing sentence, row or
    record is a problem, never a pass."""
    try:
        count, median, both = record_h5(h5_text)
        t = text(section(page))
    except ValueError as e:
        return [str(e)]
    n = re.search(r"had none on Bloomberg either \((\d+ of \d+)\); the wing mids pass the half-spread test at "
                  r"the median \(([\d.]+)\), but only because contracts without bids agree trivially, and on "
                  r"contracts both feeds bid the median is ([\d.]+)\.", t)
    h = re.search(r"H5b holds \((\d+ of \d+)\); H5a holds weakly \(([\d.]+) of a spread", page)
    out = []
    if not n:
        out.append("the Bloomberg narrative no longer states H5b's count and H5a's medians")
    else:
        for what, got, want in (("H5b's count", n.group(1), count), ("H5a's median", n.group(2), median),
                                ("the median where both feeds bid", n.group(3), both)):
            if got != want:
                out.append(f"the narrative gives {what} as {got}; the H5 file's corrected reading says {want}")
    if not h:
        out.append("the hypothesis table's H5 row no longer states H5b's count and H5a's median")
    else:
        for what, got, want in (("H5b's count", h.group(1), count), ("H5a's median", h.group(2), median)):
            if got != want:
                out.append(f"the hypothesis table gives {what} as {got}; the H5 file's corrected reading says {want}")
    return out


# ---------------- the reader's output ----------------
def parse_compare(out):
    """bloomberg_compare.py's report -> {underlying: matched, expiry, of_spread, put_wing, call_wing,
    lift_registered, lift_cboe}. Wing and lift values are None where the report has none (no far strikes that
    day). An underlying printed twice is refused."""
    if COMPARE_HEAD not in re.sub(r"\s+", " ", out):
        raise ValueError("bloomberg_compare's columns are not the ones this check reads")
    got, cur = {}, None
    for line in out.splitlines():
        m = re.match(r"^([A-Z]{1,5})\s+(\d+)\s+(\d{4}-\d{2}-\d{2})((?:\s+[-+]?[\d.]+)+)\s*$", line)
        if m:
            vals = m.group(4).split()
            if len(vals) != 10:
                raise ValueError(f"bloomberg_compare's row for {m.group(1)} has {len(vals)} figures, not 10")
            if m.group(1) in got:
                raise ValueError(f"bloomberg_compare printed {m.group(1)} twice")
            cur = got[m.group(1)] = {"matched": m.group(2), "expiry": m.group(3), "of_spread": vals[5],
                                     "put_wing": None, "call_wing": None, "lift_registered": None, "lift_cboe": None}
            continue
        if cur is None:
            continue
        w = re.match(r"^\s+(put|call) wing\s+n=\d+\s+mid gap ([\d.]+) of a spread", line)
        if w:
            cur[w.group(1) + "_wing"] = w.group(2)
            continue
        lf = re.match(r"^\s+lift, this expiry, (as registered|Cboe zero-bid rule)\s+free ([+-][\d.]+)\s+"
                      r"Bloomberg ([+-][\d.]+)", line)
        if lf:
            cur["lift_registered" if lf.group(1) == "as registered" else "lift_cboe"] = (lf.group(2), lf.group(3))
    return got


def parse_gap(out):
    """model_gap.py's report -> blocks, contracts, gap365, gap252, slope, se, r2 (None without the regression),
    underlyings, rows {(date or None, underlying, expiry): (n, gap365, gap252)}. Raises without a pooled block."""
    p = re.search(r"^POOLED over (\d+) block\(s\), (\d+) contracts:", out, re.M)
    g = re.search(r"median gap on 365 ([+-][\d.]+) vol pts, on 252 ([+-][\d.]+)", out)
    if not (p and g):
        raise ValueError("model_gap printed no pooled block")
    rows = {}
    for line in out.splitlines():
        m = re.match(r"^(?:(\d{4}-\d{2}-\d{2})\s+)?([A-Z]{1,5})\s+(\d{1,2}-\w{3}-\d{2})\s+\d+\s+\d+\s+(\d+)\s+"
                     r"[\d.]+\s+([+-][\d.]+)\s+([+-][\d.]+)\s", line)
        if m:
            key = (m.group(1), m.group(2), m.group(3))
            if key in rows:
                raise ValueError(f"model_gap printed {' '.join(k for k in key if k)} twice")
            rows[key] = (m.group(4), m.group(5), m.group(6))
    s = re.search(r"slope ([\d.]+) \(se ([\d.]+)\)\s+intercept [+-][\d.]+\s+R\^2 ([\d.]+)", out)
    return {"blocks": p.group(1), "contracts": p.group(2), "gap365": g.group(1), "gap252": g.group(2),
            "slope": s.group(1) if s else None, "se": s.group(2) if s else None, "r2": s.group(3) if s else None,
            "underlyings": str(len({k[1] for k in rows})), "rows": rows}


def reader_figures(run):
    """{label: value} from the two tools. run(kind, day, subfolder) -> the tool's output: kind "compare" is
    bloomberg_compare.py for that day; kind "gap" is model_gap.py, day "pool" meaning the 15 and 16 Sep exports
    together. A value of None is 'no figure' (the page shows a dash); a label left out is a figure the reader
    did not print at all. Every figure is taken under its own identity: a row for another expiry is reported as
    such (Astra, 11 Nov 2026), never read under the page's label."""
    out = {}

    def wrong(c, want):
        return None if c["expiry"] == want else f"another expiry ({c['expiry']}, not {want})"

    comp = {iso: parse_compare(run("compare", iso, "")) for iso in sorted(set(DAYS.values()))}
    for day, sym in ROWS:
        c = comp[DAYS[day]].get(sym)
        if c:
            other = wrong(c, EXPIRY[day])
            for cell, v in zip(CELLS, (c["matched"], c["of_spread"], c["put_wing"], c["call_wing"])):
                out[f"table {day} {sym} {cell}"] = other or v
    for day in LIFT_DAYS:
        c = comp[DAYS[day]].get("USO")
        if not c:
            continue
        other = wrong(c, EXPIRY[day])
        for rule, key in (("as registered", "lift_registered"), ("Cboe rule", "lift_cboe")):
            if other:
                out[f"lift {day} {rule}, free"] = out[f"lift {day} {rule}, Bloomberg"] = other
            elif c[key]:
                out[f"lift {day} {rule}, free"], out[f"lift {day} {rule}, Bloomberg"] = c[key]
    second = parse_compare(run("compare", DAYS["23 Sep"], SECOND))
    if "TSLA" in second and "USO" in second:
        a, b = second["TSLA"], second["USO"]
        other = wrong(a, SECOND_EXPIRY) or wrong(b, SECOND_EXPIRY)
        out["second expiry, both underlyings"] = other or (
            a["of_spread"] if a["of_spread"] == b["of_spread"] else
            f"{a['of_spread']} for TSLA and {b['of_spread']} for USO")
    pool = parse_gap(run("gap", "pool", ""))
    blocks = set(pool["rows"])
    if blocks != POOL_BLOCKS:
        odd = sorted(" ".join(str(x) for x in b) for b in blocks ^ POOL_BLOCKS)
        raise ValueError(f"the pooled day-count run did not read exactly the ten blocks of 15 and 16 Sep: {odd}")
    for label, key in zip(LABELS[-10:-2], ("blocks", "underlyings", "contracts", "gap365", "gap252", "slope", "se", "r2")):
        if pool[key] is not None:
            out[label] = pool[key]
    far = parse_gap(run("gap", DAYS["23 Sep"], LONG))["rows"]
    if set(far) == {(None,) + LONG_BLOCK}:
        n, _, g252 = far[(None,) + LONG_BLOCK]
        out["21 months gap, trading-day clock"], out["21 months contracts"] = g252, n
    return out


# ---------------- the comparison ----------------
def same(page_value, reader_value):
    """Is the page's figure the reader's? A dash stands for 'no figure'. Where the reader prints more decimals
    than the page, the page's figure must be the reader's rounded (either way on an exact half); otherwise the
    two must be equal as numbers. A sign may be left off a positive figure, never changed."""
    if reader_value is None or page_value == "–":
        return reader_value is None and page_value == "–"
    try:
        p, r = Decimal(page_value), Decimal(reader_value)
    except InvalidOperation:
        return page_value == reader_value
    dp, dr = -p.as_tuple().exponent, -r.as_tuple().exponent
    if dr <= dp:
        return p == r
    return abs(p - r) <= Decimal(5).scaleb(-(dp + 1))


def differences(page_figures, reader):
    """Sentences, one per figure that is not the same on both sides, in the page's order."""
    out = []
    for label in LABELS:
        on_page, printed = label in page_figures, label in reader
        if on_page and printed and same(page_figures[label], reader[label]):
            continue
        r = reader.get(label)
        out.append(f"{label}: the page says {page_figures[label] if on_page else 'nothing'}, the reader prints "
                   + (("no figure (a dash)" if r is None else r) if printed else "nothing"))
    for label in sorted(set(page_figures) - set(LABELS)):
        out.append(f"{label}: on the page, but not a figure this check compares")
    return out


# ---------------- running the tools on the exports ----------------
def tool_runner(folder, tools=None):
    """run(kind, day, subfolder) on the exports in `folder`. `tools` is the folder holding the two tools (the
    repository's own unless a test says otherwise)."""
    def run(kind, day, sub):
        where = folder / sub if sub else folder
        if kind == "compare":
            return _tool(["bloomberg_compare.py", "--date", day, "--dir", str(where)], (0, 1), tools)
        if day != "pool":
            return _tool(["model_gap.py", "--date", day, "--dir", str(where)], (0,), tools)
        with tempfile.TemporaryDirectory(prefix="volrec-pool-") as td:      # outside the repository
            for d in POOL:
                for f in sorted(where.glob(f"*_OMON_{d}.xlsx")):
                    os.symlink(f, Path(td) / f.name)
            return _tool(["model_gap.py", "--dir", td], (0,), tools)
    return run


def _tool(args, good, tools=None):
    """One tool's output. Always the FIXED reader: VOLREC_BBG_POSITIONAL (the pre-17-Oct reading, kept for
    reproducing old figures) is taken out of the tool's environment, so a shell that has it set cannot make this
    check compare the page with the old reader (Astra, 11 Nov 2026). A failed or silent tool stops the check."""
    env = {k: v for k, v in os.environ.items() if k != "VOLREC_BBG_POSITIONAL"}
    p = subprocess.run([sys.executable, str((tools or ROOT / "tools") / args[0])] + args[1:], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    if p.returncode not in good or not p.stdout.strip():
        raise RuntimeError(f"{args[0]} {' '.join(args[1:3])} failed ({p.returncode}): {(p.stderr or p.stdout)[-300:]}")
    return p.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=str(DEFAULT_DIR), help="folder holding the OMON exports")
    a = ap.parse_args(argv)
    folder = Path(os.path.expanduser(a.dir)).resolve()
    if folder == ROOT or ROOT in folder.parents:
        print("  FAIL  refusing to read exports from inside the repository")
        print("RESULT: INCOMPLETE")
        return 1
    if not folder.is_dir():
        print(f"  SKIP  the Bloomberg exports are not on this machine ({folder}); the page is not compared here")
        return 0
    gone = [n for n in NEEDED if not (folder / n).is_file()]
    if gone:
        for n in gone:
            print(f"  FAIL  export missing: {n}")
        print(f"RESULT: INCOMPLETE - {len(gone)} of the {len(NEEDED)} exports the page's figures come from are missing")
        return 1
    try:
        diff = differences(site_figures(SITE.read_text(encoding="utf-8")), reader_figures(tool_runner(folder)))
    except (ValueError, RuntimeError) as e:
        print(f"  FAIL  {e}")
        print("RESULT: INCOMPLETE - the page or a tool's output was not in the form this check reads")
        return 1
    for d in diff:
        print(f"  FAIL  {d}")
    print(f"RESULT: MISMATCH - {len(diff)} of {len(LABELS)} figures differ" if diff else
          f"RESULT: VERIFIED - all {len(LABELS)} Bloomberg figures on the page are what the reader prints today")
    print(ATTRIBUTION)
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
