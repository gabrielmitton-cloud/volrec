"""volrec pre-flight pressure test. Read-only. Run before Tue 8 Sep."""
import csv, hashlib, importlib.util, re, subprocess, sys
from pathlib import Path
P = Path(__file__).resolve()
R = P.parent.parent  # repo root
GOLDEN = '75035d11b530681571dbeb3294af5926'
fails, warns = [], []
def ok(c, m):
    print(("  PASS  " if c else "  FAIL  ") + m)
    if not c: fails.append(m)
def warn(c, m):
    print(("  PASS  " if c else "  WARN  ") + m)
    if not c: warns.append(m)

raw = (R/'data/iv_history.csv').read_bytes()
rows = list(csv.DictReader((R/'data/iv_history.csv').open(newline='')))
spec = importlib.util.spec_from_file_location('rec', R/'record.py')
rec = importlib.util.module_from_spec(spec); spec.loader.exec_module(rec)

print("=== A. DATASET INTEGRITY ===")
ok(hashlib.md5(raw).hexdigest() == GOLDEN, 'md5 is the protected value')
ok(raw.count(b'\r\n') == raw.count(b'\n') and raw.count(b'\r') == raw.count(b'\r\n'),
   'line endings uniformly CRLF (csv module default) - no mixed endings')
ok(raw.endswith(b'\n'), 'ends with newline, so append starts on a fresh line')
ok(len(rows) == 52 and all(len(r) == 17 for r in rows), '52 rows, none ragged')
ok(len({(r['date'],r['symbol']) for r in rows}) == len(rows), 'no duplicate (date,symbol)')
blob = subprocess.run(['git','show','HEAD:data/iv_history.csv'], cwd=R,
                      capture_output=True).stdout
ok(hashlib.md5(blob).hexdigest() == GOLDEN, 'committed blob byte-identical to worktree')

print("\n=== B. VALUE SANITY ===")
ok(all(float(r['bid']) <= float(r['mid']) <= float(r['ask']) for r in rows), 'bid <= mid <= ask')
ok(all(float(r['bid']) > 0 for r in rows), 'no one-sided quotes')
iv = [float(r['iv']) for r in rows]
ok(all(0.01 < v < 3.0 for v in iv), f'IV sane ({min(iv):.3f}-{max(iv):.3f})')
d = [int(r['dte']) for r in rows]
ok(all(rec.DTE_WINDOW[0] <= x <= rec.DTE_WINDOW[1] for x in d), f'dte in window ({min(d)}-{max(d)})')
ok(all(float(r['delta']) > 0 for r in rows), 'all calls')

print("\n=== C. record.py STATIC ===")
hdr = next(csv.reader((R/'data/iv_history.csv').open(newline='')))
ok(len(rec.FIELDS) == 32, 'FIELDS is 32 columns')
ok(len(set(rec.FIELDS)) == 32, 'no duplicate column names')
ok(rec.FIELDS[:17] == hdr, 'schema change is APPEND-ONLY (first 17 match, in order)')
syms = re.findall(r'["\']([A-Z.]+)["\']', re.search(r'WATCHLIST\s*=\s*\[(.*?)\]',
                  (R/'record.py').read_text(), re.S).group(1))
ok(len(syms) == 109 and len(set(syms)) == 109, '109 unique tickers')
ok({r['symbol'] for r in rows} <= set(syms), 'no recorded ticker was dropped')

print("\n=== D. MIGRATION DRY RUN (on a copy) ===")
import tempfile; tmp = Path(tempfile.mkdtemp()); tmp.mkdir(exist_ok=True)
(tmp/'iv_history.csv').write_bytes(raw)
for stale in tmp.glob('*.pre-*'): stale.unlink()
saved = rec.OUT; rec.OUT = tmp/'iv_history.csv'
try:
    rec.migrate_header()
finally:
    rec.OUT = saved
mig = list(csv.DictReader((tmp/'iv_history.csv').open(newline='')))
bak = list(csv.DictReader((tmp/'iv_history.pre-17col.csv').open(newline='')))
ok(next(csv.reader((tmp/'iv_history.csv').open(newline=''))) == rec.FIELDS, '17 -> 32 columns')
ok(len(mig) == 52, '52 rows survive')
ok(all(all(o[k] == n[k] for k in o) for o, n in zip(bak, mig)), 'every original value preserved')
ok(all(r['far_iv'] == '' and r['put_iv'] == '' for r in mig), 'new columns blank on old rows')
ok(hashlib.md5((R/'data/iv_history.csv').read_bytes()).hexdigest() == GOLDEN,
   'REAL dataset untouched by the dry run')

print("\n=== E. SCHEMA CONSISTENCY analyze.py <-> record.py ===")
MISSING = set()
class T(dict):
    def __missing__(self, k): MISSING.add(k); return ""
spec2 = importlib.util.spec_from_file_location('an', R/'analyze.py')
an = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(an)
for r in [T({**{f:'' for f in rec.FIELDS}, **x}) for x in rows]:
    for f in ('iv','mid','bid','ask','far_iv','far_dte','dte','put_iv','spot','strike'):
        an.num(r[f])
    an.group_of(r['symbol'])
ok(not MISSING, f'analyze.py reads no column outside FIELDS {sorted(MISSING) or ""}')

print("\n=== F. WORKFLOWS ===")
import yaml
recy = yaml.safe_load((R/'.github/workflows/record.yml').read_text())
ok(recy[True]['schedule'][0]['cron'] == '30 15 * * 1-5', 'record cron 15:30 UTC weekdays')
ok(recy['permissions']['contents'] == 'write', 'record has contents:write (needs to commit)')
job = recy['jobs']['record']
ok(any('git add data/' in str(s.get('run','')) for s in job['steps']),
   'commits the whole data/ dir, so the backup is included')
frs = yaml.safe_load((R/'.github/workflows/freshness.yml').read_text())
ok(frs['permissions']['contents'] == 'read', 'freshness is read-only')

print("\n=== G. GUARD ORDER (the Labor Day question) ===")
msrc = (R/'record.py').read_text()
gi, ci = msrc.find('is_trading_day(s, today)'), msrc.find('if rows:')
ok(0 < gi < ci, 'holiday guard returns BEFORE any write')
ok('migrate_header()' in msrc[msrc.find('def append'):msrc.find('def probe')],
   'migrate_header runs inside append(), i.e. only when rows exist')
ok('already_recorded' in msrc, 'idempotent: re-running the same day cannot duplicate')

print("\n=== H. PUBLIC MONITOR vs THE 32-COLUMN JUMP ===")
mon = (R/'tools/monitor.html').read_text()
ok('h.forEach((k,i)=>o[k]=c[i])' in mon, 'parses by header NAME, not position')
ok('split(/\\r?\\n/)' in mon, 'handles CRLF')
warn('c[i]' in mon and '"' not in mon.split('const c=l.split(",")')[1][:40],
     'naive split(",") - fine while no field contains a comma')

print("\n" + "="*54)
print(f"RESULT: {len(fails)} fail, {len(warns)} warn")
for f in fails: print("  FAIL:", f)
for w in warns: print("  WARN:", w)
sys.exit(1 if fails else 0)
