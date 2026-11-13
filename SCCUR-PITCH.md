# SCCUR 2026: what to say at the poster (Sat 21 Nov, SDSU)

*Drafted 4 Nov 2026 by Vega for practice before 21 Nov. Every number is the poster's own (`poster/build_poster.py`
copies each from a dated record). Two lines wait for the H5e and H7 readings (12-19 Nov) and are marked
**[after 19 Nov]**; fill them from the hypothesis files, never from memory. Read aloud, the walk ran about two
minutes on 4 Nov; the 8 Nov rewrite, with its caveats, runs about two and a half (about 350 spoken words).*

*Filled 13 Nov 2026 by Vega, from the hypothesis files, after the readings: H5e's FINAL (12 Nov) fails, H7a fails
and H7b holds (13 Nov), H3's reading of record holds (13 Nov). So the printed headline is the pre-decided fallback,
and the lines marked **[after 19 Nov]** below now carry the recorded numbers (the mark is kept to show where).*

**Where and when (SCCUR's email, read 11 Nov):** Sat 21 Nov, Session 2, 9:30-11:00 am, Montezuma Hall in the
Conrad Prebys Aztec Student Union, San Diego State; poster board 12, under the poster's own title. Ten minutes to
set up (double-sided tape on the supply tables in the room), the whole 75 minutes at the poster, five minutes to
take it down at the end. No schedule changes are possible.

The session is 75 minutes standing at the poster, with people arriving one or two at a time. So the talk is
not a speech: a 30-second opener for everyone, the 2-minute walk for anyone who stays, then questions.

## The 30-second opener

> Students and small researchers price options with free quotes, because the full market feed costs thousands
> of dollars a year. I asked what that free data gives up, and where the loss is: in the quotes themselves, or
> in the recipe that turns quotes into a volatility number. Since September I've recorded a free feed daily
> and checked it against Cboe's indices, the consolidated market and Bloomberg. Short answer: widen the strikes,
> and free data averages within a point of Cboe's index. Whether the rest of the gap is the quotes or the recipe
> is still open.

*Updated 13 Nov: H7a failed and H3 held, so the poster prints the fallback headline and the opener ends as above.
The 4 Nov draft ended "Short answer: the free quotes are close. Most of the error is in the recipe." Do not say
that now: on oil, the free and full-market rebuilds differed by more than their bar.*

*If H7 fails, the poster's headline changes by itself (Gabriel's rule of 21 Oct, worded 11 Nov), and which way
depends on H3. If H3 holds, it reads "Widen the strikes, and free data averages within a point of Cboe's index."
Then the opener's last two sentences become: "Short answer: widen the strikes, and free data averages within a
point of Cboe's index. Whether the rest of the gap is the quotes or the recipe is still open." If H3 fails too, it
reads "Free data misses Cboe's index by a point or more, on average." Then the opener ends: "Short answer: free
data misses Cboe's index by a point or more on average, and where that loss comes from is still open." Never say
"within a point" then, because H3's bar failed. Look at the printed headline and say what it says.*

## The 2-minute walk (the poster's numbered sections, left to right)

*Rewritten 8 Nov 2026 for the redesigned poster (graphs first, the tests as a strip of chips; the main chart
counts the days at each size of gap, with no dates and never Cboe's index itself, because the request Cboe
approved on 4 Nov promised aggregate statistics only). H3's numbers are live
until its reading of record (the one after 11 Nov): read them off the printed tile, not from this page.*
*13 Nov: the reading of record is in, and the printed tile carries it: 0.71 over 205 readings, against 1.0.*

1. **The headline, then 1 (left).** Free quotes versus the paid feed: what precision is lost, and where. If
   the loss is in the method, anyone without a data budget can fix most of it for free.
2. **2 What I did (left, the flow).** Alpaca's free feed, recorded daily since September. The VIX formula, with
   strikes and expiries I chose, turns each fund's quotes into one volatility number a day, checked against
   Cboe's indices, the full market feed and Bloomberg.
3. **3 The main chart (centre).** The blue line is Cboe's index; each bar counts the days free data landed
   that far from it, and the band is within a point. Left of the line reads low. The tile: the average gap,
   against a bar of 1.0 set beforehand. Then oil: the widest spread, mostly low.
4. **4 The quotes (right, top).** 64 of 64: when the free feed shows no bid on a far strike, neither does the
   full market. The filled dots: the free price sits a third of a spread from Bloomberg's and half a spread
   from the full market's, at or under the bar. The caveat: where both feeds bid, the hollow dots, it is 0.67,
   over the bar, though only a tick or two.
5. **5 The recipe (right).** A fixed 10% band of strikes sees 97% of a calm fund's likely moves but only 45%
   of oil's. Widen it to 30% and the average gap falls from 3.97 to 0.59 points on one calibration day; SPY's
   estimate read 0.01 points under the VIX. That shows coverage matters; it does not by itself rule out the
   feed, the timing or the index-versus-fund difference.
6. **How it stays honest (left).** Every bar was dated in a public repository before its test ran. On 17 Oct
   a second program sharing no code recomputed every result and caught one bug, fixed; no verdict changed.
7. **The strip (bottom).** Every registered test is a chip: a tick, a cross, or due. Point at a cross on
   purpose: H6a, 0 of 9. **[after 19 Nov]** Then H5e's and H7's final readings, one sentence each, off their
   chips: "Dropping empty bids did not fix oil: 0.91 against a bar of 0.5, though it was closer on 26 of 35
   days." "Through Cboe's own rules, gold's free estimate matched GVZ, 0.172 against 0.30, but on oil the free
   and full-market rebuilds were 0.316 apart, over their 0.25 bar, so H7a fails."
8. **Limits (left, bottom).** One free feed, about two months, one snapshot a day, European formulas on
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

**Did anything fail?** Yes, and it's on the poster, in the strip of chips: H6a (implied volatility did not beat the 14-day
average range at forecasting the next day's range: 0 of 9 pairs) and H2b (not supported). H5e's first reading failed too (0.90
against a bar of 0.5). **[after 19 Nov]** Add the final readings: H5e's final failed (0.91 against 0.5, 12 Nov), and
so did H7a (oil's free and full-market rebuilds 0.316 apart, bar 0.25, 13 Nov). H7b held (gold, 0.172 against 0.30).

**Why did H7a fail?** On oil, Cboe's rules keep walking out to strikes beyond the free file's edge (+/-60% of the
price): they did on 24 of 24 days, and the full market carries those strikes. On the strikes both feeds carry,
the two rebuilds differ by 0.132 instead of 0.316. I wrote that comparison down on 17 Oct, before any reading, as
a description beside the test, never in its place: the test failed as registered, and the poster says so.

**Isn't two months too short?** For a long-run claim, yes; the poster says so under Limits. Each test fixed its
window and minimum number of days in advance, and the validation used ten years of Cboe's own data, where the method found the known result:
the volatility risk premium on 9 of 11 pairs.

**What is the volatility risk premium?** Implied volatility usually sits above the volatility that follows:
option sellers are paid for carrying the risk. It is well documented, so finding it checks the method.

**Why Alpaca?** It's a free retail brokerage feed anyone can sign up for, which is the point: the question is
what a person without a data budget gets.

**Is the free feed allowed to be published?** Alpaca agreed in writing (10 Oct) to personal, non-commercial use.
Cboe approved the use of its files on 4 Nov, for non-commercial research, aggregates only, credited. Bloomberg
and OPRA data are licensed, so only aggregates appear, with credit lines (bottom right).

**Why does the chart count days instead of drawing the VIX?** My request to Cboe, approved on 4 Nov, said
only aggregate statistics would appear, "for example, average differences between my estimates and the index".
Counts of days by gap are that; a dated line of the index, or of each day's gap, is not. No index level is
printed anywhere on the poster: even the calibration day appears as a difference (SPY's estimate 0.01 points
under the VIX).

**Did you use AI?** Yes, and the poster says so: the code, the charts and draft wording were produced with AI
assistants (Claude Code), and a second AI model reviewed the work; the question, decisions and interpretation
are mine. *(SCCUR's policy: acknowledge it and be able to explain
every method without AI - which is what this page is for.)*

**What's next?** H5e and H7 were read on 12 and 13 Nov, as written in advance. Next: a confirmatory test on eight
funds and stocks (registered first, Dec-Jan), and the paper in 2027, failures included.

## Things not to say

- Any H5e or H7 number before its reading is recorded in the hypothesis file.
- "The free quotes are close; most of the error is in the recipe" (the headline before H7a failed), or that the
  free feed matched the full market on oil. It did on gold; on oil H7a failed.
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
   purpose, as a user would see them. *Since 13 Nov, also the registered timing measurement (read once, 16 days,
   21 Oct - 11 Nov): at the snapshot minute the full-market rebuild sat a mean absolute 0.021 points from OVX and
   0.010 from GVZ, and the indices then moved a mean absolute 0.630 and 0.207 before the close; the free feed sat 0.369 from OVX
   at the minute. It describes the gaps; the verdicts stand.*
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
   [after 19 Nov: say which held] (13 Nov: H3 and H7b held; H5e's final and H7a failed, and both are on the
   poster), or H8 finding the feeds not equivalent on most funds; either is reported.
9. **"Who is this for?"** - anyone without a data budget: it says what to fix first (method choices) and
   what the free quotes can carry.
10. **"With $10,000, what would you buy?"** - the scope limits in order: a second free feed, a longer
    window, more underlyings - not a fancier model.

**Score per answer (Vega keeps the tally):** under 30 seconds; a number with its unit and source; the limit
said before being asked; no H5e or H7 number before it is recorded; nothing that sounds like trading advice.

*OPRA and intraday index figures: Data provided by Databento. Bloomberg figures: Source: Bloomberg Finance L.P.
Index closes: Cboe Global Markets. Aggregates only.*
