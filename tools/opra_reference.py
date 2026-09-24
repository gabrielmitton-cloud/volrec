#!/usr/bin/env python3
"""OPRA reference quotes (via Databento) at the recorder's OWN minute.

WHY THIS EXISTS
---------------
Every price-gate failure against Bloomberg so far (USO 15 Sep, TSLA 22 Sep) came
from the underlying moving between two snapshots taken minutes apart, and a
terminal session gives one or two matched days at best. OPRA is the consolidated
feed Bloomberg's option quotes come from. Databento sells it historically at
one-minute resolution, so the free feed can be checked against the consolidated
NBBO at the very minute the recorder took its snapshot, on EVERY recorded day,
with no terminal and no time gap. H5f registers what this is expected to show.

It is a REFERENCE, like Bloomberg: raw data stays outside the repository and only
aggregates are printed. Operations only (OPS-AGENT.md): it fetches and compares;
it never searches.

MONEY - read this. New Databento accounts carry a free credit ($125 when this was
written). Every request is priced FIRST with Databento's own get_cost call. The
tool refuses a request over --max-cost (default $0.50) and refuses anything that
would take the running total in the local ledger past LIFETIME_CAP_USD ($100),
leaving the rest of the credit as margin. --dry-run spends nothing at all.

KEY: environment variable DATABENTO_API_KEY, or the file ~/.config/volrec/databento.key
(chmod 600). Never inside this repository; the tool refuses one that is.
DATA: ~/Documents/volrec-databento/  (raw CSV, the spend ledger)

USAGE
-----
  python3 tools/opra_reference.py --date 2026-09-22 --dry-run     # what, and (with a key) what it costs
  python3 tools/opra_reference.py --date 2026-09-22               # price it, fetch if under the caps
  python3 tools/opra_reference.py --date 2026-09-22 --compare     # analyse what is on disk; no network
  python3 tools/opra_reference.py --all --dry-run                 # every wide day recorded so far
"""
import argparse
import csv
import os
import re
import statistics as st
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")   # the local cache, as daily.py does; never r=0 by accident

GATEWAY = "https://hist.databento.com/v0"
DATASET = "OPRA.PILLAR"
SCHEMA = "cbbo-1m"                     # consolidated BBO, one-minute; checked live against list_schemas
# The Mac's folder by default. The cloud run (the private volrec-licensed repository's
# workflow, 24 Sep 2026) points this at its own checkout; inside_repo() still refuses
# any path inside THIS repository, whatever the variable says.
DATA_DIR = Path(os.environ.get("VOLREC_DATABENTO_DIR") or Path.home() / "Documents" / "volrec-databento")
KEY_FILE = Path.home() / ".config" / "volrec" / "databento.key"
LEDGER = DATA_DIR / "spend.csv"
LIFETIME_CAP_USD = 100.0
DEFAULT_MAX_COST = 0.50
WINDOW_BEFORE, WINDOW_AFTER = 2, 3     # minutes around the snapshot's median quote time
MATCH_TOLERANCE_S = 120                # a contract with no OPRA record this close is excluded
ATTRIBUTION = "Data provided by Databento (OPRA consolidated NBBO). Aggregates only."
REFETCH = "--refetch" in sys.argv


# ---------------- pure helpers (tested by pressure_test.py, no network) ----------------
def compact(sym):
    """'USO   261016P00119000' or 'USO261016P00119000' -> 'USO261016P00119000'."""
    return "".join(str(sym).split())


def inside_repo(p):
    p = Path(p).expanduser().resolve()
    return p == ROOT or ROOT in p.parents


def columns(header):
    """Locate the fields this needs, by name, so a CSV layout change cannot silently
    mis-read a column (the 18 Sep Bloomberg export taught that)."""
    h = [c.strip() for c in header]
    def first(pred):
        return next((i for i, c in enumerate(h) if pred(c)), None)
    cols = {"symbol": first(lambda c: c == "symbol"),
            "ts": first(lambda c: c == "ts_recv") if "ts_recv" in h else first(lambda c: c == "ts_event"),
            "bid": first(lambda c: c.startswith("bid_px")),
            "ask": first(lambda c: c.startswith("ask_px"))}
    missing = [k for k, v in cols.items() if v is None]
    if missing:
        raise ValueError(f"OPRA CSV lacks {missing}; header was {h}")
    return cols


def price(v):
    """Pretty price or nothing. Databento marks an absent side with an undefined
    sentinel; anything empty, non-numeric or absurd is treated as no quote."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 0 <= f < 1e7 else None


def parse_ts(s):
    """ISO-8601 (any precision, Z or offset) or epoch nanoseconds -> aware UTC datetime.

    23 Sep 2026: the first version took every digit after the decimal point as the
    fraction, which swallowed the digits of a '+00:00' suffix, lost the zone, and let
    Python read the time as LOCAL - every snapshot minute came out seven hours off.
    The dry run caught it before a request was priced. A string with no zone is UTC
    here, never local time."""
    s = str(s).strip()
    if s.isdigit():                                    # nanoseconds since the epoch
        return datetime.fromtimestamp(int(s) / 1e9, timezone.utc)
    m = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})?$", s)
    if not m:
        raise ValueError(f"unparseable timestamp: {s!r}")
    head, frac, tz = m.group(1), (m.group(2) or "")[:6], m.group(3) or "Z"
    tz = "+00:00" if tz == "Z" else (tz if ":" in tz else f"{tz[:3]}:{tz[3:]}")
    return datetime.fromisoformat(f"{head}{'.' + frac if frac else ''}{tz}").astimezone(timezone.utc)


def load_opra(path):
    """{compact symbol: [(ts, bid, ask), ...]} from a Databento CSV."""
    out = {}
    with open(path, newline="") as f:
        rd = csv.reader(f)
        c = columns(next(rd))
        for r in rd:
            if len(r) <= max(c.values()):
                continue
            out.setdefault(compact(r[c["symbol"]]), []).append(
                (parse_ts(r[c["ts"]]), price(r[c["bid"]]), price(r[c["ask"]])))
    return out


def nearest(records, when, tol=MATCH_TOLERANCE_S):
    best = min(records, key=lambda x: abs((x[0] - when).total_seconds()), default=None)
    if best is None or abs((best[0] - when).total_seconds()) > tol:
        return None
    return best


def ledger_total():
    if not LEDGER.exists():
        return 0.0
    with LEDGER.open(newline="") as f:
        return sum(float(r["usd"]) for r in csv.DictReader(f) if r.get("usd"))


def budget_ok(cost, max_cost, spent):
    """(allowed, reason). Pure, so the caps are tested without spending anything."""
    if cost > max_cost:
        return False, f"costs ${cost:.4f}, over the per-request cap ${max_cost:.2f} (--max-cost to raise)"
    if spent + cost > LIFETIME_CAP_USD:
        return False, (f"would take lifetime spend to ${spent + cost:.2f}, past the "
                       f"${LIFETIME_CAP_USD:.0f} cap that keeps the rest of the free credit as margin")
    return True, "within both caps"


# ---------------- the recorder's side ----------------
def recorded(date, symbol):
    rows = []
    for name in ("surface.csv", "surface_wide.csv"):
        p = ROOT / "data" / name
        if p.exists():
            rows += [dict(r, _file=name) for r in csv.DictReader(p.open(newline=""))
                     if r["date"] == date and r["symbol"] == symbol]
    return rows


def snapshot_minute(rows):
    ts = sorted(parse_ts(r["quote_time"]) for r in rows if r.get("quote_time"))
    return ts[len(ts) // 2].replace(second=0, microsecond=0) if ts else None


def wide_days():
    p = ROOT / "data" / "surface_wide.csv"
    if not p.exists():
        return []
    return sorted({(r["date"], r["symbol"]) for r in csv.DictReader(p.open(newline=""))})


def request_params(symbol, minute):
    start = minute - timedelta(minutes=WINDOW_BEFORE)
    end = minute + timedelta(minutes=WINDOW_AFTER)
    return {"dataset": DATASET, "schema": SCHEMA, "symbols": f"{symbol}.OPT",
            "stype_in": "parent", "stype_out": "instrument_id",
            "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ")}


# ---------------- the network side ----------------
def api_key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip()
    if k:
        return k
    if KEY_FILE.exists():
        if inside_repo(KEY_FILE):
            sys.exit("Refusing a Databento key stored inside the repository.")
        return KEY_FILE.read_text().strip()
    return None


class NotYetHistorical(Exception):
    """OPRA is served historically only after a delay; newer data needs a live
    licence. Found 23 Sep 2026: 22 Sep's session was refused with a 403 the
    morning after. The day is skipped and becomes fetchable later."""


def call(endpoint, data, key, method="post"):
    import requests
    fn = requests.post if method == "post" else requests.get
    kw = {"data": data} if method == "post" else {"params": data}
    r = fn(f"{GATEWAY}/{endpoint}", auth=(key, ""), timeout=120, **kw)
    if r.status_code == 403 and "license" in r.text.lower():
        m = re.search(r"after (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", r.text)
        raise NotYetHistorical(m.group(1) + " UTC" if m else "a recent cutoff")
    if r.status_code != 200:
        sys.exit(f"Databento {endpoint} returned {r.status_code}: {r.text[:300]}")
    return r


def fetch(date, symbol, key, max_cost, dry):
    rows = recorded(date, symbol)
    minute = snapshot_minute(rows)
    if not minute:
        print(f"  {symbol} {date}: nothing recorded, nothing to request")
        return
    params = request_params(symbol, minute)
    print(f"  {symbol} {date}: snapshot minute {minute:%H:%M} UTC; request {params['symbols']} "
          f"{SCHEMA} {params['start'][11:16]}-{params['end'][11:16]} UTC")
    # 23 Sep 2026: `--all` re-bought 18 and 21 Sep because nothing checked the disk first.
    # Historical data does not change, so a file already here is never paid for twice.
    if not dry and not REFETCH and (DATA_DIR / f"OPRA_{symbol}_{date}.csv").exists():
        print("    already on disk - skipped, nothing charged (--refetch to buy it again)")
        return
    if not key:
        print("    no key yet - set DATABENTO_API_KEY or ~/.config/volrec/databento.key to price it")
        return
    schemas = call("metadata.list_schemas", {"dataset": DATASET}, key, "get").json()
    if SCHEMA not in schemas:
        sys.exit(f"{DATASET} does not offer {SCHEMA}; it offers {schemas}")
    cost = float(call("metadata.get_cost", params, key).json())
    spent = ledger_total()
    allowed, why = budget_ok(cost, max_cost, spent)
    print(f"    costs ${cost:.4f}; spent so far ${spent:.2f} of the ${LIFETIME_CAP_USD:.0f} cap: {why}")
    if dry or not allowed:
        return
    out = DATA_DIR / f"OPRA_{symbol}_{date}.csv"
    if inside_repo(out):
        sys.exit("Refusing to write OPRA data inside the repository.")
    body = dict(params, encoding="csv", compression="none", pretty_px="true",
                pretty_ts="true", map_symbols="true")
    try:
        r = call("timeseries.get_range", body, key)
    except NotYetHistorical as e:
        print(f"    not yet available historically (data after {e} needs a live licence); "
              f"nothing charged - run again tomorrow")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    new = not LEDGER.exists()
    with LEDGER.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["utc", "date", "symbol", "usd"])
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), date, symbol, f"{cost:.6f}"])
    print(f"    fetched {len(r.content):,} bytes -> {out}")


# ---------------- are the unmatched contracts listed on OPRA at all? ----------------
def definitions(date, symbol, key, max_cost, dry):
    """Added 23 Sep 2026. On 21 Sep, 13 far out-of-the-money USO puts with no bid had
    no OPRA quote record at all. Either OPRA lists them and the one-minute BBO file
    simply omits a contract with no quote on either side, or the free feed carries
    listings OPRA does not have. Databento's `definition` schema answers it: every
    listed instrument, per day."""
    d0 = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    params = {"dataset": DATASET, "schema": "definition", "symbols": f"{symbol}.OPT",
              "stype_in": "parent", "stype_out": "instrument_id",
              "start": d0.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "end": (d0 + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    print(f"  {symbol} {date}: definitions for {symbol}.OPT over the whole day")
    if not key:
        print("    no key"); return
    cost = float(call("metadata.get_cost", params, key).json())
    spent = ledger_total()
    allowed, why = budget_ok(cost, max_cost, spent)
    print(f"    costs ${cost:.4f}; spent so far ${spent:.2f}: {why}")
    if dry or not allowed:
        return
    out = DATA_DIR / f"DEF_{symbol}_{date}.csv"
    try:
        r = call("timeseries.get_range", dict(params, encoding="csv", compression="none",
                                              pretty_px="true", pretty_ts="true", map_symbols="true"), key)
    except NotYetHistorical as e:
        print(f"    not yet available historically (after {e}); nothing charged"); return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    with LEDGER.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), date,
                                f"{symbol}-definition", f"{cost:.6f}"])
    print(f"    fetched {len(r.content):,} bytes -> {out.name}")


def check_listed(date, symbol):
    """Unmatched recorded contracts: listed on OPRA that day, or not? Aggregates only."""
    q, dfile = DATA_DIR / f"OPRA_{symbol}_{date}.csv", DATA_DIR / f"DEF_{symbol}_{date}.csv"
    if not (q.exists() and dfile.exists()):
        print(f"  {symbol} {date}: need both OPRA_ and DEF_ files"); return
    quoted = set(load_opra(q))
    with dfile.open(newline="") as f:
        rd = csv.reader(f); h = next(rd)
        col = h.index("raw_symbol") if "raw_symbol" in h else h.index("symbol")
        listed = {compact(r[col]) for r in rd if len(r) > col}
    rows = recorded(date, symbol)
    spot = float(rows[0]["spot"])
    absent = [r for r in rows if compact(r["option_symbol"]) not in quoted]
    otm = lambda r: (r["type"] == "P") == (float(r["strike"]) < spot)
    zb = lambda r: not r["bid"] or float(r["bid"]) == 0
    in_def = [r for r in absent if compact(r["option_symbol"]) in listed]
    print(f"  {symbol} {date}: {len(listed):,} {symbol} options listed on OPRA; {len(absent)} recorded "
          f"contracts had no OPRA quote record")
    print(f"    of those: {len(in_def)} ARE listed on OPRA, {len(absent) - len(in_def)} are NOT listed")
    for label, sub in (("listed, no quote record", in_def),
                       ("not listed at all", [r for r in absent if r not in in_def])):
        if sub:
            print(f"    {label:<24} {len(sub):>3}: out of the money {sum(otm(r) for r in sub)}, "
                  f"zero bid on the free feed {sum(zb(r) for r in sub)}, "
                  f"strikes {min(float(r['strike']) for r in sub):g}-{max(float(r['strike']) for r in sub):g}")


# ---------------- the comparison (aggregates only) ----------------
def compare(date, symbol):
    import modelfree
    path = DATA_DIR / f"OPRA_{symbol}_{date}.csv"
    if not path.exists():
        print(f"  {symbol} {date}: no OPRA file yet ({path.name})")
        return None
    opra = load_opra(path)
    rows = recorded(date, symbol)
    spot = float(rows[0]["spot"])
    matched, gaps_s, unmatched = [], [], 0
    for r in rows:
        rec = opra.get(compact(r["option_symbol"]))
        when = parse_ts(r["quote_time"]) if r.get("quote_time") else None
        hit = nearest(rec, when) if rec and when else None
        if not hit:
            unmatched += 1
            continue
        gaps_s.append(abs((hit[0] - when).total_seconds()))
        matched.append((r, hit[1], hit[2]))

    def agree(sub):
        ratio, both0, free0, opra0, n = [], 0, 0, 0, 0
        for r, ob, oa in sub:
            k, t = float(r["strike"]), r["type"]
            if (t == "P") != (k < spot) or oa is None:
                continue
            n += 1
            fb, fa = modelfree._num(r["bid"]) or 0.0, modelfree._num(r["ask"])
            ob = ob or 0.0
            both0 += fb == 0 and ob == 0
            free0 += fb == 0 and ob > 0
            opra0 += fb > 0 and ob == 0
            if fa is not None and oa > ob:
                ratio.append(abs((fb + fa) / 2 - (ob + oa) / 2) / (oa - ob))
        return n, (st.median(ratio) if ratio else None), both0, free0, opra0

    band = [m for m in matched if m[0]["_file"] == "surface.csv"]
    wing = [m for m in matched if m[0]["_file"] == "surface_wide.csv"]
    print(f"  {symbol} {date}: {len(matched)} contracts matched within {MATCH_TOLERANCE_S}s "
          f"(median {st.median(gaps_s) if gaps_s else 0:.0f}s apart), {unmatched} unmatched")
    for label, sub in (("band +/-30%", band),
                       ("put wing", [m for m in wing if float(m[0]["strike"]) < spot]),
                       ("call wing", [m for m in wing if float(m[0]["strike"]) > spot])):
        n, med, b0, f0, o0 = agree(sub)
        print(f"    {label:<12} n={n:<4} mid gap {'n/a' if med is None else f'{med:.2f}'} of the OPRA "
              f"spread; zero bid on both {b0}, free only {f0}, OPRA only {o0}")

    # The lift from OPRA's own prices on the recorder's own strikes and legs.
    def as_rows(sub, use_opra):
        out = []
        for r, ob, oa in sub:
            if use_opra:
                if oa is None:
                    continue
                q = dict(r, bid=str(ob or 0.0), ask=str(oa), mid=str(((ob or 0.0) + oa) / 2))
            else:
                q = r
            out.append(q)
        return out
    r_ = modelfree.risk_free()
    lifts = {}
    for who, use in (("free", False), ("OPRA", True)):
        inner, outer = as_rows(band, use), as_rows(wing, use)
        vals = []
        for mode in (False, True, "skip"):
            a, b = modelfree.model_free_30d(inner, r_, mode), modelfree.model_free_30d(inner + outer, r_, mode)
            vals.append(b[0] - a[0] if a and b else None)
        lifts[who] = vals
        print(f"    lift, {who:<5} as registered {vals[0]:+.2f}   Cboe rule {vals[1]:+.2f}   skip {vals[2]:+.2f}"
              if None not in vals else f"    lift, {who}: too thin")
    return lifts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--date", help="YYYY-MM-DD")
    g.add_argument("--all", action="store_true", help="every (date, symbol) with wide data")
    ap.add_argument("--symbols", nargs="+", default=["USO", "TSLA"])
    ap.add_argument("--dry-run", action="store_true", help="show and price the requests; spend nothing")
    ap.add_argument("--compare", action="store_true", help="analyse files already on disk; no network")
    ap.add_argument("--definitions", action="store_true",
                    help="fetch OPRA's listing for the day and say whether unmatched contracts exist on it")
    ap.add_argument("--max-cost", type=float, default=DEFAULT_MAX_COST, help="per-request cap, USD")
    ap.add_argument("--refetch", action="store_true", help="buy a day again even if its file is on disk")
    a = ap.parse_args()

    pairs = ([(d, s) for d, s in wide_days() if s in a.symbols] if a.all
             else [(a.date, s) for s in a.symbols])
    print(f"OPRA reference ({DATASET}, {SCHEMA}) - {'compare' if a.compare else 'dry run' if a.dry_run else 'fetch'}\n")
    if a.definitions:
        key = api_key()
        for d, s in pairs:
            if not a.dry_run and (DATA_DIR / f"DEF_{s}_{d}.csv").exists():
                print(f"  {s} {d}: definitions already on disk")
            else:
                definitions(d, s, key, a.max_cost, a.dry_run)
            if not a.dry_run:
                check_listed(d, s)
    elif a.compare:
        for d, s in pairs:
            compare(d, s)
    else:
        key = api_key()
        for d, s in pairs:
            fetch(d, s, key, a.max_cost, a.dry_run)
    print(f"\n{ATTRIBUTION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
