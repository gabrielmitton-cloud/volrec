#!/usr/bin/env python3
"""lab/ - the retail implementation audit's report (EXPLORATORY). Reads the JSON summaries written by
run_leak.py and run_breakeven.py and renders one self-contained HTML page with inline SVG charts:
the Leak Map and the Break-Even curves. Aggregates only; kept in the private folder until Cboe's
permission reply.

  FRED_KEY=use-cache python lab/report.py      # -> ~/Documents/volrec-licensed/lab-out/report.html
"""
import html
import json
import sys
from pathlib import Path

OUT_DIR = Path.home() / "Documents" / "volrec-licensed" / "lab-out"
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
LEAKS = ("spreads", "limits", "liquidation", "commissions")
LEAK_COLOR = {"spreads": "var(--c1)", "limits": "var(--c2)", "liquidation": "var(--c3)", "commissions": "var(--c4)"}
CREDIT = ("Data provided by Databento (OPRA consolidated NBBO). Cboe index levels: Cboe Global Markets. "
          "Fund closes: Alpaca Markets (personal, non-commercial use). Aggregates only.")


def leak_chart(leak):
    """Cents kept per $1 of paper return, by fund, at 5% and 20% size; positive leaks stacked after
    the kept bar (Shapley shares). Funds with a non-positive paper return are listed, not drawn."""
    rows = [(s, w) for s in FUNDS for w in ("0.05", "0.2") if leak[s]["weights"][w]["paper"] > 0]
    W, L, bar, gap = 440, 92, 22, 9               # a narrow canvas keeps labels legible on a phone
    H = 30 + len(rows) * (bar + gap) + 40
    def reach(s, w):
        d = leak[s]["weights"][w]
        return 100 * d["kept"] / d["paper"] + sum(max(0.0, 100 * d["leaks"][p][0] / d["paper"]) for p in LEAKS)
    top = max(110.0, max(reach(s, w) for s, w in rows) + 5)   # kept can pass 100 when liquidation helped
    sc = (W - L - 20) / top
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Leak Map: cents kept per dollar of paper return">',
           f'<line x1="{L}" y1="20" x2="{L}" y2="{H - 30}" class="axis"/>']
    for t in [v for v in (0, 25, 50, 75, 100, 125, 150) if v <= top]:
        x = L + t * sc
        out.append(f'<line x1="{x:.1f}" y1="20" x2="{x:.1f}" y2="{H - 30}" class="grid"/>'
                   f'<text x="{x:.1f}" y="{H - 14}" class="tick" text-anchor="middle">{t}¢</text>')
    y = 30
    for s, w in rows:
        d = leak[s]["weights"][w]
        kept = 100 * d["kept"] / d["paper"]
        out.append(f'<text x="{L - 8}" y="{y + bar * 0.72:.1f}" class="lab" text-anchor="end">{s} {int(float(w) * 100)}%</text>')
        out.append(f'<rect x="{L}" y="{y}" width="{max(kept, 0) * sc:.1f}" height="{bar}" class="kept"><title>{s} {int(float(w) * 100)}%: keeps {kept:.1f} cents</title></rect>')
        x = L + max(kept, 0) * sc
        for p in LEAKS:
            share = 100 * d["leaks"][p][0] / d["paper"]
            if share > 0.05:
                out.append(f'<rect x="{x:.1f}" y="{y}" width="{share * sc:.1f}" height="{bar}" fill="{LEAK_COLOR[p]}">'
                           f'<title>{p}: {share:.1f} cents</title></rect>')
                x += share * sc
        out.append(f'<text x="{L + max(kept, 0) * sc - 4:.1f}" y="{y + bar * 0.72:.1f}" class="val" text-anchor="end">{kept:.0f}¢</text>')
        y += bar + gap
    out.append("</svg>")
    return "".join(out)


def be_chart(sym, d):
    W, H, L, B, T, R = 300, 190, 44, 34, 14, 10
    xs = [b[0] for b in d["net_bins"]] + [b[0] for b in d["cost_bins"]]
    ys = [b[1] for b in d["net_bins"]] + [b[1] for b in d["cost_bins"]] + [0.0]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys) - 0.5, max(ys) + 0.5
    X = lambda v: L + (v - x0) / (x1 - x0 or 1) * (W - L - R)
    Y = lambda v: T + (y1 - v) / (y1 - y0 or 1) * (H - T - B)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{sym}: net volatility points by {d["index"]} quintile">',
         f'<line x1="{L}" y1="{Y(0):.1f}" x2="{W - R}" y2="{Y(0):.1f}" class="zero"/>',
         f'<text x="{L - 4}" y="{Y(0) + 4:.1f}" class="tick" text-anchor="end">0</text>']
    for v in (y0 + 0.5, y1 - 0.5):
        o.append(f'<text x="{L - 4}" y="{Y(v) + 4:.1f}" class="tick" text-anchor="end">{v:+.0f}</text>')
    for nm, key in (("net", "net_bins"), ("cost", "cost_bins")):
        pts = " ".join(f"{X(b[0]):.1f},{Y(b[1]):.1f}" for b in d[key])
        o.append(f'<polyline points="{pts}" class="{nm}"/>')
        for b in d[key]:
            o.append(f'<circle cx="{X(b[0]):.1f}" cy="{Y(b[1]):.1f}" r="3.5" class="{nm}dot">'
                     f'<title>{d["index"]} {b[0]:.1f}: {nm} {b[1]:+.3f} pts (n={b[2]})</title></circle>')
    for v in (x0, x1):
        o.append(f'<text x="{X(v):.1f}" y="{H - 16}" class="tick" text-anchor="middle">{v:.0f}</text>')
    o.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 3}" class="tick" text-anchor="middle">{d["index"]}, previous close (quintile means)</text>')
    o.append("</svg>")
    return "".join(o)


def free_data_rows(leak):
    """Spec Q6: what a free-data user would think the spreads cost, using H8's pilot free/OPRA ratio."""
    import importlib.util as _u
    s = _u.spec_from_file_location("engine", Path(__file__).resolve().parent / "engine.py")
    eng = _u.module_from_spec(s)
    s.loader.exec_module(eng)
    out = []
    for f in FUNDS:
        w = leak[f]["weights"]["0.05"]
        if w["paper"] > 0:
            true_c = 100 * w["leaks"]["spreads"][0] / w["paper"]
            est = true_c * eng.PILOT[f][2]
            out.append(f"<tr><td>{f}</td><td>{true_c:.1f}¢</td><td>{est:.1f}¢</td><td>{est - true_c:+.1f}¢</td></tr>")
    return "".join(out)


def page(leak, be):
    stress_rows = "".join(
        f"<tr><td>{s}</td><td>{100 * leak[s]['stress']['dd50']:.0f}%</td><td>{100 * leak[s]['stress']['dd95']:.0f}%</td>"
        f"<td>{100 * leak[s]['stress']['ruin']:.1f}%</td><td>{100 * leak[s]['stress']['worst']:+.1f}%</td></tr>" for s in FUNDS)
    be_cards = "".join(
        f'<figure><figcaption><b>{s}</b> · '
        + (f"line crosses at {be[s]['index']} {be[s]['crossing']:.0f}, but 90% of resamples span "
           f"{be[s]['ci'][0]:.0f}-{be[s]['ci'][1]:.0f} and {100 * be[s]['out'] / 2000:.0f}% cross outside the data"
           if be[s]["crossing"] is not None and be[s]["ci"] else "no break-even in range")
        + f"</figcaption>{be_chart(s, be[s])}</figure>" for s in FUNDS)
    undrawn = ", ".join(s for s in FUNDS if leak[s]["weights"]["0.05"]["paper"] <= 0)
    legend = " ".join(f'<span class="key"><i style="background:{LEAK_COLOR[p]}"></i>{p}</span>' for p in LEAKS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Retail Volatility Audit</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1c1a;--mut:#6b6862;--line:#d9d5cc;--kept:#2f6f5e;--c1:#d08a2e;--c2:#7b6bb0;--c3:#c2493d;--c4:#8c8c8c;--net:#2f5f9e;--cost:#c2493d}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#151514;--fg:#ecebe7;--mut:#a29f98;--line:#3a3935;--kept:#5fb39b;--c1:#e3a24f;--c2:#a497d6;--c3:#e2766b;--c4:#a5a5a5;--net:#7aa7e0;--cost:#e2766b}}}}
:root[data-theme="dark"]{{--bg:#151514;--fg:#ecebe7;--mut:#a29f98;--line:#3a3935;--kept:#5fb39b;--c1:#e3a24f;--c2:#a497d6;--c3:#e2766b;--c4:#a5a5a5;--net:#7aa7e0;--cost:#e2766b}}
body{{background:var(--bg);color:var(--fg);font:16px/1.55 Georgia,'Iowan Old Style',serif;margin:0;padding:0 16px}}
main{{max-width:760px;margin:0 auto;padding:32px 0 48px}}h1{{font-size:1.9rem;line-height:1.2;margin:0 0 6px}}
h2{{font:600 1.05rem/1.3 system-ui,sans-serif;margin:36px 0 8px;letter-spacing:.01em}}.sub{{color:var(--mut);font-family:system-ui,sans-serif;font-size:.85rem}}
.answer{{border-left:3px solid var(--kept);padding:4px 0 4px 14px;margin:20px 0}}svg{{width:100%;height:auto;display:block}}
svg text{{fill:var(--fg);font:13px system-ui,sans-serif}}.tick{{fill:var(--mut);font-size:12px}}.grid{{stroke:var(--line);stroke-width:1}}
.axis,.zero{{stroke:var(--mut);stroke-width:1}}.kept{{fill:var(--kept)}}.val{{fill:#fff;font-weight:600}}
.net{{fill:none;stroke:var(--net);stroke-width:2}}.cost{{fill:none;stroke:var(--cost);stroke-width:2;stroke-dasharray:4 3}}
.netdot{{fill:var(--net)}}.costdot{{fill:var(--cost)}}.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}}
figure{{margin:0}}figcaption{{font:13px system-ui,sans-serif;color:var(--mut);margin-bottom:4px}}
table{{border-collapse:collapse;width:100%;font:14px system-ui,sans-serif}}td,th{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right}}
td:first-child,th:first-child{{text-align:left}}.key{{display:inline-flex;align-items:center;gap:6px;margin-right:14px;font:13px system-ui,sans-serif}}
.key i{{width:12px;height:12px;display:inline-block;border-radius:2px}}footer{{color:var(--mut);font:12px system-ui,sans-serif;margin-top:40px}}
.tw{{overflow-x:auto}}
</style></head><body><main>
<p class="sub">volrec · lab/ · exploratory side project · private until Cboe's reply</p>
<h1>How much of the volatility premium does a retail investor keep?</h1>
<p class="sub">Short one-month at-the-money straddles on SPY, QQQ, IWM, GLD and USO, every month from January 2016 to August 2026, priced on real OPRA quotes and settled on the funds' closes.</p>
<div class="answer"><p><b>Costs barely matter on liquid funds; crashes and margin do.</b> At a modest size a retail seller keeps 90-95 cents of each paper dollar on SPY, QQQ and IWM, and 58 on USO; gold lost money before any cost. At larger sizes margin calls become the biggest leak, and a single month (the COVID crash) cost a quarter to a third of the account at the modest size. No fear level emerges at which costs eat the premium.</p></div>
<h2>The Leak Map: cents kept per $1 of paper return</h2>
<p class="sub">Premium written = 5% or 20% of the account. Leaks are Shapley shares over all 24 orders of the frictions. {('Not drawn (no paper profit to keep): ' + undrawn + '.') if undrawn else ''} A negative leak (forced liquidation sometimes cut losses) is left out of the bar and reported in the registration.</p>
<div>{legend}<span class="key"><i style="background:var(--kept)"></i>kept</span></div>
{leak_chart(leak)}
<h2>What free data gets wrong about the cost</h2>
<p class="sub">Spreads' share of each paper dollar on real (OPRA) quotes, against what a user pricing from the free feed would estimate (its quotes run wider; ratio measured 17 Sep - 9 Oct 2026 and assumed constant). Estimate error only - never subtracted as cash.</p>
<div class="tw"><table><tr><th>Fund</th><th>True (OPRA)</th><th>Free-data estimate</th><th>Misjudged by</th></tr>{free_data_rows(leak)}</table></div>
<h2>The Break-Even VIX: no reliable crossing</h2>
<p class="sub">Solid: the straddle's net result (P&amp;L / vega, minus retail cost) in volatility points, by quintile of the fund's own index. Dashed: the retail cost alone. Costs stay near zero beside swings of several points.</p>
<div class="grid2">{be_cards}</div>
<h2>Ten simulated years at the modest size</h2>
<div class="tw"><table><tr><th>Fund</th><th>Median worst drawdown</th><th>95th percentile</th><th>Chance of losing half</th><th>Worst month</th></tr>{stress_rows}</table></div>
<p class="sub">Stationary bootstrap of the real monthly results, 10,000 paths; odds are conditional on 2016-2026's crashes.</p>
<h2>Predictions, written before the data</h2>
<div class="tw"><table><tr><th>Prediction</th><th>Result</th></tr>
<tr><td>P1 Retail keeps under half on at least 3 of 5 funds</td><td>Fails (keeps 58-95 cents)</td></tr>
<tr><td>P2 Spreads are the largest leak on at least 3 of 5</td><td>Holds as written; only because margin never binds at 5%</td></tr>
<tr><td>P3 The full strip costs at least twice the ATM estimate</td><td>Holds on 5 of 5 (2.1-3.4x)</td></tr>
<tr><td>P4 Cost as a share of premium rises with fear on 4 of 5</td><td>Fails (1 of 5, gold)</td></tr>
<tr><td>P5 Retention highest on SPY, lowest on USO</td><td>Holds among funds with a paper profit</td></tr></table></div>
<h2>Limits</h2>
<p>Cost fractions (80% and 30% of the quoted half-spread) are borrowed from Muravyev &amp; Pearson's single-stock study. Daily marks outside the stress months are model prices at the fund's own index level. One trade a month, held to expiry; American exercise ignored. Excluded months cluster in crashes: with them added back, USO's and GLD's results turn worse (shown in the registration).</p>
<footer>{html.escape(CREDIT)}</footer>
</main></body></html>"""


def main():
    leak = json.load(open(OUT_DIR / "leak_summary.json"))
    be = json.load(open(OUT_DIR / "breakeven_summary.json"))
    out = OUT_DIR / "report.html"
    out.write_text(page(leak, be))
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
