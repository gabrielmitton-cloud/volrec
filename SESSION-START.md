# Session start — one screen, read this before anything else

volrec measures what free, retail-grade option data costs a researcher, against
authoritative references (Cboe's published indices, Bloomberg). It runs itself; a
session's job is to read results, answer a question, or do one bounded thing.
(OPS-AGENT.md item 5, 23 Sep 2026. It holds only what does not go stale.)

## Read in this order, and stop as soon as you know enough

1. **This file.**
2. **The live state** - never trust a document for it:
   `.../python3 tools/daily.py` -> did today land, 0 fail / n warn, the H3 reading,
   the H5e tally, and ALL CLEAR or LOOK AT.
3. **The newest dated subsection of HANDOFF.md section 17** (headed by a date).
   The rest of HANDOFF is history: read it only when a task needs the reasoning.
4. **The hypothesis file the task touches**, in `hypotheses/`.

## Commands (always the framework python; Homebrew's has no `requests`)

    PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
    $PY tools/daily.py                           # the whole daily check
    $PY tools/pressure_test.py                   # before and after ANY change: 0 fail
    FRED_KEY=use-cache $PY modelfree.py --wide   # H3 + H5e; without the prefix r=0
    FRED_KEY=use-cache $PY hedged.py             # H4, descriptive until ~40 date pairs
    $PY tools/bloomberg_prep.py --date YYYY-MM-DD      # before a terminal session
    $PY tools/bloomberg_compare.py --date D --pull-time HH:MM   # after one
    $PY tools/opra_reference.py --date D --dry-run     # Databento: cost first, always
    $PY tools/opra_reference.py --all                  # fetch what Databento has released
    $PY tools/opra_reference.py --all --compare        # free feed vs OPRA, same minute
    $PY tools/daily.py --notify                        # and text the verdict (tools/notify.py)

`analysis/` runs in `.venv` instead. Pushes to main run the pressure test through
`tools/hooks/pre-push` (install per clone: `git config core.hooksPath tools/hooks`).

## What runs unattended (UTC; all weekdays unless noted)

| what | when | if it goes wrong |
|---|---|---|
| `record.yml` (ATM panel) | 14:47 cron, lands 3-5h later | `freshness` FAILS on a missed day, and emails |
| `surface.yml` (strike surface + wide band) | 14:57 cron | same |
| `freshness.yml` | 20:00 and 23:00 daily | installs nothing, on purpose |
| `health.yml` | 23:37 | the full daily check; emails on any FAIL or crash |
| launchd `com.volrec.daily` (this Mac, once installed) | 13:30 Pacific | texts the verdict by iMessage |

## Standing rules - these are not up for re-argument without new, dated evidence

- **Never adjust a registered threshold, bucket, bar, band or window.** Post-output
  changes to a hypothesis are logged; three of them and it is abandoned.
- **Never edit record.yml or surface.yml's `schedule:` on a day whose run is
  needed.** The cron is held as-is until Wed 11 Nov 2026 (Gabriel, 23 Sep).
- **Licensed data never enters the repo.** Bloomberg exports live in
  `~/Documents/volrec-bloomberg`, Databento data in `~/Documents/volrec-databento`,
  keys outside the repo. Publish aggregates only; Bloomberg figures carry
  "Source: Bloomberg Finance L.P.".
- **Operations, never search.** Tools may run, check and report. Nothing proposes,
  ranks or tests a hypothesis that is not already registered.
- **Report numbers before recommending.** Label anything seen after the fact.
- **Never change the recorder's ticker universe.** It is frozen.
- **Check prior art before calling anything new.** The day count (textbook) and
  H5e's estimator (Andersen, Bondarenko & Gonzalez-Perez 2015) were both prior art.

## Where things live

- `data/` the recorded panels (the irreplaceable part), written only by the recorders
- `hypotheses/` one file per registered claim, with its adjustment log
- `tools/` everything that checks, compares or reports; `tools/hooks/` the pre-push hook
- `OPS-AGENT.md` what the operations layer is and is not allowed to do
- `BLOOMBERG-MONDAY.md` the ranked terminal asks
