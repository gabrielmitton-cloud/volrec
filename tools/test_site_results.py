"""Known-answer tests for tools/site_results.py (the page's results, generated from the hypothesis files).

The fixtures are the four recorded blocks as the files hold them on 13 Nov 2026 (H3's reading of record, H5e's FINAL
reading, H7's verdict with its companion readings, the timing measurement's one reading), each with its credit:
public aggregates. One line is NOT copied: H5e's "Skip-only gap by day" keeps the writer's form but holds two
synthetic values on 2001 dates. The real line gives the gap to OVX day by day, and with the public estimator that
gives back Cboe's closes (Astra, 13 Nov 2026); the parser never reads it. Every answer below can be checked by
reading those blocks. The page fixture copies the real page's layout around the three marker pairs, and the style
fixture the real stylesheet's own hiding rules. Nothing here reads the real page, the real files, the network or a
licensed folder; files are written only in a temporary folder.

  python tools/test_site_results.py
"""
import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / "tools")]
import site_results as SR   # noqa: E402

fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def raises(fn, why=""):
    """True if fn refuses with Unrecognised (the house's 'present but not in the form expected') and, when `why` is
    given, names it in its reason, so a case passes only for the refusal it is about. Any other exception is a
    crash: printed, and never a pass."""
    try:
        fn()
    except SR.Unrecognised as e:
        return why in str(e)
    except Exception as e:  # noqa: BLE001 - a crash fails the case; it is never read as a refusal
        print(f"        crashed: {type(e).__name__}: {e}")
        return False
    return False


def got(fn):
    """fn(), or None when it crashes (printed): a missing or broken function fails its own cases, never the run."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a crash fails the case that reads it; it is never a value
        print(f"        crashed: {type(e).__name__}: {e}")
        return None


def mut(text, old, new, count=1):
    """text with old replaced by new; refuses when old is absent, so no case rests on an edit that never happened."""
    if old not in text:
        raise AssertionError(f"test edit target not found: {old[:60]!r}")
    return text.replace(old, new, count)


# ---------------- the records, copied exactly ----------------
H3 = """## Result: the reading of record, to 11 Nov 2026 (scored 13 Nov 2026)

**H3, the reading of record over the series to Wed 11 Nov 2026** - scored by the frozen scorer
(`tools/h3_scorer.py`, specified 17 Oct; see the adjustment log) on `modelfree.py`'s registered output (not
`--wide`), at full precision and the frozen risk-free rate (3.910%). Run by Vega on 13 Nov 2026; its output is
identical, line for line, to the cloud workflow's companion step of 13 Nov 2026, 03:28 UTC. Numbers copied from
that output; nothing re-cut. The running readings in the sections above (23 Sep - 6 Nov) were readings to date.

- **H3a HOLDS:** pooled mean absolute gap 0.708 volatility points over 205 readings on 41 days (bar: under 1.0).
- **H3b HOLDS:** pooled mean gap -0.444 (registered: negative; the free estimate reads low on average).
- **H3c HOLDS:** pooled slope of the absolute gap on the index level +0.0455 per point, t 20.51, one-sided p
  0.0104 (wild cluster bootstrap, Webb weights, all 7,776 weight vectors; registered: positive and significant).
- **Benjamini-Hochberg at q 0.05, across the five registered underlyings (all five testable):** H3a holds on 4
  of 5, and H3c's slope is positive and significant on 3 of 5.
- Per underlying, 41 days each (Newey-West, fixed-b): mean absolute gap, H3a's p; slope, H3c's p.
  GLD 0.363, 0.0000; +0.0177, 0.3287. IWM 0.461, 0.0000; +0.0113, 0.2495. QQQ 0.504, 0.0070; +0.1039, 0.0003.
  SPY 0.443, 0.0092; +0.2040, 0.0000. USO 1.767, 0.9155; +0.1979, 0.0000. USO is the one fund over the bar.

*Index closes: Cboe Global Markets. Derived aggregates only.*

## Adjustment log
"""

# H5e's FINAL block as written on 12 Nov 2026, its aggregates exact (index closes: Cboe Global Markets; derived
# aggregates only). Its "Skip-only gap by day" line is SYNTHETIC: the writer's form, two made-up values on 2001 dates.
H5 = """**H5e, FINAL reading over 23 Sep - 11 Nov 2026, read 12 November 2026** - the reading the write-up uses; written by the cloud workflow (`tools/record_verdict.py`), numbers from `modelfree.py --wide`, wording fixed in advance.

- **FAILS**: the mean gap is not under 0.5.
- Mean absolute gap of the skip-only estimate to OVX: 0.91 volatility points (bar: under 0.5).
- Closer to OVX than the registered estimate on 26 of 35 counted days (bar: a majority).
- Skip-only gap by day: 2001-01-02 +0.91; 2001-01-03 -0.91.
- Risk-free rate as the reading of record uses it (FRED cache): 3.910%.
- Dropped as recorded after the close, under Gabriel's 23 Sep rule (applied 30 Sep, before this verdict): 2026-09-28.
- The first verdict (the block above) was FAILS; this reading agrees.
- The estimator is Andersen, Bondarenko & Gonzalez-Perez (2015)'s RX*, credited above; what is this project's is its application to a free retail-grade feed on USO.

**Companion readings, added 13 Nov 2026 beside the FINAL reading above, never in place of it.** Descriptive: no
"""

H7 = """## Result

Not read yet: due 12 Nov 2026 (`tools/record_verdict.py`, from `tools/h7_reader.py`).

**H7, reading over 9 Oct - 11 Nov 2026, read 13 November 2026** - written by the cloud workflow (`tools/record_verdict.py`) from `tools/h7_reader.py`; numbers copied from its output, wording fixed in advance.

- **H7a FAILS:** mean absolute difference between the free-feed and OPRA Cboe replicas at the same minute: USO 0.316 over 24 days, GLD 0.034 over 24 days (bar: 0.25 or less, each).
- **H7b HOLDS:** the free-feed replica for GLD lies a mean absolute 0.172 points from GVZ's close over 24 days (bar: 0.30 or less).
- H7c (descriptive): the free-feed replica for USO minus OVX's close averaged -0.244 over 24 days.
- The method is Cboe's own (Volatility Index Mathematics Methodology v5.0; ETF index methodology v9.0), applied to the monthly legs recorded from 9 Oct; after-close days dropped.

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

**Companion readings, added 13 Nov 2026 beside the verdict above, never in place of it.** Descriptive: none is a
registered test, and none changes the verdict. Copied from the cloud workflow's companion step (13 Nov 2026, 03:28
UTC), which ran once, after both final readings were recorded.
- *Intervals* (`tools/describe.py`, on exactly the registered days; Newey-West, lag 6, fixed-b critical value
  2.80): H7a USO mean 0.316 points, 95% interval 0.150 to 0.482 (rho 0.41, n_eff 10.1), so the interval spans the
  0.25 bar (one-sided p of a mean under it, 0.808); H7a GLD 0.035, 0.020 to 0.050 (n_eff 21.7); H7b 0.172, 0.117 to
  0.228 (n_eff 21.3); H7c -0.244, -0.588 to 0.099 (n_eff 21.7).
- *H7a on matched strikes* (`tools/h7_reader.py --matched`, log entry 3): with OPRA cut to the strikes the free
  file holds, the two replicas differ by a mean absolute 0.132 points for USO and 0.061 for GLD, over 24 days each,
  against the registered 0.316 and 0.034 on every strike OPRA lists. The two readings differ only in that strike
  set. Cboe's walk ran past the free file's edge (+/-60% of spot) on 24 of 24 days for both.
- *The second implementation* (`tools/independent_check.py`, same step): 1302 of 1302 values agree within 0.01
  points, H7's 48 free-feed and 48 OPRA replica values among them (largest difference anywhere 0.00088).
- *Timing* (`hypotheses/2026-11-06-index-timing.md`, registered 6 Nov, read once 13 Nov; descriptive): on the 16
  covered days (21 Oct - 11 Nov), the OPRA replica sat a mean absolute 0.021 points from OVX and 0.010 from GVZ at
  the snapshot minute; the free-feed replica 0.369 and 0.037.

*Data provided by Databento (OPRA consolidated NBBO). Index closes: Cboe Global Markets. Aggregates only.*

## Adjustment log
"""

TIMING = """## Result

Filled in after the run, which waits for both verdicts.

**Read once, 13 November 2026, 16:34 UTC** - by Vega, with the registered command (`VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra python tools/index_timing.py`, the framework Python), on the reader whose sha256 is the registered `e65b5270...` (checked before the run), after H5e's FINAL reading (12 Nov) and H7's reading (13 Nov) were both recorded (Gabriel's go-ahead, 12 Nov: read once H7 is recorded). Exit 0: every refusal passed (the seal and its files, the frozen rate, `modelfree`, the recorded days and means). Its output, whole:

```
Index timing - EXPLORATORY, descriptive; no test, no verdict. DBIX days: 2026-10-21 to 2026-11-11 (16 files).

== H5e registered, against OVX: 16 of 16 covered days measured; 19 counted days before the data begins (2026-09-23 to 2026-10-20)
   signed means, points: E - C -2.896 = (E - I(T)) -2.810 + (I(T) - C) -0.087   [adds up to 0.0e+00]
   mean absolute: |E - C| 2.896, |E - I(T)| 2.810, |I(T) - C| 0.634; corr(E - I(T), I(T) - C) -0.057
   persistence (days, rho, n_eff): E - C 16, +0.017, 15.5; E - I(T) 16, +0.389, 7.0; I(T) - C 16, -0.092, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -2.821, I - C -0.076
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +30
      2026-10-21 +27 (-774 to +32); 2026-10-22 +30 (-463 to +37); 2026-10-23 +23 (-16 to +31); 2026-10-26 +29 (-366 to +40)
      2026-10-27 +33 (-165 to +35); 2026-10-28 +31 (-595 to +35); 2026-10-29 +28 (-222 to +30); 2026-10-30 +30 (-82 to +32)
      2026-11-02 +32 (+7 to +33); 2026-11-03 +40 (+8 to +45); 2026-11-04 +32 (+20 to +34); 2026-11-05 +48 (+26 to +52)
      2026-11-06 +33 (-33 to +36); 2026-11-09 +23 (-6 to +92); 2026-11-10 +27 (-106 to +34); 2026-11-11 +25 (-117 to +32)
== H5e skip-only, against OVX: 16 of 16 covered days measured; 19 counted days before the data begins (2026-09-23 to 2026-10-20)
   signed means, points: E - C -1.203 = (E - I(T)) -1.116 + (I(T) - C) -0.087   [adds up to 0.0e+00]
   mean absolute: |E - C| 1.203, |E - I(T)| 1.117, |I(T) - C| 0.634; corr(E - I(T), I(T) - C) -0.181
   persistence (days, rho, n_eff): E - C 16, +0.332, 8.0; E - I(T) 16, +0.625, 3.7; I(T) - C 16, -0.092, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -1.127, I - C -0.076
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +30
      2026-10-21 +27 (-774 to +58); 2026-10-22 +30 (-463 to +66); 2026-10-23 +24 (-16 to +63); 2026-10-26 +29 (-366 to +68)
      2026-10-27 +33 (-165 to +63); 2026-10-28 +31 (-595 to +63); 2026-10-29 +28 (-9815 to +56); 2026-10-30 +30 (-16416 to +56)
      2026-11-02 +32 (-2386 to +63); 2026-11-03 +40 (-14185 to +71); 2026-11-04 +32 (+20 to +65); 2026-11-05 +48 (+26 to +84)
      2026-11-06 +36 (-33 to +71); 2026-11-09 +23 (-6 to +103); 2026-11-10 +26 (-113 to +62); 2026-11-11 +25 (-117 to +62)
== H7 OPRA replica, against GVZ: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C +0.040 = (E - I(T)) +0.002 + (I(T) - C) +0.038   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.198, |E - I(T)| 0.010, |I(T) - C| 0.207; corr(E - I(T), I(T) - C) -0.675
   persistence (days, rho, n_eff): E - C 16, -0.105, 16.0; E - I(T) 16, -0.256, 16.0; I(T) - C 16, -0.130, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.002, I - C +0.043
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +11
      2026-10-21 +1 (-688 to +8); 2026-10-22 +13 (-814 to +16); 2026-10-23 +9 (-74 to +13); 2026-10-26 +12 (-3229 to +17)
      2026-10-27 +8 (-904 to +13); 2026-10-28 +11 (-7 to +13); 2026-10-29 +59 (-154 to +66); 2026-10-30 +6 (-9081 to +11)
      2026-11-02 +9 (-229 to +12); 2026-11-03 +19 (-31 to +26); 2026-11-04 +10 (-496 to +16); 2026-11-05 +30 (-49 to +35)
      2026-11-06 +15 (-55 to +20); 2026-11-09 +42 (-22 to +123); 2026-11-10 +12 (-2597 to +16); 2026-11-11 +8 (-932 to +11)
== H7 OPRA replica, against OVX: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C -0.083 = (E - I(T)) -0.017 + (I(T) - C) -0.066   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.639, |E - I(T)| 0.021, |I(T) - C| 0.630; corr(E - I(T), I(T) - C) -0.060
   persistence (days, rho, n_eff): E - C 16, -0.031, 16.0; E - I(T) 16, -0.182, 16.0; I(T) - C 16, -0.064, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.016, I - C -0.067
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +14
      2026-10-21 +59 (-234 to +63); 2026-10-22 +51 (-463 to +70); 2026-10-23 +3 (-35 to +8); 2026-10-26 +10 (-426 to +13)
      2026-10-27 +3 (-225 to +9); 2026-10-28 +4 (-655 to +8); 2026-10-29 +50 (-261 to +61); 2026-10-30 +0 (-179 to +6)
      2026-11-02 +4 (-561 to +7); 2026-11-03 +18 (-57 to +21); 2026-11-04 +4 (-48 to +11); 2026-11-05 +27 (-7 to +30)
      2026-11-06 +10 (-16860 to +15); 2026-11-09 +43 (-12889 to +49); 2026-11-10 +51 (-11332 to +71); 2026-11-11 +52 (-2720 to +66)
== H7 free-feed replica, against GVZ: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C +0.039 = (E - I(T)) +0.001 + (I(T) - C) +0.038   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.192, |E - I(T)| 0.037, |I(T) - C| 0.207; corr(E - I(T), I(T) - C) -0.483
   persistence (days, rho, n_eff): E - C 16, -0.124, 16.0; E - I(T) 16, +0.131, 12.3; I(T) - C 16, -0.130, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.004, I - C +0.043
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +11
      2026-10-21 +1 (-688 to +8); 2026-10-22 +13 (-814 to +16); 2026-10-23 +9 (-74 to +13); 2026-10-26 +12 (-3229 to +17)
      2026-10-27 +8 (-904 to +13); 2026-10-28 +11 (-7 to +13); 2026-10-29 +59 (-154 to +66); 2026-10-30 +6 (-9081 to +11)
      2026-11-02 +9 (-229 to +12); 2026-11-03 +19 (-31 to +26); 2026-11-04 +10 (-496 to +16); 2026-11-05 +30 (-49 to +35)
      2026-11-06 +15 (-55 to +20); 2026-11-09 +42 (-22 to +123); 2026-11-10 +12 (-2597 to +16); 2026-11-11 +8 (-932 to +11)
== H7 free-feed replica, against OVX: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C -0.435 = (E - I(T)) -0.369 + (I(T) - C) -0.066   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.699, |E - I(T)| 0.369, |I(T) - C| 0.630; corr(E - I(T), I(T) - C) -0.264
   persistence (days, rho, n_eff): E - C 16, -0.094, 16.0; E - I(T) 16, +0.532, 4.9; I(T) - C 16, -0.064, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.368, I - C -0.067
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +14
      2026-10-21 +59 (-234 to +63); 2026-10-22 +51 (-463 to +70); 2026-10-23 +3 (-35 to +8); 2026-10-26 +10 (-426 to +13)
      2026-10-27 +3 (-225 to +9); 2026-10-28 +4 (-655 to +8); 2026-10-29 +50 (-261 to +61); 2026-10-30 +0 (-179 to +6)
      2026-11-02 +4 (-561 to +7); 2026-11-03 +18 (-57 to +21); 2026-11-04 +4 (-48 to +11); 2026-11-05 +27 (-7 to +30)
      2026-11-06 +10 (-16860 to +15); 2026-11-09 +43 (-12889 to +49); 2026-11-10 +51 (-11332 to +71); 2026-11-11 +52 (-2720 to +66)
close check (|last DBIX value - Cboe close| > 0.05, kept): no day flagged
Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.
```
"""

# A page in the real page's layout around the three marker pairs (index.html, 13 Nov 2026): the masthead's dek, the
# OPRA section with the in-sample paragraph the H7 passage stands beside, and the ledger function reading by id.
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>What Free Options Data Costs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Martian+Mono:wdth,wght@75..112.5,300..700&display=swap">
<link rel="stylesheet" href="tools/volrec.css?v=20261104">
</head>
<body>
<main class="paper">

  <section class="masthead">
    <div>
      <h1 class="title">What does free options data cost?</h1>
      <p class="dek">Lead sentence. <!-- results:headline -->old line<!-- /results:headline --></p>
    </div>
  </section>

  <section class="section" id="opra">
    <h2>Checked against the consolidated feed, at the same minute</h2>
      <div class="prose" style="margin-top:28px">
      <p><b>Rebuilt with Cboe's own rules, the free feed is not the problem.</b> Ten days, in sample.</p>
      <div class="src">Data provided by Databento (OPRA consolidated NBBO). Derived aggregates only.</div>
    </div>
    <!-- results:h7note -->old note<!-- /results:h7note -->
  </section>

</main>

<script src="tools/volrec.js"></script>
<script>
  function ledger(h) {
    const t = V.clear($("ledger"));
    const hr = V.h("tr", null, V.h("thead", null, t));
    ["", "Hypothesis", "Registered", "Where it stands", "Evidence", "File"].forEach(x => V.h("th", null, hr, x));
    const tb = V.h("tbody", null, t);
    /* results:ledger */const RESULTS = {};/* /results:ledger */
    const rows = [
      ["H1", "The premium is positive.", "6 Sep 2026", ["tested", "Tested, holds"], ["9 of 11 pairs", "t = 5.14"], "h1.md"],
      ["H3", "A model-free estimate built from free data reproduces the published Cboe index.", "12 Sep 2026", RESULTS.H3.st, RESULTS.H3.ev, "h3.md"],
      ["H5", "What free option data costs sits in the far wings.", "19 Sep 2026", RESULTS.H5.st, [RESULTS.H5.ev, "H5b holds (44 of 44)"], "h5.md"],
      ["H7", "The free feed, run through Cboe's own rules, reproduces Cboe's oil and gold volatility indices.", "8 Oct 2026", RESULTS.H7.st, RESULTS.H7.ev, "h7.md"],
      ["T", "The timing measurement. Descriptive: no test, no bar.", "6 Nov 2026", RESULTS.timing.st, RESULTS.timing.ev, "t.md"]
    ];
    rows.forEach(([id, claim, reg, st, ev, file]) => {
      const tr = V.h("tr", null, tb);
      V.h("td", { class: "hid" }, tr, id);
      V.h("td", { class: "claim" }, tr, claim);
      V.h("td", null, tr, reg);
      V.h("span", { class: "hs", "data-h": st[0] }, V.h("td", null, tr), st[1]);
      const e = V.h("td", { class: "ev" }, tr, ev[0]);
      V.h("span", null, e, ev[1]);
      V.h("a", { href: `${V.REPO}/blob/main/hypotheses/${file}` }, V.h("td", null, tr), "Read");
    });
  }
  ledger(null);
</script>
</body>
</html>
"""

# tools/volrec.css's own hiding rules, in its layout (13 Nov 2026): none of them hides a results passage.
CSS = """[hidden] { display: none !important; }
.rail-cells::-webkit-scrollbar { display: none; }
.dek {
  font-size: 19px;
}
@media (max-width: 760px) {
  .rail-brand span { display: none; }
  .ledger thead { display: none; }
  .ledger, .ledger tbody, .ledger tr, .ledger td { display: block; }
}
"""


def make_root(d, **over):
    """A temporary checkout: the four records, the page and its stylesheet, each overridable (css=None: none)."""
    root = Path(d)
    texts = {"h3": H3, "h5e": H5, "h7": H7, "timing": TIMING}
    texts.update({k: v for k, v in over.items() if k not in ("page", "css")})
    for k, rel in SR.FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(texts[k], encoding="utf-8")
    (root / "index.html").write_text(over.get("page", PAGE), encoding="utf-8")
    css = root / "tools/volrec.css"
    css.parent.mkdir(parents=True, exist_ok=True)
    if over.get("css", CSS) is None:
        css.unlink(missing_ok=True)
    else:
        css.write_text(over.get("css", CSS), encoding="utf-8")
    return root


def quiet(fn, *a):
    """fn(*a) with its printing kept out of the test's output; a crash returns None (printed), never an exit code."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a)
    except Exception as e:  # noqa: BLE001 - a crash fails the case; it is never read as an exit code
        print(f"        crashed: {type(e).__name__}: {e}")
        return None


def drop_reading(text, header):
    """The timing output without one reading: its header line up to the next reading or the close check."""
    return re.sub(re.escape(header) + r".*?\n(?=== |close check)", "", text, count=1, flags=re.S)


# ---------------- H3 ----------------
h3 = SR.h3_record(H3)
check("H3: the three verdicts and the pooled figures, exactly as written",
      h3 is not None and (h3["a"], h3["mae"], h3["n"], h3["days"], h3["b"], h3["mean"], h3["c"], h3["slope"],
                          h3["t"], h3["p"]) == ("HOLDS", "0.708", "205", "41", "HOLDS", "-0.444", "HOLDS", "+0.0455",
                                                "20.51", "0.0104"))
check("H3: Benjamini-Hochberg's two counts, all five funds, and the one fund at or over the 1.0 bar",
      h3 is not None and (h3["bh_a"], h3["bh_c"]) == ("4", "3") and sorted(h3["per"]) == ["GLD", "IWM", "QQQ", "SPY", "USO"]
      and h3["per"]["USO"] == ("1.767", "0.9155", "+0.1979", "0.0000") and h3["per"]["GLD"][0] == "0.363"
      and h3["over"] == ["USO"])
check("H3: a block whose H3c line is not the writer's is refused, never read as two parts",
      raises(lambda: SR.h3_record(mut(H3, "- **H3c HOLDS:**", "- **H3c holds:**"))))
check("H3: a fund missing from the per-fund lines is refused",
      raises(lambda: SR.h3_record(mut(H3, "QQQ 0.504, 0.0070; +0.1039, 0.0003.", ""))))
check("H3: a figure not in the record's form (0.7O8) is refused",
      raises(lambda: SR.h3_record(mut(H3, "0.708", "0.7O8"))))
check("H3: a bar other than the registered 1.0 is refused",
      raises(lambda: SR.h3_record(mut(H3, "(bar: under 1.0)", "(bar: under 1.5)"))))
check("H3: no reading of record yet reads as None (the page check then refuses it, below)",
      SR.h3_record(mut(H3, SR.MARK_H3, "**H3, a reading")) is None)
# Astra, 13 Nov 2026: the first match was taken, and nothing held the figures to the registered rules.
_h3a2 = ("- **H3a HOLDS:** pooled mean absolute gap 0.555 volatility points over 205 readings on 41 days (bar: under "
         "1.0).\n- **H3b HOLDS:**")
check("H3: a second, conflicting H3a line is refused, never read from the first",
      raises(lambda: SR.h3_record(mut(H3, "- **H3b HOLDS:**", _h3a2)), "2 times"))
check("H3: H3a HOLDS beside a mean absolute gap of 1.708 contradicts its rule (under 1.0) and is refused",
      raises(lambda: SR.h3_record(mut(H3, "gap 0.708 volatility", "gap 1.708 volatility")), "contradicts"))
check("H3: H3a FAILS beside 0.708 is refused",
      raises(lambda: SR.h3_record(mut(H3, "- **H3a HOLDS:**", "- **H3a FAILS:**")), "contradicts"))
check("H3: a figure printed at its bar (1.000) is consistent with either verdict: the writer decided unrounded",
      SR.h3_record(mut(H3, "gap 0.708 volatility", "gap 1.000 volatility")) is not None)
check("H3: H3b HOLDS beside a positive mean gap (+0.444) is refused",
      raises(lambda: SR.h3_record(mut(H3, "pooled mean gap -0.444", "pooled mean gap +0.444")), "contradicts"))
check("H3: H3c HOLDS beside p 0.0600 (registered: under 0.05) is refused",
      raises(lambda: SR.h3_record(mut(H3, "one-sided p\n  0.0104", "one-sided p\n  0.0600")), "contradicts"))
check("H3: H3c HOLDS beside a falling slope (-0.0455) is refused",
      raises(lambda: SR.h3_record(mut(H3, "level +0.0455 per point", "level -0.0455 per point")), "contradicts"))
check("H3: a pooled p-value over 1 is refused",
      raises(lambda: SR.h3_record(mut(H3, "one-sided p\n  0.0104", "one-sided p\n  1.0104")), "p-value"))
check("H3: a per-fund p-value over 1 is refused",
      raises(lambda: SR.h3_record(mut(H3, "GLD 0.363, 0.0000;", "GLD 0.363, 2.0000;")), "p-value"))
check("H3: Benjamini-Hochberg holding on 9 of 5 is refused",
      raises(lambda: SR.h3_record(mut(H3, "H3a holds on 4", "H3a holds on 9")), "Benjamini-Hochberg"))
check("H3: Benjamini-Hochberg holding on 5 of 5 when one fund (USO, 1.767) is over the bar is refused",
      raises(lambda: SR.h3_record(mut(H3, "H3a holds on 4", "H3a holds on 5")), "Benjamini-Hochberg"))
check("H3: more readings than five funds a day (206 on 41 days) is refused",
      raises(lambda: SR.h3_record(mut(H3, "over 205 readings on 41 days", "over 206 readings on 41 days")), "a day"))
# Astra's follow-up, 13 Nov 2026: Benjamini-Hochberg's counts were held to the slopes' directions, never to the
# p-values they come from; a block written twice was read from its first copy; a figure too long to be a number read
# as infinity. By hand at q 0.05 over five: H3a's p-values (0, 0, 0.0070, 0.0092, 0.9155) pass 4 (0.0092 <= 4/5 x
# 0.05 = 0.04; 0.9155 > 0.05); H3c's (0.0000, 0.0000, 0.0003, 0.2495, 0.3287) pass 3 (0.2495 > 0.04).
check("H3: H3c significant on 5 of 5 is refused: GLD's and IWM's p-values (0.3287, 0.2495) cannot pass at q 0.05",
      raises(lambda: SR.h3_record(mut(H3, "significant on 3 of 5", "significant on 5 of 5")), "p-values"))
check("H3: H3a holding on 3 of 5 is refused: its five p-values pass 4 under Benjamini-Hochberg at q 0.05",
      raises(lambda: SR.h3_record(mut(H3, "H3a holds on 4", "H3a holds on 3")), "p-values"))
check("H3: the reading of record written twice is refused, never read from its first copy",
      raises(lambda: SR.h3_record(H3 + "\n" + H3[H3.index(SR.MARK_H3):]), "2 times"))
check("H3: a slope of 309 digits (infinite as a number) is refused",
      raises(lambda: SR.h3_record(mut(H3, "level +0.0455 per", "level +" + "9" * 309 + ".0455 per")), "finite"))
check("H3: a t of 400 digits is refused",
      raises(lambda: SR.h3_record(mut(H3, "t 20.51,", "t " + "9" * 400 + ".51,")), "finite"))

# ---------------- H5e ----------------
# Astra's follow-up, 13 Nov 2026: H5e's FINAL block was read by the poster's parser and nothing held it to its rule
# (record_verdict.h5e_score: HOLDS when the mean is under 0.5 AND closer on a majority, read on 10 days or more).
h5 = got(lambda: SR.h5e_record(H5))
check("H5e: the FINAL reading, exactly as written", h5 == {"verdict": "FAILS", "mae": "0.91", "closer": "26", "n": "35"})
check("H5e: HOLDS beside a mean of 0.91 (bar: under 0.5) is refused",
      raises(lambda: SR.h5e_record(mut(H5, "- **FAILS**: the mean gap", "- **HOLDS**: the mean gap")), "contradicts"))
check("H5e: FAILS beside 0.41 and 26 of 35 days, both parts met, is refused",
      raises(lambda: SR.h5e_record(mut(H5, "to OVX: 0.91 volatility", "to OVX: 0.41 volatility")), "contradicts"))
check("H5e: closer on 36 of 35 days is refused",
      raises(lambda: SR.h5e_record(mut(H5, "on 26 of 35 counted", "on 36 of 35 counted")), "days"))
check("H5e: a FINAL reading over 9 counted days (the minimum is 10) is refused",
      raises(lambda: SR.h5e_record(mut(H5, "on 26 of 35 counted", "on 5 of 9 counted")), "minimum"))
check("H5e: a second verdict line is refused, never read from the first",
      raises(lambda: SR.h5e_record(mut(H5, "- Mean absolute gap of", "- **HOLDS**: both.\n- Mean absolute gap of")),
             "2 times"))
check("H5e: the FINAL block written twice is refused", raises(lambda: SR.h5e_record(H5 + "\n" + H5), "2 times"))
check("H5e: not written yet reads as None", got(lambda: SR.h5e_record(mut(H5, SR.BP.MARK_H5E_FINAL, "**H5e, later")))
      is None and h5 is not None)

# ---------------- H7 and its companion ----------------
h7 = SR.h7_record(H7)
check("H7: both verdicts and the registered figures, exactly as written",
      h7 is not None and (h7["a"], h7["uso"], h7["uso_n"], h7["gld"], h7["gld_n"], h7["b"], h7["gvz"], h7["n"])
      == ("FAILS", "0.316", "24", "0.034", "24", "HOLDS", "0.172", "24"))
check("H7: the companion's matched-strike figures and the edge count",
      h7 is not None and (h7["m_uso"], h7["m_gld"], h7["m_n"], h7["edge"], h7["edge_k"], h7["edge_n"])
      == ("0.132", "0.061", "24", "60", "24", "24"))
check("H7: a companion whose 'registered' figures are not the verdict's is refused",
      raises(lambda: SR.h7_record(mut(H7, "against the registered 0.316 and 0.034",
                                             "against the registered 0.315 and 0.034"))))
check("H7: a verdict without its companion readings is refused (0.132 is shown only beside 0.316)",
      raises(lambda: SR.h7_record(mut(H7, SR.MARK_H7_COMPANION, "**Other readings"))))
check("H7: a companion without its matched-strike sentence is refused",
      raises(lambda: SR.h7_record(mut(H7, "the two replicas differ by a mean absolute 0.132",
                                             "the two replicas differ by about 0.132"))))
check("H7: not read yet reads as None", SR.h7_record(mut(H7, SR.BP.MARK_H7, "**H7, later")) is None)
# Astra, 13 Nov 2026: the edge count went unchecked, repeated sentences were read from the first, and nothing held
# the verdicts to their figures.
check("H7: the edge walked on 25 of 24 days is refused",
      raises(lambda: SR.h7_record(mut(H7, "on 24 of 24 days for both", "on 25 of 24 days for both")), "edge"))
check("H7: an edge count over another sample (23 days, the readings cover 24) is refused",
      raises(lambda: SR.h7_record(mut(H7, "on 24 of 24 days for both", "on 23 of 23 days for both")), "edge"))
_m2 = ("set. With OPRA cut, the two replicas differ by a mean absolute 0.100 points for USO and 0.061 for GLD, over 24 "
       "days each, against the registered 0.316 and 0.034 on every strike OPRA lists.")
check("H7: a second, different matched-strike sentence is refused, never read from the first",
      raises(lambda: SR.h7_record(mut(H7, "set.", _m2)), "2 times"))
check("H7: a second edge sentence is refused",
      raises(lambda: SR.h7_record(mut(H7, "for both.", "for both. Cboe's walk ran past the free file's edge "
                                                       "(+/-60% of spot) on 20 of 24 days for both.")), "2 times"))
check("H7: H7a HOLDS beside oil's 0.316 (bar: 0.25 or less, each) is refused",
      raises(lambda: SR.h7_record(mut(H7, "- **H7a FAILS:**", "- **H7a HOLDS:**")), "contradicts"))
check("H7: H7b FAILS beside 0.172 (bar: 0.30 or less) is refused",
      raises(lambda: SR.h7_record(mut(H7, "- **H7b HOLDS:**", "- **H7b FAILS:**")), "contradicts"))
check("H7: a figure the writer printed as n/a is refused (the page gives every figure)",
      raises(lambda: SR.h7_record(mut(H7, "GLD 0.034 over 24 days", "GLD n/a over 24 days")), "three decimals"))
# Astra's follow-up, 13 Nov 2026: the verdict lines and the blocks were read from their first copy, the registered
# minimum of 10 days per part (record_verdict.h7_verdicts) went unchecked, and a figure of 400 digits read as infinity.
_h7a2 = ("- **H7a HOLDS:** mean absolute difference between the free-feed and OPRA Cboe replicas at the same minute: "
         "USO 0.100 over 24 days, GLD 0.034 over 24 days (bar: 0.25 or less, each).\n- **H7b HOLDS:**")
check("H7: a second, conflicting H7a line is refused, never read from the first",
      raises(lambda: SR.h7_record(mut(H7, "- **H7b HOLDS:**", _h7a2)), "2 times"))
_h7b2 = ("- **H7b FAILS:** the free-feed replica for GLD lies a mean absolute 0.400 points from GVZ's close over 24 days "
         "(bar: 0.30 or less).\n- H7c (descriptive)")
check("H7: a second H7b line is refused", raises(lambda: SR.h7_record(mut(H7, "- H7c (descriptive)", _h7b2)), "2 times"))
check("H7: the verdict block written twice is refused",
      raises(lambda: SR.h7_record(H7 + "\n" + H7[H7.index(SR.BP.MARK_H7):]), "2 times"))
check("H7: the companion readings written twice are refused",
      raises(lambda: SR.h7_record(H7 + "\n" + H7[H7.index(SR.MARK_H7_COMPANION):]), "2 times"))
check("H7: H7b HOLDS over 9 days (the registered minimum is 10) is refused",
      raises(lambda: SR.h7_record(mut(H7, "from GVZ's close over 24 days", "from GVZ's close over 9 days")), "minimum"))
_h7_9 = mut(H7, "USO 0.316 over 24 days, GLD 0.034 over 24 days", "USO 0.316 over 9 days, GLD 0.034 over 9 days")
_h7_9 = mut(mut(_h7_9, "for GLD, over 24 days each", "for GLD, over 9 days each"), "on 24 of 24 days for both",
            "on 9 of 9 days for both")
check("H7: H7a over 9 days for each fund, its companion counted alike, is refused (the minimum is 10)",
      raises(lambda: SR.h7_record(_h7_9), "minimum"))
check("H7: a figure of 400 digits (infinite as a number) is refused, whatever its verdict",
      raises(lambda: SR.h7_record(mut(mut(H7, "- **H7b HOLDS:**", "- **H7b FAILS:**"), "absolute 0.172 points",
                                      "absolute " + "9" * 400 + ".172 points")), "finite"))

# ---------------- the timing measurement ----------------
tm = SR.timing_record(TIMING)
check("timing: its days, from the reader's own first line",
      tm is not None and (tm["first"], tm["last"], tm["files"], tm["n"]) == ("2026-10-21", "2026-11-11", "16", "16"))
check("timing: all six readings, each with its three signed means and three mean absolutes as written",
      tm is not None and sorted(tm["r"]) == sorted(SR.TIMING_KEYS)
      and tm["r"][("H7 OPRA replica", "OVX")] == {"ec": "-0.083", "ei": "-0.017", "ic": "-0.066",
                                                   "aec": "0.639", "aei": "0.021", "aic": "0.630"}
      and tm["r"][("H7 OPRA replica", "GVZ")]["aei"] == "0.010" and tm["r"][("H7 OPRA replica", "GVZ")]["aic"] == "0.207"
      and tm["r"][("H7 OPRA replica", "GVZ")]["ic"] == "+0.038"
      and tm["r"][("H7 free-feed replica", "OVX")]["aei"] == "0.369"
      and tm["r"][("H7 free-feed replica", "GVZ")]["aei"] == "0.037"
      and tm["r"][("H5e skip-only", "OVX")]["aei"] == "1.117" and tm["r"][("H5e skip-only", "OVX")]["aic"] == "0.634")
check("timing: a reading missing from the output is refused",
      raises(lambda: SR.timing_record(drop_reading(TIMING, "== H7 OPRA replica, against GVZ"))))
_dup = mut(TIMING, "close check", TIMING[TIMING.index("== H7 OPRA replica, against GVZ"):
                                             TIMING.index("== H7 OPRA replica, against OVX")] + "close check", 1)
check("timing: a reading printed twice is refused", raises(lambda: SR.timing_record(_dup)))
check("timing: readings over different day counts are refused (the page states one count)",
      raises(lambda: SR.timing_record(mut(TIMING, "== H7 OPRA replica, against GVZ: 16 of 16",
                                                     "== H7 OPRA replica, against GVZ: 15 of 16", 1))))
check("timing: a reading whose mean absolutes are not the reader's form is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|E - I(T)| 0.021", "|E - I(T)| 0.02", 1))))
check("timing: an output without its fence is refused", raises(lambda: SR.timing_record(mut(TIMING, "```", "~~~", -1))))
check("timing: not read yet reads as None", SR.timing_record(mut(TIMING, SR.MARK_TIMING, "**Later")) is None)
# Astra, 13 Nov 2026: counts, dates and the figures' own arithmetic went unchecked; repeated lines were read from
# the first; only the first output block was read.
check("timing: every reading measuring 17 of 16 covered days is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "16 of 16 covered days", "17 of 16 covered days", -1)), "measured"))
check("timing: more covered days (16) than index files (15) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "(16 files)", "(15 files)")), "files"))
check("timing: a first day after the last is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "2026-10-21 to 2026-11-11 (16", "2026-11-11 to 2026-10-21 (16")),
             "dates"))
check("timing: a day that does not exist (2026-13-21) is refused, never a crash",
      raises(lambda: SR.timing_record(mut(TIMING, "DBIX days: 2026-10-21", "DBIX days: 2026-13-21")), "dates"))
check("timing: signed figures that do not add up (E - C -0.183 = -0.017 + -0.066) are refused",
      raises(lambda: SR.timing_record(mut(TIMING, "E - C -0.083 = (E - I(T)) -0.017",
                                                     "E - C -0.183 = (E - I(T)) -0.017")), "add up"))
check("timing: a mean absolute smaller than its signed mean (|E - C| 0.030 beside -0.083) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|E - C| 0.639,", "|E - C| 0.030,")), "signed mean"))
check("timing: |E - C| larger than its two parts together (0.300 > 0.010 + 0.207) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|E - C| 0.198,", "|E - C| 0.300,")), "other two together"))
# Astra's follow-up, 13 Nov 2026: E - C = (E - I) + (I - C) bounds each mean absolute by the other two, and only the
# first was held; a mean of 400 digits read as infinity.
check("timing: |E - I(T)| larger than |E - C| and |I(T) - C| together (0.500 > 0.198 + 0.207) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|E - I(T)| 0.010,", "|E - I(T)| 0.500,")), "other two together"))
check("timing: |I(T) - C| larger than the other two together (0.700 > 0.639 + 0.021) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|I(T) - C| 0.630; corr(E - I(T), I(T) - C) -0.060",
                                                     "|I(T) - C| 0.700; corr(E - I(T), I(T) - C) -0.060")),
             "other two together"))
check("timing: a mean of 400 digits (infinite as a number) is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "|E - C| 0.198,", "|E - C| " + "9" * 400 + ".198,")), "finite"))
check("timing: the reading written twice is refused",
      raises(lambda: SR.timing_record(TIMING + "\n" + TIMING[TIMING.index(SR.MARK_TIMING):]), "2 times"))
_sl = ("   signed means, points: E - C -0.083 = (E - I(T)) -0.017 + (I(T) - C) -0.066   [adds up to 0.0e+00]\n"
       "   mean absolute: |E - C| 0.639")
check("timing: a reading with its signed line printed twice is refused",
      raises(lambda: SR.timing_record(mut(TIMING, "   mean absolute: |E - C| 0.639", _sl)), "2 times"))
check("timing: a second output block is refused, never read from the first",
      raises(lambda: SR.timing_record(mut(TIMING, "Aggregates only.\n```\n",
                                                     "Aggregates only.\n```\n\n```\nmore\n```\n")), "output blocks"))
check("timing: two readings at one snapshot minute giving OVX two moves (-0.066 and -0.065) are refused",
      raises(lambda: SR.timing_record(mut(TIMING, "E - C -0.435 = (E - I(T)) -0.369 + (I(T) - C) -0.066",
                                                     "E - C -0.434 = (E - I(T)) -0.369 + (I(T) - C) -0.065")),
             "two moves"))

# ---------------- the passages ----------------
H5E = {"verdict": "FAILS", "mae": "0.91", "closer": "26", "n": "35"}     # H5's FINAL block, read by hand
rec = {"h3": h3, "h5e": H5E, "h7": h7, "timing": tm}
ok_rec = all(rec.values())
p = SR.render(rec) if ok_rec else {}
check("the headline: the poster's rule (H7 fails, H3 holds), then H3a's figures exactly as recorded",
      p.get("headline") == "Widen the strikes, and free data averages within a point of Cboe's index. On the "
      "registered test, the estimate built from free quotes missed Cboe's indices by a mean absolute "
      '<span class="m">0.708</span> volatility points over <span class="m">205</span> readings on '
      '<span class="m">41</span> days, against a limit of 1.0 written down before the data.')
check("the headline follows the record, never a typed figure (H3a's 0.708 recorded as 0.555)",
      ok_rec and '<span class="m">0.555</span>' in SR.render(dict(rec, h3=SR.h3_record(mut(H3, "0.708", "0.555"))))["headline"])
check("the headline if H7 had held: the poster's first headline",
      ok_rec and SR.headline(dict(rec, h7=dict(h7, a="HOLDS", b="HOLDS"))).startswith(
          "The free quotes are close. Most of the error is in the recipe. On the registered test"))
check("the headline if H3 had failed as well: the poster's most cautious line",
      ok_rec and SR.headline(dict(rec, h3=dict(h3, a="FAILS"))).startswith(
          "Free data misses Cboe's index by a point or more, on average. On the registered test"))
# Astra, 13 Nov 2026: the H7 passage said "gold holds, oil fails" whatever the record said. Its words fit one outcome;
# any other is refused as a whole, never rendered beside a headline and ledger that say otherwise.
check("the whole rendering refuses H7a holding: the H7 passage narrates oil failing",
      ok_rec and raises(lambda: SR.render(dict(rec, h7=dict(h7, a="HOLDS", b="HOLDS"))), "narrates"))
check("the whole rendering refuses H7a failing on gold, not oil",
      ok_rec and raises(lambda: SR.render(dict(rec, h7=dict(h7, uso="0.100", gld="0.316"))), "narrates"))
check("the whole rendering refuses H7b failing",
      ok_rec and raises(lambda: SR.render(dict(rec, h7=dict(h7, b="FAILS", gvz="0.400"))), "narrates"))

led = p.get("ledger", "")
_m = re.fullmatch(r"const RESULTS = (\{.*\});", led, re.S)
try:
    RES = json.loads(_m.group(1)) if _m else {}
except ValueError:
    RES = {}
check("the ledger's results are one JSON constant the page's script reads",
      _m is not None and set(RES) == {"H3", "H5", "H7", "timing"})
# Every row typed here by hand from the four records: each figure under its own label (Astra, 13 Nov 2026: finding a
# figure somewhere in a row passed when two figures traded places).
LEDGER = {
    "H3": {"st": ["tested", "Tested, holds"],
           "ev": ["0.708 mean absolute gap over 205 readings on 41 days, against a 1.0 limit: the reading of record, "
                  "to 11 Nov 2026",
                  "H3b and H3c hold; H3a holds for 4 of 5 funds after Benjamini-Hochberg, and crude oil (USO) reads "
                  "1.767"]},
    "H5": {"st": ["tested", "Partly tested; H5e fails"],
           "ev": "H5e FAILS at its final reading: 0.91 against a 0.5 bar; closer than the registered estimate on 26 of "
                 "35 days"},
    "H7": {"st": ["tested", "Tested; H7a fails, H7b holds"],
           "ev": ["H7a FAILS: the free and full-market rebuilds differ by 0.316 on oil and 0.034 on gold, over 24 days "
                  "(bar 0.25 each)",
                  "H7b holds: gold's free rebuild sits 0.172 from GVZ's close (bar 0.30). On the strikes both feeds "
                  "carry, oil's rebuilds differ by 0.132: a companion reading, not the test"]},
    "timing": {"st": ["tested", "Read once, descriptive"],
               "ev": ["At the snapshot minute, Cboe's method on the full market's quotes sits 0.021 points from OVX "
                      "and 0.010 from GVZ",
                      "the indices then move a mean absolute 0.630 (OVX) and 0.207 (GVZ) before the close; 16 days, "
                      "21 Oct to 11 Nov 2026"]},
}
check("the ledger, row by row, exactly as typed by hand from the records", RES == LEDGER)
_ev = lambda k, i: RES.get(k, {}).get("ev", ["", ""])[i] if isinstance(RES.get(k, {}).get("ev"), list) else ""
check("H3's row: tested and holding, with the pooled figure, its readings and days as recorded",
      RES.get("H3", {}).get("st") == ["tested", "Tested, holds"] and "0.708" in _ev("H3", 0)
      and "205 readings" in _ev("H3", 0) and "41 days" in _ev("H3", 0) and "1.0" in _ev("H3", 0))
check("H3's row: H3b and H3c, Benjamini-Hochberg's count, and the fund over the bar with its figure",
      "H3b and H3c hold" in _ev("H3", 1) and "4 of 5" in _ev("H3", 1) and "USO" in _ev("H3", 1)
      and "1.767" in _ev("H3", 1))
check("H5's row: partly tested, and H5e's FINAL verdict and figures",
      RES.get("H5", {}).get("st") == ["tested", "Partly tested; H5e fails"]
      and "H5e FAILS" in str(RES.get("H5", {}).get("ev")) and "0.91" in str(RES.get("H5", {}).get("ev"))
      and "26 of 35" in str(RES.get("H5", {}).get("ev")))
check("H7's row: each part's verdict in its state, the registered figures, and the companion named as one",
      RES.get("H7", {}).get("st") == ["tested", "Tested; H7a fails, H7b holds"] and "H7a FAILS" in _ev("H7", 0)
      and "0.316" in _ev("H7", 0) and "0.034" in _ev("H7", 0) and "0.172" in _ev("H7", 1)
      and "0.132" in _ev("H7", 1) and "companion" in _ev("H7", 1))
check("the timing row: read once, descriptive; the minute's and the move's figures, and its days",
      RES.get("timing", {}).get("st") == ["tested", "Read once, descriptive"] and "0.021" in _ev("timing", 0)
      and "0.010" in _ev("timing", 0) and "0.630" in _ev("timing", 1) and "0.207" in _ev("timing", 1)
      and "16 days" in _ev("timing", 1) and "21 Oct" in _ev("timing", 1) and "11 Nov 2026" in _ev("timing", 1))
check("the ledger's text names no feed the site's code may not load (the pressure test: no opra, databento, cbbo)",
      bool(led) and not re.search(r"databento|cbbo|\bopra\b", led, re.I))
check("nothing in the ledger's text can end its marker comment or the script", bool(led) and "*/" not in led
      and "</script" not in led.lower())

note = p.get("h7note", "")
check("the H7 passage gives every figure as recorded, in the page's number style",
      all(f'<span class="m">{v}</span>' in note for v in
          ("0.316", "0.034", "0.172", "0.132", "0.061", "24", "0.021", "0.010", "0.369", "0.037", "0.630", "0.207",
           "1.117", "0.634", "16")))
M = lambda v: f'<span class="m">{v}</span>'   # noqa: E731
# Each figure bound to its fund, feed, measure and sign, typed here by hand from the records (Astra, 13 Nov 2026).
NOTE = [f"Gold holds: the free and full-market rebuilds differ by {M('0.034')} points over {M('24')} days",
        f"the free rebuild sits {M('0.172')} from GVZ's close (bars 0.25 and 0.30)",
        f"Oil does not: the two rebuilds differ by {M('0.316')} over {M('24')} days, over the 0.25 bar, so H7a fails",
        f"Cboe's rule walked past that edge on {M('24')} of {M('24')} days for both funds",
        f"the rebuilds differ by {M('0.132')} for oil and {M('0.061')} for gold",
        f"On the {M('16')} days from 21 October to 11 November 2026",
        f"Cboe's method on OPRA's quotes sat a mean absolute {M('0.021')} points from OVX and {M('0.010')} from GVZ "
        "at the snapshot minute",
        f"the free feed's rebuild sat {M('0.369')} from OVX and {M('0.037')} from GVZ",
        f"OVX then moved a mean absolute {M('0.630')} points and GVZ {M('0.207')}",
        f"H5e's skip-only estimate was already {M('1.117')} points from OVX at its snapshot minute, and OVX then moved "
        f"a mean absolute {M('0.634')} before the close"]
for _f in NOTE:
    check(f"the H7 passage binds its figures: {re.sub(r'<[^>]+>', '', _f)[:90]}", _f in note)
# I(T) - C is the index at the snapshot less its close, so OVX's -0.066 means it closed HIGHER than at the snapshot:
# the signed figures are named in that direction, never called the move to the close (Astra, 13 Nov 2026).
check("the signed figures are the index at the snapshot minus its close, -0.066 for OVX and +0.038 for GVZ",
      f"the index at the snapshot minus its close averaged {M('-0.066')} for OVX and {M('+0.038')} for GVZ" in note
      and "averaging" not in note)
check("each of its two blocks credits Databento and Cboe, and says it shows aggregates only",
      note.count('<div class="src">Data provided by Databento') == 2 and note.count("Cboe Global Markets") == 2
      and note.count("Derived aggregates only") == 2)
check("it says the companion stands beside the test and that both verdicts stand, and it is dated",
      "never in its place" in note and "The verdicts stand as registered" in note
      and "Added 13 November 2026" in note and "read once on 13 November 2026" in note)
check("its days come from the record (21 October to 11 November 2026)", "21 October to 11 November 2026" in note)

# ---------------- writing and checking the page ----------------
page = SR.apply(PAGE, p) if p else PAGE
check("apply writes each passage between its own markers and leaves the rest of the page as it was",
      bool(p) and all(f"{a}{p[k]}{b}" in page for k, (a, b) in SR.MARKERS.items())
      and page.replace(p.get("headline", "\0"), "old line", 1).replace(p.get("h7note", "\0"), "old note", 1)
      .replace(p.get("ledger", "\0"), "const RESULTS = {};", 1) == PAGE)
check("a page that carries exactly the rendered passages has no difference", bool(p) and SR.check(page, rec=rec) == [])
_bad = mut(page, '<span class="m">0.316</span>', '<span class="m">0.216</span>', 1)
_d = SR.check(_bad, rec=rec)
check("a changed figure is a difference, named by its passage and shown", len(_d) == 1 and "h7note" in _d[0]
      and "0.216" in _d[0])
_d2 = SR.check(mut(page, "0.708", "0.71", -1), rec=rec)
check("a figure re-rounded on the page (0.708 to 0.71) is a difference in each passage that holds it",
      len(_d2) == 2 and any("headline" in x for x in _d2) and any("ledger" in x for x in _d2))
check("a missing marker is a difference, never a skipped passage",
      any("h7note" in x for x in SR.check(mut(page, "<!-- /results:h7note -->", ""), rec=rec)))
check("a duplicated marker is a difference", SR.check(page + "<!-- results:headline -->", rec=rec) != [])
_swap = mut(PAGE, "<!-- results:h7note -->old note<!-- /results:h7note -->",
                     "<!-- /results:h7note -->old note<!-- results:h7note -->")
check("markers out of order are a difference", SR.check(_swap, rec=rec) != [])
check("apply refuses a page without a marker rather than leaving a passage unwritten",
      raises(lambda: SR.apply(mut(PAGE, "<!-- results:headline -->", ""), p)) if p else False)

# ---------------- where the passages sit ----------------
# Astra, 13 Nov 2026: comparing the bytes between the markers passed a passage moved somewhere it is never shown,
# the in-sample paragraph removed from above the H7 passage, rows reading each other's results, and a contradicting
# claim written outside the markers. Each case below keeps every passage exactly as rendered.
# The ledger function is pinned by its fingerprint (its text with the generated passage cut out). The real page's is
# SR.LEDGER_SHA256; this fixture's own is FIX, and every case below but one is held to FIX.
FIX = got(lambda: SR.ledger_fingerprint(PAGE))


def placed(old, new, count=1):
    if not p:
        return ["no rendering"]
    r = got(lambda: SR.placement(mut(page, old, new, count), CSS, FIX))
    return ["crashed"] if r is None else r


_tpl = mut(page, "    <!-- results:h7note -->", "    <template><!-- results:h7note -->")
check("placement: the page in the real layout, with its passages written, has no problem",
      bool(p) and got(lambda: SR.placement(page, CSS, FIX)) == [])
check("placement: a passage moved into a template is a problem, though its words still match the record",
      bool(p) and SR.check(_tpl, rec=rec) == []
      and any("h7note" in x and "template" in x for x in got(lambda: SR.placement(_tpl, CSS, FIX)) or []))
check("placement: a passage in a section marked hidden is a problem",
      any("h7note" in x and "hidden" in x
          for x in placed('<section class="section" id="opra">', '<section class="section" id="opra" hidden>')))
check("placement: the dek moved out of the masthead is a problem",
      any("headline" in x for x in placed('<section class="masthead">',
                                          '<section class="masthead"></section><section>')))
check("placement: a start marker swallowed by another comment is a problem (no live marker is left)",
      any("headline" in x and "0 live" in x for x in placed("<!-- results:headline -->",
                                                            "<!-- <!-- results:headline -->")))
check("placement: the in-sample paragraph gone from above the H7 passage is a problem",
      any("in-sample" in x for x in placed("<b>Rebuilt with Cboe's own rules, the free feed is not the problem.</b>",
                                           "<b>Rebuilt.</b>")))
check("placement: another block between the in-sample paragraph and the H7 passage is a problem",
      any("in-sample" in x for x in placed("    <!-- results:h7note -->",
                                           '    <div class="prose"><p>Other.</p></div>\n    <!-- results:h7note -->')))
check("placement: an unmarked paragraph saying H7a holds is a problem",
      any("H7a holds" in x for x in placed("<!-- /results:h7note -->",
                                           "<!-- /results:h7note -->\n    <p>H7a holds: 0.216.</p>")))
check("placement: a hand-typed row giving H3's verdict is a problem",
      any("H3 fails" in x for x in placed('"H5b holds (44 of 44)"', '"H3 fails (0.9)"')))
check("placement: a row reading another hypothesis's results is a problem",
      any("ledger" in x for x in placed("RESULTS.H3.st, RESULTS.H3.ev,", "RESULTS.H7.st, RESULTS.H7.ev,")))
check("placement: the rows' columns read in another order is a problem",
      any("ledger" in x for x in placed("rows.forEach(([id, claim, reg, st, ev, file]) => {",
                                        "rows.forEach(([id, claim, reg, ev, st, file]) => {")))
check("placement: the results read anywhere else in the script is a problem",
      any("ledger" in x for x in placed("    const rows = [", "    const extra = RESULTS.H7.ev;\n    const rows = [")))
check("placement: the ledger's passage commented out on its line is a problem",
      any("ledger" in x for x in placed("    /* results:ledger */", "    // /* results:ledger */")))
check("placement: the ledger in a script that never runs (type text/plain) is a problem",
      any("ledger" in x for x in placed("<script>\n  function ledger",
                                        '<script type="text/plain">\n  function ledger')))
# Astra's follow-up, 13 Nov 2026: the ledger was held by lines it contains, so an early return or a row overwritten
# after its declaration still matched; a claim wrapped across lines, split by a tag or joined by an entity went
# unseen; and the attributes around a passage could not show a style element or a hidden in-sample block.
check("placement: the fixture's ledger has a fingerprint, the same before and after the passages are written",
      FIX is not None and FIX == got(lambda: SR.ledger_fingerprint(page)))
check("placement: by default the real page's pinned fingerprint is applied, and the fixture's is not it",
      FIX is not None and FIX != SR.LEDGER_SHA256
      and any("ledger" in x and "fingerprint" in x for x in got(lambda: SR.placement(page, CSS)) or []))
check("placement: an early return in the ledger function is a problem, though every line it reads is still there",
      any("ledger" in x and "fingerprint" in x
          for x in placed("  function ledger(h) {\n", "  function ledger(h) {\n    return;\n")))
check("placement: a row's evidence overwritten after the rows are declared is a problem",
      any("ledger" in x and "fingerprint" in x
          for x in placed("    rows.forEach(", "    rows[1][4] = rows[3][4];\n    rows.forEach(")))
check("placement: an unmarked paragraph saying H7a holds across a line break is a problem",
      any("H7a holds" in x for x in placed("<!-- /results:h7note -->",
                                           "<!-- /results:h7note -->\n    <p>H7a\n    holds.</p>")))
check("placement: a claim split by a tag (<b>H7a</b> holds) is a problem",
      any("H7a holds" in x for x in placed("<!-- /results:h7note -->",
                                           "<!-- /results:h7note -->\n    <p><b>H7a</b> holds.</p>")))
check("placement: a claim joined by an entity (H7a&nbsp;holds) is a problem",
      any("H7a" in x and "holds" in x for x in placed("<!-- /results:h7note -->",
                                                      "<!-- /results:h7note -->\n    <p>H7a&nbsp;holds.</p>")))
check("placement: a style element on the page is a problem (the site's styles live in tools/volrec.css)",
      any("style" in x for x in placed("</head>", "<style>.dek { display: none }</style>\n</head>")))
check("placement: a second stylesheet linked from the page is a problem (only tools/volrec.css and the fonts)",
      any("stylesheet" in x for x in placed("</head>", '<link rel="stylesheet" href="tools/other.css">\n</head>')))
check("placement: the page's own stylesheet under a new cache key is no problem (the key changes with the sheet)",
      placed("tools/volrec.css?v=20261104", "tools/volrec.css?v=20261120") == [])
check("placement: a stylesheet that imports another is a problem",
      any("@import" in x for x in got(lambda: SR.css_hides('@import url("other.css");\n' + CSS)) or []))
check("placement: the in-sample paragraph's block marked hidden is a problem",
      any("in-sample" in x for x in placed('<div class="prose" style="margin-top:28px">\n      <p><b>Rebuilt',
                                           '<div class="prose" style="margin-top:28px" hidden>\n      <p><b>Rebuilt')))
check("placement: the in-sample sentence in a hidden paragraph is a problem",
      any("in-sample" in x for x in placed("<p><b>Rebuilt with", "<p hidden><b>Rebuilt with")))
check("placement: the stylesheet's own hiding rules (the rail, [hidden], the ledger's head on phones) are no problem",
      got(lambda: SR.css_hides(CSS)) == [])
check("placement: a stylesheet rule hiding the dek on phones is a problem",
      any(".dek" in x for x in got(lambda: SR.css_hides(
          CSS + "@media (max-width: 480px) {\n  .masthead .dek { display: none; }\n}\n")) or []))
check("placement: a rule hiding the credit lines (.src) is a problem",
      any(".src" in x for x in got(lambda: SR.css_hides(CSS + ".prose .src { visibility: hidden; }\n")) or []))
check("placement: a rule making the measured figures transparent (.m, opacity 0) is a problem",
      any(".m" in x for x in got(lambda: SR.css_hides(CSS + ".m { opacity: 0; }\n")) or []))
check("placement: a rule that only styles the dek (opacity 0.8, display block) is no problem",
      got(lambda: SR.css_hides(CSS + ".dek { opacity: 0.8; display: block; }\n")) == [])
check("placement: a page whose stylesheet hides a passage is a problem",
      any(".dek" in x for x in got(lambda: SR.placement(page, CSS + ".dek { display: none }\n", FIX)) or []))

with tempfile.TemporaryDirectory() as d:
    root = make_root(d, h7=mut(H7, SR.BP.MARK_H7, "**H7, later"), page=page)
    _p = SR.check(page, root=root)
    check("a record not yet written is a difference, never a pass", bool(_p) and any("H7" in x for x in _p))
with tempfile.TemporaryDirectory() as d:
    root = make_root(d, h3=mut(H3, "0.708 volatility points", "0.708 points"), page=page)
    check("a record not in the writer's form is a difference, never a pass", SR.check(page, root=root) != [])
with tempfile.TemporaryDirectory() as d:
    root = make_root(d, page=page)
    check("the four records read from a checkout give exactly the passages above",
          SR.check(page, root=root) == [] and SR.record(root)["h5e"] == H5E)

with tempfile.TemporaryDirectory() as d:
    root = make_root(d)                      # the stale page
    before = (root / "index.html").read_bytes()
    rc = quiet(SR.main, ["--check"], root, FIX)
    check("--check on a stale page exits 1 and writes nothing", rc == 1 and (root / "index.html").read_bytes() == before)
    rc2 = quiet(SR.main, [], root, FIX)
    after = (root / "index.html").read_bytes()
    rc3 = quiet(SR.main, ["--check"], root, FIX)
    rc4 = quiet(SR.main, [], root, FIX)
    check("the plain run writes the passages; --check then exits 0; a second run changes nothing",
          rc2 == 0 and rc3 == 0 and rc4 == 0 and after != before and (root / "index.html").read_bytes() == after)
    rc5 = quiet(SR.main, ["--check"], make_root(d, timing=mut(TIMING, SR.MARK_TIMING, "**Later"), page=after.decode()),
                FIX)
    check("--check exits 1 when a record is missing, even on a page that was right before", rc5 == 1)
with tempfile.TemporaryDirectory() as d:
    hid = mut(page, "    <!-- results:h7note -->", "    <template><!-- results:h7note -->")
    rc6 = quiet(SR.main, ["--check"], make_root(d, page=hid), FIX)
    check("--check exits 1 for a passage moved into a template, though every passage matches its record", rc6 == 1)
    root = make_root(d, page=mut(PAGE, "    <!-- results:h7note -->", "    <template><!-- results:h7note -->"))
    before = (root / "index.html").read_bytes()
    rc7 = quiet(SR.main, [], root, FIX)
    check("the plain run refuses a page whose passage would be hidden, and writes nothing",
          rc7 == 1 and (root / "index.html").read_bytes() == before)
with tempfile.TemporaryDirectory() as d:
    check("--check exits 0 on the right page with its stylesheet (so the two cases below fail for their reason)",
          quiet(SR.main, ["--check"], make_root(d, page=page), FIX) == 0)
    check("--check exits 1 when the stylesheet hides a passage, though the page itself is right",
          quiet(SR.main, ["--check"], make_root(d, page=page, css=CSS + ".dek { display: none; }\n"), FIX) == 1)
    check("--check exits 1 when the stylesheet is missing: a problem, never a crash",
          quiet(SR.main, ["--check"], make_root(d, page=page, css=None), FIX) == 1)

src = (R / "tools/site_results.py").read_text(encoding="utf-8")
check("the standard library and the poster's own parsers only: no requests, no numerical library",
      not re.search(r"^\s*(?:import|from)\s+(?:requests|numpy|pandas)\b", src, re.M))
check("the poster's parsers are imported, never retyped (one implementation of each reading)",
      "h5e_final" in src and "h7_reading" in src and "def h5e_final" not in src and "def h7_reading" not in src)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
