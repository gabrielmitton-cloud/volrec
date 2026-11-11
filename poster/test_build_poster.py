"""The poster's readers and chips against fixtures made by the project's own writers.

    .../python3 poster/test_build_poster.py

Every verdict fixture is produced by tools/record_verdict.py's own functions (h5e_score, block_h5e(final=True),
block_h7, append_result) or tools/h3_scorer.py's (parse, score, report), appended to the REAL hypothesis files,
so a change in the writer's wording breaks these tests rather than the poster on print day. Covered: HOLDS and
FAILS, the block-absent case (the chip says when the reading is due), malformed blocks (the reader raises, never
guesses), the main chart's daily series and its cross-check against the scorer's printed numbers (figures rounded
once, from full precision), the reading of record only once 11 Nov's data is in, the main chart getting gaps and
never Cboe's own values, every status-table hypothesis on the poster as a chip, the assembled page's claims, and
the bell curves' numbers against the README's sentence.
Stdlib only; reads the repository, writes only to temporary folders.
"""
import html
import json
import re
import sys
import tempfile
import unittest
import zlib
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "poster"), str(ROOT / "tools"), str(ROOT)]
import build_poster as bp          # noqa: E402
import record_verdict as rv        # noqa: E402

READ_ON = date(2026, 11, 12)       # the day the finals fall due (record_verdict H5E_FINAL_DUE, H7_DUE)


def trading_days(start, end):
    d, out = date.fromisoformat(start), []
    while d <= date.fromisoformat(end):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def fake_modelfree(days, gap_of=lambda g, i: g + 0.01 * (i % 3), base=0.0):
    """Text in modelfree.py's row form (date, symbol, ours, cboe, gap, legs, n) for the five benchmarked pairs,
    read by h3_scorer's own row pattern. gap_of(base gap, day index) sets each day's gap; base shifts every index
    level (so a test can pick levels no other number on the page shares)."""
    lines = ["risk-free (DGS1MO): 3.910%", "date        sym       ours    cboe     gap      legs    n"]
    for i, d in enumerate(days):
        for sym, lvl, g in (("GLD", 25.0, -0.2), ("IWM", 20.0, 0.3), ("QQQ", 21.0, -0.4), ("SPY", 16.0, -0.1),
                            ("USO", 58.0, -1.5)):
            cb, gap = base + lvl + 0.1 * i, gap_of(g, i)
            lines.append(f"{d}  {sym:<5} {cb + gap:10.6f} {cb:10.6f} {gap:+10.6f}   25d/32d   75")
    return "\n".join(lines) + "\n"


def scored(out):
    """The frozen scorer's report on a modelfree.py output, read by the poster's own reader."""
    import h3_scorer as hs
    return bp.parse_h3(hs.report(hs.score(hs.parse(out))))


def h5e_rows(skip_gap, reg_gap):
    """modelfree --wide's H5e rows as rv.parse_h5e returns them: (date, ovx, reg_gap, skip_gap, counted)."""
    return [(d, 58.0 + (i % 5) * 0.4, reg_gap + 0.01 * (i % 3), skip_gap * (1 if i % 2 else -1), True)
            for i, d in enumerate(trading_days(rv.H5E_START, rv.H5E_END))]


def base_h5():
    """The real H5 file, without any FINAL block (it holds the 8 Oct first verdict, which must NOT be read)."""
    text = rv.H5.read_text()
    return text.split(rv.MARK_H5E_FINAL)[0].rstrip("\n") + "\n"


def base_h7():
    text = rv.H7.read_text()
    if rv.MARK_H7 in text:                     # after 12 Nov: drop the real block to rebuild the "absent" form
        i = text.index(rv.MARK_H7)
        j = text.find("\n## ", i)
        text = text[:i] + text[j:]
    return text


def with_h5e_final(rows, first_verdict="FAILS"):
    sc = rv.h5e_score(rows, last=rv.H5E_END)
    blk = rv.block_h5e(sc, "3.910", [], READ_ON, True, first_verdict, ["2026-09-28"])
    return sc, rv.append_result(base_h5(), blk)


def h7_v(uso_a, gld_a, gld_b, uso_c=0.05, n=22):
    """rv.parse_h7's dict form: {key: (days, value)}."""
    return {"USO_a": (n, uso_a), "GLD_a": (n, gld_a), "GLD_b": (n, gld_b), "USO_c": (n, uso_c)}


class H5eFinal(unittest.TestCase):
    def test_holds(self):
        sc, text = with_h5e_final(h5e_rows(skip_gap=0.31, reg_gap=-1.1))
        self.assertTrue(sc["holds"])
        got = bp.h5e_final(text)
        self.assertEqual(got, {"verdict": "HOLDS", "mae": f"{sc['mae']:.2f}", "closer": str(sc["closer"]),
                               "n": str(sc["n"])})
        self.assertNotEqual(got["mae"], "0.90")          # the first verdict's figure: not the block read
        c = bp.h5e_chip(got)
        self.assertEqual((c["kind"], c["verdict"]), ("ok", "holds (final)"))
        # The recorded first verdict stays beside a final one, so a final HOLDS never hides it (8 Nov review).
        self.assertEqual(c["number"], f"{sc['mae']:.2f} (bar < 0.5); closer on {sc['closer']} of {sc['n']} days; "
                                      "8 Oct: fails, 0.90")

    def test_fails(self):
        sc, text = with_h5e_final(h5e_rows(skip_gap=0.95, reg_gap=-0.4), first_verdict="FAILS")
        self.assertFalse(sc["holds"])
        got = bp.h5e_final(text)
        self.assertEqual(got["verdict"], "FAILS")
        self.assertEqual(got["mae"], f"{sc['mae']:.2f}")
        self.assertEqual((got["closer"], got["n"]), (str(sc["closer"]), str(sc["n"])))
        c = bp.h5e_chip(got)
        self.assertEqual((c["kind"], c["verdict"]), ("bad", "fails (final)"))

    def test_absent_is_due(self):
        self.assertIsNone(bp.h5e_final(base_h5()))
        c = bp.h5e_chip(None)
        self.assertEqual((c["kind"], c["verdict"]), ("bad", "fails (first, 8 Oct)"))
        self.assertIn("0.90", c["number"])                     # only the recorded first verdict, no preview
        self.assertIn("final due 12–19 Nov", c["number"])

    def test_malformed_raises(self):
        _, text = with_h5e_final(h5e_rows(skip_gap=0.31, reg_gap=-1.1))
        for broken in (text.replace("volatility points (bar: under 0.5)", "vol pts (bar: under 0.5)"),
                       text.replace("counted days (bar: a majority)", "days (bar: a majority)"),
                       text.replace("\n- **HOLDS**.", "\n- HOLDS.")):
            self.assertNotEqual(broken, text)
            with self.assertRaises(bp.Unrecognised):
                bp.h5e_final(broken)


    def test_a_changed_bar_or_malformed_number_raises(self):
        # Astra, 8 Nov: "([\d.]+)" took "1.2.3" for a figure, and a block carrying another bar still parsed. The
        # reader now matches the writer's line exactly: two decimals, the registered bars word for word.
        sc, text = with_h5e_final(h5e_rows(skip_gap=0.31, reg_gap=-1.1))
        fig = f"OVX: {sc['mae']:.2f} volatility points"
        self.assertIn(fig, text)
        for broken in (text.replace(fig, "OVX: 1.2.3 volatility points"),
                       text.replace(fig, "OVX: . volatility points"),
                       text.replace(fig, f"OVX: {sc['mae']:.3f} volatility points"),      # not the writer's form
                       text.replace("(bar: under 0.5)", "(bar: under 0.6)"),
                       text.replace("counted days (bar: a majority)", "counted days (bar: a third)")):
            self.assertNotEqual(broken, text)
            with self.assertRaises(bp.Unrecognised):
                bp.h5e_final(broken)


class Scorer(unittest.TestCase):
    def test_a_refusing_scorer_stops_the_build(self):
        # Astra, 8 Nov: score_saved returned the scorer's text whatever its exit. h3_scorer.main exits 0 on HOLDS
        # and FAILS alike and refuses with SystemExit, so a nonzero exit is a refusal, never a report to print.
        import h3_scorer as hs
        good = hs.report(hs.score(hs.parse(fake_modelfree(H3Series.DAYS))))
        for code in (1, 2):
            with mock.patch.object(bp.subprocess, "run", return_value=mock.Mock(returncode=code, stdout=good,
                                                                               stderr="")):
                with self.assertRaises(SystemExit):
                    bp.score_saved("a saved run")
        with mock.patch.object(bp.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=good, stderr="")):
            self.assertEqual(bp.score_saved("a saved run"), good)


def whole_pdf(body):
    """`body` closed the way Chrome closes a PDF: the cross-reference table, the trailer, startxref, %%EOF."""
    return (body + b"xref\n0 1\n0000000000 65535 f \ntrailer\n<</Size 1>>\nstartxref\n" + str(len(body)).encode()
            + b"\n%%EOF\n")


def png(w, h, *, rows=None, bad_crc=False, iend=True):
    """A real PNG, w x h, 8-bit RGB, black; `rows` writes fewer rows than the header promises."""
    def chunk(kind, data):
        crc = zlib.crc32(kind + data) ^ (1 if bad_crc and kind == b"IDAT" else 0)
        return len(data).to_bytes(4, "big") + kind + data + crc.to_bytes(4, "big")
    pixels = zlib.compress(bytes((1 + 3 * w) * (h if rows is None else rows)))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", w.to_bytes(4, "big") + h.to_bytes(4, "big") + bytes([8, 2, 0, 0, 0]))
            + chunk(b"IDAT", pixels) + (chunk(b"IEND", b"") if iend else b""))


class PdfWhole(unittest.TestCase):
    """A PDF counts only if it was written to its end (Astra, 11 Nov: the page count, the MediaBox and the title can
    all sit in a file cut short, with no cross-reference table or trailer)."""
    BODY = b"%PDF-1.4\n1 0 obj\n<</Title (t)>>\nendobj\n2 0 obj\n<</Type /Page /MediaBox [0 0 3456 2592]>>\nendobj\n"

    def test_a_pdf_written_to_its_end(self):
        self.assertTrue(bp.pdf_whole(whole_pdf(self.BODY)))

    def test_a_pdf_cut_short_is_not(self):
        p = whole_pdf(self.BODY)
        for cut in (2, 7, 30, len(p) - len(self.BODY), len(p) // 2):
            self.assertFalse(bp.pdf_whole(p[:-cut]), cut)

    def test_startxref_must_point_at_the_table(self):
        p = whole_pdf(self.BODY).replace(f"startxref\n{len(self.BODY)}".encode(), b"startxref\n9")
        self.assertFalse(bp.pdf_whole(p))


class PngSize(unittest.TestCase):
    """The preview counts only if it decodes whole (Astra, 11 Nov): its size is read from a PNG whose every chunk
    checks out and whose image data inflates to exactly the rows its header promises."""
    def test_a_whole_png(self):
        self.assertEqual(bp.png_size(png(8, 6)), (8, 6))

    def test_a_broken_png_has_no_size(self):
        p = png(8, 6)
        for name, broken in (("cut short", p[:-5]), ("a chunk's checksum wrong", png(8, 6, bad_crc=True)),
                             ("no end chunk", png(8, 6, iend=False)), ("rows missing", png(8, 6, rows=5)),
                             ("not a PNG", b"\x89PNG preview"), ("empty", b"")):
            self.assertIsNone(bp.png_size(broken), name)


@unittest.skipUnless(Path(bp.SIPS).exists(), "needs macOS sips")
class RasterWithSips(unittest.TestCase):
    """The real sips draws a real one-page PDF into a PNG that png_size() reads whole, a pixel a point."""
    def test_a_page_becomes_a_whole_png(self):
        objs = [b"<</Type /Catalog /Pages 2 0 R>>", b"<</Type /Pages /Kids [3 0 R] /Count 1>>",
                b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 48 36] /Resources <<>>>>"]
        pdf, at = b"%PDF-1.4\n", []
        for i, o in enumerate(objs, 1):
            at.append(len(pdf))
            pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
        xref = len(pdf)
        pdf += (f"xref\n0 4\n0000000000 65535 f \n".encode() + b"".join(f"{a:010d} 00000 n \n".encode() for a in at)
                + f"trailer\n<</Size 4 /Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode())
        self.assertTrue(bp.pdf_whole(pdf))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "page.pdf").write_bytes(pdf)
            bp.raster(Path(d) / "page.pdf", Path(d) / "page.png")
            self.assertEqual(bp.png_size((Path(d) / "page.png").read_bytes()), (48, 36))


class Chrome(unittest.TestCase):
    """A Chrome run counts only when it produced something itself (Astra, 8 Nov: a zero exit with no new file let
    render() check an older poster.pdf; 31 Oct: a whole PDF can come with a teardown exit 2)."""
    def test_an_older_file_is_never_taken_for_this_run(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "poster.pdf"
            out.write_bytes(b"%PDF an older poster")
            with mock.patch.object(bp.subprocess, "run",
                                   return_value=mock.Mock(returncode=0, stdout="", stderr="")) as run:
                with self.assertRaises(SystemExit):
                    bp.chrome(["--print-to-pdf=" + str(out)], out)
            self.assertEqual(run.call_count, 2)                   # tried twice, then refused
            self.assertFalse(out.exists())                        # and the older file is not left to be mistaken

    def test_a_fresh_file_counts_after_a_teardown_exit(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "poster.pdf"

            def run(*a, **k):
                out.write_bytes(b"%PDF this run's poster")
                return mock.Mock(returncode=2, stdout="", stderr="Teardown watchdog expired")
            with mock.patch.object(bp.subprocess, "run", side_effect=run):
                self.assertEqual(bp.chrome([], out).returncode, 2)

    def test_a_page_dump_without_its_check_is_refused(self):
        with mock.patch.object(bp.subprocess, "run", return_value=mock.Mock(
                returncode=0, stdout="<html><body>no check here</body></html>", stderr="")):
            with self.assertRaises(SystemExit):
                bp.chrome(["--dump-dom", "file:///poster.html"])


class PrintCheck(unittest.TestCase):
    """The PDF carries the page check of the run that printed it, in its /Title, so a later run can never vouch for
    it (Astra, 8 Nov: the PDF, the preview and the measured page came from three Chrome runs)."""
    OK = {"minPx": 32, "overflow": 0, "qr": "svg", "fonts": 0, "clipped": 0, "overlaps": 0}

    @staticmethod
    def pdf(title):
        lit = title.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return b"%PDF-1.4\n1 0 obj\n<</Title (" + lit.encode() + b")\n/Producer (Skia/PDF m156)>>\nendobj\n"

    def test_a_passing_check_reads_back(self):
        got = bp.pdf_check(self.pdf(bp.TITLE + " | check " + json.dumps(self.OK)))
        self.assertEqual(got, self.OK)
        self.assertEqual(bp.problems(got), [])

    def test_each_failure_is_named(self):
        for k, v, why in (("minPx", 31.9, "text below 24 pt"), ("overflow", 1, "a column overflows"),
                          ("qr", "none", "QR code is not vector SVG"), ("fonts", 1, "web fonts did not load"),
                          ("clipped", 2, "chart text runs outside its chart"), ("overlaps", 1, "chart labels overlap")):
            self.assertEqual(bp.problems({**self.OK, k: v}), [why])

    def test_a_pdf_without_its_check_has_none(self):
        self.assertIsNone(bp.pdf_check(self.pdf(bp.TITLE)))          # the check had not run when Chrome printed
        self.assertIsNone(bp.pdf_check(b"%PDF-1.4 no title at all"))


class Render(unittest.TestCase):
    """render() judges the printed PDF by the check of the run that printed it; a clean check from the later run that
    measures the page cannot vouch for it (Astra, 8 Nov). A failed file is renamed, never left as poster.pdf. The
    preview is drawn from that checked PDF, never from a Chrome run of its own (Astra, 11 Nov)."""
    OK = PrintCheck.OK
    PREVIEW = png(2304, 1728)

    def chrome(self, printed, whole=True, calls=None):
        page = {**self.OK, "where": "x", "room": {}, "words": 1,
                "detail": {"overflow": [], "fonts": [], "clipped": [], "overlaps": []}}

        def run(args, out=None):
            if calls is not None:
                calls.append(list(args))
            if out is not None and out.suffix == ".pdf":
                t = (bp.TITLE + ("" if printed is None else " | check " + json.dumps(printed)))
                body = (b"%PDF-1.4\n<</Title (" + t.replace("(", "\\(").replace(")", "\\)").encode()
                        + b")>>\n<</Type /Page /MediaBox [0 0 3456 2592]>>\n")
                out.write_bytes(whole_pdf(body) if whole else body)
            elif out is not None:
                out.write_bytes(b"\x89PNG preview")
            return mock.Mock(returncode=0, stdout=f'<body data-check="{html.escape(json.dumps(page))}">')
        return run

    def raster(self, preview, drawn=None):
        def run(pdf, png_path):
            if drawn is not None:
                drawn.append((pdf.name, pdf.read_bytes()[:5]))
            if preview is not None:
                png_path.write_bytes(preview)
        return run

    def render(self, printed, whole=True, preview=PREVIEW, calls=None, drawn=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name)
        (d / "poster.html").write_text("<html></html>")
        with mock.patch.object(bp, "chrome", self.chrome(printed, whole, calls)), \
                mock.patch.object(bp, "raster", self.raster(preview, drawn)), mock.patch("builtins.print"):
            try:
                bp.render(d / "poster.html")
                return d, None
            except SystemExit as e:
                return d, str(e)

    def test_the_preview_is_drawn_from_the_checked_pdf(self):
        calls, drawn = [], []
        d, err = self.render(self.OK, calls=calls, drawn=drawn)
        self.assertIsNone(err)
        self.assertFalse([a for a in calls if any(x.startswith("--screenshot") for x in a)])   # no run of its own
        self.assertEqual(drawn, [("poster.unchecked.pdf", b"%PDF-")])                          # the checked file
        self.assertEqual((d / "preview.png").read_bytes(), self.PREVIEW)

    def test_a_pdf_cut_short_is_refused(self):
        drawn = []
        d, err = self.render(self.OK, whole=False, drawn=drawn)
        self.assertIn("the PDF was not written to its end", err or "")
        self.assertEqual(drawn, [])                                       # nothing is drawn from a broken file
        self.assertFalse((d / "poster.pdf").exists())
        self.assertTrue((d / "poster.FAILED-CHECK.pdf").exists())

    def test_a_preview_that_does_not_decode_is_refused(self):
        # whole PNGs of the wrong shape first, so a render that skipped the check fails on an assertion, not later
        for preview in (png(800, 600), png(2304, 1000), png(2304, 1728, rows=1000), b"\x89PNG\r\n\x1a\n cut", None):
            d, err = self.render(self.OK, preview=preview)
            self.assertIn("the preview drawn from the PDF is not one whole 48 x 36 in page", err or "")
            self.assertFalse((d / "poster.pdf").exists())
            self.assertFalse((d / "preview.png").exists())

    def test_the_print_run_check_decides(self):
        for printed, why in ((None, "the printed PDF carries no page check"),
                             ({**self.OK, "overlaps": 1}, "in the printed PDF, chart labels overlap"),
                             ({**self.OK, "fonts": 1}, "in the printed PDF, web fonts did not load")):
            d, err = self.render(printed)
            self.assertIsNotNone(err, printed)
            self.assertIn(why, err)
            self.assertFalse((d / "poster.pdf").exists())                  # never left to be taken for the poster
            self.assertTrue((d / "poster.FAILED-CHECK.pdf").exists())
            self.assertTrue((d / "preview.FAILED-CHECK.png").exists())

    def test_a_passing_print_is_kept(self):
        d, err = self.render(self.OK)
        self.assertIsNone(err)
        self.assertEqual(sorted(f.name for f in d.iterdir()), ["poster.html", "poster.pdf", "preview.png"])

    def test_a_run_that_dies_leaves_no_poster(self):
        # poster.pdf exists only after a render that passed: an older one is cleared first, and a run that dies
        # before its checks (here the page measurement) leaves its files unchecked, never as poster.pdf.
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        d = Path(td.name)
        (d / "poster.html").write_text("<html></html>")
        (d / "poster.pdf").write_bytes(b"%PDF an older poster")
        (d / "preview.png").write_bytes(b"\x89PNG an older preview")
        good = self.chrome(self.OK)

        def dies(args, out=None):
            if out is None:
                raise SystemExit("Chrome produced no fresh output twice")
            return good(args, out)
        with mock.patch.object(bp, "chrome", dies), mock.patch.object(bp, "raster", self.raster(self.PREVIEW)), \
                mock.patch("builtins.print"):
            with self.assertRaises(SystemExit):
                bp.render(d / "poster.html")
        self.assertFalse((d / "poster.pdf").exists())
        self.assertFalse((d / "preview.png").exists())


@unittest.skipUnless(Path(bp.CHROME).exists(), "needs Google Chrome")
class PageCheckInChrome(unittest.TestCase):
    """The page check measured by Chrome on a tiny page: a label run past its chart's edge and two labels drawn over
    each other are both caught (Astra, 8 Nov: the unit tests estimate text widths; only the browser has the boxes)."""
    def test_clipped_and_overlapping_labels_are_caught(self):
        svg = ('<svg viewBox="0 0 400 100" width="400" height="100" font-family="sans-serif">'
               '<text x="10" y="40" font-size="32">clear</text>'
               '<text x="330" y="90" font-size="32">clipped</text>'
               '<text x="200" y="40" font-size="32">one</text><text x="215" y="48" font-size="32">two</text></svg>')
        page = ("<!doctype html><html><head><meta charset='utf-8'><title>t</title></head><body>"
                f"<div class='poster'><div class='col a'>{svg}</div></div><div id='qr'></div>"
                f"<script>{bp.CHECK_JS}</script></body></html>")
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text(page)
            dom = bp.chrome(["--window-size=800,600", "--dump-dom", f.as_uri()]).stdout
        chk = json.loads(html.unescape(re.search(r'data-check="([^"]*)"', dom)[1]))
        self.assertEqual((chk["clipped"], chk["overlaps"]), (1, 1))
        self.assertEqual(chk["detail"]["clipped"], ["clipped"])
        self.assertEqual(chk["detail"]["overlaps"], ["one / two"])
        self.assertIn(" | check {", re.search(r"<title>([^<]*)</title>", dom)[1])

    @staticmethod
    def check(body):
        page = ("<!doctype html><html><head><meta charset='utf-8'><title>t</title></head><body>"
                f"<div class='poster'><div class='col a'>{body}</div></div><div id='qr'></div>"
                f"<script>{bp.CHECK_JS}</script></body></html>")
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text(page)
            dom = bp.chrome(["--window-size=800,600", "--dump-dom", f.as_uri()]).stdout
        return json.loads(html.unescape(re.search(r'data-check="([^"]*)"', dom)[1]))

    def test_half_a_pixel_counts_and_touching_does_not(self):
        # Astra, 11 Nov: the check let a label stick out of its chart, or into another, by up to a whole pixel.
        # Placed in the browser from the boxes it measures: "edge" ends half a pixel past its chart's right side,
        # "a2" starts half a pixel inside "a1", and "b2" starts exactly where "b1" ends (touching, not over).
        svgs = "".join(f'<svg id="{k}" width="600" height="100" font-family="sans-serif">{t}</svg>' for k, t in (
            ("s1", '<text id="edge" x="300" y="50" font-size="40">edge</text>'),
            ("s2", '<text id="a1" x="10" y="50" font-size="40">a1</text><text id="a2" x="300" y="50" font-size="40">a2</text>'),
            ("s3", '<text id="b1" x="10" y="50" font-size="40">b1</text><text id="b2" x="300" y="50" font-size="40">b2</text>')))
        place = """<script>
          const box = id => document.getElementById(id).getBoundingClientRect();
          const shift = (id, by) => { const t = document.getElementById(id); t.setAttribute("x", +t.getAttribute("x") + by); };
          shift("edge", box("s1").right + 0.5 - box("edge").right);
          shift("a2", box("a1").right - 0.5 - box("a2").left);
          shift("b2", box("b1").right - box("b2").left);
        </script>"""
        chk = self.check(svgs + place)
        self.assertEqual(chk["detail"]["clipped"], ["edge"])
        self.assertEqual(chk["detail"]["overlaps"], ["a1 / a2"])

    def test_text_a_hair_under_24_pt_is_caught(self):
        # Astra, 11 Nov: the smallest size was rounded before the comparison, so 31.996 px (23.997 pt) passed.
        chk = self.check('<p style="font-size:40px">big</p><p style="font-size:31.996px">a hair small</p>')
        self.assertLess(chk["minPx"], 32)
        self.assertEqual(chk["where"], "a hair small")
        self.assertIn("text below 24 pt", bp.problems(chk))      # (the tiny page also lacks the QR and web fonts)


class H7Reading(unittest.TestCase):
    def read(self, v, waiting=()):
        return bp.h7_reading(rv.append_result(base_h7(), rv.block_h7(v, READ_ON, waiting)))

    def test_holds(self):
        got = self.read(h7_v(0.112, 0.087, 0.214))
        self.assertEqual(got, {"a": "HOLDS", "uso": "0.112", "uso_n": "22", "gld": "0.087", "gld_n": "22",
                               "b": "HOLDS", "gvz": "0.214", "n": "22"})
        a, b = bp.h7_chips(got)
        self.assertEqual((a["id"], a["kind"], a["verdict"]), ("H7a", "ok", "holds"))
        self.assertEqual(a["number"], "USO 0.112, GLD 0.087 (bar ≤ 0.25)")
        self.assertEqual((b["id"], b["kind"], b["number"]), ("H7b", "ok", "0.214 (bar ≤ 0.30)"))

    def test_fails(self):
        got = self.read(h7_v(0.412, 0.087, 0.355), waiting=["2026-11-11 GLD OPRA"])
        self.assertEqual((got["a"], got["b"], got["uso"], got["gvz"]), ("FAILS", "FAILS", "0.412", "0.355"))
        a, b = bp.h7_chips(got)
        self.assertEqual((a["kind"], b["kind"]), ("bad", "bad"))

    def test_split_verdict(self):
        got = self.read(h7_v(0.10, 0.20, 0.31))
        self.assertEqual((got["a"], got["b"]), ("HOLDS", "FAILS"))

    def test_below_minimum_is_not_a_verdict(self):
        got = self.read(h7_v(0.10, None, 0.20, n=6))
        self.assertTrue(got["a"].startswith("NOT READ"))
        self.assertEqual(got["gld"], "n/a")
        a = bp.h7_chips(got)[0]
        self.assertEqual(a["kind"], "na")      # grey "–", never scored; not amber "…", which reads as still due
        self.assertTrue(a["verdict"].startswith("not read"))

    def test_absent_is_due(self):
        self.assertIsNone(bp.h7_reading(base_h7()))
        a, b = bp.h7_chips(None)
        self.assertEqual((a["kind"], a["verdict"], a["number"]), ("due", "due 12–19 Nov", "bar ≤ 0.25"))
        self.assertEqual((b["kind"], b["verdict"], b["number"]), ("due", "due 12–19 Nov", "bar ≤ 0.30"))

    def test_malformed_raises(self):
        text = rv.append_result(base_h7(), rv.block_h7(h7_v(0.112, 0.087, 0.214), READ_ON))
        for broken in (text.replace("GVZ's close", "GVZ close"),
                       text.replace("(bar: 0.25 or less, each)", "(bar: 0.25)"),
                       text.replace("USO 0.112 over", "USO about 0.11 over")):
            self.assertNotEqual(broken, text)
            with self.assertRaises(bp.Unrecognised):
                bp.h7_reading(broken)


class Headline(unittest.TestCase):
    """Gabriel's 21 Oct rule, decided before H7's verdict, on blocks made by record_verdict's own writer."""
    def h7(self, uso_a, gld_a, gld_b, n=22):
        return bp.h7_reading(rv.append_result(base_h7(), rv.block_h7(h7_v(uso_a, gld_a, gld_b, n=n), READ_ON)))

    def test_no_verdict_keeps_the_headline(self):
        self.assertEqual(bp.headline({"verdict": "HOLDS"}, None), bp.HEADLINE)

    def test_h7_holds_keeps_the_headline(self):
        self.assertEqual(bp.headline({"verdict": "HOLDS"}, self.h7(0.112, 0.087, 0.214)), bp.HEADLINE)

    def test_either_part_failing_switches(self):
        for v in ((0.40, 0.087, 0.214), (0.10, 0.20, 0.31), (0.412, 0.087, 0.355)):
            self.assertEqual(bp.headline({"verdict": "HOLDS"}, self.h7(*v)), bp.HEADLINE_IF_H7_FAILS)

    def test_h3_failing_too_uses_the_cautious_one(self):
        self.assertEqual(bp.headline({"verdict": "FAILS"}, self.h7(0.10, 0.20, 0.31)), bp.HEADLINE_IF_H7_AND_H3_FAIL)

    def test_below_minimum_is_not_a_failure(self):
        self.assertEqual(bp.headline({"verdict": "HOLDS"}, self.h7(0.10, None, 0.20, n=6)), bp.HEADLINE)


class H3Box(unittest.TestCase):
    def report(self):
        import h3_scorer as hs
        rows = [(d, sym, lvl + 0.3 * i % 2, (-0.4 if sym != "USO" else -1.2) + 0.05 * (i % 3))
                for i, d in enumerate(trading_days("2026-09-14", "2026-10-16"))
                for sym, lvl in (("GLD", 25.0), ("IWM", 20.0), ("QQQ", 21.0), ("SPY", 16.0), ("USO", 58.0))]
        return hs.report(hs.score(rows))

    def test_parse_scorer_report(self):
        got = bp.parse_h3(self.report())
        self.assertEqual(got["verdict"], "HOLDS")
        self.assertEqual(got["b"], "HOLDS")
        self.assertIn(got["c"], ("HOLDS", "FAILS"))
        self.assertGreater(got["n"], 100)
        self.assertEqual(set(got["per"]), {"GLD", "IWM", "QQQ", "SPY", "USO"})
        self.assertTrue(all(n > 10 and m > 0 for n, m in got["per"].values()))
        self.assertLess(got["mean"], 0)

    def test_so_far_then_of_record(self):
        h3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS", "mean": -0.31}
        before, after = bp.h3_chip(h3, False), bp.h3_chip(h3, True)
        self.assertEqual((before["kind"], before["verdict"]), ("ok", "holds so far"))
        self.assertEqual(after["verdict"], "holds")
        self.assertEqual(before["number"], "0.45 over 125 readings (bar < 1.0)")
        t = bp.h3_tile(h3, False)
        self.assertEqual((t["a"], t["b"], t["c"], t["mean"]), ("holds so far", "holds so far", "holds so far", "−0.31"))
        self.assertEqual(t["label"], "To date; the reading of record runs to 11 Nov")
        self.assertNotIn("so far", " ".join(str(v) for v in bp.h3_tile(h3, True).values()))

    def test_of_record_needs_the_11_nov_data(self):
        # Not the date alone: Cboe's closes can lag a day or two (tools/record_verdict.py), so the reading of record
        # needs 11 Nov in every pair's series, and a build after that day (8 Nov review).
        full = bp.h3_series(fake_modelfree(trading_days("2026-11-02", "2026-11-13")))     # the scorer cuts at 11 Nov
        self.assertTrue(bp.of_record(full, date(2026, 11, 12)))
        self.assertFalse(bp.of_record(full, date(2026, 11, 11)))
        late = bp.h3_series(fake_modelfree(trading_days("2026-11-02", "2026-11-10")))
        self.assertFalse(bp.of_record(late, date(2026, 11, 13)))
        one_short = {**full, "GLD": full["GLD"][:-1]}
        self.assertFalse(bp.of_record(one_short, date(2026, 11, 13)))

    def test_a_failing_part_is_marked_bad(self):
        h3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "FAILS", "mean": -0.31}
        t = bp.tile_html(bp.h3_tile(h3, False))
        self.assertIn('<li class="ok"><b>✓ H3a holds so far</b>', t)
        self.assertIn('<li class="bad"><b>✗ H3c fails so far</b>', t)              # never printed in pass green

    def test_malformed_raises(self):
        rep = self.report()
        for broken in (rep.replace("vs bar under 1.0", "vs bar 1.0"),
                       rep.replace("readings to 2026-11-11", "readings to 2026-12-31"),
                       "\n".join(l for l in rep.splitlines() if not l.startswith("H3c")),
                       "\n".join(l for l in rep.splitlines() if "T=" not in l)):
            with self.assertRaises(bp.Unrecognised):
                bp.parse_h3(broken)


class Scorecard(unittest.TestCase):
    H3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS", "mean": -0.31}

    def test_every_status_table_hypothesis_is_on_the_poster(self):
        status = (ROOT / "hypotheses/README.md").read_text().split("## Status", 1)[1]
        ids = {line.split("|")[1].strip() for line in status.splitlines() if line.startswith("| H")}
        conf, side = bp.scorecard(self.H3, None, None, False)
        shown = " ".join(c["id"] for c in conf + side)
        for h in sorted(ids):
            self.assertIn(h, shown, f"{h} is in hypotheses/README.md's status table but not on the poster")
        self.assertEqual(conf[0]["id"], "H3")                         # confirmatory first, side studies apart
        self.assertIn("H1", [c["id"] for c in side])

    def test_every_chip_is_complete_and_never_colour_alone(self):
        conf, side = bp.scorecard(self.H3, None, None, False)
        for c in conf + side:
            self.assertIn(c["kind"], bp.ICON)
            self.assertTrue(all(c[k] for k in ("id", "claim", "verdict", "number")), c)
            html_ = bp.chip_html(c)
            self.assertIn(bp.ICON[c["kind"]], html_)                   # an icon and a word, not colour alone
            self.assertIn(c["verdict"], html_)

    def test_comparisons_never_break_across_lines(self):
        # 8 Nov review: H6b broke "p <" from "0.01". Every comparison is held together with no-break spaces.
        conf, side = bp.scorecard(self.H3, None, None, False)
        for c in conf + side:
            h = bp.chip_html(c)
            self.assertIsNone(re.search(r" (?:&lt;|&gt;|[=≤≥])|(?:&lt;|&gt;|[=≤≥]) ", h), h)


class H3Series(unittest.TestCase):
    DAYS = trading_days("2026-11-02", "2026-11-13")                    # crosses the 11 Nov cut

    def test_series_is_the_scorers_rows_to_11_nov(self):
        s = bp.h3_series(fake_modelfree(self.DAYS))
        self.assertEqual(set(s), {"GLD", "IWM", "QQQ", "SPY", "USO"})
        self.assertEqual(s["SPY"][-1][0], "2026-11-11")               # 12 and 13 Nov come after the reading of record
        self.assertEqual(len(s["SPY"]), len([d for d in self.DAYS if d <= "2026-11-11"]))
        _, ours, cboe = s["USO"][0]
        self.assertAlmostEqual(ours - cboe, -1.5, places=6)           # ours = Cboe + gap

    def test_chart_and_scorer_agree(self):
        out = fake_modelfree(self.DAYS)
        got = bp.check_series(bp.h3_series(out), scored(out))
        self.assertEqual(got["n"], 5 * len([d for d in self.DAYS if d <= "2026-11-11"]))

    def test_a_different_run_stops_the_build(self):
        out = fake_modelfree(self.DAYS)
        h3 = scored(out)
        moved = bp.h3_series(out)
        d, ours, cboe = moved["GLD"][0]
        moved["GLD"][0] = (d, ours + 0.5, cboe)                       # one reading half a point off
        with self.assertRaises(bp.Unrecognised):
            bp.check_series(moved, h3)
        short = bp.h3_series(out)
        short["SPY"] = short["SPY"][:-1]                              # one reading missing
        with self.assertRaises(bp.Unrecognised):
            bp.check_series(short, h3)
        with self.assertRaises(bp.Unrecognised):
            bp.check_series(bp.h3_series(out), {**h3, "days": h3["days"] + 1})     # a day the chart lacks

    def test_figures_are_rounded_once_from_full_precision(self):
        # Number audit, 8 Nov: every gap -0.435186 +/- 0.01 over an even number of days makes each mean exactly
        # 0.435186, which the scorer prints as 0.435; rounding that print again gives 0.43, the value itself 0.44.
        out = fake_modelfree(self.DAYS, gap_of=lambda g, i: -0.435186 + 0.01 * (-1) ** i)
        h3 = scored(out)
        self.assertEqual((f"{h3['mae']:.3f}", f"{h3['mean']:+.3f}"), ("0.435", "-0.435"))
        self.assertEqual(f"{h3['mae']:.2f}", "0.43")                      # the double rounding this test guards against
        got = bp.check_series(bp.h3_series(out), h3)
        self.assertEqual((f"{got['mae']:.2f}", f"{got['mean']:+.2f}"), ("0.44", "-0.44"))
        self.assertEqual({s: f"{m:.2f}" for s, (_, m) in got["per"].items()}, dict.fromkeys(got["per"], "0.44"))
        self.assertEqual(bp.h3_tile(got, True)["mean"], "−0.44")
        self.assertTrue(bp.h3_chip(got, True)["number"].startswith("0.44 over 40 readings"))


class MainChart(unittest.TestCase):
    """The main chart shows aggregate statistics only - Gabriel's request to Cboe (10 Oct, repeated 21 Oct),
    approved 4 Nov: "Only aggregate statistics appear (for example, average differences between my estimates and
    the index)". Per fund,
    the days counted by gap; never a date, a single day's gap or an index value; one gap axis and one day axis for
    all five panels (8 Nov reviews; Astra, 8 Nov: daily gaps plus the public daily estimates would give each close
    back)."""
    def test_counts_only_on_shared_axes(self):
        out = fake_modelfree(H3Series.DAYS)
        series = bp.h3_series(out)
        h3 = bp.check_series(series, scored(out))
        calls, real = [], bp.charts.gap_histogram

        def spy(sym, index, what, gaps, mae, scale, counts):
            calls.append((sym, list(gaps), scale, counts))
            return real(sym, index, what, gaps, mae, scale, counts)

        with mock.patch.object(bp.charts, "gap_histogram", spy):
            cells = bp.main_chart(series, h3)
        self.assertEqual([c[0] for c in calls], [p[0] for p in bp.PAIRS])
        self.assertEqual(len({(c[2], c[3]) for c in calls}), 1)          # one gap axis and one day axis
        for sym, gaps, _, _ in calls:
            self.assertTrue(all(isinstance(g, float) for g in gaps))       # numbers only: no date travels
            self.assertEqual(sorted(round(g, 9) for g in gaps), sorted(round(o - c, 9) for _, o, c in series[sym]))
        self.assertEqual(cells.count('<div class="cell">'), 5)

    def test_the_axis_holds_every_bin(self):
        # A gap of exactly +4.00 opens the bin [4.0, 4.5): the shared axis must reach 4.5, not stop at 4.
        series = {s: [("2026-11-02", 20.0 + (4.0 if s == "IWM" else -0.3), 20.0)] for s, _, _ in bp.PAIRS}
        h3 = {"per": {s: (1, abs(series[s][0][1] - series[s][0][2])) for s, _, _ in bp.PAIRS}}
        cells = bp.main_chart(series, h3)
        self.assertEqual(cells.count('<div class="cell">'), 5)
        self.assertIn(">+6<", cells)                                      # the axis runs past the +4 bin


class Page(unittest.TestCase):
    """The assembled page, with a stand-in for the live H3 run (no modelfree.py, no Chrome)."""
    def build(self, days, today):
        out = fake_modelfree(days, base=50.37)                    # index levels no other number on the page shares
        series = bp.h3_series(out)
        h3 = bp.check_series(series, scored(out))
        with tempfile.TemporaryDirectory() as d, mock.patch.object(bp, "h3_live", return_value=(h3, series)):
            page = bp.build(today, out_dir=Path(d)).read_text()
        return " ".join(page.split()), series                      # whitespace as a browser collapses it

    @staticmethod
    def text(page):
        body = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S)
        labels = " ".join(re.findall(r'aria-label="([^"]*)"', body))
        return html.unescape(re.sub(r"<[^>]+>", " ", body) + " " + labels)

    def test_no_index_value_reaches_the_page(self):
        page, series = self.build(trading_days("2026-11-02", "2026-11-13"), date(2026, 11, 13))
        txt = self.text(page)
        for rows in series.values():
            for _, ours, cboe in rows:                            # ours = Cboe + gap would give Cboe's value back
                for v in (ours, cboe):
                    for f in (".1f", ".2f"):
                        self.assertNotIn(format(v, f), txt)

    def test_of_record_only_with_the_11_nov_data(self):
        page, _ = self.build(trading_days("2026-11-02", "2026-11-13"), date(2026, 11, 13))
        self.assertIn("The reading of record, to 11 Nov 2026", page)
        self.assertNotRegex(page, r"(holds|fails) so far")
        late, _ = self.build(trading_days("2026-11-02", "2026-11-10"), date(2026, 11, 13))    # 11 Nov not in yet
        self.assertRegex(late, r"(holds|fails) so far")
        self.assertIn("the reading of record runs to 11 Nov", late)
        self.assertNotIn("The reading of record, to 11 Nov 2026", late)

    def test_the_main_chart_draws_no_day(self):
        page, _ = self.build(trading_days("2026-11-02", "2026-11-13"), date(2026, 11, 13))
        i = page.index('<div class="grid">')
        svgs = re.findall(r"<svg\b.*?</svg>", page[i:page.index('<p class="cap">', i)])
        self.assertEqual(len(svgs), 5)
        for s in svgs:
            self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}|>(Sep|Oct|Nov)<", s))

    def test_claims_match_the_records(self):
        page, _ = self.build(trading_days("2026-11-02", "2026-11-13"), date(2026, 11, 13))
        self.assertIn("scored against a bar set before its test ran", page)   # H1, H2, H6 used history; H5 one day
        self.assertNotIn("before its data", page)
        self.assertIn("H5e and H7 were also frozen on", page)                 # OSF z5gfu holds those two only
        self.assertNotIn("every trading day", page)                           # 16 and 28 Sep have no reading
        self.assertIn("recomputed every recorded result on 17 Oct", page)    # docs/recheck-2026-10-17, dated
        self.assertNotIn("every recorded number", page)                      # results after 17 Oct were not in it


class Recipe(unittest.TestCase):
    def test_curves_use_the_readme_sentence_numbers(self):
        import charts
        readme = " ".join((ROOT / "README.md").read_text().split())
        (sd_calm, vol_calm, sd_wild, vol_wild), = re.findall(
            r"about ([\d.]+) standard deviations on a (\d+)-vol name but only ([\d.]+) on (\d+)-vol", readme)
        self.assertEqual((int(vol_calm), int(vol_wild)), (round(bp.CALM[1] * 100), round(bp.WILD[1] * 100)))
        self.assertEqual(f"{charts.band_sd(0.10, bp.CALM[1]):.1f}", sd_calm)
        self.assertEqual(f"{charts.band_sd(0.10, bp.WILD[1]):.1f}", sd_wild)
        self.assertIn(f"about {sd_calm} standard deviations on a {vol_calm}-vol name but only {sd_wild} on "
                      f"{vol_wild}-vol", bp.TRUNCATION_WHY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
