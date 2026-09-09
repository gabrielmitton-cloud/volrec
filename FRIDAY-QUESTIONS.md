# Friday questions - the page to actually bring

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

## 1. Am I measuring the right thing?

I compute the premium as **IV minus RV, in volatility points**. A lot of the
literature works in **variance** terms, IV squared minus RV squared, because
that is what a variance swap actually pays and because variance is additive
over time and volatility is not.

**"Should I be working in variance rather than volatility? And if so, does that
change how I should read what I've already collected?"**

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

## 5b. Bloomberg - this is the big one now

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
