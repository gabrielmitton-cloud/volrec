# H<n> — <one sentence, stated as a claim that could be false>

**Registered:** YYYY-MM-DD (before the join was run; the commit date is proof)
**Status:** registered | tested | abandoned
**Sample:** A (long validation) | B (own panel) | both

## Why this hypothesis exists

What question it answers, and why it is worth spending observations on. If the
honest answer is "it seemed interesting," stop: that is not a hypothesis, and
with ~6 independent episodes in Sample B there is no budget for it.

## The hypothesis, stated before the join

**H<n>a.** ...
**H<n>b.** ... (directional predictions, made in advance, one per line)

## Specification — frozen here

- Estimator, with the exact function used. Import from `analyze.py` rather than
  reimplementing, so both samples run identical code.
- Sampling: non-overlapping unless there is a stated reason otherwise.
- Test and significance level.
- Universe and window.
- How gaps, missing data and discontinued series are handled.

## What would falsify it

Say what result would make you abandon this. If nothing would, it is not a
hypothesis.

## Explicitly NOT in this hypothesis

What is deliberately excluded, so scope creep is visible when it happens.

## Adjustment log

Every change to a threshold, window, or variable set, with date and reason.
Note whether it was made **before or after** seeing any output; only post-output
changes count toward the three-strike rule.

**Three adjustments after seeing output = abandon and report the abandonment.**
An abandoned hypothesis honestly reported is worth more than a surviving one
that was quietly reshaped.

- *(none yet)*

## Result

Filled in after testing. Report what happened, including the parts that did not
work. If an automated verdict prints HOLDS but the breakdown is mixed, say so
in the same breath.
