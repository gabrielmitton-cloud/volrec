"""lab/ - Break-Even VIX statistics (EXPLORATORY): quintile bins, OLS with a Newey-West slope
interval, the crossing restricted to the observed range (no extrapolation), and a stationary
bootstrap interval for the crossing."""
import importlib.util as _iu
import random
from pathlib import Path

_s = _iu.spec_from_file_location("stress", Path(__file__).resolve().parent / "stress.py")
stress = _iu.module_from_spec(_s)
_s.loader.exec_module(stress)


def bins(x, y, q=5):
    pts = sorted(zip(x, y))
    n, out = len(pts), []
    for i in range(q):
        part = pts[i * n // q:(i + 1) * n // q]
        if part:
            out.append((sum(p[0] for p in part) / len(part), sum(p[1] for p in part) / len(part), len(part)))
    return out


def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    b = sum((u - mx) * (v - my) for u, v in zip(x, y)) / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def slope_ci(x, y, lag, z=1.96):
    """Slope with a Bartlett Newey-West standard error (series in time order)."""
    a, b = ols(x, y)
    n = len(x)
    mx = sum(x) / n
    u = [(xi - mx) * (yi - a - b * xi) for xi, yi in zip(x, y)]
    s = sum(v * v for v in u)
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * sum(u[t] * u[t - k] for t in range(k, n))
    sxx = sum((xi - mx) ** 2 for xi in x)
    se = (s ** 0.5) / sxx if sxx > 0 else float("inf")
    return b, b - z * se, b + z * se


def crossing(a, b, lo, hi):
    if b == 0:
        return None
    x = -a / b
    return x if lo <= x <= hi else None


def boot_crossing(x, y, block, n, seed, lo, hi):
    idx = list(range(len(x)))
    got, out = [], 0
    for path in stress.stationary_paths(idx, block, n, len(idx), seed):
        a, b = ols([x[i] for i in path], [y[i] for i in path])
        c = crossing(a, b, lo, hi)
        if c is None:
            out += 1
        else:
            got.append(c)
    return got, out
