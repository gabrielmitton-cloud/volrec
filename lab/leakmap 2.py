"""lab/ - the Leak Map's attribution (EXPLORATORY). Each friction's leak depends on the order the
frictions are added, so it is credited its Shapley value - the average over all orders - with the
minimum and maximum across orders reported beside it (as the main paper treats its decomposition)."""
from itertools import permutations

FRICTIONS = ("spreads", "limits", "liquidation", "commissions")


def shapley(value, players=FRICTIONS):
    leaks = {p: [] for p in players}
    for order in permutations(players):
        on = frozenset()
        for p in order:
            nxt = on | {p}
            leaks[p].append(value(on) - value(nxt))
            on = nxt
    return {p: (sum(v) / len(v), min(v), max(v)) for p, v in leaks.items()}
