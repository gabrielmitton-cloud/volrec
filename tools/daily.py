#!/usr/bin/env python3
"""The whole daily check, one command, one screen. Operations only (OPS-AGENT.md, item 2).

Runs, in order, and prints only what needs a human:
  1. git pull --rebase           (skip with --no-pull)
  2. tools/panel_health.py       did today land, is the wide file current
  3. tools/pressure_test.py      0 fail / n warn, and every FAIL or WARN line
  4. modelfree.py --wide         the registered H3 reading, the controls, the H5e tally

It changes nothing: every step is read-only except the pull, and the pull only
fast-forwards. A step that crashes is reported as a crash, never as a pass - on
23 Sep 2026 the pressure test had been crashing silently for two days.

USAGE
-----
  python3 tools/daily.py
  python3 tools/daily.py --no-pull
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable                    # whichever python runs this runs everything


def run(args, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def section(title):
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)))


def crashed(out):
    return "Traceback (most recent call last)" in out


def main():
    bad = []
    if "--no-pull" not in sys.argv:
        section("sync")
        code, out = run(["git", "pull", "--rebase", "--quiet", "origin", "main"])
        print("  up to date" if code == 0 else f"  PULL FAILED:\n{out}")
        if code:
            bad.append("git pull")

    section("did today land")
    code, out = run([PY, "tools/panel_health.py"])
    keep = [ln for ln in out.splitlines()
            if any(k in ln for k in ("newest", "WARN", "FAIL", "PEND", "wide band", "HEALTHY",
                                     "UNHEALTHY", "landed"))]
    print("\n".join(keep) or out)
    if code or crashed(out):
        bad.append("panel_health")

    section("pressure test")
    code, out = run([PY, "tools/pressure_test.py"])
    lines = out.splitlines()
    result = next((ln for ln in reversed(lines) if ln.startswith("RESULT")), None)
    if crashed(out) or result is None:
        print("  CRASHED - it did not reach a result. Last lines:")
        print("\n".join("    " + ln for ln in lines[-6:]))
        bad.append("pressure_test crashed")
    else:
        print("  " + result)
        for ln in lines[lines.index(result) + 1:]:
            print("  " + ln.strip())
        if code:
            bad.append("pressure_test")

    section("H3 reading, controls, H5e")
    code, out = run([PY, "modelfree.py", "--wide"], {"FRED_KEY": "use-cache"})
    if crashed(out):
        print("\n".join(out.splitlines()[-6:]))
        bad.append("modelfree")
    else:
        lines = out.splitlines()
        # 23 Sep 2026: the first CI run read USO at +9.39 against +9.41 locally, because
        # the FRED cache is gitignored (FRED's terms) and the runner fell back to r=0.
        rate = next((ln.strip() for ln in lines if ln.startswith("risk-free")), None)
        if rate:
            print("   " + rate + ("   <- r=0: NOT the reading of record; run locally with the"
                                  " FRED cache for that" if "0.000%" in rate else ""))
        grab, shown = False, []
        for ln in lines:
            if ln.strip().startswith("sym ") and "days" in ln:
                grab = True
            if ln.startswith("-- H5e"):
                grab = True
            if grab and ln.strip():
                shown.append(ln)
            if grab and ln.strip().startswith("Pre-registered in H3"):
                grab = False
        print("\n".join(shown) if shown else "  no wide data yet")

    section("verdict")
    print("  ALL CLEAR - nothing needs you today." if not bad
          else "  LOOK AT: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
