#!/usr/bin/env python3
"""Break every safeguard on purpose and prove its check notices. The auditor's core.

WHY THIS EXISTS (30 Sep 2026)
-----------------------------
On 28 Sep the recorders ran after the close and two checks passed anyway: the free
feed stamps after-close quotes at the close's last second, and both panel_health and
the pressure test read that as "landed a second before the close". Nothing was
wrong with the checks' code paths - they simply had never been shown a case they
should fail on. A check that has never been seen to fail is not known to work.

So this is mutation testing for the project's safeguards. For each one it makes a
throwaway git worktree of HEAD, breaks exactly that one thing, runs the pressure
test there, and requires the matching check to FAIL:

  KILLED        the check failed on the breakage. Good.
  SURVIVED      the check passed on a broken repository: a FALSE CHECK. The audit fails.
  INCONCLUSIVE  the check already fails on the unbroken repository, or its line is
                missing - either way this run cannot vouch for it. The audit fails.

It never touches the real working tree, data/, or any remote; every worktree is
removed afterwards. Doc-drift checks follow (stale "current state" dates).

USAGE
-----
  python3 tools/audit.py              # all mutants, 4 at a time (~1 min)
  python3 tools/audit.py --list       # what each mutant breaks, run nothing
  python3 tools/audit.py -k credit    # only mutants whose name contains "credit"
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _sub(path, old, new, count=1):
    """Replace text in a worktree file; refuse silently-failing mutations."""
    t = path.read_text()
    if old not in t:
        raise RuntimeError(f"mutation target not found in {path.name}: {old[:60]!r}")
    path.write_text(t.replace(old, new, count if count else t.count(old)))


def _write(path, text, add=False):
    path.write_text(text)
    if add:
        subprocess.run(["git", "add", "-f", path.name], cwd=path.parent, check=True,
                       capture_output=True)


# (name, what it breaks, mutate(worktree), the pressure-test check that must FAIL)
MUTANTS = [
    ("spreadsheet-in-repo", "a Bloomberg export lands in the repo root",
     lambda w: _write(w / "TSLA_OMON_2026-09-30.xlsx", "x"),
     "no spreadsheet is sitting in the repo"),
    ("pdf-committed", "an interlibrary-loan paper gets committed",
     lambda w: _write(w / "paper.pdf", "%PDF-1.4", add=True),
     ".gitignore blocks PDFs and none is tracked"),
    ("gitignore-loses-pdf", "the *.pdf rule is deleted",
     lambda w: _sub(w / ".gitignore", "*.pdf\n", ""),
     ".gitignore blocks PDFs and none is tracked"),
    ("databento-key-committed", "a Databento API key gets committed",
     lambda w: _write(w / "notes.txt", "key db-" + "Ab3" * 9 + "\n", add=True),
     "no Databento API key in any tracked file"),
    ("opra-data-inside-repo", "the OPRA data folder defaults to inside the repo",
     lambda w: _sub(w / "tools/opra_reference.py",
                    'Path.home() / "Documents" / "volrec-databento")', 'ROOT / "opra-data")'),
     "OPRA data and the Databento key live outside the repository"),
    ("opra-cap-raised", "the Databento lifetime cap is raised tenfold",
     lambda w: _sub(w / "tools/opra_reference.py", "LIFETIME_CAP_USD = 100.0", "LIFETIME_CAP_USD = 1000.0"),
     "the caps leave margin inside the free credit"),
    ("docs-lose-databento-credit", "OPRA figures in H5 lose the Databento credit",
     lambda w: _sub(w / "hypotheses/2026-09-19-h5-wing-quote-quality.md",
                    "Data provided by Databento", "Data from a vendor", count=0),
     "every section publishing an OPRA-derived figure credits Databento"),
    ("docs-lose-bloomberg-credit", "Bloomberg figures in H5 lose their attribution",
     lambda w: _sub(w / "hypotheses/2026-09-19-h5-wing-quote-quality.md",
                    "Source: Bloomberg Finance L.P.", "Source: a terminal", count=0),
     "every section publishing a Bloomberg-derived figure carries the attribution"),
    ("site-opra-block-uncredited", "one OPRA block on the site loses its credit",
     lambda w: _sub(w / "index.html", "Data provided by Databento (OPRA consolidated NBBO). Derived",
                    "Data (OPRA consolidated NBBO). Derived"),
     "every block of the OPRA section that states a figure credits Databento"),
    ("site-bloomberg-block-uncredited", "one Bloomberg block on the site loses its attribution",
     lambda w: _sub(w / "index.html", "Source: Bloomberg Finance L.P. Derived", "Source: vendor. Derived"),
     "every block of the Bloomberg section that states a figure carries the attribution"),
    ("site-option-symbol", "a raw option symbol is pasted onto the site",
     lambda w: _sub(w / "index.html", "<tr><td>18 Sep</td><td>USO</td><td>138</td>",
                    "<tr><td>18 Sep</td><td>USO261016P00119000</td><td>138</td>"),
     "no raw OPRA data on the site"),
    ("site-code-loads-opra", "the site's code starts loading OPRA data",
     lambda w: _sub(w / "index.html", "  function ledger(h) {",
                    "  const opraFile = 'data/opra.csv';\n  function ledger(h) {"),
     "the site's code loads no OPRA data"),
    ("frozen-h5f-script-edited", "the H5f verdict script is edited after the data",
     lambda w: (w / "tools/h5f_pooled.py").write_text((w / "tools/h5f_pooled.py").read_text() + "# tuned\n"),
     "tools/h5f_pooled.py is byte-for-byte the script frozen on 23 Sep"),
    ("verdict-bar-moved", "the verdict writer's H5e bar moves from 0.5 to 0.6",
     lambda w: _sub(w / "tools/record_verdict.py", "H5E_MIN_DAYS, H5E_BAR = 10, 0.5", "H5E_MIN_DAYS, H5E_BAR = 10, 0.6"),
     "the verdict writer carries H5f's and H5e's registered minimums, bar and window"),
    ("h5e-bar-moved-in-estimator", "modelfree's H5e bar moves, so writer and estimator disagree",
     lambda w: _sub(w / "modelfree.py", "H5E_MAX_ABS_GAP = 0.5", "H5E_MAX_ABS_GAP = 0.6"),
     "the verdict writer carries H5f's and H5e's registered minimums, bar and window"),
    ("h3-bar-moved", "H3's registered wide-prediction bracket is widened",
     lambda w: _sub(w / "modelfree.py", 'PREDICTED_LIFT = {"USO": (1.4, 3.2)}', 'PREDICTED_LIFT = {"USO": (1.4, 3.5)}'),
     "H3's wide-prediction bar, controls and first-reading rule are as registered"),
    ("good-friday-misdated", "2027's Good Friday goes back to the wrong date",
     lambda w: _sub(w / "tools/panel_health.py", "date(2027, 3, 26)", "date(2027, 4, 2)"),
     "Good Friday is listed on the right date in every covered year"),
    ("after-close-guard-removed", "the 30 Sep after-close guard is deleted",
     lambda w: _sub(w / "tools/panel_health.py", "clamped = c - 1 <= mid <= c", "clamped = False"),
     "a snapshot whose quotes are pinned to the close's last second FAILS"),
    ("freshness-gains-dependency", "the missed-day alarm starts installing packages",
     lambda w: _sub(w / ".github/workflows/freshness.yml",
                    "      - name: Fail loudly if either panel has gone stale or empty\n",
                    "      - run: pip install requests\n      - name: Fail loudly if either panel has gone stale or empty\n"),
     "freshness still installs nothing"),
    ("databento-retry-removed", "Databento gateway errors stop being retried",
     lambda w: _sub(w / "tools/opra_reference.py", "TRANSIENT = (502, 503, 504)", "TRANSIENT = ()"),
     "a Databento gateway timeout (504, 503) is retried"),
    ("recorder-guard-removed", "the ATM recorder stops checking the close",
     lambda w: _sub(w / "record.py", 'refuse_after_close("the ATM panel")', 'pass  # guard removed'),
     "both recorders check the close before fetching or writing anything"),
    ("guard-before-done-check", "the guard runs before the already-recorded exit (false failure emails, 5 Oct)",
     lambda w: _sub(w / "record.py", "    done = already_recorded(today)\n",
                    '    refuse_after_close("the ATM panel")\n    done = already_recorded(today)\n'),
     "both recorders check the close before fetching or writing anything"),
    ("ovx-zero-ask-kept", "the OVX replica stops excluding zero-ask quotes",
     lambda w: _sub(w / "tools/ovx_replicate.py", "if qt[0] == 0 or qt[1] == 0:", "if qt[0] == 0:"),
     "the OVX replica excludes zero-ask quotes"),
    ("ovx-weeklies-allowed", "the OVX replica accepts weekly expiries",
     lambda w: _sub(w / "tools/ovx_replicate.py", "    return exp == third_friday(exp.year, exp.month, holidays)",
                    "    return True"),
     "the OVX replica uses third-Friday monthlies only"),
    ("ovx-tie-highest", "the OVX replica breaks an ATM tie at the highest strike",
     lambda w: _sub(w / "tools/ovx_replicate.py", "mid(quotes[(k, \"P\")])), k))", "mid(quotes[(k, \"P\")])), -k))"),
     "the OVX replica breaks an at-the-money tie at the lowest strike"),
    ("h4-dividends-ignored", "H4 strike 2 stops adjusting the price for dividends",
     lambda w: _sub(w / "hedged.py", "S = [S[i] - (pv_dividends(", "S = [S[i] - 0.0 * (pv_dividends("),
     "hedged.py unit tests pass"),
    ("h4-carry-trading-days", "H4 strike 2 accrues carry per trading day again",
     lambda w: _sub(w / "hedged.py", "step = [(days[i + 1] - days[i]).days / 365.0 for i in range(n - 1)]",
                    "step = [1 / 365.0] * (n - 1)"),
     "hedged.py unit tests pass"),
    ("by-is-bh", "Benjamini-Yekutieli loses its dependence factor (becomes plain BH)",
     lambda w: _sub(w / "analyze.py", "    c = sum(1.0 / i for i in range(1, m + 1))", "    c = 1.0"),
     "under Benjamini-Yekutieli H1 keeps 8 of 11"),
    ("fixed-b-ignores-lag", "the fixed-b p stops using the lag (back to the ordinary t)",
     lambda w: _sub(w / "analyze.py", "    lag = max(0, min(lag, T - 1))\n    hits = 0", "    lag = 0\n    hits = 0"),
     "fixed-b p: lag 0 matches the t-test"),
    ("coverage-date-mismatch", "ticker coverage compares a date object with text dates (sees 0 tickers)",
     lambda w: _sub(w / "tools/panel_health.py",
                    '    newest = newest.isoformat() if hasattr(newest, "isoformat") else str(newest)   # day_span gives a date\n', ""),
     "panel_health names every missing ticker"),
    ("h7-cap-ignored", "H7's own spending cap stops being applied",
     lambda w: _sub(w / "tools/opra_reference.py", "    if spent_monthly + cost > H7_BUDGET_USD:", "    if False:"),
     "H7's monthly-leg OPRA purchases stop at their own"),
    ("guard-clock-wrong", "the guard treats 20:50 UTC as mid-session",
     lambda w: _sub(w / "record.py", "return (ny.hour, ny.minute) >= (16, 0)", "return (ny.hour, ny.minute) >= (17, 0)"),
     "the guard refuses 28 Sep's 20:50 UTC start"),
    ("guard-gone-delay-unchecked", "the surface recorder loses its guard while the backup can land late",
     lambda w: _sub(w / "surface.py", 'R.refuse_after_close("the strike surface")', 'pass  # guard removed'),
     "surface's worst delay seen still lands before the earlier close, or the after-close guard"),
    ("h3-keeps-after-close-day", "H3's wide reading stops dropping after-close days",
     lambda w: _sub(w / "modelfree.py", "wide_lift_report(registered, extra, r, dropped)", "wide_lift_report(registered, extra, r)"),
     "days recorded after the close are dropped from H3"),
    ("h4-keeps-after-close-day", "H4 stops dropping after-close days",
     lambda w: _sub(w / "hedged.py", 'rows = [r_ for r_ in rows if r_["date"] not in dropped]', "pass"),
     "days recorded after the close are dropped from H3"),
    ("health-starts-committing", "the health check starts committing to main",
     lambda w: _sub(w / ".github/workflows/health.yml",
                    "          python tools/daily.py --no-pull | tee report.txt\n",
                    "          python tools/daily.py --no-pull | tee report.txt\n          git commit -am report\n"),
     "health is read-only and never commits"),
]


def check_lines(out):
    """{check text: 'PASS'|'FAIL'} from pressure_test output."""
    res = {}
    for line in out.splitlines():
        m = re.match(r"\s+(PASS|FAIL)\s+(.*)$", line)
        if m:
            res[m.group(2)] = m.group(1)
    return res


def find(res, needle):
    hits = [s for k, s in res.items() if needle in k]
    return hits[0] if hits else None


def run_pressure(tree):
    p = subprocess.run([PY, "tools/pressure_test.py"], cwd=tree, capture_output=True, text=True,
                       timeout=600)
    return check_lines(p.stdout)


def make_tree(base, i):
    tree = base / f"m{i:02d}"
    subprocess.run(["git", "worktree", "add", "--detach", "--quiet", str(tree), "HEAD"],
                   cwd=ROOT, check=True, capture_output=True)
    return tree


def drift():
    """Cheap doc-drift checks: is the 'current state' still current?"""
    out = []
    h = (ROOT / "HANDOFF.md").read_text()
    today = datetime.now(timezone.utc).date()
    m = re.search(r"### System status, checked (\d{1,2}) (\w{3}) (\d{4})", h)
    if m:
        d = datetime.strptime(" ".join(m.groups()), "%d %b %Y").date()
        age = (today - d).days
        out.append(("WARN" if age > 7 else "OK", f"HANDOFF's system-status table was last checked {age} days ago"))
    else:
        out.append(("WARN", "HANDOFF has no dated system-status table"))
    days = [datetime.strptime(f"{a} {b} 2026", "%d %b %Y").date()
            for a, b in re.findall(r"^\*\*(?:Today, )?\w{3} (\d{1,2}) (\w{3})", h, re.M)
            if b in ("Sep", "Oct", "Nov", "Dec")]
    if days:
        age = (today - max(days)).days
        out.append(("WARN" if age > 7 else "OK", f"the newest dated next-step heading is {age} days old"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("-k", help="only mutants whose name contains this")
    ap.add_argument("-j", type=int, default=4, help="parallel worktrees")
    a = ap.parse_args()
    muts = [m for m in MUTANTS if not a.k or a.k in m[0]]
    if a.list:
        for name, what, _, check in muts:
            print(f"{name:32} {what}\n{'':32} must fail: {check}")
        return 0
    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                      capture_output=True, text=True).stdout.strip():
        print("NOTE  the working tree has uncommitted changes; the audit tests HEAD, not them.")

    base = Path(tempfile.mkdtemp(prefix="volrec-audit-"))
    trees = []
    try:
        base_tree = make_tree(base, 0)
        trees.append(base_tree)
        jobs = []
        for i, (name, what, mutate, check) in enumerate(muts, 1):
            tree = make_tree(base, i)
            trees.append(tree)
            try:
                mutate(tree)
                jobs.append((name, what, check, tree, None))
            except Exception as e:                     # a mutation that cannot apply is itself a finding
                jobs.append((name, what, check, tree, f"could not apply: {e}"))
        with ThreadPoolExecutor(max_workers=max(1, a.j)) as ex:
            baseline = ex.submit(run_pressure, base_tree)
            futures = {j[0]: ex.submit(run_pressure, j[3]) for j in jobs if j[4] is None}
            baseline = baseline.result()
            results = {k: f.result() for k, f in futures.items()}
    finally:
        for t in trees:
            subprocess.run(["git", "worktree", "remove", "--force", str(t)], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)
        shutil.rmtree(base, ignore_errors=True)

    bad = 0
    print(f"volrec audit {date.today()}: {len(jobs)} safeguards broken on purpose, one at a time\n")
    for name, what, check, _, err in jobs:
        if err:
            verdict, why = "INCONCLUSIVE", err
        else:
            before, after = find(baseline, check), find(results[name], check)
            if before is None or after is None:
                verdict, why = "INCONCLUSIVE", "check line not found in the pressure test output"
            elif before == "FAIL":
                verdict, why = "INCONCLUSIVE", "the check already fails on the unbroken repository"
            elif after == "FAIL":
                verdict, why = "KILLED", ""
            else:
                verdict, why = "SURVIVED", "the check PASSED on a broken repository - a false check"
        bad += verdict != "KILLED"
        print(f"  {verdict:12} {name:32} {what}" + (f"\n{'':15}{why}" if why else ""))
    print()
    for level, msg in drift():
        print(f"  {level:12} {msg}")
    print(f"\nRESULT: {len(jobs) - bad} of {len(jobs)} safeguards proven to fail when broken"
          + ("" if not bad else f"; {bad} NOT proven - read above"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
