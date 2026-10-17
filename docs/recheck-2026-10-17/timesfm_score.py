"""Re-score the saved TimesFM benchmark (analysis/out/timesfm_vix_baseline.csv) without re-running any model (FRED's
terms; CLAUDE.md), and re-derive every target - the mean of log VIX over the next 21 trading days - from the saved file."""
import csv, math, os, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
rows = list(csv.DictReader(open(ROOT / "analysis/out/timesfm_vix_baseline.csv"))); a = [float(r["actual"]) for r in rows]
def stats(k):
    e = sorted(abs(float(r[k]) - x) for r, x in zip(rows, a)); return math.sqrt(sum(v * v for v in e) / len(e)), sum(e) / len(e), st.median(e), e[-1]
for k in ("rw", "har", "timesfm"):
    print(f"{k:8} RMSE {stats(k)[0]:.4f}  MAE {stats(k)[1]:.4f}  median {stats(k)[2]:.4f}  max {stats(k)[3]:.4f}")
gain = 1 - stats("timesfm")[0] / stats("har")[0]
wins = sum(abs(float(r["timesfm"]) - x) < abs(float(r["har"]) - x) for r, x in zip(rows, a)) / len(rows)
print(f"{len(rows)} origins: RMSE gain {gain:+.1%}, TimesFM wins {wins:.1%} (bar: +5% and 55%)")
v = [(r.get("observation_date") or r.get("DATE"), r["VIXCLS"]) for r in csv.DictReader(open(ROOT / "analysis/data/VIXCLS.csv"))]
v = [(d, float(x)) for d, x in v if x not in ("", ".")]; pos = {d: i for i, (d, _) in enumerate(v)}
ok = sum(any(abs(sum(math.log(v[j][1]) for j in range(pos[r["date"]] + o, pos[r["date"]] + o + 21)) / 21 - x) < 1e-9 for o in (0, 1)) for r, x in zip(rows, a))
print(f"targets re-derived from the saved data: {ok} of {len(rows)}")
