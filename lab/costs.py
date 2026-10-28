"""lab/ - the retail implementation audit (EXPLORATORY; docs/superpowers/specs/
2026-10-12-retail-vrp-audit-design.md). What a seller pays to trade, in dollars and in volatility
points. Pure functions; lab/test_lab.py checks each against a hand-worked answer.

Held to expiry, so only the ENTRY half-spread is charged (Santa-Clara & Saretto 2009, footnote 7;
Muravyev & Pearson 2020's convention). The fractions are Muravyev & Pearson's published figures
for single-stock options, 2004-2015 - assumptions here, not findings about fund options.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

COST_CASES = {"mid": 0.0, "timed": 0.30, "retail": 0.80, "quoted": 1.00}   # fraction of the quoted half-spread
COMMISSIONS = (0.0, 0.65)                                                   # dollars per contract


def half_spread(bid, ask):
    """Quoted half-spread per share. A missing bid is a zero bid (Databento writes a blank, the
    free feed a 0); no ask, or a crossed quote, is no quote."""
    if ask is None:
        return None
    b = bid or 0.0
    if ask < b:
        return None
    return (ask - b) / 2.0


def charged(half, case):
    """Per-share cost of one entry under a registered cost case."""
    return half * COST_CASES[case]


def straddle_cost(call_q, put_q, case):
    """call_q, put_q: (bid, ask). Per-share cost of selling one straddle, or None."""
    hc, hp = half_spread(*call_q), half_spread(*put_q)
    if hc is None or hp is None:
        return None
    return charged(hc, case) + charged(hp, case)


def vol_points(cost_per_share, vega_per_point):
    """A per-share dollar cost expressed in volatility points of the position."""
    return cost_per_share / vega_per_point if vega_per_point > 0 else None


def commission(contracts, per_contract):
    return contracts * per_contract


def strip_cost(rows, r):
    """Cost of SELLING the variance strip, in volatility points: the registered estimator on mids
    minus the same estimator on bids, over contracts with a positive bid (a zero-bid wing cannot
    be sold, so it is left out of both runs and the comparison stays like for like)."""
    import modelfree
    live = [x for x in rows if float(x.get("bid") or 0) > 0]
    if not live:
        return None
    at_mid = modelfree.model_free_30d(live, r)
    at_bid = modelfree.model_free_30d([dict(x, mid=x["bid"]) for x in live], r)
    if not at_mid or not at_bid:
        return None
    return at_mid[0] - at_bid[0]


def _basket_one_expiry(rows, r):
    """The model-free strip ONE expiry holds, chosen exactly as modelfree.variance_one_expiry chooses it on mids:
    -> (sigma2, T, {strike: (variance weight per $ of premium, half-spread of the leg held)}) or None."""
    from math import exp
    import modelfree
    if not rows:
        return None
    T = int(rows[0]["dte"]) / 365.0
    if T <= 0:
        return None
    calls, puts = {}, {}
    for row in rows:
        mid, k = modelfree._num(row["mid"]), modelfree._num(row["strike"])
        if mid is None or mid <= 0 or k is None:
            continue
        h = half_spread(modelfree._num(row.get("bid")), modelfree._num(row.get("ask")))
        (calls if row["type"] == "C" else puts)[k] = (mid, h if h is not None else 0.0)
    both = sorted(set(calls) & set(puts))
    if len(both) < 3:
        return None
    disc = exp(r * T)
    k_star = min(both, key=lambda k: abs(calls[k][0] - puts[k][0]))
    F = k_star + disc * (calls[k_star][0] - puts[k_star][0])
    below = [k for k in sorted(set(calls) | set(puts)) if k <= F]
    if not below:
        return None
    K0 = below[-1]
    q = {}
    for k in sorted(set(calls) | set(puts)):
        if k < K0 and k in puts:
            q[k] = puts[k]
        elif k > K0 and k in calls:
            q[k] = calls[k]
        elif k == K0 and k in calls and k in puts:
            q[k] = ((calls[k][0] + puts[k][0]) / 2.0, (calls[k][1] + puts[k][1]) / 2.0)
    ks = sorted(q)
    if len(ks) < 3:
        return None
    total, legs = 0.0, {}
    for i, k in enumerate(ks):
        dK = ks[1] - ks[0] if i == 0 else ks[-1] - ks[-2] if i == len(ks) - 1 else (ks[i + 1] - ks[i - 1]) / 2.0
        wgt = (2.0 / T) * (dK / (k * k)) * disc
        total += wgt * q[k][0]
        legs[k] = (wgt, q[k][1])
    return total - (1.0 / T) * ((F / K0 - 1.0) ** 2), T, legs


def strip_cost_fixed(rows, r):
    """Cost of SELLING the variance strip, in volatility points, with the PORTFOLIO HELD FIXED (28 Oct 2026, outside
    review M02). The strip is chosen once, on mids, as the registered estimator chooses it (forward, K0, legs and
    their weights); selling it at the bid gives up each held leg's half-spread, which lowers the strip's variance by
    sum(weight x half-spread). The 30-day blend is modelfree.model_free_30d's. A quote the strip does not hold can no
    longer move the cost (the old strip_cost re-ran the whole estimator on bids, so the forward, K0 and legs moved
    with the quotes). Same contracts as strip_cost: a zero-bid quote cannot be sold and is left out."""
    from math import sqrt
    import modelfree
    live = [x for x in rows if float(x.get("bid") or 0) > 0]
    by_exp = {}
    for x in live:
        by_exp.setdefault(x["expiration"], []).append(x)
    legs = []
    for e, rs in by_exp.items():
        got = _basket_one_expiry(rs, r)
        if got:
            s2, T, held = got
            legs.append((int(rs[0]["dte"]), s2, T, sum(w * h for w, h in held.values())))
    if not legs:
        return None
    pair = modelfree.pick_pair([x[0] for x in legs])
    legs = sorted(x for x in legs if x[0] in pair)
    td = modelfree.TARGET_DAYS
    if len(legs) == 1 or not (legs[0][0] <= td <= legs[-1][0]):
        d, s2, T, c2 = min(legs, key=lambda x: abs(x[0] - td))
        mid_v, bid_v = s2, s2 - c2
    else:
        (d1, s1, T1, c1), (d2, s2, T2, c2) = legs[0], legs[-1]
        w = (d2 - td) / (d2 - d1)
        scale = 365.0 / td
        mid_v = (T1 * s1 * w + T2 * s2 * (1 - w)) * scale
        bid_v = (T1 * (s1 - c1) * w + T2 * (s2 - c2) * (1 - w)) * scale
    if mid_v <= 0 or bid_v <= 0:
        return None
    return 100.0 * (sqrt(mid_v) - sqrt(bid_v))
