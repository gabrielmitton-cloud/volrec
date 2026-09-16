"""volrec pre-flight pressure test. Read-only. Run before and after every run.

  python tools/pressure_test.py

Exits non-zero on any failure.

WHY THE ANCHOR IS THE BACKUP, NOT THE LIVE FILE
-----------------------------------------------
Until 8 Sep 2026 this test pinned data/iv_history.csv to a fixed md5. That
stopped working the moment the schema migrated and the recorder began appending
daily, because the live file now legitimately changes every trading day, and a
tripwire that fires on correct behaviour gets disabled by whoever is on call.

data/iv_history.pre-17col.csv is the one-time migration backup. It is finished:
nothing should ever write to it again. So it is pinned by md5, and the live
file is checked *against* it - the original 52 rows must still be there,
value-for-value. That catches the failure that actually matters (history being
rewritten) without firing on the one that does not (history growing).
"""
import csv, hashlib, importlib.util, re, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parent.parent
BACKUP_MD5 = "75035d11b530681571dbeb3294af5926"   # pre-17col backup. IMMUTABLE.
ORIGINAL_DAY, ORIGINAL_ROWS = "2026-09-04", 52

fails, warns = [], []
def ok(c, m):
    print(("  PASS  " if c else "  FAIL  ") + m)
    if not c: fails.append(m)
def warn(c, m):
    print(("  PASS  " if c else "  WARN  ") + m)
    if not c: warns.append(m)

live = R / "data/iv_history.csv"
back = R / "data/iv_history.pre-17col.csv"
raw = live.read_bytes()
rows = list(csv.DictReader(live.open(newline="")))
hdr = next(csv.reader(live.open(newline="")))
spec = importlib.util.spec_from_file_location("rec", R / "record.py")
rec = importlib.util.module_from_spec(spec); spec.loader.exec_module(rec)

print("=== A. PROVENANCE (the anchor) ===")
if back.exists():
    bh = next(csv.reader(back.open(newline="")))
    brows = list(csv.DictReader(back.open(newline="")))
    ok(hashlib.md5(back.read_bytes()).hexdigest() == BACKUP_MD5,
       "migration backup md5 unchanged - the immutable anchor")
    ok(len(bh) == 17 and len(brows) == ORIGINAL_ROWS,
       f"backup is the original 17-col, {ORIGINAL_ROWS}-row dataset")
    ok(rec.FIELDS[:17] == bh,
       "schema change is APPEND-ONLY (FIELDS[:17] == the original header, in order)")
    orig = [r for r in rows if r["date"] == ORIGINAL_DAY]
    ok(len(orig) == ORIGINAL_ROWS, f"{ORIGINAL_ROWS} rows still present for {ORIGINAL_DAY}")
    ok(all(all(o[k] == n[k] for k in o) for o, n in zip(brows, orig)),
       "every original value preserved in the live file - history not rewritten")
else:
    warn(False, "no pre-17col backup yet (expected only before the first migration)")
    ok(hashlib.md5(raw).hexdigest() == BACKUP_MD5, "pre-migration md5 unchanged")

print("\n=== B. LIVE DATASET INTEGRITY ===")
ok(hdr == rec.FIELDS, f"header matches FIELDS ({len(hdr)} columns)")
ok(all(len(r) == len(rec.FIELDS) for r in rows), "no ragged rows")
ok(len({(r["date"], r["symbol"]) for r in rows}) == len(rows), "no duplicate (date,symbol)")
ok(raw.count(b"\r\n") == raw.count(b"\n") == raw.count(b"\r"),
   "line endings uniformly CRLF (csv module default)")
ok(raw.endswith(b"\n"), "ends with newline, so append starts on a fresh line")
blob = subprocess.run(["git", "show", "HEAD:data/iv_history.csv"], cwd=R,
                      capture_output=True).stdout
ok(hashlib.md5(blob).hexdigest() == hashlib.md5(raw).hexdigest(),
   "committed blob byte-identical to worktree (no uncommitted drift)")
days = sorted({r["date"] for r in rows})
print(f"  INFO  {len(rows)} rows over {len(days)} trading days, {days[0]} to {days[-1]}")

print("\n=== C. VALUE SANITY (all rows) ===")
ok(all(float(r["bid"]) <= float(r["mid"]) <= float(r["ask"]) for r in rows), "bid <= mid <= ask")
ok(all(float(r["bid"]) > 0 for r in rows), "no one-sided quotes")
iv = [float(r["iv"]) for r in rows if r["iv"]]
ok(all(0.01 < v < 3.0 for v in iv), f"IV sane ({min(iv):.3f}-{max(iv):.3f})")
d = [int(r["dte"]) for r in rows]
ok(all(rec.DTE_WINDOW[0] <= x <= rec.DTE_WINDOW[1] for x in d), f"dte in window ({min(d)}-{max(d)})")
ok(all(float(r["delta"]) > 0 for r in rows), "all calls")
ok(all(r["iv"] for r in rows), "IV populated on every row")

print("\n=== D. PER-DAY COVERAGE ===")
for day in days:
    dr = [r for r in rows if r["date"] == day]
    far = sum(1 for r in dr if r.get("far_iv"))
    put = sum(1 for r in dr if r.get("put_iv"))
    qt = sorted({r["quote_time"][11:16] for r in dr if r.get("quote_time")})
    span = f"{qt[0]}-{qt[-1]}Z" if qt else "n/a (pre-schema)"
    print(f"  {day}  {len(dr):>4} rows | far {100*far/len(dr):>3.0f}% | "
          f"put {100*put/len(dr):>3.0f}% | quotes {span}")
recent = [r for r in rows if r["date"] == days[-1]]
if any(r.get("far_iv") for r in recent):
    frac = sum(1 for r in recent if r.get("far_iv")) / len(recent)
    warn(frac >= 0.90, f"far leg on >=90% of the latest day (got {100*frac:.0f}%)")

print("\n=== E. SNAPSHOT-TIME DRIFT (comparability) ===")
# The cron is fixed but GitHub delays scheduled runs. A drifting snapshot time
# is a comparability problem the DST note in HANDOFF section 6 already worries
# about at one hour; delays have been larger.
times = {}
for r in rows:
    if r.get("quote_time"):
        times.setdefault(r["date"], []).append(r["quote_time"][11:16])
if len(times) >= 2:
    mids = {d: sorted(v)[len(v) // 2] for d, v in times.items()}
    mins = {d: int(t[:2]) * 60 + int(t[3:]) for d, t in mids.items()}
    spread = max(mins.values()) - min(mins.values())
    for dd, t in sorted(mids.items()):
        print(f"  {dd}  median quote {t}Z")
    warn(spread <= 60, f"snapshot time spread across days is {spread} min "
                       f"(>60 breaks comparability; control for it or split the sample)")
elif times:
    d0, t0 = next(iter(sorted(times.items())))
    print(f"  only one day with quote_time so far ({d0}, median "
          f"{sorted(t0)[len(t0)//2]}Z) - need a second to measure drift")

print("\n=== F. record.py STATIC ===")
ok(len(set(rec.FIELDS)) == len(rec.FIELDS), "no duplicate column names in FIELDS")
syms = re.findall(r'["\']([A-Z.]+)["\']',
                  re.search(r"WATCHLIST\s*=\s*\[(.*?)\]", (R / "record.py").read_text(), re.S).group(1))
ok(len(syms) == 109 and len(set(syms)) == 109, f"{len(syms)} unique tickers")
ok({r["symbol"] for r in rows} <= set(syms), "no recorded ticker was dropped from WATCHLIST")

print("\n=== G. MIGRATION still works (synthetic 17-col fixture) ===")
# Must NOT use the live file: it is already migrated, so migrate_header() would
# correctly no-op and the test would prove nothing.
tmp = Path(tempfile.mkdtemp())
(tmp / "iv_history.csv").write_bytes(back.read_bytes() if back.exists() else raw)
saved, rec.OUT = rec.OUT, tmp / "iv_history.csv"
try:
    rec.migrate_header()
finally:
    rec.OUT = saved
mig = list(csv.DictReader((tmp / "iv_history.csv").open(newline="")))
bak2 = tmp / "iv_history.pre-17col.csv"
ok(next(csv.reader((tmp / "iv_history.csv").open(newline=""))) == rec.FIELDS, "17 -> 32 columns")
ok(bak2.exists(), "one-time backup created beside the file")
if bak2.exists():
    ob = list(csv.DictReader(bak2.open(newline="")))
    ok(all(all(o[k] == n[k] for k in o) for o, n in zip(ob, mig)), "every value preserved")
ok(hashlib.md5(live.read_bytes()).hexdigest() == hashlib.md5(raw).hexdigest(),
   "REAL dataset untouched by the dry run")

print("\n=== H. analyze.py <-> record.py SCHEMA CONSISTENCY ===")
MISSING = set()
class T(dict):
    def __missing__(self, k): MISSING.add(k); return ""
spec2 = importlib.util.spec_from_file_location("an", R / "analyze.py")
an = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(an)
for r in [T({**{f: "" for f in rec.FIELDS}, **x}) for x in rows[:5]]:
    for f in ("iv", "mid", "bid", "ask", "far_iv", "far_dte", "dte", "put_iv", "spot", "strike"):
        an.num(r[f])
    an.group_of(r["symbol"])
ok(not MISSING, f"analyze.py reads no column outside FIELDS {sorted(MISSING) or ''}")
import inspect
ok(inspect.signature(an.fetch_closes).parameters["feed"].default == "sip",
   "fetch_closes defaults to the sip feed (iex is shallow and ragged)")
ok("subscription does not permit" in (R / "analyze.py").read_text(),
   "the sip recent-data clamp is present (free plan 403s on end=today)")

print("\n=== H2. SURFACE FILE (strike surface, separate from the ATM panel) ===")
surf = R / "data/surface.csv"
import importlib.util as _iu
_ss = _iu.spec_from_file_location("surf", R / "surface.py")
_sm = _iu.module_from_spec(_ss); _ss.loader.exec_module(_sm)
if surf.exists():
    srows = list(csv.DictReader(surf.open(newline="")))
    shdr = next(csv.reader(surf.open(newline="")))
    ok(shdr == _sm.FIELDS, f"surface header matches its FIELDS ({len(shdr)} cols)")
    ok(all(len(r) == len(_sm.FIELDS) for r in srows), "no ragged surface rows")
    ok(len({(r["date"], r["option_symbol"]) for r in srows}) == len(srows),
       "no duplicate (date, option_symbol)")
    sdays = sorted({r["date"] for r in srows})
    print(f"  INFO  {len(srows)} rows over {len(sdays)} days, "
          f"{sdays[0]} to {sdays[-1]}")
    last = [r for r in srows if r["date"] == sdays[-1]]
    volpop = sum(1 for r in last if str(r.get("volume", "")).strip() not in ("", "0"))
    warn(volpop / max(len(last), 1) >= 0.80,
         f"volume populated on >=80% of the latest day ({100*volpop/max(len(last),1):.0f}%)")
    oipop = sum(1 for r in last if str(r.get("open_interest", "")).strip() != "")
    warn(oipop / max(len(last), 1) >= 0.70,
         f"open interest populated on >=70% of the latest day ({100*oipop/max(len(last),1):.0f}%)")
    oidates = {r.get("open_interest_date", "") for r in last if r.get("open_interest_date")}
    warn(all(d < sdays[-1] for d in oidates) if oidates else True,
         f"open interest is lagged, never same-day (dates {sorted(oidates)[:2]})")
    mny = [float(r["moneyness"]) for r in last if r.get("moneyness")]
    if mny:
        warn(max(mny) - min(mny) > 0.10,
             f"latest day spans a real moneyness range ({min(mny):.2f}-{max(mny):.2f})")
    mb = surf.stat().st_size / 1e6
    warn(mb < 200, f"surface file under 200 MB (currently {mb:.1f} MB)")
else:
    print("  INFO  no surface.csv yet (expected before the first surface run)")
# Check the CODE, not the docstring: surface.py documents that it stays away
# from the ATM panel, so a plain substring search matches its own prose.
import ast as _ast
_tree = _ast.parse((R / "surface.py").read_text())
_body = [n for n in _tree.body
         if not (isinstance(n, _ast.Expr) and isinstance(n.value, _ast.Constant)
                 and isinstance(n.value.value, str))]
_code = "\n".join(_ast.unparse(n) for n in _body)
ok("iv_history" not in _code,
   "surface.py code never touches the protected ATM panel (docstring aside)")
ok(_sm.OUT.name == "surface.csv", f"surface.py writes only to surface.csv (OUT={_sm.OUT.name})")

print("\n=== H3. DELTA-HEDGED P&L ESTIMATOR ===")
import subprocess as _sp
_t = _sp.run([sys.executable, str(R / "tools/test_hedged.py")],
             capture_output=True, text=True)
_nfail = 0
for _ln in _t.stdout.splitlines():
    if _ln.strip().startswith("FAIL"):
        _nfail += 1
ok(_t.returncode == 0 and _nfail == 0,
   f"hedged.py unit tests pass ({_nfail} failures)" if _nfail
   else "hedged.py unit tests pass (18 hand-computed cases)")
_hsrc = (R / "hedged.py").read_text()
ok("iv_history" not in _hsrc, "hedged.py never touches the ATM panel")
ok("cluster" in _hsrc.lower() and "demean" in _hsrc.lower(),
   "hedged.py warns that its pooled t is descriptive, not inferential")
_mf = (R / "modelfree.py").read_text()
ok("SystemExit" in _mf,
   "risk_free catches SystemExit (fred._key calls sys.exit, which bypasses "
   "except Exception)")

print("\n=== I. WORKFLOWS ===")
import yaml
recy = yaml.safe_load((R / ".github/workflows/record.yml").read_text())
ok(recy[True]["schedule"][0]["cron"] == "30 15 * * 1-5", "record cron 15:30 UTC weekdays")
ok(recy["permissions"]["contents"] == "write", "record has contents:write")
ok(any("git add data/" in str(s.get("run", "")) for s in recy["jobs"]["record"]["steps"]),
   "commits all of data/, so the backup is included")
frs = yaml.safe_load((R / ".github/workflows/freshness.yml").read_text())
ok(frs["permissions"]["contents"] == "read", "freshness is read-only")
ok(any("panel_health.py" in str(st.get("run", ""))
       for st in frs["jobs"]["freshness"]["steps"]),
   "freshness actually runs panel_health.py (not a silently emptied job)")
_crons = {c["cron"] for c in frs[True]["schedule"]}
ok(_crons == {"0 17 * * *", "0 21 * * *"},
   "freshness runs twice: 17:00 for the ATM panel, 21:00 once the surface lands")
ok(set(p.name for p in (R / ".github/workflows").glob("*.yml"))
   == {"record.yml", "freshness.yml", "surface.yml"},
   "no leftover TEMP workflows")
srf = yaml.safe_load((R / ".github/workflows/surface.yml").read_text())
ok(srf[True]["schedule"][0]["cron"] == "40 15 * * 1-5", "surface cron staggered 10 min after record")
ok(any("git add data/surface.csv" in str(st.get("run", ""))
       for st in srf["jobs"]["surface"]["steps"]),
   "surface workflow stages ONLY data/surface.csv")
ok(any("git diff --exit-code -- data/iv_history.csv" in str(st.get("run", ""))
       for st in srf["jobs"]["surface"]["steps"]),
   "surface workflow aborts if the ATM panel was touched")

print("\n=== I2. PANEL HEALTH (did the data arrive, not just: is the code right) ===")
phsrc = (R / "tools" / "panel_health.py").read_text()
ok("ast.literal_eval" in phsrc and '"SURFACE"' in phsrc,
   "reads the watchlist out of surface.py, so the two cannot drift apart")
ok("import requests" not in phsrc and "import surface" not in phsrc,
   "parses that list instead of importing it: no third-party dependency")
ok(not re.search(r"\.write_text\(|\bopen\([^)]*[\"']w[\"']|writer\(", phsrc),
   "panel_health is read-only: it never opens a file for writing")
ok("SURFACE_LANDED_HOUR_UTC" in phsrc and "SURFACE_START" in phsrc,
   "a missing surface.csv before the first run has landed is PEND, not FAIL")
ok("def now_utc" in phsrc and "date.today()" not in phsrc,
   "one clock seam in UTC: same verdict on a runner and on a laptop")
ok(int(re.search(r"SURFACE_LANDED_HOUR_UTC = (\d+)", phsrc).group(1))
   <= max(int(c["cron"].split()[1]) for c in frs[True]["schedule"]),
   "the checker starts judging no later than the last freshness cron of the day")
ok("sys.exit(main())" in phsrc and "return 1" in phsrc,
   "exits non-zero on failure, which is what actually sends the email")
ok(phsrc.count("warns.append") == 1 and "return 1" not in phsrc.split("def warn")[1].split("def ")[0],
   "warnings never change the exit code (an alert that cries wolf stops being read)")
_ph = subprocess.run([sys.executable, str(R / "tools" / "panel_health.py")],
                     capture_output=True, text=True)
ok(_ph.returncode == 0, f"panel_health passes against the live panels (exit {_ph.returncode})")

print("\n=== J. GUARD ORDER ===")
msrc = (R / "record.py").read_text()
ok(0 < msrc.find("is_trading_day(s, today)") < msrc.find("if rows:"),
   "holiday guard returns BEFORE any write")
ok("migrate_header()" in msrc[msrc.find("def append"):msrc.find("def probe")],
   "migrate_header runs inside append(), i.e. only when rows exist")
ok("already_recorded" in msrc, "idempotent: re-running the same day cannot duplicate")

print("\n=== K. PUBLIC SITE (index.html, tools/monitor.html, tools/volrec.js) ===")
site = (R / "tools/volrec.js").read_text()
mon = (R / "tools/monitor.html").read_text()
idx = (R / "index.html").read_text()
ok("h.forEach((k,i)=>o[k]=c[i])" in site, "parses by header NAME, not position")
ok("split(/\\r?\\n/)" in site, "handles CRLF")
ok('src="volrec.js"' in mon and 'src="tools/volrec.js"' in idx, "both pages load the shared runtime")
_js = lambda name: re.findall(r'"([A-Z.]+)"', re.search(re.escape(name) + r"\s*=\s*\[(.*?)\]", site, re.S).group(1))
ok(sorted(_js("V.WATCHLIST")) == sorted(syms) and len(_js("V.WATCHLIST")) == len(syms),
   "site watchlist matches record.py (a new ticker would otherwise show as absent)")
ok(_js("V.SURFACE") == re.findall(r'"([A-Z.]+)"', re.search(r"^SURFACE\s*=\s*\[(.*?)\]", (R / "surface.py").read_text(), re.S | re.M).group(1)),
   "site surface list matches surface.py")
_ph = (R / "tools/panel_health.py").read_text()
_start = re.search(r"SURFACE_START = date\((\d+), (\d+), (\d+)\)", _ph).groups()
ok(f'V.SURFACE_START = "{int(_start[0]):04d}-{int(_start[1]):02d}-{int(_start[2]):02d}"' in site
   and f"V.STALE_DAYS = {re.search(r'STALE_DAYS = (\d+)', _ph).group(1)};" in site
   and f"V.SURFACE_LANDED_HOUR_UTC = {re.search(r'SURFACE_LANDED_HOUR_UTC = (\d+)', _ph).group(1)};" in site,
   "site health rules use the same constants as panel_health.py")
ok(not re.search(r"bloomberg", site + mon + idx.replace("derived from Bloomberg", ""), re.I),
   "the site reads no Bloomberg-derived data")

print("\n=== L. BLOOMBERG COMPARISON (licensed data must never enter the repo) ===")
bc = (R / "tools/bloomberg_compare.py").read_text()
ok("Refusing to read exports from inside the repository" in bc,
   "refuses to read exports from inside the repo")
ok("Refusing to write the summary inside the repository" in bc,
   "refuses to write its summary inside the repo")
ok("MAX_QUOTE_GAP_MIN" in bc and "MIN_MATCHED" in bc and "MAX_MID_VS_SPREAD" in bc,
   "gates on snapshot gap, matched count and price agreement")
ok(not list(R.glob("**/*.xlsx")), "no spreadsheet is sitting in the repo")

print("\n" + "=" * 56)
print(f"RESULT: {len(fails)} fail, {len(warns)} warn")
for f in fails: print("  FAIL:", f)
for w in warns: print("  WARN:", w)
sys.exit(1 if fails else 0)
