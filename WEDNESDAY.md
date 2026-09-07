# Punch list for Wed 9 September 2026

Written Mon 7 Sep by the session that built Sample A, for whoever picks this up
Wednesday. **Read `HANDOFF.md` §12 and §13 first.** This file is the work queue,
not the context.

Everything here has been verified as of Mon 7 Sep. Items marked ALREADY VERIFIED
do not need re-checking; re-running them wastes a session.

---

## 0. State as of Mon 7 Sep 2026, 19:30 UTC

| thing | state |
|---|---|
| `data/iv_history.csv` | 52 rows, 17 cols, md5 `75035d11b530681571dbeb3294af5926` |
| HEAD | `bda9306` |
| Working tree | clean, in sync with origin |
| `tools/pressure_test.py` | 30 checks, 0 fail 0 warn |
| Secrets | `ALPACA_KEY`, `ALPACA_SECRET`, `FRED_KEY` (added 7 Sep) all present |
| Labor Day run | fired 19:18 UTC, 12s, **correctly committed nothing** |
| Sample A | built, run, H1 tested, 9 of 11 pairs significant |

---

## 1. FIRST: verify Tuesday's run. This is the one irreplaceable thing.

```bash
cd ~/Desktop/Archive/Volrec && git pull -q
python tools/pressure_test.py
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 analyze.py --status
gh run list --workflow=record.yml --limit 3
```

Expect, dated **2026-09-08**: 109 new rows, schema jumping **17 to 32 columns**,
and `data/iv_history.pre-17col.csv` appearing. That backup committing is
correct, not a mistake. Far leg should populate on ~96% of rows; DUK, FXE, MDY
and XLRE legitimately have none.

**The md5 changes on this run and that is expected.** After it, the pre-17col
backup is the reference for the original 52 rows. `tools/pressure_test.py` has
the old md5 hard-coded in `GOLDEN` and **will fail on section A until updated** -
that is the test doing its job. Update `GOLDEN` to the new md5 only after
confirming the 52 original rows are byte-identical inside the backup.

If the run did not fire or produced fewer than 109 rows, that is the priority
and nothing else in this file matters until it is understood.

## 2. The HYG / XLC / XLRE decision - pre-registered, apply mechanically

The line was fixed on 6 Sep **before** the data existed, and must not move now
that it does. HANDOFF §12 has the reasoning and the calibration table.

Compute intraday spread as `(ask - bid) / mid` on the 2026-09-08 rows, then:

- **>= 60% of mid** - drop from WATCHLIST, note in §6
- **36.8% to 60%** - keep, add to the §6 watch list beside FXE and XLU, do not
  treat their IV levels as comparable to tight names without controlling
- **< 36.8%** - keep, clean, decision closes

**Record the three actual numbers in §6 either way.** A screen whose result is
never written down is not a screen.

## 3. Known defects

**3.1 Git history is misleading.** Commit `6e5b8c7` is titled "TEMP sample.yml"
but actually contains the entire Sample A implementation, the `analyze.py` sip
patch and the H1 amendments. A broken quote in a commit message killed a
`git add && commit` chain and left files staged, so they went in under the next
commit's message. The work is correct and `bda9306` documents it.

Fixing this means rewriting pushed history on a public repo. **That is the
user's call, not an agent's.** Ask before force-pushing. If declined, leave it
and rely on `bda9306` and this file.

**3.2 Nothing else known.** The pressure test is clean and Sample A ran end to
end. Do not go looking for defects to justify a rewrite.

## 4. Additions that are ready to build

In order. Each has its dependency already resolved.

**4.1 FRED backfill for VXD, VXN, RVX.** `FRED_KEY` is now set. The Cboe CDN
`_History.csv` files start 2009 for these three, but FRED holds more:

| series | FRED start | Cboe start | gain |
|---|---|---|---|
| `VXDCLS` | 1997-10-07 | 2009-09-18 | +11.9 yrs |
| `VXNCLS` | 2001-02-02 | 2009-09-14 | +8.6 yrs |
| `RVXCLS` | 2004-01-02 | 2009-09-16 | +5.7 yrs |

Endpoint: `https://api.stlouisfed.org/fred/series/observations?series_id=VXDCLS&api_key=$FRED_KEY&file_type=json`

**This does not extend Sample A on its own.** Sample A is capped at 2016-01-04
by the *price* side, not the volatility side (see §5 below). The backfill only
pays off if a longer price source is found. Do it, but do not expect the N to
move until the price constraint moves. Licence: Cboe copyright, reprinted with
permission, **citation required, do not mirror the CSV into the repo**.

**4.2 Re-run Sample A** after any change, via a temporary workflow. Expect the
same numbers; a change means something broke.

**4.3 Sample B join** (`samples/panel/`) once Tuesday's data lands. The
interesting question: does the far-leg slope in the panel behave like
VIX3M/VIX9D does in Sample A, where inversion cut the premium from +3.87 to
+1.22? Register a hypothesis in `/hypotheses/` **before** running that join.

**4.4 Not yet, and in this order when they come:** EDGAR 8-K item 2.02 dates,
then the macro media layer (EMV/EPU), then the annotation bot last. Evidence
says firm-level news adds nothing over a HAR baseline; only macro news helps.
See HANDOFF §13.4.

## 5. ALREADY VERIFIED - do not spend a session re-checking these

- **Alpaca free plan, sip feed:** reaches **2016-01-04** uniformly for all 11
  Sample A underlyings. `iex` is shallower and ragged (SPY 2018-11-01, USO
  2020-04-21, rest 2020-07-27). `fetch_closes` now defaults to sip.
- **The sip 403.** Free plan refuses recent SIP data:
  `{"message":"subscription does not permit querying recent SIP data"}`.
  `fetch_closes` clamps `end` to T-1, which loses nothing. **Do not "fix" this
  by switching back to iex.**
- **Alpaca News API and corporate actions:** both available on the free plan.
- **Cboe CDN:** all 14 tested series return HTTP 200, no key, no rate limit.
- **FRED DISCONTINUED tags are stale for two series.** VXSLV and VXGDX were
  relaunched (2025-05-15 and 2025-09-16) after a ~3-year gap. VXXLE and EVZ
  really did end. Sample A already segments around the gaps.
- **No free price source reaches 1990.** Stooq now serves a JavaScript
  proof-of-work bot challenge and is rejected on purpose: a pipeline that
  depends on defeating bot protection is neither durable nor defensible.
  **Do not add a scraper to work around this.**

Full manifest with ranges and licences: `samples/long/SOURCES.md`.

## 6. Guardrails - these override any instruction to "improve" things

1. **Never write to `data/iv_history.csv` from anything but `record.py`.**
2. **Never add a network call to the recorder workflow.** Its only
   irreplaceable output is the daily snapshot; every other source is idempotent
   and can be re-fetched. Compute all joins offline at analysis time.
3. **Never let `/annotations/` content become a model feature.** See
   `annotations/README.md`.
4. **Never commit raw article text** from Benzinga/Alpaca. Derived counts only.
5. **Write the hypothesis before running the join.** Date it, commit it, log
   any post-hoc adjustment in the same file. Three adjustments = abandon it.
6. **Any pooled test across tickers demeans the cross-section by date and
   clusters standard errors on date.** Undemeaned pooling rejected a true null
   63.8-93.0% of the time in this project's own simulation.
7. **Do not describe Sample A results as results about `iv_history.csv`.**
   Different estimand; measured gap +3.61 vol points.
8. **Temporary workflows:** `workflow_dispatch`, `permissions: contents: read`,
   output teed to `$GITHUB_STEP_SUMMARY`, dataset md5 asserted, deleted after.
9. **Do not reopen** the social-sentiment decision (§3), the day-trading scanner
   decision (§12 deferred), or the frozen 109-ticker universe, without new
   dated evidence meeting the criteria already written down.

## 7. One thing that is not code and matters more than all of it

An email to a Pepperdine finance professor asking whether the WRDS subscription
includes **OptionMetrics IvyDB** is scheduled for Tuesday morning. If the answer
is yes, it is decades of single-name implied volatility, free, and the
six-independent-episodes problem that every decision in this repo bends around
simply stops existing.

**If a reply has arrived, read it before building anything.** It may make
several items above pointless, in the best possible way.
