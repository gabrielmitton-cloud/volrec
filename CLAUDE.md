# volrec

**Start at `SESSION-START.md`** - one screen: read order, commands, what runs
unattended, standing rules. Then run `tools/daily.py` for the live state, and read
only the newest dated subsection of `HANDOFF.md` section 17. The rest of HANDOFF is
history with the reasoning attached; sections 1-3 hold closed decisions - do not
re-argue them without new, dated evidence.

## Which python

`python3` on this Mac resolves to `/opt/homebrew/bin/python3`, which has **no
`requests`**, so every project tool dies with `ModuleNotFoundError` on it. Use:

    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3

for `pressure_test.py`, `panel_health.py`, `analyze.py`, `hedged.py` and the
`tools/` scripts. Homebrew sits earlier in PATH than the framework install, so
this is a silent trap rather than an obvious one; it has now cost two sessions.
CI is unaffected - the workflows use `actions/setup-python` and `pip install
requests`.

`analysis/` is different: it runs in `.venv` (`.venv/bin/python`), which carries
pandas, numpy and torch. The pipeline itself stays stdlib + `requests`, and
`requirements.txt` is deliberately not the place to add analysis dependencies.

## Daily and Bloomberg commands

    .../python3 tools/daily.py                        # the whole daily check, one screen
    .../python3 tools/bloomberg_prep.py --date DATE   # what to pull, when, what to write down

`daily.py` ends ALL CLEAR or LOOK AT. A crash is reported as a crash, never a pass.

## Tools and rules
### TimesFM benchmark (analysis/timesfm_vix_baseline.py)
- Question: does TimesFM beat HAR and a random walk at forecasting mean log VIX over the next 21 trading days?
- Data: FRED VIXCLS only (the long validation sample). Origins every 21 trading days from 2008-01-01. Context 1024 days.
- Model: TimesFM 2.5 (google/timesfm-2.5-200m-pytorch, Apache-2.0). Never switch to TimesFM 3.0 weights (non-commercial license).
- Pre-registered pass bar: TimesFM must cut log-RMSE by at least 5% vs HAR AND beat HAR on at least 55% of origins. Never change the bar, horizon, start date, or metrics after seeing results. A FAIL is reported as a negative result in the Feb 2027 write-up.
- Never fit or evaluate any forecaster on data/iv_history.csv alone. The live panel has too few independent episodes. Follow the guardrails in volrec-data-layer-brief.md.
- Never change the recorder's ticker universe. It's frozen.

### Vibe-Trading MCP
- Research tools only: get_market_data, get_options_chain, analyze_options, analyze_options_payoff, backtest, quantlib_call, technical_indicators, get_macro_series.
- Never call trading_select_connection, trading_check, trading_account, trading_positions, trading_orders or any other trading_* tool. Never configure a broker connector.
- Backtest runs are saved to ~/vibe-trading-runs.
