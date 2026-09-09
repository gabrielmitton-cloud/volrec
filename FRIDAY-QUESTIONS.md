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

**"Does the school have anything else I should know about, a Bloomberg terminal,
Capital IQ, Refinitiv? I don't know what's actually available to undergraduates."**

Already settled, no need to ask: Cboe index history is free and in use back to
1990, FRED adds about 26 more years across VXD, VXN and RVX, SEC EDGAR gives
free filing dates.

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
