"""lab/ - the trades (EXPLORATORY). Short ATM straddle and 5% OTM strangle, entered at 14:30 New
York, held to expiry, settled at intrinsic on the fund's RAW close. Per-share figures; returns are
per dollar of mid premium. Rules read the previous trading day's closes."""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import importlib.util as _iu               # noqa: E402

_s = _iu.spec_from_file_location("costs", ROOT / "lab" / "costs.py")
costs = _iu.module_from_spec(_s)
_s.loader.exec_module(costs)

INDEX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
R2_REF = 20.0


def _sellable(q):
    """A leg a seller can actually hit: a positive bid, and not crossed."""
    return q[0] is not None and q[0] > 0 and q[1] >= q[0]


def nearest_strike(chain, target):
    two = [k for k, q in chain.items() if "C" in q and "P" in q and _sellable(q["C"]) and _sellable(q["P"])]
    return min(two, key=lambda k: (abs(k - target), k)) if two else None


# 28 Oct 2026 (outside review M03). OCC Information Memo #46881 (28 Apr 2020): USO's 1-for-8 reverse split,
# effective before the open on 29 Apr 2020. Its options became USO1, delivering 12 new USO shares plus cash in lieu
# of half a share, and OCC priced USO1 = 0.125 x USO until the cash was fixed. A contract opened before an effective
# day and held past it is therefore worth `ratio` x the new share, not the new share itself. Raw closes stay raw
# (they must match the strikes of contracts opened after the event); only the position's own deliverable changes.
# The only such event for the five funds over 2016-2026 (the lab's quote files hold no other root - scanned 28 Oct).
DELIVERABLE = {"USO": (("2020-04-29", 0.125),)}


def spot(bars, symbol, day, opened=None):
    """The underlying price for a contract opened on `opened` (None = a new contract), on `day`."""
    s = bars[symbol][day][0]
    for eff, ratio in (DELIVERABLE.get(symbol, ()) if opened else ()):
        if opened < eff <= day:
            s *= ratio
    return s


def settle(bars, symbol, day, opened=None):
    return spot(bars, symbol, day, opened)


def intrinsic(kind, K, S):
    return max(S - K, 0.0) if kind == "C" else max(K - S, 0.0)


def leg(bid, ask, kind, K, S, case):
    """(mid premium, P&L per share), or None for a quote half_spread rejects (no ask, crossed)."""
    h = costs.half_spread(bid, ask)
    if h is None:
        return None
    mid = ((bid or 0.0) + ask) / 2.0
    return mid, mid - costs.charged(h, case) - intrinsic(kind, K, S)


def position(chain, F, S_exp, case, kind="straddle"):
    if kind == "straddle":
        kp = kc = nearest_strike(chain, F)
    else:
        kp, kc = nearest_strike(chain, 0.95 * F), nearest_strike(chain, 1.05 * F)
    if kp is None or kc is None:
        return None
    lp, lc = leg(*chain[kp]["P"], "P", kp, S_exp, case), leg(*chain[kc]["C"], "C", kc, S_exp, case)
    if lp is None or lc is None:
        return None
    (pm, pp), (cm, cp) = lp, lc
    prem = pm + cm
    return {"K_put": kp, "K_call": kc, "premium": prem, "pnl": pp + cp, "ret": (pp + cp) / prem if prem > 0 else None}


def vega76(F, K, T, vol):
    """Black-76 vega with r = 0, per volatility POINT."""
    v = vol * math.sqrt(T)
    d1 = (math.log(F / K) + v * v / 2) / v
    return F * math.sqrt(T) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) / 100.0


def rule_weights(index_prev, rv_prev, vix_prev, vix3m_prev):
    """R2 is 20/index uncapped (registered: below an index of 20 it sizes above 1). No index level
    that day -> only R0 and R3 can trade, and R2 stands aside."""
    if index_prev is None or index_prev <= 0:
        return {"R0": 1.0, "R1": 0.0, "R2": 0.0,
                "R3": 0.0 if (vix3m_prev is not None and vix_prev is not None and vix3m_prev < vix_prev) else 1.0}
    return {"R0": 1.0,
            "R1": 1.0 if (rv_prev is not None and index_prev > rv_prev) else 0.0,
            "R2": R2_REF / index_prev,
            "R3": 0.0 if (vix3m_prev is not None and vix_prev is not None and vix3m_prev < vix_prev) else 1.0}
