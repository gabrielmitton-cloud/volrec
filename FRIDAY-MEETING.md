# Friday 11 September 2026 - meeting prep

A volatility researcher is going to point toward databases, calculations and
data points. This file is what to bring, what to ask, and where to write the
answers down. Fill in section 4 during or right after the meeting, while it is
still fresh, then the repo can act on it.

---

## 1. The 60-second version, if he asks what you have

Recording ATM call implied volatility daily since 4 Sep 2026, 109 tickers
spanning index ETFs, sectors, commodities, rates, FX and single names, at
21-45 days to expiry, plus the put at the same strike and a second expiry for
term-structure slope. Runs itself in GitHub Actions. Source is Alpaca's free
indicative options feed.

Testing whether implied volatility overshoots subsequent realised volatility.

**The problem, stated honestly:** by late October there will be ~40 trading
days, but most days move together, so the number of independent episodes is
closer to six. A simulation under a true null confirms it - a pooled test
across tickers rejects 63.8% of the time when the true premium is zero by
construction, while a non-overlapping test sits near its nominal 5%.

**What has been done about it so far:** a second, longer sample built from free
Cboe volatility indices, 2016-2026, ~127 non-overlapping episodes per pair. The
same code recovers a significant positive premium on 9 of 11 pairs there. So
the method is validated even though the self-collected panel is small.

## 2. Questions, in priority order

Ask 2.1 to 2.3 even if time runs short. They change the design; the rest only
add to it.

### 2.1 Is the estimand right?

The premium is currently computed as `IV - RV` in volatility points. Much of
the literature works in **variance** terms instead, `IV^2 - RV^2`, because the
variance swap is the instrument that actually pays that difference and because
variance is additive over time while volatility is not.

> *"Should I be measuring this in variance rather than volatility terms, and
> does that change how I should interpret what I have already collected?"*

This is the single most consequential question on the list. It is cheap to
change now and expensive to change in November.

### 2.2 How should overlapping observations be handled?

Currently every headline test uses **non-overlapping** 21-day windows, stepping
21 trading days at a time and discarding the rest, because overlapping daily
windows are what produce the 63.8% false rejection rate.

> *"Is throwing away overlapping windows the right call, or is there a standard
> correction - Hansen-Hodrick, Newey-West with the right lag - that would let me
> keep them without overstating significance?"*

Non-overlapping is honest but expensive: it discards ~95% of the rows.

### 2.3 Is at-the-money implied volatility defensible on its own?

Only the ATM strike is recorded. Cboe's indices are model-free and integrate
the whole strike surface. Measured gap on four matched pairs on 4 Sep: our ATM
reading sat **3.61 volatility points below** the Cboe index on average, correct
sign on all four.

> *"Is ATM implied volatility an acceptable proxy, or should I be building a
> model-free estimate across strikes? And is that 3.6 point gap the skew
> premium, or is something else going on?"*

### 2.4 Which realised volatility estimator?

Currently close-to-close log returns, un-demeaned, with a small-sample bias
correction, annualised at 252 days.

> *"Would a range-based estimator - Parkinson, Garman-Klass, realised range -
> be materially better at a 21-day horizon, given I can get daily OHLC free?"*

### 2.5 Data

> *"Is there any free or student-accessible source of historical option-implied
> volatility? I looked at OptionMetrics but was not sure it was an avenue open
> to me."*

Already ruled in or out, so no need to ask about these: Cboe's index history is
free and already in use, back to 1990 for VIX. FRED adds ~26 more years across
VXD, VXN and RVX. SEC EDGAR gives free retroactive filing dates. Social
sentiment was researched and rejected.

### 2.6 Events

> *"If I join earnings dates to this, what is the right way to handle the fact
> that many firms report the same week? I have read that I should demean the
> cross-section by date and cluster standard errors on the event date."*

### 2.7 The open question worth asking last

Firm-level news reportedly adds nothing to volatility forecasting once a HAR
baseline is in place, though macro news does. Nobody seems to have tested
whether that holds for **implied** volatility specifically.

> *"Is that a real gap in the literature, or am I missing a paper?"*

If it is a real gap, that is a legitimate thing for a write-up to pose without
answering.

## 3. What to offer

The repo is public and the write-up is honest about its limits. Offering to
show it is a better move than describing it. If he suggests something that
contradicts a decision already made here, **take the note and re-open the
decision properly** rather than defending it in the room.

## 4. Answers - fill this in

### Databases named
-

### Calculations or estimators he would change
-

### Papers or authors
-

### Things to watch out for
-

### Anything that contradicts a current decision
-

## 5. Turning answers into work

Do these in order, after the meeting:

1. **Write it down here first.** Section 4, same day.
2. **Anything methodological** that changes an estimator: open a new file in
   `hypotheses/` from `hypotheses/TEMPLATE.md` **before** changing code, and
   note in `H1`'s adjustment log that a specification changed and why. H1 has
   already been tested, so re-running it after a change is the honest way to
   show the change was not chosen for its result.
3. **Anything that is a new data source:** add it to
   `samples/long/SOURCES.md` with coverage, licence and join key, verified
   against the endpoint rather than from a description.
4. **Anything that is a new variable:** it does not enter a model until it has
   a pre-registered hypothesis and has been tested on the long sample first.
   That rule is in `annotations/README.md` and it exists to stop exactly the
   kind of enthusiasm a good meeting produces.
5. **Anything that contradicts a closed decision** in HANDOFF sections 1-3:
   that is new evidence and the decision genuinely reopens. Record who said it
   and when.
