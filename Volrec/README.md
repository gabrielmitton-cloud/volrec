# volrec — daily options data recorder

Records one at-the-money call snapshot per ticker per day into a CSV.
Free to run. Historical implied-volatility data is expensive to buy and
cheap to accumulate — this starts accumulating today.

## Account

One free Alpaca account. Paper trading only:

1. alpaca.markets → sign up (email and password; no SSN, no funding,
   no brokerage application)
2. In the dashboard, switch to **Paper Trading**
3. Generate API keys — you get a Key ID and a Secret. The secret is shown
   once, so copy it immediately.

Options data is enabled by default in the paper environment.

## Run it

```bash
pip install requests
export ALPACA_KEY="your_key_id"
export ALPACA_SECRET="your_secret"
python record.py
```

Good output looks like:

```
  SPY    spot    642.10  strike   640.00  31d  iv 0.1287
  AAPL   spot    221.44  strike   220.00  31d  iv 0.2517
  ...
Wrote 4 row(s) to data/iv_history.csv
```

If anything looks wrong — empty `iv`, a 403, no contracts — run:

```bash
python record.py --probe SPY
```

That prints the raw API response so the actual field names are visible.

## Feeds

The script uses Alpaca's free tiers: `indicative` for options and `iex`
for stocks. Both are free; `opra` and `sip` need a paid subscription and
will return 403 without one.

The indicative options feed has delayed trades and modified quotes. That
is fine for a daily snapshot and worth knowing when you write up results:
your bid/ask are indicative, not the exact NBBO.

## Daily automation

The whole value is in never missing a day.

**cron** (`crontab -e`):

```
30 11 * * 1-5 cd /path/to/volrec && ALPACA_KEY="..." ALPACA_SECRET="..." /usr/bin/python3 record.py >> log.txt 2>&1
```

**GitHub Actions** — better if your laptop closes a lot. Put both keys in
Settings → Secrets → Actions, then `.github/workflows/record.yml`:

```yaml
name: record
on:
  schedule:
    - cron: "30 15 * * 1-5"   # 15:30 UTC ≈ 11:30 ET during EDT
  workflow_dispatch:
permissions:
  contents: write
jobs:
  record:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install requests
      - run: python record.py
        env:
          ALPACA_KEY: ${{ secrets.ALPACA_KEY }}
          ALPACA_SECRET: ${{ secrets.ALPACA_SECRET }}
      - run: |
          git config user.name  "recorder"
          git config user.email "recorder@local"
          git add -f data/
          git diff --staged --quiet || git commit -m "snapshot $(date +%F)"
          git push
```

Note: if you use Actions, remove `data/*.csv` from `.gitignore` — the
whole point is committing the data. GitHub's scheduler runs on UTC and
does not adjust for daylight saving, so the ET time drifts an hour in
November. Harmless, as long as it stays inside market hours.

## What you're collecting

| column | why it matters |
|---|---|
| `iv` | The forecast you're testing. The number you can't buy cheaply. |
| `spot` | Lets you compute what volatility actually showed up afterward. |
| `delta`, `gamma`, `vega` | Broker-computed greeks, to check your own maths against. |
| `bid`, `ask` | Your real hedging cost, instead of the slider guess in Gamma Lab. |
| `dte`, `moneyness` | Keeps snapshots comparable as expiries roll. |

The analysis, once there are a few months of rows: for each snapshot,
compare the `iv` recorded that day against the volatility the stock
actually delivered over the following 30 days. If realized consistently
comes in under implied, options were expensive — the volatility risk
premium, measured by you rather than read about.

## Notes

- Parsing, expiry and strike selection, put filtering, missing-greeks
  handling, and dedupe are covered by offline tests. The live endpoints
  have not been hit — the first real run is the actual test.
- A missed day is not fatal. Don't gap for months.
