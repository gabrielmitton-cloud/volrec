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
