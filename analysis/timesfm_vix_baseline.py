"""
TimesFM as a zero-shot benchmark on the LONG validation sample (FRED VIXCLS).

Question: does a pretrained forecaster beat HAR at predicting the average
VIX over the next 21 trading days? If it can't beat HAR here, with 30+ years
of data, it has no business near the live panel.

Guardrail (from volrec-data-layer-brief.md): this runs on FRED history only.
Do not point it at data/iv_history.csv -- the live panel has too few
independent episodes to evaluate a forecaster.

Pre-registered rule: TimesFM earns a place in the write-up only if it beats
HAR on log-RMSE by >= 5% AND wins in at least 55% of origins. Otherwise report
it as a negative result (still a good interview story).

Setup (inside volrec's venv, NOT global):
    pip install "timesfm[torch]" pandas requests
    python analysis/timesfm_vix_baseline.py              # full run
    python analysis/timesfm_vix_baseline.py --no-timesfm # baselines only, no model download

Uses TimesFM 2.5 weights (Apache-2.0). The 3.0 weights are non-commercial only.
"""

import argparse
import io
import os

import numpy as np
import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
H = 21          # forecast horizon, trading days
CONTEXT = 1024  # TimesFM context length used per origin


def load_vix(cache="analysis/data/VIXCLS.csv"):
    if os.path.exists(cache):
        df = pd.read_csv(cache)
    else:
        import requests
        r = requests.get(FRED_URL, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        df.to_csv(cache, index=False)
    date_col = "observation_date" if "observation_date" in df.columns else df.columns[0]
    s = pd.to_numeric(df["VIXCLS"], errors="coerce")   # FRED marks gaps with "."
    s.index = pd.to_datetime(df[date_col])
    return s.dropna()


def har_features(logv):
    """Corsi HAR on log VIX: yesterday, past-week mean, past-month mean."""
    d = logv
    w = logv.rolling(5).mean()
    m = logv.rolling(22).mean()
    return pd.concat([d, w, m], axis=1, keys=["d", "w", "m"])


def har_forecast(logv, origin_idx):
    """Fit on data strictly before the origin; predict mean log VIX over next H days."""
    X = har_features(logv)
    y = logv[::-1].rolling(H).mean()[::-1].shift(-1)       # mean of t+1..t+H
    train = pd.concat([X, y.rename("y")], axis=1).iloc[:origin_idx - H].dropna()
    A = np.column_stack([np.ones(len(train)), train[["d", "w", "m"]].values])
    beta, *_ = np.linalg.lstsq(A, train["y"].values, rcond=None)
    x0 = X.iloc[origin_idx]
    return float(beta @ np.r_[1.0, x0.values])


def timesfm_forecasts(logv, origins):
    import timesfm
    import torch
    torch.set_float32_matmul_precision("high")
    model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    model.compile(timesfm.ForecastConfig(
        max_context=CONTEXT, max_horizon=64, normalize_inputs=True,
        use_continuous_quantile_head=True, fix_quantile_crossing=True,
    ))
    vals = logv.values
    inputs = [vals[max(0, i - CONTEXT + 1): i + 1] for i in origins]
    preds = []
    for k in range(0, len(inputs), 64):                    # batch to keep memory sane
        point, _ = model.forecast(horizon=H, inputs=inputs[k:k + 64])
        preds.extend(np.asarray(point).mean(axis=1).tolist())
    return preds


def evaluate(logv, start="2008-01-01", step=H, use_timesfm=True, tfm_fn=timesfm_forecasts):
    idx = np.arange(len(logv))
    first = max(int(np.searchsorted(logv.index, pd.Timestamp(start))), CONTEXT)
    origins = [i for i in idx[first::step] if i + H < len(logv)]

    rows = []
    for i in origins:
        actual = float(logv.iloc[i + 1:i + 1 + H].mean())
        rows.append({"date": logv.index[i], "actual": actual,
                     "rw": float(logv.iloc[i]), "har": har_forecast(logv, i)})
    out = pd.DataFrame(rows)
    if use_timesfm:
        out["timesfm"] = tfm_fn(logv, origins)
    return out


def summarize(out):
    models = [c for c in ("rw", "har", "timesfm") if c in out]
    table = pd.DataFrame({
        m: {"log_rmse": float(np.sqrt(((out[m] - out["actual"]) ** 2).mean())),
            "log_mae": float((out[m] - out["actual"]).abs().mean())}
        for m in models}).T
    verdict = None
    if "timesfm" in out:
        gain = 1 - table.loc["timesfm", "log_rmse"] / table.loc["har", "log_rmse"]
        wins = float(((out["timesfm"] - out["actual"]).abs()
                      < (out["har"] - out["actual"]).abs()).mean())
        passed = gain >= 0.05 and wins >= 0.55
        verdict = f"TimesFM vs HAR: RMSE gain {gain:+.1%}, wins {wins:.0%} of origins -> " \
                  f"{'PASSES' if passed else 'FAILS'} pre-registered bar"
    return table, verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-timesfm", action="store_true")
    ap.add_argument("--start", default="2008-01-01")
    args = ap.parse_args()

    logv = np.log(load_vix())
    out = evaluate(logv, start=args.start, use_timesfm=not args.no_timesfm)
    os.makedirs("analysis/out", exist_ok=True)
    out.to_csv("analysis/out/timesfm_vix_baseline.csv", index=False)
    table, verdict = summarize(out)
    print(f"// VIX {H}D-AHEAD   origins={len(out)}   {out['date'].min():%Y-%m} to {out['date'].max():%Y-%m}")
    print(table.round(4).to_string())
    if verdict:
        print(verdict)


if __name__ == "__main__":
    main()
