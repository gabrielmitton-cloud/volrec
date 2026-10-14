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


def nearest_strike(chain, target):
    two = [k for k, q in chain.items() if "C" in q and "P" in q and q["C"][1] > 0 and q["P"][1] > 0]
    return min(two, key=lambda k: (abs(k - target), k)) if two else None


def settle(bars, symbol, day):
    return bars[symbol][day][0]


def intrinsic(kind, K, S):
    return max(S - K, 0.0) if kind == "C" else max(K - S, 0.0)


def leg(bid, ask, kind, K, S, case):
    mid = ((bid or 0.0) + ask) / 2.0
    sold = mid - costs.charged(costs.half_spread(bid, ask), case)
    return mid, sold - intrinsic(kind, K, S)


def position(chain, F, S_exp, case, kind="straddle"):
    if kind == "straddle":
        kp = kc = nearest_strike(chain, F)
    else:
        kp, kc = nearest_strike(chain, 0.95 * F), nearest_strike(chain, 1.05 * F)
    if kp is None or kc is None:
        return None
    pm, pp = leg(*chain[kp]["P"], "P", kp, S_exp, case)
    cm, cp = leg(*chain[kc]["C"], "C", kc, S_exp, case)
    prem = pm + cm
    return {"K_put": kp, "K_call": kc, "premium": prem, "pnl": pp + cp, "ret": (pp + cp) / prem if prem > 0 else None}


def vega76(F, K, T, vol):
    """Black-76 vega with r = 0, per volatility POINT."""
    v = vol * math.sqrt(T)
    d1 = (math.log(F / K) + v * v / 2) / v
    return F * math.sqrt(T) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) / 100.0


def rule_weights(index_prev, rv_prev, vix_prev, vix3m_prev):
    return {"R0": 1.0,
            "R1": 1.0 if (rv_prev is not None and index_prev > rv_prev) else 0.0,
            "R2": R2_REF / index_prev,
            "R3": 0.0 if (vix3m_prev is not None and vix_prev is not None and vix3m_prev < vix_prev) else 1.0}
