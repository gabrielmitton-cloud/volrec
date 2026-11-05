#!/usr/bin/env python3
"""The three link-preview images (og/home.png, og/monitor.png, og/lab.png; 1200x630), drawn by headless Chrome
from fixed text in the site's own colours (tools/volrec.css) and fonts. No data and no verdict: a shared link
shows what the page is, never a result. Built 5 Nov 2026; the pages name the images in their og:image tags.

  python tools/og_cards.py        # rewrites the three images (needs Google Chrome and the network, for the fonts)
"""
import html
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SITE = "gabrielmitton-cloud.github.io/volrec"
CARDS = {
    "home": ("Working paper · live data", "What Free Options Data Costs",
             "A zero-budget measurement of free, retail-grade option quotes against Cboe’s published volatility "
             "indices."),
    "monitor": ("The instrument", "The live recorder",
                "Daily implied volatility for 109 tickers and the strike surface for eight, read straight from the "
                "repository."),
    "lab": ("Side study", "What a retail seller keeps",
            "How much of the volatility premium a retail seller of fund straddles keeps after spreads, commissions "
            "and margin, 2016 to 2026."),
}
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Martian+Mono:wdth,wght@75..112.5,300..700&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&display=block">
<style>
html,body{{margin:0;width:1200px;height:630px;background:#000;overflow:hidden}}
.card{{box-sizing:border-box;width:1200px;height:630px;padding:62px 72px 54px;display:flex;flex-direction:column;
  position:relative;background:#000;
  background-image:linear-gradient(#0d1a22 1px,transparent 1px),linear-gradient(90deg,#0d1a22 1px,transparent 1px);
  background-size:60px 60px;background-position:-1px -1px}}
.bar{{position:absolute;left:0;top:0;width:100%;height:6px;display:flex}} .bar i{{flex:1}}
.brand{{display:flex;align-items:center;gap:14px;font:500 20px/1 "Martian Mono",monospace;letter-spacing:.18em;
  text-transform:uppercase;color:#9eacb8}}
.kicker{{margin-top:54px;font:500 20px/1 "Martian Mono",monospace;letter-spacing:.14em;text-transform:uppercase;
  color:#2396C4}}
h1{{margin:22px 0 0;font:500 76px/1.04 "Newsreader",serif;color:#e8eef3;letter-spacing:-.01em;max-width:1040px}}
p{{margin:26px 0 0;font:400 32px/1.36 "Newsreader",serif;color:#c5cfd7;max-width:980px}}
.foot{{margin-top:auto;padding-top:22px;border-top:1px solid #25323e;display:flex;justify-content:space-between;
  font:400 17px/1 "Martian Mono",monospace;letter-spacing:.04em;color:#6e7c8a;background:#000;gap:40px}}
</style></head><body><div class="card">
<div class="bar"><i style="background:#2396C4"></i><i style="background:#B08500"></i><i style="background:#CF4F97"></i></div>
<div class="brand"><svg width="36" height="36" viewBox="0 0 32 32"><rect width="32" height="32" fill="#000"
 stroke="#25323e"/><path d="M3 23C9 23 11 8 16 8s7 15 13 15" fill="none" stroke="#2396C4" stroke-width="2.6"/></svg>volrec</div>
<div class="kicker">{kicker}</div><h1>{title}</h1><p>{sub}</p>
<div class="foot"><span>Gabriel Mitton · Pepperdine University</span><span>{site}</span></div>
</div></body></html>"""


def main():
    out = ROOT / "og"
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, (kicker, title, sub) in CARDS.items():
            src = Path(tmp) / f"{name}.html"
            src.write_text(PAGE.format(kicker=html.escape(kicker), title=html.escape(title), sub=html.escape(sub),
                                       site=SITE))
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--force-device-scale-factor=1", "--window-size=1200,630", "--virtual-time-budget=10000",
                            f"--user-data-dir={tmp}/profile", f"--screenshot={out / (name + '.png')}",
                            src.as_uri()], check=True, capture_output=True)
            print(f"  og/{name}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
