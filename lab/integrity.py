"""lab/ - integrity checks on every OPRA day the lab buys (EXPLORATORY). Thresholds are fixed in
lab/REGISTRATION.md before any purchase. A day failing any check is not used.

1. completeness: every strike OPRA LISTS for that expiry (Databento's definition schema) within
   +/-BAND of the implied forward has a call and a put quoted (ask > 0), and there are at least
   MIN_LISTED of them. (Replaced a 10-strike minimum on 12 Oct 2026, after the test day: at $12.81
   with $0.50 strikes, USO's complete 2018 chain holds 5 strikes in the band. Gabriel's decision.)
2. sane spreads: at least SANE_SHARE of those quotes have 0 <= bid <= ask and
   ask - bid <= max(mid, $0.10);
3. put-call parity: within +/-PARITY_BAND, at least PARITY_SHARE of strikes have
   |(C_mid - P_mid + K) - median| <= the two half-spreads + DIV_ALLOW x forward
   (American fund options: dividends and early exercise loosen parity a little).
"""
import csv
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import opra_reference as ore               # noqa: E402

BAND, PARITY_BAND, MIN_LISTED = 0.10, 0.05, 3
SANE_SHARE, PARITY_SHARE, DIV_ALLOW = 0.95, 0.90, 0.005
EDGE = 1e-9                                   # band edges are inclusive despite float rounding
OSI = re.compile(r"^(.+?)(\d{6})([CP])(\d{8})$")


def parse_osi(sym):
    m = OSI.match("".join(str(sym).split()))
    if not m:
        return None
    root, ymd, kind, k = m.groups()
    return root, f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:]}", kind, int(k) / 1000.0


def listed_strikes(def_path, expiry):
    """Strikes OPRA lists for one expiry, from a Databento definition CSV (column raw_symbol)."""
    out = set()
    with open(def_path, newline="") as f:
        for r in csv.DictReader(f):
            p = parse_osi(r.get("raw_symbol", ""))
            if p and p[1] == expiry:
                out.add(p[3])
    return out


def chain_at(opra, expiry, when, tol=120):
    """{strike: {'C': (bid, ask), 'P': (bid, ask)}} for one expiry, at the record nearest `when`."""
    out = {}
    for sym, recs in opra.items():
        p = parse_osi(sym)
        if not p or p[1] != expiry:
            continue
        hit = ore.nearest(recs, when, tol)
        if hit and hit[2] is not None:
            out.setdefault(p[3], {})[p[2]] = (hit[1] or 0.0, hit[2])
    return out


def _mid(q):
    return (q[0] + q[1]) / 2.0


def forward(chain):
    """F ~ K + C_mid - P_mid at the strike where the call and put mids are closest."""
    both = [(k, q) for k, q in chain.items() if "C" in q and "P" in q]
    if not both:
        return None
    k, q = min(both, key=lambda kq: abs(_mid(kq[1]["C"]) - _mid(kq[1]["P"])))
    return k + _mid(q["C"]) - _mid(q["P"])


def check_chain(chain, listed):
    """(passed, {'complete': (ok, detail), 'sane': (ok, detail), 'parity': (ok, detail)}).
    listed: the strikes OPRA lists for this expiry (listed_strikes)."""
    F = forward(chain)
    if F is None:
        return False, {"forward": (False, "no strike with both a call and a put")}
    band = sorted(k for k in listed if abs(k / F - 1) <= BAND + EDGE)
    full = [k for k in band if k in chain and all(t in chain[k] and chain[k][t][1] > 0 for t in "CP")]
    complete = (len(band) >= MIN_LISTED and len(full) == len(band),
                f"{len(full)} of {len(band)} listed strikes two-sided (need all, and >= {MIN_LISTED})")
    quotes = [chain[k][t] for k in band if k in chain for t in "CP" if t in chain[k]]
    good = [q for q in quotes if 0 <= q[0] <= q[1] and q[1] - q[0] <= max(_mid(q), 0.10)]
    share = len(good) / len(quotes) if quotes else 0.0
    sane = (share >= SANE_SHARE, f"{share:.0%} of {len(quotes)} quotes sane (need {SANE_SHARE:.0%})")
    near = [k for k in full if abs(k / F - 1) <= PARITY_BAND + EDGE]
    x = {k: _mid(chain[k]["C"]) - _mid(chain[k]["P"]) + k for k in near}
    if x:
        med = st.median(x.values())
        tol = {k: (chain[k]["C"][1] - chain[k]["C"][0]) / 2 + (chain[k]["P"][1] - chain[k]["P"][0]) / 2
               + DIV_ALLOW * F for k in near}
        inside = sum(1 for k in near if abs(x[k] - med) <= tol[k])
        pshare = inside / len(near)
    else:
        pshare = 0.0
    parity = (pshare >= PARITY_SHARE, f"{pshare:.0%} of {len(near)} strikes within parity (need {PARITY_SHARE:.0%})")
    det = {"complete": complete, "sane": sane, "parity": parity}
    return all(v[0] for v in det.values()), det
