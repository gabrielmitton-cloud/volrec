#!/usr/bin/env python3
"""The whole daily check, one command, one screen. Operations only (OPS-AGENT.md, item 2).

Runs, in order, and prints only what needs a human:
  1. sync with main              (skip with --no-pull; see sync())
  2. tools/panel_health.py       did today land, is the wide file current
  3. tools/pressure_test.py      0 fail / n warn, and every FAIL or WARN line
  4. modelfree.py --wide         the registered H3 reading, the controls, the H5e tally

It changes nothing: every step is read-only except the sync (a fast-forward, or git pull --rebase when
there are unpushed local commits to replay on top of main), and the frozen-rate seed before step 4, which writes
only in a clone with no FRED cache (GitHub's runner) and otherwise checks the cache. A step that crashes is
reported as a crash, never as a pass - on 23 Sep 2026 the pressure test had been crashing silently for two days.

On GitHub's runner (GITHUB_ACTIONS=true) step 4 prints aggregates only, because there this report is public:
health.yml keeps it in the run's log and job summary (18 Nov 2026, aggregates_only()). The same day, after Astra 2's
reviews: each block's lines must be exactly what modelfree writes there, the lines steps 3 and 4 print of their own
(warnings, a crash's last lines) have every digit masked (masked()), the RESULT and risk-free lines print only in
their exact form, a notification carries no H5e tally, and a reading with neither block is a LOOK AT. On the Mac
everything prints in full.

USAGE
-----
  python3 tools/daily.py
  python3 tools/daily.py --no-pull
  python3 tools/daily.py --notify         # and text Gabriel the one-line verdict (tools/notify.py)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable                    # whichever python runs this runs everything
DIGIT = re.compile(r"\d")
RESULT = re.compile(r"RESULT: \d+ fail, \d+ warn")            # the pressure test's result line, exactly
RATE = re.compile(r"risk-free \(DGS1MO\): \d+\.\d{3}%")       # modelfree's rate line, exactly
# The lines of modelfree's two blocks a public log may carry, each matched whole and only inside its own block (18
# Nov 2026, Astra 2's reviews). H3's lift table compares two free-feed readings (wide strikes minus registered ones),
# so no index is in it; H5e's two headings carry no value. Anything else - a dated row, the tally, a known line with
# something appended, a line not recognised - is held back.
H3_SYMS = ("SPY", "QQQ", "IWM", "GLD", "USO", "TSLA", "NVDA", "AAPL")   # surface.py's SURFACE; another is held back
H3_NOTE = (r"registered bracket \d+\.\d to \d+\.\d: (?:INSIDE|OUTSIDE)"
           r"(?: \(only \d+ day\(s\); first reading at \d+\))?"
           r"|null control, must stay under \d+(?:\.\d+)?: (?:ok|FAILED - lift that is not tail variance)")
H3_ROW = (rf"(?:{'|'.join(H3_SYMS)}) +\d+ +[+-]\d+\.\d\d +[+-]\d+\.\d\d"    # sym, days, the two mean lifts
          rf"(?:   (?:{H3_NOTE}))?")                                        # and modelfree's note, if it has one
H3_REGISTERED = "Pre-registered in H3 on 18 Sep: USO's reading is the as-registered mean over"
KNOWN = {"h3": (re.compile(r"sym +days +mean as reg +mean zero-bid +reading"),
                re.compile(H3_ROW),
                re.compile(re.escape(H3_REGISTERED))),
         "h5e": (re.compile(r"-- H5e: [A-Z]+, wide strikes, zero bids SKIPPED, against [A-Z]+ "
                            r"\(registered \d+ [A-Z][a-z]{2}; judged from 20\d\d-\d\d-\d\d\)"),
                 re.compile(r"date +[A-Z]+ +registered +gap +wide skip +gap +counted"),
                 re.compile(r"no counted day yet; H5e needs \d+"))}


def on_github():
    """GitHub's runner sets GITHUB_ACTIONS=true. There this report is public: the repository is public, and health.yml
    keeps the report in the run's log and job summary."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


def masked(lines):
    """A step's own lines as a public log may carry them (18 Nov 2026, Astra 2's reviews): every digit masked, so a
    crash or a warning keeps its words but no value - a whole number, a leading dot or an exponent included (masking
    only decimals left those). Its dates and counts go too; the Mac prints them."""
    return [DIGIT.sub("#", ln) for ln in lines]


def aggregates_only(tagged):
    """The reading's lines, each tagged with its block ("h3" or "h5e"), as a public log may carry them. 18 Nov 2026:
    H5e's block printed one row per day with that day's Cboe OVX close beside the free reading, in every health run
    from 23 Sep (946 rows in 43 public logs). Cboe approved aggregates only (4 Nov 2026: "No Cboe data files are
    republished. Only aggregate statistics appear"). The same day, after Astra 2's reviews, a line stays only if it
    is exactly one of its own block's KNOWN lines. H5e's running tally is held back too: it changes every night, so
    two nights' logs would give that night's gap, and with the public free reading the close (CLAUDE.md, mistake
    10). One line, where the first held line stood, says how many."""
    out, held, at = [], 0, None
    for block, ln in tagged:
        if any(k.fullmatch(ln.strip()) for k in KNOWN[block]):
            out.append(ln)
        else:
            held += 1
            at = len(out) if at is None else at
    if held:
        out.insert(at, f"   ({held} line(s) held back: this log is public. They are H5e's dated rows, which carry "
                       "Cboe's daily closes; its running tally, which two nights' logs would turn into a day's gap; "
                       "and any line not recognised. tools/daily.py on the Mac prints them.)")
    return out


def run(args, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def section(title):
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)))


def crashed(out):
    return "Traceback (most recent call last)" in out


def sync():
    """Bring main up to date without tripping over an uncommitted file. 31 Oct 2026: `git pull --rebase`
    refuses outright on any unstaged change, so a local file kept uncommitted on purpose (Astra's bridge,
    since 24 Oct) turned every day into LOOK AT: git pull while main was already in step. Now: fetch; nothing
    new is up to date; new commits and no local ones fast-forward (git refuses, touching nothing, if they
    would overwrite an uncommitted file); local commits as well take the old rebase. Hardened the same day
    (Astra's review): only main is synced - another branch or a detached HEAD is reported, not rebased; the
    comparison is against the commit this fetch brought (FETCH_HEAD); git may neither stash a dirty file
    aside (autostash) nor overwrite an ignored one."""
    code, out = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
    if code or out.strip() != "main":
        return 1, f"  not on main ({out.strip() or 'detached HEAD'}): nothing synced; switch to main or use --no-pull"
    code, out = run(["git", "fetch", "--quiet", "origin", "main"])
    if code:
        return code, out
    code, out = run(["git", "rev-list", "--left-right", "--count", "HEAD...FETCH_HEAD"])
    if code:
        return code, out
    ahead, behind = (int(n) for n in out.split()[:2])         # stdout first; a stray stderr line follows
    if not behind:
        return 0, f"  up to date{f' ({ahead} local commit(s) not pushed yet)' if ahead else ''}"
    code, out = run(["git", "merge", "--ff-only", "--no-autostash", "--no-overwrite-ignore", "--quiet", "FETCH_HEAD"]
                    if not ahead else ["git", "pull", "--rebase", "--no-autostash", "--quiet", "origin", "main"])
    return code, out if code else f"  up to date (pulled {behind} commit(s))"


def main():
    bad, facts = [], {}
    if "--no-pull" not in sys.argv:
        section("sync")
        code, out = sync()
        print(out if code == 0 else f"  PULL FAILED:\n{out}")
        if code:
            bad.append("git pull")

    section("did today land")
    code, out = run([PY, "tools/panel_health.py"])
    keep = [ln for ln in out.splitlines()
            if any(k in ln for k in ("newest", "WARN", "FAIL", "PEND", "wide band", "HEALTHY",
                                     "UNHEALTHY", "landed"))]
    print("\n".join(keep) or out)
    for ln in out.splitlines():
        if "Surface panel" in ln:
            facts["panel"] = "surface"
        if facts.get("panel") == "surface" and "newest" in ln and "surface_newest" not in facts:
            facts["surface_newest"] = ln.split("newest", 1)[1].split()[0]
        if facts.get("panel") == "surface" and "landed" in ln and "landed" not in facts:
            facts["landed"] = ln.split("landed", 1)[1].split("UTC")[0].strip()
    if code or crashed(out):
        bad.append("panel_health")

    section("pressure test")
    code, out = run([PY, "tools/pressure_test.py"])
    lines = out.splitlines()
    # 18 Nov 2026 (Astra 2's follow-up review): the result is the last line in RESULT's exact form, so a diagnostic
    # that starts like it is neither taken for the result nor printed whole. The FAIL and WARN lines follow it.
    at = next((i for i in reversed(range(len(lines))) if RESULT.fullmatch(lines[i])), None)
    if crashed(out) or at is None:
        print("  CRASHED - it did not reach a result. Last lines:")
        print("\n".join("    " + ln for ln in (masked(lines[-6:]) if on_github() else lines[-6:])))
        bad.append("pressure_test crashed")
    else:
        result = lines[at]
        print("  " + result)
        facts["pressure"] = result.replace("RESULT:", "").strip()
        rest = lines[at + 1:]
        for ln in masked(rest) if on_github() else rest:
            print("  " + ln.strip())
        if code:
            bad.append("pressure_test")

    section("H3 reading, controls, H5e")
    # 3 Nov 2026: with no cache (git-ignored, so never on GitHub's runner) this read r = 0, and the phone's nightly
    # H5e line was not the reading of record: 0.99, 20 of 28 against 0.98, 19 of 28 on 2 Nov. tools/seed_frozen_rate.py
    # writes the frozen rate only where no cache exists; where one does, it checks it and leaves it untouched. A cache
    # without the registered rate (other series only, say) is a LOOK AT, not a quiet r = 0 (Astra's review, 3 Nov).
    code, out = run([PY, "tools/seed_frozen_rate.py"])
    if code or crashed(out):
        print("  FROZEN RATE NOT READY:\n" + "\n".join("    " + ln for ln in out.strip().splitlines()[-4:]))
        bad.append("frozen rate")
    code, out = run([PY, "modelfree.py", "--wide"], {"FRED_KEY": "use-cache"})
    if code != 0 or crashed(out):        # 16 Oct: a sys.exit("...") has no traceback but is still a crash
        tail = out.splitlines()[-6:]     # 18 Nov: rows printed before a crash were among them; masked on the runner
        print("\n".join(masked(tail) if on_github() else tail))
        bad.append("modelfree")
    else:
        lines = out.splitlines()
        # 23 Sep 2026: the first CI run read USO at +9.39 against +9.41 locally, because
        # the FRED cache is gitignored (FRED's terms) and the runner fell back to r=0.
        rate = next((ln.strip() for ln in lines if ln.startswith("risk-free")), None)
        if rate and on_github() and not RATE.fullmatch(rate):     # 18 Nov 2026: it printed whole, anything on it
            print("   risk-free line not recognised: held back, as this log is public (the Mac prints it)")
        elif rate:
            print("   " + rate + ("   <- r=0: NOT the reading of record; run locally with the"
                                  " FRED cache for that" if "0.000%" in rate else ""))
        block, shown = None, []          # (block, line), so that each line is matched to its own block's lines
        for ln in lines:
            if block is None and ln.strip().startswith("sym ") and "days" in ln:
                block = "h3"
            if ln.startswith("-- H5e"):
                block = "h5e"
            if block and ln.strip():
                shown.append((block, ln))
            if block == "h3" and ln.strip().startswith("Pre-registered in H3"):
                block = None
        if not shown:
            # 18 Nov 2026 (Astra 2's review): this read ALL CLEAR. The wide file exists since 18 Sep, so a reading
            # with neither block went wrong somewhere.
            print("  NO READING: modelfree printed neither H3's table nor H5e's block")
            bad.append("modelfree printed no reading")
        else:
            print("\n".join(aggregates_only(shown) if on_github() else [ln for _, ln in shown]))
        uso = next((ln.split() for b, ln in shown if b == "h3" and ln.strip().startswith("USO ") and "bracket" in ln),
                   None)
        if uso:
            facts["h3"] = f"H3 USO lift {uso[2]} ({'inside' if 'INSIDE' in ' '.join(uso) else 'outside'} 1.4-3.2)"
        tally = [ln.strip() for b, ln in shown
                 if b == "h5e" and ln.strip().startswith(("mean |gap|", "no counted day"))]
        if tally and not on_github():    # 18 Nov 2026: a notification's dry run prints its message into the log
            facts["h5e"] = "H5e: " + tally[-1].split(";")[0].replace("no counted day yet", "0 counted days")

    section("verdict")
    print("  ALL CLEAR - nothing needs you today." if not bad
          else "  LOOK AT: " + ", ".join(bad))

    if "--notify" in sys.argv or "--notify-dry-run" in sys.argv:
        # OPS-AGENT item 7: one line to Gabriel's phone. LOOK AT leads when it applies.
        from datetime import date
        msg = (f"volrec {date.today():%a %d %b}: "
               + ("ALL CLEAR" if not bad else "LOOK AT " + ", ".join(bad)) + ". "
               + (f"Surface {facts['surface_newest']}, landed {facts.get('landed', '?')} UTC. "
                  if facts.get("surface_newest") else "")
               + (f"Pressure {facts['pressure']}. " if facts.get("pressure") else "")
               + " ".join(facts[k] + "." for k in ("h3", "h5e") if facts.get(k)))
        import notify
        sent, why = notify.send(msg, dry="--notify-dry-run" in sys.argv)
        print(f"\n  notify: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
