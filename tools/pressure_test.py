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
# The contract type comes from the OCC symbol, not from delta: on 21-22 Sep 2026 the
# vendor returned a quote with NO greeks for one HYG contract, delta was blank, and
# float('') crashed this whole test in section C - so nothing after it ran.
ok(all(rec.parse_occ(r["option_symbol"])[2] == "C" for r in rows), "all calls (by OCC symbol)")
ok(all(float(r["delta"]) > 0 for r in rows if r["delta"].strip()),
   "every delta the vendor sent is positive, as a call's must be")
# Missing greeks are a VENDOR gap, recorded honestly beside a good quote. Judged on the
# latest day only, like the drift check: one contract warns that day and ages out; a
# day with more than 5% missing is an outage and fails. History is reported, not judged.
_noiv = [r for r in rows if not r["iv"].strip()]
_last_noiv = [r for r in _noiv if r["date"] == days[-1]]
_last_n = sum(1 for r in rows if r["date"] == days[-1])
if _noiv:
    print(f"  INFO  {len(_noiv)} row(s) in history have a quote but no vendor IV/greeks: "
          + ", ".join(sorted({f"{r['symbol']} {r['date']}" for r in _noiv})))
ok(len(_last_noiv) <= 0.05 * _last_n,
   f"vendor IV present on >=95% of the latest day ({_last_n - len(_last_noiv)}/{_last_n})")
warn(not _last_noiv, f"vendor IV present on every row of the latest day "
                     f"({len(_last_noiv)} missing: {', '.join(r['symbol'] for r in _last_noiv)})")

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
# Judged over a ROLLING WINDOW, not all history. The cron moved once, on
# 16 Sep 2026, so the full-history spread contains a deliberate step change that
# would keep this warning lit forever - and a warning that is always on is one
# nobody reads. A rolling window lets a one-time schedule change age out while
# genuine ongoing drift still fires. Full history is printed as context.
DRIFT_WINDOW_DAYS = 10
if len(times) >= 2:
    mids = {d: sorted(v)[len(v) // 2] for d, v in times.items()}
    mins = {d: int(t[:2]) * 60 + int(t[3:]) for d, t in mids.items()}
    for dd, t in sorted(mids.items()):
        print(f"  {dd}  median quote {t}Z")
    recent = [mins[d] for d in sorted(mins)[-DRIFT_WINDOW_DAYS:]]
    spread = max(recent) - min(recent)
    full = max(mins.values()) - min(mins.values())
    if full != spread:
        print(f"  full history spans {full} min; judging the last "
              f"{len(recent)} day(s), which span {spread} min")
    warn(spread <= 60, f"snapshot time spread over the last {len(recent)} day(s) "
                       f"is {spread} min (>60 breaks comparability; control for "
                       f"it or split the sample)")
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
ok(_sm.OUT.name == "surface.csv", f"surface.py's registered output is surface.csv (OUT={_sm.OUT.name})")

# --- the wide band (added 17 Sep 2026). It must be ADDITIVE and SEPARATE. ------
ok(_sm.WIDE_OUT.name == "surface_wide.csv" and _sm.WIDE_OUT.parent == _sm.OUT.parent,
   "the wide band writes to its own file, beside the registered one")
# The registered path must not know the wide band exists. If rows_for, chain or
# append ever reference a WIDE_ constant, the registered grid has been changed.
_regsrc = "".join(_iu_src for _iu_src in [
    __import__("inspect").getsource(getattr(_sm, f))
    for f in ("rows_for", "chain", "append", "open_interest")])
ok("WIDE_" not in _regsrc and "wide" not in _regsrc.lower(),
   "the registered path (rows_for, chain, append, open_interest) never touches the wide band")
ok(abs(_sm.STRIKE_BAND - 0.30) < 1e-12 and _sm.STRIKE_COUNT == 40,
   "the registered grid is still +/-30% x 40, as frozen in H3")
_wt = _sm.wide_targets(0.60)
ok(_wt and all(abs(m - 1) > _sm.STRIKE_BAND for m in _wt),
   "every wide target lies strictly outside the registered band")
ok(_sm.wide_targets(_sm.STRIKE_BAND) == [],
   "a symbol that needs no widening gets no wide targets")
ok(_sm.wide_band(0.13, 30) == _sm.STRIKE_BAND,
   "a low-volatility name (13% IV) is left at the registered band")
ok(_sm.wide_band(5.0, 30) == _sm.WIDE_CAP, "the wide band never exceeds its cap")
ok(_sm.wide_band("", 30) == _sm.STRIKE_BAND and _sm.wide_band(None, 30) == _sm.STRIKE_BAND,
   "a missing IV falls back to the registered band rather than raising")
# The wide pass must never fail the run: a non-zero exit skips the commit step,
# which would lose surface.csv even though it had already been written.
import contextlib as _ctx2, io as _io2, datetime as _dtw
_orig = _sm.wide_rows_for
for _exc in (RuntimeError("api down"), SystemExit(1), KeyError("x")):
    def _boom(*a, _e=_exc, **k): raise _e
    _sm.wide_rows_for = _boom
    try:
        with _ctx2.redirect_stdout(_io2.StringIO()):
            _sm.record_wide(None, {"USO": 150.0},
                            [{"symbol": "USO", "expiration": "2026-10-16"}],
                            _dtw.date(2026, 9, 18))
        _raised = None
    except BaseException as _e2:
        _raised = _e2
    ok(_raised is None, f"the wide pass swallows {type(_exc).__name__} instead of failing the run")
_sm.wide_rows_for = _orig
# And the file-level separation, checked against the real data.
if surf.exists():
    _far = [r for r in csv.DictReader(surf.open(newline=""))
            if r.get("moneyness") and abs(float(r["moneyness"]) - 1) > 0.305]
    ok(not _far, f"surface.csv holds no row beyond the registered band "
                 f"({len(_far)} found)")
# --- which two expiries H3 integrates, and whether the wide pass covers them -------
# Added 18 Sep 2026. modelfree used to integrate the OUTERMOST expiries present, and
# carry-forward puts a third, shorter one in the file on ~3 days in 5: that broke
# Cboe's 23-day near-term floor and left --wide measuring a leg the wide pass never
# extended (a known 1.93-point lift read as 0.63). modelfree.pick_pair now copies
# rows_for's rule; these check the copy against the frozen original, on a calendar.
_ms = _iu.spec_from_file_location("mfree", R / "modelfree.py")
_mfm = _iu.module_from_spec(_ms)
_ms.loader.exec_module(_mfm)
if surf.exists():
    _two = {}
    for _r in srows:
        _two.setdefault((_r["date"], _r["symbol"]), set()).add(int(_r["dte"]))
    _two = {k: v for k, v in _two.items() if len(v) == 2}
    ok(all(_mfm.pick_pair(v) == sorted(v) for v in _two.values()),
       f"every recorded two-expiry day keeps both legs ({len(_two)} symbol-days), so no "
       f"registered H3 gap moved when the pair rule changed")
# A trading calendar to 31 Dec with Friday expiries (what all eight names list inside
# the 21-45 day window, as recorded on 17 Sep). A Friday holiday moves to Thursday.
from datetime import timedelta as _td
_hol = {date(2026, 11, 26), date(2026, 12, 25)}
_cal, _t = [], date(2026, 9, 18)
while _t <= date(2026, 12, 31):
    if _t.weekday() < 5 and _t not in _hol:
        _fri = [_t + _td(n) for n in range(_sm.DTE_WINDOW[0], _sm.DTE_WINDOW[1] + 1)
                if (_t + _td(n)).weekday() == 4]
        _cal.append((_t, [e - _td(1) if e in _hol else e for e in _fri]))
    _t += _td(1)
def _occ(e, kind, K):
    return f"USO{e:%y%m%d}{kind[0].upper()}{int(round(K * 1000)):08d}"
# Drive the FROZEN rows_for and the real wide_rows_for with fake chains, day by day,
# carrying forward exactly as the recorder does.
_saved = (_sm.chain, _sm.wide_chain, _sm.open_interest, _sm.previous_contracts, _sm.PACE)
_bad_pick, _bad_cboe, _bad_cover, _prev = [], [], [], set()
try:
    _sm.PACE = 0
    _sm.open_interest = lambda *a, **k: {}
    for _t, _listed in _cal:
        _sm.chain = (lambda s, sym, spot, day, kind, _L=_listed:
                     {_occ(e, kind, K): {"latestQuote": {"bp": 1.0, "ap": 1.1},
                                         "impliedVolatility": 0.51}
                      for e in _L for K in range(105, 196, 5)})
        _sm.previous_contracts = lambda sym, day: set()
        _picked = sorted({int(r["dte"]) for r in _sm.rows_for(None, "USO", 150.0, _t)})
        _sm.previous_contracts = lambda sym, day, _p=_prev: _p
        _rows = _sm.rows_for(None, "USO", 150.0, _t)
        _dtes = sorted({int(r["dte"]) for r in _rows})
        if _mfm.pick_pair([(e - _t).days for e in _listed]) != _picked:
            _bad_pick.append(_t)
        _pair = _mfm.pick_pair(_dtes)
        if _pair[0] <= 23 and any(23 < d <= 30 for d in _dtes):
            _bad_cboe.append(_t)
        for _r in _rows:
            _r["moneyness"], _r["iv"] = str(float(_r["strike"]) / 150.0), "0.51"
        _sm.wide_chain = (lambda s, sym, spot, day, kind, band, _L=_listed:
                          {_occ(e, kind, K): {} for e in _L for K in range(40, 250, 5)})
        _got, _ = _sm.wide_rows_for(None, "USO", 150.0, _t, _rows)
        _ext = {int(r["dte"]) for r in _got}
        if any(w > 0 and d not in _ext for d, w in _mfm.leg_weights(_pair).items()):
            _bad_cover.append(_t)
        _prev = {r["option_symbol"] for r in _rows}
finally:
    _sm.chain, _sm.wide_chain, _sm.open_interest, _sm.previous_contracts, _sm.PACE = _saved
ok(not _bad_pick, f"modelfree.pick_pair reproduces the frozen rows_for pick on all "
                  f"{len(_cal)} trading days to 31 Dec ({len(_bad_pick)} differ)")
ok(not _bad_cboe, f"H3 never integrates a near leg of 23 days or less while a 24-30 day "
                  f"expiry exists - Cboe's rule ({len(_bad_cboe)} of {len(_cal)} days break it)")
ok(not _bad_cover, f"the wide pass extends every leg the H3 estimate weights, carry-forward "
                   f"included ({len(_bad_cover)} of {len(_cal)} days uncovered)")
# Stronger than any calendar: every layout of 2-4 expiries the DTE window allows.
from itertools import combinations as _comb
_span = range(_sm.DTE_WINDOW[0], _sm.DTE_WINDOW[1] + 1)
_lay = [c for n in (2, 3, 4) for c in _comb(_span, n)]
_diff = [c for c in _lay if _sm.wide_expiries({f"e{x}": x for x in c})
         != {f"e{x}" for x in _mfm.pick_pair(c)}]
ok(not _diff, f"surface.wide_expiries and modelfree.pick_pair agree on all {len(_lay):,} "
              f"possible layouts of 2-4 expiries ({len(_diff)} differ)")

_wide = R / "data/surface_wide.csv"
if _wide.exists():
    _near = [r for r in csv.DictReader(_wide.open(newline=""))
             if r.get("moneyness") and abs(float(r["moneyness"]) - 1) <= _sm.STRIKE_BAND]
    ok(not _near, f"surface_wide.csv holds no row inside the registered band "
                  f"({len(_near)} found) - the two files never overlap")

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

print("\n=== H3b. CALIBRATION (every instrument against a known reference truth) ===")
# Each instrument is fed an input whose right answer is known in advance - parity,
# invertibility, Carr-Madan's sigma^2, a simulated known vol, a no-premium world -
# so a failure here means an instrument is wrong, never that the market moved.
_c = _sp.run([sys.executable, str(R / "tools/calibrate.py")],
             capture_output=True, text=True)
_cfail = [ln.strip()[6:] for ln in _c.stdout.splitlines() if ln.strip().startswith("FAIL")]
_cpass = sum(1 for ln in _c.stdout.splitlines() if ln.strip().startswith("PASS"))
ok(_c.returncode == 0 and not _cfail,
   f"all instruments calibrated ({_cpass} checks)" if not _cfail
   else f"UNCALIBRATED: {'; '.join(_cfail)}")
_hsrc = (R / "hedged.py").read_text()
ok("iv_history" not in _hsrc, "hedged.py never touches the ATM panel")
ok("cluster" in _hsrc.lower() and "demean" in _hsrc.lower(),
   "hedged.py warns that its pooled t is descriptive, not inferential")
_mf = (R / "modelfree.py").read_text()
ok("SystemExit" in _mf,
   "risk_free catches SystemExit (fred._key calls sys.exit, which bypasses "
   "except Exception)")

print("\n=== H4. MULTIPLE TESTING (H1 reports a COUNT of significant pairs) ===")
import analyze as _az
_bh_all, _bh_adj = _az.benjamini_hochberg({f"n{i}": 1.0 for i in range(10)})
ok(len(_bh_all) == 0, "eleven true nulls reject nothing")
_bh_all, _ = _az.benjamini_hochberg({f"z{i}": 0.0 for i in range(10)})
ok(len(_bh_all) == 10, "ten certain rejections all survive")
# Benjamini & Hochberg (1995) worked example: m=4, q=0.05, all four reject.
_bh_all, _ = _az.benjamini_hochberg({"a": 0.005, "b": 0.01, "c": 0.03, "d": 0.04})
ok(_bh_all == {"a", "b", "c", "d"}, "BH step-up accepts up to the largest i "
   "with p(i) <= i*q/m, not the first failure")
# A single p just over the last threshold must not drag the rest down with it.
_bh_all, _ = _az.benjamini_hochberg({"a": 0.001, "b": 0.9})
ok(_bh_all == {"a"}, "one hopeless test does not cost the good one")
# Adjusted p-values must be monotone in the raw ordering.
_, _adj = _az.benjamini_hochberg({"a": 0.001, "b": 0.02, "c": 0.03, "d": 0.5})
_seq = [_adj[k] for k in ("a", "b", "c", "d")]
ok(_seq == sorted(_seq), "adjusted p-values are monotone (running-min applied)")
ok(all(0.0 <= v <= 1.0 for v in _adj.values()), "adjusted p-values stay in [0,1]")
# H1's own eleven, from the recorded result table. The conclusion must not move.
_h1 = {"VIX/SPY": 0.0, "VXN/QQQ": 0.0003, "RVX/IWM": 0.0, "VXD/DIA": 0.0,
       "OVX/USO": 0.0, "GVZ/GLD": 0.0001, "VXEEM/EEM": 0.0, "VXSLV/SLV": 0.0159,
       "EVZ/FXE": 0.0, "VXXLE/XLE": 0.1904, "VXGDX/GDX": 0.9347}
_bh_all, _ = _az.benjamini_hochberg(_h1)
ok(len(_bh_all) == 9, "H1's 9 of 11 survives FDR control at q=0.05")
ok(any("benjamini_hochberg" in (R / "samples/long/build_sample_a.py").read_text()
       for _ in (0,)), "build_sample_a.py actually reports the correction")

print("\n=== I. WORKFLOWS ===")
import yaml
import datetime as _dt

# The crons are checked by their REASONING, not their literal text, because the
# literal text has already been wrong once. Measured over six days at the old
# 15:30 UTC slot, GitHub delayed the scheduled run by 3h06m to 4h24m, so the
# snapshot landed 18:36-19:54 and on 14 Sep arrived six minutes before the
# 20:00 close. A snapshot that lands after the close is not a late snapshot, it
# is a different measurement: closing quotes, on a day the file still labels as
# a mid-session observation. So the cron must clear the close even at the worst
# delay ever seen, with margin, and must avoid the quarter hours where the
# scheduling queue is deepest.
WORST_DELAY_MIN = 264          # 4h24m, observed 14 Sep 2026 at the OLD 15:30 cron
DELAY_MARGIN_MIN = 30          # room for a delay worse than any yet seen
# 23 Sep 2026: the hardcoded 264 went stale. On Mon 21 Sep record.yml fired 4h57m
# after its 14:47 cron and the snapshot landed 16 minutes before the close, and
# nothing noticed, because this file trusted a constant. The worst delay is now
# MEASURED from the panels' own quote times since the cron moved (16 Sep), and the
# constant is only a floor.
CRON_SINCE = "2026-09-16"


def _measured_delay(path, cron_min):
    by = {}
    for _r in csv.DictReader(path.open(newline="")):
        _t = _r.get("quote_time", "")
        if _r["date"] >= CRON_SINCE and len(_t) >= 16:
            by.setdefault(_r["date"], []).append(int(_t[11:13]) * 60 + int(_t[14:16]))
    lands = {d: sorted(v)[len(v) // 2] for d, v in by.items()}
    return max(((m - cron_min, d) for d, m in lands.items()), default=(0, None))
# Cron is UTC; the US session is not. Under DST the market runs 13:30-20:00 UTC,
# and from the first Sunday in November it runs 14:30-21:00. A cron picked
# against the summer session alone fires BEFORE the winter open, so both panels
# must clear the LATER open and the EARLIER close. That leaves a window of
# 14:30 to 15:06 UTC, and it is narrow because the worst delay is 4h24m.
US_OPEN_UTC_MIN = 14 * 60 + 30     # the later of the two opens (standard time)
US_CLOSE_UTC_MIN = 20 * 60         # the earlier of the two closes (DST)


def cron_minutes(expr):
    """'7 14 * * 1-5' -> (847, '1-5'): minutes past midnight UTC, and the days."""
    f = expr.split()
    return int(f[1]) * 60 + int(f[0]), f[4]


recy = yaml.safe_load((R / ".github/workflows/record.yml").read_text())
_rec_min, _rec_days = cron_minutes(recy[True]["schedule"][0]["cron"])
ok(_rec_days == "1-5", "record runs weekdays only")
ok(_rec_min >= US_OPEN_UTC_MIN,
   f"record starts after the LATER of the two US opens, so it survives the "
   f"November DST shift ({_rec_min//60:02d}:{_rec_min%60:02d} UTC)")
_meas, _meas_day = _measured_delay(live, _rec_min)
WORST_DELAY_MIN = max(WORST_DELAY_MIN, _meas)
_land = _rec_min + WORST_DELAY_MIN
print(f"  INFO  worst record delay since {CRON_SINCE}: {_meas // 60}h{_meas % 60:02d}m "
      f"({_meas_day}); judged on {WORST_DELAY_MIN // 60}h{WORST_DELAY_MIN % 60:02d}m")
ok(_land <= US_CLOSE_UTC_MIN,
   f"record's worst delay seen still lands before the earlier close "
   f"(lands {_land // 60:02d}:{_land % 60:02d}, close 20:00 UTC)")
warn(_land + DELAY_MARGIN_MIN <= US_CLOSE_UTC_MIN,
     f"record keeps {DELAY_MARGIN_MIN} min of margin at the worst delay seen "
     f"({US_CLOSE_UTC_MIN - _land} min left) - see HANDOFF 17, 23 Sep, on the cron")
ok(_rec_min % 15 != 0,
   "record cron avoids the quarter hours, where GitHub's queue is deepest")
ok(recy["permissions"]["contents"] == "write", "record has contents:write")
ok(any("git add data/" in str(s.get("run", "")) for s in recy["jobs"]["record"]["steps"]),
   "commits all of data/, so the backup is included")
frs = yaml.safe_load((R / ".github/workflows/freshness.yml").read_text())
ok(frs["permissions"]["contents"] == "read", "freshness is read-only")
ok(any("panel_health.py" in str(st.get("run", ""))
       for st in frs["jobs"]["freshness"]["steps"]),
   "freshness actually runs panel_health.py (not a silently emptied job)")
_fresh = sorted(cron_minutes(c["cron"])[0] for c in frs[True]["schedule"])
ok(len(_fresh) == 2, "freshness runs twice a day")
ok(_fresh[0] >= _rec_min + WORST_DELAY_MIN,
   "the early freshness slot runs after the recorders typically land")
ok(_fresh[-1] >= _rec_min + WORST_DELAY_MIN + DELAY_MARGIN_MIN,
   "the late freshness slot runs after even an unusually delayed landing")
ok(set(p.name for p in (R / ".github/workflows").glob("*.yml"))
   == {"record.yml", "freshness.yml", "surface.yml"},
   "no leftover TEMP workflows")
srf = yaml.safe_load((R / ".github/workflows/surface.yml").read_text())
_srf_min, _srf_days = cron_minutes(srf[True]["schedule"][0]["cron"])
ok(_srf_days == _rec_days and _srf_min - _rec_min == 10,
   f"surface cron staggered exactly 10 min after record "
   f"({_srf_min//60:02d}:{_srf_min%60:02d} vs "
   f"{_rec_min//60:02d}:{_rec_min%60:02d} UTC)")
ok(_srf_min % 15 != 0,
   "surface cron avoids the quarter hours too")
_smeas, _ = _measured_delay(surf, _srf_min) if surf.exists() else (0, None)
_sland = _srf_min + max(_smeas, WORST_DELAY_MIN)
ok(_sland <= US_CLOSE_UTC_MIN,
   f"surface's worst delay seen still lands before the earlier close "
   f"(lands {_sland // 60:02d}:{_sland % 60:02d})")
_srf_run = " ".join(str(st.get("run", "")) for st in srf["jobs"]["surface"]["steps"])
ok("git add data/surface.csv" in _srf_run,
   "surface workflow stages the registered surface file")
ok("if [ -f data/surface_wide.csv ]; then git add data/surface_wide.csv; fi" in _srf_run,
   "surface workflow stages the wide file ONLY if it exists (a bare git add on a "
   "missing path exits 128 and would lose surface.csv)")
ok("git add data/" not in _srf_run.replace("git add data/surface.csv", "")
                                  .replace("git add data/surface_wide.csv", ""),
   "surface workflow stages nothing else under data/ - never the ATM panel")
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
# The DST shift is the kind of thing that is correct for half the year and then
# silently is not, so the session bounds are checked on both sides of it.
_phm = _iu.module_from_spec(_iu.spec_from_file_location("_ph_mod", R / "tools/panel_health.py"))
try:
    _iu.spec_from_file_location("_ph_mod", R / "tools/panel_health.py").loader.exec_module(_phm)
    ok(_phm.session_bounds_utc(_dt.date(2026, 10, 30)) == (13 * 60 + 30, 20 * 60),
       "session bounds under DST are 13:30-20:00 UTC")
    ok(_phm.session_bounds_utc(_dt.date(2026, 11, 2)) == (14 * 60 + 30, 21 * 60),
       "session bounds after the November shift are 14:30-21:00 UTC")
    # A missed trading day used to read as HEALTHY: on 16 Sep 2026 no recorder
    # ran and the only signal was that someone looked. It must FAIL, because
    # GitHub emails on failures and nothing else.
    # Written date-independently on purpose: the first version asserted the result
    # was exactly [16 Sep], which was true only on 16 Sep and failed the next day.
    _m = _phm.missed_trading_days(_dt.date(2026, 9, 15))
    ok(_dt.date(2026, 9, 16) in _m,
       "a skipped weekday is detected as a missed trading day")
    ok(not any(d.weekday() >= 5 for d in _m),
       "weekends are never counted as missed trading days")
    ok(_phm.missed_trading_days(_dt.date(2026, 11, 25)) == [] or
       _dt.date(2026, 11, 26) not in _phm.missed_trading_days(_dt.date(2026, 11, 25)),
       "Thanksgiving is not counted as a missed trading day")
    ok(_dt.date(2026, 10, 12) not in _phm.US_MARKET_HOLIDAYS,
       "Columbus Day is NOT a holiday: the stock market trades")
    # One holiday list, not two.
    _mgsrc = (R / "tools/model_gap.py").read_text()
    ok("from panel_health import US_MARKET_HOLIDAYS" in _mgsrc
       and "date(2026, 11, 26)" not in _mgsrc,
       "model_gap imports the holiday list instead of keeping a second copy")

    _fl = len(_phm.fails)
    # Deliberately provoking a failure, so its own output is swallowed: a FAIL
    # line printed here would read as a real one.
    import contextlib as _ctx, io as _io
    with _ctx.redirect_stdout(_io.StringIO()):
        _phm.check_landing([{"date": "2026-11-05",
                             "quote_time": "2026-11-05T21:30:00.000000Z"}] * 20,
                           [_dt.date(2026, 11, 5)])
    ok(len(_phm.fails) > _fl,
       "a snapshot after the close FAILS, which is what sends the email")
    _phm.fails.clear(); _phm.warns.clear()
except Exception as _e:
    ok(False, f"panel_health session checks are importable ({_e})")

ok("SURFACE_LANDED_HOUR_UTC" in phsrc and "SURFACE_START" in phsrc,
   "a missing surface.csv before the first run has landed is PEND, not FAIL")
ok("def now_utc" in phsrc and "date.today()" not in phsrc,
   "one clock seam in UTC: same verdict on a runner and on a laptop")
ok(int(re.search(r"SURFACE_LANDED_HOUR_UTC = (\d+)", phsrc).group(1)) * 60
   <= _fresh[-1],
   "the checker starts judging no later than the last freshness cron of the day")
ok("sys.exit(main())" in phsrc and "return 1" in phsrc,
   "exits non-zero on failure, which is what actually sends the email")
ok(phsrc.count("warns.append") == 1 and "return 1" not in phsrc.split("def warn")[1].split("def ")[0],
   "warnings never change the exit code (an alert that cries wolf stops being read)")
_ph = subprocess.run([sys.executable, str(R / "tools" / "panel_health.py")],
                     capture_output=True, text=True)
# This one is about the DATA, not the code. Everything above checks that
# panel_health is written correctly; this checks what it currently says. A
# failure here is a real gap in the panels - a missed trading day, a snapshot
# outside the session - and is fixed by collecting data, never by editing a
# test. The reason is quoted so it cannot be mistaken for a code regression.
_ph_reasons = [ln.strip()[6:].split(".")[0]
               for ln in (_ph.stdout or "").splitlines() if ln.strip().startswith("FAIL")]
ok(_ph.returncode == 0,
   "panel_health passes against the live panels"
   + (f" -- DATA problem, not code: {'; '.join(_ph_reasons)[:160]}"
      if _ph.returncode else ""))

ok("ACCEPTED_GAPS" in phsrc and "report_missed" in phsrc,
   "a lost trading day can be accepted, so the daily alarm does not cry wolf forever")
_acc = re.findall(r"date\((\d{4}), (\d+), (\d+)\): \(", phsrc)
ok(len(_acc) <= 5, f"accepted gaps stay few ({len(_acc)}); this is not a dumping ground")
ok(all(len(m) > 80 for m in re.findall(r"date\(\d{4}, \d+, \d+\): \((.*?)\),\n", phsrc, re.S)),
   "every accepted gap records why it was accepted")

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
# The real invariant is about CODE, not words: the site must never LOAD Bloomberg
# data. The first version of this check failed on any occurrence of the word, which
# would also have failed the page for saying, correctly, that Bloomberg is NOT used.
# Disclosure is the opposite of a violation, so only executable code is inspected.
def _scripts(html):
    return " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I))
_code = site + _scripts(idx) + _scripts(mon)
ok(not re.search(r"bloomberg|omon|\bIVM\b|\.xlsx|surface_wide", _code, re.I),
   "the site's code loads no Bloomberg data (and not the unregistered wide file)")
_fetches = set(re.findall(r"data/[A-Za-z0-9_.-]+\.(?:csv|json)", _code))
ok(_fetches <= {"data/iv_history.csv", "data/surface.csv"},
   f"the site fetches only the two registered panels ({sorted(_fetches)})")
ok("Not used on this page" in idx and "Source: Bloomberg Finance L.P." in idx,
   "the site discloses that it uses no Bloomberg data, with the attribution for "
   "where it does appear")
ok("DGS1MO" in idx and "VIXCLS" in idx and "retrieved from FRED" in idx,
   "the site cites both FRED series in FRED's own form")

# The site's countdown runs off its own copy of the cron. A stale copy is a
# public clock that is quietly wrong, which is worse than no clock, and moving
# the workflows on 16 Sep did exactly that until this caught it.
_js = (R / "tools/volrec.js").read_text()
for _name, _wf, _job in (("RECORD_CRON", "record.yml", "record"),
                         ("SURFACE_CRON", "surface.yml", "surface")):
    _m = re.search(rf"V\.{_name} = \[(\d+), (\d+)\]", _js)
    _cr = yaml.safe_load((R / f".github/workflows/{_wf}").read_text())
    _h, _mi = cron_minutes(_cr[True]["schedule"][0]["cron"])[0] // 60, \
              cron_minutes(_cr[True]["schedule"][0]["cron"])[0] % 60
    ok(_m is not None and (int(_m.group(1)), int(_m.group(2))) == (_h, _mi),
       f"site's {_name} matches {_wf} ({_h:02d}:{_mi:02d} UTC)")
ok("15:40 UTC" not in (R / "tools/monitor.html").read_text()
   and "15:30 UTC" not in (R / "tools/monitor.html").read_text(),
   "monitor.html does not hard-code a cron time beside the constant")

print("\n=== L. BLOOMBERG COMPARISON (licensed data must never enter the repo) ===")
bc = (R / "tools/bloomberg_compare.py").read_text()
ok("Refusing to read exports from inside the repository" in bc,
   "refuses to read exports from inside the repo")
ok("Refusing to write the summary inside the repository" in bc,
   "refuses to write its summary inside the repo")
ok("MAX_QUOTE_GAP_MIN" in bc and "MIN_MATCHED" in bc and "MAX_MID_VS_SPREAD" in bc,
   "gates on snapshot gap, matched count and price agreement")
# OMON has exported two column orders. The 18 Sep 2026 export put Ticker before
# Strike and every parser silently read zero quotes from it. Both must parse alike.
_bcs = _iu.spec_from_file_location("bcmp", R / "tools/bloomberg_compare.py")
_bcm = _iu.module_from_spec(_bcs); _bcs.loader.exec_module(_bcm)
_old = ["116", "USO 10/16/26 C116", "39.65", "42.2", "41.08", "0", "3",
        "116", "USO 10/16/26 P116", "0.31", "0.59", "0.38", "60.96", "17"]
_new = ["USO 10/16/26 C116", "116", "39.65", "42.2", "41.08", "0", "3",
        "USO 10/16/26 P116", "116", "0.31", "0.59", "0.38", "60.96", "17"]
_hdr = ["Ticker", "Strike", "Bid", "Ask", "Last", "IVM", "Volm"] * 2
_blk = ["16-Oct-26 (28d); CSize 100; IBrw 1.51; R 4.31; IFwd 154.52", "", "", "", "", "", ""]
ok(_bcm.strike_cells(_old) == _bcm.strike_cells(_new) and len(_bcm.strike_cells(_new)) == 2
   and not _bcm.strike_cells(_hdr) and not _bcm.strike_cells(_blk),
   "OMON exports parse identically whether Strike or Ticker comes first, and headers parse to nothing")
for _tool in ("model_gap", "iv_convention"):
    _src = (R / f"tools/{_tool}.py").read_text()
    ok("strike_cells" in _src and 're.match(r"^\\d+(\\.\\d+)?$", first)' not in _src,
       f"tools/{_tool}.py uses the shared layout-aware parser, not its own first-cell test")
# Skip vendored trees. The analysis venv holds thousands of third-party files and
# any one of them could ship a test spreadsheet, which would fail this check for a
# reason that has nothing to do with Bloomberg data.
_VENDORED = (".venv", "venv", "node_modules", "__pycache__", ".git")
# Attribution, as a checked invariant. Confirmed 17 Sep 2026 by the librarian who
# administers the subscription: derived Bloomberg figures may be published with
# "Source: Bloomberg Finance L.P.", raw data may not enter an open repository.
# Any Markdown section that states a measured Bloomberg-derived number must carry
# that line, so a future edit cannot publish one uncited.
_BBG = re.compile(r"\bIVM\b|OMON|Bloomberg'?s? (?:own |printed )?(?:IVM|forward|mid|quote|"
                  r"prices?|bid|ask|export)|divisor|bloomberg_compare|model_gap|iv_convention", re.I)
_FIG = re.compile(r"[+-]\d+\.\d{2}\b|\bt\s*=\s*[+-]?\d|\b\d{3}\.\d\b|R\^2|R-squared")
_uncited = []
for _doc in ["HANDOFF.md", "BLOOMBERG-MONDAY.md", "README.md"] + \
            [q.relative_to(R).as_posix() for q in (R / "hypotheses").glob("*.md")]:
    _t = (R / _doc).read_text() if (R / _doc).exists() else ""
    _head = "(preamble)"
    for _chunk in re.split(r"(?m)^(#{2,4} .*)$", _t):
        if re.match(r"#{2,4} ", _chunk):
            _head = _chunk.strip()
            continue
        if _BBG.search(_chunk) and _FIG.search(_chunk) and \
                "Source: Bloomberg Finance L.P." not in _chunk:
            _uncited.append(f"{_doc} :: {_head[:50]}")
ok(not _uncited, "every section publishing a Bloomberg-derived figure carries the attribution"
   + (f" -- MISSING in {'; '.join(_uncited[:3])}" if _uncited else ""))
for _tool in ("bloomberg_compare", "model_gap", "iv_convention"):
    _src = (R / f"tools/{_tool}.py").read_text()
    ok("ATTRIBUTION" in _src,
       f"tools/{_tool}.py prints the shared attribution line on every run")

_sheets = [q for pat in ("**/*.xlsx", "**/*.xls", "**/*.xlsm")
           for q in R.glob(pat)
           if not any(part in _VENDORED for part in q.relative_to(R).parts)]
ok(not _sheets, "no spreadsheet is sitting in the repo"
   + (f" (found {', '.join(q.relative_to(R).as_posix() for q in _sheets[:4])})"
      if _sheets else ""))
# Defence in depth. On 16 Sep 2026 the whole export folder was moved into the
# repo root; this check caught it, but only because someone ran the test. A
# .gitignore entry catches it without anyone running anything, so the entry
# itself is now a checked invariant rather than a good intention.
_gi = (R / ".gitignore").read_text()
ok("*.xlsx" in _gi, ".gitignore blocks spreadsheets even if one lands here")
ok("volrec-bloomberg/" in _gi,
   ".gitignore blocks the export folder by name as well as by extension")

print("\n=== M. REGISTERED CONSTANTS, ZERO-BID SEMANTICS, OPERATIONS TOOLS ===")
# A pre-registered bar that can be edited without anything noticing is not a bar.
ok(_mfm.PREDICTED_LIFT == {"USO": (1.4, 3.2)} and _mfm.NULL_LIFT_MAX == 0.3
   and _mfm.NULL_CONTROLS == ("GLD", "AAPL") and _mfm.FIRST_READING_DAYS == 3,
   "H3's wide-prediction bar, controls and first-reading rule are as registered 17-18 Sep")
ok((_mfm.H5E_SYMBOL, _mfm.H5E_START, _mfm.H5E_MAX_ABS_GAP, _mfm.H5E_MIN_DAYS)
   == ("USO", "2026-09-23", 0.5, 10), "H5e's symbol, start, bar and minimum are as registered 23 Sep")
# The zero-bid walk, against a chain whose right answer is known by construction:
# K0 = 100, OTM puts walking down carry bids ok, 0, ok, 0, 0, ok; every call is quoted.
# As registered all 6 puts count; Cboe keeps 95 and 85 and stops at the 80/75 pair;
# skip drops only the three zeros. Strikes used: 13, 9 and 10.
_zb_put = {95: 1, 90: 0, 85: 1, 80: 0, 75: 0, 70: 1}
_zrows = []
for _k in range(70, 135, 5):
    for _t in ("C", "P"):
        _px = max(0.05, (_k - 100 if _t == "P" else 100 - _k)) + 1.0
        _bid = 0.0 if (_t == "P" and _zb_put.get(_k) == 0) else _px * 0.9
        _zrows.append({"dte": "30", "strike": str(_k), "type": _t,
                       "mid": str(_px if _bid else _px / 2), "bid": str(_bid)})
# Parity must put the forward at 100: equal call and put mids there.
_n = {m: _mfm.variance_one_expiry(_zrows, 0.0, m)[2] for m in (False, True, "skip")}
ok(_n == {False: 13, True: 9, "skip": 10},
   f"zero-bid walk: as registered / Cboe / skip use 13 / 9 / 10 strikes (got "
   f"{_n[False]} / {_n[True]} / {_n['skip']})")
# bloomberg_prep must reproduce the two sessions that were worked out by hand.
_bps = _iu.spec_from_file_location("bprep", R / "tools/bloomberg_prep.py")
_bpm = _iu.module_from_spec(_bps); _bps.loader.exec_module(_bpm)
ok(_bpm.DTE_WINDOW == _sm.DTE_WINDOW and _bpm.WIDE_CAP == _sm.WIDE_CAP,
   "bloomberg_prep's DTE window and wide cap are surface.py's")
def _prep_pair(d):
    _l = _bpm.listed_expiries(d)
    _p = _mfm.pick_pair([(e - d).days for e in _l])
    return [_bpm.bbg_label(e) for e in _l if (e - d).days in _p]
ok(_prep_pair(date(2026, 9, 18)) == ["16-Oct-26", "23-Oct-26"]
   and _prep_pair(date(2026, 9, 22)) == ["16-Oct-26", "23-Oct-26"]
   and _prep_pair(date(2026, 9, 23)) == ["23-Oct-26", "30-Oct-26"],
   "bloomberg_prep names the recorder's expiries for 18, 22 and 23 Sep")
_daily = (R / "tools/daily.py").read_text()
ok(all(s in _daily for s in ("panel_health.py", "pressure_test.py", '"--wide"', "Traceback")),
   "daily.py runs panel health, the pressure test and the H3/H5e reading, and reports crashes")

print("\n" + "=" * 56)
print(f"RESULT: {len(fails)} fail, {len(warns)} warn")
for f in fails: print("  FAIL:", f)
for w in warns: print("  WARN:", w)
sys.exit(1 if fails else 0)
