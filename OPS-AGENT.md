# The operations agent

**Built 23 September 2026.** Designed 19 Sep, built and tested in one session: every
component below exists, runs, and is held to its contract by `tools/pressure_test.py`
(sections I, M, N and O, and `calibrate.py`). No LLM sits in the daily loop - that is what keeps it free.

## The one rule that decides everything

**The agent runs operations. It never searches for results.**

It records, checks, compares against references and reports. It never proposes,
ranks, scores or tests a hypothesis that is not already registered in `hypotheses/`,
because an agent hunting patterns in this data would destroy the pre-registration
that makes any of its numbers citable (assessed 16 Sep, reaffirmed 18-19 Sep; see
HANDOFF 17). Greg Jensen's argument on Odd Lots (11 Sep) - AI keeps markets
inefficient because frontier capability leapfrogs - is an argument for NOT competing
on compute. This project's edge is attention: nobody funded measures what free data
costs, because they buy OPRA.

Claude is for judgement - reading a result, drafting a write-up, deciding what a
number means - and is called by a person, not by a schedule.

## The components

| # | component | runs | does | fails loudly when |
|---|---|---|---|---|
| - | `record.yml`, `surface.yml` | CI, weekdays 14:47 / 14:57 UTC | record the panels (the irreplaceable part) | a run errors |
| - | `freshness.yml` | CI, 20:00 and 23:00 UTC daily | `panel_health` alone; installs nothing | a trading day is missed, a snapshot lands outside the session |
| 1 | `tools/bloomberg_prep.py` | by hand, before a terminal session | names both expiries, the strike range, the landing window, what to write down | - |
| 2 | `tools/daily.py` | by hand, any time | pull, panel health, pressure test, H3 reading, H5e tally, one verdict | any FAIL or crash (a crash is never a pass) |
| 3 | `health.yml` | CI, weekdays 23:37 UTC | `daily.py` on the runner; report on the run page; never commits | any FAIL or crash - GitHub emails |
| 4 | `tools/hooks/pre-push` | every push to main | runs the pressure test on the tree being pushed | a FAIL or crash blocks the push |
| 5 | `SESSION-START.md` | every Claude session, via `CLAUDE.md` | one screen of orientation; live state comes from `daily.py` | - |
| 6 | `tools/opra_reference.py` | by hand | OPRA quotes at the recorder's own minute; prices every request first | a request over $0.50 or past the $100 lifetime cap is refused |
| 7 | `tools/notify.py` + `tools/launchd/install.sh` | this Mac, weekdays 13:30 local, once Gabriel installs it | pulls a separate clean clone (`~/.volrec-ops`), runs `daily.py`, texts the one-line verdict by iMessage | LOOK AT leads the message; a failed send never fails the check |

The watchdog routine (Wednesdays 16:13 UTC, outside GitHub) was rewritten 23 Sep: it
fetches the current code, builds Python 3.12, runs `daily.py`, checks all four
workflows are active, and notifies only when something is wrong. It runs on
Gabriel's Claude usage - its 16 Sep run failed on a session limit - which is why
`health.yml` and the iMessage job, which cost nothing, carry the daily load.

## Design decisions, and why

- **health is a separate workflow from freshness.** freshness installs nothing, so
  the missed-day alarm can never break on a dependency. health needs `requests` and
  `pyyaml`; if it ever breaks, the alarm that matters most keeps working.
- **health never commits.** Two recorders push to main every weekday; a third
  committer would only add push races against the irreplaceable data. The report
  goes on the run page instead.
- **CI reads with r=0.** The FRED cache is gitignored under FRED's terms, so the
  runner discounts at zero and its H3 number differs from the local one by ~0.02.
  `daily.py` says so on the line; **the local reading is the reading of record.**
- **The hook tests the working tree**, which is what was just committed in the
  normal flow. `git push --no-verify` exists for an emergency and should be
  explained in the commit message.
- **The iMessage job pulls its own clone, never the working copy.** A pull into a
  tree with uncommitted edits fails, and a failed pull would text a false alarm.
  It costs nothing: no LLM, no service - macOS Messages, driven by AppleScript, with
  the text passed as data. Installing it changes Gabriel's Mac, so he runs the
  installer; nothing else ever does.
- **OPRA is priced before it is fetched, every time.** Databento's own `get_cost`
  runs first; the ledger lives beside the data, outside the repo. The dry run caught
  a timestamp bug (every minute read as local time, seven hours off) before a single
  request was priced.

## When workflows may be edited

The rule that matters is narrower than "Saturdays only", which this file said on
19 Sep: **never edit `record.yml` or `surface.yml` on a day whose run is still
needed** - the 16 Sep loss followed a schedule edit pushed between the trigger and
the delayed run. A new or non-recorder workflow may be added before 14:00 UTC after
it passes the pressure test, with one manual run straight after; `health.yml` went in
that way on 23 Sep and ran green in 32 seconds.

## What it must never do

- Propose, rank or test a hypothesis that is not already registered.
- Write to `data/`, which only the recorders write.
- Edit a recorder's `schedule:` on a day whose run is needed.
- Put a Bloomberg export, an OPRA file, a key, or any spreadsheet inside the repository.
- Change a registered threshold, bucket, bar, band or window.
- Spend money without pricing the request first.

## Not in scope, deliberately

Trading, signals, screeners, backtest loops, broker connectors, correlation searches
(Kalshi, news-to-market) - ruled out in HANDOFF sections 1 and 5 and reaffirmed 23 Sep.

## Possible next pieces, not built

- A weekly digest in `health.yml` (Fridays): days recorded, gate results, the H5e and
  H5f tallies, days left to 11 Nov. Only worth it if the daily report goes unread.
- Pass a FRED key to CI as a repository secret, so CI's reading matches the local one.
