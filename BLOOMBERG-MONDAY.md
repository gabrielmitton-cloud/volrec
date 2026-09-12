# Bloomberg session checklist

**The terminal is a validation instrument, not a data source.** It holds only
~90 days of historical equity option data, so there is no long history to
collect. What it can do, and nothing else can, is tell you how good your free
data is. See HANDOFF section 15.1.

Do not try to build a dataset here. Two or three good days beats a rushed pull.

---

## Priority 0: get ONE chain into Excel. Nothing else matters until this works.

If you leave with nothing but a working export and the exact syntax that
produced it, the session was a success. Everything below is optional by
comparison.

1. `TSLA US Equity` then `OMON` then `<GO>` - the option monitor
2. Switch the display to **Table** (the default is a graph)
3. Find the expiry nearest **30 days out**
4. Export to Excel: the green **Export** button, or `Actions > Export to Excel`

**Write down exactly what worked.** Menu path, button, any dialog. That is the
thing you cannot reconstruct later from memory.

## Priority 1: verify the field names before spending time on a big pull

**Do not trust field names from me or from any web source.** Verify them at the
terminal, which takes a minute:

- `FLDS` then `<GO>` on a contract shows the real field list for that security
- Search within FLDS for: `BID`, `ASK`, `VOLUME`, `IVOL`, `OPEN_INT`

The names I believe are right, all **unverified** until you check: `PX_BID`,
`PX_ASK`, `PX_LAST`, `PX_VOLUME`, `OPEN_INT`, `IVOL_MID`. Marc's confirmed
working example used `30DAY_IMPVOL_100.0%MNY_DF` and `VOLATILITY_30D`, but
those are *equity* fields, not per-contract option fields.

**Write down the names that actually exist.** One wrong field name wastes a
whole session.

## Priority 2: the comparison pull

This is what the whole exercise is for.

**Tickers, in priority order.** If time runs short, the first two are the ones
that matter:

| ticker | why |
|---|---|
| **USO** | highest volatility, where truncation and feed quality bite hardest |
| **SPY** | lowest volatility, and the one that already matched Cboe to 0.01 |
| TSLA | the single-name case, and the name the professor named |

**For each: the expiry nearest 30 days out, every strike within about +/-30% of
spot.** Do not filter to twenty strikes. Pull the whole chain for that expiry
and let me do the matching afterwards; filtering by hand at the terminal wastes
time and risks dropping the contracts that matter.

**Per contract, the columns wanted:** strike, type (call/put), expiry, **bid**,
**ask**, **implied volatility**, **volume**, **open interest**.

## Priority 3: timing, which matters more than it looks

The recorder snapshots at roughly **18:45-19:00 UTC**, which is about
**11:45am-12:00pm Pacific**. Options move all day, so a Bloomberg pull at 9am
and an Alpaca snapshot at noon are not measuring the same thing, and the
difference would show up as a "feed quality gap" that is really a time gap.

- **Pull as close to noon Pacific as you can manage.**
- **Whatever time you pull, write it down.** An exact time with a mismatch is
  usable. A tight match with an unknown time is not.

## Priority 4: two facts worth confirming while you are there

- **How far back does the "As of" field actually go?** Set it to 30 days ago,
  then 60, then 120. Library guides say 90 calendar days. Confirm it yourself,
  because the whole Bloomberg plan was rewritten on that claim.
- **Is there a visible export limit?** Any warning about daily or monthly
  download caps, note the wording.

## What NOT to do

- **Do not attempt a fifteen-year pull.** It is impossible; the data is not
  there. Do not burn the session discovering that again.
- **Do not export raw data intending to commit it.** Bloomberg's licence is
  restrictive and this repo is public. Derived results only, and that question
  is still open with Goukasian.
- **Do not skip Priority 0 to get more tickers.** One verified export beats
  three half-finished ones.

## Send me

The Excel file, plus:
- the **time** you pulled, with timezone
- the **field names** that actually existed in FLDS
- whether the "As of" field reached past 90 days
- anything that did not work

I will match it contract by contract against the surface recorded the same day
and decompose the gap into feed quality versus strike coverage. That is the one
piece of H3 that cannot be answered from free data alone.
