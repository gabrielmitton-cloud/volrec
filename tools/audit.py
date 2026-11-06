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
  python3 tools/audit.py              # all mutants, 4 at a time (~1 min in Sep; 130 took ~25-30 min at -j 6, 31 Oct)
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
     lambda w: _sub(w / "tools/opra_reference.py", "LIFETIME_CAP_USD = 120.0", "LIFETIME_CAP_USD = 1200.0"),
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
    ("gitignore-lseg-dropped", "the LSEG export folder is no longer git-ignored",
     lambda w: _sub(w / ".gitignore", "volrec-lseg/", "# volrec-lseg/"),
     ".gitignore blocks the LSEG export folder by name"),
    ("lseg-csv-committed", "a raw LSEG export is committed",
     lambda w: _write(w / "OVX_30min.csv", "Date,TRDPRC_1,HIGH_1,LOW_1\n2026-10-01,1,1,1\n", add=True),
     "no tracked CSV carries LSEG's field names"),
    ("site-fred-notice-dropped", "the site loses the notice FRED's API terms require",
     lambda w: _sub(w / "index.html", "This product uses the FRED® API but is not endorsed",
                    "This product uses FRED data"),
     "README and the site carry the notice FRED's API terms require"),
    ("seed-rate-drifts", "the fresh-clone seed carries today's rate instead of the registered one",
     lambda w: _sub(w / "tools/seed_frozen_rate.py", '{"2026-09-10": 3.91}}', '{"2026-10-08": 4.14}}'),
     "the fresh-clone seed carries the registered rate"),
    ("h8-blank-bid-dropped", "H8 drops OPRA's blank-bid quotes instead of reading them as zero bids",
     lambda w: _sub(w / "tools/h8_quotes.py", "            b = hit[1] or 0.0\n",
                    "            if hit[1] is None:\n                continue\n            b = hit[1]\n"),
     "H8's instrument tests pass"),
    ("h8-tost-one-sided", "H8's equivalence test checks only the lower bound",
     lambda w: _sub(w / "tools/h8_quotes.py", "(p_lo < 0.05 and p_hi < 0.05)", "(p_lo < 0.05)"),
     "H8's instrument tests pass"),
    ("h8-neff-ignores-rho", "H8 counts every day as independent",
     lambda w: _sub(w / "tools/h8_quotes.py", "return max(1.0, T * (1 - r) / (1 + r))", "return float(T)"),
     "H8's instrument tests pass"),
    ("h8-tost-uses-t", "H8's equivalence decision reads t(T-1) p-values instead of the registered fixed-b ones",
     lambda w: _sub(w / "tools/h8_quotes.py",
                    "    p_lo = sum(x >= t_lo for x in null) / len(null)\n    p_hi = sum(x <= t_hi for x in null) / len(null)\n",
                    "    p_lo = t_pvalue(t_lo, T - 1) / 2 if t_lo > 0 else 1 - t_pvalue(t_lo, T - 1) / 2\n"
                    "    p_hi = t_pvalue(t_hi, T - 1) / 2 if t_hi < 0 else 1 - t_pvalue(t_hi, T - 1) / 2\n"),
     "H8's instrument tests pass"),
    ("h8-fixedb-two-sided", "H8's lower one-sided test counts both tails of the fixed-b null",
     lambda w: _sub(w / "tools/h8_quotes.py", "    p_lo = sum(x >= t_lo for x in null) / len(null)\n",
                    "    p_lo = sum(abs(x) >= abs(t_lo) for x in null) / len(null)\n"),
     "H8's instrument tests pass"),
    ("h8-lag-rule", "H8's lag rule truncates 1.3*sqrt(T) instead of rounding it",
     lambda w: _sub(w / "tools/h8_quotes.py", "    return math.floor(1.3 * math.sqrt(T) + 0.5)",
                    "    return math.floor(1.3 * math.sqrt(T))"),
     "H8's instrument tests pass"),
    ("h8-reps-shared", "H8's equivalence test falls back to the shared 4,000 draws",
     lambda w: _sub(w / "tools/h8_quotes.py", "def tost(d, bound, lag, reps=H8_REPS):",
                    "def tost(d, bound, lag, reps=4000):"),
     "H8's instrument tests pass"),
    ("h8-reps-not-passed", "H8's equivalence test drops its draw count on the way to the shared null",
     lambda w: _sub(w / "tools/h8_quotes.py", "    null = fixed_b_null(T, lag, reps)\n", "    null = fixed_b_null(T, lag)\n"),
     "H8's instrument tests pass"),
    ("h8-tie-excluded", "H8's lower test leaves out a null draw equal to its statistic",
     lambda w: _sub(w / "tools/h8_quotes.py", "    p_lo = sum(x >= t_lo for x in null) / len(null)\n",
                    "    p_lo = sum(x > t_lo for x in null) / len(null)\n"),
     "H8's instrument tests pass"),
    ("h8-tie-excluded-upper", "H8's upper test leaves out a null draw equal to its statistic",
     lambda w: _sub(w / "tools/h8_quotes.py", "    p_hi = sum(x <= t_hi for x in null) / len(null)\n",
                    "    p_hi = sum(x < t_hi for x in null) / len(null)\n"),
     "H8's instrument tests pass"),
    ("h8-threshold-inclusive", "H8 calls a p of exactly 0.05 significant",
     lambda w: _sub(w / "tools/h8_quotes.py", "(p_lo < 0.05 and p_hi < 0.05)", "(p_lo <= 0.05 and p_hi <= 0.05)"),
     "H8's instrument tests pass"),
    ("h8-sides-swapped", "H8's item 7 puts OPRA's calls into the put mix and its puts into the call mix",
     lambda w: _sub(w / "tools/h8_quotes.py", 'if (x["type"] == "C") == (side == "C") else x',
                    'if (x["type"] == "C") != (side == "C") else x'),
     "H8's instrument tests pass"),
    ("h8-sides-one-order", "H8's item 7 reports the puts-first split twice, the second under the calls-first label",
     lambda w: (_sub(w / "tools/h8_quotes.py", '"calls_first": {"call": two([x["S0s"] - x["MCs"] for x in keep]),',
                     '"calls_first": {"call": two([x["MPs"] - x["S1s"] for x in keep]),'),
                _sub(w / "tools/h8_quotes.py", '"put": two([x["MCs"] - x["S1s"] for x in keep])}}',
                     '"put": two([x["S0s"] - x["MPs"] for x in keep])}}')),
     "H8's instrument tests pass"),
    ("h8-sides-nonfinite-kept", "H8's item 7 averages in a fund-day whose estimate is not a finite number",
     lambda w: _sub(w / "tools/h8_quotes.py", "all(x.get(k) is not None and math.isfinite(x[k]) for k in",
                    "all(x.get(k) is not None for k in"),
     "H8's instrument tests pass"),
    ("h8-sides-not-printed", "H8's report leaves item 7's split out",
     lambda w: _sub(w / "tools/h8_quotes.py", '({len(snap)} days)")\n    print(side_line(days))\n', '({len(snap)} days)")\n'),
     "H8's instrument tests pass"),
    ("h8-sides-minimum", "H8's report shows item 7's split only for a fund with three quote-time days",
     lambda w: _sub(w / "tools/h8_quotes.py", '        print(side_line(days))\n        return\n', "        return\n"),
     "H8's instrument tests pass"),
    ("h8-sides-quote-time-set", "H8's item 7 mixes the quote-time contracts instead of the snapshot contracts",
     lambda w: _sub(w / "tools/h8_quotes.py", 'else x for x in s])', 'else x for x in a if x["option_symbol"] in at_s])'),
     "H8's instrument tests pass"),
    ("h8-sides-quote-time-quotes", "H8's item 7 takes OPRA's quote at each free quote's time, not at the snapshot minute",
     lambda w: _sub(w / "tools/h8_quotes.py", 'return v([at_s[x["option_symbol"]] if',
                    'return v([at_t.get(x["option_symbol"], at_s[x["option_symbol"]]) if'),
     "H8's instrument tests pass"),
    ("timing-reads-ahead", "the index-timing reader takes a bar whose second has not ended by the snapshot minute",
     lambda w: _sub(w / "tools/index_timing.py", "if ts + ONE_SECOND <= T:", "if ts <= T:"),
     "the index-timing reader's tests pass"),
    ("timing-stale-index", "the index-timing reader fills a day from an index value more than 60 s old",
     lambda w: _sub(w / "tools/index_timing.py", "    if T - ts > MAX_AGE:\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-seal-unchecked", "the index-timing reader reads a sealed file without checking its sha256",
     lambda w: _sub(w / "tools/index_timing.py", "    if hashlib.sha256(raw).hexdigest() != want:\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-opens-before-verdicts", "the index-timing reader opens the sealed files before both verdicts are recorded",
     lambda w: _sub(w / "tools/index_timing.py", "    if not verdicts_recorded():\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-gate-either", "the index-timing reader opens the sealed files once EITHER verdict is recorded",
     lambda w: _sub(w / "tools/index_timing.py", "rv.MARK_H5E_FINAL in rv.H5.read_text() and rv.MARK_H7",
                    "rv.MARK_H5E_FINAL in rv.H5.read_text() or rv.MARK_H7"),
     "the index-timing reader's tests pass"),
    ("timing-lost-file-unchecked", "the index-timing reader reads a sealed day file missing from disk as a day not covered",
     lambda w: _sub(w / "tools/index_timing.py", "    if gone:\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-reference-exit-ignored", "the index-timing reader accepts a reference run that failed",
     lambda w: _sub(w / "tools/index_timing.py", "    if code != 0:\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-rate-unchecked", "the index-timing reader rebuilds the readings at a rate other than the frozen one",
     lambda w: _sub(w / "tools/index_timing.py", '    if not rv.rate_ok(f"{100 * r:.3f}"):\n', "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-printed-rate-unchecked", "the index-timing reader accepts modelfree's output at another rate",
     lambda w: _sub(w / "tools/index_timing.py", "    if not rv.rate_ok(rf):\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-empty-agreement", "the index-timing reader calls two empty H5e sides an agreement",
     lambda w: _sub(w / "tools/index_timing.py", "    if not printed and not mine:\n", "    if False:\n"),
     "the index-timing reader's tests pass"),
    ("timing-key-kept", "the index-timing reader keeps a real FRED key, which can fetch today's rate",
     lambda w: _sub(w / "tools/index_timing.py", 'os.environ["FRED_KEY"] = "use-cache"',
                    'os.environ.setdefault("FRED_KEY", "use-cache")'),
     "the index-timing reader's tests pass"),
    ("timing-default-widened", "the index-timing reader's default reads an index beyond OVX and GVZ",
     lambda w: _sub(w / "tools/index_timing.py", "def bars(path, sealed, indices=INDICES):",
                    'def bars(path, sealed, indices=INDICES + ("VIX",)):'),
     "the index-timing reader's tests pass"),
    ("h8index-opens-before-window", "H8's index reading opens its files before the window closes",
     lambda w: _sub(w / "tools/h8_index.py", "    if today.isoformat() <= WINDOW[1]:\n", "    if False:\n"),
     "H8's index reading's tests pass"),
    ("h8index-reads-timing-folder", "H8's index reading reads the timing plan's sealed folder",
     lambda w: _sub(w / "tools/h8_index.py", "    if folder.resolve() == it.DBIX_DIR.resolve():\n", "    if False:\n"),
     "H8's index reading's tests pass"),
    ("h8index-one-feed-day", "H8's index reading counts a day on which only one feed has an estimate",
     lambda w: _sub(w / "tools/h8_index.py", '        if x["free"] is None or x["opra"] is None:\n',
                    '        if x["free"] is None and x["opra"] is None:\n'),
     "H8's index reading's tests pass"),
    ("h8index-window-ignored", "H8's index reading takes fund-days from outside H8's window",
     lambda w: _sub(w / "tools/h8_index.py", '        if not in_window(x["day"]):\n', "        if False:\n"),
     "H8's index reading's tests pass"),
    ("h8index-day-dropped", "H8's index reading drops a window day it has no fund-day for, instead of listing it",
     lambda w: _sub(w / "tools/h8_index.py", """                g["missing"].append((day, "no fund-day from H8's files" if day in days else\n"""
                    """                                     "neither a fund-day from H8's files nor an index file"))\n""",
                    "                pass\n"),
     "H8's index reading's tests pass"),
    ("h8index-reads-near", "H8's index reading takes the bar nearest T, which may be printed after it",
     lambda w: _sub(w / "tools/h8_index.py", '        I, why = it.index_at(series, x["T"])\n',
                    '        I, why = it.index_near(series, x["T"]), "none within 15 s"\n'),
     "H8's index reading's tests pass"),
    ("timing-nonfinite-index", "the index-timing reader takes a close that is not a finite number as the index",
     lambda w: _sub(w / "tools/index_timing.py", "    if not math.isfinite(close):", "    if False:"),
     "the index-timing reader's tests pass"),
    ("h8index-nonfinite-estimate", "H8's index reading counts a day whose estimate is not a finite number",
     lambda w: _sub(w / "tools/h8_index.py", '        if not (math.isfinite(x["free"]) and math.isfinite(x["opra"])):\n',
                    "        if False:\n"),
     "H8's index reading's tests pass"),
    ("h8index-calendar-ignored", "H8's index reading loses a trading day missing from both its sources",
     lambda w: _sub(w / "tools/h8_index.py", "    expected = set(window_days() if calendar is None else calendar) | set(days)\n",
                    "    expected = set(days)\n"),
     "H8's index reading's tests pass"),
    ("site-preview-raster-unchecked", "the preview check passes a whole PNG with no pixels in it",
     lambda w: _sub(w / "tools/pressure_test.py", "    if len(raw) != h * line or any(raw[i] > 4 for i in range(0, len(raw), line)):\n",
                    "    if False:\n"),
     "the preview check refuses a truncated or damaged image"),
    ("site-preview-png-unchecked", "the preview check passes an image that ends early",
     lambda w: _sub(w / "tools/pressure_test.py", '    if i != len(b) or not kinds or kinds[0] != b"IHDR" or kinds[-1] != b"IEND" or not idat:\n',
                    "    if not kinds:\n"),
     "the preview check refuses a truncated or damaged image"),
    ("h8index-reseals", "H8's seal writer seals a file name a second time, under a new hash",
     lambda w: _sub(w / "tools/h8_index.py", "    if name in have:\n", "    if False:\n"),
     "H8's index reading's tests pass"),
    ("site-option-symbol", "a raw option symbol is pasted onto the site",
     lambda w: _sub(w / "index.html", "<tr><td>18 Sep</td><td>USO</td><td>138</td>",
                    "<tr><td>18 Sep</td><td>USO261016P00119000</td><td>138</td>"),
     "no raw OPRA data on the site"),
    ("site-preview-image-missing", "a page's link preview names an image that is not in the repository",
     lambda w: _sub(w / "tools/monitor.html", 'volrec/og/monitor.png">', 'volrec/og/instrument.png">'),
     "each page's link preview names its own title, description, address and a 1200x630 image"),
    ("site-preview-description-drifts", "the home page's link preview says something other than its description",
     lambda w: _sub(w / "index.html", '<meta property="og:description" content="A zero-budget',
                    '<meta property="og:description" content="A free'),
     "each page's link preview names its own title, description, address and a 1200x630 image"),
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
    ("databento-unreleased-422-stops", "Databento's 'not released yet' 422 stops the nightly run again (6 Nov)",
     lambda w: _sub(w / "tools/opra_reference.py",
                    'if r.status_code == 422 and "_after_available_end" in r.text:', "if False:"),
     "Databento's 'not released yet' 422"),
    ("databento-unreleased-any-422", "every Databento 422 is taken for an unreleased day, hiding real errors",
     lambda w: _sub(w / "tools/opra_reference.py",
                    'if r.status_code == 422 and "_after_available_end" in r.text:', "if r.status_code == 422:"),
     "Databento's 'not released yet' 422"),
    ("fetch-unreleased-price-crashes", "an unreleased day's price query crashes fetch() again",
     lambda w: _sub(w / "tools/opra_reference.py",
                    'nothing charged - run again tomorrow")\n        return\n    spent = ledger_total()',
                    'nothing charged - run again tomorrow")\n        raise\n    spent = ledger_total()'),
     "a day Databento has not released yet is skipped at the price query"),
    ("definitions-unreleased-crashes", "an unreleased day's price query crashes the definitions lookup",
     lambda w: _sub(w / "tools/opra_reference.py",
                    'nothing charged"); return\n    spent = ledger_total()',
                    'nothing charged"); raise\n    spent = ledger_total()'),
     "the definitions lookup skips an unreleased day"),
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
     lambda w: _sub(w / "analyze.py", "    return list(_fixed_b_null(T, max(0, min(lag, T - 1)), reps, seed))",
                    "    return list(_fixed_b_null(T, 0, reps, seed))"),
     "fixed-b p: lag 0 matches the t-test"),
    ("coverage-date-mismatch", "ticker coverage compares a date object with text dates (sees 0 tickers)",
     lambda w: _sub(w / "tools/panel_health.py",
                    '    newest = newest.isoformat() if hasattr(newest, "isoformat") else str(newest)   # day_span gives a date\n', ""),
     "panel_health names every missing ticker"),
    ("h7-cap-ignored", "H7's own spending cap stops being applied",
     lambda w: _sub(w / "tools/opra_reference.py", "    if spent_monthly + cost > H7_BUDGET_USD:", "    if False:"),
     "H7's monthly-leg OPRA purchases stop at their own"),
    ("h8-cap-ignored", "H8's own spending cap stops being applied",
     lambda w: _sub(w / "tools/opra_reference.py", "    if spent_h8 + cost > H8_BUDGET_USD:", "    if False:"),
     "H8's OPRA purchases stop at their own"),
    ("h8-trim-drops-header", "H8's purchase trim drops Databento's header line",
     lambda w: _sub(w / "tools/opra_reference.py", "    out = [lines[0]]\n", "    out = []\n"),
     "H8's instrument tests pass"),
    ("lab-cap-ignored", "the lab's own spending cap stops being applied",
     lambda w: _sub(w / "lab/fetch_lab.py", "    if spent + cost > LAB_BUDGET_USD:", "    if False:"),
     "lab/ OPRA purchases stop at their own"),
    ("lab-date-range-ignored", "the lab may buy days inside a registered window",
     lambda w: _sub(w / "lab/fetch_lab.py", "    return LAB_START <= day <= LAB_END", "    return True"),
     "lab/ purchases refused outside"),
    ("lab-margin-ignores-otm", "the margin rule forgets to subtract the out-of-the-money amount",
     lambda w: _sub(w / "lab/margin.py", "    otm = max(S - K, 0.0)", "    otm = 0.0"),
     "lab/ tests pass"),
    ("lab-raw-prices-dropped", "options settle on split-adjusted closes instead of raw ones",
     lambda w: _sub(w / "lab/trades.py", "    s = bars[symbol][day][0]", "    s = bars[symbol][day][1]"),
     "lab/ tests pass"),
    ("lab-cost-roundtrip-charged", "a held-to-expiry trade is charged a round trip",
     lambda w: _sub(w / "lab/costs.py", "    return half * COST_CASES[case]", "    return 2 * half * COST_CASES[case]"),
     "lab/ tests pass"),
    ("lab-shapley-single-order", "the Leak Map credits each friction from one order only",
     lambda w: _sub(w / "lab/leakmap.py", "    for order in permutations(players):", "    for order in [tuple(players)]:"),
     "lab/ tests pass"),
    ("lab-bootstrap-iid", "the bootstrap draws months independently, breaking up crash clusters",
     lambda w: _sub(w / "lab/stress.py", "    rnd, n, p = random.Random(seed), len(x), 1.0 / max(b, 1.0)", "    rnd, n, p = random.Random(seed), len(x), 1.0"),
     "lab/ tests pass"),
    ("lab-breakeven-extrapolates", "the Break-Even VIX reports a crossing outside the observed range",
     lambda w: _sub(w / "lab/breakeven.py", "    return x if lo <= x <= hi else None", "    return x"),
     "lab/ tests pass"),
    ("lab-verify-ignores-empty", "the purchase verifier accepts a header-only file",
     lambda w: _sub(w / "lab/verify_purchases.py", "    if len(lines) < 2:\n        return \"header only - no data rows\"\n", ""),
     "lab/ tests pass"),
    ("lab-verify-ignores-ledger", "the purchase verifier stops comparing files with the ledger",
     lambda w: _sub(w / "lab/verify_purchases.py", "    return [(key, have[key], paid[key]) for key in sorted(set(have) | set(paid)) if have[key] != paid[key]]", "    return []"),
     "lab/ tests pass"),
    ("lab-imported-by-registered", "a registered reader starts reading the side project",
     lambda w: _sub(w / "modelfree.py", "import ", "import lab  # noqa\nimport ", 1),
     "no registered reader imports or reads lab/"),
    ("record-push-no-retry", "the recorder pushes once, without rebasing",
     lambda w: _sub(w / ".github/workflows/record.yml",
                    "            git pull --rebase origin main && git" + " push origin main && exit 0\n",
                    "            git" + " push && exit 0\n"),   # split so this file never contains a push command
     "record.yml rebases and retries its push, so a concurrent commit cannot drop a day"),
    ("guard-trusts-the-run", "the guard calls a day complete without reading the data",
     lambda w: _sub(w / "tools/guard.py", "    if have >= need:\n        return \"ok\"", "    if True:\n        return \"ok\""),
     "the guard and alert tests pass"),
    ("guard-retries-forever", "the guard re-runs a recorder again after its own re-run",
     lambda w: _sub(w / "tools/guard.py", "    if any(r.get(\"actor\") == BOT for r in runs):\n", "    if False:\n"),
     "the guard and alert tests pass"),
    ("guard-red-at-the-bell", "RED fires when no one can act before the close",
     lambda w: _sub(w / "tools/guard.py", "RED_BEFORE_CLOSE_MIN = 10", "RED_BEFORE_CLOSE_MIN = 0"),
     "the guard and alert tests pass"),
    ("alert-repeats-4xx", "the sender repeats a request Pushover refused",
     lambda w: _sub(w / "tools/alert.py", "400 <= status < 500", "400 <= status < 400"),
     "the guard and alert tests pass"),
    ("guard-skips-refetch", "after its re-run the guard judges stale data instead of reading main again",
     lambda w: _sub(w / "tools/guard.py", 'f = git(["fetch", "-q", "--depth", "1", "origin", "main"])',
                    'f = git(["status"])\n        fetched = True\n        break'),
     "the guard and alert tests pass"),
    ("guard-reruns-early", "the guard may start a recorder before its own trigger slot",
     lambda w: _sub(w / "tools/guard.py", "    if mins < trig:\n", "    if False:\n"),
     "the guard and alert tests pass"),
    ("guard-dispatch-cap-gone", "the re-run cap trusts the bot login alone",
     lambda w: _sub(w / "tools/guard.py", "    if len(dispatches) >= 2:", "    if False:"),
     "the guard and alert tests pass"),
    ("guard-split-queues", "guard runs go back to separate queues and can re-run the same recorder twice",
     lambda w: _sub(w / ".github/workflows/guard.yml", "  group: guard\n",
                    "  group: guard-${{ github.event.workflow_run.path || github.event_name }}\n"),
     "the guard runs after every recorder run and when dispatched"),
    ("ledger-headerless-trusted", "the caps trust a ledger with no header (every cap reads $0)",
     lambda w: _sub(w / "tools/opra_reference.py", "        if rd.fieldnames != LEDGER_HEADER:", "        if False:"),
     "the ledger writer always writes its header, and a headerless ledger is refused"),
    ("ledger-stale-allowed", "the Mac buys against its own stale ledger",
     lambda w: _sub(w / "tools/opra_reference.py", "    if not a.compare and not a.dry_run and stale_ledger():",
                    "    if False:"),
     "a purchase from the Mac's default folder is refused while the real (private) ledger exists"),
    ("recorder-starts-early", "the ATM recorder may record hours before its slot",
     lambda w: _sub(w / "record.py", "    return ny.hour * 60 + ny.minute < h * 60 + m + offset_min - lead_min",
                    "    return False"),
     "a recorder refuses to start more than 15 min before its slot"),
    ("recorder-records-past-bell", "the recorders keep recording closing quotes after 16:00 mid-run",
     lambda w: _sub(w / "surface.py", "        if R.after_close():\n            print(\"The session has closed: skipping",
                    "        if False:\n            print(\"The session has closed: skipping"),
     "both recorders refuse an early start and stop at the bell mid-run"),
    ("push-window-in-utc", "the no-push window is read in UTC, so it misses the recorders all winter",
     lambda w: _sub(w / "tools/push_window.py", 'NY = ZoneInfo("America/New_York")', "NY = timezone.utc"),
     "the pre-push hook refuses a hand push while the recorders commit"),
    ("push-window-unhooked", "the pre-push hook stops consulting the no-push window",
     lambda w: _sub(w / "tools/hooks/pre-push", '"$PY" tools/push_window.py || exit 1\n', ""),
     "the pre-push hook refuses a hand push while the recorders commit"),
    ("push-window-checked-first", "the window is checked before the pressure test, whose run can carry a push into it",
     lambda w: (_sub(w / "tools/hooks/pre-push", '"$PY" tools/push_window.py || exit 1\n', ""),
                _sub(w / "tools/hooks/pre-push", 'out=$("$PY" tools/pressure_test.py',
                     '"$PY" tools/push_window.py || exit 1\nout=$("$PY" tools/pressure_test.py')),
     "the pre-push hook refuses a hand push while the recorders commit"),
    ("interior-gaps-ignored", "a missed day inside the panel goes unreported",
     lambda w: _sub(w / "tools/panel_health.py", "        if (d.weekday() < 5 and d not in US_MARKET_HOLIDAYS and d not in have",
                    "        if (False and d not in have"),
     "a missed day INSIDE the panel is reported"),
    ("h3-bar-not-strict", "the H3 scorer passes H3a at exactly 1.0 ('under 1.0' is strict)",
     lambda w: _sub(w / "tools/h3_scorer.py", "lambda m: m < H3A_BAR)", "lambda m: m <= H3A_BAR)"),
     "the frozen H3 scorer passes its known-answer tests"),
    ("h3-bootstrap-two-sided", "the H3c bootstrap counts both tails (a negative slope could pass)",
     lambda w: _sub(w / "tools/h3_scorer.py", "        hits += ts >= t", "        hits += abs(ts) >= abs(t)"),
     "the frozen H3 scorer passes its known-answer tests"),
    ("h7-companion-leaks", "the registered H7 replica reads the matched (cut) chain",
     lambda w: _sub(w / "tools/h7_reader.py", "    opra = replica(ochain, exps, when, R) if ochain is not None else None",
                    "    opra = replica(match_chain(ochain, quotes_from_rows(rows)), exps, when, R) if ochain is not None else None"),
     "H7's reader tests pass"),
    ("writer-ignores-own-judgement", "the verdict writer stops checking modelfree's full-precision judgement",
     lambda w: _sub(w / "tools/record_verdict.py",
                    '    if (own.group(1) == "under") != sc["under"] or (own.group(2) == "majority") != sc["majority"]:',
                    "    if False:"),
     "the writer refuses H5e on a full-precision judgement mismatch"),
    ("writer-any-rate", "the verdict writer accepts any risk-free rate (a missing cache gives r = 0)",
     lambda w: _sub(w / "tools/record_verdict.py", "        return abs(float(str(rf_text).rstrip(\"%\")) - FROZEN_RATE_PCT) < 0.0005",
                    "        return True"),
     "the writer refuses H5e on a full-precision judgement mismatch"),
    ("writer-h7-missing-days", "the verdict writer stops noticing H7 days that dropped silently",
     lambda w: _sub(w / "tools/record_verdict.py", "            if h7_gone and not a.preview:", "            if False:"),
     "the writer refuses H7 on a mismatch with h7_reader's own verdict"),
    ("guard-commits", "the guard starts committing to main",
     lambda w: _sub(w / ".github/workflows/guard.yml", "        run: python tools/guard.py",
                    "        run: python tools/guard.py && git" + " commit --allow-empty -m x"),
     "the guard never commits, installs nothing, and may only start a re-run"),
    ("health-phone-only-on-success", "health's phone step is skipped whenever the daily check fails",
     lambda w: _sub(w / ".github/workflows/health.yml",
                    "      - name: Tell Gabriel's phone\n        if: always()", "      - name: Tell Gabriel's phone\n        if: success()"),
     "health's phone step runs even when the daily check fails"),
    ("health-pages-red", "the nightly check wakes Gabriel with RED",
     lambda w: _sub(w / ".github/workflows/health.yml", "--level yellow", "--level red"),
     "only the guard can send RED"),
    ("describe-p-flipped", "the descriptive one-sided p reads the wrong tail",
     lambda w: _sub(w / "tools/describe.py", 'out["p_bar"] = frac_le if side == "below" else 1.0 - frac_le',
                    'out["p_bar"] = 1.0 - frac_le if side == "below" else frac_le'),
     "the descriptive-statistics tests pass"),
    ("describe-ignores-dependence", "n_eff stops discounting persistent days",
     lambda w: _sub(w / "tools/describe.py", '"n_eff": n_eff(T, rho)', '"n_eff": float(T)'),
     "the descriptive-statistics tests pass"),
    ("writer-tests-read-live-files", "the writer tests read the live hypothesis files (recording a verdict would fail them)",
     lambda w: _sub(w / "tools/pressure_test.py", "def _hide_marks(t):\n    return t.replace(", "def _hide_marks(t):\n    return t; t.replace("),
     "the writer tests read copies with the not-yet-written verdicts hidden"),
    ("writer-preview-dies-on-h5f", "the verdict writer's preview aborts when the frozen H5f script fails",
     lambda w: _sub(w / "tools/record_verdict.py", "            if not (MARK_H5F in h5 and a.preview):\n                raise",
                    "            if True:\n                raise"),
     "the writer's preview survives the frozen H5f script failing"),
    ("bloomberg-positional-cells", "the Bloomberg reader goes back to reading cells in order (an omitted IVM drops the put)",
     lambda w: _sub(w / "tools/bloomberg_compare.py", 'POSITIONAL = os.environ.get("VOLREC_BBG_POSITIONAL") == "1"', "POSITIONAL = True"),
     "a Bloomberg row with an omitted IVM cell keeps its put"),
    ("independent-shares-code", "the independent replica starts importing project code (it could share a reader's mistake)",
     lambda w: _sub(w / "tools/independent_replica.py", "import csv\n", "import csv\nimport alert\n"),
     "the independent re-implementation passes its own known-answer tests"),
    ("independent-no-stop", "the independent replica's Cboe rule stops honouring two consecutive zero bids",
     lambda w: _sub(w / "tools/independent_replica.py", '            elif rule == "cboe":\n                zeros += 1\n                if zeros >= 2:',
                    '            elif rule == "cboe":\n                zeros += 1\n                if zeros >= 99:'),
     "the independent re-implementation passes its own known-answer tests"),
    ("independent-clock-flipped", "the independent H7 clock swaps daylight and standard time",
     lambda w: _sub(w / "tools/independent_replica.py", "20 if dst else 21", "21 if dst else 20"),
     "the independent re-implementation passes its own known-answer tests"),
    ("independent-half-variance", "the independent variance sum loses its factor of 2",
     lambda w: _sub(w / "tools/independent_replica.py", "    return 2 / T * tot - (F / K0 - 1) ** 2 / T", "    return 1 / T * tot - (F / K0 - 1) ** 2 / T"),
     "the independent re-implementation passes its own known-answer tests"),
    ("vault-resealed", "the discovery vault's split is redrawn after sealing",
     lambda w: _sub(w / "lab/vault.py", "SEED = 20261014", "SEED = 20261015"),
     "lab/ tests pass"),
    ("monthly-short-legs", "the monthly pass accepts expiries under 7 days",
     lambda w: _sub(w / "surface.py", "MONTHLY_MIN_DAYS = 7", "MONTHLY_MIN_DAYS = 0"),
     "the monthly pass takes Cboe's two nearest monthlies"),
    ("monthly-before-registered", "the monthly pass runs before surface.csv is written",
     lambda w: _sub(w / "surface.py", "            record_monthly(s, spots, today)\n", "") or
               _sub(w / "surface.py", "    if rows:\n        append(rows)", "    if rows:\n        record_monthly(s, spots, today)\n        append(rows)"),
     "the monthly pass runs only after surface.csv is written"),
    ("h6-lookahead", "H6 forecasts the SAME day's range (look-ahead)",
     lambda w: _sub(w / "samples/long/h6_range.py", "out.append((d, log(nh / nl),", "out.append((d, log(h / l),"),
     "H6's unit tests pass"),
    ("h6-no-hln", "H6 drops the Harvey-Leybourne-Newbold correction",
     lambda w: _sub(w / "samples/long/h6_range.py", "stat = t * sqrt((T - 1) / T)", "stat = t"),
     "H6's unit tests pass"),
    ("h6-atr-seed", "H6 seeds Wilder's ATR with the first true range instead of 14",
     lambda w: _sub(w / "samples/long/h6_range.py", "            if len(trs) == n:", "            if len(trs) == 1:"),
     "H6's unit tests pass"),
    ("h6-workflow-scheduled", "the H6 analysis workflow gains a schedule",
     lambda w: _sub(w / ".github/workflows/h6.yml", "on:\n  workflow_dispatch:\n", "on:\n  workflow_dispatch:\n  schedule:\n    - cron: '0 3 * * *'\n"),
     "no leftover TEMP workflows"),
    ("h6-workflow-no-pipefail", "the H6 workflow pipes through tee without pipefail (a crash reads as success)",
     lambda w: _sub(w / ".github/workflows/h6.yml", "          set -o pipefail\n", ""),
     "no leftover TEMP workflows"),
    ("ovx-blank-bid-null", "the OVX replica reads OPRA's blank bid as a null quote again (8 Oct)",
     lambda w: _sub(w / "tools/ovx_replicate.py", "    return (0.0 if bid is None else bid, 0.0 if ask is None else ask)",
                    "    return (bid, ask)"),
     "the OVX replica reads OPRA's blank bid as a zero bid"),
    ("h7-blank-bid-null", "the OVX replica reads OPRA's blank bid as a null quote again, seen through H7",
     lambda w: _sub(w / "tools/ovx_replicate.py", "    return (0.0 if bid is None else bid, 0.0 if ask is None else ask)",
                    "    return (bid, ask)"),
     "H7's reader tests pass"),
    ("analyze-stride-unbound", "analyze.py's report prints `stride` before assigning it again",
     lambda w: _sub(w / "analyze.py", "    stride = max(NONOVERLAP_STRIDE, win_td)   # never shorter than the window itself\n",
                    "", 1) or _sub(w / "analyze.py", "    sub = xs[::stride]",
                                   "    stride = max(NONOVERLAP_STRIDE, win_td)\n    sub = xs[::stride]"),
     "analyze.py's live-panel report runs end to end"),
    ("analyze-cost-units", "the cost block forgets that vega is per volatility point",
     lambda w: _sub(w / "analyze.py", "((a - b) / 2.0) / v / 100.0", "((a - b) / 2.0) / v"),
     "the cost block converts half-spread / vega"),
    ("sign-test-double-count", "the sign test's lower tail counts P(X = pos) twice again",
     lambda w: _sub(w / "analyze.py", "    p = 2.0 * min(tail(pos), 1.0 - tail(pos + 1))",
                    "    p = 2.0 * min(tail(pos), 1.0 - tail(pos + 1) + (comb(n, pos) / 2.0 ** n))"),
     "the sign test's p is the exact two-sided binomial"),
    ("final-h5e-no-wait", "the H5e FINAL is written on 12 Nov even with 11 Nov's OVX close missing",
     lambda w: _sub(w / "tools/record_verdict.py", "        if final and late and str(today) < COMPLETE_BY and not a.preview:",
                    "        if False:"),
     "the final readings WAIT while a day in their window lacks"),
    ("final-h7-no-wait", "H7 is written on 12 Nov even with 11 Nov's OPRA missing",
     lambda w: _sub(w / "tools/record_verdict.py", "        if waiting and str(today) < COMPLETE_BY and not a.preview:",
                    "        if False:"),
     "the final readings WAIT while a day in their window lacks"),
    ("final-h5e-no-crosscheck", "the H5e FINAL loses its cross-check against modelfree's tally",
     lambda w: _sub(w / "tools/record_verdict.py", "        bad = crosscheck(out, sc)                           # against modelfree's own tally",
                    "        bad = crosscheck(out, sc) if not final else None"),
     "the H5e FINAL is cross-checked against modelfree's own tally"),
    ("guard-early-close-ignored", "the after-close guard forgets NYSE's 1 p.m. early closes",
     lambda w: _sub(w / "record.py", "        if ny.date() in EARLY_CLOSES:\n            return (ny.hour, ny.minute) >= (13, 0)\n", ""),
     "the guard knows NYSE's 1 p.m. early closes"),
    ("early-closes-disagree", "panel_health's early-close list loses 24 Dec 2026",
     lambda w: _sub(w / "tools/panel_health.py", "EARLY_CLOSES = {date(2026, 11, 27), date(2026, 12, 24), ",
                    "EARLY_CLOSES = {date(2026, 11, 27), "),
     "record.py and panel_health carry the same early closes"),
    ("backup-rule-gone", "the ATM recorder stops applying the early-backup rule",
     lambda w: _sub(w / "record.py", "    if backup_too_early():", "    if False:"),
     "both recorders apply the backup rule"),
    ("backup-rule-utc", "the early-backup rule judges 14:30 as UTC, not New York",
     lambda w: _sub(w / "record.py", "TRIGGER_NY, EARLY_TRIGGER_NY, BACKUP_GRACE_MIN = (14, 30), (11, 30), 15",
                    "TRIGGER_NY, EARLY_TRIGGER_NY, BACKUP_GRACE_MIN = (18, 30), (11, 30), 15"),
     "a GitHub backup starting before the trigger's slot"),
    ("trigger-window-utc", "panel_health judges the trigger window in UTC minutes again",
     lambda w: _sub(w / "tools/panel_health.py", "        ny = ny_minutes(days[-1], mid)\n", "        ny = mid\n"),
     "the trigger window is judged in New York time"),
    ("protocol-noise-floor-dropped", "the hypothesis template stops asking for the noise floor",
     lambda w: _sub(w / "hypotheses/TEMPLATE.md", "## Noise floor", "## Notes"),
     "the protocol holds"),
    ("h7-bar-a-moved", "the verdict writer's H7a bar moves from 0.25 to 0.35",
     lambda w: _sub(w / "tools/record_verdict.py", 'H7_DUE, H7_MIN_DAYS, H7_BAR_A, H7_BAR_B = "2026-11-12", 10, 0.25, 0.30',
                    'H7_DUE, H7_MIN_DAYS, H7_BAR_A, H7_BAR_B = "2026-11-12", 10, 0.35, 0.30'),
     "the verdict writer reads H7 by its registered bars"),
    ("h7-reader-bar-moved", "the H7 reader's bar moves from 0.25 to 0.35",
     lambda w: _sub(w / "tools/h7_reader.py", "BAR_A, BAR_B = 0.25, 0.30", "BAR_A, BAR_B = 0.35, 0.30"),
     "H7's reader tests pass"),
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
    # 28 Oct 2026 - the outside review's guards (Astra; verified and fixed by Vega). Each must be caught.
    ("h3-nan-statistic-holds", "the H3 scorer gives a verdict on an undefined (NaN) cluster t (review R1)",
     lambda w: _sub(w / "tools/h3_scorer.py", "    if not (math.isfinite(b) and math.isfinite(t)):", "    if False:"),
     "the frozen H3 scorer passes its known-answer tests"),
    ("h3-ignores-display-rounding", "the H3 scorer judges printed (rounded) gaps as exact at the bar (review R3)",
     lambda w: _sub(w / "tools/h3_scorer.py", "    h = half_ulp\n", "    h = 0.0\n"),
     "the frozen H3 scorer passes its known-answer tests"),
    ("h3-reads-rounded-print", "the H3 scorer reads modelfree's 2-decimal print instead of --precise (review R3)",
     lambda w: _sub(w / "tools/h3_scorer.py", 'str(ROOT / "modelfree.py"), "--precise"]', 'str(ROOT / "modelfree.py")]'),
     "the H3 scorer reads modelfree at full precision"),
    ("h3-bh-family-shrinks", "an untestable pair leaves the BH family, so fewer tests make rejection easier (review R4)",
     lambda w: _sub(w / "tools/h3_scorer.py", "            for s in BENCH}", "            for s in BENCH if per.get(s)}"),
     "the frozen H3 scorer passes its known-answer tests"),
    ("h7-nan-counts-as-day", "H7 counts a NaN or infinite value as a day (review R8)",
     lambda w: _sub(w / "tools/h7_reader.py", "    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)",
                    "    return v is not None"),
     "H7's reader tests pass"),
    ("h7-uncounted-day-unnamed", "the H7 record stops naming days that have a row but do not count (review R5)",
     lambda w: _sub(w / "tools/record_verdict.py", "    if not_counted:\n", "    if False:\n"),
     "the H7 record names every day that has a row but does not count"),
    ("h7-nan-input-not-waited", "an OPRA file giving a NaN reading is listed but not waited on (Astra follow-up)",
     lambda w: _sub(w / "tools/h7_reader.py", '    elif not _ok(x["opra"]):\n', '    elif x["opra"] is None:\n'),
     "H7's reader tests pass"),
    ("lab-strip-crossed-costs-zero", "a crossed quote on a held strip leg is charged zero instead of refused (Astra follow-up)",
     lambda w: _sub(w / "lab/costs.py", "            if any(h is None for _w, h in held.values()):\n",
                    "            if False:\n"),
     "lab/ tests pass"),
    ("panel-metadata-passes-window", "the price cache's metadata keys satisfy the forward-window check again (review R2)",
     lambda w: _sub(w / "analyze.py", 'avail = sorted(k for k in series if not k.startswith("_"))',
                    'avail = sorted(k for k in series if k != "_end")'),
     "a forward window whose prices stop early is dropped with or without the cache's metadata keys"),
    ("independent-empty-agrees", "the independent check counts two empty values as an agreement (review R6)",
     lambda w: _sub(w / "tools/independent_check.py",
                    "        if a is None and b is None:\n            both_none += 1\n            continue\n        n += 1\n",
                    "        n += 1\n        if a is None and b is None:\n            both_none += 1\n            agree += 1\n            continue\n"),
     "the independent check counts only finite pairs as agreement"),
    ("describe-h7-wider-sample", "the H7 descriptive series include days the registered summary does not count (review M04)",
     lambda w: _sub(w / "tools/describe.py",
                    '        if "n/a" in (m.group(3), m.group(4), m.group(5), fo, fc):\n            continue\n'
                    '        s[f"{sym}_a"].append(abs(float(fo)))\n',
                    '        if fo != "n/a":\n            s[f"{sym}_a"].append(abs(float(fo)))\n'
                    '        if fc == "n/a":\n            continue\n'),
     "the descriptive-statistics tests pass"),
    ("lab-split-ignored", "a USO contract held across the 2020 reverse split settles on the new share (review M03)",
     lambda w: _sub(w / "lab/trades.py", 'DELIVERABLE = {"USO": (("2020-04-29", 0.125),)}', "DELIVERABLE = {}"),
     "lab/ tests pass"),
    ("lab-roots-overwrite", "two option roots for one expiry silently overwrite each other (review M03)",
     lambda w: _sub(w / "lab/integrity.py", "        if len(roots) > 1:\n", "        if False:\n"),
     "lab/ tests pass"),
    ("lab-strip-rebuilds-basket", "the fixed strip cost re-runs the estimator on bids again (review M02)",
     lambda w: _sub(w / "lab/costs.py", "    from math import sqrt\n    import modelfree\n    live =",
                    "    return strip_cost(rows, r)\n    from math import sqrt\n    import modelfree\n    live ="),
     "lab/ tests pass"),
    ("delta-keeps-after-close", "the H4 delta sensitivity keeps the after-close days (review M07)",
     lambda w: _sub(w / "tools/delta_model.py", '    rows = [r_ for r_ in rows if r_["date"] not in dropped]\n', "    pass\n"),
     "the H4 delta sensitivity drops the after-close days H4 itself drops"),
    ("health-starts-committing", "the health check starts committing to main",
     lambda w: _sub(w / ".github/workflows/health.yml",
                    "          python tools/daily.py --no-pull | tee report.txt\n",
                    "          python tools/daily.py --no-pull | tee report.txt\n          git commit -am report\n"),
     "health is read-only and never commits"),
    # 3 Nov 2026 - the deep audit's fixes (Gabriel: "check everything"). Each new check must be caught.
    ("side-job-writes-fred-cache", "a pressure-test side job writes data/fred_cache.json (calibrate did, with a real key)",
     lambda w: _sub(w / "tools/calibrate.py", "def main():\n",
                    'def main():\n    (ROOT / "data" / "fred_cache.json").write_text("{}")\n'),
     "this run left data/fred_cache.json as it found it"),
    ("fred-placeholder-fetches", "FRED_KEY=use-cache goes to FRED again on a cache miss",
     lambda w: _sub(w / "tools/fred.py", '    if k == "use-cache":', "    if False:"),
     "FRED_KEY=use-cache reads the cache only"),
    ("trigger-token-lapses", "the cron-job.org trigger's token is days from lapsing",
     lambda w: _sub(w / "tools/pressure_test.py", "TRIGGER_TOKEN_EXPIRES = date(",
                    "TRIGGER_TOKEN_EXPIRES = date.today() or date("),
     "the cron-job.org trigger's GitHub token has more than a week left"),
    ("licensed-token-lapses", "the private run's PUBLIC_REPO_TOKEN is days from lapsing",
     lambda w: _sub(w / "tools/pressure_test.py", "LICENSED_TOKEN_EXPIRES = date(",
                    "LICENSED_TOKEN_EXPIRES = date.today() or date("),
     "the private run's GitHub token (PUBLIC_REPO_TOKEN) has more than a week left"),
    ("daily-skips-rate-seed", "GitHub's nightly H3/H5e lines read r = 0 again (no frozen seed)",
     lambda w: _sub(w / "tools/daily.py", '    code, out = run([PY, "tools/seed_frozen_rate.py"])\n',
                    '    code, out = 0, ""\n'),
     "daily.py seeds the frozen rate where there is no cache and checks it where there is"),
    # 3 Nov 2026, Astra's review: a cache that exists without the registered rate gave a quiet r = 0.
    ("daily-ignores-seed-failure", "daily.py reads on past a cache without the registered rate (r = 0, ALL CLEAR)",
     lambda w: _sub(w / "tools/daily.py", '        bad.append("frozen rate")\n', "        pass\n"),
     "daily.py seeds the frozen rate where there is no cache and checks it where there is"),
    # 3 Nov 2026, Astra's follow-up review: the text check above passes `if False:`; the stubbed run must not.
    ("daily-seed-test-disabled", "daily.py's test of the seed is switched off (if False:), so a failed seed reads ALL CLEAR",
     lambda w: _sub(w / "tools/daily.py", '    if code or crashed(out):\n        print("  FROZEN RATE NOT READY',
                    '    if False:\n        print("  FROZEN RATE NOT READY'),
     "a seed that fails (exit 1) or crashes makes the day LOOK AT: frozen rate"),
    ("daily-seed-crash-unseen", "daily.py tests only the seed's exit code, so a seed crash reads ALL CLEAR",
     lambda w: _sub(w / "tools/daily.py", '    if code or crashed(out):\n        print("  FROZEN RATE NOT READY',
                    '    if code:\n        print("  FROZEN RATE NOT READY'),
     "a seed that fails (exit 1) or crashes makes the day LOOK AT: frozen rate"),
    ("cache-lacks-frozen-rate", "the FRED cache holds other series but not the registered rate",
     lambda w: _write(w / "data" / "fred_cache.json", '{"OTHER||": {"2026-09-10": 1.0}}'),
     "the fresh-clone seed carries the registered rate"),
    ("seed-accepts-wrong-cache", "the seed passes a cache without the registered rate",
     lambda w: _sub(w / "tools/seed_frozen_rate.py", "sys.exit(0 if same else 1)", "sys.exit(0)"),
     "the seed writes the rate where there is no cache and leaves a cache untouched"),
    ("site-start-time-drifts", "the site's record start drifts from record.py's 14:30 New York",
     lambda w: _sub(w / "tools/volrec.js", '{"record": [14, 30],', '{"record": [14, 47],'),
     "site's start times match record.py and the guard"),
    ("site-holiday-dropped", "the site's holiday list loses Thanksgiving",
     lambda w: _sub(w / "tools/volrec.js", '"2026-11-26", ', ""),
     "site's early closes and holidays match record.py and panel_health.py"),
    ("site-rail-counts-to-surface", "the rail's countdown is wired to the wrong recorder",
     lambda w: _sub(w / "tools/volrec.js", 'V.nextTrigger("record", now)', 'V.nextTrigger("surface", now)'),
     "the site's countdowns count to the recorders' real start"),
    # 4 Nov 2026: the Lab page (tools/lab.html, rendered by lab/report.py) publishes OPRA-derived aggregates.
    ("lab-page-uncredited", "a table on the Lab page loses its Databento credit",
     lambda w: _sub(w / "tools/lab.html", '<div class="src">Data provided by Databento (OPRA consolidated NBBO).',
                    '<div class="src">(OPRA consolidated NBBO).'),
     "every section and every figure of the Lab page credits Databento"),
    # Astra, 4 Nov 2026: a part stating only whole numbers passed uncredited. The generator and the page change
    # together, so only the credit rule can catch it.
    ("lab-page-integer-uncredited", "the Lab page's Data sources section, which states only whole numbers, loses its credit",
     lambda w: (_sub(w / "lab/report.py", "Databento, Inc. Data provided by Databento. Derived", "Databento, Inc. Derived"),
                _sub(w / "tools/lab.html", "Databento, Inc. Data provided by Databento. Derived", "Databento, Inc. Derived")),
     "every section and every figure of the Lab page credits Databento"),
    ("lab-page-fetches-opra", "the Lab page's script starts fetching an OPRA file",
     lambda w: _sub(w / "tools/lab.html", 'V.load("data/surface.csv", "../")]',
                    'V.load("data/surface.csv", "../"), fetch("../data/opra.csv")]'),
     "the site's code loads no OPRA data"),
    ("lab-page-unlinked", "the paper's navigation loses the Lab page",
     lambda w: _sub(w / "index.html", ', ["Lab", "tools/lab.html", "lab"]', ""),
     "every page's navigation reaches the Lab page"),
    # Astra, 4 Nov 2026: a figure is held to the registration's figure for the same fund. Here the generator pins two
    # funds' COVID losses on each other and the page is re-rendered to match, so the page still equals the render and
    # every number on it is still somewhere in the registration.
    ("lab-page-claims-swapped", "the Lab page gives IWM's COVID loss to USO and USO's to IWM",
     lambda w: (_sub(w / "lab/report.py", '    added, covid = p3plan["added"], p3plan["covid"]\n',
                     '    added, covid = p3plan["added"], p3plan["covid"]\n'
                     '    covid = {**covid, "IWM": covid["USO"], "USO": covid["IWM"]}\n'),
                _sub(w / "tools/lab.html", 'IWM <span class="m">34.8%</span> and USO <span class="m">29.4%</span>',
                     'IWM <span class="m">29.4%</span> and USO <span class="m">34.8%</span>')),
     "the COVID sentence names the registration's three largest COVID losses"),
    # Astra's follow-up, 4 Nov 2026: a key number's value was checked anywhere on the page, not under its own label.
    # Only the label moves, in the generator and the page alike, so the page still equals the render and every
    # figure on it is still right.
    ("lab-page-kpi-mislabelled", "the Lab page's key numbers show SPY's COVID loss under QQQ's name",
     lambda w: (_sub(w / "lab/report.py", 'kpi("SPY\'s COVID month"', 'kpi("QQQ\'s COVID month"'),
                _sub(w / "tools/lab.html", '<div class="kpi-k">SPY\'s COVID month</div>',
                     '<div class="kpi-k">QQQ\'s COVID month</div>')),
     "every key number at the top of the Lab page sits under its own label"),
    ("lab-page-partial-skip", "the Lab page's generator treats a half-copied summaries folder as a fresh clone",
     lambda w: _sub(w / "lab/report.py", "    if not have:\n        return None", "    if len(have) < len(INPUTS):\n        return None"),
     "lab/ tests pass"),
    ("lab-page-margin-range-unchecked", "the Leak Map checks only the margin leaks' mean, not their range over the orders",
     lambda w: _sub(w / "lab/report.py", 'if any(v != 0.0 for v in d["leaks"][k]):', 'if d["leaks"][k][0] != 0.0:'),
     "lab/ tests pass"),
]
# The pressure test runs the site's countdown in node; where node is missing that check is only a WARN, so
# its mutant would be INCONCLUSIVE rather than KILLED. It runs wherever the check can.
if shutil.which("node"):
    MUTANTS.append(("site-countdown-ignores-holidays", "the site's countdown counts to a market holiday",
                    lambda w: _sub(w / "tools/volrec.js", " || V.HOLIDAYS.includes(iso)) continue;", ") continue;"),
                    "the site's countdown lands on the recorders' next real start"))
    # 3 Nov 2026: the 13 Sep formula, which read "1h 60m ago" for 30 s an hour.
    MUTANTS.append(("site-ago-reads-60m", "the rail's 'ago' rounds the minutes after taking the hours again",
                    lambda w: _sub(w / "tools/volrec.js",
                                   '    const m = Math.round(Math.max(0, ms) / 6e4);\n    return m < 60 ? m + "m ago" : '
                                   'm < 2880 ? Math.floor(m / 60) + "h " + p2(m % 60) + "m ago" : Math.floor(m / 1440) '
                                   '+ "d ago";',
                                   '    const h = Math.max(0, ms) / 36e5;\n    return h < 1 ? Math.round(h * 60) + "m ago" : '
                                   'h < 48 ? Math.floor(h) + "h " + p2(Math.round((h % 1) * 60)) + "m ago" : '
                                   'Math.floor(h / 24) + "d ago";'),
                    "the site's 'ago' never reads 60m"))


# The Lab page is compared with the private lab summaries only where they exist (this Mac); elsewhere the
# check is a SKIP, so its mutant would be INCONCLUSIVE rather than KILLED. It runs wherever the check can.
if (Path.home() / "Documents" / "volrec-licensed" / "lab-out" / "leak_summary.json").exists():
    MUTANTS.append(("lab-page-hand-edited", "a figure on the Lab page is edited by hand instead of re-rendered",
                    lambda w: _sub(w / "tools/lab.html", '<span class="lm-v">95.4¢</span>', '<span class="lm-v">96.4¢</span>'),
                    "the Lab page is exactly what lab/report.py renders from the lab summaries"))


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
