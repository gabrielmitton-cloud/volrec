# Friday questions - the page to actually bring

> **CORRECTED 11 Sep, morning of the meeting.** The meeting is with
> **Levon Goukasian** (Seaver, Singleton Chair in Finance), not Kownatzki.
> Checked his page directly: his research is asset pricing, portfolio
> management, hedging via Monte Carlo simulation, and he teaches Financial
> Derivatives. No published work found on options, implied vol, or the
> variance risk premium specifically - do not open with the Risks paper or
> the dissertation, they are not his. Everything below still works; open
> with the plain version instead of section 0's paper-specific hook:
>
> *"I'm doing independent research on options and volatility, testing
> whether implied volatility overshoots realized volatility. I've been
> recording my own daily data since early September. Marc Vinyard in the
> library pointed me your way given your background in derivatives and
> risk management."*
>
> He is Seaver, same as you, so no introduction-needed friction either.

---

## 0. Sample A - state it plainly, no paper hook needed

Sample A uses Cboe's VIX-family index history (free since 1990) as the implied
vol measure and ETF prices for realised vol, run through the same code that
will run on the collected panel. It is a validation step, not a discovery.

> *"I built a validation sample from Cboe's VIX history against ETF prices to
> prove my method before trusting it on my own six-observation panel. It
> found the premium significant on 9 of 11 pairs. Does that seem like a sound
> way to validate the approach?"*

**The practical ask - still worth making, independent of who is in the room:**
the single thing blocking this project from extending past 2016 is *price*
history, not volatility history. Cboe gives VIX back to 1990 for free, but the
free Alpaca plan only serves stock closes back to 2016-01-04.

> *"My volatility data goes back to 1990 but my price data stops at 2016 on
> the free plan I'm using. Is there a defensible free source that reaches
> further back? I looked at Yahoo Finance but it has no official API, so I'm
> wary of building on it without a second opinion."*

If a defensible source exists, the long sample could triple, from about 127
non-overlapping episodes per pair to somewhere near 380, at no cost.

## 0b. Keck funding - ask in general terms

> *"I understand Pepperdine's Keck Institute funds undergraduate data science
> research. Would a project like this be eligible, and would a faculty sponsor
> change what data I could realistically get access to?"*

This matters because it reframes the whole problem. Library access is a wall:
WRDS excludes undergraduates and nothing else Pepperdine publishes carries
options data. A funded project with a faculty sponsor can buy data. That is a
different door entirely.

Caveat: the Keck pages were stale when last checked, so confirm the current
cycle by email rather than trusting what is posted.

---

One page. Ask 1 to 3 even if time runs short: those change the design. The rest
only add to it. Leave room to write, and write in the room, not after.

---

## Opening, about 30 seconds

"I'm recording at-the-money implied volatility daily on 109 tickers, 21 to 45
days out, testing whether implied vol overshoots realised. The recorder runs
itself in GitHub Actions. My problem is that even with 40 trading days, most
days move together, so I have closer to six independent observations. I
validated the method on ten years of Cboe index data first and it finds the
premium on 9 of 11 pairs, so I think the code is right, but I'd like help
making the study itself stronger."

That sentence is the whole project. If he only hears that, it is enough.

---

## 1. Variance rather than volatility - now a CONFIRMATION, not an open question

**Updated 9 Sep.** Marc Vinyard sent Carr & Wu (2009), *"Variance Risk
Premiums,"* RFS 22(3), as methodology guidance. It largely answers this. Read
it before Friday if you read one thing.

What it establishes: the premium belongs in **variance**, the variance swap rate
is the right risk-neutral quantity, and **VIX approximates the 30-day variance
swap rate on the S&P 500**. That last point matters, because it means Sample A
can implement the paper almost exactly using `VIX^2`, rather than loosely.

So do not ask whether variance is right. Ask the sharper version:

**"I'm moving to a variance formulation after reading Carr and Wu. Since I only
record at-the-money rather than a full strike surface, I can't synthesise a real
variance swap rate from my own data. Is using VIX squared as the swap rate proxy
in my long sample defensible, and what am I giving up by not having the surface?"**

**"They note the premium looks closer to an independent series in log terms than
in dollar terms. Given my whole problem is dependence between observations, is
the log formulation the right response, or am I reading too much into that?"**

**One thing to be careful about out loud:** Carr and Wu define the premium as
realised minus swap rate, so theirs is **negative** when insurance is
overpriced. Mine is IV minus RV, so mine is **positive**. Same phenomenon,
opposite sign. Do not quote one next to the other without saying which is which.

Notes:


---

## 2. What do I do about overlapping windows?

Every headline test uses **non-overlapping** 21-day windows, stepping 21
trading days and discarding the rest, because overlapping daily windows made a
pooled test reject a true null 63.8% of the time in my own simulation. But
non-overlapping throws away about 95% of my rows.

**"Is discarding them the right call, or is there a standard correction,
Hansen-Hodrick or Newey-West with the right lag, that would let me keep them
without overstating significance?"**

Notes:


---

## 3. Is at-the-money implied vol defensible on its own?

I record only the ATM strike. Cboe's indices are model-free and integrate the
whole strike surface. On four matched pairs my ATM reading sat **3.61
volatility points below** the Cboe index, correct sign on all four.

**"Is ATM an acceptable proxy, or should I be building a model-free estimate
across strikes? And is that 3.6 point gap the skew premium, or something else?"**

Notes:


---

## 4. Which realised volatility estimator?

Currently close-to-close log returns, un-demeaned, small-sample bias corrected,
annualised at 252 days.

**"Would a range-based estimator, Parkinson or Garman-Klass or realised range,
be materially better at a 21-day horizon? I can get daily OHLC for free."**

Notes:


---

## 5. Data

**"Is there any free or student-accessible source of historical option-implied
volatility? I looked at OptionMetrics but wasn't sure it was open to me."**

Already settled, no need to ask: Cboe index history is free and in use back to
1990, FRED adds about 26 more years across VXD, VXN and RVX, SEC EDGAR gives
free filing dates.

Notes:


---

## 5b. Bloomberg - Marc has already answered the mechanics

**Updated 9 Sep.** Marc confirmed Bloomberg is the route, daily history is
available, and gave the exact syntax:

```
HIVG                     then select Table, the default is a graph
=BDH("AAPL US Equity", {"30DAY_IMPVOL_100.0%MNY_DF", "VOLATILITY_30D"},
     "20210101", "20260901", "Days=A")
```

**That formula returns both sides of the premium in one call.**
`30DAY_IMPVOL_100.0%MNY_DF` is 30-day implied vol at 100% moneyness, which is
at-the-money implied vol. `VOLATILITY_30D` is 30-day realised. Implied and
realised, per ticker, daily, from one function.

So the remaining Bloomberg questions are narrow:

**"How far back does 30DAY_IMPVOL go for ordinary large caps? Marc's example
started in 2021 but I don't know if that was the limit or just an example."**

**"Is pulling this for something like 100 tickers over several years reasonable,
or will I hit export limits?"**

**"What am I allowed to publish? My repo is public. I assume the raw series
can't go in it, but can derived results and regression output, with a citation?"**

That last one still matters most. If the answer is derived-results-only, the
design becomes a free reproducible public core plus a larger Bloomberg layer
that is described but not shipped. That has to be decided before pulling
anything, not after committing a file that should not have been committed.

Pepperdine has a terminal. Bloomberg holds historical implied volatility on
single names, which is exactly the thing that is missing, and it may make the
whole six-observation problem go away.

**"How do undergraduates get terminal time, and is there a booking system?"**

**"What's the right way to pull historical implied volatility? I've seen OVDV
for the surface and HIVG for a history, and I think BDH in the Excel add-in
with a field like 30DAY_IMPVOL_100.0%MNY_DF would give me a daily series. Is
that the approach you'd use?"**

**"How far back does implied vol go for ordinary large caps?"**

**"What are the export limits? I'd want a daily series for something like 100
tickers over several years, and I don't know if that's reasonable or absurd."**

### The question most students would not think to ask, and the one that matters most

Bloomberg data almost certainly **cannot be redistributed**, and this project
lives in a public GitHub repository.

**"If I pull data from the terminal, what am I allowed to publish? I assume I
can't put the raw series in a public repo, but can I publish derived results,
regression output and summary statistics, with a citation?"**

Why this matters more than it sounds: if the answer is derived-results-only,
then the design becomes two layers rather than one. The free Alpaca data stays
as the **public, reproducible core** that anyone can rebuild from scratch, and
Bloomberg becomes a **larger validation sample that is described but not
shipped**. That is a perfectly respectable structure and it is how a lot of
academic work handles licensed data, but it has to be a deliberate decision
made up front rather than something discovered after committing a file that
should not have been committed.

If the answer is that even derived output is restricted, that is worth knowing
before spending terminal hours.

Notes:


---

## 6. Events

**"If I join earnings dates to this, how do I handle the fact that many firms
report the same week? I've read I should demean the cross-section by date and
cluster standard errors on the event date, is that right?"**

Notes:


---

## 7. Last, if there's time

Firm-level news reportedly adds nothing to volatility forecasting once a HAR
baseline is in place, though macro news does. I can't find anyone testing
whether that holds for **implied** volatility specifically.

**"Is that a real gap, or am I missing a paper?"**

Notes:


---

## Closing

Ask what he'd read first if he were starting this. Ask whether he'd be willing
to look at it again once there's more data. Offer the repo, it's public.

**Then write section 4 of FRIDAY-MEETING.md the same day, while it's fresh.**

## Things to say plainly if they come up

- The sample is small and I'd rather say so than dress it up.
- I'm not looking for a trading edge, I'm testing a documented phenomenon.
- I built the long validation sample specifically because six observations
  can't carry a claim.

## Things not to do

- Don't defend a decision in the room. Take the note, reopen it properly later.
- Don't promise to build something before understanding why it helps.


---

# What I need answered to keep building

Each of these changes actual code. Ordered by how much they change.

| # | Answer needed | What it changes |
|---|---|---|
| 1 | **Variance or volatility?** `IV - RV` or `IV^2 - RV^2` | The premium definition itself, in `analyze.py` and `build_sample_a.py`. Everything downstream. |
| 2 | **Overlapping windows: discard, or correct?** If correct, which estimator and what lag rule? | The headline test. Recovering the discarded ~95% of rows would be the single biggest gain available. |
| 3 | **Realised vol estimator.** Close-to-close, or Parkinson / Garman-Klass / realised range? | `analyze.py:realized_vol`. Both samples use it, so it must change in one place. |
| 4 | **Annualisation.** 252 trading days is assumed. Is that his convention? | A constant, but it shifts every number reported. |
| 5 | **Is ATM enough?** | Whether the recorder needs to start capturing multiple strikes, which is a schema change and the sooner the better. |
| 6 | **Bloomberg fields and depth.** Exact field names, history length, export limits. | Whether a single-name Sample A is buildable at all. |
| 7 | **Bloomberg publishing rules.** Raw, derived, or nothing. | Whether the repo stays reproducible end to end, or splits into a public core plus a described-not-shipped layer. |
| 8 | **Clustering.** Demean the cross-section by date and cluster standard errors on the event date, for anything pooled. | Currently assumed correct. If he disagrees, the pooled tests need rebuilding. |

**Numbers 1, 3 and 4 are cheap now and expensive in November,** because they
change the definition of every value already computed. If you get nothing else,
get those three.

**Number 5 is the one with a deadline.** If he says ATM alone is not defensible,
the recorder should start capturing more strikes as soon as possible, since
every day of single-strike data is a day that cannot be re-collected later.
