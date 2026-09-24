"""H5f, read exactly as registered in hypotheses/2026-09-19-h5-wing-quote-quality.md.
Written 23 Sep 2026, BEFORE days 4 and 5 existed. Aggregates only. Run from the repo root:
    FRED_KEY=use-cache <framework python> ~/Documents/volrec-databento/verdict/h5f_pooled.py
Matching and the contract rule are opra_reference.compare()'s own, unchanged:
each recorded contract matched to the OPRA record nearest its quote time within 120 s
(unmatched excluded and counted); wing = surface_wide.csv rows, out of the money, an
OPRA ask present; a missing bid read as zero.
  H5f-a  pooled median |free mid - OPRA mid| / OPRA spread <= 0.5
  H5f-b  free no-bid -> OPRA no-bid on >= 80% of matched wing contracts
  H5f-c  on underlying-days whose wings carry free-feed zero bids: OPRA inflation
         (as registered minus Cboe rule) positive on every such day, and at the median
         across those days within 25% of the free feed's. Printed two ways, because the
         registered sentence can be read as (i) the median of per-day relative gaps or
         (ii) the median OPRA inflation against the median free inflation.
Minimum: five days with OPRA data."""
import io, os, sys, statistics as st, contextlib
from pathlib import Path
REPO = Path.cwd()
sys.path[:0] = [str(REPO), str(REPO / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")
import opra_reference as ore
import modelfree

days, ratios, two_sided = set(), [], []
both0 = free0 = opra0 = unmatched_total = 0
infl = []                                   # (date, symbol, free, opra) on zero-bid wing days
for date, sym in ore.wide_days():
    if sym not in ("USO", "TSLA") or not (ore.DATA_DIR / f"OPRA_{sym}_{date}.csv").exists():
        continue
    days.add(date)
    opra = ore.load_opra(ore.DATA_DIR / f"OPRA_{sym}_{date}.csv")
    rows = ore.recorded(date, sym)
    spot = float(rows[0]["spot"])
    f0_day = 0
    for r in rows:
        if r["_file"] != "surface_wide.csv":
            continue
        rec = opra.get(ore.compact(r["option_symbol"]))
        when = ore.parse_ts(r["quote_time"]) if r.get("quote_time") else None
        hit = ore.nearest(rec, when) if rec and when else None
        if not hit:
            unmatched_total += 1
            continue
        ob, oa = hit[1], hit[2]
        k, t = float(r["strike"]), r["type"]
        if (t == "P") != (k < spot) or oa is None:
            continue
        fb, fa = modelfree._num(r["bid"]) or 0.0, modelfree._num(r["ask"])
        ob = ob or 0.0
        both0 += fb == 0 and ob == 0
        free0 += fb == 0 and ob > 0
        opra0 += fb > 0 and ob == 0
        f0_day += fb == 0
        if fa is not None and oa > ob:
            x = abs((fb + fa) / 2 - (ob + oa) / 2) / (oa - ob)
            ratios.append(x)
            if fb > 0 and ob > 0:
                two_sided.append(x)
    if f0_day:
        with contextlib.redirect_stdout(io.StringIO()):
            lifts = ore.compare(date, sym)
        if lifts and None not in lifts["free"][:2] and None not in lifts["OPRA"][:2]:
            infl.append((date, sym, lifts["free"][0] - lifts["free"][1], lifts["OPRA"][0] - lifts["OPRA"][1]))

print(f"days with OPRA data: {len(days)} {sorted(days)}  (minimum 5)")
if len(days) < 5:
    print("BELOW THE REGISTERED MINIMUM: descriptive only, no verdict.")
print(f"wing contracts: {len(ratios)} with a spread; {unmatched_total} wide rows unmatched (excluded by the rule)")
a = st.median(ratios) if ratios else None
print(f"H5f-a  pooled median {a:.3f} of the OPRA spread (bar 0.5) -> {'HOLDS' if a is not None and a <= 0.5 else 'FAILS'}")
if two_sided:
    print(f"       descriptive: both feeds bid, n={len(two_sided)}, median {st.median(two_sided):.3f}")
fz = both0 + free0
b = both0 / fz if fz else None
print(f"H5f-b  free no-bid -> OPRA no-bid {both0} of {fz} = {b:.1%} (bar 80%) -> {'HOLDS' if b is not None and b >= 0.8 else 'FAILS'};"
      f" OPRA-only no-bid {opra0}")
if infl:
    for d, s, f, o in infl:
        print(f"       {d} {s}: inflation free {f:+.2f}  OPRA {o:+.2f}  gap {abs(o - f) / abs(f):.1%}")
    pos = all(o > 0 for *_, o in infl)
    i_ = st.median(abs(o - f) / abs(f) for *_, f, o in infl)
    mf, mo = st.median(f for *_, f, _o in infl), st.median(o for *_, o in infl)
    ii = abs(mo - mf) / abs(mf)
    ok_i, ok_ii = pos and i_ <= 0.25, pos and ii <= 0.25
    print(f"H5f-c  OPRA inflation positive on every zero-bid day: {pos}; median per-day gap {i_:.1%} (i); "
          f"median OPRA {mo:+.2f} vs median free {mf:+.2f} = {ii:.1%} (ii); bar 25%")
    print(f"       -> (i) {'HOLDS' if ok_i else 'FAILS'}, (ii) {'HOLDS' if ok_ii else 'FAILS'}"
          + ("" if ok_i == ok_ii else "  READINGS DISAGREE: report both, flag for Gabriel, do not choose"))
print("Stated beside any verdict: the rule excludes unmatched contracts, so it cannot see the free "
      "feed's hours-old one-sided quotes on far contracts OPRA did not quote (H5, 23 Sep).")
print("Data provided by Databento (OPRA consolidated NBBO). Aggregates only.")
