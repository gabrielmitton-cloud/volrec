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
BANDS = [("±10%", 20, 3.97, -12.37, "USO"), ("±20%", 30, 1.31, -4.39, None), ("±30%", 40, 0.59, -1.84, "USO")]
FEEDS = [("Bloomberg (179 far strikes; 134 bid on both feeds)", (0.33, "0.33"), (0.67, "0.67")),
         ("Full market, OPRA (466 far strikes; 402 bid on both feeds)", (0.5, "0.500"), (0.667, "0.667"))]


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
        self.assertIn("USO vs OVX", s)
        self.assertIn("crude oil · off by 1.74 on average", s)
        self.assertIn(f"{charts.within_one(G38)} of 38 days within 1 point", s)

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
        for t in ("S&amp;P 500 (volatility 16)", "Crude oil (volatility 59)", "band sees 97% of moves",
                  "band sees 45% of moves", "±10% strike band", "−40%", "+40%"):
            self.assertIn(t, s)
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
        for t in ("3.97", "1.31", "0.59", "worst: USO −12.37", "worst: −4.39", "40 strikes"):
            self.assertIn(t, s)
        ends = [max(x for x, _ in pts) for pts in b]
        self.assertEqual(ends, sorted(ends, reverse=True))               # a longer bar is a bigger gap
        for pts in b:                                                     # square at the baseline, rounded at the end
            self.assertEqual(sum(1 for x, _ in pts if x == pts[0][0]), 2)
            self.assertEqual(pts[0][0], min(x for x, _ in pts))


    def test_lengths_in_proportion(self):
        # Independent arithmetic: the longest bar (3.97) spans 1300 - 220 - 330 = 750 px from x = 220.
        ends = [max(x for x, _ in pts) - 220 for pts in bars(charts.band_bars(BANDS))]
        for got, (_, _, mae, _, _) in zip(ends, BANDS, strict=True):
            self.assertAlmostEqual(got, mae * 750 / 3.97, delta=0.1)


class QuoteScale(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
