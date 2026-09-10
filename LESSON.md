# The lesson: the finance and statistics behind this project

Written 10 Sep 2026, the night before the meeting. Companion to EXPLAINER.md.
EXPLAINER is "what the project does." This is "understand the concepts well
enough to follow the professor and ask the questions intelligently."

Read it once tonight, once tomorrow morning.

---

## Part 1: What implied volatility actually is

Most people who use the term don't really understand it. Get this solid and you
follow 80% of what the professor says.

Start with a call option: the right to buy AAPL at $200 anytime in the next 30
days. If AAPL is at $195, that right is worth something, because AAPL might rise
past $200 before expiry.

What sets that price? Five things: the stock price, the strike, time to expiry,
interest rates (small), and **how much the stock is expected to move**. The last
one is the only hard part. A stock that swings 3% a day is far more likely to
blow past $200 than one that creeps 0.2% a day, so its option costs more.

Black-Scholes is the formula that takes those five inputs and returns the option
price. Four inputs are known facts. The fifth, expected movement, is a guess
about the future.

The trick: in the real market you don't know expected movement, but you DO see
the option price. Quote is $4.10. Run the formula backwards: what movement
number, plugged in, produces exactly $4.10? Say the answer is 25%.

**That 25% is the implied volatility.** Nobody measured it. It's the volatility
implied by the price people are actually paying. Read "IV is 25%" as: option
prices right now only make sense if traders expect this stock to move about 25%
annualized over the option's life.

Your recorder captures this (`iv`) for 109 tickers daily. Alpaca does the
backing-out.

---

## Part 2: Realized volatility and the premium

Realized volatility (RV) is the easy one. After the fact, look at how much the
stock actually moved: daily price changes over a window, standard deviation,
annualized. A measured fact, not a forecast.

- IV = the forecast, made before, priced into options
- RV = what actually happened, measured after

**The premium is IV minus RV.** Was the forecast too high, too low, or right?

Documented answer: on average IV is higher than the RV that follows. The
forecast systematically overshoots. Option sellers tend to come out ahead
because the stock usually moves less than implied.

Your Sample A: VIX vs SPY, +3.52 volatility points on average. S&P options
priced for ~3.5 points more movement than showed up, for ten years.

---

## Part 3: Why the premium exists (the economics)

If sellers reliably win, why buy? Three reasons, and they matter because they're
why the premium is real and not a fluke:

1. **Insurance.** A pension fund buys puts as crash protection even knowing
   they're slightly overpriced. Not trying to win the trade, capping the
   downside. Like fire insurance.

2. **Crash risk is lopsided.** Stocks drift up slowly, crash down fast. Whoever
   sold you the put faces a sudden huge loss on a gap down. They demand extra
   compensation for that ugly risk, and that extra compensation is the premium.

3. **Volatility spikes when you're already hurting.** Vol jumps during crashes,
   when your portfolio is down and everything's bad at once. An asset that pays
   off then is worth overpaying for; being short vol (collecting the premium)
   has to pay you to hold it.

Carr & Wu call this a common variance risk factor: one underlying risk all these
options share, priced with a premium market-wide. Their key result: the premium
is bigger for stocks more sensitive to overall market volatility (their
"variance beta").

---

## Part 4: The N problem (the heart of it)

Your instinct: 109 tickers x 40 days = 4,400 data points. Reality: about SIX.

**Why tickers don't count as separate.** When the market drops, almost
everything drops together. Your 109 Tuesday measurements aren't 109 independent
facts, they're closer to one fact measured 109 ways. "Cross-sectional
correlation."

**Why days don't count as separate.** A 30-day option today and one tomorrow
cover almost the same future, 29 of 30 days overlap. A big move next week lands
in both windows. Today's and tomorrow's measurements aren't independent
experiments. "Serial correlation" / "overlapping windows."

Together: ~40 trading days, each overlapping its neighbors, tickers moving as a
pack, gives roughly SIX independent pieces of information by late October.

**Why six is dangerous.** Every statistical test assumes independence. Feed it
4,400 correlated numbers as if independent and it becomes wildly overconfident,
finding "significant" patterns in noise.

**Proven on itself.** `analyze.py --simulate` builds fake data with the true
premium set to EXACTLY ZERO, then runs the tests:

- naive (all rows independent): significant "discovery" 63.8% of the time
- with a market factor: 93%
- careful non-overlapping test: 3.8%, which is correct since nothing is there

The naive approach is a lie detector that lies 9 times in 10. That result is why
the project has all its discipline.

---

## Part 5: What a t-statistic means

**t = (effect you measured) / (uncertainty in that measurement)**

A signal-to-noise ratio. How many standard errors from zero.

- t about 0: effect smaller than the noise, could be nothing
- t about 2: twice the noise, conventionally "significant," borderline
- t about 5: five times the noise, hard to dismiss as luck
- t about 16: overwhelming, IF assumptions hold

The catch, and it's your whole project: the denominator depends on how many
INDEPENDENT observations you have. Claim 4,400 when you have 6 and you shrink the
denominator artificially and t explodes. A huge t on the wrong N is how you fool
yourself.

Sample A: VIX/SPY at t = 5.14 on ~127 properly independent windows. Real. Your
six-observation panel will give much smaller t's, honestly computed, and that's
fine, because the honest small number is defensible.

---

## Part 6: Sample A and the two-sample idea

Can't manufacture independent observations from two months. More tickers won't
help (move together). More days won't help fast enough.

The VIX is essentially implied volatility for the S&P 500, and Cboe has
published it daily since 1990, free. Similar indices for Nasdaq (VXN), Russell
(RVX), gold (GVZ), oil (OVX).

Two samples, same code:

- **Sample A:** VIX-family indices as implied vol, ETF prices for realized,
  2016-2026, ~127 independent windows per pair. Where you check the method works.
- **Sample B:** your own panel, ~6 independent episodes. The actual study.

Why it's the strong move: the premium is ALREADY known in Sample A, it's in the
textbooks. You're proving your exact code and estimators recover a known result
when data is plentiful, then running that validated code on your small dataset
with the sample size stated honestly.

The sentence it buys:

> "My method recovers the known premium on ten years of index history, 9 of 11
> underlyings, VIX/SPY at t = 5.1. Here's what the same code finds on the two
> months I collected myself, and here's exactly why six independent observations
> means I'm not claiming more than a suggestive result."

---

## Part 7: Question 1 - variance vs volatility

You compute the premium as IV - RV in volatility points. Carr & Wu, and much of
the literature, works in VARIANCE, which is volatility squared.

Why squared:

1. **Variance adds across time; volatility doesn't.** Variance V per day means
   30V over 30 days. Volatility (the square root) goes as sqrt(30), not 30. For
   math across horizons, variance is the natural unit.

2. **The traded instrument pays on variance.** A variance swap is a real
   contract paying realized variance minus a fixed rate. That fixed rate is the
   market's risk-neutral variance forecast, the cleanest "implied variance."
   Carr & Wu synthesize it from option prices across strikes.

**What H2 found.** Three versions on 508 equity-index observations:

| formulation | t-stat |
|---|---|
| IV - RV (volatility, current) | 9.28 |
| IV^2 - RV^2 (raw variance) | 2.14 |
| ln(IV^2) - ln(RV^2) (log variance) | 16.26 |

Raw variance was the WEAKEST. Squaring amplifies extremes: one 80% spike becomes
6400 in variance and dominates the mean while inflating the noise. Gold-miners
(VXGDX/GDX) flips sign under raw variance. Fragile.

Log variance was much stronger than plain volatility. The log compresses those
extremes.

So the question isn't "should I use variance," it's:

> "Raw variance was my weakest formulation, t = 2.1, and it flipped the sign on
> one pair. Log variance was much stronger than plain volatility. Is the log
> form what you'd use, and does raw variance being that weak suggest I've got a
> bug somewhere?"

Offer the bug possibility genuinely. Weak result can mean weak effect or wrong
code, and a good researcher says both.

**Sign convention.** Carr & Wu: premium = realized - swap rate, NEGATIVE when
insurance is overpriced. Yours: IV - RV, POSITIVE for the same thing. Flip
before comparing.

---

## Part 8: Question 2 - overlapping windows

Your analysis steps 21 trading days at a time and discards everything between.
Out of ~127 possible start points per year you keep ~12. You discard ~95% of
rows.

Why: overlapping windows are the serial-correlation problem. Every day as a
start point means consecutive measurements share 20 of 21 days, and the test
thinks it has 25x more independent info than it does. The 63.8% false-positive
engine.

Is there a middle path, a correction that uses the overlapping data without the
test becoming a liar. Two names he'll mention:

- **Newey-West** (HAC standard errors). Inflates the uncertainty estimate to
  account for overlap. Keep all the data, test knows to be more skeptical. Your
  analyze.py already has this; open question is whether to use it for the
  headline. Tricky part is choosing the "lag."

- **Hansen-Hodrick.** Related correction built specifically for the
  overlapping-forecast problem (originally currencies). Similar idea.

What to tell him you tried: the log formulation from Q1, partly hoping it would
cut the dependence. It didn't move, because non-overlapping sampling had already
removed the dependence. So the sampling design works; question is whether you
can relax it.

If a properly-lagged Newey-West is defensible here, you get most of that 95%
back. Big potential win.

---

## Part 9: Question 3 - ATM vs the whole surface

**Moneyness.** ATM = strike equals current price. Your recorder captures only
the ATM option.

**The volatility smile / skew.** IV isn't one number per stock, it's different
at every strike. Plot IV vs strike and you get a curve, not a flat line. For
indices it's a "skew": way-out-of-the-money puts (crash protection) have much
higher IV than ATM, because everyone wants crash insurance. That shape carries
real tail-risk information.

Your recorder sees none of it. One strike, one number, per ticker per day. You
sample the middle and ignore the wings.

**Why VIX is different.** Not backed out from one option. Built from a whole
strip of S&P options across many strikes, "model-free" (no Black-Scholes
assumption, just integrate the surface). That's the variance swap rate from
Part 7. Captures the skew and tail premium.

**You've measured the gap.** Four matched pairs, your ATM reading vs the Cboe
index: yours ~3.61 vol points BELOW, every time, same direction. That 3.6 is
roughly the skew premium you're not capturing.

The question:

> "I only record at-the-money. My reading runs about 3.6 vol points below Cboe's
> full-surface number, consistently. Is ATM defensible as a proxy, or do I need
> multiple strikes? Asking now because every day I record one strike is a day I
> can't re-collect."

**Why this has a deadline.** Historical option quotes aren't free after the
fact. Not recording strikes this week means that data is gone. Every other
question can wait; this one can't.

**Carr & Wu connection.** Their method needs the full surface. But the paper
says VIX approximates the 30-day variance swap rate, so for Sample A you can use
VIX^2 directly as the swap rate and get a near-replication for free. For your
own panel you're stuck with ATM unless you start recording strikes.

---

## Part 10: Vocabulary he'll use

| term | one line |
|---|---|
| implied volatility | movement forecast baked into an option price |
| realized volatility | how much the asset actually moved, measured after |
| variance risk premium | the gap; usually positive (options overpriced) |
| variance swap | real contract paying realized variance minus a fixed rate |
| variance swap rate | that fixed rate; risk-neutral variance forecast |
| risk-neutral | pricing as if nobody charged for risk; the "fair" benchmark |
| the skew / smile | IV varies by strike; puts cost more; tail-risk info |
| model-free | doesn't assume Black-Scholes (VIX is model-free) |
| moneyness | strike distance from current price; ATM = at the money |
| term structure | how IV differs across expiration dates (your "far leg") |
| HAR model | standard workhorse for forecasting volatility |
| Newey-West / HAC | fix for standard errors when observations overlap or cluster |
| serial / autocorrelation | today relates to yesterday; breaks independence |
| non-overlapping | sampling that steps far enough to avoid that |
| realized range | vol from the high-low range, not just close-to-close |
| Parkinson / Garman-Klass | range-based vol estimators, more efficient |
| t-statistic | effect / its uncertainty; ~2 borderline, ~5 strong |
| cross-sectional | comparing across entities (tickers) at one time |
| panel data | observations across both entities and time (what you collect) |

---

## Five things walking in

1. Implied vol is a forecast backed out of a price. Realized vol is what
   happened. The premium is the gap, usually positive because options are
   insurance.
2. You have ~6 independent observations, not 4,400, because tickers move
   together and days overlap. Your own simulation proves the naive approach lies
   9 times in 10.
3. Sample A exists to prove your code works on data where the answer is known.
   The strong move.
4. On variance: raw variance was your weakest formulation, log variance your
   strongest. Ask if that means a bug.
5. The ATM question has a deadline. If he says it's not enough, the recorder
   changes this week.
