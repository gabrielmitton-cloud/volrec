"""Build the SCCUR 2026 poster (48 x 36 in, landscape) from the project's own records.

    .../python3 poster/build_poster.py            # writes poster/poster.html
    .../python3 poster/build_poster.py --pdf      # also poster/poster.pdf and poster/preview.png (Chrome)
    .../python3 poster/test_build_poster.py       # the verdict-box parsers against record_verdict's own writer

Frozen results are copied below with the file they come from. The live boxes are filled by
the project's own readers, never typed by hand:
  - H3: tools/h3_scorer.py (its H3a/H3b/H3c lines); "so far" until the data reaches 11 Nov 2026 in
    every pair and the build runs after that day, the reading of record then (never by the date alone);
  - H5e FINAL and H7: the blocks tools/record_verdict.py writes into the hypothesis files.
    Until a block exists its box says when the reading is due; it never shows a preview.
    A block that is present but not recognised stops the build (the poster never guesses).
Derived figures only, with each source's credit line: no licensed raw data, and no index series (the main chart
draws each day's gap, never Cboe's values: Cboe approved aggregates only, 4 Nov 2026).
The --pdf render also checks the page: smallest text >= 32 CSS px (24 pt at 48 x 36 in), no
column overflowing, the QR code drawn as vector SVG, one 3456 x 2592 pt page.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
import zlib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "poster"
sys.path[:0] = [str(OUT), str(ROOT / "tools")]
from record_verdict import MARK_H5E_FINAL, MARK_H7  # noqa: E402  (the marks the writer uses)
import h3_scorer as hs  # noqa: E402  (the frozen H3 scorer: its own row reader feeds the main chart)
import charts  # noqa: E402  (poster/charts.py: the inline SVG charts)

# ---------------- the switches ----------------
# The headline, (plain sentence, orange sentence). One-line switch. Chosen 21 Oct 2026 (research report, option 3).
HEADLINE = ("The free quotes are close.", "Most of the error is in the recipe.")
# HEADLINE = ("The free quotes aren't the problem.", "The recipe is.")     # the first draft's headline

# The fallback, decided by Gabriel on 21 Oct 2026, BEFORE H7's verdict: if H7 is written and either part
# FAILS, the headline no longer claims the split and says only what H3 supports. If H3 had failed too
# (it reads 0.45 against 1.0 on 21 Oct), the most cautious option of the research report is used.
HEADLINE_IF_H7_FAILS = ("Widen the strikes,", "and free data lands within a point of Cboe's index.")
HEADLINE_IF_H7_AND_H3_FAIL = ("So far, free data loses more", "to the method than to the quotes.")
HEADLINES = (HEADLINE, HEADLINE_IF_H7_FAILS, HEADLINE_IF_H7_AND_H3_FAIL)     # --headline N previews each

# Gabriel: set True once you approve the AI-use sentence below; until then it prints marked DRAFT.
AI_LINE_APPROVED = True   # approved by Gabriel, 21 Oct 2026
AI_LINE = ("Code written with the help of an AI coding assistant (Claude Code); the research question, "
           "decisions and interpretation are the author's.")

H3_FILE = ROOT / "hypotheses/2026-09-12-h3-free-data-model-free.md"
H5_FILE = ROOT / "hypotheses/2026-09-19-h5-wing-quote-quality.md"
H7_FILE = ROOT / "hypotheses/2026-10-08-h7-free-feed-cboe-replica.md"
SITE = "https://gabrielmitton-cloud.github.io/volrec/"
OSF = "https://osf.io/z5gfu"
H3_RECORD_DAY = date(2026, 11, 11)       # tools/h3_scorer.py THROUGH: the reading of record is the one after it
DUE = "due 12–19 Nov"                    # record_verdict.py: due 12 Nov, written by COMPLETE_BY = 19 Nov at the latest
ENV = {"FRED_KEY": "use-cache", "PATH": "/usr/bin:/bin"}   # the frozen 3.910% rate; the scorer refuses any other
# The five benchmarked pairs (tools/h3_scorer.py BENCH), in the main chart's order: fund, Cboe index, what it tracks.
PAIRS = (("SPY", "VIX", "S&P 500"), ("QQQ", "VXN", "Nasdaq-100"), ("IWM", "RVX", "Russell 2000"),
         ("GLD", "GVZ", "gold"), ("USO", "OVX", "crude oil"))

# ---------------- frozen figures, each with its source ----------------
# README.md "Calibrated 11 September 2026" (also PAPER-DRAFT.md, H3 file "Calibration, 2026-09-11"): one day,
# five fund/index pairs. Columns: band, strikes, mean absolute gap to Cboe, worst single pair, that pair.
# Worst pair: USO/OVX at +/-10% (README: "which is why USO was twelve points light"; index.html: "12.37
# measured") and at +/-30% (H3 file: "USO 57.08 against 58.92 (-1.84)"). The +/-20% row's pair is not
# recorded anywhere in the repo, so it is not named.
BANDS = [("±10%", 20, 3.97, -12.37, "USO"), ("±20%", 30, 1.31, -4.39, None), ("±30%", 40, 0.59, -1.84, "USO")]
SPY_VS_VIX = ("15.83", "15.84")  # README.md, same calibration day ("SPY comes in at 15.83 against ... 15.84")
# README.md, under the calibration table (wording kept): why a fixed band misses oil.
TRUNCATION_WHY = ("A fixed ±10% band spans about 2.2 standard deviations on a 16-vol name but only 0.6 on "
                  "59-vol crude oil, which is why USO read twelve points light.")

# The right column, one track per feed: (all far strikes, only those both feeds bid). H5 file, Result (corrected
# 17 Oct): H5a's pooled median, 0.33 of Bloomberg's spread over 179 wing contracts, and 0.67 on the 134 both feeds
# bid, "still over the bar" ("holds weakly": "the pass rests on the contracts with no bid on at least one feed";
# read plainly, the two-sided wing quotes are "within a tick or two, not within half a spread"). "H5f, read 25
# September 2026": H5f-a 0.500 of OPRA's spread over 466 (ON the bar; TEST-INVENTORY.md: exactly 1/2), and,
# descriptive, "where both feeds bid, n=402, median 0.667". The bar, 0.5 of a spread, is H5a's and H5f-a's ("fails
# if the pooled wing mid gap exceeds half a spread"). Scope (H5 file): USO and TSLA, Sep 2026.
QUOTE_FEEDS = [("Bloomberg (179 far strikes; 134 bid on both feeds)", (0.33, "0.33"), (0.67, "0.67")),
               ("Full market, OPRA (466 far strikes; 402 bid on both feeds)", (0.500, "0.500"), (0.667, "0.667"))]
QUOTE_BAR = 0.5
# H5f-b 64 of 64 ("H5f, read 25 September 2026"); H5b 44 of 44 (Result, corrected 17 Oct).
EMPTY_BIDS = ("64 of 64", "44 of 44")
# The bell curves: TRUNCATION_WHY's 16-vol name and 59-vol crude oil (README.md, under the calibration table). A
# lognormal model, not market data; test_build_poster.py's Recipe test ties both numbers to the README itself.
CALM, WILD = ("S&P 500", 0.16), ("Crude oil", 0.59)


class Unrecognised(ValueError):
    """A reader's output or a verdict block is present but not in the form expected: stop, never guess."""


# ---------------- live readers ----------------
H3_LINE_A = re.compile(r"^H3a (HOLDS|FAILS): pooled mean \|gap\| ([\d.]+) vs bar under 1\.0 "
                       r"\((\d+) readings over (\d+) days\)", re.M)
H3_LINE_B = re.compile(r"^H3b (HOLDS|FAILS): pooled mean gap ([+-][\d.]+) \(registered: negative\)", re.M)
H3_LINE_C = re.compile(r"^H3c (HOLDS|FAILS): pooled slope of \|gap\| on the index level", re.M)
# The scorer's per-pair lines, e.g. "   SPY  T= 38  mean |gap| 0.446  p(H3a) ...".
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
    """One registered, full-precision modelfree.py run: the same command tools/h3_scorer.py runs itself."""
    p = subprocess.run([sys.executable, str(ROOT / "modelfree.py"), "--precise"], cwd=ROOT,
                       capture_output=True, text=True, env=ENV)
    if p.returncode != 0:
        raise SystemExit(f"modelfree.py failed ({p.returncode}): {p.stderr[-500:]}")
    return p.stdout


def score_saved(out):
    """The frozen scorer on that saved run (h3_scorer.py --file), with its own rate check and precision rule."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "modelfree.txt"
        f.write_text(out)
        p = subprocess.run([sys.executable, str(ROOT / "tools/h3_scorer.py"), "--file", str(f)], cwd=ROOT,
                           capture_output=True, text=True, env=ENV)
    if p.returncode != 0:      # the scorer exits 0 on HOLDS and FAILS alike; anything else is a refusal (Astra, 8 Nov)
        raise SystemExit(f"tools/h3_scorer.py refused the run ({p.returncode}): {(p.stderr or p.stdout)[-500:]}")
    return p.stdout + p.stderr


def h3_series(out):
    """{symbol: [(date, ours, cboe)]} for the five pairs, read with the scorer's own parse: exactly the rows it
    scores, to 11 Nov 2026. ours = Cboe + gap, as modelfree.py defines the gap."""
    series = {}
    for d, sym, cboe, gap in hs.parse(out, H3_RECORD_DAY.isoformat()):
        series.setdefault(sym, []).append((d, cboe + gap, cboe))
    return series


def check_series(series, h3):
    """The chart and the printed numbers come from one run, and the poster's 2-decimal figures come from that run's
    full-precision rows (modelfree.py --precise), never from rounding the scorer's 3-decimal print a second time:
    the printed 0.365 rounds to 0.36, while the value it stands for, 0.3651, rounds to 0.37 (number audit, 8 Nov
    2026). The readings and days must equal the scorer's, and every figure must lie within half the last printed
    digit of its print, or the build stops. Returns h3 with 'mae', 'mean' and each pair's mean |gap| at full
    precision, as drawn."""
    def near(x, printed):
        return abs(x - printed) <= 0.0005 + 1e-9

    per = {}
    for sym, _, _ in PAIRS:
        rows = series.get(sym, [])
        n, printed = h3["per"][sym]
        got = sum(abs(o - c) for _, o, c in rows) / len(rows) if rows else float("nan")
        if len(rows) != n or not near(got, printed):
            raise Unrecognised(f"{sym}: the chart has {len(rows)} readings with mean |gap| {got:.4f}; the scorer "
                               f"printed {n} and {printed:.3f} - the poster will not draw a different run")
        per[sym] = (n, got)
    rows = [r for sym, _, _ in PAIRS for r in series[sym]]
    days = len({d for d, _, _ in rows})
    mae = sum(abs(o - c) for _, o, c in rows) / len(rows)
    mean = sum(o - c for _, o, c in rows) / len(rows)
    if (len(rows), days) != (h3["n"], h3["days"]) or not (near(mae, h3["mae"]) and near(mean, h3["mean"])):
        raise Unrecognised(f"pooled: {len(rows)} readings over {days} days, mean |gap| {mae:.4f}, mean gap "
                           f"{mean:+.4f}; the scorer printed {h3['n']} over {h3['days']}, {h3['mae']:.3f} and "
                           f"{h3['mean']:+.3f} - the poster will not guess")
    return {**h3, "mae": mae, "mean": mean, "per": per}


def h3_live():
    """H3: the frozen scorer's report on one saved modelfree.py run (figures at that run's full precision), and
    the same run's daily series."""
    out = run_modelfree()
    series = h3_series(out)
    return check_series(series, parse_h3(score_saved(out))), series


def of_record(series, today):
    """The reading of record: a build after 11 Nov 2026 whose data reaches 11 Nov in every pair. Never by the date
    alone: Cboe's closes can lag a day or two (tools/record_verdict.py), and a build on 12 Nov without the 11 Nov
    close is still a reading to date (8 Nov review)."""
    last = H3_RECORD_DAY.isoformat()
    return today > H3_RECORD_DAY and all(series.get(s) and series[s][-1][0] == last for s, _, _ in PAIRS)


def _block(text, mark):
    """The verdict block that starts at `mark`, up to the next bold paragraph or section heading."""
    i = text.find(mark)
    if i < 0:
        return None
    ends = [j for j in (text.find(s, i + len(mark)) for s in ("\n**", "\n## ", "\n---")) if j >= 0]
    return text[i:min(ends)] if ends else text[i:]


def h5e_final(text):
    """The H5e FINAL block record_verdict.block_h5e(final=True) writes -> dict, or None if not written yet."""
    b = _block(text, MARK_H5E_FINAL)
    if b is None:
        return None
    v = re.search(r"^- \*\*(HOLDS|FAILS)\*\*", b, re.M)
    # The writer's lines exactly, bars included (Astra, 8 Nov: "([\d.]+)" took "1.2.3" for a figure, and a line
    # carrying another bar still parsed).
    mae = re.search(r"^- Mean absolute gap of the skip-only estimate to OVX: (\d+\.\d{2}) volatility points "
                    r"\(bar: under 0\.5\)\.$", b, re.M)
    days = re.search(r"^- Closer to OVX than the registered estimate on (\d+) of (\d+) counted days "
                     r"\(bar: a majority\)\.$", b, re.M)
    if not (v and mae and days):
        raise Unrecognised("H5e FINAL block found but not recognised - the poster will not guess.")
    return {"verdict": v[1], "mae": mae[1], "closer": days[1], "n": days[2]}


def h7_reading(text):
    """The H7 block record_verdict.block_h7 writes -> dict, or None if not written yet."""
    b = _block(text, MARK_H7)
    if b is None:
        return None
    num = r"(\d+\.\d+|n/a)"
    a = re.search(r"^- \*\*H7a ([^:*]+):\*\* .*?: USO " + num + r" over (\d+) days, GLD " + num +
                  r" over (\d+) days \(bar: 0\.25 or less, each\)", b, re.M)
    bb = re.search(r"^- \*\*H7b ([^:*]+):\*\* .*? a mean absolute " + num +
                   r" points from GVZ's close over (\d+) days \(bar: 0\.30 or less\)", b, re.M)
    if not (a and bb):
        raise Unrecognised("H7 block found but not recognised - the poster will not guess.")
    return {"a": a[1], "uso": a[2], "uso_n": a[3], "gld": a[4], "gld_n": a[5], "b": bb[1], "gvz": bb[2], "n": bb[3]}


def headline(h3, h7):
    """The decided headline, or its pre-decided fallback once H7's verdict exists and fails."""
    if h7 is None or not any(h7[k].startswith("FAILS") for k in ("a", "b")):
        return HEADLINE
    return HEADLINE_IF_H7_FAILS if h3["verdict"] == "HOLDS" else HEADLINE_IF_H7_AND_H3_FAIL


# ---------------- the chips: every registered test, a side note to point at ----------------
def esc(s):
    return html.escape(str(s), quote=False)


KIND = {"HOLDS": "ok", "FAILS": "bad"}
ICON = {"ok": "✓", "bad": "✗", "due": "…", "na": "–"}     # a verdict is an icon and a word, never colour alone


def chip(hid, claim, kind, verdict, number):
    return {"id": hid, "claim": claim, "kind": kind, "verdict": verdict, "number": number}


def so_far(record):
    return "" if record else " so far"


def h3_chip(h3, record):
    """H3 in the scorer's words: 'so far' until the reading of record (of_record)."""
    return chip("H3", "Free data tracks Cboe's index", KIND.get(h3["verdict"], "due"),
                h3["verdict"].lower() + so_far(record), f'{h3["mae"]:.2f} over {h3["n"]} readings (bar < 1.0)')


def h3_tile(h3, record):
    """The summary tile beside the five panels: the pooled numbers and the three registered parts."""
    return {"mae": f'{h3["mae"]:.2f}', "n": h3["n"], "days": h3["days"],
            "a": h3["verdict"].lower() + so_far(record), "b": h3["b"].lower() + so_far(record),
            "c": h3["c"].lower() + so_far(record), "mean": f'{h3["mean"]:+.2f}'.replace("-", "−"),
            "label": ("The reading of record, to 11 Nov 2026" if record else
                      "To date; the reading of record runs to 11 Nov")}


def h5e_chip(h5e):
    """H5e: the recorded first verdict (8 Oct: FAILS, 0.90) until the FINAL block exists; then the final, with the
    first beside it, so a final HOLDS never hides the recorded failure (8 Nov review)."""
    claim = "Dropping empty bids fixes oil"
    if h5e is None:
        # H5 file, Result: first verdict FAILS, 0.90, closer on 2 of 10 days.
        return chip("H5e", claim, "bad", "fails (first, 8 Oct)", f"0.90 (bar < 0.5); final {DUE}")
    return chip("H5e", claim, KIND[h5e["verdict"]], h5e["verdict"].lower() + " (final)",
                f'{h5e["mae"]} (bar < 0.5); closer on {h5e["closer"]} of {h5e["n"]} days; 8 Oct: fails, 0.90')


def h7_chips(h7):
    """H7a and H7b: due until record_verdict.py's block exists; then its words and numbers. A part below its
    minimum reads NOT READ, which is not a failure, and nothing is due after it: grey "–", not amber "…"."""
    a, b = ("H7a", "Free feed matches the full market"), ("H7b", "Gold's estimate matches GVZ")
    if h7 is None:
        return [chip(*a, "due", DUE, "bar ≤ 0.25"), chip(*b, "due", DUE, "bar ≤ 0.30")]
    return [chip(*a, KIND.get(h7["a"].split()[0], "na"), h7["a"].lower(),
                 f'USO {h7["uso"]}, GLD {h7["gld"]} (bar ≤ 0.25)'),
            chip(*b, KIND.get(h7["b"].split()[0], "na"), h7["b"].lower(), f'{h7["gvz"]} (bar ≤ 0.30)')]


def scorecard(h3, h5e, h7, record):
    """Every hypothesis in hypotheses/README.md's status table as a chip: (confirmatory, side studies)."""
    confirmatory = [
        # H3 file, "The hypothesis": H3a bar under 1.0 vol points; H3b negative; H3c positive slope. Live: h3_scorer.py.
        h3_chip(h3, record),
        # H5 file, Result (corrected 17 Oct): 0.33 over 179 (bar 0.5); 0.67 on the 134 both feeds bid; "holds weakly".
        chip("H5a", "Far quotes near Bloomberg's", "ok", "holds, weakly", "0.33 of a spread (bar 0.5)"),
        # H5 file, Result (corrected 17 Oct): 44 of 44 (bar 80%).
        chip("H5b", "Empty bids are empty there too", "ok", "holds", "44 of 44 (bar 80%)"),
        # H5 file, "H5f, read 25 September 2026": a 0.500 (bar 0.5, ON the bar), b 64 of 64 (bar 80%),
        # c 0.6% median per-day gap (bar 25%).
        chip("H5f", "The same, on the full market", "ok", "holds", "0.500 (on the bar); 64 of 64"),
        # H5 file, Result: "H5c, H5d: descriptive until their 10 underlying-days support the date-clustered test";
        # HANDOFF 18: H5d "12 underlying-days on 3 dates; the date-clustered test needs more dates". H5c: Bloomberg's
        # prices reproduce the inflation (the estimate's overshoot, as registered minus Cboe's rule); H5d: it grows
        # with the share of zero-bid wing contracts. "Overshoot", not "inflation", which reads as prices (8 Nov).
        chip("H5c–d", "Same overshoot on Bloomberg; more with empty bids", "na", "not yet tested", "too few dates"),
        # H5 file, H5e: mean absolute gap under 0.5 AND closer than the registered estimate on a majority of days.
        h5e_chip(h5e),
        # H7 file: H7a free vs OPRA replica, 0.25 or less for USO and GLD; H7b GLD vs GVZ, 0.30 or less;
        # H7c (USO vs OVX) descriptive only.
        *h7_chips(h7),
    ]
    side = [
        # H1 file, Result: H1a 9 of 11 pairs, all 9 survive Benjamini-Hochberg; H1b holds but mixed; H1c holds.
        chip("H1", "The known risk premium, 10 years", "ok", "holds", "9 of 11 pairs"),
        # H2 file, Result: log variance t 16.26, raw variance t 2.14 (H2a holds as recorded). 28 Oct 2026 (outside
        # review M05): the pooled t treats the equity indices' windows as independent though they share market
        # episodes. Companion, Actions run 40720872275 (28 Oct): clustered on date, raw variance t 1.34 (p 0.18).
        # The write-up's words: "holds as recorded; not robust to date clustering or to the price source".
        chip("H2a", "The premium, in variance", "ok", "holds as recorded", "p = 0.18 by date; vendor-sensitive"),
        # H2 file, Result: H2b not supported; companion (28 Oct): on its registered statistic, log lower on 3 of 11.
        # H2b's claim: the log formulation, ln(IV^2) - ln(RV^2), is less autocorrelated than the level one.
        chip("H2b", "Log form less autocorrelated", "bad", "not supported", "3 of 11 pairs"),
        # H4 file / hypotheses README: registered 13 Sep, not yet tested; adjustment log "STRIKE 2 of 3" (8 Oct);
        # "roughly 40 day pairs is enough for both claims".
        chip("H4", "Hedged option gains negative", "na", "not yet tested", "needs ~40 day pairs"),
        # H6 file, Result: implied vol has the lower error in 0 of 9 pairs (bar: at least 7 of 9). Its rival: "the
        # 14-day Average True Range (Wilder 1978)", a range, not a plain average.
        chip("H6a", "Implied vol beats the 14-day average range", "bad", "fails", "0 of 9 pairs (bar 7)"),
        # H6 file, Result: mean d +0.3272 after spikes vs +0.4165 calm; Welch p < 0.0001; Newey-West lag 21
        # p 0.0001, lag 63 p 0.0018.
        chip("H6b", "Its miss shrinks after spikes", "ok", "holds", "0.33 vs 0.42, p < 0.01"),
    ]
    return confirmatory, side


def together(s):
    """A comparison never breaks across lines: no-break spaces beside <, >, =, ≤ and ≥ (8 Nov review: H6b's
    "p <" sat on one line and "0.01" on the next)."""
    return re.sub(r" ([<>=≤≥]) ", " \\1 ", s)


def chip_html(c):
    return (f'<div class="chip {c["kind"]}"><div class="ch"><b>{esc(c["id"])}</b>'
            f'<span class="vd">{ICON[c["kind"]]} {esc(together(c["verdict"]))}</span></div>'
            f'<div class="cl">{esc(together(c["claim"]))}</div>'
            f'<div class="cn">{esc(together(c["number"]))}</div></div>')


# ---------------- the page ----------------
def short_date(d):
    return f"{int(d[8:])} {charts.MONTHS[int(d[5:7]) - 1]}"


def span_label(series, record):
    """The main chart's days, counted against the weekdays they span (a weekday without a reading is not counted
    in any panel), and what they are: to date, or the reading of record."""
    days = sorted({d for rows in series.values() for d, _, _ in rows})
    of = charts.weekday_slot(days[0], days[-1]) + 1
    span = f"{len(days)} of the {of} weekdays, {short_date(days[0])} to {short_date(days[-1])} 2026"
    return span if record else f"{span} (the reading of record runs to 11 Nov)"


def tile_html(t):
    """The sixth cell beside the five panels: H3's pooled number and its three registered parts, each coloured by
    its own verdict (a part that fails is never printed in pass green)."""
    mark = {"holds": ("ok", ICON["ok"]), "fails": ("bad", ICON["bad"])}
    parts = (("a", "Bar, set before the data: under 1.0"),
             ("b", f"Free data reads low on average ({t['mean']})"),
             ("c", "The gap grows when volatility is high"))
    items = "".join('<li class="{0}"><b>{1} H3{2} {3}</b><span>{4}</span></li>'.format(
        *mark.get(t[k].split()[0], ("na", ICON["na"])), k, esc(t[k]), esc(words)) for k, words in parts)
    return (f'<div class="cell tile"><div class="tk">All five funds · {t["n"]} daily readings</div>'
            f'<div class="tv">{t["mae"]}</div><div class="tu">points off Cboe’s index, on average</div>'
            f'<ul class="tl">{items}</ul><div class="tk">{esc(t["label"])}</div></div>')


def main_chart(series, h3):
    """The five panels: per fund, the days counted by their gap (free data minus Cboe's index) in half-point bins,
    on one gap axis and one day axis shared by all five. Aggregate statistics only: no date, no single day's gap
    and no index value reaches the chart. Gabriel's request to Cboe (10 Oct 2026, repeated 21 Oct; approved 4 Nov):
    "Only aggregate statistics appear (for example, average differences between my estimates and the index)"; daily
    gaps would give each close back to anyone holding the public daily estimates (Astra review, 8 Nov 2026)."""
    gaps = {s: [o - c for _, o, c in series[s]] for s, _, _ in PAIRS}
    bins = {s: charts.bin_counts(g) for s, g in gaps.items()}
    ks = [k for b in bins.values() for k in b]
    scale = charts.shared_scale([min(ks) * charts.BIN, (max(ks) + 1) * charts.BIN])    # every bin's far edge
    counts = charts.count_scale(max(n for b in bins.values() for n in b.values()))
    return "".join(f'<div class="cell">{charts.gap_histogram(s, ix, what, gaps[s], h3["per"][s][1], scale, counts)}'
                   f'</div>' for s, ix, what in PAIRS)


def build(today=None, force_headline=None, out_dir=OUT):
    today = today or date.today()
    h3, series = h3_live()
    h5e = h5e_final(H5_FILE.read_text())
    h7 = h7_reading(H7_FILE.read_text())
    record = of_record(series, today)
    conf, side = scorecard(h3, h5e, h7, record)
    head = headline(h3, h7) if force_headline is None else HEADLINES[force_headline]
    long = " long" if len(" ".join(head)) > 64 else ""
    ai = (f'<p class="ai">{esc(AI_LINE)}</p>' if AI_LINE_APPROVED else
          f'<p class="ai draft"><span class="tag">DRAFT, for Gabriel to approve</span> {esc(AI_LINE)}</p>')
    panels = main_chart(series, h3)
    finals = ("The final readings of H5e and H7 are in the strip below." if h5e and h7 else
              "12–19 Nov: the final readings of H5e and H7, as registered.")

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
  <div class="kicker">On the evidence so far</div>
  <div class="big{long}">{esc(head[0])} <em>{esc(head[1])}</em></div>
</section>
<main class="body">
  <section class="col left">
    <div><h2><span class="n">1</span>The question</h2>
      <p>Students and small researchers price options with <b>free quotes</b>, because the full market feed costs
      thousands of dollars a year. What precision does free data give up, and <b>where</b> is the loss: in the
      quotes, or in the recipe that turns them into a volatility number?</p>
      <p class="why"><b>Why it matters:</b> if the error lies in the method rather than the data, anyone without a
      data budget can remove most of it for free.</p></div>
    <div><h2><span class="n">2</span>What I did</h2>
      <div class="flow">
        <div class="box"><b>Free quotes</b> from a retail brokerage (Alpaca), recorded daily since September
        2026: 109 tickers</div>
        <div class="arrow">↓ the VIX formula, with strikes and expiries I chose</div>
        <div class="box"><b>A volatility number</b> per fund per day: the swing the market expects over the next
        30 days</div>
        <div class="arrow">↓ checked against</div>
        <div class="refs"><div>Cboe's published indices</div><div>The full market feed (OPRA)</div>
        <div>Bloomberg</div></div>
      </div></div>
    <div><h2>How it stays honest</h2>
      <ul>
        <li>Every pass/fail bar was <b>written before its test ran</b>, dated in a public repository; H5e and H7
            were also frozen on <b>OSF</b>.</li>
        <li>A <b>second program sharing no code</b> recomputed every recorded result on 17 Oct, catching one
            spreadsheet-reading bug (fixed; no verdict changed).</li>
        <li>Failures are reported beside successes: see the strip below.</li>
      </ul></div>
    <div><h2>What's next</h2>
      <ul>
        <li>{finals}</li>
        <li>Dec–Jan: a confirmatory test on eight funds and stocks, registered first.</li>
        <li>2027: the paper, failures included.</li>
      </ul></div>
    <div class="limits"><h2>Limits</h2>
      <p>One free feed; about two months of data; one snapshot a day, since October about 80 minutes before the
      close (in stress months the estimate drifts a median 0.53 points between 14:30 and 15:55); American options
      priced with European formulas; far contracts nobody quotes can carry hours-old free quotes.</p></div>
  </section>
  <section class="col center">
    <h2><span class="n">3</span>Free data tracks Cboe's index</h2>
    <div class="legend"><span><i class="sw up"></i>Cboe's published index (zero gap)</span>
      <span><i class="sw bar"></i>Days at each gap</span><span><i class="sw band"></i>Within 1 point</span></div>
    <div class="grid">{panels}{tile_html(h3_tile(h3, record))}</div>
    <p class="cap">Bars count the days at each gap: the free-data estimate minus Cboe's published index, in
    volatility points (a VIX of 20 means swings of about 20% a year); left of zero, free data reads low. One scale
    for all five;
    {span_label(series, record)}. The estimate uses a ±30% strike band (see 5).</p>
  </section>
  <section class="col right">
    <div><h2><span class="n">4</span>The quotes: close to the professional feeds</h2>
      <div class="kpi"><b>{EMPTY_BIDS[0]}</b><span>far-out options with no bid (no buyer) on the free feed had
      no bid on the full market either (Bloomberg: {EMPTY_BIDS[1]})</span></div>
      <p class="cap">How far the free price sits from the professional one, in bid-ask spreads (the gap between
      the buy and sell quotes; medians), far strikes on USO and TSLA, Sep 2026:</p>
      {charts.quote_scale(QUOTE_FEEDS, QUOTE_BAR)}
      <p class="cap">Filled: all far strikes; hollow: only those both feeds bid. Both passes rest on strikes one
      feed left unbid; where both bid, the gap is over the bar, though only a tick or two. Source: Bloomberg
      Finance L.P. Data provided by Databento (OPRA).</p></div>
    <div><h2><span class="n">5</span>The recipe: widen the strikes, and the gap shrinks</h2>
      <p class="lead">A fixed ±10% band of strikes sees almost all of a calm fund's likely moves, but under half
      of oil's:</p>
      {charts.coverage_curves(CALM, WILD)}
      <p class="cap">30-day price moves under a simple model. {esc(TRUNCATION_WHY)}</p>
      <p class="lead">Widen the band: the average gap falls from {BANDS[0][2]:.2f} to {BANDS[-1][2]:.2f} points</p>
      {charts.band_bars(BANDS)}
      <p class="cap">Mean absolute gap to Cboe's index, five fund–index pairs, one calibration day (11 Sep 2026);
      worst: the pair furthest off (minus: reads low). At ±30%, SPY read {SPY_VS_VIX[0]} against a VIX of
      {SPY_VS_VIX[1]}. This shows a coverage effect; it does not by itself rule out the feed's own error, the
      snapshot's timing or the index-versus-fund difference.</p></div>
  </section>
</main>
<footer class="bottom">
  <div class="tests"><h3>Every registered hypothesis, H1–H7, scored against a bar set before its test ran</h3>
    <div class="row"><div class="rl">The free-data question</div>{chips(conf)}</div>
    <div class="row"><div class="rl">Side studies (H1 checks the method)</div>{chips(side)}</div></div>
  <div class="qr"><div id="qr"></div>Data, code and every registration: scan me</div>
  <div class="credits">
    <p><b>Acknowledgments.</b> I thank Marc Vinyard for mentoring this project and for library data access.</p>
    {ai}
    <p>Data provided by Databento (OPRA consolidated NBBO). Bloomberg figures: Source: Bloomberg Finance L.P.
    Index values © Cboe Global Markets. This product uses the FRED® API but is not endorsed or certified by the
    Federal Reserve Bank of St. Louis. Options quotes: Alpaca indicative feed, personal, non-commercial use.
    Derived figures only; an index level is quoted only where a result depends on it. Registration:
    <span class="nw">{OSF.removeprefix("https://")}</span> · <span class="nw">{SITE.removeprefix("https://")}</span></p>
  </div>
</footer>
"""
    page = PAGE.replace("@@TITLE@@", html.escape(TITLE)).replace("@@CHECK@@", CHECK_JS).replace("@@CSS@@", CSS).replace("@@BODY@@", body).replace("@@SITE@@", SITE)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "poster.html").write_text(page)
    return out_dir / "poster.html"


CSS = """
  @page { size: 48in 36in; margin: 0; }
  :root { --navy:#0b2447; --ink:#14213d; --mute:#4f5a6d; --rule:#d3d9e3; --orange:#e35205; --cboe:#1f4e9c;
          --tint:#f3f5f9; --ok:#1f7a4d; --bad:#b42318; --due:#8a6d00; --na:#56607a; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html, body { width:48in; height:36in; background:#fff; color:var(--ink); font-family:Inter, system-ui, sans-serif;
               font-size:40px; line-height:1.35; -webkit-print-color-adjust:exact; print-color-adjust:exact;
               overflow:hidden; }
  .poster { display:grid; grid-template-rows:auto auto minmax(0, 1fr) auto; width:48in; height:36in; overflow:hidden; }
  .banner { background:var(--navy); color:#fff; padding:0.42in 0.8in 0.4in; display:flex;
            justify-content:space-between; align-items:flex-end; gap:1in; }
  h1 { font:800 120px/1.0 'Inter Tight'; letter-spacing:-0.01em; }
  .subtitle { font:600 56px/1.15 'Inter Tight'; color:#c9d5e8; margin-top:0.14in; }
  .who { text-align:right; font-size:37px; line-height:1.32; color:#dbe4f3; flex:none; }
  .who .name { font:700 56px/1.15 'Inter Tight'; color:#fff; margin-bottom:0.04in; }
  .headline { padding:0.3in 0.8in 0.28in; border-bottom:4px solid var(--rule); }
  .kicker { font:700 36px/1.2 'Inter Tight'; letter-spacing:0.12em; text-transform:uppercase; color:var(--orange); }
  .big { font:800 112px/1.05 'Inter Tight'; color:var(--navy); letter-spacing:-0.015em; margin-top:0.05in; }
  .big.long { font-size:96px; }
  .big em { font-style:normal; color:var(--orange); }
  .body { display:grid; grid-template-columns:10.4in minmax(0, 1fr) 14.4in; gap:0.6in;
          padding:0.36in 0.8in 0.3in; min-height:0; }
  .col { display:flex; flex-direction:column; gap:0.26in; min-height:0; overflow:hidden; }
  h2 { font:700 48px/1.12 'Inter Tight'; color:var(--navy); padding-bottom:0.08in; border-bottom:6px solid var(--orange);
       margin-bottom:0.14in; display:flex; align-items:center; gap:0.18in; }
  h2 .n { flex:none; width:0.64in; height:0.64in; border-radius:50%; background:var(--navy); color:#fff;
          display:inline-flex; align-items:center; justify-content:center; font-size:40px; }
  .left { font-size:36px; }
  .left p, .left li { line-height:1.32; text-wrap:pretty; }
  .nw { white-space:nowrap; }
  ul { padding-left:0.4in; } li + li { margin-top:0.06in; }
  .flow { display:flex; flex-direction:column; gap:0.06in; }
  .flow .box { background:var(--tint); border-left:10px solid var(--navy); padding:0.1in 0.18in; font-size:35px; line-height:1.28; }
  .flow .arrow { font:700 35px/1.2 'Inter Tight'; color:var(--orange); padding-left:0.24in; }
  .flow .refs { display:grid; grid-template-columns:repeat(3, 1fr); gap:0.1in; }
  .flow .refs div { background:var(--navy); color:#fff; padding:0.1in 0.12in; font:700 33px/1.18 'Inter Tight';
                    text-align:center; border-radius:8px; display:flex; align-items:center; justify-content:center; }
  .limits p { font-size:33px; color:var(--mute); line-height:1.3; }
  .legend { display:flex; gap:0.6in; font-size:35px; color:var(--mute); margin:-0.04in 0 0.04in; }
  .sw { display:inline-block; width:0.6in; height:0; border-top:6px solid var(--cboe); vertical-align:middle; margin-right:0.14in; }
  .sw.bar { width:0.16in; height:0.34in; border:none; border-radius:3px 3px 0 0; background:var(--orange); }
  .sw.band { width:0.5in; height:0.3in; border:none; background:#e9eef6; }
  .sw.up { width:0; height:0.34in; border-top:none; border-left:6px solid var(--cboe); }
  .grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); grid-auto-rows:minmax(0, 1fr);
          gap:0.22in 0.45in; flex:1; min-height:0; }
  .cell { min-height:0; display:flex; align-items:center; justify-content:center; }
  .cell svg.chart { width:100%; height:100%; display:block; }
  .tile { background:var(--tint); border-radius:20px; padding:0.24in 0.34in; flex-direction:column;
          align-items:flex-start; justify-content:center; }
  .tile .tk { font-size:33px; color:var(--mute); }
  .tile .tv { font:800 136px/1.0 'Inter Tight'; color:var(--navy); margin:0.04in 0 0; }
  .tile .tu { font:700 38px/1.2 'Inter Tight'; color:var(--ink); margin-bottom:0.12in; }
  .tile .tl { list-style:none; padding:0; font-size:33px; line-height:1.25; }
  .tile .tl li + li { margin-top:0.07in; }
  .tile .tl b { display:block; font-family:'Inter Tight'; color:var(--na); }
  .tile .tl .ok b { color:var(--ok); } .tile .tl .bad b { color:var(--bad); }
  .cap { font-size:33px; color:var(--mute); line-height:1.28; }
  .lead { font:700 38px/1.24 'Inter Tight'; color:var(--ink); }
  .right > div { display:flex; flex-direction:column; gap:0.1in; }
  .right svg.chart { width:100%; height:auto; display:block; }
  .kpi { display:flex; align-items:center; gap:0.3in; }
  .kpi b { font:800 100px/1.0 'Inter Tight'; color:var(--navy); white-space:nowrap; }
  .kpi span { font-size:35px; line-height:1.28; }
  .why { margin-top:0.12in; padding-left:0.2in; border-left:8px solid var(--orange); }
  .why b { color:var(--navy); }
  .bottom { display:grid; grid-template-columns:minmax(0, 1fr) 3.2in 11.2in; gap:0.45in; align-items:start;
            padding:0.26in 0.8in 0.36in; background:var(--tint); border-top:4px solid var(--rule); }
  .tests h3 { font:700 38px/1.2 'Inter Tight'; color:var(--navy); margin-bottom:0.12in; }
  .tests .row { display:grid; grid-template-columns:2.2in repeat(8, minmax(0, 1fr)); gap:0.1in; }
  .tests .row + .row { margin-top:0.1in; }
  .tests .rl { font:700 32px/1.2 'Inter Tight'; color:var(--mute); align-self:center; }
  .chip { background:#fff; border:3px solid var(--rule); border-top:10px solid var(--na); border-radius:10px;
          padding:0.05in 0.09in 0.07in; font-size:32px; line-height:1.17; }
  .chip.ok { border-top-color:var(--ok); } .chip.bad { border-top-color:var(--bad); } .chip.due { border-top-color:var(--due); }
  .chip .ch { display:flex; flex-wrap:wrap; justify-content:space-between; column-gap:0.1in; font-family:'Inter Tight'; }
  .chip .ch b { color:var(--navy); }
  .chip .vd { font-weight:700; margin-left:auto; text-align:right; }
  .chip.ok .vd { color:var(--ok); } .chip.bad .vd { color:var(--bad); } .chip.due .vd { color:var(--due); }
  .chip.na .vd { color:var(--na); }
  .chip .cl { margin-top:0.03in; }
  .chip .cn { color:var(--mute); margin-top:0.03in; }
  .qr { background:#fff; padding:0.12in 0.12in 0.16in; border-radius:16px; text-align:center; color:var(--ink);
        font-size:32px; line-height:1.2; }
  .qr #qr { width:2.95in; height:2.95in; margin:0 auto 0.06in; }
  .qr svg { display:block; width:100%; height:100%; shape-rendering:crispEdges; }
  .credits { font-size:32px; line-height:1.25; color:var(--mute); }
  .credits p + p { margin-top:0.08in; }
  .credits b { color:var(--ink); }
  .ai.draft { border:4px dashed var(--bad); padding:0.06in 0.12in; color:var(--ink); }
  .ai .tag { font-weight:800; color:var(--bad); }
"""

TITLE = "What Does Free Options Data Cost? (SCCUR 2026 poster)"

# The page check, for render(): run once the web fonts and the QR code are in. It records the smallest text in CSS
# px (SVG text scaled by its transform), any column whose content overflows, whether the QR code is vector SVG, any
# font family the text asks for first that no loaded web font supplies (or a web font that failed), chart labels
# running outside their chart, and chart labels drawn over each other - by the boxes Chrome itself gives each label,
# not an estimate (Astra, 8 Nov 2026). The verdict fields are appended to the page title as well: Chrome writes the
# title into the PDF it prints, so the printed file carries the check of the run that made it. 11 Nov 2026 (Astra):
# the smallest size is reported unrounded (31.996 px had rounded to 32 and passed), and a label may cross its chart's
# edge or another label's box only by numerical error (TOL), not by the whole pixel the first version allowed.
CHECK_JS = r"""
window.addEventListener("load", async () => {
  await document.fonts.ready;
  await new Promise(r => setTimeout(r, 400));
  let min = 1e9, where = "";
  const fams = new Set();
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode, el = t.parentElement;
    if (!t.textContent.trim() || el.closest("script,style")) continue;
    const cs = getComputedStyle(el);
    let px = parseFloat(cs.fontSize);
    if (el instanceof SVGElement) { const m = el.getScreenCTM(); px *= Math.hypot(m.a, m.b); }
    if (px < min) { min = px; where = t.textContent.trim().slice(0, 48); }
    fams.add(cs.fontFamily.split(",")[0].replace(/["']/g, "").trim());
  }
  const faces = [...document.fonts];
  const fonts = [...fams].filter(f => !faces.some(x => x.family.replace(/["']/g, "") === f && x.status === "loaded"))
    .concat(faces.filter(x => x.status === "error").map(x => `${x.family} ${x.weight}: failed`));
  const over = [...document.querySelectorAll(".poster, .poster > *, .col")]
    .filter(s => s.scrollHeight > s.clientHeight + 1 || s.scrollWidth > s.clientWidth + 1)
    .map(s => s.className || s.tagName);
  const clipped = [], overlaps = [], TOL = 0.01;   // CSS px: layout snaps boxes to 1/64 px; touching is not over
  for (const s of document.querySelectorAll("svg")) {
    const b = s.getBoundingClientRect();
    const ts = [...s.querySelectorAll("text")].map(t => [t.textContent.trim(), t.getBoundingClientRect()]);
    ts.forEach(([t, r], i) => {
      if (r.left < b.left - TOL || r.right > b.right + TOL || r.top < b.top - TOL || r.bottom > b.bottom + TOL) clipped.push(t);
      for (const [u, q] of ts.slice(i + 1))
        if (Math.min(r.right, q.right) - Math.max(r.left, q.left) > TOL &&
            Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top) > TOL) overlaps.push(`${t} / ${u}`);
    });
  }
  // Room left at the foot of each column, in CSS px (what the layout can still take; negative never shows,
  // because a column that runs over is caught above).
  const room = Object.fromEntries([...document.querySelectorAll(".col")].map(c => [c.className.split(" ")[1],
    Math.round(c.getBoundingClientRect().bottom - Math.max(...[...c.children].map(k => k.getBoundingClientRect().bottom)))]));
  const words = document.body.innerText.split(/\s+/).filter(x => /[A-Za-z0-9]/.test(x)).length;
  const qr = document.querySelector("#qr svg") ? "svg" : (document.querySelector("#qr img, #qr canvas") ? "raster" : "none");
  const v = {minPx: min, overflow: over.length, qr, fonts: fonts.length,
             clipped: clipped.length, overlaps: overlaps.length};
  document.body.dataset.check = JSON.stringify({...v, where, room, words, detail: {overflow: over, fonts, clipped, overlaps}});
  document.title += " | check " + JSON.stringify(v);
});
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>@@TITLE@@</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;700;800&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>@@CSS@@</style></head>
<body><div class="poster">
@@BODY@@
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js" integrity="sha384-3zSEDfvllQohrq0PHL1fOXJuC/jSOO34H46t6UQfobFOmxE5BpjjaIJY5F2/bMnU" crossorigin="anonymous"></script>
<script>
// qrcodejs encodes; the poster draws its module matrix as one vector path (runs of dark modules), with the
// standard 4-module quiet zone, so the printed code stays sharp at any size.
(() => {
  const tmp = document.createElement("div");
  const m = new QRCode(tmp, {text:"@@SITE@@", width:64, height:64, correctLevel:QRCode.CorrectLevel.M})._oQRCode;
  const n = m.getModuleCount(), qz = 4, s = n + 2 * qz;
  let d = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    if (!m.isDark(r, c) || (c > 0 && m.isDark(r, c - 1))) continue;
    let k = c; while (k + 1 < n && m.isDark(r, k + 1)) k++;
    d += `M${c + qz} ${r + qz}h${k - c + 1}v1h-${k - c + 1}z`;
  }
  document.getElementById("qr").innerHTML = `<svg viewBox="0 0 ${s} ${s}" role="img" aria-label="QR code: @@SITE@@">`
    + `<rect width="${s}" height="${s}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
})();
</script>
<script>@@CHECK@@</script>
</body></html>
"""

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def chrome(args, out=None):
    """Headless Chrome, judged by what it produced, never by its exit code alone. 31 Oct 2026: under heavy load
    Chrome wrote the complete PDF and then exited 2 ("Teardown watchdog expired") - the file was whole, the exit
    code was not. 8 Nov 2026 (Astra): the reverse, a zero exit with no new file, would have let render() check an
    older poster.pdf. So `out` is deleted before each run, and a run counts only if it produced its output: the
    file at `out`, else the dumped page with its check. Otherwise once more, then fail with Chrome's last words."""
    for _ in range(2):
        if out:
            out.unlink(missing_ok=True)
        p = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000",
                            *args], capture_output=True, text=True)
        if (out.exists() and out.stat().st_size > 0) if out else 'data-check="' in p.stdout:
            return p
    raise SystemExit(f"Chrome produced no fresh output twice (exit {p.returncode}): "
                     + " | ".join(p.stderr.splitlines()[-3:]))


def pdf_check(pdf):
    """The page check of the Chrome run that printed `pdf` (bytes): the fields the page appended to its title, which
    Chrome writes as the PDF's /Title. None if they are not there (the check had not finished when Chrome printed)."""
    m = re.search(rb"/Title\s*\(((?:\\.|[^\\)])*)\)", pdf)
    title = re.sub(rb"\\(.)", rb"\1", m[1]).decode("latin-1") if m else ""
    _, mark, fields = title.partition(" | check ")
    return json.loads(fields) if mark else None


def pdf_whole(pdf):
    """True if `pdf` (bytes) was written to its end: it closes with startxref and %%EOF, and startxref points at the
    cross-reference table, which Chrome writes as a classic table (checked on the 11 Nov poster). These come last,
    so a file cut short fails (Astra, 11 Nov 2026: the title, the page count and the MediaBox can all sit in a
    truncated file). A PDF with a compressed xref stream would be refused, loudly, not passed."""
    m = re.search(rb"startxref\s+(\d+)\s+%%EOF\s*$", pdf)
    return bool(m) and pdf[int(m[1]):int(m[1]) + 4] == b"xref"


def png_size(png):
    """(width, height) of a PNG (bytes) that decodes whole, else None: the signature, every chunk's checksum, a
    header, image data that inflates to exactly the rows the header promises, and the end chunk (Astra, 11 Nov 2026)."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i, head, data = 8, None, []
    while i + 12 <= len(png):
        n = int.from_bytes(png[i:i + 4], "big")
        kind, body, crc = png[i + 4:i + 8], png[i + 8:i + 8 + n], png[i + 8 + n:i + 12 + n]
        if len(body) != n or len(crc) != 4 or zlib.crc32(kind + body) != int.from_bytes(crc, "big"):
            return None
        if kind == b"IEND":
            break
        head = body if kind == b"IHDR" else head
        data += [body] if kind == b"IDAT" else []
        i += 12 + n
    else:
        return None                                        # no end chunk: cut short
    if not head or len(head) != 13 or not data or head[12] != 0:      # interlaced is not what sips writes
        return None
    w, h, bits = int.from_bytes(head[:4], "big"), int.from_bytes(head[4:8], "big"), head[8]
    per = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(head[9])                   # samples a pixel, by colour type
    try:
        rows = zlib.decompress(b"".join(data))
    except zlib.error:
        return None
    return (w, h) if per and len(rows) == h * (1 + (w * per * bits + 7) // 8) else None


SIPS = "/usr/bin/sips"


def raster(pdf, png):
    """Draw the preview from the PDF itself with macOS's own sips (3456 x 2592 px, a pixel a point). Astra, 11 Nov
    2026: the preview came from a Chrome run of its own whose page check nothing read. Drawn from the checked PDF,
    it shows exactly what was checked, and a PDF that sips cannot read gives no preview."""
    subprocess.run([SIPS, "-s", "format", "png", str(pdf), "--out", str(png)], capture_output=True, text=True)


def problems(chk):
    """What fails the page check. The measured page and the printed PDF's title carry the same fields. The smallest
    size arrives unrounded; 1e-6 px allows float noise only (Astra, 11 Nov 2026)."""
    return [why for bad, why in ((chk["minPx"] < 32 - 1e-6, "text below 24 pt"),
                                 (chk["overflow"], "a column overflows"),
                                 (chk["qr"] != "svg", "QR code is not vector SVG"),
                                 (chk["fonts"], "web fonts did not load"),
                                 (chk["clipped"], "chart text runs outside its chart"),
                                 (chk["overlaps"], "chart labels overlap")) if bad]


def render(path):
    """poster.pdf and preview.png beside the HTML at `path`, then the checks. The PDF is judged by the run that
    printed it: the page appends its check to its title, which Chrome writes into the PDF (Astra, 8 Nov 2026: the
    PDF, the preview and the measured page come from three runs, so a later run's check could vouch for an earlier
    file). The measured page adds the details for the report. poster.pdf and preview.png exist only after a render
    that passed: older ones are cleared first, the new ones are written as *.unchecked.*, and those are renamed to
    the poster's names on a pass or to *.FAILED-CHECK.* on a failure (a run that dies leaves them unchecked). 11 Nov
    2026 (Astra): the PDF must be written to its end, and the preview is drawn from it (raster), so it is the checked
    page itself and proves the PDF can be read; a preview that does not decode as one 4:3 page fails the render."""
    pdf_path, png_path = path.with_name("poster.pdf"), path.with_name("preview.png")
    new_pdf, new_png = path.with_name("poster.unchecked.pdf"), path.with_name("preview.unchecked.png")
    for old in (pdf_path, png_path, *path.parent.glob("*.FAILED-CHECK.*"), *path.parent.glob("*.unchecked.*")):
        old.unlink(missing_ok=True)
    big = "--window-size=4608,3456"
    chrome([f"--print-to-pdf={new_pdf}", "--no-pdf-header-footer", big, path.as_uri()], new_pdf)
    dom = chrome([big, "--dump-dom", path.as_uri()]).stdout
    chk = json.loads(html.unescape(re.search(r'data-check="([^"]*)"', dom)[1]))     # chrome() returned only with it
    pdf = new_pdf.read_bytes()
    whole = pdf_whole(pdf)
    if whole:
        raster(new_pdf, new_png)
    size = png_size(new_png.read_bytes()) if new_png.exists() else None
    printed = pdf_check(pdf)
    boxes = re.findall(rb"/MediaBox\s*\[\s*0 0 ([\d.]+) ([\d.]+)\s*\]", pdf)
    pages = len(re.findall(rb"/Type\s*/Page\b", pdf))
    d = chk["detail"]
    print(f"check: smallest text {chk['minPx']:g}px = {chk['minPx'] * 0.75:g}pt ('{chk['where']}'); "
          f"{chk['words']} words; QR {chk['qr']}; overflow {d['overflow'] or 'none'}; fonts {d['fonts'] or 'loaded'}; "
          f"chart labels clipped {d['clipped'] or 'none'}, overlapping {d['overlaps'] or 'none'}; "
          f"room left (px) {chk['room']}; PDF pages {pages}, MediaBox {[b.decode() for b in boxes[0]] if boxes else '?'}, "
          f"{'written to its end' if whole else 'CUT SHORT'}; preview from the PDF {size or 'none'}; "
          f"the PDF's own check: {'missing' if printed is None else (problems(printed) or 'passed')}")
    bad = problems(chk) + (["the printed PDF carries no page check"] if printed is None
                           else [f"in the printed PDF, {p}" for p in problems(printed)])
    if pages != 1 or not boxes or boxes[0] != (b"3456", b"2592"):
        bad.append("PDF is not one 48 x 36 in page")
    if not whole:
        bad.append("the PDF was not written to its end")
    elif not size or size[0] * 3 != size[1] * 4 or size[0] < 2304:
        bad.append("the preview drawn from the PDF is not one whole 48 x 36 in page")
    if bad:
        new_pdf.replace(path.with_name("poster.FAILED-CHECK.pdf"))
        if new_png.exists():
            new_png.replace(path.with_name("preview.FAILED-CHECK.png"))
        raise SystemExit("poster check failed: " + "; ".join(bad) + " (outputs renamed *.FAILED-CHECK.*)")
    new_pdf.replace(pdf_path)
    new_png.replace(png_path)
    return pdf_path, png_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="also render poster.pdf and preview.png with Chrome")
    ap.add_argument("--today", help="YYYY-MM-DD, to preview the H3 label on another date (default: today)")
    ap.add_argument("--headline", type=int, choices=range(len(HEADLINES)),
                    help="PREVIEW ONLY: force headline 0, 1 or 2 (the decided one and its two fallbacks) to check "
                         "that each fits; written to a temporary folder, never to poster/")
    a = ap.parse_args()
    where = Path(tempfile.mkdtemp(prefix="poster-headline-")) if a.headline is not None else OUT
    p = build(date.fromisoformat(a.today) if a.today else None, a.headline, where)
    print(f"wrote {p}")
    if a.pdf:
        print("wrote {} and {}".format(*render(p)))
