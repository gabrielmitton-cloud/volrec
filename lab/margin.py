"""lab/ - Cboe customer margin for short options (EXPLORATORY). Source: Cboe Margin Manual,
30 November 2021, customer margin account, initial requirement. Percentages unchanged since
6 Jun 1988, so one rule covers 2015-2026. Per share; x100 per contract.

  short put:  max(P + a*S - OTM amount, P + b*K)
  short call: max(C + a*S - OTM amount, C + b*S)
  short put + short call, same underlying: the greater requirement plus the other side's proceeds
  a = 15%, b = 10% for an ETF tracking a broad-based index; 20% / 10% for equity and other ETFs.
"""
RATES = {"SPY": (0.15, 0.10), "QQQ": (0.15, 0.10), "IWM": (0.15, 0.10),
         "GLD": (0.20, 0.10), "USO": (0.20, 0.10)}
BROKER = (0.40, 0.35)                     # Santa-Clara & Saretto (2009): E-Trade's house rate


def short_put(P, S, K, a, b):
    otm = max(S - K, 0.0)
    return max(P + a * S - otm, P + b * K)


def short_call(C, S, K, a, b):
    otm = max(K - S, 0.0)
    return max(C + a * S - otm, C + b * S)


def short_straddle(C, P, S, Kc, Kp, a, b):
    mc, mp = short_call(C, S, Kc, a, b), short_put(P, S, Kp, a, b)
    return mc + P if mc >= mp else mp + C
