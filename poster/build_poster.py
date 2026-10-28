"""Build the SCCUR 2026 poster (48 x 36 in, landscape) from the project's own records.

    .../python3 poster/build_poster.py            # writes poster/poster.html
    .../python3 poster/build_poster.py --pdf      # also poster/poster.pdf and poster/preview.png (Chrome)
    .../python3 poster/test_build_poster.py       # the verdict-box parsers against record_verdict's own writer

Frozen results are copied below with the file they come from. The live boxes are filled by
the project's own readers, never typed by hand:
  - H3: tools/h3_scorer.py (its H3a/H3b/H3c lines); "so far" until 11 Nov 2026, the reading of
    record after it;
  - H5e FINAL and H7: the blocks tools/record_verdict.py writes into the hypothesis files.
    Until a block exists its box says when the reading is due; it never shows a preview.
    A block that is present but not recognised stops the build (the poster never guesses).
Aggregates only, with each source's credit line (licensed raw data never appears).
The --pdf render also checks the page: smallest text >= 32 CSS px (24 pt at 48 x 36 in), no
column overflowing, the QR code drawn as vector SVG, one 3456 x 2592 pt page.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "poster"
sys.path.insert(0, str(ROOT / "tools"))
from record_verdict import MARK_H5E_FINAL, MARK_H7  # noqa: E402  (the marks the writer uses)

# ---------------- the switches ----------------
# The headline, (plain sentence, orange sentence). One-line switch. Chosen 21 Oct 2026 (research report, option 3).
HEADLINE = ("The free quotes are close.", "Most of the error is in the recipe.")
# HEADLINE = ("The free quotes aren't the problem.", "The recipe is.")     # the first draft's headline

# The fallback, decided by Gabriel on 21 Oct 2026, BEFORE H7's verdict: if H7 is written and either part
# FAILS, the headline no longer claims the split and says only what H3 supports. If H3 had failed too
# (it reads 0.45 against 1.0 on 21 Oct), the most cautious option of the research report is used.
HEADLINE_IF_H7_FAILS = ("Widen the strikes,", "and free data lands within a point of Cboe's index.")
HEADLINE_IF_H7_AND_H3_FAIL = ("So far, free data loses more", "to the method than to the quotes.")

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
DUE = "reading due 12–19 Nov"            # record_verdict.py: due 12 Nov, written by COMPLETE_BY = 19 Nov at the latest

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

# The quotes. H5 file, Result: H5a corrected 17 Oct (0.33 over 179 wing contracts; 0.67 on the 134 both feeds
# bid; verdict unchanged); "H5f, read 25 September 2026": H5f-a 0.500 over 466 wing contracts (ON the bar),
# H5f-b 64 of 64, H5f-c 0.6% (median per-day gap). TEST-INVENTORY.md: H5f-a's median is exactly 1/2.
QUOTE_STATS = [
    ("0.33", "of a bid-ask spread from Bloomberg (median, 179 far-strike contracts)"),
    ("0.500", "from the consolidated market, same minute (466 contracts): on its bar"),
    ("64 / 64", "free-feed missing bids also missing there"),
]


class Unrecognised(ValueError):
    """A reader's output or a verdict block is present but not in the form expected: stop, never guess."""


# ---------------- live readers ----------------
H3_LINE_A = re.compile(r"^H3a (HOLDS|FAILS): pooled mean \|gap\| ([\d.]+) vs bar under 1\.0 "
                       r"\((\d+) readings over (\d+) days\)", re.M)
H3_LINE_B = re.compile(r"^H3b (HOLDS|FAILS): pooled mean gap ([+-][\d.]+) \(registered: negative\)", re.M)
H3_LINE_C = re.compile(r"^H3c (HOLDS|FAILS): pooled slope of \|gap\| on the index level", re.M)


def parse_h3(out):
    """tools/h3_scorer.py's report -> dict. Raises Unrecognised if any registered line is missing."""
    if f"readings to {H3_RECORD_DAY.isoformat()}" not in out:
        raise Unrecognised("h3_scorer.py no longer reads to 2026-11-11 - the poster will not guess:\n" + out)
    a, b, c = H3_LINE_A.search(out), H3_LINE_B.search(out), H3_LINE_C.search(out)
    if not (a and b and c):
        raise Unrecognised("h3_scorer.py output not recognised - the poster will not guess:\n" + out)
    return {"verdict": a[1], "mae": float(a[2]), "n": int(a[3]), "days": int(a[4]), "b": b[1], "c": c[1]}


def h3_live():
    """H3's lines from the frozen scorer, e.g. 'pooled mean |gap| 0.448 vs bar under 1.0 (125 readings over 25 days)'."""
    out = subprocess.run([sys.executable, str(ROOT / "tools/h3_scorer.py")], cwd=ROOT,
                         capture_output=True, text=True, env={"FRED_KEY": "use-cache", "PATH": "/usr/bin:/bin"})
    return parse_h3(out.stdout + out.stderr)


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
    mae = re.search(r"^- Mean absolute gap of the skip-only estimate to OVX: ([\d.]+) volatility points", b, re.M)
    days = re.search(r"^- Closer to OVX than the registered estimate on (\d+) of (\d+) counted days", b, re.M)
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


# ---------------- table cells ----------------
def esc(s):
    return html.escape(str(s), quote=False)


def pill(text, kind=None):
    if kind is None:
        first = text.split()[0] if text else ""
        kind = {"HOLDS": "ok", "FAILS": "bad"}.get(first, "due")
        if text.startswith(("H7a ", "H7b ")):
            kind = {"HOLDS": "ok", "FAILS": "bad"}.get(text.split()[1], "due")
    return f'<span class="pill {kind}">{esc(text)}</span>'


def note(text):
    return f'<span class="vnote">{esc(text)}</span>'


def h3_cells(h3, today):
    """(measured, verdict) for H3. 'so far' until 11 Nov 2026; after it, the reading of record."""
    record = today > H3_RECORD_DAY
    measured = f'{h3["mae"]:.2f} over {h3["n"]} readings'
    measured += "; reading of record, to 11 Nov" if record else "; of record 11 Nov"
    verdict = pill(h3["verdict"] if record else f'{h3["verdict"]} so far')
    others = f'H3b {h3["b"]}, H3c {h3["c"]}' if h3["b"] != h3["c"] else f'H3b, H3c: {h3["b"]}'
    return esc(measured), verdict + note(others)


def h5e_cells(h5e):
    """(measured, verdict) for H5e. Before the FINAL block exists: the recorded first verdict and 'due'."""
    first = "first (8 Oct): 0.90; closer on 2 of 10"   # H5 file, Result: first verdict FAILS, 0.90, 2 of 10 days
    if h5e is None:
        return esc(first), pill("FAILS") + note("first verdict") + pill("final: " + DUE, "due")
    measured = f'final: {h5e["mae"]}; closer on {h5e["closer"]} of {h5e["n"]}; {first}'
    return esc(measured), pill(h5e["verdict"]) + note("final reading")


def h7_cells(h7):
    """(measured, verdict) for H7. Before its block exists: the window and 'due'."""
    if h7 is None:
        return esc("window 9 Oct – 11 Nov"), pill(DUE, "due")
    measured = (f'a: USO {h7["uso"]} ({h7["uso_n"]} days), GLD {h7["gld"]} ({h7["gld_n"]}); '
                f'b: {h7["gvz"]} ({h7["n"]} days)')
    return esc(measured), pill(f'H7a {h7["a"]}') + pill(f'H7b {h7["b"]}')


def test_rows(h3, h5e, h7, today):
    """Every hypothesis in hypotheses/README.md's status table. (id, plain test, bar, measured, verdict html)."""
    h3m, h3v = h3_cells(h3, today)
    h5em, h5ev = h5e_cells(h5e)
    h7m, h7v = h7_cells(h7)
    confirmatory = [
        # H3 file, "The hypothesis": H3a bar under 1.0 vol points; H3b negative; H3c positive slope. Live: h3_scorer.py.
        ("H3", "Free quotes through Cboe's formula track its index", "mean gap under 1.0", h3m, h3v),
        # H5 file, Result (corrected 17 Oct): 0.33 over 179 (bar 0.5); 0.67 on the 134 both feeds bid; "holds weakly".
        ("H5a", "Far-strike free quotes sit near Bloomberg's", "within 0.5 of a spread",
         esc("0.33 (179 contracts); 0.67 where both bid"), pill("HOLDS") + note("weakly")),
        # H5 file, Result (corrected 17 Oct): 44 of 44 (bar 80%).
        ("H5b", "Missing bids are missing on Bloomberg too", "80% or more", esc("44 of 44"), pill("HOLDS")),
        # H5 file, "H5f, read 25 September 2026": a 0.500 (bar 0.5, ON the bar), b 64 of 64 (bar 80%),
        # c 0.6% median per-day gap (bar 25%).
        ("H5f", "H5a–b again on the consolidated market; zero-bid inflation too",
         "0.5 of a spread; 80%; 25%", esc("0.500 (on the bar); 64 of 64; 0.6%"), pill("HOLDS")),
        # H5 file, Result: "H5c, H5d: descriptive until their 10 underlying-days support the date-clustered test";
        # HANDOFF 18: H5d "12 underlying-days on 3 dates; the date-clustered test needs more dates".
        ("H5c–d", "Inflation repeats on Bloomberg, grows with empty strikes",
         "within 25%; positive slope", esc("too few dates to test"), pill("not yet tested", "na")),
        # H5 file, H5e: mean absolute gap under 0.5 AND closer than the registered estimate on a majority of days.
        ("H5e", "Skipping zero-bid quotes brings oil's estimate near OVX", "gap under 0.5; closer on most days",
         h5em, h5ev),
        # H7 file: H7a free vs OPRA replica, 0.25 or less for USO and GLD; H7b GLD vs GVZ, 0.30 or less;
        # H7c (USO vs OVX) descriptive only.
        ("H7", "Cboe's rules on free quotes match OPRA (a), GVZ (b)", "a: 0.25 or less; b: 0.30",
         h7m, h7v),
    ]
    side = [
        # H1 file, Result: H1a 9 of 11 pairs, all 9 survive Benjamini-Hochberg; H1b holds but mixed; H1c holds.
        ("H1", "The known volatility risk premium, 10 years of Cboe indices",
         "significantly positive", esc("9 of 11 pairs, after false-discovery control"),
         pill("HOLDS") + note("H1b mixed; H1c holds")),
        # H2 file, Result: log variance t 16.26, raw variance t 2.14 (H2a holds); H2b not supported; H2c not tested.
        ("H2", "The premium in variance, not volatility", "a: significant; b: less autocorrelated",
         # 28 Oct 2026 (outside review M05): the pooled t treats the equity indices' windows as independent, though they
         # share market episodes - so it overstates; the registered verdict stands, the poster says so.
         esc("a: pooled t 16.3 logs, 2.1 raw (overstated: shared episodes); b: no"),
         pill("H2a HOLDS", "ok") + pill("H2b NOT SUPPORTED", "bad")),
        # H4 file / hypotheses README: registered 13 Sep, not yet tested; adjustment log "STRIKE 2 of 3" (8 Oct);
        # "a third post-output adjustment abandons H4"; "roughly 40 day pairs is enough for both claims".
        ("H4", "Delta-hedged gains are negative and vary by strike", "negative; a set shape",
         esc("needs ~40 day pairs; 2 of 3 permitted changes used"), pill("not yet tested", "na")),
        # H6 file, Result: implied vol has the lower error in 0 of 9 pairs (bar: at least 7 of 9).
        ("H6a", "Implied volatility beats a 14-day average at forecasting tomorrow's range",
         "7 or more of 9 pairs", esc("0 of 9"), pill("FAILS")),
        # H6 file, Result: mean d +0.3272 after spikes vs +0.4165 calm; Welch p < 0.0001; Newey-West lag 21 p 0.0001,
        # lag 63 p 0.0018.
        ("H6b", "Its shortfall shrinks after volatility spikes", "smaller, p < 0.05",
         esc("0.33 vs 0.42; p < 0.01"), pill("HOLDS")),
    ]
    return confirmatory, side


def table_html(confirmatory, side):
    def rows(rs):
        return "".join(f'<tr><td class="id">{esc(i)}</td><td>{esc(t)}</td><td class="bar">{esc(b)}</td>'
                       f'<td class="m">{m}</td><td class="v">{v}</td></tr>' for i, t, b, m, v in rs)
    return ('<table class="tests"><colgroup><col class="c-id"><col><col class="c-bar"><col class="c-m">'
            '<col class="c-v"></colgroup>'
            '<thead><tr><th></th><th>Test</th><th>Bar, set first</th><th>Measured</th><th>Verdict</th></tr></thead>'
            '<tbody class="conf"><tr class="gh"><td colspan="5">The free-data question · confirmatory</td></tr>'
            f'{rows(confirmatory)}</tbody>'
            '<tbody class="sidegrp"><tr class="sp"><td colspan="5"></td></tr><tr class="gh"><td colspan="5">'
            f'Side studies · H1 is the method check</td></tr>{rows(side)}</tbody></table>')


# ---------------- the chart ----------------
def chart_svg():
    """Horizontal bars: mean absolute gap to Cboe by strike band; the worst pair beside each. ~1 unit = 1 CSS px."""
    w, row, x0, scale = 1600, 275, 260, 195  # scale: px per volatility point
    out = []
    for k, (band, n, mae, worst, pair) in enumerate(BANDS):
        y = 12 + k * row
        bw = mae * scale
        hi = k == len(BANDS) - 1
        who = (f"worst pair: {pair} " if pair else "worst pair ") + f"{worst:+.2f}".replace("-", "−")
        out.append(
            f'<text x="{x0 - 28}" y="{y + 100}" text-anchor="end" class="ax">{band}</text>'
            f'<text x="{x0 - 28}" y="{y + 154}" text-anchor="end" class="axs">{n} strikes</text>'
            f'<rect x="{x0}" y="{y}" width="{bw:.0f}" height="205" rx="12" class="{"bar hi" if hi else "bar"}"/>'
            f'<text x="{x0 + bw + 28:.0f}" y="{y + 98}" class="val{" hi" if hi else ""}">{mae:.2f}</text>'
            f'<text x="{x0 + bw + 28:.0f}" y="{y + 156}" class="axs">{esc(who)}</text>')
    h = 12 + len(BANDS) * row - 50
    return (f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" '
            f'aria-label="Mean absolute gap to Cboe by strike band">{"".join(out)}</svg>')


# ---------------- the page ----------------
def build(today=None):
    today = today or date.today()
    h3 = h3_live()
    h5e = h5e_final(H5_FILE.read_text())
    h7 = h7_reading(H7_FILE.read_text())
    confirmatory, side = test_rows(h3, h5e, h7, today)
    record = today > H3_RECORD_DAY
    head = headline(h3, h7)

    stats = "".join(f'<div class="q"><b>{esc(n)}</b><span>{esc(t)}</span></div>' for n, t in QUOTE_STATS)
    ai = (f'<p class="ai">{esc(AI_LINE)}</p>' if AI_LINE_APPROVED else
          f'<p class="ai draft"><span class="tag">DRAFT, for Gabriel to approve</span> {esc(AI_LINE)}</p>')
    h3_since = (f'Since then (H3{"" if record else ", so far"}): mean gap '
                f'<span class="inl">{h3["mae"]:.2f}</span> over {h3["n"]} readings; bar 1.0.')

    body = f"""
<section class="side left">
  <div>
    <h1>What Does Free Options Data Cost?</h1>
    <p class="subtitle">Measuring a Retail-Grade Feed Against Cboe's Volatility Indices</p>
    <p class="by"><b class="name">Gabriel Mitton</b><span class="nw">Pepperdine University, Malibu, California</span>
    · <span class="nw">gabriel.mitton@gmail.com</span></p>
    <p class="by">Mentor: Marc Vinyard, Pepperdine University Libraries</p>
  </div>
  <div>
    <h2>The question</h2>
    <p>Students and small researchers price options with <b>free quotes</b>, because the full market feed costs
    thousands of dollars a year. What precision does free data give up, and <b>where</b> is the loss: in the
    quotes, or in the recipe that turns them into volatility?</p>
  </div>
  <div>
    <h2>What I did</h2>
    <ul>
      <li>Since September 2026, code records a free brokerage feed (Alpaca) daily: 109 tickers, plus full strike
          ranges for 8 funds and stocks.</li>
      <li>It checks the feed against <b>Cboe's indices</b> (VIX, OVX, GVZ…), the <b>consolidated
          market</b> (OPRA) and <b>Bloomberg</b>.</li>
    </ul>
  </div>
  <div>
    <h2>How it stays honest</h2>
    <ul>
      <li>Every pass/fail bar was <b>written before its test ran</b>, dated in a public git repository; the
          open tests (H5e, H7) were also frozen on <b>OSF</b> (10 Oct 2026).</li>
      <li>Failures stay in the same table as successes.</li>
      <li>A <b>second program sharing no code</b> recomputed every recorded number, catching one
          spreadsheet-reading bug (fixed; no verdict changed).</li>
    </ul>
  </div>
  <div>
    <h2>What's next</h2>
    <ul>
      <li>12–19 Nov: the final readings of H5e and H7, as registered.</li>
      <li>Dec–Jan: a confirmatory test on all eight funds, registered first.</li>
      <li>2027: the paper, failures included.</li>
    </ul>
  </div>
</section>

<section class="center">
  <div class="kicker">On the evidence so far</div>
  <div class="big">{esc(head[0])} <em>{esc(head[1])}</em></div>
  <p class="sub">Free quotes sit a median of a third to a half of a bid-ask spread (the gap between buying and
  selling prices) from professional feeds; wider strikes cut the gap to Cboe's index from 3.97 to 0.59 points
  (one calibration day).</p>
  <div class="panel quotes">
    <h3>The quotes: close to the professional feeds</h3>
    <div class="qs">{stats}</div>
  </div>
  <div class="panel figure">
    <h3>The recipe: widen the strikes and the gap almost disappears</h3>
    <p class="cap">Mean absolute gap to Cboe's index (volatility points) by the strike range integrated;
    five fund–index pairs, 11 Sep 2026.</p>
    {chart_svg()}
    <p class="why">{esc(TRUNCATION_WHY)}</p>
    <div class="foot">
      <div class="callout">At ±30%<b>SPY {SPY_VS_VIX[0]} vs VIX {SPY_VS_VIX[1]}</b>{h3_since}</div>
      <div class="qr"><div id="qr"></div>Data, code and every<br>registration: scan me</div>
    </div>
  </div>
</section>

<section class="side right">
  <div>
    <h2>Every registered test</h2>
    {table_html(confirmatory, side)}
  </div>
  <div>
    <h2>Limits</h2>
    <p class="small">One free feed; about two months of data; one snapshot a day, about 80 minutes before the
    close (a median 0.53 points of drift by the close in stress months); American options priced with European
    formulas; far contracts nobody quotes can carry hours-old free quotes.</p>
  </div>
  <div class="credits">
    <p class="small"><b>Acknowledgments.</b> I thank Marc Vinyard for mentoring this project and for library
    data access.</p>
    {ai}
    <p class="small">Data provided by Databento (OPRA consolidated NBBO). Bloomberg figures: Source: Bloomberg
    Finance L.P. Index values © Cboe Global Markets. This product uses the FRED® API but is not endorsed or
    certified by the Federal Reserve Bank of St. Louis. Options quotes: Alpaca indicative feed, non-commercial use.
    Aggregates only. Registration: {OSF} · {SITE}</p>
  </div>
</section>
"""
    page = PAGE.replace("@@CSS@@", CSS).replace("@@BODY@@", body).replace("@@SITE@@", SITE)
    (OUT / "poster.html").write_text(page)
    return OUT / "poster.html"


CSS = """
  @page { size: 48in 36in; margin: 0; }
  :root { --navy:#0b2447; --ink:#14213d; --mute:#4f5a6d; --rule:#d3d9e3; --orange:#e35205;
          --ok:#1f7a4d; --bad:#b42318; --due:#8a6d00; --na:#56607a; --paper:#ffffff; --tint:#f3f5f9; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html, body { width:48in; height:36in; background:var(--paper); color:var(--ink);
               font-family:Inter, system-ui, sans-serif; font-size:41px; line-height:1.38;
               -webkit-print-color-adjust:exact; print-color-adjust:exact; overflow:hidden; }
  .poster { display:grid; grid-template-columns:12in 1fr 16.6in; grid-template-rows:36in; width:48in; height:36in; }
  .side { padding:0.95in 0.75in 0.8in; display:flex; flex-direction:column; gap:0.5in; overflow:hidden; }
  .left { border-right:1px solid var(--rule); font-size:46px; justify-content:space-between; gap:0.5in; }
  .right { border-left:1px solid var(--rule); background:var(--tint); gap:0.42in; }
  h1 { font-family:'Inter Tight'; font-weight:800; font-size:100px; line-height:1.02; letter-spacing:-0.01em; color:var(--navy); }
  .subtitle { font-family:'Inter Tight'; font-weight:700; font-size:54px; line-height:1.15; color:var(--ink); margin:0.22in 0 0.3in; }
  .by { font-size:38px; color:var(--mute); line-height:1.35; }
  .by + .by { margin-top:0.08in; }
  .by b { color:var(--ink); }
  .by .name { display:block; font-family:'Inter Tight'; font-size:48px; }
  .nw { white-space:nowrap; }
  h2 { font-family:'Inter Tight'; font-weight:700; font-size:50px; color:var(--navy); margin-bottom:0.15in;
       padding-bottom:0.07in; border-bottom:6px solid var(--orange); display:inline-block; }
  p + p { margin-top:0.14in; }
  ul { padding-left:0.42in; } li + li { margin-top:0.1in; }
  .center { background:var(--navy); color:#fff; padding:1.05in 0.95in 0.8in; display:flex; flex-direction:column; overflow:hidden; }
  .kicker { font-family:'Inter Tight'; font-weight:700; font-size:44px; letter-spacing:0.12em; text-transform:uppercase; color:#ffb48a; }
  .big { font-family:'Inter Tight'; font-weight:800; font-size:150px; line-height:1.0; margin:0.3in 0 0.42in; letter-spacing:-0.015em; }
  .big em { font-style:normal; color:#ff8a4c; }
  .sub { font-size:54px; line-height:1.3; color:#dbe4f3; }
  .panel { background:rgba(255,255,255,0.07); border-radius:28px; padding:0.5in 0.6in; }
  .panel h3 { font-family:'Inter Tight'; font-weight:700; font-size:54px; line-height:1.15; }
  .quotes { margin-top:0.55in; }
  .qs { display:grid; grid-template-columns:repeat(3, 1fr); gap:0.5in; margin-top:0.25in; }
  .q b { display:block; font-family:'Inter Tight'; font-weight:800; font-size:112px; line-height:1.05; color:#fff; }
  .q span { display:block; font-size:39px; line-height:1.3; color:#c9d5e8; margin-top:0.08in; }
  .figure { margin-top:0.45in; flex:1; display:flex; flex-direction:column; }
  .cap { font-size:38px; color:#c9d5e8; margin-top:0.1in; }
  .chart { width:100%; margin-top:0.35in; }
  .chart .ax { font:700 70px 'Inter Tight'; fill:#fff; }
  .chart .axs { font:400 41px Inter; fill:#c9d5e8; }
  .chart .bar { fill:#6f8fc2; } .chart .bar.hi { fill:#ff8a4c; }
  .chart .val { font:800 84px 'Inter Tight'; fill:#fff; } .chart .val.hi { fill:#ff8a4c; }
  .why { font-size:42px; line-height:1.3; color:#fff; margin-top:0.2in; padding-left:0.3in; border-left:8px solid #ff8a4c; }
  .foot { display:flex; justify-content:space-between; align-items:flex-end; margin-top:auto; gap:0.6in; padding-top:0.35in; }
  .callout { font-size:40px; line-height:1.3; color:#dbe4f3; }
  .callout b { font-family:'Inter Tight'; font-size:76px; color:#fff; display:block; margin:0.04in 0 0.1in; }
  .callout .inl { font-family:'Inter Tight'; font-weight:800; color:#ff8a4c; }
  .qr { background:#fff; padding:0.12in 0.12in 0.2in; border-radius:16px; text-align:center; color:var(--ink);
        font-size:32px; line-height:1.25; flex:none; }
  .qr #qr { width:3.5in; height:3.5in; margin-bottom:0.06in; }
  .qr svg { display:block; width:100%; height:100%; shape-rendering:crispEdges; }
  table.tests { width:100%; table-layout:fixed; border-collapse:collapse; font-size:36px; line-height:1.27; }
  col.c-id { width:1.42in; } col.c-bar { width:2.75in; } col.c-m { width:3.2in; } col.c-v { width:2.95in; }
  .tests th { text-align:left; font-family:'Inter Tight'; font-weight:700; color:var(--mute); padding:0 0.09in 0.08in;
              border-bottom:3px solid var(--navy); }
  .tests td { padding:0.13in 0.09in; border-bottom:1px solid var(--rule); vertical-align:top; }
  .tests td.id { font-family:'Inter Tight'; font-weight:700; color:var(--navy); white-space:nowrap; }
  .tests td.bar, .tests td.m { color:var(--ink); }
  .tests tr.gh td { font-family:'Inter Tight'; font-weight:700; font-size:34px; padding:0.1in 0.12in; border-bottom:none; }
  .tests tbody.conf tr.gh td { background:var(--navy); color:#fff; }
  .tests tbody.sidegrp tr.gh td { background:#dfe4ec; color:var(--navy); }
  .tests tr.sp td { height:0.22in; padding:0; border:none; }
  .tests tbody.sidegrp td.id { color:var(--mute); }
  .pill { display:inline-block; font-family:'Inter Tight'; font-weight:700; font-size:34px; line-height:1.15;
          padding:3px 14px 4px; border-radius:12px; color:#fff; margin:0 8px 6px 0; letter-spacing:0.02em; }
  .pill.ok { background:var(--ok); } .pill.bad { background:var(--bad); } .pill.due { background:var(--due); }
  .pill.na { background:var(--na); }
  .vnote { display:block; color:var(--mute); font-size:33px; margin:-2px 0 4px; }
  .small, .note { font-size:36px; color:var(--mute); line-height:1.3; }
  .note { margin-top:0.12in; }
  .credits { margin-top:auto; }
  .credits p + p { margin-top:0.12in; }
  .credits .small, .credits .ai { font-size:33px; }
  .ai.draft { font-size:32px; line-height:1.3; color:var(--ink); border:4px dashed var(--bad); padding:0.08in 0.14in; }
  .ai { font-size:32px; line-height:1.3; color:var(--mute); }
  .ai .tag { font-family:'Inter Tight'; font-weight:800; color:var(--bad); }
"""

# The check script measures the rendered page for render(): the smallest text in CSS px (SVG text scaled by its
# transform), any column whose content overflows, the word count, and whether the QR code is vector SVG.
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>What Does Free Options Data Cost? (SCCUR 2026 poster)</title>
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
<script>
window.addEventListener("load", () => setTimeout(() => {
  let min = 1e9, where = "";
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode, el = t.parentElement;
    if (!t.textContent.trim() || el.closest("script,style")) continue;
    let px = parseFloat(getComputedStyle(el).fontSize);
    if (el instanceof SVGElement) { const m = el.getScreenCTM(); px *= Math.hypot(m.a, m.b); }
    if (px < min) { min = px; where = t.textContent.trim().slice(0, 48); }
  }
  const over = [...document.querySelectorAll(".poster > section")]
    .filter(s => s.scrollHeight > s.clientHeight + 1).map(s => s.className);
  const words = document.body.innerText.split(/\\s+/).filter(x => /[A-Za-z0-9]/.test(x)).length;
  const qr = document.querySelector("#qr svg") ? "svg" : (document.querySelector("#qr img, #qr canvas") ? "raster" : "none");
  document.body.dataset.check = JSON.stringify({minPx: min, where, overflow: over, words, qr});
}, 400));
</script>
</body></html>
"""

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(path):
    common = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=8000"]
    subprocess.run(common + [f"--print-to-pdf={OUT / 'poster.pdf'}", "--no-pdf-header-footer", path.as_uri()],
                   check=True, capture_output=True)
    subprocess.run(common + [f"--screenshot={OUT / 'preview.png'}", "--window-size=4608,3456",
                             "--force-device-scale-factor=0.5", path.as_uri()], check=True, capture_output=True)
    dom = subprocess.run(common + ["--window-size=4608,3456", "--dump-dom", path.as_uri()],
                         check=True, capture_output=True, text=True).stdout
    m = re.search(r'data-check="([^"]*)"', dom)
    if not m:
        raise SystemExit("the page check did not run (fonts or scripts did not load?)")
    chk = json.loads(html.unescape(m[1]))
    pdf = (OUT / "poster.pdf").read_bytes()
    boxes = re.findall(rb"/MediaBox\s*\[\s*0 0 ([\d.]+) ([\d.]+)\s*\]", pdf)
    pages = len(re.findall(rb"/Type\s*/Page\b", pdf))
    print(f"check: smallest text {chk['minPx']:.1f}px = {chk['minPx'] * 0.75:.1f}pt ('{chk['where']}'); "
          f"{chk['words']} words; QR {chk['qr']}; overflow {chk['overflow'] or 'none'}; "
          f"PDF pages {pages}, MediaBox {[b.decode() for b in boxes[0]] if boxes else '?'}")
    problems = []
    if chk["minPx"] < 32:
        problems.append("text below 24 pt")
    if chk["overflow"]:
        problems.append("a column overflows")
    if chk["qr"] != "svg":
        problems.append("QR code is not vector SVG")
    if pages != 1 or not boxes or boxes[0] != (b"3456", b"2592"):
        problems.append("PDF is not one 48 x 36 in page")
    if problems:
        raise SystemExit("poster check failed: " + "; ".join(problems))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="also render poster.pdf and preview.png with Chrome")
    ap.add_argument("--today", help="YYYY-MM-DD, to preview the H3 label on another date (default: today)")
    a = ap.parse_args()
    p = build(date.fromisoformat(a.today) if a.today else None)
    print(f"wrote {p.relative_to(ROOT)}")
    if a.pdf:
        render(p)
        print("wrote poster/poster.pdf and poster/preview.png")
