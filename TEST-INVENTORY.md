# Every test this project ran (the count the paper must disclose)

Created 16 Oct 2026 after the cold review: a reader can only judge the results knowing how many tests
were run in total. This is the skeleton of the paper's section 5 table. Verdicts are copied from the
hypothesis files, never re-judged here; p-values and intervals are filled at write-up time
(`tools/describe.py` for the daily series; each file's own statistic otherwise), and the Holm column
comes from `describe.holm()` over the confirmatory rows. **No bar, window or verdict changes.**

Roles: **confirmatory** = forward-looking, registered before its data existed (the paper's question);
**validation** = the method checked on a known result; **side** = registered, answers a side question;
**descriptive** = no prediction registered; **exploratory** = lab/, its own registration, outside the paper's
question.

| test | role | file | verdict (as recorded) | p / interval | Holm (confirmatory) |
|---|---|---|---|---|---|
| H3a | confirmatory | hypotheses/2026-09-12-h3-free-data-model-free.md | series running | | |
| H3b | confirmatory | same | series running | | |
| H3c | confirmatory | same | series running | | |
| H5a | confirmatory | hypotheses/2026-09-19-h5-wing-quote-quality.md | holds, weakly (23 Sep); registered after one wing day | | |
| H5b | confirmatory | same | holds (23 Sep) | | |
| H5c | descriptive | same | descriptive | - | - |
| H5d | confirmatory | same | see file | | |
| H5e | confirmatory | same | first verdict FAILS (8 Oct); final due 12 Nov | | |
| H5f-a | confirmatory | same | see file (sat exactly on its bar, 0.500) | | |
| H5f-b | confirmatory | same | see file | | |
| H5f-c | confirmatory | same | see file | | |
| H7a | confirmatory | hypotheses/2026-10-08-h7-free-feed-cboe-replica.md | due 12 Nov | | |
| H7b | confirmatory | same | due 12 Nov | | |
| H7c | descriptive | same | descriptive, as registered | - | - |
| H1a | validation (11 pairs, BH and BY inside) | hypotheses/2026-09-06-h1-vrp-long-sample.md | holds, 9 of 11 | | - |
| H1b | validation | same | holds on the stated test, picture mixed | | - |
| H1c | validation | same | holds | | - |
| H2a | side | hypotheses/2026-09-09-h2-variance-formulation.md | holds (raw variance weakest) | | - |
| H2b | side | same | not supported | | - |
| H2c | side | same | see file | | - |
| H4a | side | hypotheses/2026-09-13-h4-hedged-gains-across-the-surface.md | not yet (strike 2 of 3) | | - |
| H4b | side | same | not yet | | - |
| H4c | side | same | not yet | | - |
| H6a | side | hypotheses/2026-10-08-h6-implied-vol-vs-technical-levels.md | FAILS | | - |
| H6b | side | same | holds | | - |
| TimesFM | side (analysis/) | CLAUDE.md, HANDOFF | FAILS against HAR | | - |
| P1-P5 | exploratory (lab/) | lab/REGISTRATION.md | P1 fails, P2 holds as written, P3 holds, P4 fails, P5 holds among funds with a paper profit | | - |

Not a test of any hypothesis, and not counted below: **the reproduction check** (17 Oct 2026). Every reading
above that this project computes - H3's band and wide estimates, H5e's skip rule, H7's two Cboe replicas - was
computed a second time by an independent implementation written from the method text alone
(`tools/independent_replica.py`; comparison `tools/independent_check.py`): 661 of 661 values agree within 0.01
points, largest gap 0.0009 (one exact strike tie, documented). Rerun once at verdict time beside the companions.

**Count, as of 16 Oct 2026 (counted from the rows above):** 24 registered tests with a prediction - 12
confirmatory (H3 x3, H5 x7, H7 x2), 3 validation, 9 side (H2 x3, H4 x3, H6 x2, TimesFM) - plus 2 descriptive
rows (H5c, H7c), the 11 pairs inside H1a (already corrected there), and 5 exploratory lab predictions.
Recount at write-up. Every "see file" cell is filled from the file at that time, not from memory.
