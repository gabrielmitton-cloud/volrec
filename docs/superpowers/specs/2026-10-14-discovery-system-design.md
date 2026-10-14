# The discovery system: design (agreed 14 Oct 2026; vault sealed the same day; agents not yet built)

**Gabriel's aim:** agents that look for something special and derive something important, not only
critics, with "the best possible outcomes/system." **Chosen design: option C** - explore on half the
history, confirm on the sealed half, then confirm again on data that does not exist yet.

## Why a vault
Many searchers over one dataset always find patterns, and most are noise. The vault makes discovery
honest: explorers never see the sealed half, so any pattern they report is a prediction about data
nobody has examined, and it is either confirmed or not.

## The vault (sealed 14 Oct 2026, `lab/vault.py`)
- Unit: calendar quarters 2016Q1-2026Q3 (43), because adjacent days are correlated.
- Stress quarters split evenly. Sealed: 2018Q1 (Volmageddon), 2020Q1 (COVID), 2022Q2. Open: 2018Q4,
  2024Q3, 2025Q2.
- Fixed by seed 20261014 and sha256 fingerprint e4a02cd5...; a lab test and an auditor mutant
  (vault-resealed) fail if the split changes.
- The second vault is the future: H8's window (1 Dec 2026 - 29 Jan 2027) and the live panel after the
  November verdicts. Nothing in it exists yet.
- Scope: NEW questions only. The lab's registered questions were answered on the whole history first.

## The agents (roles; built when the time comes)
- **Explorers** (open half only): pattern miner; anomaly hunter; cross-connector (free-data error x
  spreads x stress); mechanism explainer (no mechanism, flagged as likely noise).
- **Derivers:** hypothesis writer (PROTOCOL.md template, registered before the vault opens);
  forking-paths accountant (a ledger of every pattern any agent examined, so the count of tries is
  honest); practitioner translator (rules for data users; feeds the trust engine); theory builder (one
  model that explains the findings together).
- **Critics:** methods skeptic; statistician; cold replicator; novelty checker; licensing auditor;
  professor-reader.
- **Communicators:** abstract and poster writer; interview coach; visual designer.
- **Stewards:** data steward (licences, ledger, nothing raw leaves); vault keeper (enforces the seal).

## Rules
1. Explorers read only open quarters (`vault.is_sealed(day)` false) and only data already owned.
2. Every pattern examined goes in the accountant's ledger, kept or not.
3. A pattern counts only if it is registered (git + OSF) before the vault opens, then confirmed on
   the sealed half, then confirmed again on future data. Failures are reported as failures.
4. Another company's model may review text and aggregates only, never licensed raw data (OPRA,
   Bloomberg, LSEG).
5. Nothing here changes a registered verdict.

## Timing
After the 12-19 Nov verdicts and H9's registration: explorers and derivers on the open half
(December); register survivors; open the sealed half (January); confirm on H8's window and the live
panel (February); critics and communicators on the finished draft. Each phase gets its own plan.
