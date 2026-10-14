"""lab/ - the stress lab (EXPLORATORY). Stationary bootstrap (Politis & Romano 1994) with the
Patton-Politis-White (2009) automatic block length; tail statistics on the resampled decades. A
bootstrap cannot draw a month worse than history's worst, so the replays in run_leak.py add the
worst month x 1.5, and every ruin probability is conditional on this sample's crashes."""
import math
import random


def _acov(xc, k):
    n = len(xc)
    return sum(xc[i] * xc[i + k] for i in range(n - k)) / n


def ppw_block(x):
    n = len(x)
    m = sum(x) / n
    xc = [v - m for v in x]
    g0 = _acov(xc, 0)
    if g0 <= 0:
        return 1.0
    kn = max(5, int(math.sqrt(math.log10(n))))
    c = 2.0 * math.sqrt(math.log10(n) / n)
    mmax = int(math.ceil(math.sqrt(n))) + kn
    rho = lambda k: _acov(xc, k) / g0 if k < n else 0.0
    mhat = next((mm for mm in range(0, mmax) if all(abs(rho(mm + k)) < c for k in range(1, kn + 1))), mmax)
    M = min(2 * mhat, mmax)
    lam = lambda t: 1.0 if abs(t) <= 0.5 else (2.0 * (1.0 - abs(t)) if abs(t) <= 1.0 else 0.0)
    if M == 0:
        return 1.0
    G = sum(lam(k / M) * abs(k) * _acov(xc, abs(k)) for k in range(-M, M + 1))
    g = sum(lam(k / M) * _acov(xc, abs(k)) for k in range(-M, M + 1))
    D = 2.0 * g * g
    b = (2.0 * G * G / D) ** (1 / 3) * n ** (1 / 3) if D > 0 else 1.0
    return min(max(b, 1.0), math.ceil(min(3 * math.sqrt(n), n / 3)))


def stationary_paths(x, b, n_paths, length, seed):
    rnd, n, p = random.Random(seed), len(x), 1.0 / max(b, 1.0)
    out = []
    for _ in range(n_paths):
        i, path = rnd.randrange(n), []
        while len(path) < length:
            path.append(x[i])
            i = rnd.randrange(n) if rnd.random() < p else (i + 1) % n
        out.append(path)
    return out


def max_drawdown(rets):
    eq = peak = 1.0
    worst = 0.0
    for r in rets:
        eq = max(eq * (1 + r), 0.0)
        peak = max(peak, eq)
        worst = max(worst, 1 - eq / peak if peak > 0 else 1.0)
    return worst


def expected_shortfall(x, level):
    s = sorted(x)
    k = max(1, int(round(len(s) * (1 - level))))
    return sum(s[:k]) / k


def ruin_prob(paths, floor=0.5):
    def ruined(p):
        eq = 1.0
        for r in p:
            eq *= 1 + r
            if eq < floor:
                return True
        return False
    return sum(1 for p in paths if ruined(p)) / len(paths)
