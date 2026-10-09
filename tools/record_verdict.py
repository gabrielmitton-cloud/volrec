#!/usr/bin/env python3
"""Write a registered verdict into the record, in fixed wording, when it comes due.

WHY THIS EXISTS (24 Sep 2026)
-----------------------------
Three verdicts fall due while nobody may be at a keyboard: H5f at its five-OPRA-day
minimum (~25 Sep), H5e's first verdict at ten counted days (~7 Oct) and H5e's final
reading over 23 Sep - 11 Nov (~12 Nov). The private volrec-licensed repository's
workflow runs this every weekday evening. Gabriel chose FIXED wording over a model
writing prose: the frozen scripts compute, this copies their numbers into a template,
and nothing here exercises judgement.

WHAT IT MAY DO, AND NOTHING ELSE
--------------------------------
- run tools/h5f_pooled.py (frozen 23 Sep, before days 4-5; the pressure test pins its
  hash) and modelfree.py --wide, both with FRED_KEY=use-cache;
- append a verdict block to the END of the H5 file's "## Result" section, append a
  note to its **Status:** line, and replace that hypothesis's row in HANDOFF's current
  state table;
- skip a verdict whose block already exists (a Mac task or a session may have written
  it first), and refuse any verdict below its registered minimum.
It never touches a threshold, the registration text, the adjustment log or the site.

USAGE
-----
  python3 tools/record_verdict.py --dry-run            # what is due; write nothing
  python3 tools/record_verdict.py --preview            # render every block even if not due; write nothing
  python3 tools/record_verdict.py --summary out.txt    # write what is due; summary for the issue
"""
import argparse
import os
import re
import statistics as st
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
H5 = ROOT / "hypotheses" / "2026-09-19-h5-wing-quote-quality.md"
HANDOFF = ROOT / "HANDOFF.md"
DB_CREDIT = "*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*"

H5F_MIN_DAYS = 5
H5E_START, H5E_END = "2026-09-23", "2026-11-11"
H5E_MIN_DAYS, H5E_BAR = 10, 0.5
H5E_FIRST_DUE, H5E_FINAL_DUE = "2026-10-07", "2026-11-12"
MARK_H5F = "**H5f, read "
MARK_H5E_FIRST = "**H5e, first verdict"
MARK_H5E_FINAL = "**H5e, FINAL reading"
# H7 (registered 8 Oct 2026): read once over 9 Oct - 11 Nov, from tools/h7_reader.py.
H7 = ROOT / "hypotheses" / "2026-10-08-h7-free-feed-cboe-replica.md"
H7_DUE, H7_MIN_DAYS, H7_BAR_A, H7_BAR_B = "2026-11-12", 10, 0.25, 0.30
MARK_H7 = "**H7, reading over 9 Oct - 11 Nov 2026"
# The final readings (H5e FINAL, H7) are written once and never rewritten, so they wait until every
# day in their window has its data (9 Oct 2026): Databento serves day D's OPRA about a day later and
# Cboe's closes can lag a day or two, while this workflow also runs at 03:05 UTC on 12 Nov itself.
# From COMPLETE_BY they are written with whatever is in, and the missing days are named in the block.
COMPLETE_BY = "2026-11-19"


def run(args):
    env = dict(os.environ, FRED_KEY="use-cache")
    p = subprocess.run([sys.executable] + args, cwd=ROOT, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed ({p.returncode}):\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p.stdout


# ---------------- parsers (pure; the pressure test feeds them known text) ----------------
def parse_h5f(out):
    """tools/h5f_pooled.py's output -> dict. Raises if a line it needs is missing."""
    g = lambda pat: re.search(pat, out, re.M)                                  # noqa: E731
    days = g(r"^days with OPRA data: (\d+) (\[.*\])")
    a = g(r"^H5f-a\s+pooled median ([\d.]+) of the OPRA spread \(bar 0\.5\) -> (HOLDS|FAILS)")
    a2 = g(r"both feeds bid, n=(\d+), median ([\d.]+)")
    wc = g(r"^wing contracts: (\d+) with a spread; (\d+) wide rows unmatched")
    b = g(r"^H5f-b\s+free no-bid -> OPRA no-bid (\d+) of (\d+) = ([\d.]+)% \(bar 80%\) -> (HOLDS|FAILS); OPRA-only no-bid (\d+)")
    c = g(r"^H5f-c\s+OPRA inflation positive on every zero-bid day: (True|False); median per-day gap ([\d.]+)% \(i\); "
          r"median OPRA ([+-][\d.]+) vs median free ([+-][\d.]+) = ([\d.]+)% \(ii\); bar 25%")
    cv = g(r"-> \(i\) (HOLDS|FAILS), \(ii\) (HOLDS|FAILS)")
    stale = g(r"^(Stated beside any verdict:.*)$")
    if not all((days, a, wc, b)):
        raise ValueError("h5f_pooled output not recognised")
    perday = re.findall(r"^\s+(\d{4}-\d{2}-\d{2}) (\w+): inflation free ([+-][\d.]+)\s+OPRA ([+-][\d.]+)\s+gap ([\d.]+)%", out, re.M)
    return {
        "days": int(days.group(1)), "day_list": days.group(2),
        "a": float(a.group(1)), "a_v": a.group(2),
        "a2_n": int(a2.group(1)) if a2 else None, "a2": float(a2.group(2)) if a2 else None,
        "n": int(wc.group(1)), "unmatched": int(wc.group(2)),
        "b_x": int(b.group(1)), "b_y": int(b.group(2)), "b_p": float(b.group(3)), "b_v": b.group(4), "b_o": int(b.group(5)),
        "c": ({"pos": c.group(1) == "True", "i": float(c.group(2)), "mo": c.group(3), "mf": c.group(4),
               "ii": float(c.group(5)), "vi": cv.group(1), "vii": cv.group(2)} if c and cv else None),
        "perday": perday,
        "stale": stale.group(1) if stale else "",
    }


def parse_h5e(out):
    """modelfree.py --wide's H5e block -> (rows, risk-free line). A row is
    (date, ovx, reg_gap, skip_gap, counted) for dates with an OVX close."""
    i = out.find("-- H5e:")
    if i < 0:
        raise ValueError("no H5e block in modelfree output")
    rows = []
    for line in out[i:].splitlines()[2:]:
        m = re.match(r"\s+(\d{4}-\d{2}-\d{2})\s+([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)\s+([\d.]+)\s+([+-][\d.]+)\s+(yes|no)", line)
        if m:
            rows.append((m.group(1), float(m.group(2)), float(m.group(4)), float(m.group(6)), m.group(7) == "yes"))
        elif not re.match(r"\s+\d{4}-\d{2}-\d{2}", line):
            break
    rf = re.search(r"risk-free \(DGS1MO\): ([\d.]+)%", out)
    na = re.findall(r"^\s+(\d{4}-\d{2}-\d{2})\s+n/a", out[i:], re.M)
    return rows, (rf.group(1) if rf else "?"), na


def dropped_days(out):
    """Days modelfree prints as dropped (recorded after the close; panel_health.AFTER_CLOSE_DAYS)."""
    return re.findall(r"^\s+(\d{4}-\d{2}-\d{2})\s+dropped - ", out, re.M)


def h5e_score(rows, first=H5E_START, last=None):
    judged = [r for r in rows if r[4] and r[0] >= first and (last is None or r[0] <= last)]
    if not judged:
        return None
    n = len(judged)
    mae = sum(abs(r[3]) for r in judged) / n
    closer = sum(abs(r[3]) < abs(r[2]) for r in judged)
    under, majority = mae < H5E_BAR, closer > n / 2
    return {"n": n, "mae": mae, "closer": closer, "under": under, "majority": majority,
            "holds": under and majority, "days": judged,
            "near": round(abs(mae - H5E_BAR), 6) <= 0.05 or abs(closer - n / 2) <= 1}


# Rounding budget for the cross-check (7 Oct 2026). The parser re-scores from the per-day gaps
# modelfree PRINTS at 2 decimals (each off by <= 0.005, so their mean is too), and modelfree's
# own mean is printed at 2 decimals (<= 0.005 more): two honest readings can differ by 0.010.
# The first limit, 0.006, was tighter than that and refused the real first verdict on 7 Oct
# (parser 0.894 from rounded gaps, modelfree 0.90 from full precision).
MAE_ROUNDING = 0.0105


def crosscheck(out, sc):
    """None when modelfree's printed tally agrees with this parser's score; else the reason.
    On agreement the written mean becomes modelfree's own (full-precision) figure."""
    m = re.search(r"mean \|gap\| ([\d.]+) against 0\.5 .*closer than registered on (\d+) of (\d+) days", out)
    if not m:
        return "modelfree printed no H5e tally"
    mf = float(m.group(1))
    if abs(mf - sc["mae"]) > MAE_ROUNDING or int(m.group(2)) != sc["closer"] or int(m.group(3)) != sc["n"]:
        return m.group(0)
    if (mf < H5E_BAR) != sc["under"]:
        return f"{m.group(0)} - rounding straddles the bar; read it by hand"
    sc["mae"] = mf
    sc["near"] = round(abs(mf - H5E_BAR), 6) <= 0.05 or abs(sc["closer"] - sc["n"] / 2) <= 1
    return None


# ---------------- the fixed wording ----------------
def block_h5f(v, today):
    a_on = round(abs(v["a"] - 0.5), 6) <= 0.02
    lines = [f"{MARK_H5F}{today:%-d %B %Y} at its five-day minimum** - written by the cloud workflow "
             f"(`tools/record_verdict.py`) from `tools/h5f_pooled.py`, frozen 23 Sep before days 4-5 "
             f"existed; numbers copied from its output, wording fixed in advance.", ""]
    s = (f"- **H5f-a {v['a_v']}:** pooled median {v['a']:.3f} of the OPRA spread over {v['n']} wing "
         f"contracts (bar 0.5).")
    if v["a2"] is not None:
        s += f" Descriptive: {v['a2']:.3f} on the {v['a2_n']} contracts both feeds bid."
    if a_on:
        s += (" **It sits ON the bar:** the result turns on TSLA's one-tick markets, where a one-cent "
              "difference is a whole spread (on 3 and on 4 days it was exactly 0.500).")
    lines.append(s)
    lines.append(f"- **H5f-b {v['b_v']}:** where the free feed shows no bid, OPRA shows none on {v['b_x']} "
                 f"of {v['b_y']} matched wing contracts ({v['b_p']:.1f}%; bar 80%). OPRA-only no-bid: {v['b_o']}.")
    c = v["c"]
    if c:
        per = "; ".join(f"{d} {s_} free {f} / OPRA {o}" for d, s_, f, o, _ in v["perday"])
        verdict = c["vi"] if c["vi"] == c["vii"] else "UNSETTLED"
        s = (f"- **H5f-c {verdict}:** OPRA's inflation is positive on every zero-bid day: {c['pos']}; "
             f"median per-day gap {c['i']:.1f}% (reading i), medians compared {c['ii']:.1f}% (reading ii); "
             f"bar 25%. Per day: {per}.")
        if c["vi"] != c["vii"]:
            s += " **The two readings disagree: Gabriel decides; the workflow does not choose.**"
        lines.append(s)
    else:
        lines.append("- **H5f-c:** no underlying-day with free-feed zero bids in its wings; not scored.")
    lines.append(f"- {v['stale']}")
    lines.append(f"- Days: {v['day_list']}. {v['unmatched']} wide rows unmatched, excluded by the rule.")
    lines += ["", DB_CREDIT]
    return "\n".join(lines)


def block_h5e(sc, rf, na, today, final, first_verdict=None, dropped=()):
    if final:
        head = (f"{MARK_H5E_FINAL} over 23 Sep - 11 Nov 2026, read {today:%-d %B %Y}** - the reading "
                f"the write-up uses; written by the cloud workflow (`tools/record_verdict.py`), "
                f"numbers from `modelfree.py --wide`, wording fixed in advance.")
    else:
        head = (f"{MARK_H5E_FIRST} at its ten-day minimum, read {today:%-d %B %Y}** - written by the "
                f"cloud workflow (`tools/record_verdict.py`), numbers from `modelfree.py --wide`, "
                f"wording fixed in advance.")
    why = [] if sc["holds"] else ([] if sc["under"] else ["the mean gap is not under 0.5"]) + \
        ([] if sc["majority"] else ["skip-only is not closer on a majority of days"])
    lines = [head, "",
             f"- **{'HOLDS' if sc['holds'] else 'FAILS'}**" + ("" if sc["holds"] else f": {'; '.join(why)}") + ".",
             f"- Mean absolute gap of the skip-only estimate to OVX: {sc['mae']:.2f} volatility points (bar: under 0.5).",
             f"- Closer to OVX than the registered estimate on {sc['closer']} of {sc['n']} counted days (bar: a majority).",
             "- Skip-only gap by day: " + "; ".join(f"{d} {g:+.2f}" for d, _, _, g, _ in sc["days"]) + ".",
             f"- Risk-free rate as the reading of record uses it (FRED cache): {rf}%."]
    if na:
        lines.append(f"- No OVX close or too thin, not counted: {', '.join(na)}.")
    if dropped:
        lines.append(f"- Dropped as recorded after the close, under Gabriel's 23 Sep rule (applied 30 Sep, "
                     f"before this verdict): {', '.join(dropped)}.")
    if sc["near"]:
        lines.append("- **Close to its bar:** the mean gap is within 0.05 of 0.5, or the day count is within one of half.")
    if final and first_verdict:
        lines.append(f"- The first verdict (the block above) was {first_verdict}; this reading "
                     f"{'agrees' if first_verdict == ('HOLDS' if sc['holds'] else 'FAILS') else 'DISAGREES'}.")
    if not final:
        lines.append("- This is the verdict at the registered minimum; H5e is registered through Wed 11 Nov "
                     "2026, and the reading then is the one written up.")
    lines.append("- The estimator is Andersen, Bondarenko & Gonzalez-Perez (2015)'s RX*, credited above; what "
                 "is this project's is its application to a free retail-grade feed on USO.")
    return "\n".join(lines)


# ---------------- writing ----------------
def parse_h7(out):
    """h7_reader.py's summary lines -> {"USO_a": (n, m), "GLD_a": ..., "GLD_b": ..., "USO_c": ...}."""
    v = {}
    for sym, part, pat in (("USO", "a", r"H7a USO: n=(\d+) mean \|free - OPRA\| ([\d.]+|n/a)"),
                           ("GLD", "a", r"H7a GLD: n=(\d+) mean \|free - OPRA\| ([\d.]+|n/a)"),
                           ("GLD", "b", r"H7b GLD: n=(\d+) mean \|free - GVZ\| ([\d.]+|n/a)"),
                           ("USO", "c", r"H7c USO: n=(\d+) mean free - OVX ([+-][\d.]+|n/a)")):
        m = re.search(pat, out)
        if not m:
            raise SystemExit(f"h7_reader output lacks the {sym} {part} line - refusing to write")
        v[f"{sym}_{part}"] = (int(m.group(1)), None if m.group(2) == "n/a" else float(m.group(2)))
    return v


def h7_verdicts(v):
    """The registered rules, applied to parse_h7's numbers. None = below the minimum."""
    a_ok = all(v[k][0] >= H7_MIN_DAYS and v[k][1] is not None for k in ("USO_a", "GLD_a"))
    b_ok = v["GLD_b"][0] >= H7_MIN_DAYS and v["GLD_b"][1] is not None
    a = None if not a_ok else ("HOLDS" if all(v[k][1] <= H7_BAR_A for k in ("USO_a", "GLD_a")) else "FAILS")
    b = None if not b_ok else ("HOLDS" if v["GLD_b"][1] <= H7_BAR_B else "FAILS")
    return a, b


def _f3(x, sign=False):
    return "n/a" if x is None else (f"{x:+.3f}" if sign else f"{x:.3f}")


def parse_h7_waiting(out):
    """h7_reader.py's 'H7 waiting on:' line -> list of missing items ([] when complete)."""
    m = re.search(r"^H7 waiting on: (.*)$", out, re.M)
    if not m:
        raise SystemExit("h7_reader output lacks its 'waiting on' line - refusing to write")
    return [] if m.group(1).strip() == "nothing" else [w.strip() for w in m.group(1).split(",")]


def block_h7(v, today, waiting=()):
    a, b = h7_verdicts(v)
    a, b = a or "NOT READ (below its minimum)", b or "NOT READ (below its minimum)"
    c = v["USO_c"]
    lines = [f"{MARK_H7}, read {today:%-d %B %Y}** - written by the cloud workflow (`tools/record_verdict.py`) "
             f"from `tools/h7_reader.py`; numbers copied from its output, wording fixed in advance.", "",
             f"- **H7a {a}:** mean absolute difference between the free-feed and OPRA Cboe replicas at the "
             f"same minute: USO {_f3(v['USO_a'][1])} over {v['USO_a'][0]} days, GLD {_f3(v['GLD_a'][1])} over "
             f"{v['GLD_a'][0]} days (bar: 0.25 or less, each).",
             f"- **H7b {b}:** the free-feed replica for GLD lies a mean absolute {_f3(v['GLD_b'][1])} points from "
             f"GVZ's close over {v['GLD_b'][0]} days (bar: 0.30 or less).",
             f"- H7c (descriptive): the free-feed replica for USO minus OVX's close averaged "
             f"{_f3(c[1], sign=True)} over {c[0]} days.",
             "- The method is Cboe's own (Volatility Index Mathematics Methodology v5.0; ETF index methodology "
             "v9.0), applied to the monthly legs recorded from 9 Oct; after-close days dropped."]
    if waiting:
        lines.append(f"- Still missing at the {COMPLETE_BY} deadline, so not counted: {', '.join(waiting)}.")
    lines += ["", DB_CREDIT]
    return "\n".join(lines)


def append_result(text, block):
    i = text.index("\n## Result\n")
    j = text.find("\n## ", i + 1)
    j = len(text) if j < 0 else j
    body = text[:j].rstrip("\n") + "\n\n" + block + "\n"
    return body + ("\n" + text[j:].lstrip("\n") if j < len(text) else "")


def append_status(text, note):
    m = re.search(r"^\*\*Status:\*\*.*$", text, re.M)
    return text[:m.end()] + " " + note + text[m.end():]


def replace_row(text, key, row):
    """Replace the `| key |` row inside HANDOFF's highest-numbered current-state section."""
    heads = [m for m in re.finditer(r"^## (\d+)\. Current state", text, re.M)]
    if not heads:
        return text, False
    start = max(heads, key=lambda m: int(m.group(1))).start()
    m = re.search(rf"^\| {re.escape(key)} \|.*$", text[start:], re.M)
    if not m:
        return text, False
    a, b = start + m.start(), start + m.end()
    return text[:a] + row + text[b:], True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="say what is due; write nothing")
    ap.add_argument("--preview", action="store_true", help="render every block even if not due; write nothing")
    ap.add_argument("--summary", help="write a plain-text summary here (for the workflow's issue)")
    ap.add_argument("--today", help="YYYY-MM-DD; default today in UTC")
    a = ap.parse_args()
    today = date.fromisoformat(a.today) if a.today else datetime.now(timezone.utc).date()
    h5 = H5.read_text()
    hand = HANDOFF.read_text()
    notes, wrote = [], []

    # H5f
    if MARK_H5F in h5 and not a.preview:
        notes.append("H5f: already recorded - skipped")
    else:
        v = parse_h5f(run(["tools/h5f_pooled.py"]))
        if v["days"] < H5F_MIN_DAYS and not a.preview:
            notes.append(f"H5f: {v['days']} of {H5F_MIN_DAYS} OPRA days - not due")
        else:
            blk = block_h5f(v, today)
            if a.preview or a.dry_run:
                print(("PREVIEW (not due, not written)\n" if v["days"] < H5F_MIN_DAYS else "DUE\n") + blk + "\n")
            else:
                h5 = append_status(append_result(h5, blk), f"H5f read {today:%-d %b %Y} (see Result).")
                cv = v["c"]["vi"] if v["c"] and v["c"]["vi"] == v["c"]["vii"] else ("UNSETTLED" if v["c"] else "n/a")
                c_txt = (f"c {v['c']['i']:.1f}% / {v['c']['ii']:.1f}% (bar 25%)" if v["c"] else "c not scored")
                row = (f"| H5f | **read {today:%-d %b}: a {v['a_v']}, b {v['b_v']}, c {cv}** | "
                       f"a {v['a']:.3f} of OPRA's spread (bar 0.5{', ON the bar' if round(abs(v['a'] - 0.5), 6) <= 0.02 else ''}); "
                       f"b {v['b_x']} of {v['b_y']}; {c_txt}; stale quotes excluded by the rule |")
                hand, ok = replace_row(hand, "H5f", row)
                wrote.append(f"H5f: a {v['a_v']} ({v['a']:.3f}), b {v['b_v']} ({v['b_x']}/{v['b_y']}), c {cv}"
                             + ("" if ok else " [HANDOFF row not found; H5 file updated]"))

    # H5e, first and final
    for final, mark, due in ((False, MARK_H5E_FIRST, H5E_FIRST_DUE), (True, MARK_H5E_FINAL, H5E_FINAL_DUE)):
        label = "H5e final" if final else "H5e first"
        if mark in h5 and not a.preview:
            notes.append(f"{label}: already recorded - skipped")
            continue
        if str(today) < due and not a.preview:
            notes.append(f"{label}: due {due}")
            continue
        if final and MARK_H5E_FIRST not in h5 and not a.preview:
            notes.append("H5e final: the first verdict is not recorded yet - recording the first one first")
            continue
        # The final reads modelfree --through 11 Nov, so modelfree's own full-precision tally covers
        # exactly the final window and the cross-check below applies to it as to the first (9 Oct 2026).
        out = run(["modelfree.py", "--wide"] + (["--through", H5E_END] if final else []))
        rows, rf, na = parse_h5e(out)
        sc = h5e_score(rows, last=H5E_END if final else None)
        if not sc or (sc["n"] < H5E_MIN_DAYS and not a.preview):
            notes.append(f"{label}: {sc['n'] if sc else 0} of {H5E_MIN_DAYS} counted days - not yet")
            continue
        late = [d for d in na if H5E_START <= d <= H5E_END]
        if final and late and str(today) < COMPLETE_BY and not a.preview:
            notes.append(f"{label}: waiting for the OVX close on {', '.join(late)} (written regardless from {COMPLETE_BY})")
            continue
        bad = crosscheck(out, sc)                           # against modelfree's own tally
        if bad:
            raise SystemExit(f"{label}: this parser and modelfree disagree - refusing to write ({bad})")
        fv = None
        if final:
            fm = re.search(re.escape(MARK_H5E_FIRST) + r".*?\n\n- \*\*(HOLDS|FAILS)\*\*", h5, re.S)
            fv = fm.group(1) if fm else None
        blk = block_h5e(sc, rf, [d for d in na if H5E_START <= d <= H5E_END], today, final, fv,
                        sorted({d for d in dropped_days(out) if H5E_START <= d <= H5E_END}))   # H3 and H5e both print it
        if a.preview or a.dry_run:
            print(("PREVIEW (not due, not written)\n" if sc["n"] < H5E_MIN_DAYS or str(today) < due else "DUE\n") + blk + "\n")
            continue
        verdict = "HOLDS" if sc["holds"] else "FAILS"
        h5 = append_status(append_result(h5, blk),
                           f"H5e {'FINAL reading' if final else 'first verdict'} read {today:%-d %b %Y} (see Result).")
        row = (f"| H5e | **{'final' if final else 'first verdict'}: {verdict}** ({today:%-d %b}) | "
               f"mean abs gap {sc['mae']:.2f} (bar under 0.5); closer on {sc['closer']} of {sc['n']} days"
               f"{'; 23 Sep - 11 Nov' if final else '; final reading 11 Nov'} |")
        hand, ok = replace_row(hand, "H5e", row)
        wrote.append(f"{label}: {verdict} - mean abs gap {sc['mae']:.2f} vs 0.5, closer on {sc['closer']} of {sc['n']}"
                     + ("" if ok else " [HANDOFF row not found; H5 file updated]"))
        break                                                # one H5e block per run

    # H7, read once
    h7 = H7.read_text() if H7.exists() else ""
    h7_wrote = False
    if h7 and MARK_H7 in h7 and not a.preview:
        notes.append("H7: already recorded - skipped")
    elif h7 and str(today) < H7_DUE and not a.preview:
        notes.append(f"H7: due {H7_DUE}")
    elif h7:
        h7out = run(["tools/h7_reader.py"])
        v, waiting = parse_h7(h7out), parse_h7_waiting(h7out)
        va, vb = h7_verdicts(v)
        if waiting and str(today) < COMPLETE_BY and not a.preview:
            notes.append(f"H7: waiting on {', '.join(waiting)} (written regardless from {COMPLETE_BY})")
        elif (va is None or vb is None) and not a.preview:
            notes.append(f"H7: below its minimum (USO {v['USO_a'][0]}, GLD {v['GLD_a'][0]} days for H7a; "
                         f"{v['GLD_b'][0]} for H7b; need {H7_MIN_DAYS}) - not written")
        else:
            blk = block_h7(v, today, waiting)
            if a.preview or a.dry_run:
                print(("PREVIEW (not due, not written)\n" if str(today) < H7_DUE else "DUE\n") + blk + "\n")
            else:
                h7 = append_status(append_result(h7, blk), f"H7 read {today:%-d %b %Y} (see Result).")
                row = (f"| H7 | **read {today:%-d %b}: H7a {va}, H7b {vb}** | free vs OPRA replica: USO "
                       f"{_f3(v['USO_a'][1])}, GLD {_f3(v['GLD_a'][1])} (bar 0.25); GLD vs GVZ {_f3(v['GLD_b'][1])} "
                       f"(bar 0.30); USO vs OVX {_f3(v['USO_c'][1], sign=True)}, descriptive |")
                hand, ok = replace_row(hand, "H7", row)
                h7_wrote = True
                wrote.append(f"H7: H7a {va} (USO {_f3(v['USO_a'][1])}, GLD {_f3(v['GLD_a'][1])} vs 0.25), "
                             f"H7b {vb} (GLD {_f3(v['GLD_b'][1])} vs 0.30)" + ("" if ok else " [HANDOFF row not found]"))

    if wrote and not (a.dry_run or a.preview):
        H5.write_text(h5)
        HANDOFF.write_text(hand)
        if h7_wrote:
            H7.write_text(h7)
    for line in notes + wrote:
        print(line)
    if a.summary:
        Path(a.summary).write_text("\n".join(wrote) + ("\n" if wrote else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
