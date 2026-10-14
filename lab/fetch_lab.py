#!/usr/bin/env python3
"""lab/ - OPRA purchases for the retail implementation audit (EXPLORATORY).

Priced first with Databento's get_cost; refused past the per-request cap, the $100 lifetime cap,
or the lab's own $75 cap (LAB_BUDGET_USD); refused for any day outside LAB_START..LAB_END, which
keeps the lab clear of every registered window. Files go to the private repo's checkout under
opra-lab/ (git-excluded there, never in the public repo). The ledger is the private repo's
opra/spend.csv, the same one the cloud's daily run checks, so it is pulled before buying and
committed and pushed after.

  FRED_KEY=use-cache python lab/fetch_lab.py --day 2018-02-05 --symbols SPY,QQQ,IWM,GLD,USO --dry-run
"""
import argparse
import csv
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")
import opra_reference as ore               # noqa: E402

LAB_BUDGET_USD = 90.00                     # $75 at registration; $90 on 12 Oct to cover OPRA listings
LAB_START, LAB_END = "2015-08-01", "2026-08-31"
LAB_TAG = "-lab"
DEF_TAG = "-def-lab"                       # listings rows; ends in LAB_TAG, so the lab cap counts them
PRIVATE = Path(os.environ.get("VOLREC_LICENSED_DIR") or Path.home() / "Documents" / "volrec-licensed")
LAB_DIR = PRIVATE / "opra-lab"
LEDGER = PRIVATE / "opra" / "spend.csv"
LEDGER_LOCK = threading.Lock()             # buy_days.py buys the five funds in parallel


def date_ok(day):
    return LAB_START <= day <= LAB_END


def ny_minute(day, hhmm="14:30"):
    h, m = map(int, hhmm.split(":"))
    local = datetime.fromisoformat(day).replace(hour=h, minute=m, tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def lab_stem(symbol, day, hhmm):
    return f"OPRA_LAB_{symbol}_{day}_{hhmm.replace(':', '')}"


def def_stem(symbol, day):
    return f"DEF_LAB_{symbol}_{day}"


def ledger_rows():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as f:
        return list(csv.DictReader(f))


def spent_all(rows):
    return sum(float(r["usd"]) for r in rows if r.get("usd"))


def spent_lab(rows):
    return sum(float(r["usd"]) for r in rows if r.get("usd") and r.get("symbol", "").endswith(LAB_TAG))


def lab_budget_ok(cost, spent):
    """(allowed, reason). Pure, so the cap is tested without spending anything."""
    if spent + cost > LAB_BUDGET_USD:
        return False, f"would take lab spend to ${spent + cost:.2f}, past its ${LAB_BUDGET_USD:.2f} cap"
    return True, "within the lab's cap"


def _post_patiently(url, **kw):
    """requests.post, waiting out Databento's rate limit (HTTP 429) instead of stopping."""
    import requests
    for wait in (5, 15, 30, 60, 120, 240):
        r = requests.post(url, **kw)
        if r.status_code != 429:
            return r
        print(f"    Databento rate limit (429), waiting {wait}s")
        ore._sleep(wait)
    return requests.post(url, **kw)


class Unresolvable(Exception):
    """Databento 422 symbology_invalid_request: nothing listed under that symbol on that date.
    Permanent, so the request is skipped and reported, never retried (14 Oct: one ended a batch)."""


def _call(endpoint, data, key, tries=4):
    """ore.call, plus retries when Databento is slow to answer (a read timeout, 14 Oct 2026: the
    gateway retried 504s itself, but a timeout ended a 1,270-request batch). Then stop loudly."""
    import requests
    for i in range(tries):
        try:
            return ore.call(endpoint, data, key, _fn=_post_patiently)
        except SystemExit as e:
            # ore.call stops after three quick retries of a gateway error (502/503/504); a long
            # batch outlives a busy hour, so wait minutes, not seconds (14 Oct: a 504 ended the run).
            if " returned 422" in str(e) and "symbology" in str(e):
                raise Unresolvable(str(e)[:160])
            if " returned 50" not in str(e) or i == tries - 1:
                raise
            print(f"    Databento {endpoint}: gateway error, retrying in {120 * (i + 1)}s")
            ore._sleep(120 * (i + 1))
        except requests.exceptions.Timeout:
            if i == tries - 1:
                sys.exit(f"Databento {endpoint}: timed out {tries} times; stopping (nothing half-written)")
            print(f"    Databento {endpoint}: timed out, retrying in {20 * (i + 1)}s")
            ore._sleep(20 * (i + 1))


def git(*args):
    return subprocess.run(["git", "-C", str(PRIVATE), *args], capture_output=True, text=True)


def sync_ledger():
    r = git("pull", "--ff-only", "-q")
    if r.returncode != 0:
        sys.exit(f"Could not update the private repo's ledger first: {r.stderr.strip()}")


def commit_ledger(n, usd):
    git("add", "opra/spend.csv")
    c = git("commit", "-q", "-m", f"spend: lab/ purchases, {n} file(s), ${usd:.4f}")
    if c.returncode != 0:
        return
    if git("pull", "--rebase", "-q").returncode != 0 or git("push", "-q").returncode != 0:
        print("  WARNING: the ledger commit is local only - push the private repo by hand")


def fetch(day, symbol, key, max_cost, dry, hhmm="14:30"):
    if not date_ok(day):
        sys.exit(f"{day} is outside the lab's dates ({LAB_START} to {LAB_END}); refused")
    if ore.inside_repo(LAB_DIR):
        sys.exit("Refusing a lab data folder inside the public repository.")
    out = LAB_DIR / f"{lab_stem(symbol, day, hhmm)}.csv"
    if out.exists():
        print(f"  {symbol} {day} {hhmm}: already on disk - skipped, nothing charged")
        return 0.0
    params = ore.request_params(symbol, ny_minute(day, hhmm))
    try:
        cost = float(_call("metadata.get_cost", params, key).json())
    except Unresolvable:
        print(f"  {symbol} {day} {hhmm}: SKIPPED - Databento lists nothing under {symbol}.OPT then; nothing charged")
        return 0.0
    rows = ledger_rows()
    allowed, why = ore.budget_ok(cost, max_cost, spent_all(rows))
    if allowed:
        allowed, why = lab_budget_ok(cost, spent_lab(rows))
    print(f"  {symbol} {day} {hhmm} NY: costs ${cost:.4f}; lab spent ${spent_lab(rows):.2f} of "
          f"${LAB_BUDGET_USD:.0f}; lifetime ${spent_all(rows):.2f}: {why}")
    if dry or not allowed:
        return 0.0
    body = dict(params, encoding="csv", compression="none", pretty_px="true",
                pretty_ts="true", map_symbols="true")
    try:
        r = _call("timeseries.get_range", body, key)
    except ore.NotYetHistorical as e:
        print(f"    not yet historical ({e}); nothing charged")
        return 0.0
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    with LEDGER_LOCK, LEDGER.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), day,
                                symbol + LAB_TAG, f"{cost:.6f}"])
    print(f"    fetched {len(r.content):,} bytes -> {out}")
    return cost


def _priced_buy(params, out, day, tag, key, max_cost, dry, label):
    """Price, check all three caps, buy, write the file and the ledger row. Returns dollars charged."""
    if out.exists():
        print(f"  {label}: already on disk - skipped, nothing charged")
        return 0.0
    try:
        cost = float(_call("metadata.get_cost", params, key).json())
    except Unresolvable:
        print(f"  {label}: SKIPPED - Databento cannot resolve the symbol for that date; nothing charged")
        return 0.0
    rows = ledger_rows()
    allowed, why = ore.budget_ok(cost, max_cost, spent_all(rows))
    if allowed:
        allowed, why = lab_budget_ok(cost, spent_lab(rows))
    print(f"  {label}: costs ${cost:.4f}; lab spent ${spent_lab(rows):.2f} of "
          f"${LAB_BUDGET_USD:.0f}; lifetime ${spent_all(rows):.2f}: {why}")
    if dry or not allowed:
        return 0.0
    body = dict(params, encoding="csv", compression="none", pretty_px="true",
                pretty_ts="true", map_symbols="true")
    try:
        r = _call("timeseries.get_range", body, key)
    except ore.NotYetHistorical as e:
        print(f"    not yet historical ({e}); nothing charged")
        return 0.0
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    with LEDGER_LOCK, LEDGER.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), day, tag, f"{cost:.6f}"])
    print(f"    fetched {len(r.content):,} bytes -> {out}")
    return cost


def fetch_listings(day, symbol, key, max_cost, dry):
    """OPRA's listed instruments for the whole day (Databento's definition schema): the
    completeness check compares every listed strike in the band against the quotes."""
    if not date_ok(day):
        sys.exit(f"{day} is outside the lab's dates ({LAB_START} to {LAB_END}); refused")
    d0 = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    params = {"dataset": ore.DATASET, "schema": "definition", "symbols": f"{symbol}.OPT",
              "stype_in": "parent", "stype_out": "instrument_id",
              "start": d0.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "end": (d0 + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return _priced_buy(params, LAB_DIR / f"{def_stem(symbol, day)}.csv", day, symbol + DEF_TAG,
                       key, max_cost, dry, f"{symbol} {day} listings")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", required=True)
    ap.add_argument("--symbols", default="SPY,QQQ,IWM,GLD,USO")
    ap.add_argument("--at", default="14:30", help="New York time, HH:MM")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cost", type=float, default=ore.DEFAULT_MAX_COST)
    a = ap.parse_args()
    key = ore.api_key()
    if not key:
        sys.exit("No Databento key (DATABENTO_API_KEY or ~/.config/volrec/databento.key)")
    if not a.dry_run:
        sync_ledger()
    paid = []
    for s in a.symbols.split(","):
        paid.append(fetch(a.day, s.strip(), key, a.max_cost, a.dry_run, a.at))
        paid.append(fetch_listings(a.day, s.strip(), key, a.max_cost, a.dry_run))
    n, usd = sum(1 for p in paid if p > 0), sum(paid)
    if n:
        commit_ledger(n, usd)
    print(f"\n{n} file(s) bought, ${usd:.4f}. {ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
