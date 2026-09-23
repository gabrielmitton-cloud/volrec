# The operations agent — items 1-2 built, 3-5 designed

**Written 19 September 2026. Items 1 and 2 BUILT 23 September** (`tools/bloomberg_prep.py`,
`tools/daily.py`; both checked by `pressure_test.py` section M). Items 3-5 not built.
Original build window: Wednesday 23 September, morning. This file exists so that session starts from a spec instead
of rebuilding the argument.

## The one rule that decides everything

**The agent runs operations. It never searches for results.**

An agent that hunts patterns, scores variants, or proposes hypotheses from the
recorded data destroys the pre-registration in `hypotheses/`, which is the only
reason any number here is citable. That was assessed on 16 Sep (HANDOFF 17, "Ideas
assessed and parked") and rejected, and a conference on 18 Sep did not change it.
Greg Jensen's argument on Odd Lots, 11 Sep - that AI keeps markets inefficient
because frontier capability leapfrogs - is an argument for **not** competing on
compute. The asymmetry available to this project is attention: nobody funded
measures what free data costs, because they buy OPRA.

**Corollary, and it is what keeps this free: no LLM in the daily loop.** Plain
scripts plus GitHub Actions do the work. Claude is for judgement - reading a
result, drafting a write-up, deciding what a number means - not for the plumbing.

## What to build, in order

### 1. `tools/bloomberg_prep.py` — highest payoff per line
Takes a date, prints what the terminal session needs: the two expiries the recorder
will pick (`modelfree.pick_pair` on that day's listed Fridays), the strike range in
dollars for +/-60% of the last recorded spot, and the UTC pull window. This
arithmetic was done by hand on 18 Sep and it is the step most likely to go wrong at
the terminal. **Done when:** it reproduces the 18 Sep instructions exactly.

### 2. `tools/daily.py` — one command instead of four
Runs, in order: `git pull --rebase`, `panel_health`, `pressure_test`, and
`modelfree.py --wide`, and prints one block: did today land, is the wide file
current, 0 fail / n warn, and the current H3 reading against its registered grid.
**Done when:** a normal day needs exactly one command and one screen of output.

### 3. A GitHub Action that writes `reports/daily.md` - and runs the pressure test
On 21-23 Sep the pressure test crashed for two days and nothing noticed, because
the freshness workflow runs `panel_health` only. Running `daily.py` in CI closes
that. Edit workflows on a Saturday only.
The same thing as (2), on the runner, committed as a one-page report after the
surface run. Free on a public repo. The existing freshness workflow already mails
on failure, so this is for reading, not alerting. **Done when:** a week can pass
with nothing run locally and the state is still legible.

### 4. A pre-push hook running `pressure_test.py`
A broken state cannot be pushed. Cheap, and it is the 16 Sep class of failure.
**Done when:** a deliberately broken file blocks a push.

### 5. `SESSION-START.md`
The framework python path, the four commands, the standing rules, and where to
read first. Cuts the tokens a new Claude session spends rediscovering context,
which is a direct saving of usage. **Done when:** a cold session is productive
without reading HANDOFF end to end.

## What it must never do

- Propose, rank, or test a hypothesis that is not already registered.
- Touch `data/iv_history.csv` or `data/surface.csv`, ever.
- Edit a workflow's `schedule:` on a day whose run is still needed.
- Put a Bloomberg export, or any spreadsheet, inside the repository.
- Change a registered threshold, bucket, bar or band.

## Not in scope, deliberately

Trading, signals, screeners, backtest loops, broker connectors. Ruled out in
HANDOFF sections 1 and 5 and not reopened here.
