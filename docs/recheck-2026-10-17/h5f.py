"""Independent H5f, from the registration text: exact fractions for a and b, the independent replica for c."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, sys, statistics as st
from fractions import Fraction as Fr
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, ROOT + "/tools")
import independent_replica as IR

ROOT = Path(ROOT)
OPRA = Path.home() / "Documents/volrec-licensed/opra"
DAYS = ["2026-09-18", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24"]
R = 0.0391


def ts(s):
    s = s.strip().rstrip("Z")
    if "+" in s[10:]:
        s = s[:s.rindex("+")]
    if "." in s:
        a, b = s.split(".")
        return datetime.strptime(a + "." + b[:6], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def px(v):
    try:
        f = Fr(v.strip())
    except (ValueError, AttributeError, ZeroDivisionError):
        return None
    return f if 0 <= f < 10 ** 7 else None


def opra(path):
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault("".join(r["symbol"].split()), []).append((ts(r["ts_recv"]), px(r["bid_px_00"]), px(r["ask_px_00"])))
    return out


ratios, two, b0, f0, o0, unmatched, infl = [], [], 0, 0, 0, 0, []
for d in DAYS:
    for sym in ("USO", "TSLA"):
        rows = [dict(r, _f=n) for n in ("surface.csv", "surface_wide.csv")
                for r in csv.DictReader((ROOT / "data" / n).open(newline="")) if r["date"] == d and r["symbol"] == sym]
        if not rows:
            continue
        book = opra(OPRA / f"OPRA_{sym}_{d}.csv")
        spot = Fr(rows[0]["spot"])
        matched, zero_day = [], 0
        for r in rows:
            recs = book.get("".join(r["option_symbol"].split()))
            when = ts(r["quote_time"]) if r.get("quote_time") else None
            hit = None
            if recs and when:
                g, hit = min(((abs((x[0] - when).total_seconds()), x) for x in recs), key=lambda y: y[0])
                hit = hit if g <= 120 else None
            if not hit:
                unmatched += r["_f"] == "surface_wide.csv"
                continue
            matched.append((r, hit[1], hit[2]))
            if r["_f"] != "surface_wide.csv":
                continue
            ob, oa = hit[1], hit[2]
            k = Fr(r["strike"])
            if (r["type"] == "P") != (k < spot) or oa is None:
                continue
            fb, fa = px(r["bid"]) or Fr(0), px(r["ask"])
            ob = ob or Fr(0)
            b0 += fb == 0 and ob == 0; f0 += fb == 0 and ob > 0; o0 += fb > 0 and ob == 0
            zero_day += fb == 0
            if fa is not None and oa > ob:
                x = abs((fb + fa) / 2 - (ob + oa) / 2) / (oa - ob)
                ratios.append(x)
                if fb > 0 and ob > 0:
                    two.append(x)
        if zero_day:
            # inflation = as-registered lift - Cboe-rule lift, on the MATCHED contracts, free vs OPRA prices
            def priced(sub, use_opra):
                out = []
                for r, ob, oa in sub:
                    if use_opra:
                        if oa is None:
                            continue
                        out.append(dict(r, bid=str(float(ob or 0)), ask=str(float(oa))))
                    else:
                        out.append(r)
                return out
            res = []
            for use in (False, True):
                band = priced([m for m in matched if m[0]["_f"] == "surface.csv"], use)
                wing = priced([m for m in matched if m[0]["_f"] == "surface_wide.csv"], use)
                v = IR.h3_day(band, wing, R)
                res.append((v["wide_reg"] - v["reg"]) - (v["wide_cboe"] - v["reg_cboe"]))
            infl.append((d, sym, res[0], res[1]))

ratios.sort()
n = len(ratios)
med = (ratios[n // 2 - 1] + ratios[n // 2]) / 2 if n % 2 == 0 else ratios[n // 2]
print(f"wing contracts with a spread: {n}; wide rows unmatched: {unmatched}")
print(f"H5f-a pooled median, EXACT: {med} = {float(med):.6f} -> {'HOLDS' if med <= Fr(1, 2) else 'FAILS'} (bar 1/2)")
print(f"      values exactly 1/2: {sum(1 for x in ratios if x == Fr(1, 2))}; below: {sum(1 for x in ratios if x < Fr(1, 2))}; above: {sum(1 for x in ratios if x > Fr(1, 2))}")
print(f"      middle two (positions {n//2} and {n//2+1}): {ratios[n//2-1]}, {ratios[n//2]}")
print(f"      both feeds bid: n={len(two)}, median {float(st.median(two)):.3f}")
print(f"H5f-b free no-bid -> OPRA no-bid {b0} of {b0 + f0}; OPRA-only no-bid {o0}")
for d, s, f, o in infl:
    print(f"      {d} {s}: inflation free {f:+.2f} OPRA {o:+.2f}")
pos = all(o > 0 for *_, o in infl)
i_ = st.median(abs(o - f) / abs(f) for *_, f, o in infl)
mf, mo = st.median(f for *_, f, _ in infl), st.median(o for *_, o in infl)
print(f"H5f-c positive every day {pos}; (i) {i_:.1%}; (ii) median OPRA {mo:+.2f} vs free {mf:+.2f} = {abs(mo - mf) / abs(mf):.1%}")
