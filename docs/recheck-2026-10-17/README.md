# The whole-project re-check, 17 October 2026

Gabriel asked whether a bug found in one hypothesis's code could be hiding in others. Every recorded result was
computed a second time by code written from the registration text that shares nothing with the reader that first
produced it, and compared figure by figure. These scripts are that evidence, kept as they ran (paths made
portable). The H3, H5e and H7 rebuild lives in `tools/` as a maintained tool (`independent_replica.py`,
`independent_check.py`), because it runs again at verdict time.

**Result: one real bug, now fixed; everything else reproduced.** Bloomberg's exports leave an empty implied-volatility
cell out of the file, and `tools/bloomberg_compare.py` read cells in order, so it dropped those rows' puts. Corrected
beside the originals, dated, verdicts unchanged: H5a 0.33 over 179 wing contracts (was 0.40 over 169), H5b 44 of 44
(was 36 of 36). TEST-INVENTORY.md has the full table.

| script | reproduces | inputs | result |
|---|---|---|---|
| `h5f.py` | H5f a/b/c, exact fractions | surface CSVs + OPRA files (licensed) | identical; H5f-a's median is exactly 1/2 |
| `h5ab.py` (+ `bloomberg_reader.py`) | H5a, H5b | surface CSVs + Bloomberg exports (licensed) | found the reader bug; 179, 0.33, 44 of 44 |
| `long_fetch.py` then `h1.py`, `h2.py`, `h6.py` | H1, H2, H6 | a SECOND price source (Yahoo) + Cboe/FRED index closes | every count and conclusion; H2a's raw-variance p is vendor-sensitive; H1c's 87.3% counts four flat days |
| `h4.py` | H4 (strike 2) | surface CSV + dividends | 8,977 runs, every bucket identical |
| `timesfm_score.py` | the TimesFM benchmark | the saved forecasts (no model re-run) | -3.9%, 52.9%, 225 of 225 targets |
| `lab_trades.py` | lab trades, P3 | OPRA lab files (licensed) | 627 of 628 (one exact strike tie) |
| `lab_leak.py` | the Leak Map: P1, P2, P5 | OPRA lab files + fund closes (licensed) | identical at 5% and 20% |
| `lab_stress.py` | the stress lab | as above | block 1.0, replays exact, bootstrap within noise |
| `lab_breakeven.py` | the Break-Even VIX | as above | all five crossings identical |
| `lab_p4.py` | P4 | ~2,500 weekly OPRA chains (licensed) | fails 1 of 5, as recorded |
| `h8.py` | the H8 pilot figures | surface CSV + OPRA files (licensed) | the reader identical on all eight funds |

Run from the repo root with the framework python. `long_fetch.py` writes to `RECHECK_WORK` (default
`~/volrec-recheck`), outside the repository; licensed files are read where they live and never copied. Output is
aggregates only. *Data provided by Databento (OPRA consolidated NBBO). Bloomberg figures: Source: Bloomberg
Finance L.P.*
