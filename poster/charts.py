"""The SCCUR poster's charts, drawn as inline SVG (vector, so the print stays sharp at 48 x 36 in).

Pure functions: numbers in, an <svg> string out. Nothing here reads a file or runs a program;
poster/build_poster.py passes in the project's own numbers. Each chart is drawn at about the size the page shows
it, one viewBox unit per CSS pixel (96 per inch), so a font-size here is close to the printed size: 32 px is
24 pt, the poster's floor, and text() refuses anything smaller (the page's render check measures the result).

Colours mean one thing everywhere: blue is Cboe's published index, orange is free data's gap to it (or, in the
bell curves, what a fixed strike band leaves out, the source of that gap). Both pass the dataviz palette check on
white (lightness band, chroma floor, colour-blind separation, contrast; 8 Nov 2026); the poster's navy (#0b2447)
failed it as a series colour (too dark, reads as grey ink), so it stays for headings only. Identity is never
colour alone: the index is a line, the gaps are bars, and every chart is labelled in words.

The main chart draws aggregate statistics only: per fund, how many days fell at each gap from Cboe's index, in
half-point bins, never a date, a day's gap or an index's own value. Gabriel's request to Cboe (sent 10 Oct 2026,
repeated 21 Oct, approved 4 Nov) said "Only aggregate statistics appear (for example, average differences between
my estimates and the index)"; a chart of daily closes would reproduce the series, and a chart of daily gaps would
let anyone holding the (public) daily estimates read each close back (8 Nov 2026 Astra review). gap_histogram()
takes numbers only.
"""
import html
import math
from datetime import date

CBOE, ORANGE, INK, MUTE, RULE, BAND = "#1f4e9c", "#e35205", "#14213d", "#4f5a6d", "#d3d9e3", "#e9eef6"
SANS = "Inter, system-ui, sans-serif"
HEAD = "'Inter Tight', Inter, system-ui, sans-serif"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MIN_FONT = 32


def esc(s):
    return html.escape(str(s), quote=True)


def minus(s):
    """A typographic minus for printed numbers."""
    return s.replace("-", "−")


def text(x, y, s, size, *, weight=400, fill=INK, anchor="start", family=SANS):
    """One SVG text element; size in CSS px, never below the poster's floor."""
    if size < MIN_FONT:
        raise ValueError(f"text {s!r} at {size}px is below the poster's {MIN_FONT}px floor")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def svg(w, h, label, body):
    return f'<svg viewBox="0 0 {w} {h:.0f}" class="chart" role="img" aria-label="{esc(label)}">{body}</svg>'


def nice_step(span, ticks=4):
    """A round gridline step (1, 2, 2.5 or 5 times a power of ten) giving at most about `ticks` intervals."""
    raw = max(span, 1e-9) / ticks
    mag = 10 ** math.floor(math.log10(raw))
    return next(k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw * (1 - 1e-12))


def shared_scale(values, ticks=4):
    """One vertical scale for several panels: (lo, hi, step) in round numbers, with zero always on it, so the same
    gap draws the same bar in every panel (8 Nov reviews: separate scales made gold, the closest tracker, look
    second-worst)."""
    lo_v, hi_v = min(min(values), 0.0), max(max(values), 0.0)
    step = nice_step((hi_v - lo_v) or 1.0, ticks)
    lo, hi = math.floor(lo_v / step) * step, math.ceil(hi_v / step) * step
    return lo, (hi if hi - lo >= step else lo + step), step


def weekday_slot(first, d):
    """Weekdays from `first` to `d` (0 for `first` itself), so a weekday without a reading stays a blank."""
    a, b = date.fromisoformat(first), date.fromisoformat(d)
    days = (b - a).days
    return days // 7 * 5 + sum(1 for k in range(days % 7) if (a.weekday() + k) % 7 < 5)


def rounded_bar(x, w, base, end, r=4.0):
    """A vertical bar from `base` to `end` (SVG y), square on the baseline and rounded at its data end. Coordinate
    pairs only (M, L, Q), so every point can be checked against the frame."""
    r = max(0.0, min(r, abs(end - base) / 2, w / 2))
    s = -1 if end < base else 1                                    # -1: the bar rises above the baseline
    pts = (f"M{x:.1f} {base:.1f} L{x:.1f} {end - s * r:.1f} Q{x:.1f} {end:.1f} {x + r:.1f} {end:.1f} "
           f"L{x + w - r:.1f} {end:.1f} Q{x + w:.1f} {end:.1f} {x + w:.1f} {end - s * r:.1f} L{x + w:.1f} {base:.1f} Z")
    return f'<path d="{pts}" fill="{ORANGE}"/>'


BIN = 0.5      # the main chart's bin width, in volatility points: its edges fall on 0 and on the band's +/-1


def bin_counts(gaps, width=BIN):
    """{k: days} for the bins [k*width, (k+1)*width): the days counted, never listed."""
    out = {}
    for g in gaps:
        k = math.floor(float(g) / width)
        out[k] = out.get(k, 0) + 1
    return out


def within_one(gaps):
    """Days with -1 <= gap < 1: exactly the days in the bins inside the +/-1 band (the bins' edges fall on it)."""
    return sum(1 for g in gaps if -1.0 <= float(g) < 1.0)


def count_scale(most):
    """(top, step) for a day-count axis: a round step (1, 2, 5, 10, 20, 25 or 50) giving at most five intervals."""
    step = next(s for s in (1, 2, 5, 10, 20, 25, 50, 100) if most <= 5 * s)
    return max(step, math.ceil(most / step) * step), step


def gap_histogram(sym, index, what, gaps, mae, scale, counts, w=940, h=598):
    """One fund: on how many days the free estimate landed at each distance from Cboe's published index, in
    half-point bins of the gap (free data minus the index). Counts only: no date and no single day's value is
    drawn, so no day's index level can be read back (the request to Cboe of 10 and 21 Oct, approved 4 Nov 2026:
    "Only aggregate statistics appear"). The blue upright line at zero is the index itself; the light band is
    within 1 point of it; left of zero, free data read low. Titled by the market first, then which ticker is the
    fund (the free estimate) and which is Cboe's official index (Marc Vinyard's review, 14 Nov 2026: "SPY vs VIX"
    did not say which was which).

    gaps: the fund's daily gaps (numbers, no dates). mae: the frozen scorer's mean |gap| for this fund (the build
    has checked it against these gaps). scale: (lo, hi, step) of the gap axis and counts: (top, step) of the
    day axis, both shared by the five panels, so the same bin is the same bar in every panel."""
    gaps = [float(g) for g in gaps]          # a dated row (date, gap) cannot become a number: refused here
    if not gaps:
        raise ValueError(f"{sym}: nothing to draw")
    lo, hi, step = scale
    top, cstep = counts
    if not lo <= 0 <= hi:
        raise ValueError(f"{sym}: zero must be on the gap axis {scale}")
    bins = bin_counts(gaps)
    if any(not (lo - 1e-9 <= k * BIN and (k + 1) * BIN <= hi + 1e-9) for k in bins):
        raise ValueError(f"{sym}: a bin runs off the shared gap axis {scale}")
    if max(bins.values()) > top:
        raise ValueError(f"{sym}: {max(bins.values())} days in one bin, above the shared day axis's {top}")
    # Four title lines, each label's box clear of the next by a pixel or more (Inter's ascent and descent are 0.97
    # and 0.24 em: 44 px between the 46 px title and a 34 px line touched, 14 Nov 2026) and of the day axis's top
    # label, whose box starts 20 px above the plot's top edge T.
    L, R, T, B = 70, 24, 210, 64

    def x(v):
        return L + (v - lo) * (w - L - R) / (hi - lo)

    def y(n):
        return h - B - n * (h - T - B) / top

    n = len(gaps)
    market = what[:1].upper() + what[1:]                 # "gold" -> "Gold"; "S&P 500" stays (str.capitalize would not)
    out = [text(0, 46, market, 46, weight=700, family=HEAD),
           text(0, 93, f"free estimate ({sym}) vs official index ({index})", 34),
           text(0, 136, f"off by {mae:.2f} on average", 34, fill=MUTE),
           text(0, 179, f"{within_one(gaps)} of {n} days within 1 point", 34, fill=MUTE),
           f'<rect x="{x(max(-1.0, lo)):.1f}" y="{T}" width="{x(min(1.0, hi)) - x(max(-1.0, lo)):.1f}" '
           f'height="{h - T - B}" fill="{BAND}"/>']
    c = 0
    while c <= top:
        out.append(f'<line x1="{L}" x2="{w - R}" y1="{y(c):.1f}" y2="{y(c):.1f}" stroke="{RULE}" stroke-width="2"/>')
        out.append(text(L - 12, y(c) + 11, str(c), 32, fill=MUTE, anchor="end"))
        c += cstep
    k = 0
    while lo + k * step <= hi + step * 1e-9:
        v = lo + k * step
        out.append(text(x(v), h - 10, "0" if abs(v) < step * 1e-9 else minus(f"{round(v, 2):+g}"), 32,
                        fill=MUTE, anchor="middle"))
        k += 1
    out += [rounded_bar(x(b * BIN) + 1, x((b + 1) * BIN) - x(b * BIN) - 2, y(0), y(m)) for b, m in sorted(bins.items())]
    out.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{T}" y2="{h - B}" stroke="{CBOE}" stroke-width="5"/>')
    # The subtraction's order, as the caption gives it, for a screen reader too (14 Nov 2026 review).
    return svg(w, h, f"{market}: days by gap, the free estimate ({sym}) minus Cboe's official index ({index}), in "
                     f"half-point bins; off by {mae:.2f} points on average", "".join(out))


def band_sd(band, vol, days=30):
    """Standard deviations of a `days`-day price move spanned by a ±band of strikes (vol annual, as 0.16)."""
    return band / (vol * math.sqrt(days / 365))


def lognormal_pdf(r, vol, days=30):
    """Density of the `days`-day price change r = S_T/S_0 - 1 under a driftless lognormal (E[S_T] = S_0)."""
    if r <= -1:
        return 0.0
    s = vol * math.sqrt(days / 365)
    z = (math.log1p(r) + s * s / 2) / s
    return math.exp(-z * z / 2) / ((1 + r) * s * math.sqrt(2 * math.pi))


def band_coverage(band, vol, days=30):
    """Share of `days`-day price moves inside ±band under the same lognormal: how much the band sees."""
    s = vol * math.sqrt(days / 365)

    def cdf(z):
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))

    return cdf((math.log1p(band) + s * s / 2) / s) - cdf((math.log1p(-band) + s * s / 2) / s)


def coverage_curves(calm, wild, band=0.10, w=1300, h=306):
    """Two 30-day price-move curves on one scale with the same ±band of strikes shaded and its edges drawn; the
    wild curve's tails beyond the band (what a fixed band leaves out) filled orange. Both curves solid, each
    labelled on the plot beside it (no legend). A model, not market data.
    calm, wild: (name, annual vol), e.g. ("S&P 500", 0.16), ("Crude oil", 0.59)."""
    # Margins trimmed 14 Nov 2026 (the H5 caveat beside section 4's verdicts needed a line); the plot keeps 188 px.
    L, R, T, B, span = 20, 20, 62, 56, 0.5
    xs = [-span + i * 2 * span / 400 for i in range(401)]
    top = max(lognormal_pdf(r, calm[1]) for r in xs) * 1.04

    def X(r):
        return L + (r + span) / (2 * span) * (w - L - R)

    def Y(p):
        return T + (1 - p / top) * (h - T - B)

    base = Y(0)
    out = [f'<rect x="{X(-band):.1f}" y="{T - 6:.1f}" width="{X(band) - X(-band):.1f}" height="{base - T + 6:.1f}" '
           f'fill="{BAND}"/>']
    for e in (-band, band):
        out.append(f'<line x1="{X(e):.1f}" x2="{X(e):.1f}" y1="{T - 6:.1f}" y2="{base:.1f}" stroke="{MUTE}" '
                   'stroke-width="2"/>')
    out.append(text(X(0), T - 22, f"±{band:.0%} strike band", 34, weight=700, anchor="middle"))
    for tail in ([r for r in xs if r <= -band], [r for r in xs if r >= band]):
        pts = " L".join(f"{X(r):.1f} {Y(lognormal_pdf(r, wild[1])):.1f}" for r in tail)
        out.append(f'<path d="M{X(tail[0]):.1f} {base:.1f} L{pts} L{X(tail[-1]):.1f} {base:.1f} Z" '
                   f'fill="{ORANGE}" fill-opacity="0.3"/>')
    for (name, vol), color in ((calm, MUTE), (wild, INK)):
        d = " L".join(f"{X(r):.1f} {Y(lognormal_pdf(r, vol)):.1f}" for r in xs)
        out.append(f'<path d="M{d}" fill="none" stroke="{color}" stroke-width="5"/>')
    out.append(f'<line x1="{L}" x2="{w - R}" y1="{base:.1f}" y2="{base:.1f}" stroke="{MUTE}" stroke-width="2"/>')
    for r in (-0.4, -0.2, 0.0, 0.2, 0.4):
        out.append(text(X(r), h - 16, minus(f"{r:+.0%}") if r else "0%", 32, fill=MUTE, anchor="middle"))
    # The calm curve's label sits left of the band, beside the only curve that reaches that high (inside the band,
    # the band's edge line would run through it); the wild one's just above its right shoulder, where the calm
    # curve has fallen to nothing.
    (cn, cv), (wn, wv) = calm, wild
    wy = Y(lognormal_pdf(band + 0.02, wv))                        # the wild curve falls to the right of here
    out += [text(X(-band) - 14, T + 40, f"{cn} (volatility {cv * 100:.0f}%)", 34, weight=700, anchor="end"),
            text(X(-band) - 14, T + 84, f"band sees {band_coverage(band, cv):.0%} of moves", 34, fill=MUTE,
                 anchor="end"),
            text(X(band + 0.02), wy - 68, f"{wn} (volatility {wv * 100:.0f}%)", 34, weight=700),
            text(X(band + 0.02), wy - 24, f"band sees {band_coverage(band, wv):.0%} of moves", 34, fill=MUTE)]
    return svg(w, h, f"30-day price-move curves for {calm[0]} and {wild[0]} with a ±{band:.0%} strike band",
               "".join(out))


def band_bars(bands, w=1300, row=112, bar=56):
    """Mean |gap| to Cboe by strike band (the 11 Sep 2026 calibration), the worst pair beside each.
    Every bar is the same thing, free data's gap, so every bar is orange; square on the baseline, rounded at the
    data end. bands: [(label '±10%', strikes, mean_abs_gap, worst_signed_gap, pair or None)]."""
    x0, r = 220, 8.0
    scale = (w - x0 - 330) / max(b[2] for b in bands)
    out = []
    for k, (band, n, mae, worst, pair) in enumerate(bands):
        y = 6 + k * row
        bw, yb = max(mae * scale, 2 * r), y + 12
        d = (f"M{x0:.1f} {yb:.1f} L{x0 + bw - r:.1f} {yb:.1f} Q{x0 + bw:.1f} {yb:.1f} {x0 + bw:.1f} {yb + r:.1f} "
             f"L{x0 + bw:.1f} {yb + bar - r:.1f} Q{x0 + bw:.1f} {yb + bar:.1f} {x0 + bw - r:.1f} {yb + bar:.1f} "
             f"L{x0:.1f} {yb + bar:.1f} Z")
        who = "worst: " + (f"{pair} " if pair else "") + minus(f"{worst:+.2f}")
        out += [text(x0 - 22, y + 52, band, 48, weight=700, family=HEAD, anchor="end"),
                text(x0 - 22, y + 98, f"{n} strikes", 32, fill=MUTE, anchor="end"),
                f'<path d="{d}" fill="{ORANGE}"/>',
                text(x0 + bw + 20, y + 55, f"{mae:.2f}", 54, weight=800, family=HEAD),
                text(x0 + bw + 20, y + 102, who, 32, fill=MUTE)]
    return svg(w, 6 + len(bands) * row, "Mean absolute gap to Cboe by strike band", "".join(out))


KEY_ALL, KEY_BOTH = "all far options", "only those with a buy offer on both feeds"


def dot(cx, cy, hollow, key=False):
    """The quote chart's dot: filled for all far options, hollow (white inside) for those with a buy offer on both
    feeds."""
    cls, fill = (' class="key"' if key else ""), ("#fff" if hollow else ORANGE)
    return f'<circle{cls} cx="{cx:.1f}" cy="{cy}" r="17" fill="{fill}" stroke="{ORANGE}" stroke-width="6"/>'


def quote_scale(feeds, bar, w=1300, row=108, top=60):
    """How far the free feed's mid sits from a professional feed's mid, in spreads (medians), on a 0-1 spread
    scale: one track per feed, a filled dot for all far options and a hollow one for only those both feeds bid (a
    subset). A key above the tracks names both dots, each drawn like the dots it names (Marc Vinyard's review, 14
    Nov 2026: the caption below was the only place that said which was which). The registered bar's tick is drawn
    last, over the dots, so a dot ON the bar still shows it. feeds: [(label, (all_value, shown), (both_bid_value,
    shown))] top to bottom."""
    L, R = 20, 60

    def X(v):
        return L + v * (w - L - R)

    out = [dot(L + 17, 30, False, key=True), text(L + 50, 42, KEY_ALL, 34),
           dot(L + 400, 30, True, key=True), text(L + 433, 42, KEY_BOTH, 34)]
    ticks = []
    for k, (label, (va, sa), (vb, sb)) in enumerate(feeds):
        y0 = top + k * row
        ty = y0 + 84
        out += [text(L, y0 + 36, label, 34),
                f'<line x1="{X(0):.1f}" x2="{X(1):.1f}" y1="{ty}" y2="{ty}" stroke="{RULE}" stroke-width="4"/>',
                dot(X(va), ty, False), dot(X(vb), ty, True),
                text(X(va) + 30, ty + 13, sa, 36, weight=700),
                text(X(vb) + 30, ty + 13, sb, 36, weight=700)]
        ticks.append(f'<line x1="{X(bar):.1f}" x2="{X(bar):.1f}" y1="{ty - 28}" y2="{ty + 28}" stroke="{INK}" '
                     'stroke-width="5"/>')
    axis = top + len(feeds) * row + 8
    out += ticks + [text(X(0), axis + 34, "0 (same price)", 32, fill=MUTE),
                    text(X(bar), axis + 34, "½ spread = the bar, set first", 32, weight=700, anchor="middle"),
                    text(X(bar), axis + 76, "at or under it passes", 32, fill=MUTE, anchor="middle"),
                    text(X(1), axis + 34, "1 spread", 32, fill=MUTE, anchor="end")]
    # The key's meanings reach a screen reader too (14 Nov 2026 review: the caption that said them is gone).
    return svg(w, axis + 92, "How far the free price sits from the professional one, in spreads (the gap between the "
                             "highest price a buyer offers and the lowest a seller asks); filled dots: "
                             f"{KEY_ALL}; hollow dots: {KEY_BOTH}", "".join(out))
