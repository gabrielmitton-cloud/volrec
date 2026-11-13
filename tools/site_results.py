#!/usr/bin/env python3
"""The public page's results, generated from the hypothesis files: one figure, one place.

WHY THIS EXISTS (13 Nov 2026)
-----------------------------
On 13 Nov 2026, with H5e's FINAL reading (12 Nov), H7's verdict (13 Nov), H3's reading of record (scored 13 Nov)
and the timing measurement (read once, 13 Nov) all in the hypothesis files, the page's ledger still gave H3 as
"0.41 mean gap over 90 readings to 9 Oct" and H7 as "Collecting": figures typed by hand go stale (the Bloomberg
figures stayed wrong for 25 days, 17 Oct - 11 Nov). Gabriel decided on 12 Nov that the page's results table be
built from the hypothesis files, with a plain results line worded like the poster's headline and the companion
readings beside the verdicts.

This reads the four records and writes three passages of index.html between markers:
  headline   the dek's results line: the poster's headline, by the poster's own rule
             (poster/build_poster.py headline(), decided by Gabriel 21 Oct), then H3a's figures;
  ledger     the ledger's results, one JSON constant inside the page's script;
  h7note     two blocks in the OPRA section: H7's verdict with its companion, and the timing measurement.
Markers: <!-- results:NAME --> ... <!-- /results:NAME --> in HTML, /* results:NAME */ ... /* /results:NAME */ in
the script. Every figure is printed exactly as its record writes it; nothing is re-rounded. The ledger's text never
says "OPRA" or "Databento": the pressure test refuses those words anywhere in the site's code (the site must never
load licensed data), so it says "full-market"; the h7note blocks, which are prose, say it and credit it.

The verdict blocks are read by the poster's own parsers (build_poster.h5e_final, h7_reading), never retyped. A
record that is missing or not in its writer's form is refused: the page check then fails, never passes.

Hardened 13 Nov 2026 after the Astra review of the first version: each statement must appear exactly once; the
figures must agree with their own verdicts under the registered rules (bars imported, never retyped), and with
each other (counts, dates, the timing reading's two-part sum); the H7 passage is written for the outcome on record
and refuses any other; and placement() checks where the passages sit, what stands beside them, how the ledger's
script reads them, and that no other sentence on the page states their verdicts.

Hardened again 13 Nov 2026 after Astra's follow-up review: each record block, and each verdict line in it, is read
only when written once; H5e and H7 are held to their registered minimum days and rules, Benjamini-Hochberg's counts
to the p-values printed beside them, the timing reading to all three of its triangle bounds, and every figure must be
a finite number. The ledger function is pinned by its fingerprint (LEDGER_SHA256): any change to it fails the check
until someone has looked at the ledger in a browser and re-pinned it. The page's words are read as a reader meets
them (across lines and tags), the page may hold no style element and link no stylesheet but its own and its fonts,
and tools/volrec.css may import none and hide nothing beyond its four accepted rules (ACCEPTED_HIDES).
What a static check cannot see - how a browser finally renders the page - stays the look in a browser that
CLAUDE.md asks for after every page change (section 8, item 6).

  python tools/site_results.py            # write the passages into index.html (nothing else changes)
  python tools/site_results.py --check    # compare only, write nothing; exit 1 on any difference
"""
import argparse
import hashlib
import html
import json
import math
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "poster"), str(ROOT / "tools")]
import build_poster as BP  # noqa: E402  (the poster's record parsers and headline rule: one implementation)
import h3_scorer as HS  # noqa: E402  (H3's registered bar and significance level, frozen in the scorer)
import record_verdict as RV  # noqa: E402  (H5e's and H7's registered bars, as the frozen writer applies them)

Unrecognised = BP.Unrecognised
REPO = "https://github.com/gabrielmitton-cloud/volrec/blob/main/"
FILES = {"h3": BP.H3_FILE.relative_to(BP.ROOT).as_posix(), "h5e": BP.H5_FILE.relative_to(BP.ROOT).as_posix(),
         "h7": BP.H7_FILE.relative_to(BP.ROOT).as_posix(), "timing": "hypotheses/2026-11-06-index-timing.md"}
LABEL = {"h3": "H3's reading of record", "h5e": "H5e's FINAL reading", "h7": "H7's reading",
         "timing": "the timing measurement's reading"}
MARKERS = {"headline": ("<!-- results:headline -->", "<!-- /results:headline -->"),
           "h7note": ("<!-- results:h7note -->", "<!-- /results:h7note -->"),
           "ledger": ("/* results:ledger */", "/* /results:ledger */")}

# The marks the records begin with: H3's written by Vega on 13 Nov from the frozen scorer's output, the companion
# copied from the cloud workflow's companion step (13 Nov, 03:28 UTC), the timing reading's from its one run.
MARK_H3 = "**H3, the reading of record over the series to Wed 11 Nov 2026**"
MARK_H7_COMPANION = "**Companion readings, added 13 Nov 2026 beside the verdict above"
MARK_TIMING = "**Read once, 13 November 2026"
H7_WINDOW = "9 Oct - 11 Nov 2026"         # in record_verdict.MARK_H7; the passage names it in words
if H7_WINDOW not in BP.MARK_H7:
    raise Unrecognised(f"record_verdict.MARK_H7 no longer names {H7_WINDOW}: the H7 passage's window would be wrong")

FUNDS = tuple(sorted(p[0] for p in BP.PAIRS))
NAME = {fund: what for fund, _, what in BP.PAIRS}        # USO -> "crude oil"

# ---------------- reading the records ----------------
H3_A = re.compile(r"- \*\*H3a (HOLDS|FAILS):\*\* pooled mean absolute gap (\d+\.\d{3}) volatility points over (\d+) "
                  r"readings on (\d+) days \(bar: under " + re.escape(str(HS.H3A_BAR)) + r"\)\.")
H3_B = re.compile(r"- \*\*H3b (HOLDS|FAILS):\*\* pooled mean gap ([+-]\d+\.\d{3}) \(registered: negative;")
H3_C = re.compile(r"- \*\*H3c (HOLDS|FAILS):\*\* pooled slope of the absolute gap on the index level "
                  r"([+-]\d+\.\d{4}) per point, t (-?\d+\.\d{2}), one-sided p (\d\.\d{4}) \(")
H3_BH = re.compile(r"H3a holds on (\d) of 5, and H3c's slope is positive and significant on (\d) of 5\.")
H3_PER = re.compile(r"\b(GLD|IWM|QQQ|SPY|USO) (\d+\.\d{3}), (\d\.\d{4}); ([+-]\d+\.\d{4}), (\d\.\d{4})\.")

COMP_MATCHED = re.compile(r"the two replicas differ by a mean absolute (\d+\.\d{3}) points for USO and (\d+\.\d{3}) "
                          r"for GLD, over (\d+) days each, against the registered (\d+\.\d{3}) and (\d+\.\d{3}) on "
                          r"every strike OPRA lists\.")
COMP_EDGE = re.compile(r"Cboe's walk ran past the free file's edge \(\+/-(\d+)% of spot\) on (\d+) of (\d+) days "
                       r"for both\.")

TIMING_KEYS = (("H5e registered", "OVX"), ("H5e skip-only", "OVX"), ("H7 OPRA replica", "GVZ"),
               ("H7 OPRA replica", "OVX"), ("H7 free-feed replica", "GVZ"), ("H7 free-feed replica", "OVX"))
_S, _A = r"([+-]\d+\.\d{3})", r"(\d+\.\d{3})"
T_DAYS = re.compile(r"DBIX days: (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}) \((\d+) files\)\.")
T_HEAD = re.compile(r"== (H5e registered|H5e skip-only|H7 OPRA replica|H7 free-feed replica), against (OVX|GVZ): "
                    r"(\d+) of (\d+) covered days measured;")
T_SIGNED = re.compile(r"^   signed means, points: E - C " + _S + r" = \(E - I\(T\)\) " + _S + r" \+ \(I\(T\) - C\) "
                      + _S + r"   ", re.M)
T_ABS = re.compile(r"^   mean absolute: \|E - C\| " + _A + r", \|E - I\(T\)\| " + _A + r", \|I\(T\) - C\| " + _A + ";",
                   re.M)


def _flat(s):
    """A block with its wrapped lines joined, so a sentence split across lines reads as one."""
    return re.sub(r"\s*\n\s*", " ", s)


def _once(rx, t, what, who):
    """The one match of rx in t. A statement written twice is refused, never read from its first copy (Astra,
    13 Nov 2026: a second, conflicting line went unseen)."""
    ms = list(rx.finditer(t))
    if len(ms) != 1:
        raise Unrecognised(f"{who} states {what} {len(ms)} times; the page reads it exactly once - it will not guess.")
    return ms[0]


def _one_block(text, mark, who, lines=()):
    """The record block that starts at mark (the poster's _block), read only when the mark is written once and each
    of `lines` (pattern, what) stands in it exactly once; None when the mark is not there. Astra's follow-up, 13 Nov
    2026: _block and the poster's parsers read the first copy of a block or a verdict line, so a second, conflicting
    copy went unseen."""
    copies = text.count(mark)
    if copies > 1:
        raise Unrecognised(f"{who} is written {copies} times; the page reads one record - it will not guess.")
    b = BP._block(text, mark) if copies else None
    for rx, what in lines if b is not None else ():
        _once(rx, b, what, who)
    return b


def _finite(who, *figures):
    """Every figure a finite number. A figure of hundreds of digits converts to infinity, which every bar then judges
    (Astra's follow-up, 13 Nov 2026: a slope of 309 digits read as positive)."""
    bad = [f for f in figures if not math.isfinite(float(f))]
    if bad:
        raise Unrecognised(f"{who}: a figure that is not a finite number ({bad[0][:16]}...) - the page will not guess.")


def _bh_range(ps):
    """The fewest and the most of these p-values Benjamini-Hochberg passes at the scorer's q (its own function and q,
    never retyped), over every unrounded value each printed figure can stand for. Its count only falls as any p-value
    rises, so the ends are every p-value half a printed unit up, and every one half a unit down (kept to 0 and 1)."""
    ends = []
    for side in (1, -1):
        fam = {i: min(1.0, max(0.0, float(s) + side * 0.5 * 10 ** -len(s.split(".")[1]))) for i, s in enumerate(ps)}
        ends.append(len(HS.analyze.benjamini_hochberg(fam, HS.BH_Q)[0]))
    return tuple(ends)


def _sure(s, rule):
    """Whether a printed figure meets a monotone rule (x < bar, x <= bar, x > 0) whatever its unrounded value:
    'yes', 'no', or None when its rounding leaves the answer open. The writers decide on unrounded values, so a
    figure printed at its bar is consistent with either verdict."""
    x, h = float(s), 0.5 * 10 ** -len(s.split(".")[1])     # half a unit in the last printed place
    lo, hi = rule(x - h), rule(x + h)
    return "yes" if lo and hi else "no" if not (lo or hi) else None


def _all(*answers):
    """Several _sure answers that must all be 'yes' (H3c: p under its level AND a rising slope)."""
    return "no" if "no" in answers else "yes" if all(a == "yes" for a in answers) else None


def _agrees(verdict, sure):
    """False when the printed figures rule a verdict out under its registered rule."""
    return not ((verdict == "HOLDS" and sure == "no") or (verdict == "FAILS" and sure == "yes"))


def _h3_contradictions(r):
    """Where H3's figures disagree with its own verdicts, its counts or each other: sentences, empty if none."""
    out, k = [], len(FUNDS)
    n, days = int(r["n"]), int(r["days"])
    if not 1 <= days <= n <= k * days:
        out.append(f"{n} readings on {days} days is not one to {k} readings a day")
    rules = (("H3a", r["a"], _sure(r["mae"], lambda m: m < HS.H3A_BAR), f"a mean absolute gap of {r['mae']}"),
             ("H3b", r["b"], _sure(r["mean"], lambda m: m < 0), f"a mean gap of {r['mean']}"),
             ("H3c", r["c"], _all(_sure(r["p"], lambda q: q < HS.ALPHA), _sure(r["slope"], lambda s: s > 0)),
              f"a slope of {r['slope']} at p {r['p']}"))
    out += [f"{part} {verdict} beside {what} contradicts its registered rule"
            for part, verdict, sure, what in rules if not _agrees(verdict, sure)]
    if any(not 0 <= float(q) <= 1 for q in [r["p"]] + [x for f in FUNDS for x in (r["per"][f][1], r["per"][f][3])]):
        out.append("a p-value outside 0 to 1")
    under = sum(_sure(r["per"][f][0], lambda m: m < HS.H3A_BAR) != "no" for f in FUNDS)
    rising = sum(_sure(r["per"][f][2], lambda s: s > 0) != "no" for f in FUNDS)
    if int(r["bh_a"]) > under or int(r["bh_c"]) > rising:
        out.append(f"Benjamini-Hochberg's counts ({r['bh_a']} and {r['bh_c']} of {k}) exceed the {under} funds under "
                   f"the bar and the {rising} with a rising slope")
    # Astra's follow-up, 13 Nov 2026: the direction alone passed "5 of 5" with two p-values over q. The counts are the
    # scorer's Benjamini-Hochberg on the per-fund p-values printed beside them (H3a's, then H3c's).
    ra, rc = (_bh_range([r["per"][f][i] for f in FUNDS]) for i in (1, 3))
    if not (ra[0] <= int(r["bh_a"]) <= ra[1] and rc[0] <= int(r["bh_c"]) <= rc[1]):
        out.append(f"Benjamini-Hochberg at q {HS.BH_Q} passes {ra[0]} to {ra[1]} of {k} on H3a's printed p-values and "
                   f"{rc[0]} to {rc[1]} on H3c's, not the {r['bh_a']} and {r['bh_c']} recorded")
    return out


def h3_record(text):
    """H3's reading of record -> dict of the figures as written; None if not written; Unrecognised if malformed,
    repeated, or at odds with its own verdicts and counts."""
    who = "H3's reading of record"
    b = _one_block(text, MARK_H3, who)
    if b is None:
        return None
    t = _flat(b)
    lines = ((H3_A, "H3a's line"), (H3_B, "H3b's line"), (H3_C, "H3c's line"), (H3_BH, "its two corrected counts"))
    a, bb, c, bh = (_once(rx, t, what, who) for rx, what in lines)
    i = t.find("Per underlying")
    found = H3_PER.findall(t[i:]) if i >= 0 else []
    per = {m[0]: m[1:] for m in found}
    if len(found) != len(FUNDS) or sorted(per) != list(FUNDS):
        raise Unrecognised("H3's reading of record found but its per-fund lines not recognised - the page will not "
                           "guess.")
    rec = {"a": a[1], "mae": a[2], "n": a[3], "days": a[4], "b": bb[1], "mean": bb[2], "c": c[1], "slope": c[2],
           "t": c[3], "p": c[4], "bh_a": bh[1], "bh_c": bh[2], "per": per,
           # The bar is "under 1.0", so a fund at or over 1.0 is over it: a comparison, not a new figure.
           "over": [f for f in FUNDS if float(per[f][0]) >= HS.H3A_BAR]}
    _finite(who, rec["mae"], rec["mean"], rec["slope"], rec["t"], rec["p"], *(x for f in FUNDS for x in per[f]))
    problems = _h3_contradictions(rec)
    if problems:
        raise Unrecognised(f"{who}: " + "; ".join(problems) + " - the page will not guess.")
    return rec


# H5e's FINAL block as record_verdict.block_h5e(final=True) writes it: one verdict line, one mean, one count.
H5E_LINES = ((re.compile(r"^- \*\*[A-Z][A-Z ]*\*\*", re.M), "its verdict"),
             (re.compile(r"^- Mean absolute gap of the skip-only estimate to OVX:", re.M), "its mean gap"),
             (re.compile(r"^- Closer to OVX than the registered estimate on ", re.M), "its count of closer days"))


def _h5e_contradictions(v):
    """Where H5e's figures disagree with its verdict, its count or its minimum, under the writer's own rule
    (record_verdict.h5e_score: HOLDS when the mean gap is under the bar AND closer on a majority of days; a FINAL
    reading is written only on the registered minimum of days or more): sentences, empty if none."""
    n, closer, out = int(v["n"]), int(v["closer"]), []
    if n < RV.H5E_MIN_DAYS:
        out.append(f"a reading over {n} counted days, under the registered minimum of {RV.H5E_MIN_DAYS}")
    if closer > n:
        out.append(f"closer on {closer} of {n} days")
    sure = _all(_sure(v["mae"], lambda m: m < RV.H5E_BAR), "yes" if 2 * closer > n else "no")
    if not _agrees(v["verdict"], sure):
        out.append(f"{v['verdict']} beside a mean gap of {v['mae']}, closer on {closer} of {n} days, contradicts its "
                   "registered rule")
    return out


def h5e_record(text):
    """H5e's FINAL reading (the poster's parser) -> dict as written; None if not written; Unrecognised if the block or
    a line in it is written twice, or its figures are at odds with its verdict, count or minimum (Astra's follow-up,
    13 Nov 2026: nothing held it to its rule)."""
    who = "H5e's FINAL reading"
    if _one_block(text, BP.MARK_H5E_FINAL, who, H5E_LINES) is None:
        return None
    v = BP.h5e_final(text)
    _finite(who, v["mae"])
    problems = _h5e_contradictions(v)
    if problems:
        raise Unrecognised(f"{who}: " + "; ".join(problems) + " - the page will not guess.")
    return v


# H7's verdict block as record_verdict.block_h7 writes it: one line for each registered part.
H7_LINES = ((re.compile(r"^- \*\*H7a ", re.M), "H7a's verdict"), (re.compile(r"^- \*\*H7b ", re.M), "H7b's verdict"))


def h7_record(text):
    """H7's verdict (the poster's parser) with its companion readings; None if not read; Unrecognised if either is
    malformed or repeated, if a verdict is at odds with its figures, if the companion is missing, or if the
    companion's 'registered' figures or day counts are not the verdict's."""
    if _one_block(text, BP.MARK_H7, "H7's reading", H7_LINES) is None:
        return None
    v = BP.h7_reading(text)
    if not all(re.fullmatch(r"\d+\.\d{3}", v[k]) for k in ("uso", "gld", "gvz")) or not {v["a"], v["b"]} <= {
            "HOLDS", "FAILS"}:
        raise Unrecognised("H7's verdict holds a part not read or a figure not at three decimals - the page gives "
                           "every part and figure, so it will not guess.")
    _finite("H7's verdict", v["uso"], v["gld"], v["gvz"])
    # Astra's follow-up, 13 Nov 2026: the writer reads a part only on 10 days or more (record_verdict.h7_verdicts),
    # and reports one below that as not read; a verdict over fewer days is not the writer's.
    if min(int(v["uso_n"]), int(v["gld_n"]), int(v["n"])) < RV.H7_MIN_DAYS:
        raise Unrecognised(f"H7's verdict reads a part over {min(int(v['uso_n']), int(v['gld_n']), int(v['n']))} days, "
                           f"under the registered minimum of {RV.H7_MIN_DAYS} - the page will not guess.")
    sure_a = _all(*(_sure(v[k], lambda x: x <= RV.H7_BAR_A) for k in ("uso", "gld")))
    sure_b = _sure(v["gvz"], lambda x: x <= RV.H7_BAR_B)
    if not (_agrees(v["a"], sure_a) and _agrees(v["b"], sure_b)):
        raise Unrecognised(f"H7's verdict: H7a {v['a']} beside {v['uso']} and {v['gld']}, or H7b {v['b']} beside "
                           f"{v['gvz']}, contradicts its registered rule - the page will not guess.")
    who = "H7's companion readings"
    comp = _one_block(text, MARK_H7_COMPANION, who)
    if comp is None:
        raise Unrecognised("H7's verdict is recorded but not its companion readings: the page shows the "
                           "matched-strike figure only beside the registered one.")
    t = _flat(comp)
    m, e = _once(COMP_MATCHED, t, "the matched-strike reading", who), _once(COMP_EDGE, t, "the edge count", who)
    _finite(who, m[1], m[2])
    if (m[4], m[5], m[3], m[3]) != (v["uso"], v["gld"], v["uso_n"], v["gld_n"]):
        raise Unrecognised(f"H7's companion compares against {m[4]} and {m[5]} over {m[3]} days; the verdict says "
                           f"{v['uso']} and {v['gld']} over {v['uso_n']} and {v['gld_n']} - the page will not guess.")
    if not (int(e[2]) <= int(e[3]) == int(m[3]) and 0 < int(e[1]) <= 100):
        raise Unrecognised(f"H7's companion counts the edge on {e[2]} of {e[3]} days at +/-{e[1]}%, beside readings "
                           f"over {m[3]} days - the page will not guess.")
    return dict(v, m_uso=m[1], m_gld=m[2], m_n=m[3], edge=e[1], edge_k=e[2], edge_n=e[3])


# Readings at one snapshot minute against one index share the index's move: H5e's two estimates, H7's two replicas.
SAME_MINUTE = ((("H5e registered", "OVX"), ("H5e skip-only", "OVX")),
               (("H7 OPRA replica", "OVX"), ("H7 free-feed replica", "OVX")),
               (("H7 OPRA replica", "GVZ"), ("H7 free-feed replica", "GVZ")))
EPS = 1e-9          # float slack on top of the rounding allowance
# E - C = (E - I) + (I - C) bounds each mean absolute by the other two together (Astra's follow-up, 13 Nov 2026:
# only the first was held, so |E - I| 1.000 beside two zeros passed).
TRIANGLE = (("aec", "aei", "aic"), ("aei", "aec", "aic"), ("aic", "aec", "aei"))
ABS_NAME = {"aec": "|E - C|", "aei": "|E - I(T)|", "aic": "|I(T) - C|"}


def _timing_part(part):
    """One reading's head, signed means and mean absolutes, each printed once, checked against each other. The
    reader prints every figure to 0.001, so a sum of three printed figures can be off by 0.0015 and a figure beside
    another by 0.001; anything further is not the reader's arithmetic."""
    h, who = T_HEAD.match(part), f"the timing reading's part {part.splitlines()[0][:60]!r}"
    if not h:
        raise Unrecognised(f"{who} is not recognised.")
    s, a = _once(T_SIGNED, part, "its signed means", who), _once(T_ABS, part, "its mean absolutes", who)
    v = {"ec": s[1], "ei": s[2], "ic": s[3], "aec": a[1], "aei": a[2], "aic": a[3]}
    _finite(who, *v.values())
    x = {k: float(w) for k, w in v.items()}
    if abs(x["ec"] - (x["ei"] + x["ic"])) > 3 * 0.0005 + EPS:
        raise Unrecognised(f"{who}: E - C {v['ec']} does not add up to {v['ei']} + {v['ic']}.")
    if any(abs(x[k]) > x["a" + k] + 0.001 + EPS for k in ("ec", "ei", "ic")):
        raise Unrecognised(f"{who}: a signed mean larger than its mean absolute.")
    big = [k for k, o1, o2 in TRIANGLE if x[k] > x[o1] + x[o2] + 3 * 0.0005 + EPS]
    if big:
        raise Unrecognised(f"{who}: {ABS_NAME[big[0]]} {v[big[0]]} is larger than the other two together.")
    return (h[1], h[2]), (h[3], h[4]), v


def timing_record(text):
    """The timing measurement's one reading -> {first, last, files, n, covered, r: {(reading, index): parts}};
    None if not read; Unrecognised unless its one output block holds all six readings once each, every covered
    day measured, over real dates in order, with figures that agree with each other."""
    b = _one_block(text, MARK_TIMING, "the timing reading")
    if b is None:
        return None
    blocks = re.findall(r"\n```\n(.*?)\n```", b, re.S)
    if len(blocks) != 1:
        raise Unrecognised(f"the timing reading holds {len(blocks)} output blocks; the page reads exactly one.")
    out = blocks[0]
    days = _once(T_DAYS, out, "its index days", "the timing reading")
    try:
        first, last = date.fromisoformat(days[1]), date.fromisoformat(days[2])
    except ValueError:
        first = last = None
    if first is None or last < first or int(days[3]) < 1:
        raise Unrecognised(f"the timing reading's dates ({days[1]} to {days[2]}, {days[3]} files) are not a span of "
                           "real days in order.")
    r, counts = {}, set()
    for part in re.split(r"^(?=== )", out, flags=re.M)[1:]:
        key, count, v = _timing_part(part)
        if key in r:
            raise Unrecognised(f"the timing reading prints {key[0]} against {key[1]} twice.")
        r[key] = v
        counts.add(count)
    if sorted(r) != sorted(TIMING_KEYS) or len(counts) != 1:
        raise Unrecognised(f"the timing reading holds {len(r)} of the 6 readings over {len(counts)} day counts; the "
                           "page states six readings over one count.")
    (n, covered), = counts
    if not (n == covered and 1 <= int(n) <= int(days[3])):
        raise Unrecognised(f"the timing reading measured {n} of {covered} covered days over {days[3]} index files; "
                           "the page states every covered day measured.")
    for one, two in SAME_MINUTE:
        if (r[one]["ic"], r[one]["aic"]) != (r[two]["ic"], r[two]["aic"]):
            raise Unrecognised(f"the timing reading gives {one[1]} two moves after one snapshot minute ({one[0]} and "
                               f"{two[0]}).")
    return {"first": days[1], "last": days[2], "files": days[3], "n": n, "covered": covered, "r": r}


def _read(root, key):
    p = Path(root) / FILES[key]
    if not p.is_file():
        raise Unrecognised(f"{FILES[key]} is missing")
    return p.read_text(encoding="utf-8")


def record(root=ROOT):
    """The four records from a checkout. Raises Unrecognised if any is missing or malformed: the page's results
    wait for every record, and a missing one is never read as nothing to show."""
    rec = {"h3": h3_record(_read(root, "h3")), "h5e": h5e_record(_read(root, "h5e")),
           "h7": h7_record(_read(root, "h7")), "timing": timing_record(_read(root, "timing"))}
    missing = [LABEL[k] for k, v in rec.items() if v is None]
    if missing:
        raise Unrecognised("not recorded yet: " + ", ".join(missing))
    return rec


# ---------------- the passages ----------------
def _m(v):
    """A measured figure in the page's number style, exactly as recorded."""
    return f'<span class="m">{html.escape(v, quote=False)}</span>'


def _day(iso, fmt):
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime(fmt)}"


BAR_A, BAR_B = f"{RV.H7_BAR_A:.2f}", f"{RV.H7_BAR_B:.2f}"      # "0.25", "0.30": the registered bars, as written


def headline(rec):
    h3 = rec["h3"]
    first, second = BP.headline({"verdict": h3["a"]}, rec["h7"])
    return (f"{html.escape(first, quote=False)} {html.escape(second, quote=False)} On the registered test, the "
            f"estimate built from free quotes missed Cboe's indices by a mean absolute {_m(h3['mae'])} volatility "
            f"points over {_m(h3['n'])} readings on {_m(h3['days'])} days, against a limit of {HS.H3A_BAR} written "
            f"down before the data.")


def ledger(rec):
    """The ledger's results, as the page's script reads them: RESULTS[id] = {st: [state, label], ev: ...}."""
    h3, h5, h7, tm = rec["h3"], rec["h5e"], rec["h7"], rec["timing"]
    if all(h3[k] == "HOLDS" for k in "abc"):
        h3_label = "Tested, holds"
    else:
        h3_label = "Tested; " + ", ".join(f"H3{k} {h3[k].lower()}" for k in "abc")
    bc = (f"H3b and H3c {h3['b'].lower()[:-1]}" if h3["b"] == h3["c"]
          else f"H3b {h3['b'].lower()}, H3c {h3['c'].lower()}")
    over = "".join(f", and {NAME[f]} ({f}) reads {h3['per'][f][0]}" for f in h3["over"])
    h7_days = h7["uso_n"] if h7["uso_n"] == h7["gld_n"] else f"{h7['uso_n']} and {h7['gld_n']}"
    o, g = tm["r"][("H7 OPRA replica", "OVX")], tm["r"][("H7 OPRA replica", "GVZ")]
    res = {
        "H3": {"st": ["tested", h3_label],
               "ev": [f"{h3['mae']} mean absolute gap over {h3['n']} readings on {h3['days']} days, against a "
                      f"{HS.H3A_BAR} limit: the reading of record, to 11 Nov 2026",
                      f"{bc}; H3a holds for {h3['bh_a']} of {len(FUNDS)} funds after Benjamini-Hochberg{over}"]},
        "H5": {"st": ["tested", f"Partly tested; H5e {h5['verdict'].lower()}"],
               "ev": f"H5e {h5['verdict']} at its final reading: {h5['mae']} against a {RV.H5E_BAR} bar; closer than "
                     f"the registered estimate on {h5['closer']} of {h5['n']} days"},
        "H7": {"st": ["tested", f"Tested; H7a {h7['a'].lower()}, H7b {h7['b'].lower()}"],
               "ev": [f"H7a {h7['a']}: the free and full-market rebuilds differ by {h7['uso']} on oil and "
                      f"{h7['gld']} on gold, over {h7_days} days (bar {BAR_A} each)",
                      f"H7b {h7['b'].lower()}: gold's free rebuild sits {h7['gvz']} from GVZ's close (bar {BAR_B}). "
                      f"On the strikes both feeds carry, oil's rebuilds differ by {h7['m_uso']}: a companion reading, "
                      f"not the test"]},
        "timing": {"st": ["tested", "Read once, descriptive"],
                   "ev": [f"At the snapshot minute, Cboe's method on the full market's quotes sits {o['aei']} points "
                          f"from OVX and {g['aei']} from GVZ",
                          f"the indices then move a mean absolute {o['aic']} (OVX) and {g['aic']} (GVZ) before the "
                          f"close; {tm['n']} days, {_day(tm['first'], '%b')} to {_day(tm['last'], '%b')} "
                          f"{tm['last'][:4]}"]},
    }
    body = json.dumps(res, ensure_ascii=False, separators=(", ", ": "))
    if "*/" in body or "</script" in body.lower():
        raise Unrecognised("the ledger's text would end its marker comment or the page's script")
    return f"const RESULTS = {body};"


def _narrated(h7):
    """The outcome the H7 passage's words describe: H7a failing on oil alone (oil over its bar, gold under it) and
    H7b holding - the outcome recorded on 13 Nov 2026."""
    return ((h7["a"], h7["b"]) == ("FAILS", "HOLDS") and _sure(h7["uso"], lambda x: x <= RV.H7_BAR_A) == "no"
            and _sure(h7["gld"], lambda x: x <= RV.H7_BAR_A) == "yes"
            and _sure(h7["gvz"], lambda x: x <= RV.H7_BAR_B) == "yes")


def h7note(rec):
    """Two blocks for the OPRA section, beside (never replacing) the in-sample paragraph above them. Its words fit
    one outcome; any other is refused, never narrated in them (Astra, 13 Nov 2026: it said "gold holds, oil fails"
    whatever the record said)."""
    h7, tm = rec["h7"], rec["timing"]
    if not _narrated(h7):
        raise Unrecognised(f"the H7 passage narrates H7a failing on oil alone and H7b holding; the record gives H7a "
                           f"{h7['a']} ({h7['uso']} and {h7['gld']}) and H7b {h7['b']} ({h7['gvz']}). Rewrite the "
                           "passage for that outcome before the page shows it.")
    r = tm["r"]
    o, g = r[("H7 OPRA replica", "OVX")], r[("H7 OPRA replica", "GVZ")]
    fo, fg = r[("H7 free-feed replica", "OVX")], r[("H7 free-feed replica", "GVZ")]
    s = r[("H5e skip-only", "OVX")]
    span = f"{_day(tm['first'], '%B')} to {_day(tm['last'], '%B')} {tm['last'][:4]}"
    h7_url, t_url = REPO + FILES["h7"], REPO + FILES["timing"]
    return (
        '\n    <div class="prose" style="margin-top:28px">\n'
        f'      <p><b>Tested out of sample, H7 splits the two funds.</b> Added 13 November 2026, beside the paragraph '
        f'above, which describes ten days examined before H7 was registered. H7 asked the same question of the days '
        f'after its registration, 9 October to 11 November, and was read once in wording fixed in advance. Gold '
        f'holds: the free and full-market rebuilds differ by {_m(h7["gld"])} points over {_m(h7["gld_n"])} days, '
        f'and the free rebuild sits {_m(h7["gvz"])} from GVZ\'s close (bars {BAR_A} and {BAR_B}). Oil does not: the '
        f'two rebuilds differ by {_m(h7["uso"])} over {_m(h7["uso_n"])} days, over the {BAR_A} bar, so H7a fails, '
        f'and for oil the heading above did not survive its registered test. The registered reading uses every strike '
        f'OPRA lists; the free file stops at ±{h7["edge"]}% of spot, and Cboe\'s rule walked past that edge on '
        f'{_m(h7["edge_k"])} of {_m(h7["edge_n"])} days for both funds. On the strikes both feeds carry, the '
        f'comparison the paragraph above made, the rebuilds differ by {_m(h7["m_uso"])} for oil and '
        f'{_m(h7["m_gld"])} for gold. '
        f'That comparison is a companion reading, added on 17 October before any reading as a description beside '
        f'the test, never in its place.</p>\n'
        f'      <div class="src">Data provided by Databento (OPRA consolidated NBBO). Index closes: Cboe Global '
        f'Markets. Derived aggregates only: no OPRA quote or price is reproduced here, and none is stored in this '
        f'repository. <a href="{h7_url}">hypotheses/H7</a>, Result.</div>\n'
        '    </div>\n'
        '    <div class="prose" style="margin-top:28px">\n'
        f'      <p><b>Then the index moves.</b> A descriptive measurement, registered on 6 November before either '
        f'verdict and read once on 13 November 2026, split each gap at the snapshot minute. On the {_m(tm["n"])} '
        f'days from {span} that the one-second index record covers, Cboe\'s method on OPRA\'s quotes sat a mean '
        f'absolute {_m(o["aei"])} points from OVX and {_m(g["aei"])} from GVZ at the snapshot minute; the free '
        f'feed\'s rebuild sat {_m(fo["aei"])} from OVX and {_m(fg["aei"])} from GVZ. Between the snapshot and the '
        f'close, OVX then moved a mean absolute {_m(o["aic"])} points and GVZ {_m(g["aic"])}; the index at the '
        # I(T) - C, as the reader prints it: the snapshot less the close, never the move to the close (whose sign
        # is the opposite). Astra, 13 Nov 2026, caught the first wording ("averaging") reversing it.
        f'snapshot minus its close averaged {_m(o["ic"])} for OVX and {_m(g["ic"])} for GVZ. H5e\'s skip-only '
        f'estimate was already {_m(s["aei"])} points from OVX at its snapshot minute, and OVX then moved a mean '
        f'absolute {_m(s["aic"])} before the close. The verdicts stand as registered: this describes their gaps and '
        f'changes neither.</p>\n'
        f'      <div class="src">Data provided by Databento (one-second index values, DBIX.CORE; OPRA consolidated '
        f'NBBO). Index closes: Cboe Global Markets. Derived aggregates only: no index value is shown here or stored '
        f'in this repository. <a href="{t_url}">hypotheses/timing</a>; <a href="https://osf.io/4mcgf">'
        f'osf.io/4mcgf</a>.</div>\n'
        '    </div>\n    ')


def render(rec):
    return {"headline": headline(rec), "h7note": h7note(rec), "ledger": ledger(rec)}


# ---------------- the page ----------------
def _span(page, name):
    """Where a passage sits: between exactly one start and one end marker, in that order."""
    a, b = MARKERS[name]
    na, nb = page.count(a), page.count(b)
    if (na, nb) != (1, 1):
        raise Unrecognised(f"{name}: the page has {na} start and {nb} end markers; it needs one of each")
    s, e = page.index(a) + len(a), page.index(b)
    if e < s:
        raise Unrecognised(f"{name}: its end marker comes before its start")
    return s, e


def apply(page, passages):
    """The page with each passage written between its markers; refuses a page whose markers are not one pair each."""
    for name in MARKERS:
        s, e = _span(page, name)
        page = page[:s] + passages[name] + page[e:]
    return page


def check(page, root=ROOT, rec=None):
    """Problems, as sentences: each passage on the page against what the records give. Empty only when every
    record is there and every passage is exactly its rendering. Never writes."""
    try:
        want = render(rec if rec is not None else record(root))
    except Unrecognised as e:
        return [f"the record: {e}"]
    out = []
    for name in MARKERS:
        try:
            s, e = _span(page, name)
        except Unrecognised as x:
            out.append(str(x))
            continue
        got, w = page[s:e], want[name]
        if got != w:
            i = next((k for k in range(min(len(got), len(w))) if got[k] != w[k]), min(len(got), len(w)))
            out.append(f"{name}: the page has {got[max(0, i - 40):i + 40]!r} where the record gives "
                       f"{w[max(0, i - 40):i + 40]!r}")
    return out


# ---------------- where the passages sit ----------------
# Astra, 13 Nov 2026: check() compares the bytes between the markers, and that alone passed a passage moved into an
# element never shown, the in-sample paragraph removed from above the H7 passage, ledger rows reading each other's
# results, and a contradicting claim written outside the markers. placement() holds each of those to the page as it
# was built on 13 Nov 2026; a deliberate change to that layout changes WHERE, CONTEXT, LEDGER_SHA256 or ACCEPTED_HIDES
# with it. Astra's follow-up the same day: the ledger was held by lines it contains (an early return kept every one),
# claims were read in the source, never as a reader meets them, and nothing looked at the page's styles or at the
# in-sample paragraph's own block. Each is now held as well; how a browser finally renders the page is still the look
# in a browser that CLAUDE.md asks for after every page change.
VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_TOP = (("html", (("lang", "en"),)), ("body", ()))
WHERE = {"headline": _TOP + (("main", (("class", "paper"),)), ("section", (("class", "masthead"),)), ("div", ()),
                             ("p", (("class", "dek"),))),
         "h7note": _TOP + (("main", (("class", "paper"),)), ("section", (("class", "section"), ("id", "opra")))),
         "ledger": _TOP + (("script", ()),)}           # the elements around each passage, attributes and all
# The sentence the H7 passage answers, as a reader meets it, and the elements around it, attributes and all.
INSAMPLE_SAID = "Rebuilt with Cboe's own rules, the free feed is not the problem."
CONTEXT = WHERE["h7note"] + (("div", (("class", "prose"), ("style", "margin-top:28px"))), ("p", ()), ("b", ()))
LEDGER_FN, LEDGER_CALL, ROWS = "function ledger(h) {", "\n  ledger(null);", "const rows = ["
# The real page's ledger function, from its first line to its call, the generated passage cut out and its markers
# kept, pinned 13 Nov 2026 after the ledger was looked at in a browser at 1280 and 375 px. Any change to the function
# (its columns, its rows, an early return) changes it: look at the ledger again at both widths, then pin the new one.
LEDGER_SHA256 = "1ef3b4e8d25f18351a5c83d3ab62a7596981a5ee6258b1ca92e23914dfc3a663"
BIND = {"H3": "H3", "H5": "H5", "H7": "H7", "T": "timing"}   # each row's id -> the results it reads
ROW = re.compile(r'\["(\w+)", "(?:[^"\\]|\\.)*", "[^"]*", RESULTS\.(\w+)\.st, \[?RESULTS\.(\w+)\.ev\b')
_CLAIM = r"\bH(?:3[abc]?|5e|7[abc]?)\b%s{0,80}?\b(?:holds?|held|fails?|failed|pass(?:es|ed)?)\b"
CLAIM = re.compile(_CLAIM % r"[^.\n]", re.I)       # in the source as written: scripts, comments and attributes too
CLAIM_SAID = re.compile(_CLAIM % r"[^.]", re.I)    # in the words as a reader meets them, across lines and tags
# The stylesheet's hiding rules on 13 Nov 2026, each read; none hides a results passage. Any other rule that hides
# (display none, visibility hidden or collapse, content-visibility hidden, opacity 0) is a problem until someone has
# looked at the page and added it here with its reason.
ACCEPTED_HIDES = {
    "[hidden]": "lets the hidden attribute win over any display rule",
    ".rail-cells::-webkit-scrollbar": "the status rail's scrollbar",
    ".rail-brand span": "the rail's brand words, on phones",
    ".ledger thead": "the ledger's head row, on phones, where each row reads as a card",
}
HIDES = re.compile(r"\bdisplay\s*:\s*none\b|\bvisibility\s*:\s*(?:hidden|collapse)\b"
                   r"|\bcontent-visibility\s*:\s*hidden\b"
                   r"|\bopacity\s*:\s*(?:0+(?:\.0*)?|\.0+)%?\s*(?:!important\s*)?(?:;|$)", re.I)
CSS_RULE = re.compile(r"([^{};]+)\{([^{}]*)\}")
# The stylesheets the page may link: its own (under any cache key) and its fonts. Another would bring rules no check
# reads, as a style element would.
SHEETS = re.compile(r"tools/volrec\.css(?:\?v=[\w.-]+)?|https://fonts\.googleapis\.com/css2\?[^\s\"'<>]*")


class _Where(HTMLParser):
    """The open elements, with their attributes, around each comment, each run of text and each script of a page,
    numbered in the order a reader meets them; where each element starts, and how deep; how many style elements."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.open, self.comments, self.scripts, self._script = [], [], [], None
        self.k, self.starts, self.said, self.styles, self.sheets = 0, [], [], 0, []

    def handle_starttag(self, tag, attrs):
        self.k += 1
        self.styles += tag == "style"
        if tag == "link" and "stylesheet" in (dict(attrs).get("rel") or "").lower().split():
            self.sheets.append(dict(attrs).get("href") or "")
        if tag not in VOID:
            self.open.append((tag, tuple(attrs)))
            self.starts.append((self.k, len(self.open)))
            if tag == "script":
                self._script = []

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append((tuple(self.open), "".join(self._script)))
            self._script = None
        for i in range(len(self.open) - 1, -1, -1):
            if self.open[i][0] == tag:
                del self.open[i:]
                break

    def handle_data(self, data):
        self.k += 1
        if self._script is not None:
            self._script.append(data)
        else:
            self.said.append((data, tuple(self.open), self.k))

    def handle_comment(self, data):
        self.k += 1
        self.comments.append((data.strip(), tuple(self.open), self.k))


def _parsed(page):
    w = _Where()
    w.feed(page)
    w.close()
    return w


def _chain(c):
    return " > ".join(t + "".join(f"[{k}]" if v is None else f"[{k}={v}]" for k, v in a) for t, a in c) or "the top"


def _fingerprint(s):
    """The ledger function's fingerprint: sha256 of its text from its first line to its call, the generated passage
    cut out and its markers kept. None unless the script holds one function and one pair of markers, in order."""
    a, b = MARKERS["ledger"]
    if (s.count(LEDGER_FN), s.count(a), s.count(b)) != (1, 1, 1):
        return None
    f, i, j = s.index(LEDGER_FN), s.index(a), s.index(b)
    end = s.find(LEDGER_CALL, j)
    if not f < i < j < end:
        return None
    return hashlib.sha256((s[f:i + len(a)] + s[j:end + len(LEDGER_CALL)]).encode("utf-8")).hexdigest()


def _ledger_scripts(w):
    """The page's scripts that hold the ledger's markers: (open elements, text) each."""
    return [(c, s) for c, s in w.scripts if any(m in s for m in MARKERS["ledger"])]


def ledger_fingerprint(page):
    """The fingerprint of the page's ledger function; None unless one script holds it as built."""
    held = _ledger_scripts(_parsed(page))
    return _fingerprint(held[0][1]) if len(held) == 1 else None


def _ledger_reads(s, pin):
    """The ledger function is the one pinned, and reads RESULTS once per row, each row its own id's. Astra's
    follow-up, 13 Nov 2026: the lines it was held by survived an early return and a row overwritten after the rows,
    so the whole function is pinned; its rows and reads are still named when they go wrong."""
    a, b = MARKERS["ledger"]
    if (s.count(LEDGER_FN), s.count(a), s.count(b)) != (1, 1, 1):
        return [f"ledger: its script holds {s.count(LEDGER_FN)} ledger functions and {s.count(a)} start and "
                f"{s.count(b)} end markers; one of each"]
    f, i, j = s.index(LEDGER_FN), s.index(a), s.index(b)
    end, rows = s.find(LEDGER_CALL, f), s.find(ROWS, j)
    if not (f < i < j < rows < end) or s[s.rfind("\n", 0, i) + 1:i].strip() or s[j + len(b):j + len(b) + 1] != "\n":
        return ["ledger: its passage is not a line of its own inside the ledger function, above its rows"]
    rest = s[:i] + s[j + len(b):]
    body = s[f:i] + s[j + len(b):end]
    fp, out = _fingerprint(s), []
    if fp != pin:
        out.append(f"ledger: the ledger function's fingerprint is {(fp or 'none')[:12]}..., not the pinned "
                   f"{pin[:12]}...: it changed. Look at the ledger in a browser at 1280 and 375 px, then pin the new "
                   "one (LEDGER_SHA256 in tools/site_results.py)")
    found = sorted(ROW.findall(body))
    if found != sorted((k, v, v) for k, v in BIND.items()) or rest.count("RESULTS") != 2 * len(BIND):
        out.append(f"ledger: its rows read the results as {found} with {rest.count('RESULTS')} reads in all; each "
                   f"of {sorted(BIND)} must read its own, and nothing else may")
    return out


def _beside(w):
    """The H7 passage answers the in-sample paragraph: its sentence stands right above the passage, in the OPRA
    section, in the block it was built in (attributes and all: Astra's follow-up, 13 Nov 2026, hid that block), with
    no other block of the section between them."""
    start = [k for d, c, k in w.comments if d == MARKERS["h7note"][0][4:-3].strip()]
    said = [(c, k) for d, c, k in w.said if d.strip() == INSAMPLE_SAID]
    if len(start) == 1 and len(said) == 1 and said[0][0] == CONTEXT and said[0][1] < start[0] and not any(
            said[0][1] < k < start[0] and depth <= len(WHERE["h7note"]) + 1 for k, depth in w.starts):
        return []
    return ["h7note: the in-sample paragraph it answers (\"Rebuilt with Cboe's own rules ...\") is not right above it, "
            "in its own block of the OPRA section, as built"]


def _words(w, sep):
    """The page's words as a reader meets them, outside the generated passages and the scripts: entities decoded,
    runs of text joined by sep (a tag can sit inside a word or between two), whitespace collapsed."""
    cut = []
    for name in ("headline", "h7note"):
        ka, kb = ([k for d, c, k in w.comments if d == m[4:-3].strip()] for m in MARKERS[name])
        if len(ka) == len(kb) == 1 and ka[0] < kb[0]:
            cut.append((ka[0], kb[0]))    # otherwise the marker placement reports it
    return re.sub(r"\s+", " ", sep.join(d for d, c, k in w.said if not any(x < k < y for x, y in cut)))


def _claims_elsewhere(page, w):
    """H3, H5e and H7's verdicts come from the records: outside the generated passages the page states none, in its
    source or in its words as read (Astra's follow-up, 13 Nov 2026: "H7a" and "holds" on two lines went unseen)."""
    rest = page
    for name in MARKERS:
        try:
            s, e = _span(rest, name)
        except Unrecognised:
            continue                      # check() and the marker placement report it
        rest = rest[:s] + rest[e:]
    said = [m[0] for m in CLAIM.finditer(rest)]
    said += [m[0] for sep in ("", " ") for m in CLAIM_SAID.finditer(_words(w, sep))]
    return [f"outside the generated passages the page says {c!r}: H3, H5e and H7's verdicts are stated only "
            "where they are generated from the records" for c in dict.fromkeys(said)]


def css_hides(css):
    """Problems, as sentences: the stylesheet's rules that hide what they select, other than the accepted ones, and
    any stylesheet it imports (whose rules this never reads)."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    out = ["tools/volrec.css imports another stylesheet (@import), whose rules no check reads"] if re.search(
        r"@import\b", css, re.I) else []
    for sel, body in CSS_RULE.findall(css):
        sel, hit = re.sub(r"\s+", " ", sel).strip(), HIDES.search(body)
        if hit and sel not in ACCEPTED_HIDES:
            out.append(f"tools/volrec.css hides {sel!r} ({hit[0].strip(' ;')}): only the accepted hiding rules may "
                       "hide anything (ACCEPTED_HIDES in tools/site_results.py); look at the page before adding one")
    return out


def placement(page, css, pin=None):
    """Problems, as sentences: where the passages sit, what stands beside them, how the ledger's script reads them,
    any verdict of theirs stated elsewhere on the page, and a style element or stylesheet rule that would hide them.
    Empty only when all is as the page was built. css is tools/volrec.css's text; pin the ledger function's
    fingerprint (LEDGER_SHA256 unless given)."""
    w = _parsed(page)
    out = []
    for name in ("headline", "h7note"):
        for mark in MARKERS[name]:
            got = [c for d, c, k in w.comments if d == mark[4:-3].strip()]
            if len(got) != 1:
                out.append(f"{name}: the page holds {len(got)} live {mark} comments; it needs one")
            elif got[0] != WHERE[name]:
                out.append(f"{name}: {mark} sits in {_chain(got[0])}, not in {_chain(WHERE[name])}")
    held = _ledger_scripts(w)
    if len(held) != 1:
        out.append(f"ledger: {len(held)} scripts hold its markers; it needs one")
    else:
        if held[0][0] != WHERE["ledger"]:
            out.append(f"ledger: its script sits in {_chain(held[0][0])}, not in {_chain(WHERE['ledger'])}")
        out += _ledger_reads(held[0][1], LEDGER_SHA256 if pin is None else pin)
    if w.styles:
        out.append(f"the page holds {w.styles} style element(s): the site's styles live in tools/volrec.css, where no "
                   "rule may hide a passage")
    other = [h for h in w.sheets if not SHEETS.fullmatch(h)]
    if other:
        out.append(f"the page links the stylesheet(s) {other}: only tools/volrec.css and its fonts may style it, so "
                   "that no rule this check does not read can hide a passage")
    return out + _beside(w) + _claims_elsewhere(page, w) + css_hides(css)


def main(argv=None, root=ROOT, pin=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="compare only; write nothing; exit 1 on any difference")
    a = ap.parse_args(argv)
    f, sheet = Path(root) / "index.html", Path(root) / "tools/volrec.css"
    page = f.read_bytes().decode("utf-8")        # bytes: line endings stay exactly as they are
    misplaced = (placement(page, sheet.read_text(encoding="utf-8"), pin) if sheet.is_file() else
                 ["tools/volrec.css is missing: without the page's stylesheet nothing shows its passages unhidden"])
    if a.check:
        problems = check(page, root) + misplaced
        for p in problems:
            print(f"  MISMATCH  {p}")
        print("RESULT: " + (f"MISMATCH ({len(problems)})" if problems else
                            "VERIFIED - every results passage on the page is what the hypothesis files record, "
                            "where it belongs"))
        return 1 if problems else 0
    if misplaced:
        print("REFUSED: the passages would not show as built - " + "; ".join(misplaced))
        return 1
    try:
        new = apply(page, render(record(root)))
    except Unrecognised as e:
        print(f"REFUSED: {e}")
        return 1
    if new == page:
        print("index.html: the results passages are already current")
    else:
        f.write_bytes(new.encode("utf-8"))
        print("index.html: the results passages written from the hypothesis files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
