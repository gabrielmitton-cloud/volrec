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
| H2a | side | hypotheses/2026-09-09-h2-variance-formulation.md | holds (raw variance weakest); 28 Oct review: its pooled t treats the equity pairs' shared episodes as independent - date-clustered companion in test_h2_variance.py | | - |
| H2b | side | same | not supported; 28 Oct review: the verdict line tested correlation with the IV level, not the registered autocorrelation - per-pair autocorrelation companion beside it | | - |
| H2c | side | same | see file | | - |
| H4a | side | hypotheses/2026-09-13-h4-hedged-gains-across-the-surface.md | not yet (strike 2 of 3) | | - |
| H4b | side | same | not yet | | - |
| H4c | side | same | not yet | | - |
| H6a | side | hypotheses/2026-10-08-h6-implied-vol-vs-technical-levels.md | FAILS | | - |
| H6b | side | same | holds | | - |
| TimesFM | side (analysis/) | CLAUDE.md, HANDOFF | FAILS against HAR | | - |
| P1-P5 | exploratory (lab/) | lab/REGISTRATION.md | P1 fails, P2 holds as written, P3 holds, P4 fails, P5 holds among funds with a paper profit | | - |

Not a test of any hypothesis, and not counted below: **the reproduction check** (17 Oct 2026). Every
recorded number was computed a second time by an implementation written from the registration text,
sharing no code with the reader that produced it:

| test | how | result |
|---|---|---|
| H3, H5e, H7 | `tools/independent_replica.py` vs modelfree / h7_reader, same data | 661 of 661 values agree (largest gap 0.0009, one exact strike tie) |
| H5f | exact fractions on the same OPRA files | every figure identical; H5f-a's median is exactly 1/2 (226 below, 34 on, 206 above) |
| H5a, H5b | a second Bloomberg-export reader | **found a reader bug** (an omitted cell dropped the put; fixed 17 Oct). Corrected: H5a 0.33 over 179 (was 0.40 over 169), H5b 44 of 44 (was 36 of 36); both verdicts unchanged |
| H1, H2 | second implementation on a SECOND price source (Yahoo); the project's code on that same data matches it exactly | every count and conclusion reproduced; H2a's raw-variance form is vendor-sensitive (p 0.074 on Yahoo, 0.033 on Alpaca); H1c's 87.3% counts flat days as positive (strictly positive 87.1%) |
| H6 | second implementation, second price source | same N in all 9 pairs; H6a fails 0 of 9, H6b holds (-0.084 vs -0.089) |
| H4 | second implementation, same data | 8,977 runs; every bucket, the pooled mean and the date row identical |
| TimesFM | re-scored from the saved forecasts (the model was not re-run - FRED terms) | -3.9% and 52.9%, identical; all 225 targets re-derived |
| lab P1-P5 | full rebuild from the raw OPRA files | 627 of 628 trades identical (one exact strike tie); P3 identical; Leak Map identical at 5% and 20% (every Shapley leak, range and called month - so P1, P2, P5); Break-Even crossings identical; P4 fails 1 of 5 as recorded (from ~2,500 raw weekly chains); stress: block 1.0, crash replays exact, bootstrap within Monte Carlo noise |
| H8 (pilot, not registered) | second implementation, same OPRA files | the reader's gaps identical on all eight funds over the same days; the ATM yardstick identical on 7 of 8 (GLD within 0.002); the draft's calibration figures were taken on 10-12 Oct, before a few OPRA days had arrived, so they differ by up to 0.003 |

**Count, as of 16 Oct 2026 (counted from the rows above):** 24 registered tests with a prediction - 12
confirmatory (H3 x3, H5 x7, H7 x2), 3 validation, 9 side (H2 x3, H4 x3, H6 x2, TimesFM) - plus 2 descriptive
rows (H5c, H7c), the 11 pairs inside H1a (already corrected there), and 5 exploratory lab predictions.
Recount at write-up. Every "see file" cell is filled from the file at that time, not from memory.
