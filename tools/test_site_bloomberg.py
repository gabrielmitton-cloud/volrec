"""Known-answer tests for tools/site_bloomberg.py (the public page's Bloomberg figures against the reader).
Synthetic text only, in the real tools' output form and the real page's markup; no export is read.

  python tools/test_site_bloomberg.py
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / "tools")]
import site_bloomberg as SB   # noqa: E402

fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


# ---------------- the reader's output, in bloomberg_compare.py's own form (invented numbers) ----------------
HEAD = ("Bloomberg against the free feed, {d}\n  free feed snapshot   17:55:21 UTC\n"
        "  export file written  18:37:10 UTC (file time, not the pull time)\n\n"
        "       matched      expiry  IV med  IV mean  IV p90   mid %  mid c  of sprd sprd free sprd bbg  vol free  vol bbg\n")
ROW = "{s:<6}{n:>9}  {e}    1.11     0.37    4.47    0.43    5.0     {sp}       4.7      4.8     18112    25614\n"
WING = ("      strikes 108-200 matched; the recorder covers 108-200\n"
        "      parity forward free 154.60, Bloomberg 154.52: -0.05% between snapshots; calls +0.030, puts +0.005 "
        "(free minus Bloomberg, median)\n"
        "      WINGS, 56 wide rows; export reaches 0.03x-2.04x spot\n"
        "        put wing   n=19  mid gap {p} of a spread; zero bid on both 13, free only 0, Bloomberg only 1\n"
        "        call wing  n=9   mid gap {c} of a spread; zero bid on both 0, free only 0, Bloomberg only 0\n"
        "        lift, this expiry, as registered       free {a}  Bloomberg {b}  Bloomberg beyond the cap +65.86\n"
        "        lift, this expiry, Cboe zero-bid rule  free {x}  Bloomberg {y}  Bloomberg beyond the cap +0.14\n")
TAIL = ("on contracts worth 50c or more, then the same gap in cents, then as a fraction of the\n"
        "quoted bid-ask spread, which is the one the checks gate on.\n"
        "  FAIL  USO: the mids differ by 0.61 of a bid-ask spread, over 0.5; that is a feed disagreement, not rounding\n")


def compare_out(day, blocks, expiry="2026-10-16"):
    """blocks: [(sym, matched, of_spread, wing or None)], wing = (put, call, reg free, reg bbg, cboe free, cboe bbg).
    Each day's report carries the expiry the recorder matched: 16 Oct to 22 Sep, 23 Oct on 23 Sep, 30 Oct second."""
    out = HEAD.format(d=day)
    for s, n, sp, w in blocks:
        out += ROW.format(s=s, n=n, sp=sp, e=expiry)
        if w:
            out += WING.format(p=w[0], c=w[1], a=w[2], b=w[3], x=w[4], y=w[5])
    return out + TAIL


C15 = compare_out("2026-09-15", [("SPY", 14, "1.06", None), ("TSLA", 71, "0.41", None), ("USO", 44, "0.61", None)])
C18 = compare_out("2026-09-18", [("USO", 91, "0.21", ("0.05", "0.45", "+5.11", "+4.77", "+0.91", "+0.93"))])
C22 = compare_out("2026-09-22", [("TSLA", 95, "0.81", ("1.00", "1.00", "+1.10", "+1.20", "+1.10", "+1.20")),
                                 ("USO", 118, "0.36", ("0.04", "0.00", "+9.10", "+9.20", "+0.70", "+0.80"))])
C23 = compare_out("2026-09-23", [("TSLA", 83, "0.27", ("0.50", "0.80", "+1.75", "+1.71", "+1.75", "+1.71")),
                                 ("USO", 131, "0.32", ("0.00", "0.17", "+14.11", "+14.22", "+1.13", "+1.27"))],
                  expiry="2026-10-23")
C23B = compare_out("2026-09-23", [("TSLA", 75, "0.22", ("0.33", "0.67", "+1.0", "+1.0", "+1.0", "+1.0")),
                                  ("USO", 54, "0.22", ("0.01", "0.66", "+1.0", "+1.0", "+1.0", "+1.0"))],
                   expiry="2026-10-30")

# ---------------- model_gap.py's own form ----------------
GAP_POOL = """What time base reproduces Bloomberg's own volatility? 2 days, 2026-09-15 to 2026-09-16

date       sym   expiry      cal bus   n    IVM  gap 365  gap 252  gap 252+F  cal div  bus div
2026-09-15 SPY   16-Oct-26    31  23  40   13.5    +0.60    +0.08      +0.08    336.3    249.5
2026-09-15 SPY   30-Oct-26    45  33  40   13.9    +0.61    +0.13      +0.16    338.0    247.9
2026-09-15 TSLA  16-Oct-26    31  23  40   42.1    +1.80    +0.08      +0.04    338.4    251.1
2026-09-15 TSLA  20-Nov-26    66  48  40   44.7    +1.29    +0.13      +0.11    344.5    250.6
2026-09-15 USO   16-Oct-26    31  23  40   54.8    +2.21    -0.07      +0.06    341.7    253.5
2026-09-15 USO   20-Nov-26    66  48  31   53.7    +0.97    -0.42      -0.28    352.0    256.0
2026-09-16 SPY   16-Oct-26    30  22 133   16.2    +0.63    +0.06      -0.06    341.7    250.6
2026-09-16 TSLA  16-Oct-26    30  22  50   43.6    +1.55    -0.08      +0.05    344.8    252.9
2026-09-16 TSLA  20-Nov-26    65  47  50   45.3    +0.99    -0.14      -0.03    350.6    253.5
2026-09-16 USO   16-Oct-26    30  22  76   53.7    +1.89    +0.25      +0.20    340.5    249.7

POOLED over 10 block(s), 540 contracts:
  business-day divisor  median  250.5   p10-p90 244.9-258.7   <- 252 is the convention
  calendar-day divisor  median  341.6   p10-p90 332.9-354.2   <- no fixed value fits
  median gap on 365 +1.12 vol pts, on 252 +0.09

  does the divisor drift with maturity? (it must not, to be a convention; 10 blocks)
    calendar  median  341.7 ( -23.3 from 365)  slope +0.2315/day  t=+3.09   DRIFTS - not a constant
    business  median  250.8 (  -1.2 from 252)  slope +0.0567/day  t=+1.20   flat - consistent with a convention

  the clock predicts the gap with NO fitted parameter (10 blocks)
    predicted = IVM * (sqrt(T_bus/T_cal) - 1), regressed on observed
    slope 1.018 (se 0.128)   intercept +0.09   R^2 0.861   mean |resid| 0.14 pts
    a pure clock effect predicts slope 1.000 and intercept 0.00; t vs 1.0 = +0.05
Bloomberg figures: Source: Bloomberg Finance L.P.
"""
GAP_LONG = """What time base reproduces Bloomberg's own volatility? 2026-09-23

sym   expiry      cal bus   n    IVM  gap 365  gap 252  gap 252+F  cal div  bus div
TSLA  16-Jun-28   632 436 111   48.0    +0.91    +0.92      +1.73    350.0    241.4

POOLED over 1 block(s), 111 contracts:
  business-day divisor  median  241.4   p10-p90 228.9-242.5   <- 252 is the convention
  calendar-day divisor  median  350.0   p10-p90 331.8-351.5   <- no fixed value fits
  median gap on 365 +0.91 vol pts, on 252 +0.92
Bloomberg figures: Source: Bloomberg Finance L.P.
"""
CANNED = {("compare", "2026-09-15", ""): C15, ("compare", "2026-09-18", ""): C18, ("compare", "2026-09-22", ""): C22,
          ("compare", "2026-09-23", ""): C23, ("compare", "2026-09-23", "2026-09-23_30Oct"): C23B,
          ("gap", "pool", ""): GAP_POOL, ("gap", "2026-09-23", "2026-09-23_long"): GAP_LONG}


def run(kind, day, sub):
    return CANNED[(kind, day, sub)]


# ---------------- the page, in index.html's own markup, carrying exactly what the canned reader prints ----------------
def page(rows=None, h5=("44", "44", "0.33"), h5_table=("44 of 44", "0.33"), daycount=None, long_=("+0.92", "111"),
         lifts=("5.11", "4.77", "0.91", "0.93", "14.11", "14.22", "1.13", "1.27"), second="0.22", both="0.67",
         heads=("Day", "Underlying", "Contracts inside ±30%", "Inside ±30%", "Far puts", "Far calls")):
    rows = rows if rows is not None else [
        ("15 Sep", "TSLA", "71", "0.41", "–", "–"), ("15 Sep", "USO", "44", "0.61*", "–", "–"),
        ("18 Sep", "USO", "91", "0.21", "0.05", "0.45"), ("22 Sep", "USO", "118", "0.36", "0.04", "0.00"),
        ("22 Sep", "TSLA", "95", "0.81*", "1.00", "1.00"), ("23 Sep", "USO", "131", "0.32", "0.00", "0.17"),
        ("23 Sep", "TSLA", "83", "0.27", "0.50", "0.80")]
    dc = daycount or ("ten", "three", "540", "+1.12", "+0.09", "1.02", "0.13", "0.86")
    trs = "".join("          <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows)
    return f"""<section class="section" id="gap"><p>Another section, 9.99 of 9.99.</p></section>
  <section class="section" id="bloomberg">
    <h2>Checked against Bloomberg</h2>
    <div class="fig" style="grid-column:1/-1;margin-top:28px">
      <div class="ledger-wrap"><table class="data">
        <thead><tr>{"".join(f"<th>{h}</th>" for h in heads)}</tr></thead>
        <tbody>
{trs}        </tbody>
      </table></div>
      <p class="src">* Over half a spread. On 23 September the two captures were under five minutes apart; the rows show the recorder's nearer expiry, and its second expiry agrees ({second} for both underlyings).</p>
      <div class="src">Source: Bloomberg Finance L.P. Derived aggregates only.</div>
    </div>
    <div class="prose" style="margin-top:28px">
      <p><b>The implied volatilities differ by a day count.</b> Across {dc[0]} expiry blocks on 15 and 16 September ({dc[1]} underlyings, {dc[2]} contracts) the median gap was <span class="m">{dc[3]}</span> points on the calendar clock and <span class="m">{dc[4]}</span> on the trading-day clock, and the clock alone predicts each block's gap with no fitted parameter: slope <span class="m">{dc[5]}</span> (standard error {dc[6]}), R² <span class="m">{dc[7]}</span>. Two later days agree.</p>
      <p>It also has a limit. It does not: <span class="m">{long_[0]}</span> points remain on the trading-day clock ({long_[1]} contracts), and early exercise does not account for them.</p>
      <div class="src">Source: Bloomberg Finance L.P. Derived aggregates only.</div>
    </div>
    <div class="prose" style="margin-top:28px">
      <p><b>The far wings expose the estimator.</b> Adding the strikes beyond ±30% to USO's estimate lifted it by <span class="m">{lifts[0]}</span> volatility points on the free feed and <span class="m">{lifts[1]}</span> on Bloomberg's own prices on 18 September, when a quote with no bid is counted at half its ask. Under Cboe's rule of discarding such quotes the lifts were <span class="m">{lifts[2]}</span> and <span class="m">{lifts[3]}</span>. On 23 September, with the captures minutes apart, USO's far wing gave the same answer: <span class="m">{lifts[4]}</span> and <span class="m">{lifts[5]}</span> points as registered, <span class="m">{lifts[6]}</span> and <span class="m">{lifts[7]}</span> under Cboe's rule. After three matched days, every far-wing contract with no bid on the free feed had none on Bloomberg either (<span class="m">{h5[0]}</span> of <span class="m">{h5[1]}</span>); the wing mids pass the half-spread test at the median (<span class="m">{h5[2]}</span>), but only because contracts without bids agree trivially, and on contracts both feeds bid the median is <span class="m">{both}</span>. (First read otherwise.)</p>
      <div class="src">Source: Bloomberg Finance L.P. Derived aggregates only.</div>
    </div>
  </section>
<script>
      ["H5", "What free option data costs.", "19 Sep 2026", ["tested", "Partly tested"], ["H5e FAILS", "H5b holds ({h5_table[0]}); H5a holds weakly ({h5_table[1]} of a spread; corrected 17 Oct); H5f holds"], "h5.md"],
</script>"""


print("=== the reader's output, parsed ===")
c23 = SB.parse_compare(C23)
check("bloomberg_compare's rows: contracts matched and the median gap in spreads, per underlying",
      (c23["USO"]["matched"], c23["USO"]["of_spread"], c23["TSLA"]["matched"], c23["TSLA"]["of_spread"])
      == ("131", "0.32", "83", "0.27"))
check("each underlying keeps its OWN wing and lift lines (TSLA's come first on 23 Sep, then USO's)",
      (c23["TSLA"]["put_wing"], c23["TSLA"]["call_wing"], c23["USO"]["put_wing"], c23["USO"]["call_wing"])
      == ("0.50", "0.80", "0.00", "0.17")
      and c23["USO"]["lift_registered"] == ("+14.11", "+14.22") and c23["USO"]["lift_cboe"] == ("+1.13", "+1.27")
      and c23["TSLA"]["lift_registered"] == ("+1.75", "+1.71"))
c15 = SB.parse_compare(C15)
check("a day with no far strikes has no wing figure (the page shows a dash), and FAIL lines are not rows",
      c15["TSLA"]["put_wing"] is None and c15["USO"]["call_wing"] is None and set(c15) == {"SPY", "TSLA", "USO"})
g = SB.parse_gap(GAP_POOL)
check("model_gap's pooled block: blocks, contracts, both clocks, the no-parameter regression",
      (g["blocks"], g["contracts"], g["gap365"], g["gap252"], g["slope"], g["se"], g["r2"])
      == ("10", "540", "+1.12", "+0.09", "1.018", "0.128", "0.861"))
check("model_gap's rows: the underlyings counted, and one block's own figures",
      g["underlyings"] == "3" and g["rows"][("2026-09-15", "USO", "20-Nov-26")] == ("31", "+0.97", "-0.42")
      and SB.parse_gap(GAP_LONG)["rows"][(None, "TSLA", "16-Jun-28")] == ("111", "+0.91", "+0.92"))
try:
    SB.parse_gap("What time base reproduces Bloomberg's own volatility?\n\nNo exports found.\n")
    refused = False
except ValueError:
    refused = True
check("output without a pooled block is refused, never read as empty", refused)

print("\n=== the page, parsed ===")
site = SB.site_figures(page())
check("the table: every cell under its day and underlying, the over-half-a-spread star dropped",
      site["table 22 Sep USO contracts"] == "118" and site["table 22 Sep USO far puts"] == "0.04"
      and site["table 15 Sep USO inside"] == "0.61" and site["table 15 Sep TSLA far calls"] == "–"
      and site["table 23 Sep TSLA far puts"] == "0.50")
check("the second expiry, the lifts on both days, the day count in words and numbers, the 21-month block",
      site["second expiry, both underlyings"] == "0.22"
      and site["lift 18 Sep as registered, free"] == "5.11" and site["lift 23 Sep Cboe rule, Bloomberg"] == "1.27"
      and site["day count blocks"] == "10" and site["day count underlyings"] == "3"
      and site["day count contracts"] == "540" and site["day count gap, calendar clock"] == "+1.12"
      and site["day count slope"] == "1.02" and site["day count R2"] == "0.86"
      and site["21 months gap, trading-day clock"] == "+0.92" and site["21 months contracts"] == "111")
try:
    SB.site_figures('<section class="section" id="opra"><p>nothing</p></section>')
    refused = False
except ValueError:
    refused = True
check("a page without the Bloomberg section is refused, never read as having no figures", refused)
real = SB.site_figures((R / "index.html").read_text(encoding="utf-8"))
check(f"the real page yields every figure the checker compares ({len(real)} of {len(SB.LABELS)})",
      set(real) == set(SB.LABELS) and len(SB.LABELS) == 47)

print("\n=== page against reader ===")
reader = SB.reader_figures(run)
check(f"the canned reader gives every figure too ({len(reader)})", set(reader) == set(SB.LABELS))
check("a page that carries exactly what the reader prints has no difference", SB.differences(site, reader) == [])
old_row = [("15 Sep", "TSLA", "71", "0.41", "–", "–"), ("15 Sep", "USO", "44", "0.61*", "–", "–"),
           ("18 Sep", "USO", "91", "0.21", "0.05", "0.45"), ("22 Sep", "USO", "107", "0.36", "0.09", "0.00"),
           ("22 Sep", "TSLA", "95", "0.81*", "1.00", "1.00"), ("23 Sep", "USO", "131", "0.32", "0.00", "0.17"),
           ("23 Sep", "TSLA", "83", "0.27", "0.50", "0.80")]
d = SB.differences(SB.site_figures(page(rows=old_row)), reader)
check("a stale table cell is named with both values (the 17 Oct miss: 107 and 0.09 where the reader prints 118 and 0.04)",
      len(d) == 2 and "table 22 Sep USO contracts: the page says 107, the reader prints 118" in d[0]
      and "table 22 Sep USO far puts: the page says 0.09, the reader prints 0.04" in d[1])
d = SB.differences(SB.site_figures(page(rows=old_row[:-1])), reader)
check("a row missing from the page is a difference, not a shorter comparison",
      any("table 23 Sep TSLA contracts: the page says nothing" in x for x in d))
d = SB.differences(site, {k: v for k, v in reader.items() if k != "21 months contracts"})
check("a figure the reader did not print is a difference, never a silent pass",
      d == ["21 months contracts: the page says 111, the reader prints nothing"])
check("rounding: the page's 1.02 stands for the reader's 1.018; 1.03 does not; equal precision must match exactly",
      SB.same("1.02", "1.018") and not SB.same("1.03", "1.018") and SB.same("0.13", "0.128")
      and not SB.same("0.39", "0.40") and SB.same("5.11", "+5.11") and not SB.same("+1.12", "-1.12")
      and SB.same("–", None) and not SB.same("0.05", None) and not SB.same("–", "0.05"))
d = SB.differences(SB.site_figures(page(daycount=("ten", "three", "546", "+1.15", "+0.09", "1.02", "0.13", "0.86"))), reader)
check("the day-count sentence is checked figure by figure (546 and +1.15 where the reader prints 540 and +1.12)",
      [x.split(":")[0] for x in d] == ["day count contracts", "day count gap, calendar clock"])
d = SB.differences(SB.site_figures(page(second="0.20")), reader)
check("the second-expiry note is checked against BOTH underlyings", len(d) == 1 and "second expiry" in d[0])

print("\n=== the page against the record: H5a and H5b (Astra, 11 Nov: two passages of one page prove nothing) ===")
H5_RECORD = """## Result

- **H5b HOLDS.** Where the free feed shows no bid, Bloomberg shows none on **36 of 36**
  matched wing contracts (100%; bar 80%).
- **H5a HOLDS as specified, and weakly.** Pooled over all 169 contracts the median
  free-feed mid sits **0.40** of Bloomberg's spread away (bar 0.5). On the 132 contracts with a bid on
  both feeds the pooled median is **0.67**, over the bar.
- **Corrected reading, 17 October 2026 - the verdicts above are unchanged and stand as recorded.** The
  independent re-check found a reader bug. Read with every row, and confirmed by a second reader:
  **179** wing contracts (not 169). **H5a:** pooled median **0.33** of Bloomberg's spread (was 0.40; bar
  0.5); by date 0.10, 0.50 and 0.37; 56% inside half a spread; on the **134** contracts both feeds bid,
  **0.67** - unchanged and still over the bar; 45 contracts with no bid on at least one feed. **H5b:** **44
  of 44** (was 36 of 36); one the other way, as before. Both still hold.
- **H5c, H5d:** descriptive.
"""
check("the record's corrected reading is read from its own bullet, not from the first reading above it",
      SB.record_h5(H5_RECORD) == ("44 of 44", "0.33", "0.67"))
check("page, table row and record agree: no problem", SB.page_vs_record(page(), H5_RECORD) == [])
p = SB.page_vs_record(page(h5=("36", "36", "0.33")), H5_RECORD)
check("the narrative's count differs from the record's (36 of 36 against 44 of 44): named",
      len(p) == 1 and "36 of 36" in p[0] and "44 of 44" in p[0] and "narrative" in p[0])
p = SB.page_vs_record(page(h5=("36", "36", "0.40"), h5_table=("36 of 36", "0.40")), H5_RECORD)
check("BOTH passages put back together (narrative and table row at 36 of 36 and 0.40) still fail: the record is the reference",
      len(p) == 4 and sum("narrative" in x for x in p) == 2 and sum("hypothesis table" in x for x in p) == 2)
p = SB.page_vs_record(page(both="0.61"), H5_RECORD)
check("the narrative's both-feeds-bid median is checked too (0.61 against the record's 0.67)",
      len(p) == 1 and "0.61" in p[0] and "0.67" in p[0])
check("a page whose table row or narrative sentence is gone is a problem, not a pass",
      SB.page_vs_record(page().replace("H5b holds (", "H5b held ("), H5_RECORD) != []
      and SB.page_vs_record(page().replace("had none on Bloomberg either", "had none there either"), H5_RECORD) != [])
check("a record without its corrected reading is a problem, never a pass",
      SB.page_vs_record(page(), H5_RECORD.replace("Corrected reading, 17 October 2026", "A later note")) != []
      and SB.page_vs_record(page(), H5_RECORD.replace("**H5b:** **44\n  of 44**", "H5b as before")) != [])
check("the real page states H5a and H5b as the real H5 file's corrected reading does",
      SB.page_vs_record((R / "index.html").read_text(encoding="utf-8"),
                        (R / "hypotheses" / "2026-09-19-h5-wing-quote-quality.md").read_text(encoding="utf-8")) == [])

print("\n=== identities (Astra, 11 Nov: the right numbers under another block's name must not pass) ===")
moved = dict(CANNED)
moved[("compare", "2026-09-22", "")] = C22.replace("2026-10-16", "2026-10-23")
d = SB.differences(site, SB.reader_figures(lambda k, day, sub: moved[(k, day, sub)]))
check("a report for ANOTHER EXPIRY with the same numbers is a difference on every figure of that day",
      len(d) == 8 and all("22 Sep" in x and "another expiry" in x for x in d))
moved = dict(CANNED)
moved[("gap", "2026-09-23", "2026-09-23_long")] = GAP_LONG.replace("16-Jun-28", "18-Dec-26")
d = SB.differences(site, SB.reader_figures(lambda k, day, sub: moved[(k, day, sub)]))
check("the 21-month figures must come from the TSLA 16-Jun-28 block, not from whichever single row is there",
      [x.split(":")[0] for x in d] == ["21 months gap, trading-day clock", "21 months contracts"])
moved = dict(CANNED)
moved[("compare", "2026-09-23", "2026-09-23_30Oct")] = C23B.replace("2026-10-30", "2026-10-23")
d = SB.differences(site, SB.reader_figures(lambda k, day, sub: moved[(k, day, sub)]))
check("the second-expiry note must come from the 30 Oct expiry", len(d) == 1 and "second expiry" in d[0])


def raises(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


check("an underlying listed twice in one report, or a block printed twice, is refused",
      raises(SB.parse_compare, C18 + ROW.format(s="USO", n=91, sp="0.21", e="2026-10-16"))
      and raises(SB.parse_gap, GAP_POOL.replace("2026-09-16 USO   16-Oct-26", "2026-09-15 USO   16-Oct-26")))
moved = dict(CANNED)
moved[("gap", "pool", "")] = GAP_POOL.replace("2026-09-16 ", "2026-09-17 ")
check("the day-count figures must come from 15 and 16 Sep, both and only",
      raises(SB.reader_figures, lambda k, day, sub: moved[(k, day, sub)]))
print("\n=== second review (Astra, 12 Nov): headings, and the pooled blocks' own identities ===")
swapped = ("Day", "Underlying", "Contracts inside ±30%", "Inside ±30%", "Far calls", "Far puts")
check("the table's headings are part of the figures: 'Far puts' and 'Far calls' swapped, values untouched, is refused",
      raises(SB.site_figures, page(heads=swapped)) and not raises(SB.site_figures, page()))
check("a table with a heading renamed or dropped is refused too",
      raises(SB.site_figures, page(heads=swapped[:5])) and raises(SB.site_figures, page().replace("<thead>", "<tbody>", 1)))
for what, bad in (("another underlying under the same numbers (TSLA's blocks printed as QQQ's)", GAP_POOL.replace("TSLA ", "QQQ  ")),
                  ("another expiry under the same numbers", GAP_POOL.replace("2026-09-15 SPY   30-Oct-26", "2026-09-15 SPY   23-Oct-26")),
                  ("a block missing, the rest untouched", "".join(l for l in GAP_POOL.splitlines(True)
                                                                  if not l.startswith("2026-09-16 TSLA  20-Nov-26")))):
    moved = dict(CANNED)
    moved[("gap", "pool", "")] = bad
    check(f"the day count must come from exactly the ten blocks the record names: {what} is refused",
          bad != GAP_POOL and raises(SB.reader_figures, lambda k, day, sub: moved[(k, day, sub)]))

print("\n=== the runner itself (Astra, 11 Nov: exercised, not read) ===")
with tempfile.TemporaryDirectory() as td:
    tools = Path(td) / "tools"
    tools.mkdir()
    (tools / "probe.py").write_text("import os\nprint('reader mode:', os.environ.get('VOLREC_BBG_POSITIONAL', 'unset'))\n")
    (tools / "model_gap.py").write_text(
        "import os, sys\nd = sys.argv[sys.argv.index('--dir') + 1]\n"
        "for n in sorted(os.listdir(d)):\n    print(n, 'link' if os.path.islink(os.path.join(d, n)) else 'FILE',\n"
        "          os.path.exists(os.path.join(d, n)))\n")
    before = os.environ.get("VOLREC_BBG_POSITIONAL")
    os.environ["VOLREC_BBG_POSITIONAL"] = "1"
    try:
        out = SB._tool(["probe.py"], (0,), tools=tools)
    finally:
        if before is None:
            del os.environ["VOLREC_BBG_POSITIONAL"]
        else:
            os.environ["VOLREC_BBG_POSITIONAL"] = before
    check("the historical reader mode never reaches the tools: VOLREC_BBG_POSITIONAL=1 in the parent is not passed on",
          out.strip() == "reader mode: unset")
    ex = Path(td) / "exports"
    ex.mkdir()
    for n in ("SPY_OMON_2026-09-15.xlsx", "USO_OMON_2026-09-16.xlsx", "USO_OMON_2026-09-18.xlsx", "notes.txt"):
        (ex / n).write_text("x")
    out = SB.tool_runner(ex, tools=tools)("gap", "pool", "")
    check("the pooled run sees the 15 and 16 Sep exports only, as links that resolve, never as duplicates",
          out.splitlines() == ["SPY_OMON_2026-09-15.xlsx link True", "USO_OMON_2026-09-16.xlsx link True"])
    try:
        SB._tool(["absent.py"], (0,), tools=tools)
        stopped = False
    except RuntimeError:
        stopped = True
    check("a tool that fails or prints nothing stops the check; its absence is never a pass", stopped)

print("\n=== running it ===")


def main_out(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = SB.main(argv)
    return code, buf.getvalue()


with tempfile.TemporaryDirectory() as td:
    code, out = main_out(["--dir", str(Path(td) / "not-here")])
    check("no exports folder on this machine: SKIP, exit 0, nothing judged",
          code == 0 and "SKIP" in out and "VERIFIED" not in out)
    code, out = main_out(["--dir", td])
    check("an exports folder without the files is a broken setup, not a fresh clone: it fails and names what is missing",
          code == 1 and "USO_OMON_2026-09-18.xlsx" in out and "VERIFIED" not in out and "SKIP" not in out)
code, out = main_out(["--dir", str(R / "data")])
check("a folder inside the repository is refused (licensed files never live here)", code == 1 and "inside the repository" in out)

print("\n=== discipline ===")
src = (R / "tools" / "site_bloomberg.py").read_text(encoding="utf-8")
check("standard library only, and it writes no file", "import requests" not in src and "write_text" not in src
      and "open(" not in src.replace("urlopen(", ""))
check("the exports are linked for the pooled run, never copied", "symlink" in src and "copy" not in src)
check("its output carries Bloomberg's attribution", "Source: Bloomberg Finance L.P." in src)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
