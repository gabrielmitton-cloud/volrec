# Sample A source manifest — verified 6 September 2026

Facts below were checked live on 2026-09-06 against the endpoints themselves,
not read from a summary. Re-verify before relying on any of it in 2027.

## Cboe CDN — the primary source. No key, no rate limit, no registration.

`https://cdn.cboe.com/api/global/us_indices/daily_prices/<NAME>_History.csv`

`analyze.py` **already fetches from here** (§11.1) and caches to
`data/market_vol.json`. Sample A extends existing code; it does not add a
dependency.

All 14 tested returned HTTP 200:

| index | underlying | Cboe CDN range | rows | note |
|---|---|---|---|---|
| VIX | SPX | 1990-01-02 → 2026-09-04 | 9266 | the long bar |
| VIX9D | SPX 9-day | 2011-01-04 → 2026-09-04 | 3941 | |
| VIX3M | SPX 3-month | 2009-09-18 → 2026-09-04 | 4267 | slope vs VIX9D |
| VIX6M | SPX 6-month | 2008-01-02 → 2026-09-04 | 4699 | |
| VXN | NDX / QQQ | 2009-09-14 → 2026-09-04 | 4273 | FRED reaches further |
| RVX | RUT / IWM | 2009-09-16 → 2026-09-04 | 4264 | FRED reaches further |
| VXD | DJIA / DIA | 2009-09-18 → 2026-09-04 | 4267 | FRED reaches further |
| OVX | USO | 2009-09-18 → 2026-09-04 | 4265 | |
| GVZ | GLD | 2009-09-18 → 2026-09-04 | 4265 | |
| VXEEM | EEM | 2011-03-16 → 2026-09-04 | 3888 | |
| VXSLV | SLV | 2011-03-16 → 2026-09-04 | 3073 | **GAP** 2022-02-11→2025-05-15 |
| VXGDX | GDX | 2011-03-16 → 2026-09-04 | 2989 | **GAP** 2022-02-11→2025-09-16 |
| VXXLE | XLE | 2011-03-16 → 2022-02-11 | 2744 | ended, not relaunched |
| EVZ | FXE | 2009-09-18 → 2025-03-11 | 3891 | ended Mar 2025 |

**All 12 of the brief's §5.1 series map to a ticker in the frozen watchlist.**
Verified against `record.py`'s WATCHLIST: 12 of 12.

### Two corrections to the research brief

1. **The brief makes FRED §5.1 "highest priority." It is second priority.** The
   Cboe CDN carries the same data with *no API key and no rate limit*, and the
   fetcher already exists. FRED reprints Cboe under permission; going to the
   source removes a registration step and a dependency.
2. **FRED's DISCONTINUED tags are stale for two series.** FRED shows VXSLV and
   VXGDX ending 2022-02-11. Cboe shows both **relaunched** — VXSLV 2025-05-15,
   VXGDX 2025-09-16 — with a ~3-year hole between. Treat the segments
   separately (H1 specification). VXXLE and EVZ really have ended.

### Where FRED still wins — worth the free key

FRED carries **longer back-history** for three series than the Cboe CDN files:

| series | FRED start | Cboe start | extra history |
|---|---|---|---|
| VXDCLS / VXD | 1997-10-07 | 2009-09-18 | **+11.9 years** |
| VXNCLS / VXN | 2001-02-02 | 2009-09-14 | **+8.6 years** |
| RVXCLS / RVX | 2004-01-02 | 2009-09-16 | **+5.7 years** |

For a project whose binding constraint is sample size, that is ~26 extra years
across three underlyings. **Use both: Cboe CDN as primary, FRED to backfill the
head of those three.** Requires a free FRED API key (user registration).

- Endpoint: `https://api.stlouisfed.org/fred/series/observations?series_id=...&api_key=...&file_type=json`
- Licence: Cboe copyright, reprinted with permission, **citation required**.
  Cite; do not mirror raw CSV into the repo.

## The unresolved dependency — realised volatility

**Sample A needs daily closes of the underlyings and no catalogued source
provides them.** See `hypotheses/2026-09-06-h1-vrp-long-sample.md` §5.

- **Stooq: REJECTED 2026-09-06.** Now serves a JavaScript proof-of-work bot
  challenge on `stooq.com/q/d/l/`. Verified with both a default and a browser
  User-Agent; both got the challenge, not CSV.
- **Alpaca** is the leading candidate (key held, fetcher exists). Free-plan
  history depth **unverified** — settle with one call before designing.

## Not yet verified — do not design around these

| item | how to settle |
|---|---|
| Alpaca stock-bar history depth on the free plan | one REST call, existing key |
| Alpaca News API free-plan availability | one REST call, existing key |
| Alpaca corporate-actions free-plan depth | one curl |
| FRED API ToU on redistributing derived series | read the ToU on the API docs |
| Which EMV categories are daily vs monthly | policyuncertainty.com |
| Pepperdine WRDS contents (OptionMetrics IvyDB?) | ask a finance professor |
