"""Tests for poster/charts.py: every shape inside its chart, no text below the poster's 24 pt floor, text unlikely
to run past the edge, the colours meaning the same thing in every chart, one scale shared by the main chart's
five panels (counts of days by gap: aggregates only), and the bell-curve numbers right. Stdlib only; writes nothing.

    .../python3 poster/test_charts.py
"""
import html
import math
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts  # noqa: E402

VB = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')
FONT = re.compile(r'font-size="([\d.]+)"')
XY = re.compile(r'\b(?:x|x1|x2|cx)="(-?[\d.]+)"|\b(?:y|y1|y2|cy)="(-?[\d.]+)"')
PATH = re.compile(r' d="([^"]+)"')
TEXT = re.compile(r'<text x="(-?[\d.]+)" y="[^"]*" [^>]*font-size="([\d.]+)"[^>]*text-anchor="(\w+)">([^<]*)</text>')
LINE = re.compile(r'<line x1="([\d.]+)" x2="([\d.]+)" y1="([\d.]+)" y2="([\d.]+)" stroke="([^"]+)"')


def check_svg(case, svg):
    """Every font >= 32 px; every coordinate and path point inside the viewBox; text likely inside it too
    (half an em per character, a lenient estimate for Inter)."""
    w, h = map(float, VB.search(svg).groups())
    sizes = [float(s) for s in FONT.findall(svg)]
    case.assertTrue(sizes, "no text at all")
    case.assertGreaterEqual(min(sizes), charts.MIN_FONT)
    for xs, ys in XY.findall(svg):
        if xs:
            case.assertTrue(-0.5 <= float(xs) <= w + 0.5, f"x {xs} outside 0..{w}")
        if ys:
            case.assertTrue(-0.5 <= float(ys) <= h + 0.5, f"y {ys} outside 0..{h}")
    for d in PATH.findall(svg):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
        for x, y in zip(nums[0::2], nums[1::2]):
            case.assertTrue(-0.5 <= x <= w + 0.5 and -0.5 <= y <= h + 0.5, f"path point {x},{y} outside")
    for x, size, anchor, s in TEXT.findall(svg):
        x, width = float(x), 0.5 * float(size) * len(html.unescape(s))
        lo, hi = {"start": (x, x + width), "end": (x - width, x), "middle": (x - width / 2, x + width / 2)}[anchor]
        case.assertTrue(lo >= -2 and hi <= w + 2, f"text {s!r} likely runs outside ({lo:.0f}..{hi:.0f} of {w:.0f})")


def bars(svg):
    """Each orange bar's points, in drawing order (bars are paths of coordinate pairs)."""
    out = []
    for d in re.findall(r'<path d="([^"]+)" fill="%s"/>' % charts.ORANGE, svg):
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
        out.append(list(zip(nums[0::2], nums[1::2])))
    return out


def weekdays(start, end):
    d, out = date.fromisoformat(start), []
    while d <= date.fromisoformat(end):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


# The main chart's shape: 38 readings from 14 Sep to 6 Nov 2026, 16 and 28 Sep missing.
DAYS38 = [d for d in weekdays("2026-09-14", "2026-11-06") if d not in ("2026-09-16", "2026-09-28")]
GAPS38 = [(d, round(-1.6 + 1.8 * ((i * 7) % 11 - 5) / 5, 2)) for i, d in enumerate(DAYS38)]
SCALE = (-6, 4, 2)
BANDS = [("±10%", 20, 3.97), ("±20%", 30, 1.31), ("±30%", 40, 0.59)]
FEEDS = [("Bloomberg (179 far options; 134 with a buy offer on both)", (0.33, "0.33"), (0.67, "0.67")),
         ("Full market, OPRA (466 far options; 402 with a buy offer on both)", (0.5, "0.500"), (0.667, "0.667"))]


PLACED = re.compile(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>')      # a text with its position
DATA_DOT = re.compile(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="17" fill="([^"]+)"')


def quote_bindings(case, svg, feeds):
    """18 Nov 2026 (Astra 2's poster review, #11): each feed's label, its track, each dot's position and the number
    printed beside that dot, bound together. The label names the track 48 px below it (its baseline + 48); on that
    track the filled dot sits at 20 + all x 1220 and the hollow at 20 + both x 1220, and each one's number is printed
    30 px right of it, 13 px down."""
    texts = [(float(x), float(y), html.unescape(v)) for x, y, v in PLACED.findall(svg)]
    dots = [(float(x), float(y), f) for x, y, f in DATA_DOT.findall(svg)]
    for label, (va, sa), (vb, sb) in feeds:
        at = [(x, y) for x, y, v in texts if v == label]
        case.assertEqual(len(at), 1, label)
        track = at[0][1] + 48
        on = {f: x for x, y, f in dots if abs(y - track) < 0.05}
        case.assertEqual(set(on), {charts.ORANGE, "#fff"}, label)
        for fill, v, shown in ((charts.ORANGE, va, sa), ("#fff", vb, sb)):
            case.assertAlmostEqual(on[fill], 20 + v * 1220, delta=0.05, msg=label)
            beside = [w for x, y, w in texts if abs(x - (on[fill] + 30)) < 0.05 and abs(y - (track + 13)) < 0.05]
            case.assertEqual(beside, [shown], label)


def coverage_bindings(case, svg, want):
    """Each market's coverage line sits directly under its own name (same x, 44 px down). want: {name: coverage}."""
    texts = [(float(x), float(y), html.unescape(v)) for x, y, v in PLACED.findall(svg)]
    for name, cover in want.items():
        at = [(x, y) for x, y, v in texts if v == name]
        case.assertEqual(len(at), 1, name)
        under = [v for x, y, v in texts if abs(x - at[0][0]) < 0.05 and abs(y - (at[0][1] + 44)) < 0.05]
        case.assertEqual(under, [cover], name)


class Steps(unittest.TestCase):
    def test_nice_step(self):
        self.assertEqual(charts.nice_step(14.2), 5)
        self.assertEqual(charts.nice_step(9.5), 2.5)
        self.assertEqual(charts.nice_step(6.1), 2)
        self.assertEqual(charts.nice_step(1.0), 0.25)

    def test_text_below_the_floor_refuses(self):
        with self.assertRaises(ValueError):
            charts.text(0, 0, "tiny", 24)


class SharedScale(unittest.TestCase):
    def test_round_numbers_with_zero_inside(self):
        self.assertEqual(charts.shared_scale([-5.21, 2.31, 0.4]), (-6, 4, 2))     # the five pairs to 6 Nov
        self.assertEqual(charts.shared_scale([0.2, 0.9]), (0, 1.0, 0.25))          # zero kept on the scale


G38 = [g for _, g in GAPS38]


def xticks(svg):
    """{label: x} of the gap axis's labels (centred under their value), e.g. {"0": 563.0, "+2": 732.2}."""
    return {html.unescape(t): float(x) for x, _, anchor, t in TEXT.findall(svg)
            if anchor == "middle" and re.fullmatch(r"[−+]?\d+", html.unescape(t))}


def yticks(svg):
    """{count: y of its gridline}: the day axis's labels (right-aligned at the left) matched to the gridlines,
    top to bottom, so a bar's height can be read in days."""
    labels = sorted((int(m[1]) for m in re.finditer(r'text-anchor="end">(\d+)</text>', svg)), reverse=True)
    grid = sorted(float(m[1]) for m in re.finditer(
        r'<line x1="[\d.]+" x2="[\d.]+" y1="([\d.]+)" y2="\1" stroke="%s"' % charts.RULE, svg))
    assert len(labels) == len(grid), (labels, grid)
    return dict(zip(labels, grid))


def per_point(svg):
    x = xticks(svg)
    return x["0"], (x["+2"] - x["0"]) / 2


class Histogram(unittest.TestCase):
    """The main chart: per fund, how many days the free estimate landed at each distance from Cboe's index, in
    half-point bins. Counts only - no date and no single day's value is drawn (the request to Cboe of 10 and
    21 Oct, approved 4 Nov: "Only aggregate statistics appear")."""

    def test_bins_are_half_point_counts(self):
        self.assertEqual(charts.bin_counts([0.1, 0.2, -0.3, 1.2, -1.0, 0.5]), {0: 2, -1: 1, 2: 1, -2: 1, 1: 1})

    def test_within_one_point_matches_the_bins_inside_the_band(self):
        self.assertEqual(charts.within_one([-1.0, 0.99, 1.0, -1.01, 0.0]), 3)     # -1 <= gap < 1

    def test_count_scale(self):
        self.assertEqual(charts.count_scale(21), (25, 5))
        self.assertEqual(charts.count_scale(38), (40, 10))
        self.assertEqual(charts.count_scale(3), (3, 1))

    def test_one_bar_per_bin_inside_the_frame(self):
        s = charts.gap_histogram("USO", "OVX", "crude oil", G38, 1.7388, SCALE, (20, 5))
        check_svg(self, s)
        self.assertEqual(len(bars(s)), len(charts.bin_counts(G38)))
        # Marc Vinyard, 14 Nov 2026: "USO vs OVX" did not say which ticker is which. The market first, then the
        # fund whose free quotes make the estimate and Cboe's official index for that market.
        self.assertIn(">Crude oil</text>", s)
        self.assertIn("free estimate (USO) vs official index (OVX)", s)
        self.assertIn("off by 1.74 on average", s)
        self.assertIn(f"{charts.within_one(G38)} of 38 days within 1 point", s)
        self.assertNotIn("USO vs OVX", s)
        # A screen reader hears the subtraction's order too (14 Nov 2026 review: the new name had dropped it).
        name = html.unescape(re.search(r'aria-label="([^"]*)"', s)[1])
        self.assertEqual(name, "Crude oil: days by gap, the free estimate (USO) minus Cboe's official index (OVX), in "
                               "half-point bins; off by 1.74 points on average")

    def test_the_market_is_named_as_written(self):
        # Only the first letter is raised: "S&P 500" must not become "S&p 500" (str.capitalize would).
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        self.assertIn(">S&amp;P 500</text>", s)
        self.assertIn("free estimate (SPY) vs official index (VIX)", s)
        self.assertIn(">Gold</text>", charts.gap_histogram("GLD", "GVZ", "gold", [0.1, -0.2], 0.15, SCALE, (10, 5)))

    def test_no_day_can_be_read_back(self):
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}|>(Sep|Oct|Nov)<", s))
        with self.assertRaises((TypeError, ValueError)):                  # dated rows are refused, not drawn
            charts.gap_histogram("SPY", "VIX", "S&P 500", [("2026-11-02", 0.2)], 0.2, SCALE, (20, 5))

    def test_bar_heights_are_the_day_counts(self):
        s = charts.gap_histogram("GLD", "GVZ", "gold", [0.1, 0.2, 0.3, -0.6, -2.2], 0.68, SCALE, (10, 5))
        y = yticks(s)
        self.assertEqual(sorted(y), [0, 5, 10])
        y0, per_day = y[0], (y[0] - y[10]) / 10
        tops = sorted(round((y0 - min(py for _, py in b)) / per_day, 2) for b in bars(s))
        self.assertEqual(tops, [1, 1, 3])

    def test_each_bar_sits_in_its_half_point_bin(self):
        gaps = [0.1, 0.2, 0.3, -0.6, -2.2]
        s = charts.gap_histogram("GLD", "GVZ", "gold", gaps, 0.68, SCALE, (10, 5))
        x0, pp = per_point(s)
        got = []
        for pts in bars(s):
            left, right = min(px for px, _ in pts), max(px for px, _ in pts)
            lo_edge = math.floor((left - x0) / (pp / 2) + 1e-6) * 0.5
            self.assertAlmostEqual(left, x0 + lo_edge * pp + 1, delta=0.15)       # a 2 px gap between bars
            self.assertAlmostEqual(right, x0 + (lo_edge + 0.5) * pp - 1, delta=0.15)
            got.append(lo_edge)
        self.assertEqual(sorted(got), [-2.5, -1.0, 0.0])                  # -2.2, -0.6, and 0.1-0.3

    def test_band_is_one_point_each_side_of_zero(self):
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        x0, pp = per_point(s)
        rects = re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="[\d.]+" fill="%s"'
                           % charts.BAND, s)
        self.assertEqual(len(rects), 1)
        self.assertAlmostEqual(float(rects[0][0]), x0 - pp, delta=0.15)
        self.assertAlmostEqual(float(rects[0][1]), 2 * pp, delta=0.15)

    def test_known_coordinates(self):
        # Independent arithmetic (Astra, 8 Nov: a +/-2 band or a non-linear axis must fail): 940 px wide with
        # margins of 70 and 24 leaves 846 px for the 10 points of (-6, 4): 84.6 px a point from x = 70.
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        x = xticks(s)
        for label, v in (("−6", -6), ("−4", -4), ("−2", -2), ("0", 0), ("+2", 2), ("+4", 4)):
            self.assertAlmostEqual(x[label], 70 + (v + 6) * 84.6, delta=0.05)
        (bx, bw), = re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="[\d.]+" fill="%s"'
                               % charts.BAND, s)
        self.assertAlmostEqual(float(bx), 70 + 5 * 84.6, delta=0.05)              # -1 point
        self.assertAlmostEqual(float(bw), 2 * 84.6, delta=0.05)                    # to +1

    def test_band_stops_at_the_axis_end(self):
        # Every gap above zero: the axis starts at 0, so the band runs from there to +1 and no further.
        s = charts.gap_histogram("GLD", "GVZ", "gold", [0.2, 0.6], 0.4, (0, 1.0, 0.25), (3, 1))
        (bx, bw), = re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)" height="[\d.]+" fill="%s"'
                               % charts.BAND, s)
        self.assertAlmostEqual(float(bx), 70, delta=0.05)
        self.assertAlmostEqual(float(bw), 846, delta=0.05)

    def test_gap_axis_labels_on_the_shared_scale(self):
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        self.assertEqual(list(xticks(s)), ["−6", "−4", "−2", "0", "+2", "+4"])
        x = list(xticks(s).values())
        self.assertAlmostEqual(x[1] - x[0], x[-1] - x[-2], places=1)     # evenly spaced: linear

    def test_zero_line_is_cboe_upright_and_over_the_bars(self):
        s = charts.gap_histogram("SPY", "VIX", "S&P 500", G38, 0.4458, SCALE, (20, 5))
        blue = [m for m in LINE.finditer(s) if m[5] == charts.CBOE]
        self.assertEqual(len(blue), 1)                                     # the index itself: the zero line
        self.assertEqual(blue[0][1], blue[0][2])
        self.assertAlmostEqual(float(blue[0][1]), per_point(s)[0], delta=0.15)
        self.assertGreater(blue[0].start(), s.rindex(f'fill="{charts.ORANGE}"'))

    def test_reading_low_is_left_of_zero(self):
        s = charts.gap_histogram("IWM", "RVX", "Russell 2000", [2.0, -3.0], 2.5, SCALE, (10, 5))
        x0 = per_point(s)[0]
        lefts = sorted(min(px for px, _ in b) for b in bars(s))
        self.assertLess(lefts[0], x0 - 100)                               # read low: left of the zero line
        self.assertGreater(lefts[1], x0 + 100)                            # read high: right of it

    def test_the_same_bin_is_the_same_bar_in_every_panel(self):
        a = charts.gap_histogram("GLD", "GVZ", "gold", [-0.7, 0.3], 0.5, SCALE, (10, 5))
        b = charts.gap_histogram("USO", "OVX", "crude oil", [-0.7, -5.0], 2.85, SCALE, (10, 5))
        self.assertIn(sorted(bars(a))[0], sorted(bars(b)))                 # the -0.7 bin, one day, in both
        grid = re.compile(r'<line x1="[\d.]+" x2="[\d.]+" y1="([\d.]+)" y2="\1" stroke="%s"' % charts.RULE)
        self.assertEqual(grid.findall(a), grid.findall(b))

    def test_refuses(self):
        with self.assertRaises(ValueError):
            charts.gap_histogram("GLD", "GVZ", "gold", [], 0.0, SCALE, (10, 5))           # nothing to draw
        with self.assertRaises(ValueError):
            charts.gap_histogram("GLD", "GVZ", "gold", [1.5], 1.5, (1, 3, 1), (10, 5))    # zero off the scale
        with self.assertRaises(ValueError):
            charts.gap_histogram("GLD", "GVZ", "gold", [4.0], 4.0, (-2, 4, 2), (10, 5))   # its bin [4, 4.5) runs off
        with self.assertRaises(ValueError):
            charts.gap_histogram("GLD", "GVZ", "gold", [0.1] * 11, 0.1, SCALE, (10, 5))   # more days than the axis


class WeekdaySlot(unittest.TestCase):
    def test_weekdays_counted_from_the_first(self):
        self.assertEqual(charts.weekday_slot("2026-09-14", "2026-11-06"), 39)              # 40 weekdays
        self.assertEqual(charts.weekday_slot("2026-11-06", "2026-11-09"), 1)               # Fri to Mon
        self.assertEqual(len(DAYS38), 38)


class Coverage(unittest.TestCase):
    WANT = {"S&P 500 (volatility 16%)": "band sees 97% of moves", "Crude oil (volatility 59%)": "band sees 45% of moves"}

    def test_each_share_sits_under_its_own_market(self):
        # 18 Nov 2026 (Astra 2's poster review, #11): both percentages anywhere in the SVG passed with them swapped.
        # 97% and 45% are the hand-worked shares of test_share_of_moves_inside_the_band.
        s = charts.coverage_curves(("S&P 500", 0.16), ("Crude oil", 0.59))
        coverage_bindings(self, s, self.WANT)
        a, b = ">band sees 97% of moves<", ">band sees 45% of moves<"
        swapped = s.replace(a, "\0").replace(b, a).replace("\0", b)
        self.assertNotEqual(swapped, s)
        with self.assertRaises(AssertionError):
            coverage_bindings(self, swapped, self.WANT)

    def test_band_in_standard_deviations(self):
        self.assertEqual(f"{charts.band_sd(0.10, 0.16):.1f}", "2.2")
        self.assertEqual(f"{charts.band_sd(0.10, 0.59):.1f}", "0.6")

    def test_share_of_moves_inside_the_band(self):
        self.assertEqual(f"{charts.band_coverage(0.10, 0.16):.0%}", "97%")
        self.assertEqual(f"{charts.band_coverage(0.10, 0.59):.0%}", "45%")

    def test_density_integrates_to_one_with_no_drift(self):
        step = 0.0005
        grid = [-0.9995 + i * step for i in range(int(4.0 / step))]
        for vol in (0.16, 0.59):
            mass = sum(charts.lognormal_pdf(r, vol) for r in grid) * step
            mean = sum(r * charts.lognormal_pdf(r, vol) for r in grid) * step
            inside = sum(charts.lognormal_pdf(r, vol) for r in grid if -0.10 <= r <= 0.10) * step
            self.assertAlmostEqual(mass, 1.0, places=3)
            self.assertAlmostEqual(mean, 0.0, places=3)
            self.assertAlmostEqual(inside, charts.band_coverage(0.10, vol), places=2)

    def test_chart(self):
        s = charts.coverage_curves(("S&P 500", 0.16), ("Crude oil", 0.59))
        check_svg(self, s)
        # 14 Nov 2026 review: a bare "volatility 16" gave no unit; it is a percentage a year, as the VIX is.
        for t in ("S&amp;P 500 (volatility 16%)", "Crude oil (volatility 59%)", "band sees 97% of moves",
                  "band sees 45% of moves", "±10% strike band", "−40%", "+40%"):
            self.assertIn(t, s)
        self.assertNotRegex(s, r"volatility \d+\)")
        self.assertEqual(s.count('fill-opacity="0.3"'), 2)               # oil's two tails beyond the band
        self.assertNotIn("stroke-dasharray", s)                           # both curves solid, labelled on the plot
        edges = [m for m in LINE.finditer(s) if m[1] == m[2]]
        self.assertEqual(len(edges), 2)                                   # the band's two edges, drawn


class BandBars(unittest.TestCase):
    def test_bars(self):
        s = charts.band_bars(BANDS)
        check_svg(self, s)
        b = bars(s)
        self.assertEqual(len(b), 3)                                       # every bar is the same thing: the gap
        for t in ("3.97", "1.31", "0.59", "20 strikes", "40 strikes"):
            self.assertIn(t, s)
        # 18 Nov 2026 (Astra 2's review, HIGH): one fund's signed gap on one named day gives that day's index close
        # back; the chart shows the five-pair means only. No fund, no "worst", no signed number.
        self.assertNotIn("worst", s)
        self.assertNotRegex(s, r"\b(SPY|QQQ|IWM|GLD|USO)\b")
        self.assertNotRegex(s, r"[−+-]\d+\.\d")
        ends = [max(x for x, _ in pts) for pts in b]
        self.assertEqual(ends, sorted(ends, reverse=True))               # a longer bar is a bigger gap
        for pts in b:                                                     # square at the baseline, rounded at the end
            self.assertEqual(sum(1 for x, _ in pts if x == pts[0][0]), 2)
            self.assertEqual(pts[0][0], min(x for x, _ in pts))


    def test_lengths_in_proportion(self):
        # Independent arithmetic: the longest bar (3.97) spans 1300 - 220 - 330 = 750 px from x = 220.
        ends = [max(x for x, _ in pts) - 220 for pts in bars(charts.band_bars(BANDS))]
        for got, (_, _, mae) in zip(ends, BANDS, strict=True):
            self.assertAlmostEqual(got, mae * 750 / 3.97, delta=0.1)


class QuoteScale(unittest.TestCase):
    def test_each_feed_label_dot_and_number_are_bound(self):
        s = charts.quote_scale(FEEDS, 0.5)
        quote_bindings(self, s, FEEDS)

    def test_the_bindings_see_swapped_numbers_or_feeds(self):
        # Known answers: the two printed medians of one track swapped (dots and labels in place), and the two feeds'
        # labels swapped (dots and numbers in place).
        s = charts.quote_scale(FEEDS, 0.5)
        (la, (_, a1), (_, a2)), (lb, _, _) = FEEDS
        n1, n2 = f'>{a1}</text>', f'>{a2}</text>'
        self.assertEqual((s.count(n1), s.count(n2)), (1, 1))
        numbers = s.replace(n1, "\0").replace(n2, n1).replace("\0", n2)
        e1, e2 = f">{html.escape(la, quote=False)}</text>", f">{html.escape(lb, quote=False)}</text>"
        feeds = s.replace(e1, "\0").replace(e2, e1).replace("\0", e2)
        for bad in (numbers, feeds):
            self.assertNotEqual(bad, s)
            with self.assertRaises(AssertionError):
                quote_bindings(self, bad, FEEDS)

    def test_linear_from_zero_to_one_spread(self):
        # Independent arithmetic: 1300 px wide, margins 20 and 60, so one spread is 1220 px from x = 20.
        s = charts.quote_scale(FEEDS, 0.5)
        cx = sorted(float(c) for c in re.findall(r'<circle cx="([\d.]+)"', s))
        for got, v in zip(cx, sorted([0.33, 0.67, 0.5, 0.667]), strict=True):
            self.assertAlmostEqual(got, 20 + v * 1220, delta=0.05)
        self.assertEqual([float(m[1]) for m in LINE.finditer(s) if m[1] == m[2]], [630.0, 630.0])   # the bar, 0.5


    def test_scale(self):
        s = charts.quote_scale(FEEDS, 0.5)
        check_svg(self, s)
        dots = re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="([^"]+)"', s)
        self.assertEqual(len(dots), 4)
        rows = {}
        for cx, cy, fill in dots:
            rows.setdefault(cy, []).append((float(cx), fill == "#fff"))
        self.assertEqual(len(rows), 2)                                    # one track per feed
        for pts in rows.values():                                         # filled: all far strikes; hollow: both bid
            (x_all, h_all), (x_both, h_both) = pts
            self.assertEqual((h_all, h_both), (False, True))
            self.assertLess(x_all, x_both)
        ticks = [m for m in LINE.finditer(s) if m[1] == m[2]]
        self.assertEqual(len(ticks), 2)
        opra_all = float(dots[2][0])
        self.assertEqual({float(m[1]) for m in ticks}, {opra_all})       # 0.500 sits ON the bar
        self.assertGreater(min(m.start() for m in ticks), s.rindex("<circle"))   # the bar drawn over the dots
        for t in ("½ spread = the bar, set first", "at or under it passes", "0 (same price)", "1 spread"):
            self.assertIn(t, s)

    def dots_bound(self, s):
        # Each data dot is bound to its value, row by row, whatever the drawing order (14 Nov 2026 review: a set of
        # fills alone would pass with the meanings swapped). FEEDS: filled = all far options, hollow = those with a
        # buy offer on both feeds. One spread is 1220 px from x = 20.
        rows = {}
        for cx, cy, fill in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="([^"]+)"', s):
            rows.setdefault(float(cy), {})[fill] = float(cx)
        want = [{charts.ORANGE: 0.33, "#fff": 0.67}, {charts.ORANGE: 0.5, "#fff": 0.667}]
        self.assertEqual(len(rows), len(want))
        for (_, got), exp in zip(sorted(rows.items()), want, strict=True):
            self.assertEqual(set(got), set(exp))
            for fill, v in exp.items():
                self.assertAlmostEqual(got[fill], 20 + v * 1220, delta=0.05)

    def test_swapped_dot_meanings_are_caught(self):
        # A known answer for the binding: the data dots' fills swapped, the key left as it is.
        s = charts.quote_scale(FEEDS, 0.5)
        swapped = re.sub(r'(<circle cx="[\d.]+" cy="[\d.]+" r="[\d.]+" fill=")([^"]+)"',
                         lambda m: m[1] + ("#fff" if m[2] == charts.ORANGE else charts.ORANGE) + '"', s)
        self.assertNotEqual(swapped, s)
        self.assertEqual(swapped.count('class="key"'), s.count('class="key"'))
        with self.assertRaises(AssertionError):
            self.dots_bound(swapped)

    def key_bound(self, s):
        # Each key label is bound to the key dot just left of it, on its line (follow-up review, 14 Nov 2026: both
        # labels present anywhere would pass with the two swapped). A label starts 33 px right of its dot's centre.
        dots = [(float(cx), float(cy), fill) for cx, cy, fill in
                re.findall(r'<circle class="key" cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="([^"]+)"', s)]
        labels = [(float(x), float(y), html.unescape(t)) for x, y, t in
                  re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>', s)]
        self.assertEqual(len(dots), 2)
        got = {}
        for cx, cy, fill in dots:
            beside = [t for x, y, t in labels if 0 < x - cx <= 60 and abs(y - cy) <= 20]
            self.assertEqual(len(beside), 1, "each key dot has one label beside it")
            got[fill] = beside[0]
        self.assertEqual(got, {charts.ORANGE: charts.KEY_ALL, "#fff": charts.KEY_BOTH})

    def test_swapped_key_labels_are_caught(self):
        # A known answer for the binding: the key's two labels swapped; the dots and the spoken name left as they are.
        s = charts.quote_scale(FEEDS, 0.5)
        a, b = f">{charts.KEY_ALL}</text>", f">{charts.KEY_BOTH}</text>"
        swapped = s.replace(a, "\0").replace(b, a).replace("\0", b)
        self.assertNotEqual(swapped, s)
        self.dots_bound(swapped)
        with self.assertRaises(AssertionError):
            self.key_bound(swapped)

    def test_the_key_items_do_not_touch(self):
        # 18 Nov 2026 (poster v3): the first key label grew to "far options both feeds quoted" (Astra 2, #5) and ran
        # into the second key dot (the print check's overlap test sees text only; on the page the ring sat 6 units
        # from the label). The second dot's ring must clear the first label by 30 units, by the half-an-em estimate
        # check_svg uses (Inter measures about 0.48 em per character here, so the estimate is the longer one).
        s = charts.quote_scale(FEEDS, 0.5)
        dots = [(float(cx), float(r)) for cx, r in
                re.findall(r'<circle class="key" cx="([\d.]+)" cy="[\d.]+" r="([\d.]+)"', s)]
        x, size = re.search(r'<text x="([\d.]+)" y="[\d.]+" font-family="[^"]*" font-size="([\d.]+)"[^>]*>'
                            + re.escape(charts.KEY_ALL) + "</text>", s).groups()
        label_end = float(x) + 0.5 * float(size) * len(charts.KEY_ALL)
        ring_left = dots[1][0] - dots[1][1] - 3                    # the ring's stroke is 6 wide
        self.assertGreaterEqual(ring_left - label_end, 30, (ring_left, label_end))

    def test_a_key_names_both_dots(self):
        # Marc Vinyard, 14 Nov 2026: the filled and hollow dots were explained only in a caption below the chart.
        # The chart now carries its own key, above the tracks, each key dot drawn like the dots it names.
        s = charts.quote_scale(FEEDS, 0.5)
        check_svg(self, s)
        keys = re.findall(r'<circle class="key" cx="[\d.]+" cy="([\d.]+)" r="[\d.]+" fill="([^"]+)" '
                          r'stroke="([^"]+)"', s)
        self.assertEqual([(fill, stroke) for _, fill, stroke in keys], [(charts.ORANGE, charts.ORANGE),
                                                                         ("#fff", charts.ORANGE)])
        data = re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="[\d.]+" fill="([^"]+)"', s)
        self.assertEqual({fill for _, _, fill in data}, {charts.ORANGE, "#fff"})   # the same two looks as the data
        self.assertLess(max(float(y) for y, _, _ in keys), min(float(y) for _, y, _ in data))
        self.dots_bound(s)
        self.key_bound(s)
        # Plain words (Marc, 14 Nov): "no bid" became a buy offer, not "a buyer": a feed showing no buy offer does
        # not show that no buyer exists (14 Nov 2026 review).
        # 18 Nov 2026 (Astra 2's poster review, #5): the filled dots are the far options both feeds quoted (H5's rule
        # compares matched contracts only), never "all far options".
        self.assertEqual((charts.KEY_ALL, charts.KEY_BOTH),
                         ("far options both feeds quoted", "only those with a buy offer on both feeds"))
        # The key's meanings reach a screen reader too, not only the eye.
        name = html.unescape(re.search(r'aria-label="([^"]*)"', s)[1])
        self.assertIn(f"filled dots: {charts.KEY_ALL}; hollow dots: {charts.KEY_BOTH}", name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
