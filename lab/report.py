#!/usr/bin/env python3
"""lab/ - the retail implementation audit's report (EXPLORATORY). Reads the summaries written by run_trades.py,
run_leak.py and run_breakeven.py and renders the site's Lab page, tools/lab.html, in the site's own styles: the
key numbers, the Leak Map, the margin table, the free-data error, the Break-Even curves, the stress table and the
predictions. Aggregates only. Public since 4 Nov 2026 (Cboe's permission, granted that day, and Gabriel's yes);
the private report.html of 14 Oct stays in lab-out/ as it was.

  python lab/report.py            # -> tools/lab.html
  python lab/report.py --check    # exit 1 if tools/lab.html is not what the summaries give

The summaries hold aggregates of licensed OPRA data and live only in the private folder, so a fresh clone (or CI)
cannot re-render the page; the pressure test compares the page with them where they exist.

Every figure on the page is computed from the summaries; no result is typed by hand. The sentences that are not
computed rest on facts the generator checks first (`premises`, `predictions`): a summary that contradicts one
stops the render instead of publishing a stale sentence (Astra's review, 4 Nov 2026).
"""
import ast
import csv
import html
import json
import math
import re
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path.home() / "Documents" / "volrec-licensed" / "lab-out"
INPUTS = ("leak_summary.json", "breakeven_summary.json", "trades.csv", "report-plan3.txt")
PAGE = ROOT / "tools" / "lab.html"
REPO = "https://github.com/gabrielmitton-cloud/volrec"
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
LEAKS = ("spreads", "limits", "liquidation", "commissions")
LEAK_NAME = {"spreads": "spreads", "limits": "margin limits", "liquidation": "forced liquidation",
             "commissions": "commissions"}
CREDIT = ("Data provided by Databento (OPRA consolidated NBBO). Cboe index levels: Cboe Global Markets. "
          "Fund closes: Alpaca Markets (personal, non-commercial use). Aggregates only.")
# The verdicts lab/REGISTRATION.md logs (14 Oct 2026; P3 re-confirmed on the fixed strip 28 Oct). They never change:
# a summary that would give another stops the render.
LOGGED = {"P1": False, "P2": True, "P3": True, "P4": False, "P5": True}
# The predictions as registered on 12 Oct 2026, word for word (the pressure test finds each in the registration).
CLAIMS = {
    "P1": "at the retail case the straddle keeps under 50 cents per $1 on at least 3 of 5 funds.",
    "P2": "spreads are the largest leak by Shapley share on at least 3 of 5 funds.",
    "P3": "the strip costs at least twice the ATM estimate.",
    "P4": "the retail cost as a fraction of the premium rises with the index level on at least 4 of 5 funds.",
    "P5": "retention is highest on SPY and lowest on USO.",
}
esc = html.escape


def num(v, d=1, plus=False):
    """A figure in the site's style: a true minus sign, a plus sign on request, no "-0.0"."""
    s = f"{abs(v):.{d}f}"
    if float(s) == 0:
        return s
    return ("−" if v < 0 else "+" if plus else "") + s


def tip(title, rows):
    """Attributes for the site's shared tooltip (V.hover in volrec.js): rows of (value, label, colour). The same
    rows name the mark for a screen reader."""
    label = f"{title}: " + "; ".join(f"{v} {k}" for v, k, _ in rows)
    return (f' data-tip="{esc(json.dumps([title, rows], ensure_ascii=False))}" tabindex="0" role="img"'
            f' aria-label="{esc(label)}"')


def share(d, key):
    """One friction's leak in cents per $1 of paper return: (Shapley value, min, max over the 24 orders)."""
    return [100 * x / d["paper"] for x in d["leaks"][key]]


def balanced(d, where, tol=1e-12):
    """Shapley values add up to the whole effect, so paper = kept + the four leaks; refuse a summary where they
    do not (tol in fractions of the account a month)."""
    gap = d["paper"] - d["kept"] - sum(d["leaks"][k][0] for k in LEAKS)
    if abs(gap) > tol:
        raise SystemExit(f"{where}: kept plus the four leaks is not the paper return (off by {gap:.2e})")


def pilot_ratios():
    """H8's pilot free/OPRA spread ratios, read from engine.py's PILOT literal without importing it."""
    tree = ast.parse((Path(__file__).resolve().parent / "engine.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PILOT" for t in node.targets):
            return {k: v[2] for k, v in ast.literal_eval(node.value).items()}
    raise SystemExit("engine.py has no PILOT")


# ------------------------------------------------------------------ the private Plan 3 report

_N = r"([+-]\d+\.\d+)"
_HEAD = re.compile(r"^(SPY|QQQ|IWM|GLD|USO) \[(registered|added back)\] n=(\d+)\s+paper " + _N + r"%/mo\s+kept " + _N
                   + r"%/mo\s+->\s+(?:(\d+\.\d) cents per \$1|not defined \(paper <= 0\));")
_LEAK5 = re.compile(r"^\s+(spreads|limits|liquidation|commissions)\s+" + _N + r"%/mo\s+\(orders: " + _N + " to " + _N + r"\)$")
_W20 = re.compile(r"^\s+at w 20%: paper " + _N + " kept " + _N + "%/mo; leaks "
                  + ", ".join(rf"{k} {_N} \({_N}\.\.{_N}\)" for k in LEAKS) + "$")
_MARGIN = re.compile(r"^\s+margin: .*\bw 5%: eff [\d.]+%, called in (\d+)\b.*\bw 20%: eff [\d.]+%, called in (\d+)\s*$")
_STRESS = (r"block ([\d.]+)\s+maxDD median ([\d.]+)% p95 ([\d.]+)% p99 [\d.]+%\s+ES95 [+-][\d.]+%\s+ES99 [+-][\d.]+%"
           r"\s+ruin\(<\$0\.50\) ([\d.]+)%\s+worst month ([+-][\d.]+)%")
_STRESS_REG = re.compile(r"^  (SPY|QQQ|IWM|GLD|USO) " + _STRESS)
_STRESS_ADD = re.compile(r"^\s+\[added back, n=(\d+)\] " + _STRESS)
_STRESS_SAME = re.compile(r"^\s+\[added back\] no excluded month to add back")
_REPLAY = re.compile(r"\b(SPY|QQQ|IWM|GLD|USO) (\d\d)-(\d\d)->(\d\d)-(\d\d) ([+-]\d+\.\d+)%")


def plan3(text, leak):
    """The private Plan 3 report (lab-out/report-plan3.txt), read strictly. It gives the [added back] figures - the
    months that failed the data checks, put back wherever they can still be traded, which the registration
    promised beside every table - and the COVID trade from the crash replays. Its [registered] lines must agree
    with leak_summary.json, so a stale report cannot slip through; a block or stress line printed twice is refused,
    so lines from two blocks cannot mix. Returns, in leak_summary.json's units (fractions of the account a month):
      {"n": {fund: registered months}, "added": {fund: {"n", "0.05", "0.2"}},
       "stress": {fund: {"n", "block", "dd50", "dd95", "ruin", "worst"}},
       "covid": {fund: ((entry month, day), (expiry month, day), fraction)}}
    Only funds with an excluded month appear in "added" and "stress"."""
    def stale(why):
        raise SystemExit(f"lab-out/report-plan3.txt: {why} - re-run lab/run_leak.py, or the summaries are stale")

    blocks, cur, stress_reg, stress_add, same, fund = {}, None, {}, {}, set(), None
    for ln in text.splitlines():
        m = _HEAD.match(ln)
        if m:
            if (m.group(1), m.group(2)) in blocks:
                stale(f"its {m.group(2)} block for {m.group(1)} appears twice")
            cur = blocks[(m.group(1), m.group(2))] = {
                "n": int(m.group(3)), "paper": float(m.group(4)), "kept": float(m.group(5)),
                "cents": float(m.group(6)) if m.group(6) else None, "leaks": {}, "w20": None, "called": None}
            continue
        if ln.startswith("=="):
            cur = None
        m = _STRESS_REG.match(ln)
        if m:
            fund = m.group(1)
            if fund in stress_reg:
                stale(f"its registered stress line for {fund} appears twice")
            stress_reg[fund] = [float(v) for v in m.groups()[1:]]
            continue
        m = _STRESS_ADD.match(ln)
        if m and fund:
            if fund in stress_add:
                stale(f"its added-back stress line for {fund} appears twice")
            stress_add[fund] = [int(m.group(1))] + [float(v) for v in m.groups()[1:]]
            continue
        if _STRESS_SAME.match(ln) and fund:
            same.add(fund)
            continue
        if cur is None:
            continue
        if m := _LEAK5.match(ln):
            cur["leaks"][m.group(1)] = [float(v) for v in m.groups()[1:]]
        elif m := _W20.match(ln):
            v = [float(x) for x in m.groups()]
            cur["w20"] = {"paper": v[0], "kept": v[1], "leaks": {k: v[2 + 3 * i: 5 + 3 * i] for i, k in enumerate(LEAKS)}}
        elif m := _MARGIN.match(ln):
            cur["called"] = (int(m.group(1)), int(m.group(2)))

    def frac(b, w):           # one block at one weight, as fractions, in leak_summary.json's layout
        src = b if w == "0.05" else b["w20"]
        return {"paper": src["paper"] / 100, "kept": src["kept"] / 100, "called": b["called"][0 if w == "0.05" else 1],
                "leaks": {k: [x / 100 for x in src["leaks"][k]] for k in LEAKS}}

    added, stress = {}, {}
    for s in FUNDS:
        for kind in ("registered", "added back"):
            b = blocks.get((s, kind))
            if not b or set(b["leaks"]) != set(LEAKS) or not b["w20"] or not b["called"]:
                stale(f"its {kind} block for {s} is missing or incomplete")
        r, a = blocks[(s, "registered")], blocks[(s, "added back")]
        for w in ("0.05", "0.2"):           # the registered lines against the summary they were printed from
            got, want = frac(r, w), leak[s]["weights"][w]
            ok = (abs(got["paper"] - want["paper"]) <= 6e-6 and abs(got["kept"] - want["kept"]) <= 6e-6
                  and got["called"] == want["called"]
                  and all(abs(x - y) <= 6e-7 for k in LEAKS for x, y in zip(got["leaks"][k], want["leaks"][k])))
            if not ok:
                stale(f"its registered {s} line at w = {w} does not match leak_summary.json")
        sr = stress_reg.get(s)
        st_ = leak[s]["stress"]
        if not sr or sr[0] != st_["block"] or any(abs(x - 100 * st_[k]) > tol for x, k, tol in
                                                  zip(sr[1:], ("dd50", "dd95", "ruin", "worst"), (.051, .051, .051, .0051))):
            stale(f"its registered {s} stress line does not match leak_summary.json")
        if a["n"] == r["n"]:
            if frac(a, "0.05") != frac(r, "0.05") or frac(a, "0.2") != frac(r, "0.2") or s not in same:
                stale(f"{s} has no excluded month, yet its added-back figures differ from the registered ones")
            continue
        if a["n"] < r["n"] or s not in stress_add or stress_add[s][0] != a["n"]:
            stale(f"{s}'s added-back sample is smaller than the registered one, or has no stress line of its own")
        added[s] = {"n": a["n"], "0.05": frac(a, "0.05"), "0.2": frac(a, "0.2")}
        for w in ("0.05", "0.2"):           # printed to 3 and 4 decimals, so the identity holds to rounding
            balanced(added[s][w], f"{s} added back, w = {w}", tol=1.5e-5)
        if a["cents"] is not None and abs(a["cents"] - 100 * a["kept"] / a["paper"]) > 0.2:
            stale(f"{s}'s added-back cents kept do not follow from its paper and kept returns")
        added[s]["0.05"]["cents"] = a["cents"]
        n, block, dd50, dd95, ruin, worst = stress_add[s]
        stress[s] = {"n": n, "block": block, "dd50": dd50 / 100, "dd95": dd95 / 100, "ruin": ruin / 100, "worst": worst / 100}
    m = re.search(r"^\s+2020-03: (.*)$", text, re.M)
    covid = {}
    for s, e1, e2, x1, x2, v in _REPLAY.findall(m.group(1).split("|")[0] if m else ""):
        covid.setdefault(s, ((int(e1), int(e2)), (int(x1), int(x2)), float(v) / 100))
    if set(covid) != set(FUNDS) or len({c[:2] for c in covid.values()}) != 1:
        stale("its March 2020 crash replay does not hold one COVID trade, on the same dates, for every fund")
    return {"n": {s: blocks[(s, "registered")]["n"] for s in FUNDS}, "added": added, "stress": stress, "covid": covid}


def same_months(be, trades, p3plan):
    """The inputs must count the same months: Plan 3's registered blocks, the break-even summary (whose count the
    page prints) and trades.csv's registered rows; and Plan 3's added-back sample, trades.csv's tradeable rows (a
    mid return recorded), which the excluded-months sensitivity averages. A fund with nothing to add back has no
    tradeable excluded row (Astra's follow-up, 4 Nov 2026: a report whose two SPY blocks both said 126 passed)."""
    for s in FUNDS:
        rows = [t for t in trades if t["symbol"] == s]
        reg, tradeable = sum(t["registered"] == "1" for t in rows), sum(bool(t["straddle_mid_ret"]) for t in rows)
        n, added = p3plan["n"][s], p3plan["added"].get(s, {"n": p3plan["n"][s]})["n"]
        if not n == be[s]["n_month"] == reg or tradeable != added:
            raise SystemExit(f"{s}: the inputs count different months - report-plan3.txt {n} registered and {added} "
                             f"added back, breakeven_summary.json {be[s]['n_month']}, trades.csv {reg} registered "
                             f"and {tradeable} tradeable")


# ------------------------------------------------------------------ the trades

def sensitivity(trades):
    """GLD's and USO's mean straddle return at mid, cents per $1 of premium: (registered months, with the tradeable
    excluded months added back) - Plan 2's sensitivity, as corrected on 28 Oct."""
    out = {}
    for s in ("GLD", "USO"):
        r = [(t["registered"] == "1", float(t["straddle_mid_ret"])) for t in trades
             if t["symbol"] == s and t["straddle_mid_ret"]]
        reg = [v for keep, v in r if keep]
        out[s] = (100 * sum(reg) / len(reg), 100 * sum(v for _, v in r) / len(r))
    return out


def strip_ratios(trades):
    """P3: each fund's median strip cost over ATM cost on the registered trades, the strip held fixed (28 Oct)."""
    out = {}
    for s in FUNDS:
        r = [float(t["strip_cost_fixed_pts"]) / float(t["atm_cost_pts"]) for t in trades
             if t["symbol"] == s and t["registered"] == "1" and t["strip_cost_fixed_pts"] and t["atm_cost_pts"]
             and float(t["atm_cost_pts"]) > 0]
        if not r:
            raise SystemExit(f"trades.csv has no strip cost for {s}")
        out[s] = statistics.median(r)
    return out


def span(trades):
    """(first entry, last entry, last expiry, shortest hold, longest hold in days) over the registered trades."""
    reg = [(date.fromisoformat(t["entry"]), date.fromisoformat(t["expiry"])) for t in trades if t["registered"] == "1"]
    held = [(x - e).days for e, x in reg]
    return min(e for e, _ in reg), max(e for e, _ in reg), max(x for _, x in reg), min(held), max(held)


def day(d):
    return f"{d.day} {d:%B %Y}"


# ------------------------------------------------------------------ figures and tables

def margin_free(d, where, tol):
    """Fig. 1's caption, as a check on one sample at w = 5%: margin never binds (no margin leak in any of the 24
    orders, no margin call), so every order gives the same shares (spreads' and commissions' ranges collapse to one
    value, within tol)."""
    for k in ("limits", "liquidation"):
        if any(v != 0.0 for v in d["leaks"][k]):
            raise SystemExit(f"{where}: a {k} leak at w = 5% - the Leak Map assumes margin never binds there")
    if d["called"]:
        raise SystemExit(f"{where}: a margin call at w = 5% - the Leak Map assumes margin never binds there")
    for k in ("spreads", "commissions"):
        if max(d["leaks"][k]) - min(d["leaks"][k]) > tol:
            raise SystemExit(f"{where}: the {k} share differs across the 24 orders at w = 5% - the Leak Map's caption "
                             "says every order gives the same shares")


def leak_map(leak, added):
    """Fig. 1: the Leak Map at w = 5%, as HTML bars so the text stays legible at any width. Margin never binds at
    this size, so each bar is kept + spreads + commissions = one paper dollar. The page refuses to draw rather
    than draw that wrong: a margin leak anywhere in its range over the 24 orders, a margin call or shares that
    change with the order - in any sample the figure's caption covers, the fund without a paper profit and the
    added-back rows of its table included - a negative part, or parts that do not add up to the paper return."""
    rows = []
    for s in FUNDS:
        d = leak[s]["weights"]["0.05"]
        margin_free(d, s, 1e-12)
        if s in added:          # printed to 4 decimals of a percent, so one unit in the last place is 1e-6
            margin_free(added[s]["0.05"], f"{s} added back", 5e-7)
        if d["paper"] <= 0:
            rows.append(f'<div class="lm-row lm-none"><span class="lm-k">{s}</span><span class="lm-note">'
                        f'lost {num(-100 * d["paper"], 2)}% of the account a month before any cost: '
                        f'no paper dollar to keep</span></div>')
            continue
        balanced(d, f"{s} at w = 5%")
        if min(d["kept"], d["leaks"]["spreads"][0], d["leaks"]["commissions"][0]) < 0:
            raise SystemExit(f"{s}: a negative part at w = 5% cannot be drawn as a share of one paper dollar")
        kept, sp, cm = 100 * d["kept"] / d["paper"], share(d, "spreads")[0], share(d, "commissions")[0]
        t = tip(f"{s}, premium 5% of the account", [
            [f"{kept:.1f}¢", "kept", "var(--lab-kept)"], [f"{sp:.1f}¢", "spreads", "var(--lab-spread)"],
            [f"{cm:.1f}¢", "commissions", "var(--lab-comm)"],
            [f"{num(100 * d['paper'], 3, True)}%", "paper return a month", None]])
        rows.append(f'<div class="lm-row"{t}><span class="lm-k">{s}</span><span class="lm-bar">'
                    f'<i class="mk-kept" style="width:{kept:.2f}%"></i><i class="mk-spread" style="width:{sp:.2f}%"></i>'
                    f'<i class="mk-comm" style="width:{cm:.2f}%"></i></span><span class="lm-v">{kept:.1f}¢</span></div>')
    ticks_ = "".join(f'<b style="left:{t}%">{t}¢</b>' for t in (0, 25, 50, 75, 100))
    return (f'<div class="lm">{"".join(rows)}<div class="lm-row lm-axis" aria-hidden="true"><span></span>'
            f'<span class="lm-ticks">{ticks_}</span><span></span></div></div>')


def leak_row(name, d, n, cls=""):
    c = f' class="{cls}"' if cls else ""
    called = f'{d["called"]} of {n}'
    if d["paper"] <= 0:
        return (f'<tr{c}><td>{name}</td><td class="r">{num(100 * d["paper"], 3, True)}</td><td class="k r">none</td>'
                f'<td class="r">{called}</td><td class="na" colspan="4">no paper profit, so nothing kept to share out</td></tr>')
    cells = []
    for k in LEAKS:
        v, lo, hi = share(d, k)
        rg = f' <span class="rg">({num(lo, 1, True)} to {num(hi, 1, True)})</span>' if hi - lo > 0.05 else ""
        cells.append(f'<td class="r">{num(v, 1, True)}{rg}</td>')
    return (f'<tr{c}><td>{name}</td><td class="r">{num(100 * d["paper"], 3, True)}</td>'
            f'<td class="k r">{100 * d["kept"] / d["paper"]:.1f}</td><td class="r">{called}</td>{"".join(cells)}</tr>')


def leak_table(leak, be, w, added):
    """Every fund at one size: paper return, cents kept, months with a margin call and each friction's Shapley
    share, with the range over the 24 orders wherever the orders disagree. Beneath GLD and USO, the same with
    their excluded months added back."""
    out = []
    for s in FUNDS:
        d = leak[s]["weights"][w]
        balanced(d, f"{s} at w = {w}")
        out.append(leak_row(s, d, be[s]["n_month"]))
        if s in added:
            out.append(leak_row(f'<span class="abl">{s}, all {added[s]["n"]} months</span>', added[s][w], added[s]["n"], "ab"))
    head = ('<tr><th>Fund</th><th class="r">Paper return a month, %</th><th class="r">Kept, ¢ per $1</th>'
            '<th class="r">Months with a margin call</th>'
            + "".join(f'<th class="r">{LEAK_NAME[k].capitalize()}, ¢</th>' for k in LEAKS) + "</tr>")
    return f'<table class="data lab-t"><thead>{head}</thead><tbody>{"".join(out)}</tbody></table>'


def free_data_rows(leak):
    """Spec Q6: what a free-data user would think the spreads cost, using H8's pilot free/OPRA ratio."""
    ratio, out = pilot_ratios(), []
    for s in FUNDS:
        d = leak[s]["weights"]["0.05"]
        if d["paper"] > 0:
            true_c = share(d, "spreads")[0]
            est = true_c * ratio[s]
            out.append(f'<tr><td>{s}</td><td class="r">{true_c:.1f}</td><td class="r">{est:.1f}</td>'
                       f'<td class="r">{num(est - true_c, 1, True)}</td><td class="r">{ratio[s]:.2f}</td></tr>')
    return "".join(out)


def stress_rows(st, added):
    def row(name, x, cls=""):
        c = f' class="{cls}"' if cls else ""
        return (f'<tr{c}><td>{name}</td><td class="r">{100 * x["dd50"]:.1f}</td><td class="r">{100 * x["dd95"]:.1f}</td>'
                f'<td class="r">{100 * x["ruin"]:.1f}</td><td class="r">{num(100 * x["worst"], 1, True)}</td></tr>')
    out = []
    for s in FUNDS:
        out.append(row(s, st[s]))
        if s in added:
            out.append(row(f'<span class="abl">{s}, all {added[s]["n"]} months</span>', added[s], "ab"))
    return "".join(out)


def ticks(lo, hi):
    """Whole-number ticks covering [lo, hi], at most about six of them."""
    step = next(s for s in (1, 2, 5, 10, 20) if (hi - lo) / s <= 6)
    return [v for v in range(math.floor(lo / step) * step, math.ceil(hi / step) * step + 1, step)]


def fit_slope(sym, d):
    """The least-squares line of monthly net result on the index, recovered from the quintile table: OLS passes
    through the months' own mean, which is the count-weighted mean of the bins, and crosses zero at the stored
    crossing, so slope = mean net / (mean index - crossing). None without a crossing. Where the fund's own index
    is VIX the summary also stores the fit itself (vix_axis), and the two must agree."""
    net = d["net_bins"]
    n = sum(b[2] for b in net)
    if n != d["n_month"]:
        raise SystemExit(f"{sym}: the quintile table holds {n} months, not the {d['n_month']} traded")
    if d["crossing"] is None:
        return None
    xm, ym = sum(b[0] * b[2] for b in net) / n, sum(b[1] * b[2] for b in net) / n
    if abs(xm - d["crossing"]) < 1e-9:
        return None
    slope = ym / (xm - d["crossing"])
    if d["index"] == "VIX" and (abs(slope - d["vix_axis"]["slope"]) > 1e-9
                                or abs(d["crossing"] - d["vix_axis"]["crossing"]) > 1e-9):
        raise SystemExit(f"{sym}: the line recovered from the quintile table is not the stored fit")
    return slope


def be_chart(sym, d):
    """One Break-Even panel: net result and spread cost by quintile of the fund's own index, the fitted line and
    where it crosses zero, and the crossing's 90% interval. The axis spans the quintile means; an interval end or
    a crossing beyond it is written at the edge with an arrow. Five focusable columns, one per quintile."""
    W, H, L, B, T, R = 300, 186, 34, 34, 12, 12
    net, cost = sorted(d["net_bins"]), sorted(d["cost_bins"])
    if len(net) != len(cost):
        raise SystemExit(f"{sym}: the net and cost tables have different numbers of groups")
    xs = [b[0] for b in net + cost]
    pad = (max(xs) - min(xs)) * 0.05
    x0, x1 = min(xs) - pad, max(xs) + pad
    yt = ticks(min([b[1] for b in net + cost] + [0.0]), max([b[1] for b in net + cost] + [0.0]))
    y0, y1 = yt[0], yt[-1]
    X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - R)
    Y = lambda v: T + (y1 - v) / (y1 - y0) * (H - T - B)
    cid = f"be-clip-{sym.lower()}"
    o = [f'<svg viewBox="0 0 {W} {H}" role="group" aria-label="{sym}: monthly net result and spread cost in '
         f'volatility points by quintile of {d["index"]}, with the fitted line">',
         f'<defs><clipPath id="{cid}"><rect x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}"/></clipPath></defs>']
    if d["ci"]:
        lo, hi = d["ci"]
        a, b = max(lo, x0), min(hi, x1)
        if a < b:
            o.append(f'<rect x="{X(a):.1f}" y="{T}" width="{X(b) - X(a):.1f}" height="{H - T - B}" class="band"/>')
        for v in (lo, hi):
            if x0 <= v <= x1:
                o.append(f'<line x1="{X(v):.1f}" y1="{T}" x2="{X(v):.1f}" y2="{H - B}" class="ci-end"/>')
            elif v < x0:
                o.append(f'<text x="{L + 3}" y="{T + 9}" class="edge">← {v:.1f}</text>')
            else:
                o.append(f'<text x="{W - R - 3}" y="{T + 9}" class="edge" text-anchor="end">{v:.1f} →</text>')
    for v in yt:
        o.append(f'<line x1="{L}" y1="{Y(v):.1f}" x2="{W - R}" y2="{Y(v):.1f}" class="{"zero" if v == 0 else "grid"}"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" class="tick" text-anchor="end">{num(v, 0, True)}</text>')
    for v in ticks(x0, x1):
        if x0 <= v <= x1:
            o.append(f'<text x="{X(v):.1f}" y="{H - B + 15}" class="tick" text-anchor="middle">{v}</text>')
    o.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 4}" class="tick" text-anchor="middle">'
             f'{d["index"]} at the previous close</text>')
    slope = fit_slope(sym, d)
    if slope is not None:
        c = d["crossing"]
        o.append(f'<line x1="{X(x0):.1f}" y1="{Y(slope * (x0 - c)):.1f}" x2="{X(x1):.1f}" y2="{Y(slope * (x1 - c)):.1f}" '
                 f'class="fit" clip-path="url(#{cid})"/>')
        # Off the axis, the crossing is written on the zero line's edge: below the line, where the spread cost
        # (always just above zero) cannot run through it, unless zero is the plot's floor.
        ly = Y(0) + 12 if Y(0) + 12 <= H - B - 2 else Y(0) - 5
        if x0 <= c <= x1:
            o.append(f'<circle cx="{X(c):.1f}" cy="{Y(0):.1f}" r="3.5" class="cross"/>')
        elif c < x0:
            o.append(f'<text x="{L + 3}" y="{ly:.1f}" class="edge">← {c:.1f}</text>')
        else:
            o.append(f'<text x="{W - R - 3}" y="{ly:.1f}" class="edge" text-anchor="end">{c:.1f} →</text>')
    for cls, bins in (("net", net), ("cost", cost)):
        o.append(f'<polyline points="{" ".join(f"{X(b[0]):.1f},{Y(b[1]):.1f}" for b in bins)}" class="ln-{cls}"/>')
        o.extend(f'<circle cx="{X(b[0]):.1f}" cy="{Y(b[1]):.1f}" r="4" class="dt-{cls}"/>' for b in bins)
    edges = [x0] + [(net[i][0] + net[i + 1][0]) / 2 for i in range(len(net) - 1)] + [x1]
    for i, (bn, bc) in enumerate(zip(net, cost)):
        t = tip(f"{sym}, {d['index']} group {i + 1} of {len(net)}", [
            [f"{num(bn[1], 2, True)} pts", f"net result, {bn[2]} months, {d['index']} near {bn[0]:.1f}", "var(--lab-net)"],
            [f"{num(bc[1], 3, True)} pts", f"spread cost, {bc[2]} weekly samples, {d['index']} near {bc[0]:.1f}",
             "var(--lab-spread)"]])
        o.append(f'<rect x="{X(edges[i]):.1f}" y="{T}" width="{X(edges[i + 1]) - X(edges[i]):.1f}" height="{H - T - B}" '
                 f'class="hit"{t}/>')
    o.append("</svg>")
    return "".join(o)


def be_caption(sym, d):
    """The crossing and its interval, each reported for what it is: a crossing without an interval keeps its
    point estimate, and the share of resamples that cross outside the data is always given."""
    lo_r, hi_r = d["range"]
    head = f"<b>{sym}</b> on {d['index']} ({lo_r:.1f} to {hi_r:.1f} in the data)."
    out = f"{100 * d['out'] / 2000:.0f}% of resamples cross outside the data."
    cx = "No crossing inside the data" if d["crossing"] is None else f"Crosses zero at {d['crossing']:.1f}"
    if not d["ci"]:
        return f"{head} {cx}; no interval; {out}"
    lo, hi = d["ci"]
    where = "" if d["crossing"] is None or lo <= d["crossing"] <= hi else ", outside its own interval"
    return f"{head} {cx}{where}; 90% interval {lo:.1f} to {hi:.1f}; {out}"


def be_table(be):
    rows = []
    for s in FUNDS:
        d = be[s]
        for i, (bn, bc) in enumerate(zip(sorted(d["net_bins"]), sorted(d["cost_bins"]))):
            rows.append(f'<tr><td>{s if i == 0 else ""}</td><td>{d["index"] if i == 0 else ""}</td><td class="r">{i + 1}</td>'
                        f'<td class="r">{bn[0]:.1f}</td><td class="r">{num(bn[1], 2, True)}</td><td class="r">{bn[2]}</td>'
                        f'<td class="r">{bc[0]:.1f}</td><td class="r">{num(bc[1], 3, True)}</td><td class="r">{bc[2]}</td></tr>')
    head = ('<tr><th>Fund</th><th>Index</th><th class="r">Group</th><th class="r">Index, months</th>'
            '<th class="r">Net result, pts</th><th class="r">Months</th><th class="r">Index, weeks</th>'
            '<th class="r">Spread cost, pts</th><th class="r">Weekly samples</th></tr>')
    return f'<table class="data lab-t"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table>'


# ------------------------------------------------------------------ what the words rest on

def predictions(leak, be, kept5, p3):
    """The five registered predictions, judged again from the summaries. A verdict that differs from the one the
    registration logged stops the render: the logged verdict stands, so the summaries must be wrong or stale."""
    w5 = {s: leak[s]["weights"]["0.05"] for s in FUNDS}
    under = [s for s in kept5 if kept5[s] < 50]
    spread_top = [s for s in FUNDS if max(LEAKS, key=lambda k: w5[s]["leaks"][k][0]) == "spreads"]
    twice = [s for s in FUNDS if p3[s] >= 2]
    rises = [s for s in FUNDS if be[s]["p4_slope"][1] > 0]
    ranked = sorted(kept5, key=kept5.get)
    got = {"P1": len(under) >= 3, "P2": len(spread_top) >= 3, "P3": len(twice) == len(FUNDS),
           "P4": len(rises) >= 4, "P5": bool(ranked) and ranked[-1] == "SPY" and ranked[0] == "USO"}
    wrong = [p for p in LOGGED if got[p] != LOGGED[p]]
    if wrong:
        raise SystemExit(f"the summaries judge {', '.join(wrong)} differently from lab/REGISTRATION.md's logged "
                         "verdicts, which stand: the summaries are wrong or stale")
    return under, spread_top, twice, rises, ranked


def premises(leak, be, kept5, p3plan, sens):
    """The page's uncomputed sentences, as checks. Each names the sentence it protects."""
    w5 = {s: leak[s]["weights"]["0.05"] for s in FUNDS}
    w20 = {s: leak[s]["weights"]["0.2"] for s in FUNDS}
    st = {s: leak[s]["stress"] for s in FUNDS}
    eq = ("SPY", "QQQ", "IWM")
    spread_c = {s: share(w5[s], "spreads")[0] for s in kept5}
    peak = {s: max(b[1] for b in be[s]["cost_bins"]) for s in FUNDS}
    width = {s: be[s]["ci"][1] - be[s]["ci"][0] for s in FUNDS if be[s]["ci"]}
    swing = {s: max(abs(share(w20[s], k)[2] - share(w20[s], k)[1]) for k in ("limits", "liquidation"))
             for s in FUNDS if w20[s]["paper"] > 0}
    spy_mid = [b[1] for b in sorted(be["SPY"]["net_bins"])][1:4]
    covid3 = sorted(c[2] for c in p3plan["covid"].values())[:3]
    add = p3plan["stress"]
    need = {
        "'Gold lost money before any cost' (only GLD lacks a paper profit at 5%)": set(FUNDS) - set(kept5) == {"GLD"},
        "'Costs barely matter on liquid funds' (SPY, QQQ and IWM keep over 85 cents)": all(kept5[s] > 85 for s in eq),
        "'USO, whose options trade far wider' (its spread leak is at least 3x any equity fund's)":
            spread_c["USO"] >= 3 * max(spread_c[s] for s in eq),
        "'margin calls came often' (SPY called in at least one month in ten at 20%)":
            w20["SPY"]["called"] >= be["SPY"]["n_month"] / 10,
        "'forced liquidation became the largest leak on ...' (it leads on at least one fund at 20%)":
            any(max(LEAKS, key=lambda k: share(w20[s], k)[0]) == "liquidation" for s in kept5),
        "'The margin shares swing widely' (at 20% a margin share ranges over 10+ cents across the orders, every fund "
        "with a paper profit)": bool(swing) and min(swing.values()) >= 10,
        "'the COVID trade cost ...' (the three largest COVID results are losses)": max(covid3) < 0,
        "'swings by several volatility points from one group to the next' (SPY's middle three groups 2+ points apart)":
            len(spy_mid) == 3 and min(abs(spy_mid[1] - spy_mid[0]), abs(spy_mid[2] - spy_mid[1])) >= 2,
        "'Each point is the mean of one fifth of the observations' (five groups of months and of weeks, every fund)":
            all(len(be[s]["net_bins"]) == len(be[s]["cost_bins"]) == 5 for s in FUNDS),
        "'USO, the widest market here' (its spread cost peaks highest)": max(peak, key=peak.get) == "USO",
        "'block length one month for every fund'": all(st[s]["block"] == 1.0 for s in FUNDS),
        "'There is no reliable break-even' (every interval there is spans 10+ index points, 5%+ of resamples cross "
        "outside)": all(v >= 10 for v in width.values()) and min(be[s]["out"] for s in FUNDS) >= 100,
        "'GLD's tail is materially worse with its months back' (chance up 10+ points)":
            "GLD" in add and add["GLD"]["ruin"] - st["GLD"]["ruin"] >= 0.10,
        "'USO's barely moves' (chance within 5 points)": "USO" in add and abs(add["USO"]["ruin"] - st["USO"]["ruin"]) < 0.05,
        "'Added back, they make gold's result worse but not oil's'": sens["GLD"][1] < sens["GLD"][0] and sens["USO"][1] >= sens["USO"][0],
        "'the free feed's quotes run wider' (every pilot ratio above 1)": all(pilot_ratios()[s] > 1 for s in kept5),
    }
    bad = [k for k, v in need.items() if not v]
    if bad:
        raise SystemExit("the page's text no longer fits the summaries: " + "; ".join(bad))


# ------------------------------------------------------------------ the page

def page(leak, be, trades, p3plan):
    w5 = {s: leak[s]["weights"]["0.05"] for s in FUNDS}
    w20 = {s: leak[s]["weights"]["0.2"] for s in FUNDS}
    kept5 = {s: 100 * w5[s]["kept"] / w5[s]["paper"] for s in FUNDS if w5[s]["paper"] > 0}
    called20 = {s: w20[s]["called"] for s in FUNDS}
    st = {s: leak[s]["stress"] for s in FUNDS}
    same_months(be, trades, p3plan)
    sens = sensitivity(trades)
    p3 = strip_ratios(trades)
    premises(leak, be, kept5, p3plan, sens)
    under, spread_top, twice, rises, ranked = predictions(leak, be, kept5, p3)
    first, last, last_exp, hmin, hmax = span(trades)
    added, covid = p3plan["added"], p3plan["covid"]
    ruin = sorted((100 * st[s]["ruin"], s) for s in FUNDS)
    out_share = sorted(100 * be[s]["out"] / 2000 for s in FUNDS)
    width = sorted(be[s]["ci"][1] - be[s]["ci"][0] for s in FUNDS if be[s]["ci"])
    no_ci = [s for s in FUNDS if not be[s]["ci"]]
    ratio = pilot_ratios()
    over = {s: share(w5[s], "spreads")[0] * (ratio[s] - 1) for s in kept5}
    rlo, rhi = min(kept5, key=ratio.get), max(kept5, key=ratio.get)
    peak = {s: max(b[1] for b in be[s]["cost_bins"]) for s in FUNDS}
    eq_peak = math.ceil(100 * max(peak[s] for s in ("SPY", "QQQ", "IWM"))) / 100     # an upper bound: "at or below"
    lead20 = [s for s in kept5 if max(LEAKS, key=lambda k: share(w20[s], k)[0]) == "liquidation"]
    gained20 = {s: 100 * w20[s]["kept"] / w20[s]["paper"] for s in kept5 if w20[s]["kept"] > w20[s]["paper"]}
    n = {s: be[s]["n_month"] for s in FUNDS}
    crossed = [s for s in FUNDS if be[s]["crossing"] is not None]
    spy_mid = [b[1] for b in sorted(be["SPY"]["net_bins"])][1:4]
    hardest = set(sorted(FUNDS, key=lambda f: covid[f][2])[:3])          # the three largest COVID losses
    worst3 = [s for s in FUNDS if s in hardest]
    (cm1, cd1), (cm2, cd2) = covid["SPY"][:2]
    covid_when = f"{day(date(2020, cm1, cd1))[:-5]} to {day(date(2020, cm2, cd2))}"
    eq3 = [kept5[s] for s in ("SPY", "QQQ", "IWM")]
    gaps = (f"{min(b[2] for s in FUNDS for b in be[s]['net_bins'])} to {max(b[2] for s in FUNDS for b in be[s]['net_bins'])}",
            f"{min(b[2] for s in FUNDS for b in be[s]['cost_bins'])} to {max(b[2] for s in FUNDS for b in be[s]['cost_bins'])}")
    months = f"SPY, QQQ and IWM {n['SPY']}, GLD {n['GLD']}, USO {n['USO']}"
    added_note = " ".join(
        f"With its {a['n'] - n[s]} excluded months added back, {s} " +
        (f"keeps {a['0.05']['cents']:.1f} cents." if a["0.05"]["paper"] > 0 else "still has no paper profit.")
        for s, a in added.items())
    # The crossing and its interval are reported independently: a fund may have either without the other.
    fit_txt = ("for every fund" if len(crossed) == len(FUNDS) else
               f"for {len(crossed)} of 5 funds" if crossed else "for no fund inside the data")
    if width:
        ci_txt = (f'its 90% interval is <span class="m">{width[0]:.0f}</span>'
                  + (f' to <span class="m">{width[-1]:.0f}</span>' if f"{width[0]:.0f}" != f"{width[-1]:.0f}" else "")
                  + " index points wide"
                  + (f" ({' and '.join(no_ci)} {'has' if len(no_ci) == 1 else 'have'} no interval)" if no_ci else ""))
    else:
        ci_txt = "no fund's crossing has an interval"
    # P4's registered test is a slope interval wholly above zero; failing it shows no rise, not proportional spreads.
    others = [s for s in FUNDS if s not in rises]
    p4_e = f"Rises on {len(rises)} of 5 ({', '.join(rises)})" if rises else "Rises on none of the 5"
    p4_g = ("the registered test: the slope's 95% Newey-West interval lies wholly above zero"
            + (" only there" if rises else ", on no fund")
            + ("; on the others it includes zero" if all(be[s]["p4_slope"][1] <= 0 <= be[s]["p4_slope"][2] for s in others)
               else "; the others do not pass it"))
    be_cards = "".join(f'<div class="be"><p class="be-cap">{be_caption(s, be[s])}</p>{be_chart(s, be[s])}</div>'
                       for s in FUNDS)
    src = f'<div class="src">{esc(CREDIT)}</div>'

    def kpi(k, v, g):
        return f'<div class="kpi"><div class="kpi-k">{k}</div><div class="kpi-v">{v}</div><div class="kpi-g">{g}</div></div>'

    kpis = "".join([
        kpi("Kept on SPY, QQQ, IWM", f"{min(eq3):.0f}–{max(eq3):.0f}¢", "of each paper dollar, premium 5% of the account"),
        kpi("Kept on USO", f"{kept5['USO']:.0f}¢", "its options trade far wider"),
        kpi("SPY at 20% of the account", f"{called20['SPY']} of {n['SPY']}", "months with a margin call"),
        kpi("SPY's COVID month", f"{num(100 * covid['SPY'][2], 1, True)}%", "of the account at 5%, held to expiry"),
        kpi("Chance of falling below half", f"{ruin[0][0]:.1f}–{ruin[-1][0]:.1f}%", "within ten simulated years, by fund"),
    ])
    p_rows = [
        ("P1", "Tested, fails",
         (f"{len(under)} of 5 keep under 50 cents" if under else "No fund keeps under 50 cents"),
         ", ".join(f"{s} {kept5[s]:.0f}" for s in kept5) + "; " + ", ".join(s for s in FUNDS if s not in kept5) + " has no paper profit"),
        ("P2", "Tested, holds as written", f"{len(spread_top)} of 5 at 5% of the account",
         f"only because margin never binds at that size; at 20% forced liquidation is the largest leak on {' and '.join(lead20)}"),
        ("P3", "Tested, holds", f"{len(twice)} of 5 funds, {min(p3.values()):.1f} to {max(p3.values()):.1f} times",
         "the strip: every strike a model-free volatility estimate prices, each charged its half-spread; median per fund"),
        ("P4", "Tested, fails", p4_e, p4_g),
        ("P5", "Tested, holds", f"{ranked[-1]} {kept5[ranked[-1]]:.0f} highest, {ranked[0]} {kept5[ranked[0]]:.0f} lowest",
         "among the funds with a paper profit; " + ", ".join(s for s in FUNDS if s not in kept5) + " has none to rank"),
    ]
    p_table = "".join(
        f'<tr><td class="hid">{p}</td><td class="claim">{esc(CLAIMS[p][0].upper() + CLAIMS[p][1:])}</td>'
        f'<td><span class="hs" data-h="tested">{v}</span></td><td class="ev">{e}<span>{g}</span></td></tr>'
        for p, v, e, g in p_rows)
    links = '[["Paper", "../", "paper"], ["Instrument", "monitor.html", "monitor"], ["Lab", "lab.html", "lab"], ["Code", V.REPO, "code"]]'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Volrec Lab</title>
<meta name="description" content="A side study to 'What does free options data cost?': how much of the volatility premium a retail seller of fund straddles keeps after spreads, commissions and margin, 2016 to 2026.">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23000'/%3E%3Cpath d='M3 23C9 23 11 8 16 8s7 15 13 15' fill='none' stroke='%232396C4' stroke-width='2.6'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Martian+Mono:wdth,wght@75..112.5,300..700&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&display=swap">
<link rel="stylesheet" href="volrec.css?v=20261104">
<!-- Generated by lab/report.py from the private lab summaries. Edit the generator, not this file. -->
<style>
/* Lab colours. Neutral grey is what the seller keeps (pinned to the grey the palette was validated with); the two
   leaks take the dataviz palette's orange and violet (dark steps, validated on --panel), clear of the channel and
   status colours. */
:root {{ --lab-kept: #697785; --lab-spread: #d95926; --lab-comm: #9085e9; --lab-net: var(--read); }}
.mk-kept {{ background: var(--lab-kept); }} .mk-spread {{ background: var(--lab-spread); }} .mk-comm {{ background: var(--lab-comm); }}
.lab-key {{ margin-top: 40px; }}
.lab-key .kpis {{ border: 1px solid var(--rule); }}
.lab-key .src {{ margin-top: 10px; }}
.lm {{ display: grid; gap: 12px; max-width: 760px; }}
.lm-row {{ display: grid; grid-template-columns: 44px minmax(0, 1fr) 58px; gap: 12px; align-items: center; outline-offset: 4px; }}
.lm-k {{ color: var(--ink); }}
/* Each part is its true share of the bar's full width; the 2px separators are drawn inside the following part,
   so they take no width from the scale, and a part of zero width shows nothing. */
.lm-bar {{ display: flex; height: 22px; border-radius: 0 4px 4px 0; overflow: hidden; }}
.lm-bar i {{ display: block; flex: none; height: 100%; }}
.lm-bar i + i {{ box-shadow: inset 2px 0 0 var(--panel); }}
.lm-row[data-tip]:hover .lm-bar i + i, .lm-row[data-tip]:focus .lm-bar i + i {{ box-shadow: inset 2px 0 0 var(--panel-2); }}
.lm-v {{ color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }}
.lm-note {{ grid-column: 2 / -1; color: var(--ink-3); font-size: 10.5px; }}
.lm-row[data-tip]:hover, .lm-row[data-tip]:focus {{ background: var(--panel-2); }}
.lm-axis {{ margin-top: -4px; }}
.lm-ticks {{ position: relative; height: 16px; border-top: 1px solid var(--rule-2); }}
.lm-ticks b {{ position: absolute; top: 3px; transform: translateX(-50%); font-weight: 400; font-size: 10px; color: var(--ink-3); }}
.lm-ticks b:first-child {{ transform: none; }} .lm-ticks b:last-child {{ transform: translateX(-100%); }}
.sw-dash {{ width: 16px; height: 2px; display: inline-block; background: repeating-linear-gradient(90deg, var(--lab-spread) 0 5px, transparent 5px 8px); }}
.sw-fit {{ width: 16px; height: 1px; display: inline-block; background: var(--ink-2); }}
.sw-dot {{ width: 7px; height: 7px; display: inline-block; border-radius: 50%; background: var(--ink); }}
.be-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr)); gap: 26px 32px; }}
.be-cap {{ margin: 0 0 8px; font-size: 11.5px; line-height: 1.6; color: var(--ink-2); min-height: 4.8em; }}
.be-cap b {{ color: var(--ink); font-weight: 500; }}
.be svg {{ display: block; width: 100%; height: auto; overflow: visible; }}
.be text {{ font-family: var(--mono); }}
.be .tick {{ fill: var(--ink-3); font-size: 9.5px; }}
.be .edge {{ fill: var(--ink-2); font-size: 9.5px; paint-order: stroke; stroke: var(--panel); stroke-width: 3px; stroke-linejoin: round; }}
.be .grid {{ stroke: var(--rule); stroke-width: 1; }}
.be .zero {{ stroke: var(--ink-3); stroke-width: 1; }}
.be .band {{ fill: var(--panel-3); }}
.be .ci-end {{ stroke: var(--ink-3); stroke-width: 1; stroke-dasharray: 3 3; }}
.be .fit {{ stroke: var(--ink-2); stroke-width: 1; }}
.be .cross {{ fill: var(--ink); stroke: var(--panel); stroke-width: 1.5; }}
.ln-net {{ fill: none; stroke: var(--lab-net); stroke-width: 2; }}
.ln-cost {{ fill: none; stroke: var(--lab-spread); stroke-width: 2; stroke-dasharray: 5 3; }}
.dt-net {{ fill: var(--lab-net); stroke: var(--panel); stroke-width: 2; }}
.dt-cost {{ fill: var(--lab-spread); stroke: var(--panel); stroke-width: 2; }}
.hit {{ fill: #fff; fill-opacity: 0; outline: none; cursor: default; }}
.hit:hover, .hit:focus {{ fill-opacity: .05; }}
.hit:focus-visible {{ fill-opacity: .08; stroke: var(--ink-2); stroke-width: 1; }}
table.data th {{ white-space: normal; vertical-align: bottom; }}
table.data td.r, table.data th.r {{ text-align: right; padding-left: 14px; }}
table.data .rg {{ display: block; color: var(--ink-3); font-size: 10px; }}
table.data td.k {{ color: var(--ink); font-weight: 500; }}
table.data td.na {{ color: var(--ink-3); white-space: normal; padding-left: 14px; }}
table.data tr.ab td {{ color: var(--ink-3); }}
table.data tr.ab td:first-child {{ padding-left: 10px; color: var(--ink-2); }}
table.lab-t td:first-child, table.lab-t th:first-child {{ position: sticky; left: 0; background: var(--panel); z-index: 1; }}
table.data.compact {{ min-width: 0; width: auto; }}
table.data.compact td, table.data.compact th {{ padding-right: 36px; }}
table.data.compact th span {{ display: inline-block; max-width: 17ch; }}   /* headers wrap, so the columns close up */
@media (max-width: 620px) {{
  .lm-ticks b:nth-child(even) {{ display: none; }}
  table.lab-t tr.ab .abl {{ display: inline-block; width: 10ch; white-space: normal; }}   /* two lines, so the pinned column stays narrow */
}}
</style>
</head>
<body>
<header class="rail" id="rail"></header>

<main class="paper">

  <section class="masthead">
    <div>
      <h1 class="title">What does a retail seller keep?</h1>
      <p class="dek">A side study to the paper. A one-month at-the-money straddle sold on SPY, QQQ, IWM, GLD and USO every month from {first:%B %Y} to {last:%B %Y}, priced on the real consolidated quotes. On SPY, QQQ and IWM a retail seller kept about {min(eq3):.0f} to {max(eq3):.0f} cents of each paper dollar; crash months and margin calls, not trading costs, were the danger.</p>
    </div>
    <dl class="meta">
      <div><dt>Author</dt><dd class="byline">Gabriel Mitton</dd><dd>Pepperdine University</dd></div>
      <div><dt>Status</dt><dd>Exploratory side study, not one of the paper's registered tests. Finished 14 October 2026, rebuilt by a second implementation on 17 October, corrected after an outside review on 28 October.</dd></div>
      <div><dt>Registration</dt><dd>Rules and predictions committed before any data was bought: <a href="{REPO}/blob/main/lab/REGISTRATION.md">lab/REGISTRATION.md</a></dd></div>
      <div><dt>Data</dt><dd>Option quotes: OPRA. Data provided by Databento. Index closes: Cboe Global Markets. Fund closes: Alpaca. Aggregates only.</dd></div>
    </dl>
  </section>

  <section class="lab-key" aria-label="Key numbers">
    <div class="kpis">{kpis}</div>
    {src}
  </section>

  <section class="section">
    <h2>Costs barely matter on liquid funds. Crashes and margin do.</h2>
    <div class="prose">
      <p>Writing premium equal to 5% of the account each month, a retail seller kept <span class="m">{kept5['SPY']:.0f}</span> cents of each paper dollar on SPY, <span class="m">{kept5['QQQ']:.0f}</span> on QQQ and <span class="m">{kept5['IWM']:.0f}</span> on IWM after spreads and commissions, and <span class="m">{kept5['USO']:.0f}</span> on USO, whose options trade far wider. Gold lost money before any cost, so it had no paper dollar to keep.</p>
      <p>Size changes the picture. At 20% of the account, margin calls came often (SPY in <span class="m">{called20['SPY']}</span> of {n['SPY']} months), each forcing the position to be bought back at a bad moment and reopened smaller, and forced liquidation became the largest leak on {' and '.join(lead20)}. {' '.join(f'On {s} the same rule cut losses that kept growing, so the seller kept <span class="m">{v:.0f}</span> cents per paper dollar, more than the paper trade itself.' for s, v in gained20.items())}</p>
      <p>The real risk is the crash month. Held to expiry at the modest size, the COVID trade ({covid_when}) cost {', '.join(f'{s} <span class="m">{num(-100 * covid[s][2], 1)}%</span>' for s in worst3[:-1])} and {worst3[-1]} <span class="m">{num(-100 * covid[worst3[-1]][2], 1)}%</span> of the account. Over ten simulated years, the chance of equity falling below half its starting value runs from <span class="m">{ruin[0][0]:.1f}%</span> ({ruin[0][1]}) to <span class="m">{ruin[-1][0]:.1f}%</span> ({ruin[-1][1]}).</p>
    </div>
    <aside class="aside">
      <div><b>The trade.</b> One short at-the-money straddle a month per fund, entered at 2:30 p.m. New York (11:30 a.m. on half-days) on the first trading day after each monthly expiry, held to the next one ({hmin} to {hmax} days) and settled on the fund's close. The first entry was on {day(first)}, the last on {day(last)}, expiring {day(last_exp)}.</div>
      <div><b>Paper dollar.</b> One dollar of the trade's return at the mid price, before any cost: the yardstick for what is kept.</div>
      <div><b>Retail costs.</b> 80% of the quoted half-spread on every trade, after Muravyev and Pearson (2020), and $0.65 a contract per leg.</div>
      <div><b>Margin limits.</b> At entry the position is cut, if need be, so the margin it needs beyond the premium taken in stays within 90% of the account.</div>
      <div><b>Forced liquidation.</b> On any day the account cannot meet the margin requirement, the whole position is bought back at that day's mark and reopened smaller at the same strike.</div>
      <div><b>Leaks.</b> Each friction's share is its Shapley value: its average effect over all 24 orders in which the four frictions can be switched on.</div>
    </aside>
    <figure class="fig" id="fig1">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Fig. 1</span><h2 class="fig-title">The Leak Map: cents kept of each paper dollar, premium 5% of the account</h2></div>
        <div class="fig-tools">
          <div class="legend">
            <span><i class="sw-sq" style="background:var(--lab-kept)"></i>kept</span>
            <span><i class="sw-sq" style="background:var(--lab-spread)"></i>spreads</span>
            <span><i class="sw-sq" style="background:var(--lab-comm)"></i>commissions</span>
          </div>
        </div>
        <div class="fig-body">
          {leak_map(leak, added)}
          <details class="tv"><summary>Show the numbers as a table</summary><div class="tv-wrap">{leak_table(leak, be, "0.05", added)}</div></details>
        </div>
      </div>
      <figcaption class="fig-cap">
        <p>Each bar is one dollar of paper return: the straddle traded at the mid price, with no costs. Grey is what a retail seller kept; the coloured parts are the leaks. At this size margin never binds, so the two margin frictions are exactly zero and every order of the frictions gives the same shares. {added_note} Hover over or tap a bar for its numbers.</p>
        <div class="src">Months traded: {months}, entered {first:%B %Y} to {last:%B %Y}; months that failed the registered data checks are left out (below, under limits), and the table adds them back beneath the registered rows.<br>{esc(CREDIT)}</div>
      </figcaption>
    </figure>
    <figure class="fig">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Table 1</span><h2 class="fig-title">At 20% of the account, margin decides</h2></div>
        <div class="fig-body"><div class="tv-wrap" style="margin-top:0">{leak_table(leak, be, "0.2", added)}</div></div>
      </div>
      <figcaption class="fig-cap">
        <p>Cents per dollar of paper return; each row sums to 100, kept plus the four shares. A positive share is a leak; a negative one means that friction added to what was kept. At this size the frictions interact, so the shares depend on the order in which they are switched on: below each share, the lowest and highest it takes across the 24 orders. The margin shares swing widely. Rows marked "all" put back the months that failed the registered data checks, where they can still be traded; the registered rows are the result.</p>
        {src}
      </figcaption>
    </figure>
  </section>

  <section class="section">
    <h2>What free data gets wrong about the cost</h2>
    <div class="prose">
      <p>Someone pricing these trades from a free feed would misjudge the spread cost, because on these funds the free feed's quotes run wider than the consolidated market's: from {100 * (ratio[rlo] - 1):.0f}% wider on {rlo} to {ratio[rhi]:.1f} times as wide on {rhi}. Using the ratio measured between the two feeds from 17 September to 9 October 2026, and assuming it held for ten years, the free-data user overstates the spread leak by <span class="m">{over['SPY']:.1f}</span> cents per dollar on SPY, <span class="m">{over['QQQ']:.1f}</span> on QQQ, <span class="m">{over['IWM']:.1f}</span> on IWM and <span class="m">{over['USO']:.1f}</span> on USO. It is an error in the estimate only, never subtracted as cash.</p>
    </div>
    <figure class="fig">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Table 2</span><h2 class="fig-title">The spread leak on real quotes and as a free feed would show it, premium 5% of the account</h2></div>
        <div class="fig-body"><div class="tv-wrap" style="margin-top:0"><table class="data compact"><thead><tr><th>Fund</th><th class="r"><span>Real quotes (OPRA), ¢</span></th><th class="r"><span>Free-feed estimate, ¢</span></th><th class="r"><span>Overstated by, ¢</span></th><th class="r"><span>Free/OPRA spread ratio</span></th></tr></thead><tbody>{free_data_rows(leak)}</tbody></table></div></div>
      </div>
      <figcaption class="fig-cap">
        <p>Cents per dollar of paper return. The ratio is the free feed's median at-the-money half-spread over OPRA's at the same minute, 17 September to 9 October 2026, from the pilot of the paper's planned free-feed test (H8). GLD has no paper profit to measure against.</p>
        {src}
      </figcaption>
    </figure>
  </section>

  <section class="section">
    <h2>No reliable break-even level, and costs are not what moves it</h2>
    <div class="prose">
      <p>If costs rose fast enough with fear, there would be an index level above which selling stopped paying. Grouped by each fund's own volatility index, the monthly result net of the spread cost swings by several volatility points from one group to the next (SPY's middle three groups: <span class="m">{num(spy_mid[0], 2, True)}</span>, <span class="m">{num(spy_mid[1], 2, True)}</span>, <span class="m">{num(spy_mid[2], 2, True)}</span>), while the spread cost stays at or below <span class="m">{eq_peak:.2f}</span> of a point on the equity funds and peaks at <span class="m">{peak['USO']:.1f}</span> on USO, the widest market here. A straight line fitted through the months crosses zero {fit_txt}, but {ci_txt}, and <span class="m">{out_share[0]:.0f}</span> to <span class="m">{out_share[-1]:.0f}%</span> of resamples cross outside the data altogether. There is no reliable break-even.</p>
    </div>
    <aside class="aside">
      <div><b>Volatility points.</b> A month's profit at the mid price divided by the straddle's vega at entry, less the spread cost, so that every fund sits on one scale.</div>
      <div><b>The line.</b> Least squares through all of a fund's months, not through the five group means; months beyond the axis pull it too.</div>
    </aside>
    <figure class="fig" id="fig2">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Fig. 2</span><h2 class="fig-title">Monthly result and spread cost, in volatility points, by the fund's own index</h2></div>
        <div class="fig-tools">
          <div class="legend">
            <span><i class="sw-line" style="background:var(--lab-net)"></i>net result, after spread cost</span>
            <span><i class="sw-dash"></i>spread cost alone</span>
            <span><i class="sw-fit"></i>fitted line</span>
            <span><i class="sw-dot"></i>where it crosses zero</span>
            <span><i class="sw-sq" style="background:var(--panel-3);outline:1px solid var(--rule-2)"></i>90% interval of the crossing</span>
          </div>
        </div>
        <div class="fig-body"><div class="be-grid">{be_cards}</div>
          <details class="tv"><summary>Show the numbers as a table</summary><div class="tv-wrap">{be_table(be)}</div></details>
        </div>
      </div>
      <figcaption class="fig-cap">
        <p>Each point is the mean of one fifth of the observations, grouped by the fund's index at the previous close: {gaps[0]} monthly trades for the net result, {gaps[1]} weekly samples for the cost. The shaded interval and its dashed ends come from 2,000 stationary-bootstrap resamples; the axis spans the group means, so an interval end or a crossing beyond it is written at the edge with an arrow. Each panel has its own scales. Registered months only: this analysis was not rerun with the excluded months added back. Hover over or tap a column for its numbers.</p>
        {src}
      </figcaption>
    </figure>
  </section>

  <section class="section">
    <h2>Ten simulated years at the modest size</h2>
    <div class="prose">
      <p>Resampling the real monthly results into 10,000 ten-year paths shows what a decade of selling could feel like at 5% of the account, after spreads and commissions. The odds are conditional on the crashes that 2016 to 2026 happened to contain.</p>
    </div>
    <figure class="fig">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Table 3</span><h2 class="fig-title">Ten simulated years, premium 5% of the account</h2></div>
        <div class="fig-body"><div class="tv-wrap" style="margin-top:0"><table class="data compact lab-t"><thead><tr><th>Fund</th><th class="r"><span>Worst drawdown, median path, %</span></th><th class="r"><span>Worst drawdown, 1 path in 20, %</span></th><th class="r"><span>Chance equity falls below half its start, %</span></th><th class="r"><span>Worst actual month, %</span></th></tr></thead><tbody>{stress_rows(st, p3plan["stress"])}</tbody></table></div></div>
      </div>
      <figcaption class="fig-cap">
        <p>A stationary bootstrap of the registered monthly results (block length one month for every fund, chosen by the Patton, Politis and White rule), 10,000 paths of 120 months. The drawdowns are each path's largest fall from a peak; 1 path in 20 falls further than the second column. The chance counts paths whose equity drops below half its starting value at any point within the ten years, a different event from a 50% fall from a later peak. The worst actual month is the worst single month in the data, not simulated. Rows marked "all" put back the excluded months: GLD's tail is materially worse with its {p3plan["stress"]["GLD"]["n"] - n["GLD"]} gold-rally months back, USO's barely moves.</p>
        {src}
      </figcaption>
    </figure>
  </section>

  <section class="section">
    <h2>Predictions, written before any data was bought</h2>
    <figure class="fig" style="margin-top:0">
      <div class="fig-frame">
        <div class="fig-head"><span class="fig-no">Table 4</span><h2 class="fig-title">Five predictions, registered before any data was bought</h2></div>
        <div class="fig-body"><div class="ledger-wrap"><table class="ledger"><thead><tr><th></th><th>Prediction, as registered</th><th>Result</th><th>Evidence</th></tr></thead><tbody>{p_table}</tbody></table></div></div>
      </div>
      <figcaption class="fig-cap"><p>Each verdict is as logged in the registration, which also records every amendment and correction since; the page refuses to render if the summaries would judge one differently.</p>{src}</figcaption>
    </figure>
  </section>

  <section class="section">
    <h2>What this cannot show</h2>
    <ul class="limits">
      <li><b>The cost fractions are borrowed.</b> 80% of the quoted half-spread comes from Muravyev and Pearson's study of single-stock options (2020). A working paper on retail option trading (Bogousslavsky and Muravyev) suggests retail traders often avoid paying the spread, so this case is probably pessimistic.</li>
      <li><b>Most daily marks are model prices.</b> Outside the registered stress months, positions are marked with Black-76 at the fund's own Cboe index level, which misses the smile. The stress months, where margin calls cluster, use real OPRA quotes.</li>
      <li><b>One trade a month, held to expiry.</b> Early exercise of these American options is ignored, and nothing is rolled or hedged.</li>
      <li><b>Excluded months cluster in crashes.</b> Months that failed the registered data checks are left out. Added back, they make gold's result worse (from <span class="m">{num(sens['GLD'][0], 1, True)}</span> to <span class="m">{num(sens['GLD'][1], 1, True)}</span> cents per dollar of premium at mid) but not oil's: USO earns <span class="m">{num(sens['USO'][1], 1, True)}</span> instead of <span class="m">{num(sens['USO'][0], 1, True)}</span>, once the one trade held across its 2020 reverse split is settled on the adjusted contract.</li>
      <li><b>The free-data error assumes a constant ratio.</b> It was measured over three weeks in 2026 and applied to ten years.</li>
      <li><b>Nothing here touches a registered result.</b> The paper's hypotheses and verdicts are unchanged by this study.</li>
    </ul>
    <div class="src" style="grid-column:1;margin-top:16px">{esc(CREDIT)}</div>
  </section>

  <section class="section">
    <h2>Data sources</h2>
    <ul class="limits">
      <li><b>OPRA.</b> Consolidated best bid and offer, one-minute bars, bought historically from Databento, Inc. Data provided by Databento. Derived aggregates only: no quote or price is reproduced here, and none is stored in the public repository.</li>
      <li><b>Volatility indices.</b> VIX, VXN, RVX, GVZ and OVX daily closes: Cboe Global Markets, used with Cboe's permission (granted 4 November 2026).</li>
      <li><b>Fund closes.</b> Alpaca Markets, for personal, non-commercial research use.</li>
    </ul>
  </section>

  <footer class="inst-foot">
    <span>Gabriel Mitton, Pepperdine University</span>
    <a href="../">The paper</a>
    <a href="monitor.html">The instrument</a>
    <a href="{REPO}/blob/main/lab/REGISTRATION.md">The registration</a>
    <a href="{REPO}/tree/main/lab">The code</a>
    <span>Exploratory. Aggregates only.</span>
  </footer>
</main>

<script src="volrec.js"></script>
<script>
(function () {{
  "use strict";
  const $ = id => document.getElementById(id);
  const LINKS = {links};
  V.rail($("rail"), {{ home: "../", here: "lab", state: "loading", links: LINKS }});
  document.querySelectorAll("[data-tip]").forEach(el => {{
    const d = JSON.parse(el.getAttribute("data-tip"));
    V.hover(el, () => [d[0], d[1].map(r => ({{ v: r[0], k: r[1], c: r[2] }}))]);
  }});
  (async function () {{
    const [a, s] = await Promise.all([V.load("data/iv_history.csv", "../"), V.load("data/surface.csv", "../")]);
    if (!a.rows) {{ V.rail($("rail"), {{ home: "../", here: "lab", state: "offline", links: LINKS }}); return; }}
    const h = V.health(a.rows, s.rows), days = V.days(a.rows);
    V.rail($("rail"), {{ home: "../", here: "lab", state: h.atm.state === "ok" ? "live" : "stale", links: LINKS,
      days: days.length, rows: a.rows.length, snapshot: V.lastSnapshot(a.rows), surface: h.surface }});
  }})();
}})();
</script>
</body>
</html>
"""


def render():
    """The page from the private summaries; None only when none of them is on this machine (a fresh clone, CI).
    Some present and some missing is a broken setup, not a fresh clone, and stops with the names missing."""
    have = [f for f in INPUTS if (OUT_DIR / f).exists()]
    if not have:
        return None
    if len(have) < len(INPUTS):
        raise SystemExit(f"lab summaries incomplete in {OUT_DIR}: missing "
                         + ", ".join(f for f in INPUTS if f not in have))
    leak = json.loads((OUT_DIR / "leak_summary.json").read_text())
    be = json.loads((OUT_DIR / "breakeven_summary.json").read_text())
    with open(OUT_DIR / "trades.csv", newline="") as f:
        trades = list(csv.DictReader(f))
    return page(leak, be, trades, plan3((OUT_DIR / "report-plan3.txt").read_text(), leak))


def main(argv):
    out = render()
    if out is None:
        print(f"no lab summaries in {OUT_DIR}: nothing to render")
        return 2
    if "--check" in argv:
        same = PAGE.exists() and PAGE.read_text(encoding="utf-8") == out
        print("tools/lab.html matches the summaries" if same else
              "tools/lab.html DIFFERS from the summaries: run lab/report.py")
        return 0 if same else 1
    PAGE.write_text(out, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
