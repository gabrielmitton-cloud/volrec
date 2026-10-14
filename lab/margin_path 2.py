"""lab/ - one month of a short ATM straddle under Cboe customer margin (EXPLORATORY).
Santa-Clara & Saretto (2009)'s mechanic: $1 of capital, premium written = target weight, margin
calls met from cash, forced liquidation when cash cannot cover the requirement, then reopening at
margin due <= 90% of wealth. Per-share prices; r = 0. Frictions switch on independently so the Leak
Map can attribute the losses (lab/leakmap.py)."""
import importlib.util as _iu
from pathlib import Path

_L = Path(__file__).resolve().parent


def _load(name):
    s = _iu.spec_from_file_location(name, _L / f"{name}.py")
    m = _iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


margin, costs = _load("margin"), _load("costs")
FRICTIONS = ("spreads", "limits", "liquidation", "commissions")
COMMISSION_PER_LEG = 0.0065          # $0.65 a contract on $100,000: per $1 of capital per share of n


def simulate(month, w, frictions, a, b):
    K, mid0 = month["K"], month["C0"] + month["P0"]
    cost = costs.COST_CASES["retail"] * month["half0"] if "spreads" in frictions else 0.0
    comm = 2 * COMMISSION_PER_LEG if "commissions" in frictions else 0.0
    n = w / mid0
    sold = mid0 - cost
    if "limits" in frictions:
        req0 = margin.short_straddle(month["C0"], month["P0"], month["S0"], K, K, a, b)
        if req0 > sold:
            n = min(n, 0.9 / (req0 - sold))
    w_eff = n * mid0
    cash = 1.0 + n * sold - n * comm
    calls = 0
    if "liquidation" in frictions:
        for S, C, P in month["days"]:
            V = C + P
            req = margin.short_straddle(C, P, S, K, K, a, b)
            if n > 0 and cash < n * req:
                calls += 1
                cash -= n * (V + cost) + n * comm          # buy back at mark plus the same cost
                n = 0.0
                sold_now = V - cost
                if cash > 0 and req > sold_now and sold_now > 0:
                    n = min(w / mid0, 0.9 * cash / (req - sold_now))
                    cash += n * sold_now - n * comm
    cash -= n * month["settle"]
    return {"ret": cash - 1.0, "w_eff": w_eff, "liquidations": calls}
