# What this project actually does, in plain language

No jargon that is not explained. Read it in order.

---

## 1. The idea: options are insurance

If you own a stock and you are worried it might crash, you can buy a **put
option**. It pays you if the stock falls below a set price. That is insurance,
in every meaningful sense: you pay a premium now to be protected later.

Somebody sells you that insurance. And like any insurance company, they want to
charge you *more* than they expect to pay out. That gap is their profit, and it
is compensation for taking on a risk you did not want.

**The question this project asks: does that gap actually exist in options
markets, and how big is it?**

It has a name, the **volatility risk premium**, and it is well documented. This
project is not trying to discover it. It is trying to measure it honestly in
data collected from scratch, and to be able to defend every step.

## 2. The two numbers everything rests on

**Implied volatility (IV).** The price of the insurance, expressed as a
percentage. When you see "implied vol is 20%," the market is saying it expects
this stock to move about 20% over a year, and option prices are set accordingly.
It is a **forecast**, baked into a price, made by people risking real money.

**Realised volatility (RV).** How much the stock *actually* moved, measured
after the fact from daily price changes. Not a forecast. A fact.

**The premium is IV minus RV.**

- Positive means the insurance was overpriced. The forecast was higher than
  reality, so the seller profited.
- Negative means the buyer got a bargain.

Averaged over many periods, the literature says this is positive. Sellers of
volatility insurance get paid, the way insurance companies do.

## 3. What the recorder actually collects

Every weekday at 14:47 UTC, a script wakes up on GitHub's servers and asks
Alpaca for option prices on 109 tickers. GitHub runs scheduled jobs late when it
is busy - three to four hours, in practice - so the reading is usually taken
around 18:00-19:20 UTC, comfortably inside the trading day. For each ticker it
writes a row:

| what | why it is there |
|---|---|
| `spot` | the stock price right now |
| `strike`, `expiration`, `dte` | which option, and how many days until it expires |
| `bid`, `ask`, `mid` | what buyers and sellers are quoting |
| `iv` | the implied volatility, the forecast |
| `delta` … `rho` | the greeks, standard option sensitivity measures |
| `put_*` | the matching put at the same strike |
| `far_*` | a second, longer-dated option |
| `quote_time` | when the quote was actually taken |

Roughly 30 days to expiry, at the strike nearest the current price
(**at-the-money**, or ATM). One row per ticker per day. 109 rows a day.

**Why it must never miss a day:** you cannot go back and ask what an option
cost last Tuesday. There is no free historical archive of option quotes. A
missed day is gone permanently. That is why the recorder runs itself, why it is
guarded against holidays, and why nothing else is allowed to write to that file.

## 4. The problem that shapes every decision: N

This is the part worth actually understanding, because it explains almost every
choice in the repo.

By late October there will be about 40 trading days of 109 tickers, so roughly
4,400 rows. That *feels* like 4,400 pieces of evidence. **It is not.**

**Reason one: tickers move together.** When the market falls, nearly everything
falls. So on any given day, your 109 tickers are largely telling you the same
story. That is closer to one piece of information than to 109.

**Reason two: days overlap.** A 30-day option bought today and one bought
tomorrow cover almost the same stretch of future. Consecutive days are not
separate experiments; they are the same experiment measured twice.

Put together, roughly 40 trading days gives about **six genuinely independent
observations.**

**Why that matters so much.** Statistics assumes your observations are
independent. Feed it 4,400 correlated rows as if they were 4,400 independent
ones and it will confidently announce a discovery that is not there.

This project *proved* that on itself. `analyze.py --simulate` builds fake data
where the true premium is **exactly zero by construction**, then runs the tests:

- the naive pooled test claims a significant finding **63.8%** of the time
- with a realistic market factor, **93.0%** of the time
- the careful non-overlapping test: **3.8%**, which is about right

So the naive approach is wrong nine times out of ten, on data where the right
answer is known to be nothing. That single result justifies most of the
discipline in this repo.

## 5. The fix: a second, much longer sample

You cannot manufacture more independent observations out of two months. So get
them from history instead.

Cboe publishes the **VIX** every day back to **1990**, free. VIX is essentially
implied volatility for the S&P 500. They publish similar indices for the Nasdaq,
Russell, gold, oil, and others.

So there are two samples running **the same code**:

- **Sample A**, 2016 to 2026. Cboe indices as the implied vol, ETF prices as the
  realised vol. About **127 independent windows per pair**.
- **Sample B**, the panel you collect yourself. About **six**.

**Sample A is not the discovery. It is the proof the machinery works.** The
premium is already well documented there. If the code cannot find a known result
on ten years of data, nothing it says about six observations is worth reading.

**It worked.** The premium came out positive and statistically significant on
**9 of 11** pairs. VIX against SPY: **+3.52 volatility points**, positive in 83%
of windows.

That buys one sentence, and it is the most valuable sentence in the project:

> *"My method recovers the known result on ten years of history. Here is what
> the same code finds on the data I collected myself, and here is exactly why
> six observations means I am not claiming more than that."*

An interviewer who hears that is talking to someone who understands their own
statistics. That is worth far more than a big-sounding number.

## 6. Why the honesty is the point

The instinct is to make a project sound impressive. Here, the opposite is
stronger. Anyone competent will immediately ask "how many independent
observations do you really have?" Having already answered it, in writing, with a
simulation, is the difference between a project that survives scrutiny and one
that falls apart in ninety seconds.

That is also why the repo has rules that look excessive:

- **`hypotheses/`** holds predictions written and committed *before* the test is
  run. Otherwise you find a pattern, then invent a reason you expected it. The
  commit date is the proof you did not.
- **`annotations/` can never become a model input.** Notes written about the data
  cannot become variables predicting the data.
- **Nothing writes to `iv_history.csv` except the recorder**, and 39 automated
  checks verify the history has not been rewritten.

## 7. What Friday is actually about

Three questions, in plain terms.

**1. Should the premium be squared?**
Currently: `IV - RV`, in volatility points. But **variance** is volatility
squared, and variance has a property volatility lacks: it adds up cleanly over
time. The instrument that actually pays this premium in real markets, a variance
swap, pays on variance. So the whole thing may belong in variance terms.
Cheap to change now. Expensive in November, because it redefines every number.

**2. Can the discarded data be recovered?**
To keep windows independent, the analysis steps forward 21 trading days at a
time and throws away everything between, roughly **95% of the rows**. There may
be a standard statistical correction that allows keeping them without lying
about significance. If so, that is a large amount of data back for free.

**3. Is at-the-money alone good enough?**
Only the strike nearest the current price is recorded. The "proper" measure uses
*every* strike. On four matched pairs, the ATM reading sat **3.61 volatility
points below** Cboe's full-surface number, consistently.

**This is the question with a deadline.** If the answer is that ATM alone is not
defensible, the recorder should start capturing more strikes immediately, because
every day recorded with one strike is a day that cannot be re-collected.

## 8. If you remember five things

1. Options are insurance, and this measures whether the insurance is overpriced.
2. Implied vol is the forecast; realised vol is what happened; the premium is
   the gap.
3. 4,400 rows are not 4,400 pieces of evidence. There are about six.
4. Sample A exists to prove the code works, not to make a discovery.
5. Being honest about the small sample is the strongest thing about the project,
   not its weakness.
