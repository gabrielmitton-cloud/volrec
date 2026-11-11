# SCCUR poster, findings first: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the 48 x 36 in SCCUR poster around graphs of real findings (layout A, classic look), with
the hypothesis list shrunk to a strip of small chips.

**Architecture:** `poster/build_poster.py` keeps reading every number from the project's own records and
readers; a new `poster/charts.py` draws each chart as inline SVG from plain numbers (pure functions). The
page is HTML/CSS rendered to one PDF page by headless Chrome, with the existing render checks.

**Tech Stack:** Python 3.14 stdlib only (framework install), inline SVG, HTML/CSS, Google Chrome headless.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` (never bare `python3`). Stdlib only.
- Every number comes from the project's records or readers, never typed by hand; frozen figures stay copied
  with a comment naming their source file and section.
- Aggregates only; the credit lines stay word for word; the headline, its fallback rule and the AI line are
  unchanged.
- 48 x 36 in, one PDF page (MediaBox 3456 x 2592), smallest text >= 32 CSS px (24 pt), no column overflowing,
  QR code as vector SVG.
- Do not commit, do not push, do not touch files outside the task's list. The controller commits.
- Tests: `.../python3 poster/test_build_poster.py` and `.../python3 poster/test_charts.py`, all green.
- Spec: `docs/superpowers/specs/2026-11-08-sccur-poster-findings-first-design.md`.

Deviation from the default flow, logged: the per-task spec and quality reviews are folded into one round of
four role reviewers on the rendered poster (Task 5) plus the project's Astra review (Task 6), because the
tasks are small and the rendered page is where the problems show.

---

### Task 1: One-run H3 data and the chip strip (data layer)

**Files:**
- Modify: `poster/build_poster.py` (imports; the live readers; replace the table cells with chips)
- Modify: `poster/test_build_poster.py`

**Interfaces:**
- Produces: `PAIRS` (tuple of (symbol, index, description)), `parse_h3(out) -> dict` (adds `"mean"` and
  `"per": {symbol: (T, mean_abs)}`), `run_modelfree() -> str`, `score_saved(out) -> str`,
  `h3_series(out) -> {symbol: [(date, ours, cboe)]}`, `check_series(series, per)`, `h3_live() -> (h3, series)`,
  `h3_tile(h3, today) -> dict`, `chip(...) -> dict`, `h3_chip(h3, today)`, `h5e_chip(h5e)`, `h7_chips(h7)`,
  `scorecard(h3, h5e, h7, today) -> (confirmatory, side)`, `chip_html(c) -> str`, `ICON`, `KIND`.
- Removes: `pill`, `note`, `h3_cells`, `h5e_cells`, `h7_cells`, `test_rows`, `table_html`. `build()` is left
  as it is and is rewritten in Task 3 (it will not run between Task 1 and Task 3; the tests do not call it).

- [ ] **Step 1: Write the failing tests.** In `poster/test_build_poster.py`:

Add after `trading_days`:

```python
def fake_modelfree(days):
    """Text in modelfree.py's row format (date, symbol, ours, cboe, gap, legs, n) for the five benchmarked pairs."""
    lines = ["risk-free (DGS1MO): 3.910%", "date        sym       ours    cboe     gap      legs    n"]
    for i, d in enumerate(days):
        for sym, lvl, g in (("GLD", 25.0, -0.2), ("IWM", 20.0, 0.3), ("QQQ", 21.0, -0.4), ("SPY", 16.0, -0.1),
                            ("USO", 58.0, -1.5)):
            cb, gap = lvl + 0.1 * i, g + 0.01 * (i % 3)
            lines.append(f"{d}  {sym:<5} {cb + gap:10.6f} {cb:10.6f} {gap:+10.6f}   25d/32d   75")
    return "\n".join(lines) + "\n"
```

In `H5eFinal.test_holds`, replace the last four lines (from `measured, verdict = bp.h5e_cells(got)`) with:

```python
        c = bp.h5e_chip(got)
        self.assertEqual((c["kind"], c["verdict"]), ("ok", "holds (final)"))
        self.assertEqual(c["number"], f"{sc['mae']:.2f} (bar < 0.5); closer on {sc['closer']} of {sc['n']} days")
```

In `H5eFinal.test_fails`, replace `self.assertIn('class="pill bad">FAILS', bp.h5e_cells(got)[1])` with:

```python
        c = bp.h5e_chip(got)
        self.assertEqual((c["kind"], c["verdict"]), ("bad", "fails (final)"))
```

Replace the body of `H5eFinal.test_absent_is_due` with:

```python
        self.assertIsNone(bp.h5e_final(base_h5()))
        c = bp.h5e_chip(None)
        self.assertEqual((c["kind"], c["verdict"]), ("bad", "fails (first, 8 Oct)"))
        self.assertIn("0.90", c["number"])                     # only the recorded first verdict, no preview
        self.assertIn("final due 12–19 Nov", c["number"])
```

In `H7Reading.test_holds`, replace the five lines from `measured, verdict = bp.h7_cells(got)` with:

```python
        a, b = bp.h7_chips(got)
        self.assertEqual((a["id"], a["kind"], a["verdict"]), ("H7a", "ok", "holds"))
        self.assertEqual(a["number"], "USO 0.112, GLD 0.087 (bar ≤ 0.25)")
        self.assertEqual((b["id"], b["kind"], b["number"]), ("H7b", "ok", "0.214 (bar ≤ 0.30)"))
```

In `H7Reading.test_fails`, replace the three lines from `verdict = bp.h7_cells(got)[1]` with:

```python
        a, b = bp.h7_chips(got)
        self.assertEqual((a["kind"], b["kind"]), ("bad", "bad"))
```

In `H7Reading.test_below_minimum_is_not_a_verdict`, replace the last line with:

```python
        a = bp.h7_chips(got)[0]
        self.assertEqual(a["kind"], "due")
        self.assertTrue(a["verdict"].startswith("not read"))
```

Replace the body of `H7Reading.test_absent_is_due` with:

```python
        self.assertIsNone(bp.h7_reading(base_h7()))
        a, b = bp.h7_chips(None)
        self.assertEqual((a["kind"], a["verdict"], a["number"]), ("due", "due 12–19 Nov", "bar ≤ 0.25"))
        self.assertEqual((b["kind"], b["verdict"], b["number"]), ("due", "due 12–19 Nov", "bar ≤ 0.30"))
```

In `H3Box.test_parse_scorer_report`, add at the end:

```python
        self.assertEqual(set(got["per"]), {"GLD", "IWM", "QQQ", "SPY", "USO"})
        self.assertTrue(all(n > 10 and m > 0 for n, m in got["per"].values()))
        self.assertLess(got["mean"], 0)
```

Replace `H3Box.test_so_far_then_of_record` with:

```python
    def test_so_far_then_of_record(self):
        h3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS", "mean": -0.31}
        before, after = bp.h3_chip(h3, date(2026, 11, 11)), bp.h3_chip(h3, date(2026, 11, 12))
        self.assertEqual((before["kind"], before["verdict"]), ("ok", "holds so far"))
        self.assertEqual(after["verdict"], "holds")
        self.assertEqual(before["number"], "0.45 over 125 readings (bar < 1.0)")
        t = bp.h3_tile(h3, date(2026, 11, 11))
        self.assertEqual((t["a"], t["b"], t["c"], t["mean"]), ("holds so far", "holds so far", "holds so far", "−0.31"))
        self.assertNotIn("so far", " ".join(str(v) for v in bp.h3_tile(h3, date(2026, 11, 12)).values()))
```

In `H3Box.test_malformed_raises`, add one more broken form to the tuple:

```python
                       "\n".join(l for l in rep.splitlines() if "T=" not in l),
```

Replace the `Table` class with:

```python
class Scorecard(unittest.TestCase):
    H3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS", "mean": -0.31}

    def test_every_status_table_hypothesis_is_on_the_poster(self):
        status = (ROOT / "hypotheses/README.md").read_text().split("## Status", 1)[1]
        ids = {line.split("|")[1].strip() for line in status.splitlines() if line.startswith("| H")}
        conf, side = bp.scorecard(self.H3, None, None, date(2026, 10, 21))
        shown = " ".join(c["id"] for c in conf + side)
        for h in sorted(ids):
            self.assertIn(h, shown, f"{h} is in hypotheses/README.md's status table but not on the poster")
        self.assertEqual(conf[0]["id"], "H3")                         # confirmatory first, side studies apart
        self.assertIn("H1", [c["id"] for c in side])

    def test_every_chip_is_complete_and_never_colour_alone(self):
        conf, side = bp.scorecard(self.H3, None, None, date(2026, 10, 21))
        for c in conf + side:
            self.assertIn(c["kind"], bp.ICON)
            self.assertTrue(all(c[k] for k in ("id", "claim", "verdict", "number")), c)
            html_ = bp.chip_html(c)
            self.assertIn(bp.ICON[c["kind"]], html_)                   # an icon and a word, not colour alone
            self.assertIn(c["verdict"], html_)


class H3Series(unittest.TestCase):
    DAYS = trading_days("2026-11-02", "2026-11-13")                    # crosses the 11 Nov cut

    def per(self, out):
        import h3_scorer as hs
        return bp.parse_h3(hs.report(hs.score(hs.parse(out))))["per"]

    def test_series_is_the_scorers_rows_to_11_nov(self):
        s = bp.h3_series(fake_modelfree(self.DAYS))
        self.assertEqual(set(s), {"GLD", "IWM", "QQQ", "SPY", "USO"})
        self.assertEqual(s["SPY"][-1][0], "2026-11-11")               # 12 and 13 Nov come after the reading of record
        self.assertEqual(len(s["SPY"]), len([d for d in self.DAYS if d <= "2026-11-11"]))
        _, ours, cboe = s["USO"][0]
        self.assertAlmostEqual(ours - cboe, -1.5, places=6)           # ours = Cboe + gap

    def test_chart_and_scorer_agree(self):
        out = fake_modelfree(self.DAYS)
        bp.check_series(bp.h3_series(out), self.per(out))             # no exception

    def test_a_different_run_stops_the_build(self):
        out = fake_modelfree(self.DAYS)
        per = self.per(out)
        moved = bp.h3_series(out)
        d, ours, cboe = moved["GLD"][0]
        moved["GLD"][0] = (d, ours + 0.5, cboe)                       # one reading half a point off
        with self.assertRaises(bp.Unrecognised):
            bp.check_series(moved, per)
        short = bp.h3_series(out)
        short["SPY"] = short["SPY"][:-1]                              # one reading missing
        with self.assertRaises(bp.Unrecognised):
            bp.check_series(short, per)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 poster/test_build_poster.py`
Expected: errors such as `AttributeError: module 'build_poster' has no attribute 'h5e_chip'`.

- [ ] **Step 3: Implement.** In `poster/build_poster.py`:

Add `import tempfile` to the imports, and after `from record_verdict import ...` add:

```python
import h3_scorer as hs  # noqa: E402  (the frozen H3 scorer: its parse is the chart's row reader)
```

After the `DUE = ...` line add:

```python
CHIP_DUE = "due 12–19 Nov"
ENV = {"FRED_KEY": "use-cache", "PATH": "/usr/bin:/bin"}
# The five benchmarked pairs (tools/h3_scorer.py BENCH), in the main chart's order.
PAIRS = (("SPY", "VIX", "S&P 500"), ("QQQ", "VXN", "Nasdaq-100"), ("IWM", "RVX", "Russell 2000"),
         ("GLD", "GVZ", "gold"), ("USO", "OVX", "crude oil"))
```

Replace the block from `H3_LINE_A = ...` through the end of `h3_live()` with:

```python
H3_LINE_A = re.compile(r"^H3a (HOLDS|FAILS): pooled mean \|gap\| ([\d.]+) vs bar under 1\.0 "
                       r"\((\d+) readings over (\d+) days\)", re.M)
H3_LINE_B = re.compile(r"^H3b (HOLDS|FAILS): pooled mean gap ([+-][\d.]+) \(registered: negative\)", re.M)
H3_LINE_C = re.compile(r"^H3c (HOLDS|FAILS): pooled slope of \|gap\| on the index level", re.M)
H3_PER = re.compile(r"^\s+([A-Z]{3})\s+T=\s*(\d+)\s+mean \|gap\| ([\d.]+)\s", re.M)


def parse_h3(out):
    """tools/h3_scorer.py's report -> dict. Raises Unrecognised if any registered line is missing."""
    if f"readings to {H3_RECORD_DAY.isoformat()}" not in out:
        raise Unrecognised("h3_scorer.py no longer reads to 2026-11-11 - the poster will not guess:\n" + out)
    a, b, c = H3_LINE_A.search(out), H3_LINE_B.search(out), H3_LINE_C.search(out)
    per = {m[1]: (int(m[2]), float(m[3])) for m in H3_PER.finditer(out)}
    if not (a and b and c) or set(per) != {p[0] for p in PAIRS}:
        raise Unrecognised("h3_scorer.py output not recognised - the poster will not guess:\n" + out)
    return {"verdict": a[1], "mae": float(a[2]), "n": int(a[3]), "days": int(a[4]), "b": b[1],
            "mean": float(b[2]), "c": c[1], "per": per}


def run_modelfree():
    """One registered, full-precision modelfree.py run: the command tools/h3_scorer.py runs itself."""
    p = subprocess.run([sys.executable, str(ROOT / "modelfree.py"), "--precise"], cwd=ROOT,
                       capture_output=True, text=True, env=ENV)
    if p.returncode != 0:
        raise SystemExit(f"modelfree.py failed ({p.returncode}): {p.stderr[-500:]}")
    return p.stdout


def score_saved(out):
    """The frozen scorer on that saved output (h3_scorer.py --file), with its own rate check and precision rule."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "modelfree.txt"
        f.write_text(out)
        p = subprocess.run([sys.executable, str(ROOT / "tools/h3_scorer.py"), "--file", str(f)], cwd=ROOT,
                           capture_output=True, text=True, env=ENV)
    return p.stdout + p.stderr


def h3_series(out):
    """{symbol: [(date, ours, cboe)]} for the five pairs, read with the scorer's own parse: the rows it scores,
    to 11 Nov 2026. ours = Cboe + gap, as modelfree.py defines the gap."""
    series = {}
    for d, sym, cboe, gap in hs.parse(out, H3_RECORD_DAY.isoformat()):
        series.setdefault(sym, []).append((d, cboe + gap, cboe))
    return series


def check_series(series, per):
    """The chart and the printed numbers must come from the same run: for each pair the number of readings
    and the mean |gap| (to the scorer's three printed decimals) agree, or the build stops."""
    for sym, _, _ in PAIRS:
        rows = series.get(sym, [])
        n, mae = per[sym]
        got = sum(abs(o - c) for _, o, c in rows) / len(rows) if rows else float("nan")
        if len(rows) != n or not abs(got - mae) <= 0.0005 + 1e-9:
            raise Unrecognised(f"{sym}: the chart has {len(rows)} readings with mean |gap| {got:.4f}; the scorer "
                               f"printed {n} and {mae:.3f} - the poster will not draw a different run")


def h3_live():
    """H3: the frozen scorer's report on one saved modelfree.py run, and that run's daily series."""
    out = run_modelfree()
    h3 = parse_h3(score_saved(out))
    series = h3_series(out)
    check_series(series, h3["per"])
    return h3, series
```

Replace the whole `# ---------------- table cells ----------------` section (from `def esc(s):` through the end
of `table_html`) with:

```python
# ---------------- the chips (the strip of every registered test) ----------------
def esc(s):
    return html.escape(str(s), quote=False)


KIND = {"HOLDS": "ok", "FAILS": "bad"}
ICON = {"ok": "✓", "bad": "✗", "due": "…", "na": "–"}


def chip(hid, claim, kind, verdict, number):
    return {"id": hid, "claim": claim, "kind": kind, "verdict": verdict, "number": number}


def so_far(today):
    return "" if today > H3_RECORD_DAY else " so far"


def h3_chip(h3, today):
    """H3 in the scorer's words: 'so far' until 11 Nov 2026, the reading of record after it."""
    return chip("H3", "Free data tracks Cboe's index", KIND.get(h3["verdict"], "due"),
                h3["verdict"].lower() + so_far(today), f'{h3["mae"]:.2f} over {h3["n"]} readings (bar < 1.0)')


def h3_tile(h3, today):
    """The summary tile beside the five panels: the pooled numbers and the three registered parts."""
    record = today > H3_RECORD_DAY
    return {"mae": f'{h3["mae"]:.2f}', "n": h3["n"], "days": h3["days"],
            "a": h3["verdict"].lower() + so_far(today), "b": h3["b"].lower() + so_far(today),
            "c": h3["c"].lower() + so_far(today), "mean": f'{h3["mean"]:+.2f}'.replace("-", "−"),
            "label": "Reading of record, to 11 Nov" if record else "To date; the reading of record is 11 Nov"}


def h5e_chip(h5e):
    """H5e: the recorded first verdict (8 Oct: FAILS, 0.90) until the FINAL block exists; then the final."""
    claim = "Skipping empty bids fixes oil"
    if h5e is None:
        # H5 file, Result: first verdict FAILS, 0.90, closer on 2 of 10 days.
        return chip("H5e", claim, "bad", "fails (first, 8 Oct)", "0.90 (bar < 0.5); final due 12–19 Nov")
    return chip("H5e", claim, KIND[h5e["verdict"]], h5e["verdict"].lower() + " (final)",
                f'{h5e["mae"]} (bar < 0.5); closer on {h5e["closer"]} of {h5e["n"]} days')


def h7_chips(h7):
    """H7a and H7b: due until record_verdict.py's block exists; then its words and numbers. A part below its
    minimum reads NOT READ, which is not a failure."""
    a, b = ("H7a", "Free feed equals full market"), ("H7b", "Gold's estimate matches GVZ")
    if h7 is None:
        return [chip(*a, "due", CHIP_DUE, "bar ≤ 0.25"), chip(*b, "due", CHIP_DUE, "bar ≤ 0.30")]
    return [chip(*a, KIND.get(h7["a"].split()[0], "due"), h7["a"].lower(),
                 f'USO {h7["uso"]}, GLD {h7["gld"]} (bar ≤ 0.25)'),
            chip(*b, KIND.get(h7["b"].split()[0], "due"), h7["b"].lower(), f'{h7["gvz"]} (bar ≤ 0.30)')]


def scorecard(h3, h5e, h7, today):
    """Every hypothesis in hypotheses/README.md's status table as a chip: (confirmatory, side studies)."""
    confirmatory = [
        h3_chip(h3, today),
        # H5 file, Result (corrected 17 Oct): 0.33 over 179 (bar 0.5); 0.67 on the 134 both feeds bid; "holds weakly".
        chip("H5a", "Far quotes near Bloomberg's", "ok", "holds, weakly", "0.33 of a spread (bar 0.5)"),
        # H5 file, Result (corrected 17 Oct): 44 of 44 (bar 80%).
        chip("H5b", "Empty bids are empty there too", "ok", "holds", "44 of 44 (bar 80%)"),
        # H5 file, "H5f, read 25 September 2026": a 0.500 (ON the bar 0.5), b 64 of 64, c 0.6% (bar 25%).
        chip("H5f", "The same, on the full market", "ok", "holds", "0.500 (on the bar); 64 of 64"),
        # H5 file, Result: H5c, H5d descriptive until their 10 underlying-days support the date-clustered test.
        chip("H5c–d", "Inflation repeats on Bloomberg", "na", "not yet tested", "too few dates"),
        h5e_chip(h5e),
        *h7_chips(h7),
    ]
    side = [
        # H1 file, Result: H1a 9 of 11 pairs, all surviving Benjamini-Hochberg; H1b mixed; H1c holds.
        chip("H1", "The known risk premium, 10 years", "ok", "holds", "9 of 11 pairs"),
        # H2 file, Result; 28 Oct companion (Actions run 40720872275): clustered on date, raw variance p 0.18.
        chip("H2a", "The premium, in variance", "ok", "holds as recorded", "by date p 0.18: not robust"),
        # H2 file, Result: H2b not supported; on its registered statistic, log lower on 3 of 11 pairs.
        chip("H2b", "Variance less autocorrelated", "bad", "not supported", "3 of 11 pairs"),
        # H4 file / hypotheses README: registered 13 Sep, not yet tested; about 40 day pairs needed.
        chip("H4", "Hedged option gains negative", "na", "not yet tested", "needs ~40 day pairs"),
        # H6 file, Result: implied vol has the lower error in 0 of 9 pairs (bar: at least 7 of 9).
        chip("H6a", "Implied vol beats a 14-day average", "bad", "fails", "0 of 9 pairs (bar 7)"),
        # H6 file, Result: mean d +0.33 after spikes vs +0.42 calm; Welch p < 0.0001; Newey-West p < 0.01.
        chip("H6b", "Its miss shrinks after spikes", "ok", "holds", "0.33 vs 0.42, p < 0.01"),
    ]
    return confirmatory, side


def chip_html(c):
    return (f'<div class="chip {c["kind"]}"><div class="ch"><b>{esc(c["id"])}</b>'
            f'<span class="vd">{ICON[c["kind"]]} {esc(c["verdict"])}</span></div>'
            f'<div class="cl">{esc(c["claim"])}</div><div class="cn">{esc(c["number"])}</div></div>')
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 poster/test_build_poster.py`
Expected: `OK` (24 tests: the 19, less the 1 replaced table test, plus 2 scorecard and 3 series tests, and one
renamed in place). `grep -n "h3_cells\|h5e_cells\|h7_cells\|test_rows\|table_html\|def pill\|def note" poster/*.py`
prints only lines inside `build()`.

---

### Task 2: The charts module

**Files:**
- Create: `poster/charts.py`
- Create: `poster/test_charts.py`

**Interfaces:**
- Produces: `NAVY`, `ORANGE`, `MIN_FONT`, `nice_step(span, ticks=4)`, `daily_panel(sym, index, what, rows,
  mae, w=940, h=560) -> str`, `band_sd(band, vol, days=30)`, `band_coverage(band, vol, days=30)`,
  `lognormal_pdf(r, vol, days=30)`, `coverage_curves(calm, wild, band=0.10, w=1300, h=600) -> str`,
  `band_bars(bands, w=1300) -> str`, `quote_scale(points, bar, w=1300) -> str`. Every function returns one
  `<svg class="chart" viewBox="0 0 w h" role="img" aria-label="...">`; one unit is one CSS px.

- [ ] **Step 1: Write the failing tests** in `poster/test_charts.py`:

```python
"""Tests for poster/charts.py: geometry stays inside each chart, no text below the poster's 24 pt floor,
text unlikely to run past the edge, and the bell-curve numbers agree with the README. Stdlib only.

    .../python3 poster/test_charts.py
"""
import html
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts  # noqa: E402

VB = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')
FONT = re.compile(r'font-size="([\d.]+)"')
XY = re.compile(r'\b(?:x|x1|x2|cx)="(-?[\d.]+)"|\b(?:y|y1|y2|cy)="(-?[\d.]+)"')
PATH = re.compile(r' d="([^"]+)"')
TEXT = re.compile(r'<text x="(-?[\d.]+)" y="[^"]*" [^>]*font-size="([\d.]+)"[^>]*text-anchor="(\w+)">([^<]*)</text>')


def check_svg(case, svg):
    """Every font >= 32 px; every coordinate and path point inside the viewBox; text likely inside it too
    (half an em per character, a lenient estimate for Inter)."""
    w, h = map(float, VB.search(svg).groups())
    sizes = [float(s) for s in FONT.findall(svg)]
    case.assertTrue(sizes, "no text at all")
    case.assertGreaterEqual(min(sizes), charts.MIN_FONT)
    for xs, ys in XY.findall(svg):
        if xs:
            case.assertTrue(-0.5 <= float(xs) <= w + 0.5, f"x {xs} outside 0..{w}")
        if ys:
            case.assertTrue(-0.5 <= float(ys) <= h + 0.5, f"y {ys} outside 0..{h}")
    for d in PATH.findall(svg):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
        for x, y in zip(nums[0::2], nums[1::2]):
            case.assertTrue(-0.5 <= x <= w + 0.5 and -0.5 <= y <= h + 0.5, f"path point {x},{y} outside")
    for x, size, anchor, s in TEXT.findall(svg):
        x, width = float(x), 0.5 * float(size) * len(html.unescape(s))
        lo, hi = {"start": (x, x + width), "end": (x - width, x), "middle": (x - width / 2, x + width / 2)}[anchor]
        case.assertTrue(lo >= -2 and hi <= w + 2, f"text {s!r} likely runs outside ({lo:.0f}..{hi:.0f} of {w:.0f})")


ROWS = [("2026-09-14", 16.9, 17.1), ("2026-09-30", 15.9, 16.3), ("2026-10-01", 16.3, 16.4),
        ("2026-10-30", 21.4, 19.4), ("2026-11-02", 20.6, 21.2), ("2026-11-11", 24.3, 28.2)]
BANDS = [("±10%", 20, 3.97, -12.37, "USO"), ("±20%", 30, 1.31, -4.39, None), ("±30%", 40, 0.59, -1.84, "USO")]
POINTS = [("Against Bloomberg, all far strikes (179)", 0.33, "0.33", False),
          ("Against the full market (OPRA), all far strikes (466)", 0.5, "0.500", False),
          ("Where both feeds show a bid (Bloomberg, 134)", 0.67, "0.67", True)]


class Steps(unittest.TestCase):
    def test_nice_step(self):
        self.assertEqual(charts.nice_step(14.2), 5)
        self.assertEqual(charts.nice_step(6.1), 2)
        self.assertEqual(charts.nice_step(1.0), 0.25)

    def test_text_below_the_floor_refuses(self):
        with self.assertRaises(ValueError):
            charts.text(0, 0, "tiny", 24)


class DailyPanel(unittest.TestCase):
    def test_draws_both_lines_and_the_gap_inside_the_frame(self):
        s = charts.daily_panel("SPY", "VIX", "S&P 500", ROWS, 0.446)
        check_svg(self, s)
        self.assertIn("SPY vs VIX", s)
        self.assertIn("S&amp;P 500 · off by 0.45 on average", s)
        self.assertIn(f'stroke="{charts.NAVY}"', s)
        self.assertIn(f'stroke="{charts.ORANGE}"', s)
        self.assertIn('stroke-dasharray="14 9"', s)                      # never colour alone
        self.assertEqual(s.count('fill-opacity="0.16"'), 1)              # the gap, shaded once

    def test_a_month_label_where_each_month_starts(self):
        s = charts.daily_panel("SPY", "VIX", "S&P 500", ROWS, 0.446)
        self.assertEqual(re.findall(r">(Sep|Oct|Nov)<", s), ["Sep", "Oct", "Nov"])

    def test_flat_and_single_reading_series(self):
        check_svg(self, charts.daily_panel("GLD", "GVZ", "gold", [("2026-10-01", 22.0, 22.0)] * 3, 0.0))
        check_svg(self, charts.daily_panel("GLD", "GVZ", "gold", [("2026-10-01", 22.0, 22.4)], 0.4))

    def test_empty_refuses(self):
        with self.assertRaises(ValueError):
            charts.daily_panel("GLD", "GVZ", "gold", [], 0.0)


class Coverage(unittest.TestCase):
    def test_band_in_standard_deviations(self):
        self.assertEqual(f"{charts.band_sd(0.10, 0.16):.1f}", "2.2")
        self.assertEqual(f"{charts.band_sd(0.10, 0.59):.1f}", "0.6")

    def test_share_of_moves_inside_the_band(self):
        self.assertEqual(f"{charts.band_coverage(0.10, 0.16):.0%}", "97%")
        self.assertEqual(f"{charts.band_coverage(0.10, 0.59):.0%}", "45%")

    def test_density_integrates_to_one_with_no_drift(self):
        step = 0.0005
        grid = [-0.9995 + i * step for i in range(int(4.0 / step))]
        for vol in (0.16, 0.59):
            mass = sum(charts.lognormal_pdf(r, vol) for r in grid) * step
            mean = sum(r * charts.lognormal_pdf(r, vol) for r in grid) * step
            inside = sum(charts.lognormal_pdf(r, vol) for r in grid if -0.10 <= r <= 0.10) * step
            self.assertAlmostEqual(mass, 1.0, places=3)
            self.assertAlmostEqual(mean, 0.0, places=3)
            self.assertAlmostEqual(inside, charts.band_coverage(0.10, vol), places=2)

    def test_chart(self):
        s = charts.coverage_curves(("S&P 500", 0.16), ("Crude oil", 0.59))
        check_svg(self, s)
        for t in ("S&amp;P 500 (volatility 16)", "Crude oil (volatility 59)", "band sees 97% of moves",
                  "band sees 45% of moves", "±10% strike band"):
            self.assertIn(t, s)
        self.assertEqual(s.count('fill-opacity="0.3"'), 2)               # oil's two tails beyond the band


class BandBars(unittest.TestCase):
    def test_bars(self):
        s = charts.band_bars(BANDS)
        check_svg(self, s)
        self.assertEqual(s.count(f'fill="{charts.ORANGE}"'), 1)          # the widest band, highlighted
        for t in ("3.97", "1.31", "0.59", "worst: USO −12.37", "worst −4.39", "40 strikes"):
            self.assertIn(t, s)
        widths = [float(v) for v in re.findall(r'<rect [^>]*width="([\d.]+)"', s)]
        self.assertEqual(widths, sorted(widths, reverse=True))           # a longer bar is a bigger gap


class QuoteScale(unittest.TestCase):
    def test_scale(self):
        s = charts.quote_scale(POINTS, 0.5)
        check_svg(self, s)
        cx = [float(v) for v in re.findall(r'<circle cx="([\d.]+)"', s)]
        self.assertEqual(len(cx), 3)
        self.assertTrue(cx[0] < cx[1] < cx[2])
        bar_x = {float(v) for v in re.findall(r'<line x1="([\d.]+)" x2="\1"', s)}
        self.assertEqual(bar_x, {cx[1]})                                 # 0.500 sits ON the bar
        self.assertEqual(s.count('fill="#fff"'), 1)                      # one hollow dot: the caveat row
        self.assertIn("the bar, set first: 0.5", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 poster/test_charts.py`
Expected: `ModuleNotFoundError: No module named 'charts'`.

- [ ] **Step 3: Implement** `poster/charts.py`:

```python
"""The SCCUR poster's charts, drawn as inline SVG (vector, so the print stays sharp at 48 x 36 in).

Pure functions: numbers in, an <svg> string out. Nothing here reads a file or runs a program;
poster/build_poster.py passes in the project's own numbers. Each chart is drawn at the size the page shows
it, one viewBox unit per CSS pixel (96 per inch), so a font-size here is the printed size: 32 px is 24 pt,
the poster's floor, and text() refuses anything smaller.
"""
import html
import math

NAVY, ORANGE, INK, MUTE, RULE, BAND, BAR = "#0b2447", "#e35205", "#14213d", "#4f5a6d", "#d3d9e3", "#e9eef6", "#6f8fc2"
SANS = "Inter, system-ui, sans-serif"
HEAD = "'Inter Tight', Inter, system-ui, sans-serif"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MIN_FONT = 32


def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, size, *, weight=400, fill=INK, anchor="start", family=SANS):
    """One SVG text element; size in CSS px, never below the poster's floor."""
    if size < MIN_FONT:
        raise ValueError(f"text {s!r} at {size}px is below the poster's {MIN_FONT}px floor")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def svg(w, h, label, body):
    return f'<svg viewBox="0 0 {w} {h:.0f}" class="chart" role="img" aria-label="{esc(label)}">{body}</svg>'


def nice_step(span, ticks=4):
    """A round gridline step (1, 2, 2.5 or 5 times a power of ten) giving about `ticks` intervals at most."""
    raw = max(span, 1e-9) / ticks
    mag = 10 ** math.floor(math.log10(raw))
    return next(k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw * (1 - 1e-12))


def daily_panel(sym, index, what, rows, mae, w=940, h=560):
    """One fund, every reading: Cboe's published close (navy, solid), the free-data estimate (orange, dashed)
    and the gap between them (orange, light), on the fund's own volatility scale, with month labels.

    rows: [(date 'YYYY-MM-DD', ours, cboe)] in date order. mae: the frozen scorer's mean |gap| for this fund,
    printed in the subtitle (the build has already checked it against these rows)."""
    if not rows:
        raise ValueError(f"{sym}: nothing to draw")
    L, R, T, B = 92, 18, 128, 58
    vals = [v for _, o, c in rows for v in (o, c)]
    step = nice_step((max(vals) - min(vals)) or 1.0)
    lo, hi = math.floor(min(vals) / step) * step, math.ceil(max(vals) / step) * step
    if hi - lo < step:
        hi = lo + step
    n = len(rows)

    def x(i):
        return L + (w - L - R) * (i / (n - 1) if n > 1 else 0.5)

    def y(v):
        return T + (hi - v) * (h - T - B) / (hi - lo)

    out = [text(0, 46, f"{sym} vs {index}", 46, weight=700, family=HEAD),
           text(0, 94, f"{what} · off by {mae:.2f} on average", 34, fill=MUTE)]
    k = 0
    while lo + k * step <= hi + step * 1e-9:
        v = lo + k * step
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{RULE}" stroke-width="2"/>')
        out.append(text(L - 14, y(v) + 11, f"{v:.0f}" if step >= 1 else f"{v:.1f}", 32, fill=MUTE, anchor="end"))
        k += 1
    month = None
    for i, (d, _, _) in enumerate(rows):
        m = int(d[5:7])
        if m != month:
            month = m
            out.append(text(x(i), h - 12, MONTHS[m - 1], 32, fill=MUTE,
                            anchor="start" if x(i) < w - R - 80 else "end"))
    fwd = [f"{x(i):.1f} {y(r[1]):.1f}" for i, r in enumerate(rows)]
    back = [f"{x(i):.1f} {y(r[2]):.1f}" for i, r in reversed(list(enumerate(rows)))]
    out.append(f'<path d="M{" L".join(fwd + back)} Z" fill="{ORANGE}" fill-opacity="0.16"/>')
    out.append(f'<path d="M{" L".join(back[::-1])}" fill="none" stroke="{NAVY}" stroke-width="5" '
               'stroke-linejoin="round" stroke-linecap="round"/>')
    out.append(f'<path d="M{" L".join(fwd)}" fill="none" stroke="{ORANGE}" stroke-width="5" '
               'stroke-dasharray="14 9" stroke-linejoin="round"/>')
    return svg(w, h, f"{sym} against {index}: the free-data estimate is off by {mae:.2f} points on average",
               "".join(out))


def band_sd(band, vol, days=30):
    """Standard deviations of a `days`-day price move spanned by a ±band of strikes (vol annual, as 0.16)."""
    return band / (vol * math.sqrt(days / 365))


def lognormal_pdf(r, vol, days=30):
    """Density of the `days`-day price change r = S_T/S_0 - 1 under a driftless lognormal (E[S_T] = S_0)."""
    if r <= -1:
        return 0.0
    s = vol * math.sqrt(days / 365)
    z = (math.log1p(r) + s * s / 2) / s
    return math.exp(-z * z / 2) / ((1 + r) * s * math.sqrt(2 * math.pi))


def band_coverage(band, vol, days=30):
    """Share of `days`-day price moves inside ±band under the same lognormal: how much the band sees."""
    s = vol * math.sqrt(days / 365)

    def cdf(z):
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    return cdf((math.log1p(band) + s * s / 2) / s) - cdf((math.log1p(-band) + s * s / 2) / s)


def coverage_curves(calm, wild, band=0.10, w=1300, h=600):
    """Two 30-day price-move curves on one scale with the same ±band of strikes shaded; the wild curve's
    tails beyond the band (what a fixed band cannot price) filled orange. A model, not market data.
    calm, wild: (name, annual vol), e.g. ("S&P 500", 0.16), ("Crude oil", 0.59)."""
    L, R, T, B, span = 20, 20, 150, 66, 0.5
    xs = [-span + i * 2 * span / 400 for i in range(401)]
    top = max(lognormal_pdf(r, calm[1]) for r in xs) * 1.04

    def X(r):
        return L + (r + span) / (2 * span) * (w - L - R)

    def Y(p):
        return T + (1 - p / top) * (h - T - B)

    base = Y(0)
    out = [f'<rect x="{X(-band):.1f}" y="{T - 6:.1f}" width="{X(band) - X(-band):.1f}" height="{base - T + 6:.1f}" '
           f'fill="{BAND}"/>',
           text(X(0), T - 22, f"±{band:.0%} strike band", 34, weight=700, anchor="middle")]
    for tail in ([r for r in xs if r <= -band], [r for r in xs if r >= band]):
        pts = " L".join(f"{X(r):.1f} {Y(lognormal_pdf(r, wild[1])):.1f}" for r in tail)
        out.append(f'<path d="M{X(tail[0]):.1f} {base:.1f} L{pts} L{X(tail[-1]):.1f} {base:.1f} Z" '
                   f'fill="{ORANGE}" fill-opacity="0.3"/>')
    for (name, vol), color, dash in ((calm, MUTE, "14 9"), (wild, INK, "none")):
        d = " L".join(f"{X(r):.1f} {Y(lognormal_pdf(r, vol)):.1f}" for r in xs)
        out.append(f'<path d="M{d}" fill="none" stroke="{color}" stroke-width="5" stroke-dasharray="{dash}"/>')
    out.append(f'<line x1="{L}" x2="{w - R}" y1="{base:.1f}" y2="{base:.1f}" stroke="{MUTE}" stroke-width="2"/>')
    for r in (-0.4, -0.2, 0.0, 0.2, 0.4):
        out.append(text(X(r), h - 16, f"{r:+.0%}" if r else "0%", 32, fill=MUTE, anchor="middle"))
    for (name, vol), color, dash, x0 in ((calm, MUTE, "14 9", L), (wild, INK, "none", w - R - 560)):
        out += [f'<line x1="{x0}" x2="{x0 + 48}" y1="30" y2="30" stroke="{color}" stroke-width="5" '
                f'stroke-dasharray="{dash}"/>',
                text(x0 + 62, 42, f"{name} (volatility {vol * 100:.0f})", 34, weight=700),
                text(x0 + 62, 86, f"band sees {band_coverage(band, vol):.0%} of moves", 34, fill=MUTE)]
    return svg(w, h, f"30-day price-move curves for {calm[0]} and {wild[0]} with a ±{band:.0%} strike band",
               "".join(out))


def band_bars(bands, w=1300):
    """Mean |gap| to Cboe by strike band (the 11 Sep 2026 calibration), the worst pair beside each, the widest
    band highlighted. bands: [(label '±10%', strikes, mean_abs_gap, worst_signed_gap, pair or None)]."""
    row, x0 = 128, 220
    scale = (w - x0 - 330) / max(b[2] for b in bands)
    out = []
    for k, (band, n, mae, worst, pair) in enumerate(bands):
        y = 6 + k * row
        bw = max(mae * scale, 6)
        last = k == len(bands) - 1
        who = (f"worst: {pair} " if pair else "worst ") + f"{worst:+.2f}".replace("-", "−")
        out += [text(x0 - 22, y + 56, band, 48, weight=700, family=HEAD, anchor="end"),
                text(x0 - 22, y + 96, f"{n} strikes", 32, fill=MUTE, anchor="end"),
                f'<rect x="{x0}" y="{y + 8}" width="{bw:.0f}" height="96" rx="10" fill="{ORANGE if last else BAR}"/>',
                text(x0 + bw + 20, y + 60, f"{mae:.2f}", 54, weight=800, family=HEAD),
                text(x0 + bw + 20, y + 98, who, 32, fill=MUTE)]
    return svg(w, 6 + len(bands) * row, "Mean absolute gap to Cboe by strike band", "".join(out))


def quote_scale(points, bar, w=1300):
    """How far the free feed's mid sits from a professional feed's mid, in bid-ask spreads (medians), on a
    0-1 spread scale, the registered bar marked on each track. points: [(label, value, shown, hollow)] top
    to bottom; a hollow dot marks the caveat row."""
    L, R, row, top = 20, 60, 116, 66

    def X(v):
        return L + v * (w - L - R)

    out = [text(X(bar) + 14, top - 26, f"the bar, set first: {bar:g}", 32)]
    for k, (label, v, shown, hollow) in enumerate(points):
        y0 = top + k * row
        out += [text(L, y0 + 36, label, 34),
                f'<line x1="{X(0):.1f}" x2="{X(1):.1f}" y1="{y0 + 78}" y2="{y0 + 78}" stroke="{RULE}" stroke-width="4"/>',
                f'<line x1="{X(bar):.1f}" x2="{X(bar):.1f}" y1="{y0 + 56}" y2="{y0 + 100}" stroke="{INK}" '
                'stroke-width="4"/>',
                f'<circle cx="{X(v):.1f}" cy="{y0 + 78}" r="17" fill="{"#fff" if hollow else ORANGE}" '
                f'stroke="{ORANGE}" stroke-width="6"/>',
                text(X(v) + 30, y0 + 91, shown, 36, weight=700)]
    axis = top + len(points) * row + 4
    out += [text(X(0), axis + 34, "0 (same price)", 32, fill=MUTE),
            text(X(0.5), axis + 34, "½ spread", 32, fill=MUTE, anchor="middle"),
            text(X(1), axis + 34, "1 spread", 32, fill=MUTE, anchor="end")]
    return svg(w, axis + 48, "Distance of the free quote from the professional quote, in bid-ask spreads", "".join(out))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 poster/test_charts.py`
Expected: `OK` (13 tests). If a text-extent assertion fails, move the label (never shrink it below 32 px).

---

### Task 3: The page (controller)

**Files:**
- Modify: `poster/build_poster.py` (frozen right-column figures; `build()`; `CSS`; `PAGE`'s check; `render()`;
  `main`; delete `chart_svg` and `QUOTE_STATS`)
- Modify: `poster/test_build_poster.py` (one test)

**Interfaces:**
- Consumes: everything Task 1 and Task 2 produce.
- Produces: `build(today=None, force_headline=None, out_dir=OUT) -> Path`, `HEADLINES`, `QUOTE_POINTS`,
  `QUOTE_BAR`, `EMPTY_BIDS`, `CALM`, `WILD`; `--headline N` (preview only, writes to a temporary folder).

- [ ] **Step 1: Failing test** (`poster/test_build_poster.py`, new class; add `import re` at the top):

```python
class Recipe(unittest.TestCase):
    def test_curves_use_the_readme_sentence_numbers(self):
        import charts
        (sd_calm, vol_calm, sd_wild, vol_wild), = re.findall(
            r"about ([\d.]+) standard deviations on a (\d+)-vol name but only ([\d.]+) on (\d+)-vol", bp.TRUNCATION_WHY)
        self.assertEqual((int(vol_calm), int(vol_wild)), (round(bp.CALM[1] * 100), round(bp.WILD[1] * 100)))
        self.assertEqual(f"{charts.band_sd(0.10, bp.CALM[1]):.1f}", sd_calm)
        self.assertEqual(f"{charts.band_sd(0.10, bp.WILD[1]):.1f}", sd_wild)
```

Run the poster tests; expected: `AttributeError: ... 'CALM'`.

- [ ] **Step 2: Implement.** Add `import charts  # noqa: E402` after the `h3_scorer` import (and
`sys.path.insert(0, str(OUT))` beside the tools insert so `charts` imports from `poster/`). Delete `QUOTE_STATS`
and `chart_svg()`. After `TRUNCATION_WHY` add:

```python
# The right column. H5 file, Result (corrected 17 Oct): H5a's pooled median, 0.33 of Bloomberg's spread over 179
# wing contracts, and 0.67 on the 134 both feeds bid ("holds weakly": the pass rests on contracts with no bid on
# one feed). "H5f, read 25 September 2026": H5f-a 0.500 of OPRA's spread over 466 (ON the bar). Bar 0.5, H5a's.
QUOTE_POINTS = [("Against Bloomberg, all far strikes (179)", 0.33, "0.33", False),
                ("Against the full market (OPRA), all far strikes (466)", 0.500, "0.500", False),
                ("Where both feeds show a bid (Bloomberg, 134)", 0.67, "0.67", True)]
QUOTE_BAR = 0.5
# H5f-b 64 of 64 ("H5f, read 25 September 2026"); H5b 44 of 44 (Result, corrected 17 Oct).
EMPTY_BIDS = ("64 of 64", "44 of 44")
# TRUNCATION_WHY's 16-vol name and 59-vol crude oil (VIX 15.84 and OVX 58.92 on 11 Sep 2026). The curves are a
# lognormal model, not market data; the Recipe test ties them to that sentence.
CALM, WILD = ("S&P 500", 0.16), ("Crude oil", 0.59)
HEADLINES = (HEADLINE, HEADLINE_IF_H7_FAILS, HEADLINE_IF_H7_AND_H3_FAIL)
```

Replace `build()` with:

```python
def tile_html(t):
    return (f'<div class="cell tile"><div class="tk">All five funds, {t["n"]} daily readings</div>'
            f'<div class="tv">{t["mae"]}</div><div class="tu">points off on average</div><ul class="tl">'
            f'<li>Bar, set before the data: under 1.0. <b>H3a {esc(t["a"])}</b></li>'
            f'<li>Registered: free data reads low on average ({t["mean"]}). <b>H3b {esc(t["b"])}</b></li>'
            f'<li>Registered: the gap grows when volatility is high. <b>H3c {esc(t["c"])}</b></li>'
            f'</ul><div class="tk">{esc(t["label"])}</div></div>')


def build(today=None, force_headline=None, out_dir=OUT):
    today = today or date.today()
    h3, series = h3_live()
    h5e = h5e_final(H5_FILE.read_text())
    h7 = h7_reading(H7_FILE.read_text())
    conf, side = scorecard(h3, h5e, h7, today)
    head = headline(h3, h7) if force_headline is None else HEADLINES[force_headline]
    long = " long" if len(" ".join(head)) > 64 else ""
    ai = (f'<p class="ai">{esc(AI_LINE)}</p>' if AI_LINE_APPROVED else
          f'<p class="ai draft"><span class="tag">DRAFT, for Gabriel to approve</span> {esc(AI_LINE)}</p>')
    panels = "".join(f'<div class="cell">{charts.daily_panel(s, ix, what, series[s], h3["per"][s][1])}</div>'
                     for s, ix, what in PAIRS)

    def chips(cs):
        return "".join(chip_html(c) for c in cs)

    body = f"""
<header class="banner">
  <div>
    <h1>What Does Free Options Data Cost?</h1>
    <p class="subtitle">Measuring a Retail-Grade Feed Against Cboe's Volatility Indices</p>
  </div>
  <div class="who">
    <p class="name">Gabriel Mitton</p>
    <p>Pepperdine University, Malibu, California · gabriel.mitton@gmail.com</p>
    <p>Mentor: Marc Vinyard, Pepperdine University Libraries</p>
  </div>
</header>
<section class="headline">
  <div class="kicker">Main finding, on the evidence so far</div>
  <div class="big{long}">{esc(head[0])} <em>{esc(head[1])}</em></div>
</section>
<main class="body">
  <section class="col left">
    <div><h2><span class="n">1</span>The question</h2>
      <p>Students and small researchers price options with <b>free quotes</b>, because the full market feed costs
      thousands of dollars a year. What precision does free data give up, and <b>where</b> is the loss: in the
      quotes, or in the recipe that turns them into a volatility number? If it is the recipe, anyone can fix it
      for free.</p></div>
    <div><h2><span class="n">2</span>What I did</h2>
      <div class="flow">
        <div class="box"><b>Free quotes</b> from a retail brokerage (Alpaca), recorded every trading day since
        September 2026: 109 tickers</div>
        <div class="arrow">↓ Cboe's recipe, the VIX formula</div>
        <div class="box"><b>A volatility number</b> per fund per day: the swing the market expects over the next
        30 days</div>
        <div class="arrow">↓ checked against</div>
        <div class="refs"><div>Cboe's published indices</div><div>The full market feed (OPRA)</div><div>Bloomberg</div></div>
      </div></div>
    <div><h2>How it stays honest</h2>
      <ul>
        <li>Every pass/fail bar was <b>written before its test ran</b>, dated in a public repository; the open
            tests were also frozen on <b>OSF</b>.</li>
        <li>A <b>second program sharing no code</b> recomputed every recorded number.</li>
        <li>Failures are reported beside successes, in the strip below.</li>
      </ul></div>
    <div class="limits"><h2>Limits</h2>
      <p>One free feed; about two months of data; one snapshot a day, about 80 minutes before the close (a
      median 0.53 points of drift by the close in stress months); American options priced with European
      formulas; far contracts nobody quotes can carry hours-old free quotes.</p></div>
  </section>
  <section class="col center">
    <h2><span class="n">3</span>Free data tracks Cboe's index, day after day</h2>
    <div class="legend"><span><i class="sw"></i>Cboe's published index</span>
      <span><i class="sw orange"></i>Free data, this project</span><span><i class="sw gap"></i>the gap</span></div>
    <div class="grid">{panels}{tile_html(h3_tile(h3, today))}</div>
    <p class="cap">Each panel is one fund, every trading day from 14 Sep to 11 Nov 2026, in volatility points: a
    VIX of 20 means the market expects swings of about 20% a year.</p>
  </section>
  <section class="col right">
    <div><h2><span class="n">4</span>The quotes are close to the professional feeds</h2>
      <div class="kpi"><b>{EMPTY_BIDS[0]}</b><span>far strikes with no bid on the free feed had no bid on the full
      market either (Bloomberg: {EMPTY_BIDS[1]})</span></div>
      <p class="cap">How far the free price sits from the professional one, in bid-ask spreads (medians):</p>
      {charts.quote_scale(QUOTE_POINTS, QUOTE_BAR)}
      <p class="cap">Far strikes trade for pennies, so even 0.67 of a spread is a tick or two.</p></div>
    <div><h2><span class="n">5</span>Most of the error is in the recipe</h2>
      <p class="lead">A fixed ±10% band of strikes sees almost all of a calm fund's likely moves, but under half
      of oil's:</p>
      {charts.coverage_curves(CALM, WILD)}
      <p class="cap">30-day price moves, a simple model. {esc(TRUNCATION_WHY)} Orange: the tails the band
      leaves out, which Cboe's formula still counts.</p>
      <p class="lead">Widen the band, and the gap to Cboe's index falls from {BANDS[0][2]:.2f} to
      {BANDS[-1][2]:.2f} points:</p>
      {charts.band_bars(BANDS)}
      <p class="cap">Mean gap to Cboe's index, five fund–index pairs, one calibration day (11 Sep 2026).</p></div>
  </section>
</main>
<footer class="bottom">
  <div class="tests"><h3>Every registered test, scored against a bar set before its data</h3>
    <div class="row"><div class="rl">The free-data question</div>{chips(conf)}</div>
    <div class="row"><div class="rl">Side studies</div>{chips(side)}</div></div>
  <div class="qr"><div id="qr"></div>Data, code and every registration</div>
  <div class="credits">
    <p><b>Acknowledgments.</b> I thank Marc Vinyard for mentoring this project and for library data access.</p>
    {ai}
    <p>Data provided by Databento (OPRA consolidated NBBO). Bloomberg figures: Source: Bloomberg Finance L.P.
    Index values © Cboe Global Markets. This product uses the FRED® API but is not endorsed or certified by the
    Federal Reserve Bank of St. Louis. Options quotes: Alpaca indicative feed, non-commercial use. Aggregates
    only. Registration: {OSF} · {SITE}</p>
  </div>
</footer>
"""
    page = PAGE.replace("@@CSS@@", CSS).replace("@@BODY@@", body).replace("@@SITE@@", SITE)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "poster.html").write_text(page)
    return out_dir / "poster.html"
```

Replace `CSS` with:

```python
CSS = """
  @page { size: 48in 36in; margin: 0; }
  :root { --navy:#0b2447; --ink:#14213d; --mute:#4f5a6d; --rule:#d3d9e3; --orange:#e35205; --tint:#f3f5f9;
          --ok:#1f7a4d; --bad:#b42318; --due:#8a6d00; --na:#56607a; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html, body { width:48in; height:36in; background:#fff; color:var(--ink); font-family:Inter, system-ui, sans-serif;
               font-size:40px; line-height:1.35; -webkit-print-color-adjust:exact; print-color-adjust:exact;
               overflow:hidden; }
  .poster { display:grid; grid-template-rows:auto auto minmax(0, 1fr) auto; width:48in; height:36in; overflow:hidden; }
  .banner { background:var(--navy); color:#fff; padding:0.5in 0.8in 0.45in; display:flex;
            justify-content:space-between; align-items:flex-end; gap:1in; }
  h1 { font:800 124px/1.0 'Inter Tight'; letter-spacing:-0.01em; }
  .subtitle { font:600 58px/1.15 'Inter Tight'; color:#c9d5e8; margin-top:0.16in; }
  .who { text-align:right; font-size:38px; line-height:1.32; color:#dbe4f3; flex:none; }
  .who .name { font:700 58px/1.15 'Inter Tight'; color:#fff; margin-bottom:0.06in; }
  .headline { padding:0.36in 0.8in 0.32in; border-bottom:4px solid var(--rule); }
  .kicker { font:700 38px/1.2 'Inter Tight'; letter-spacing:0.12em; text-transform:uppercase; color:var(--orange); }
  .big { font:800 120px/1.05 'Inter Tight'; color:var(--navy); letter-spacing:-0.015em; margin-top:0.06in; }
  .big.long { font-size:100px; }
  .big em { font-style:normal; color:var(--orange); }
  .body { display:grid; grid-template-columns:10.6in minmax(0, 1fr) 14.4in; gap:0.6in;
          padding:0.4in 0.8in 0.3in; min-height:0; }
  .col { display:flex; flex-direction:column; gap:0.3in; min-height:0; overflow:hidden; }
  h2 { font:700 50px/1.12 'Inter Tight'; color:var(--navy); padding-bottom:0.08in; border-bottom:6px solid var(--orange);
       margin-bottom:0.16in; display:flex; align-items:center; gap:0.18in; }
  h2 .n { flex:none; width:0.66in; height:0.66in; border-radius:50%; background:var(--navy); color:#fff;
          display:inline-flex; align-items:center; justify-content:center; font-size:42px; }
  .left { font-size:37px; }
  .left p, .left li { line-height:1.33; }
  ul { padding-left:0.4in; } li + li { margin-top:0.07in; }
  .flow { display:flex; flex-direction:column; gap:0.07in; }
  .flow .box { background:var(--tint); border-left:10px solid var(--navy); padding:0.12in 0.18in; font-size:35px; line-height:1.28; }
  .flow .arrow { font:700 35px/1.2 'Inter Tight'; color:var(--orange); padding-left:0.24in; }
  .flow .refs { display:grid; grid-template-columns:repeat(3, 1fr); gap:0.1in; }
  .flow .refs div { background:var(--navy); color:#fff; padding:0.1in 0.12in; font:700 33px/1.18 'Inter Tight';
                    text-align:center; border-radius:8px; display:flex; align-items:center; justify-content:center; }
  .limits p { font-size:33px; color:var(--mute); line-height:1.3; }
  .legend { display:flex; gap:0.6in; font-size:35px; color:var(--mute); margin:-0.06in 0 0.06in; }
  .sw { display:inline-block; width:0.6in; height:0; border-top:6px solid var(--navy); vertical-align:middle; margin-right:0.14in; }
  .sw.orange { border-top:6px dashed var(--orange); }
  .sw.gap { height:0.3in; border:none; background:rgba(227, 82, 5, 0.16); }
  .grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); grid-auto-rows:minmax(0, 1fr);
          gap:0.24in 0.45in; flex:1; min-height:0; }
  .cell { min-height:0; display:flex; align-items:center; justify-content:center; }
  .cell svg.chart { width:100%; height:100%; display:block; }
  .tile { background:var(--tint); border-radius:20px; padding:0.26in 0.34in; flex-direction:column;
          align-items:flex-start; justify-content:center; }
  .tile .tk { font-size:33px; color:var(--mute); }
  .tile .tv { font:800 140px/1.0 'Inter Tight'; color:var(--orange); margin:0.04in 0; }
  .tile .tu { font:700 40px/1.2 'Inter Tight'; color:var(--ink); margin-bottom:0.12in; }
  .tile .tl { list-style:none; padding:0; font-size:33px; line-height:1.28; }
  .tile .tl li + li { margin-top:0.06in; }
  .tile .tl b { color:var(--navy); white-space:nowrap; }
  .cap { font-size:33px; color:var(--mute); line-height:1.28; }
  .lead { font:700 39px/1.24 'Inter Tight'; color:var(--ink); }
  .right > div { display:flex; flex-direction:column; gap:0.12in; }
  .right svg.chart { width:100%; height:auto; display:block; }
  .kpi { display:flex; align-items:center; gap:0.3in; }
  .kpi b { font:800 104px/1.0 'Inter Tight'; color:var(--navy); white-space:nowrap; }
  .kpi span { font-size:35px; line-height:1.28; }
  .bottom { display:grid; grid-template-columns:minmax(0, 1fr) 3.3in 11.4in; gap:0.45in; align-items:start;
            padding:0.28in 0.8in 0.4in; background:var(--tint); border-top:4px solid var(--rule); }
  .tests h3 { font:700 38px/1.2 'Inter Tight'; color:var(--navy); margin-bottom:0.12in; }
  .tests .row { display:grid; grid-template-columns:2.3in repeat(8, minmax(0, 1fr)); gap:0.1in; }
  .tests .row + .row { margin-top:0.1in; }
  .tests .rl { font:700 32px/1.2 'Inter Tight'; color:var(--mute); align-self:center; }
  .chip { background:#fff; border:3px solid var(--rule); border-top:10px solid var(--na); border-radius:10px;
          padding:0.05in 0.09in 0.07in; font-size:32px; line-height:1.17; }
  .chip.ok { border-top-color:var(--ok); } .chip.bad { border-top-color:var(--bad); } .chip.due { border-top-color:var(--due); }
  .chip .ch { display:flex; flex-wrap:wrap; justify-content:space-between; column-gap:0.1in; font-family:'Inter Tight'; }
  .chip .ch b { color:var(--navy); }
  .chip .vd { font-weight:700; }
  .chip.ok .vd { color:var(--ok); } .chip.bad .vd { color:var(--bad); } .chip.due .vd { color:var(--due); }
  .chip.na .vd { color:var(--na); }
  .chip .cl { margin-top:0.03in; }
  .chip .cn { color:var(--mute); margin-top:0.03in; }
  .qr { background:#fff; padding:0.12in 0.12in 0.16in; border-radius:16px; text-align:center; color:var(--ink);
        font-size:32px; line-height:1.2; }
  .qr #qr { width:3.05in; height:3.05in; margin:0 auto 0.06in; }
  .qr svg { display:block; width:100%; height:100%; shape-rendering:crispEdges; }
  .credits { font-size:32px; line-height:1.25; color:var(--mute); }
  .credits p + p { margin-top:0.08in; }
  .credits b { color:var(--ink); }
  .ai.draft { border:4px dashed var(--bad); padding:0.06in 0.12in; color:var(--ink); }
  .ai .tag { font-weight:800; color:var(--bad); }
"""
```

In `PAGE`'s check script, replace the `over` line with:

```javascript
  const over = [...document.querySelectorAll(".poster, .poster > *, .col")]
    .filter(s => s.scrollHeight > s.clientHeight + 1 || s.scrollWidth > s.clientWidth + 1).map(s => s.className || s.tagName);
```

In `render()`, write the PDF and preview next to the HTML: `pdf, png = path.with_name("poster.pdf"),
path.with_name("preview.png")`, use them in both `chrome()` calls and in the MediaBox read. In `__main__`, add the
`--headline` option (`type=int, choices=range(len(HEADLINES))`, help says PREVIEW ONLY), write to
`Path(tempfile.mkdtemp(prefix="poster-headline-"))` when it is given, call `build(today, a.headline, out_dir)`
and print absolute paths.

- [ ] **Step 3: Run the tests.** Both suites `OK`.

- [ ] **Step 4: Render and look.**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 poster/build_poster.py --pdf`
Expected: `check: smallest text >= 32.0px ...; overflow none; PDF pages 1, MediaBox ['3456', '2592']`. Open
`poster/preview.png` and look: no clipped column, no label collision, every chart readable. Adjust sizes (never
below 32 px) until it passes and reads well. Then `--headline 1 --pdf` and `--headline 2 --pdf` must pass too.

---

### Task 4: The pitch walk

**Files:** Modify: `SCCUR-PITCH.md` (the 2-minute walk and the line under the opener).

- [ ] Rewrite "The 2-minute walk" for the new order: banner and headline; 1-2 (left: question, what I did);
3 (centre: the five panels, the tile; point at oil); 4 (right: 64 of 64, the distance scale and its caveat);
5 (right: the bell curves, then the bars); the strip (point at a red chip, H6a; after 19 Nov, H5e and H7 from
the chips); limits. Every number the poster's own. Keep the opener, the questions and the [after 19 Nov] marks.

---

### Task 5: Four reviewers on the rendered poster (subagents, in parallel)

Each gets `poster/preview.png`, `poster/poster.html`, the spec, the source files, and one role:
1. **Poster judge and designer:** can a non-finance student read it from six feet; is each graph understood in
   ten seconds; flow; five concrete fixes, worst first.
2. **Number auditor:** every number on the page traced to its source (hypothesis files, README, scorer output);
   any mismatch, rounding error or claim stronger than its record.
3. **Chart and accessibility reviewer:** each chart against the dataviz rules (one axis, labels, honest scales,
   colour never alone, colour-blind separation of navy/orange); the 24 pt floor; contrast.
4. **Integrity and licensing auditor:** credit lines verbatim, aggregates only, nothing from licensed raw data,
   "so far" and "of record" right, failures visible, AI line, nothing the registrations do not support.

- [ ] Fix what they find that is real (verify each), re-render, re-run both suites.

---

### Task 6: Astra review, records, commit, push

- [ ] `tools/codex_review.py` on the diff (framework Python; Ultra; follow docs/CODEX-REVIEW.md); fix verified
  findings; one follow-up at most.
- [ ] HANDOFF: a dated entry (what changed, test counts, reviews); the pitch file; memory.
- [ ] Commit with explicit paths (poster/build_poster.py, poster/charts.py, poster/test_build_poster.py,
  poster/test_charts.py, SCCUR-PITCH.md, HANDOFF.md, the plan); push with the scratchpad's push_offhours.sh
  (audit N of N, outside 14:15-15:15 New York on weekdays).

---

## Amendments made during execution (8 Nov 2026, Decided, Gabriel's to veto)

- **Cboe's line is blue `#1f4e9c`, not navy.** The dataviz palette check failed navy as a series colour (OKLCH
  lightness 0.263, under the 0.43-0.77 band; chroma 0.072, under the 0.10 floor: it reads as grey ink).
  `#1f4e9c` with the orange passes all five checks (colour-blind separation dE 24.8, normal vision 36.5,
  contrast over 3:1). Navy stays for the banner and headings.
- **Every calibration bar is orange.** The three bars are one quantity (free data's gap), so one colour; no
  single highlighted bar. Orange means free data and its gap in every chart.
- **Gridline labels keep their halves** (57.5, not 58): `f"{round(v, 2):g}"`, with a test.
- **The Recipe test reads README.md itself** (whitespace normalised), not only the poster's copy of the sentence.
- **"Why it matters" is one sentence in section 1** (the SCCUR abstract's approved wording), not a box in the
  right column: the box ran that column 250 px over the page.
- **Panel 5's title is the measured finding**, "The recipe: widen the strikes, and the gap shrinks". The
  headline already says "Most of the error is in the recipe" (Gabriel's 21 Oct wording, with its fallback rule);
  PAPER-DRAFT narrowed the causal reading on 28 Oct (M09), so the panel claims only what its bars show.
- **"What's next" stays in the left column** (the spec lists it). Its first line points to the strip once both
  final blocks exist.
- **Sizes to fit:** the bell curves at 440 px high and the bars at 116 px a row. The page check now also prints
  the room left at the foot of each column.

## Amendments after the reviews (8-11 Nov 2026, Decided, Gabriel's to veto)

Three independent reviews of the rendered poster (design, the claims against the records, the code), then Astra
Ultra on 8 Nov and its one follow-up on 11 Nov; each finding was checked against the records before it changed
anything. Full list: HANDOFF, the Sat 7 - Wed 11 Nov entry.

- **The main chart counts days; it draws no index level and no day.** Task 3's five panels drew Cboe's index and
  the free estimate as two lines. The request Cboe approved on 4 Nov promised "Only aggregate statistics", so on
  8 Nov they became each day's gap as a bar; Astra read those dated gaps as per-day data, so they are now
  histograms (`charts.gap_histogram`): days counted in half-point gap bins (`charts.bin_counts`), one gap axis
  and one day axis for all five (`charts.shared_scale` over every bin's far edge, `charts.count_scale`), a blue
  line at zero (Cboe's index), a band for within one point, no dates. `gap_histogram` refuses dated rows, and
  page tests fail if an index value or a day reaches the page.
- **Figures are rounded once, from full precision.** `check_series` recomputes every pooled and per-pair figure
  from the run and checks it against the scorer's three-decimal print; the page rounds the full-precision values.
- **"Of record" needs the 11 Nov data in every pair**, not the date alone.
- **The H3 tile's colour follows each part's verdict** (it was always green).
- **The quote scale shows both readings for both feeds:** four dots on two tracks (filled: all far strikes;
  hollow: only those both feeds bid), the bar's tick drawn over them.
- **A final H5e chip keeps the recorded 8 Oct failure beside it**; an H7 part below its minimum shows a grey "-"
  (never scored), not the amber "..." of a reading still due.
- **A comparison never breaks across lines** (no-break spaces beside <, >, =, <= and >=).
- **Wording matched to the records:** the flow's arrow ("the VIX formula, with strikes and expiries I chose");
  "recorded daily"; "H5e and H7 were also frozen on OSF"; "eight funds and stocks"; the H2a, H2b, H5c-d and H6a
  chips; the snapshot-timing limit; a section 5 caveat (a coverage effect, which by itself does not rule out the
  feed, the timing or index-versus-fund); the re-check "recomputed every recorded result on 17 Oct".
- **The build refuses what it cannot vouch for:** the H5e lines are matched exactly as the frozen writer prints
  them; a scorer refusal (nonzero exit) stops the build; Chrome's output counts only if that run wrote it; the page
  check (`CHECK_JS`, after `document.fonts.ready`) measures the smallest text, overflow, the fonts, chart text that
  leaves its chart or meets another label, and the room left, and appends its result to the page title, which
  Chrome writes into the PDF's /Title; `render()` reads it back (`pdf_check`) and names the files `poster.pdf` /
  `preview.png` only on a pass (`*.FAILED-CHECK.*` otherwise).
- **After the follow-up review (11 Nov):** the preview is drawn from the checked PDF by macOS's own sips
  (`raster`), never from a Chrome run of its own; the PDF must be written to its end (`pdf_whole`: startxref
  pointing at the cross-reference table, then %%EOF) and the preview must decode whole (`png_size`) as one 4:3
  page; the page check reports the smallest size unrounded and lets a label cross its chart's edge or another
  label only by numerical error (0.01 px); the pitch follows both fallback branches of the headline rule.
- **Sizes to fit:** histograms 940 x 560 px with a 64 px foot; the bell curves 380 px high; the band bars 112 px
  a row.
- **Checks:** poster 57 and charts 27 tests; 43 mutants, all caught by their intended tests; four broken pages
  refused in real Chrome; five states pass (today, both fallback headlines, a worst and a best case after the
  verdicts).
