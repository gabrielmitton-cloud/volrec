# SCCUR 2026: what to say at the poster (Sat 21 Nov, SDSU)

*Drafted 4 Nov 2026 by Vega for practice before 21 Nov. Every number is the poster's own (`poster/build_poster.py`
copies each from a dated record). Two lines wait for the H5e and H7 readings (12-19 Nov) and are marked
**[after 19 Nov]**; fill them from the hypothesis files, never from memory. Read aloud, the 2-minute version
runs about two minutes.*

The session is 75 minutes standing at the poster, with people arriving one or two at a time. So the talk is
not a speech: a 30-second opener for everyone, the 2-minute walk for anyone who stays, then questions.

## The 30-second opener

> Students and small researchers price options with free quotes, because the full market feed costs thousands
> of dollars a year. I asked what that free data gives up, and where the loss is: in the quotes themselves, or
> in the recipe that turns quotes into a volatility number. Since September I've recorded a free feed every
> trading day and checked it against Cboe's indices, the consolidated market and Bloomberg. Short answer: the
> free quotes are close. Most of the error is in the recipe.

*If H7 fails, the poster's headline changes by itself, to "Widen the strikes, and free data lands within a point
of Cboe's index." Then the opener's last two sentences become: "Short answer: widen the strikes, and free data
lands within a point of Cboe's index. Whether the rest of the gap is the quotes or the recipe is still open."*

## The 2-minute walk (left to right across the poster)

1. **The question (left column).** Free quotes versus the paid feed: what precision is lost, and where.
2. **What I did.** Code records Alpaca's free feed every trading day: 109 tickers, plus full strike ranges for
   eight funds and stocks. Three references: Cboe's published indices, OPRA (the consolidated market) and
   Bloomberg.
3. **The quotes (centre, top).** Point at the three numbers. Far-strike free quotes sit a median of a third of
   a bid-ask spread from Bloomberg's, and half a spread from the consolidated market at the same minute. And
   when the free feed shows no bid, the professional feed has no bid either: 64 of 64.
4. **The recipe (centre, chart).** Cboe's formula integrates across strikes. With only strikes within 10% of
   the price, the estimate misses Cboe's index by about 4 points on average, and oil by 12. Widen to 30% and
   the average gap is 0.6. On that day SPY came out at 15.83 against a VIX of 15.84. The reason is in the
   chart's note: a fixed 10% band covers 2.2 standard deviations of a calm fund but only 0.6 of crude oil.
5. **How it stays honest (left).** Every pass/fail bar was written and dated in a public repository before
   its test ran, and the two open tests were also frozen on OSF. A second program sharing no code recomputed
   every recorded number. Failures stay in the same table as successes.
6. **Every registered test (right).** Point at a FAILS row on purpose: H6a (0 of 9) is the clearest.
   **[after 19 Nov]** Then H5e's and H7's final readings, one sentence each, read off the table.
7. **Limits.** One free feed, about two months, one snapshot a day before the close, European formulas on
   American options.

## Questions you are likely to get, with short answers

**What is a volatility index?** A number for how much the market expects a fund to move over the next month,
read from option prices. VIX is the one for the S&P 500; OVX is crude oil's, GVZ gold's.

**Why does it matter who gets this right?** If the error is in the method, not the data, anyone without a data
budget can remove most of it for free.

**What is a "recipe" here?** The steps from quotes to one volatility number: which strikes to include, what to
do with a strike nobody bids on, how to count days. Cboe publishes its own; the poster tests what changes when
you follow it on free quotes.

**What does pre-registered mean, and why bother?** I wrote down each test and its pass/fail bar, dated and
public, before running it. For the forward-looking tests that was also before the data existed - H5 after
one day of its wing data, which its file says - while the ten-year validation and one side study used history
that already existed. It stops me from choosing the test after seeing the answer.

**Did anything fail?** Yes, and it's on the poster: H6a (implied volatility did not beat a simple 14-day
average at forecasting the next day's range: 0 of 9 pairs) and H2b (not supported). H5e's first reading failed too (0.90
against a bar of 0.5). **[after 19 Nov]** Add the final readings.

**Isn't two months too short?** For a long-run claim, yes; the poster says so under Limits. Each test fixed its
window and minimum number of days in advance, and the validation used ten years of Cboe's own data, where the method found the known result:
the volatility risk premium on 9 of 11 pairs.

**What is the volatility risk premium?** Implied volatility usually sits above the volatility that follows:
option sellers are paid for carrying the risk. It is well documented, so finding it checks the method.

**Why Alpaca?** It's a free retail brokerage feed anyone can sign up for, which is the point: the question is
what a person without a data budget gets.

**Is the free feed allowed to be published?** Alpaca agreed in writing (10 Oct) to personal, non-commercial use.
Cboe approved the use of its files on 4 Nov. Bloomberg and OPRA data are licensed, so only aggregates appear,
with credit lines (bottom right).

**Did you use AI?** Yes, and the poster says so: the code was written with an AI coding assistant (Claude Code);
the question, decisions and interpretation are mine. *(SCCUR's policy: acknowledge it and be able to explain
every method without AI - which is what this page is for.)*

**What's next?** Final readings of H5e and H7 (12-19 Nov), a confirmatory test on all eight funds (registered
first, Dec-Jan), and the paper in 2027, failures included.

## Things not to say

- Any H5e or H7 number before its reading is recorded in the hypothesis file.
- "Free data is as good as Bloomberg." The poster's claim is narrower: the quotes are close, on the funds and
  days measured.
- Anything that sounds like trading advice.

## Practice

Say the 30-second opener until it fits in one breath-paced half minute. Then walk the poster with a friend
(or a phone recording) and answer three random questions from the list without reading them.

## Mock judging (added 5 Nov 2026): the harder questions

Run it with Vega any day before 21 Nov: say **"judge me"**. Vega plays a judge who has read nothing: the
30-second opener, the 2-minute walk, then six questions mixed from both lists, one at a time, with a score
after each. No scripted answers below on purpose: each line says what a good answer must contain.

1. **"The free feed is altered by design. Isn't the answer obviously 'it's worse'? By how much, in what
   units?"** - the size at the same minute, in volatility points and as a fraction of the spread, from the
   recorded readings (README's results table); "worse" is not the question, "where" is.
2. **"Your snapshot is about 80 minutes before the close. How do you know the gap isn't just timing?"** -
   measured, not assumed: a median 0.53 volatility points between 14:30 and 15:55 on stress days (GLD 0.14),
   beside H7's 0.25-0.30 bars. The OPRA comparison takes the 80 minutes out, not all timing: each free quote is
   matched to OPRA's record within two minutes, and the snapshot reading keeps the free feed's stale quotes on
   purpose, as a user would see them.
3. **"You designed and graded your own tests. Why should I trust them?"** - dated, public registrations
   before each test was run, and before the data for the forward-looking ones (H5 after one day of it);
   failures shown (H6a, H2b, H5e's first reading); an auditor proves every safeguard fails when broken.
4. **"What is n_eff, and why do you report it?"** - daily gaps persist, so 40 days are not 40 independent
   points; T(1 - rho)/(1 + rho); it sets how small an effect the data can see.
5. **"How do you show two feeds are the same, not just 'not significantly different'?"** - an equivalence
   test (two one-sided tests against +/-0.10 points) for H8; failing to find a difference is not evidence
   of none; fixed-b critical values because the days are correlated.
6. **"Isn't your +/-30% strike band a choice that drives the result?"** - yes, and that is the finding:
   +/-10% reads oil 12 points light, +/-30% brings the mean gap to 0.59 (H3); truncation grows with
   volatility (Jiang and Tian's mechanism).
7. **"VIX is built on S&P 500 index options and you record SPY. Apples and oranges?"** - for VIX, VXN and
   RVX, yes, and the poster says so; OVX and GVZ are built on USO's and GLD's own options, so the main tests
   use those.
8. **"What result would change your conclusion?"** - name it before being asked: a failed final reading
   [after 19 Nov: say which held], or H8 finding the feeds not equivalent on most funds; either is reported.
9. **"Who is this for?"** - anyone without a data budget: it says what to fix first (method choices) and
   what the free quotes can carry.
10. **"With $10,000, what would you buy?"** - the scope limits in order: a second free feed, a longer
    window, more underlyings - not a fancier model.

**Score per answer (Vega keeps the tally):** under 30 seconds; a number with its unit and source; the limit
said before being asked; no H5e or H7 number before it is recorded; nothing that sounds like trading advice.
