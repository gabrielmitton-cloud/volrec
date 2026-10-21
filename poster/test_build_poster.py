"""The poster's verdict-box readers against fixtures made by the verdict writer itself.

    .../python3 poster/test_build_poster.py

Every fixture is produced by tools/record_verdict.py's own functions (h5e_score, block_h5e(final=True),
block_h7, append_result) or tools/h3_scorer.py's (score, report), appended to the REAL hypothesis files, so a
change in the writer's wording breaks these tests rather than the poster on print day. Covered: HOLDS and FAILS,
the block-absent case (the box says "reading due"), and malformed blocks (the reader raises, never guesses).
Stdlib only; reads the repository, writes nothing.
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

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
        measured, verdict = bp.h5e_cells(got)
        self.assertIn(f"final: {sc['mae']:.2f}; closer on {sc['closer']} of {sc['n']}", measured)
        self.assertIn('class="pill ok">HOLDS', verdict)
        self.assertNotIn("due", verdict)

    def test_fails(self):
        sc, text = with_h5e_final(h5e_rows(skip_gap=0.95, reg_gap=-0.4), first_verdict="FAILS")
        self.assertFalse(sc["holds"])
        got = bp.h5e_final(text)
        self.assertEqual(got["verdict"], "FAILS")
        self.assertEqual(got["mae"], f"{sc['mae']:.2f}")
        self.assertEqual((got["closer"], got["n"]), (str(sc["closer"]), str(sc["n"])))
        self.assertIn('class="pill bad">FAILS', bp.h5e_cells(got)[1])

    def test_absent_is_due(self):
        self.assertIsNone(bp.h5e_final(base_h5()))
        measured, verdict = bp.h5e_cells(None)
        self.assertIn("reading due 12–19 Nov", verdict)
        self.assertIn("first (8 Oct): 0.90", measured)       # only the recorded first verdict, no preview
        self.assertNotIn("final:", measured)

    def test_malformed_raises(self):
        _, text = with_h5e_final(h5e_rows(skip_gap=0.31, reg_gap=-1.1))
        for broken in (text.replace("volatility points (bar: under 0.5)", "vol pts (bar: under 0.5)"),
                       text.replace("counted days (bar: a majority)", "days (bar: a majority)"),
                       text.replace("\n- **HOLDS**.", "\n- HOLDS.")):
            self.assertNotEqual(broken, text)
            with self.assertRaises(bp.Unrecognised):
                bp.h5e_final(broken)


class H7Reading(unittest.TestCase):
    def read(self, v, waiting=()):
        return bp.h7_reading(rv.append_result(base_h7(), rv.block_h7(v, READ_ON, waiting)))

    def test_holds(self):
        got = self.read(h7_v(0.112, 0.087, 0.214))
        self.assertEqual(got, {"a": "HOLDS", "uso": "0.112", "uso_n": "22", "gld": "0.087", "gld_n": "22",
                               "b": "HOLDS", "gvz": "0.214", "n": "22"})
        measured, verdict = bp.h7_cells(got)
        self.assertIn("a: USO 0.112", measured)
        self.assertIn("b: 0.214", measured)
        self.assertIn('class="pill ok">H7a HOLDS', verdict)
        self.assertIn('class="pill ok">H7b HOLDS', verdict)

    def test_fails(self):
        got = self.read(h7_v(0.412, 0.087, 0.355), waiting=["2026-11-11 GLD OPRA"])
        self.assertEqual((got["a"], got["b"], got["uso"], got["gvz"]), ("FAILS", "FAILS", "0.412", "0.355"))
        verdict = bp.h7_cells(got)[1]
        self.assertIn('class="pill bad">H7a FAILS', verdict)
        self.assertIn('class="pill bad">H7b FAILS', verdict)

    def test_split_verdict(self):
        got = self.read(h7_v(0.10, 0.20, 0.31))
        self.assertEqual((got["a"], got["b"]), ("HOLDS", "FAILS"))

    def test_below_minimum_is_not_a_verdict(self):
        got = self.read(h7_v(0.10, None, 0.20, n=6))
        self.assertTrue(got["a"].startswith("NOT READ"))
        self.assertEqual(got["gld"], "n/a")
        self.assertIn('class="pill due">H7a NOT READ', bp.h7_cells(got)[1])

    def test_absent_is_due(self):
        self.assertIsNone(bp.h7_reading(base_h7()))
        measured, verdict = bp.h7_cells(None)
        self.assertIn("reading due 12–19 Nov", verdict)
        self.assertNotRegex(measured, r"\d\.\d")             # no number until the block exists

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

    def test_so_far_then_of_record(self):
        h3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS"}
        before = bp.h3_cells(h3, date(2026, 11, 11))
        self.assertIn("of record 11 Nov", before[0])
        self.assertIn("HOLDS so far", before[1])
        after = bp.h3_cells(h3, date(2026, 11, 12))
        self.assertIn("reading of record", after[0])
        self.assertNotIn("so far", after[0] + after[1])

    def test_malformed_raises(self):
        rep = self.report()
        for broken in (rep.replace("vs bar under 1.0", "vs bar 1.0"),
                       rep.replace("readings to 2026-11-11", "readings to 2026-12-31"),
                       "\n".join(l for l in rep.splitlines() if not l.startswith("H3c"))):
            with self.assertRaises(bp.Unrecognised):
                bp.parse_h3(broken)


class Table(unittest.TestCase):
    def test_every_status_table_hypothesis_is_on_the_poster(self):
        status = (ROOT / "hypotheses/README.md").read_text().split("## Status", 1)[1]
        ids = {line.split("|")[1].strip() for line in status.splitlines() if line.startswith("| H")}
        h3 = {"verdict": "HOLDS", "mae": 0.448, "n": 125, "days": 25, "b": "HOLDS", "c": "HOLDS"}
        conf, side = bp.test_rows(h3, None, None, date(2026, 10, 21))
        shown = " ".join(r[0] for r in conf + side)
        for h in sorted(ids):
            self.assertIn(h, shown, f"{h} is in hypotheses/README.md's status table but not on the poster")
        self.assertEqual([r[0] for r in conf][:1], ["H3"])          # confirmatory first, side studies apart
        self.assertIn("H1", [r[0] for r in side])


if __name__ == "__main__":
    unittest.main(verbosity=2)
