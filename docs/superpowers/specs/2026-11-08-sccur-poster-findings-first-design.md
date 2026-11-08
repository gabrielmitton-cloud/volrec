# SCCUR poster, findings first (design, 8 Nov 2026)

**Status.** Direction chosen by Gabriel on 7 Nov 2026 (Pacific): layout A ("headline + evidence") with the
classic research-poster look, graphs easy to read but informative, and the verdicts small, "basically a side
note for me to point to during talks". He asked Vega to "do ur thing" and to use different subagents. Every
detail below the direction is Decided (his to veto).

**Why.** The 21 Oct poster spends about a third of its area on a 12-row table of hypotheses and has one
chart. Purrington's guide and the #BetterPoster format agree: results take the middle and the most space,
graphs instead of tables, each graph titled with its finding, direct labels, the main finding in big plain
words. The current poster already does the last one; it keeps it.

## What does not change

- Every number comes from the project's own records or readers, never typed by hand. Frozen figures stay
  copied with the file they come from; H3 is read live from the frozen scorer; H5e FINAL and H7 from the
  blocks `tools/record_verdict.py` writes. A block that is present but not recognised stops the build.
- The headline and its fallback rule (Gabriel, 21 Oct), the approved AI-use sentence, the mentor credit, the
  data credits (Databento, Bloomberg, Cboe, FRED notice, Alpaca), "Aggregates only". No licensed raw data.
- 48 x 36 in landscape, one PDF page, text at least 24 pt (32 CSS px), QR code as vector, no column
  overflowing (the existing render checks).
- No new data, no new analysis, no hypothesis touched. The timing registration (osf.io/4mcgf) stays off the
  poster (6 Nov decision: it has no result yet).

## Layout (48 x 36 in)

```
+----------------------------------------------------------------------------------+
| TITLE BANNER (navy): title, subtitle | name, university, email, mentor            |
+----------------------------------------------------------------------------------+
| HEADLINE: "The free quotes are close. Most of the error is in the recipe."        |
+---------------+------------------------------------+-----------------------------+
| 1 The question| 3 Free data tracks Cboe's index,   | 4 The quotes are close      |
| 2 What I did  |   day after day (MAIN CHART:       |   (64 of 64; distance scale)|
|   (pipeline)  |   five funds, daily, 14 Sep-11 Nov,|-----------------------------|
| How it stays  |   plus an H3 summary tile)         | 5 The error is in the recipe|
|   honest      |                                    |   (bell curves + band bars) |
| What's next   |                                    | Why it matters              |
| Limits        |                                    |                             |
+---------------+------------------------------------+-----------------------------+
| EVERY REGISTERED TEST (small chips, 2 rows)          | QR | credits, AI line       |
+----------------------------------------------------------------------------------+
```

Reading order is left to right, numbered. Classic look: a navy title banner, numbered section headers with
an orange rule, white body, light panels behind the results.

## The panels

**3. Main chart: free data against Cboe's index, every day (H3).** Five small panels (SPY-VIX, QQQ-VXN,
IWM-RVX, GLD-GVZ, USO-OVX), each with its own volatility scale: Cboe's published close (navy, solid) and the
free-data estimate (orange, dashed), with month labels. Each panel's subtitle gives its mean gap, read from
the frozen scorer's per-underlying lines. The sixth cell is a summary tile: the pooled mean gap, the number
of readings, the bar set first (under 1.0), and H3a/H3b/H3c in plain words with their verdicts as the
scorer prints them ("so far" until 11 Nov, the reading of record after). Data: one `modelfree.py --precise`
run (FRED_KEY=use-cache), parsed with the scorer's own `parse`, cut at the scorer's THROUGH (11 Nov). The
same saved output is scored with `tools/h3_scorer.py --file`, so the chart and the numbers come from one run;
the build stops if any panel's computed mean differs from the scorer's printed one.

**4. The quotes are close.** "64 of 64": where the free feed shows no bid on a far strike, the full market
(OPRA) shows none either (H5f-b; Bloomberg 44 of 44, H5b). A distance scale from 0 to 1 bid-ask spread: the
median free mid against Bloomberg's (0.33, 179 contracts) and OPRA's (0.500, 466), the bar at 0.5 drawn as
a line, and the honest caveat drawn too: where both feeds bid, 0.67 (Bloomberg, 134 contracts), which on
cheap far options is a tick or two. All frozen from the H5 file.

**5. The error is in the recipe.** (a) Two bell curves, a calm fund at 16 volatility and crude oil at 59,
30 days out, with the same +/-10% strike band shaded: the band sees 2.2 standard deviations of one and 0.6 of
the other (computed, and checked against the README's sentence). (b) The calibration bars as now: mean gap
to Cboe 3.97, 1.31 and 0.59 points at +/-10, 20 and 30%, oil's worst pair labelled. Frozen figures as now.

**Every registered test (the side note).** Small chips in two rows, confirmatory tests first: H3, H5a, H5b,
H5f, H5c-d, H5e, H7a, H7b; then the side studies H1, H2a, H2b, H4, H6a, H6b. Each chip: ID, verdict word with
an icon (never colour alone), a few-word claim and the key number against its bar. H5e and H7 show "due
12-19 Nov" until their blocks exist, then the recorded numbers. Every hypothesis in `hypotheses/README.md`'s
status table must appear (the existing test, adapted).

## Charts

Inline SVG drawn by the build (vector, prints sharp), Inter type, at least 32 CSS px for any text. Navy for
Cboe, orange for free data, everywhere; checked with the dataviz palette validator on white. Direct labels
instead of legends where there is room, recessive gridlines, no dual axes, each chart titled with its
finding as a sentence.

## Checks

- Tests first for the new logic: the one-run series and its cross-check, the per-underlying parse, the
  bell-curve coverage numbers, the chip list (every status-table hypothesis; due before a block exists).
- The existing 19 poster tests stay green (the table tests move to the chips).
- The render checks (24 pt, no overflow, vector QR, one 48 x 36 page).
- Different reviewers, as Gabriel asked, each on the rendered poster and its code: a poster judge (can a
  non-finance student read it from six feet?), a number auditor (every number traced to its source), a
  chart and accessibility reviewer, and an integrity and licensing auditor. Then Astra Ultra on the code
  (project rule), one follow-up at most.
- `SCCUR-PITCH.md`'s two-minute walk is rewritten for the new layout.

## Timeline

Built and reviewed by about 9 Nov. Rebuilt the day the verdict blocks land (about 13 Nov), Gabriel looks at
it, print order Mon 16 Nov (reminder set), SDSU Sat 21 Nov.
