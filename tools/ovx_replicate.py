#!/usr/bin/env python3
"""How much of the gap between this project's USO estimate and OVX is the free data, and how
much is everything else? Written 8 Oct 2026 for the methods audit (HANDOFF 18, item 1).

EXPLORATORY, NOT REGISTERED. Nothing here changes a registered number or a recorded verdict.
It measures; it does not re-score anything.

WHY. Cboe builds OVX from USO options with rules this project's estimator does not follow
(Cboe "Selected Broad-Based Index, Equity and ETF Volatility Indices" methodology v9.0, s2.1
and Step 1; Cboe "Volatility Index Mathematics Methodology" v5.0, s2(b) and s3):
  - only PM-settled USO options expiring on the third Friday of the month (Thursday if that
    Friday is a holiday); series with fewer than 7 days to expiry excluded;
  - near and next term by the Nearest Term Method - the two nearest remaining expiries, with
    the 30-day blend extrapolating when they do not bracket 30 days;
  - time to expiry in MINUTES to the 16:00 ET settlement, over a 525,600-minute year;
  - mid quotes; walking outward from K0, any option with a zero bid OR a zero ask excluded,
    and nothing beyond two consecutive such strikes (s3(a)(iii));
  - the rate a bond-equivalent CMT yield converted to continuous (s2.1).
`modelfree.model_free_30d` instead takes the recorded weekly expiries either side of 30 days,
whole days over 365, and (as registered for H3) keeps zero-bid quotes inside a +/-30% band.

WHAT IT DOES. For every day with a Databento OPRA file for USO (consolidated NBBO, the full
chain around the snapshot minute - already bought for H5f; this script never buys anything),
it computes four readings at the snapshot minute and compares each with Cboe's OVX close:
  S0  the registered estimate: free feed, recorded band and legs, registered rules;
  S1  the same contracts and rules, priced at OPRA's NBBO instead      -> the DATA effect;
  S1c OPRA, the same band and legs, Cboe's quote rules and minute clock -> Cboe's QUOTE RULES;
  S2  OPRA, the same two legs, every listed strike, Cboe's rules        -> strike COVERAGE;
  S3  OPRA, Cboe's own legs, strikes, rules and clock                  -> the EXPIRY effect;
  S3 - OVX close is what is left: the snapshot is ~2-5 h before the close (timing), Cboe's
  rate curve vs one 1-month rate, and Cboe's index-level filter (holds the last value when the
  index jumps more than 0.5 points in 30 s), none of which a single snapshot reproduces.

LIMITS, STATE THEM. One snapshot minute per day, not Cboe's close. Databento's cbbo-1m is a
one-minute consolidated BBO, Cboe uses its own NBBO feed. The rate is DGS1MO for both terms.

Run from the repo root:  FRED_KEY=use-cache python tools/ovx_replicate.py
Output is aggregates only.  Data provided by Databento (OPRA consolidated NBBO).
"""
import csv
import math
import os
import re
import statistics as st
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")

import modelfree                                   # noqa: E402
import opra_reference as ore                       # noqa: E402

try:
    from zoneinfo import ZoneInfo
    NY = ZoneInfo("America/New_York")
except Exception:                                  # pragma: no cover - stdlib on 3.9+
    NY = None

MIN365 = 365 * 1440
CM_MIN = 30 * 1440
MIN_DAYS = 7                                       # Cboe v9.0 s2.1, OVX and GVZ
SYM_RE = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


# ---------------- calendar ----------------
def third_friday(y, m, holidays=()):
    """Cboe's monthly expiry: the third Friday, or the Thursday before it if that is a holiday."""
    d = date(y, m, 15)
    d += timedelta(days=(4 - d.weekday()) % 7)
    return d - timedelta(days=1) if d in holidays else d


def is_monthly(exp, holidays=()):
    return exp == third_friday(exp.year, exp.month, holidays)


def settle_utc(exp):
    """16:00 New York on the expiry date, as UTC (PM-settled)."""
    if NY is not None:
        return datetime.combine(exp, time(16, 0), NY).astimezone(timezone.utc)
    # fallback: EDT from the second Sunday of March to the first Sunday of November
    mar = date(exp.year, 3, 8) + timedelta(days=(6 - date(exp.year, 3, 8).weekday()) % 7)
    nov = date(exp.year, 11, 1) + timedelta(days=(6 - date(exp.year, 11, 1).weekday()) % 7)
    off = 4 if mar <= exp < nov else 5
    return datetime.combine(exp, time(16 + off, 0), timezone.utc)


def minutes_to(exp, when):
    """Whole minutes from `when` to settlement, rounded down (Cboe v5.0 s3(a)(i))."""
    return int((settle_utc(exp) - when).total_seconds() // 60)


# ---------------- Cboe's single-term variance, as written in v5.0 s3(a) ----------------
def cboe_sigma2(quotes, R, T):
    """quotes: {(strike, 'C'|'P'): (bid, ask)} for one expiry. Returns (sigma2, F, K0, n) or None.

    (ii) the ATM strike minimises |C - P| on mids; series with a null quote or bid > ask are
    not candidates; ties take the LOWEST strike. F = K + e^{RT}(C - P). K0 = the strike at or
    immediately below F; if its call or put is null or crossed, no value.
    (iii) null quotes removed; walk outward from K0, excluding any option with a zero bid or a
    zero ask, and stop after two consecutive such strikes.
    (iv) dK half the gap to the neighbours, the full gap at the two edges of the INCLUDED set.
    """
    def ok(q):
        return q is not None and q[0] is not None and q[1] is not None and q[0] <= q[1]
    def mid(q):
        return (q[0] + q[1]) / 2.0
    strikes = sorted({k for k, _ in quotes})
    pairs = [k for k in strikes if ok(quotes.get((k, "C"))) and ok(quotes.get((k, "P")))]
    if not pairs:
        return None
    atm = min(pairs, key=lambda k: (abs(mid(quotes[(k, "C")]) - mid(quotes[(k, "P")])), k))
    F = atm + math.exp(R * T) * (mid(quotes[(atm, "C")]) - mid(quotes[(atm, "P")]))
    below = [k for k in strikes if k <= F]
    if not below:
        return None
    K0 = below[-1]
    if not (ok(quotes.get((K0, "C"))) and ok(quotes.get((K0, "P")))):
        return None
    q = {K0: (mid(quotes[(K0, "C")]) + mid(quotes[(K0, "P")])) / 2.0}
    for side, walk in (("P", [k for k in reversed(strikes) if k < K0]),
                       ("C", [k for k in strikes if k > K0])):
        zeros = 0
        for k in walk:
            qt = quotes.get((k, side))
            if qt is None or qt[0] is None or qt[1] is None:
                continue                                   # null quotes removed first
            if qt[0] == 0 or qt[1] == 0:
                zeros += 1
                if zeros >= 2:
                    break
                continue
            zeros = 0
            if qt[0] <= qt[1]:
                q[k] = mid(qt)
    ks = sorted(q)
    if len(ks) < 3 or not any(k < K0 for k in ks) or not any(k > K0 for k in ks):
        return None
    total = 0.0
    for i, k in enumerate(ks):
        dK = (ks[1] - ks[0]) if i == 0 else (ks[-1] - ks[-2]) if i == len(ks) - 1 \
            else (ks[i + 1] - ks[i - 1]) / 2.0
        total += dK / (k * k) * math.exp(R * T) * q[k]
    return (2.0 / T) * total - (1.0 / T) * (F / K0 - 1.0) ** 2, F, K0, len(ks)


def blend30(m1, s1, m2, s2):
    """Cboe v5.0 s3(b): interpolate - or extrapolate, when both terms sit on one side - to 30
    days in minutes. Returns the index level in points, or None if the variance is not positive."""
    T1, T2 = m1 / MIN365, m2 / MIN365
    v = (T1 * s1 * (m2 - CM_MIN) / (m2 - m1) + T2 * s2 * (CM_MIN - m1) / (m2 - m1)) * MIN365 / CM_MIN
    return 100.0 * math.sqrt(v) if v > 0 else None


def bey_to_continuous(bey):
    """Cboe v5.0 s2.1: APY = (1 + BEY/2)^2 - 1, then R = ln(1 + APY)."""
    return math.log((1 + bey / 2) ** 2)


# ---------------- the four readings for one day ----------------
def chain_at(opra, when, root="USO"):
    """{expiry: {(strike, type): (bid, ask)}} from OPRA records nearest `when` (within 120 s)."""
    out = {}
    for sym, recs in opra.items():
        m = SYM_RE.match(sym)
        if not m or m.group(1) != root:
            continue
        hit = ore.nearest(recs, when)
        if not hit:
            continue
        exp = datetime.strptime(m.group(2), "%y%m%d").date()
        out.setdefault(exp, {})[(int(m.group(4)) / 1000.0, m.group(3))] = (hit[1], hit[2])
    return out


def as_quote_rows(chain, exp, dte):
    """A chain leg in the row shape modelfree reads (mid > 0 only, as its registered rule)."""
    rows = []
    for (k, t), (b, a) in chain.get(exp, {}).items():
        if a is None:
            continue
        b = b or 0.0
        rows.append({"dte": str(dte), "strike": str(k), "type": t, "bid": str(b), "ask": str(a),
                     "mid": str((b + a) / 2.0), "expiration": exp.isoformat()})
    return rows


def day_readings(day, opra_path, r_bey, ovx_close, holidays=()):
    rows = ore.recorded(day, "USO")
    band = [r for r in rows if r["_file"] == "surface.csv"]
    when = ore.snapshot_minute(rows)
    if not band or not when:
        return None
    opra = ore.load_opra(opra_path)
    chain = chain_at(opra, when)
    out = {"day": day, "ovx": ovx_close, "when": when}

    # S0 - the registered estimate, exactly as modelfree computes it
    s0 = modelfree.model_free_30d(band, r_bey)
    out["S0"] = s0[0] if s0 else None
    legs = sorted({(r["expiration"], int(r["dte"])) for r in band})
    out["legs_ours"] = modelfree.pick_pair([d for _, d in legs])

    # S1 - the recorded band's own contracts, priced at OPRA's NBBO, registered rules
    s1rows = []
    for r in band:
        recs = opra.get(ore.compact(r["option_symbol"]))
        hit = ore.nearest(recs, ore.parse_ts(r["quote_time"])) if recs and r.get("quote_time") else None
        if hit and hit[2] is not None:
            b = hit[1] or 0.0
            s1rows.append(dict(r, bid=str(b), ask=str(hit[2]), mid=str((b + hit[2]) / 2)))
    s1 = modelfree.model_free_30d(s1rows, r_bey) if s1rows else None
    out["S1"] = s1[0] if s1 else None

    R = bey_to_continuous(r_bey)

    def cboe_index(exps):
        terms = []
        for e in exps:
            mins = minutes_to(e, when)
            got = cboe_sigma2(chain.get(e, {}), R, mins / MIN365) if mins > 0 else None
            if not got:
                return None, None
            terms.append((mins, got[0], got[3]))
        (m1, s1_, n1), (m2, s2_, n2) = terms
        return blend30(m1, s1_, m2, s2_), n1 + n2

    our_exps = sorted(date.fromisoformat(e) for e, d in legs if d in out["legs_ours"])

    # S1c - OPRA, our two legs, ONLY the recorded band's strikes, Cboe's quote rules and minute
    # clock -> the RULES step, with coverage held fixed. (The registered rule cannot be applied
    # to the full chain: it keeps every zero-bid stub at half its ask, and across a full USO
    # chain that reads 60-280 points - see `stub_check`.)
    band_keys = {(float(r["strike"]), r["type"], r["expiration"]) for r in band}
    banded = {e: {kt: q for kt, q in chain.get(e, {}).items() if (kt[0], kt[1], e.isoformat()) in band_keys}
              for e in our_exps}
    terms = []
    for e in our_exps:
        mins = minutes_to(e, when)
        got = cboe_sigma2(banded[e], R, mins / MIN365) if mins > 0 else None
        terms.append((mins, got[0]) if got else None)
    out["S1c"] = blend30(terms[0][0], terms[0][1], terms[1][0], terms[1][1]) \
        if len(terms) == 2 and all(terms) else None

    # S2 - OPRA, our two legs, every listed strike, Cboe's quote rules and clock
    out["S2"], out["n2"] = cboe_index(our_exps) if len(our_exps) == 2 else (None, None)

    # S3 - Cboe's own legs: monthlies, >= 7 days, the nearest two (extrapolating if need be)
    cand = sorted(e for e in chain if is_monthly(e, holidays)
                  and (e - when.date()).days >= MIN_DAYS and minutes_to(e, when) > 0)
    out["legs_cboe"] = [(e - when.date()).days for e in cand[:2]]
    out["S3"], out["n3"] = cboe_index(cand[:2]) if len(cand) >= 2 else (None, None)
    return out


def summarise(label, days):
    keys = ("S0", "S1", "S1c", "S2", "S3")
    full = [x for x in days if x.get("ovx") is not None and all(x.get(k) is not None for k in keys)]
    if not full:
        print(f"\n{label}: no complete days")
        return
    m = lambda f: st.mean(f(x) for x in full)
    print(f"\n{label} - {len(full)} complete days")
    print("  mean gap to the OVX close  " + "  ".join(f"{k} {m(lambda x, k=k: x[k] - x['ovx']):+.2f}" for k in keys))
    print("  mean |gap|                 " + "  ".join(f"{k} {m(lambda x, k=k: abs(x[k] - x['ovx'])):.2f}" for k in keys))
    print("  median |gap|               " + "  ".join(
        f"{k} {st.median(abs(x[k] - x['ovx']) for x in full):.2f}" for k in keys))
    steps = (("data", "S1", "S0"), ("Cboe rules", "S1c", "S1"), ("coverage", "S2", "S1c"), ("expiry", "S3", "S2"))
    print("  mean step                  " + "  ".join(f"{n} {m(lambda x, a=a, b=b: x[a] - x[b]):+.2f}" for n, a, b in steps)
          + f"  left {m(lambda x: x['S3'] - x['ovx']):+.2f}")
    print("  mean |step|                " + "  ".join(f"{n} {m(lambda x, a=a, b=b: abs(x[a] - x[b])):.2f}" for n, a, b in steps)
          + f"  left {m(lambda x: abs(x['S3'] - x['ovx'])):.2f}")


def main():
    import analyze
    from panel_health import US_MARKET_HOLIDAYS, AFTER_CLOSE_DAYS
    files = sorted(ore.DATA_DIR.glob("OPRA_USO_*.csv"))
    if not files:
        sys.exit(f"no OPRA USO files in {ore.DATA_DIR} (set VOLREC_DATABENTO_DIR)")
    ovx = analyze.fetch_market_vol(["OVX"]).get("OVX", {})
    r = modelfree.risk_free()
    print(f"OVX replication from OPRA - EXPLORATORY (HANDOFF 18, methods audit item 1). r = {r:.3%} (DGS1MO)")
    print("S0 free/registered  S1 OPRA same contracts  S1c +Cboe quote rules & clock  S2 +all strikes  "
          "S3 +Cboe's monthly legs\n")
    print(f"{'date':<11}{'OVX':>7}{'S0':>7}{'S1':>7}{'S1c':>7}{'S2':>7}{'S3':>7}  "
          f"{'data':>6}{'rules':>7}{'cover':>7}{'expiry':>7}{'left':>7}  legs ours -> Cboe")
    res = []
    for f in files:
        day = f.stem.split("_")[-1]
        got = day_readings(day, f, r, ovx.get(day), US_MARKET_HOLIDAYS)
        if not got:
            continue
        got["dropped"] = date.fromisoformat(day) in AFTER_CLOSE_DAYS
        res.append(got)
        v = lambda k: f"{got[k]:7.2f}" if got.get(k) is not None else "    n/a"
        def d(a, b):
            return f"{got[a] - got[b]:+7.2f}" if got.get(a) is not None and got.get(b) is not None else "    n/a"
        print(f"{day:<11}{v('ovx')}{v('S0')}{v('S1')}{v('S1c')}{v('S2')}{v('S3')}  "
              f"{d('S1','S0')[1:]}{d('S1c','S1')}{d('S2','S1c')}{d('S3','S2')}{d('S3','ovx')}  "
              f"{got['legs_ours']} -> {got['legs_cboe']}" + ("  (after the close: dropped)" if got["dropped"] else ""))
    summarise("ALL days with OPRA", res)
    summarise("H5e's counted days (from 23 Sep, after-close days dropped)",
              [x for x in res if x["day"] >= modelfree.H5E_START and not x["dropped"]])
    print(f"\n{ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
