"""Independent H5a/H5b from the Bloomberg OMON exports (licensed; read from ~/Documents/volrec-bloomberg, never copied).
Columns are found from the header row and every cell is placed by its column letter (bloomberg_reader.py), which is
how this found the 17 Oct reader bug. Pooled mid gap as a share of Bloomberg's spread, raw and in exact cents;
H5b's no-bid concordance. Aggregates only. Bloomberg figures: Source: Bloomberg Finance L.P."""
import csv, os, statistics as st, sys
from datetime import datetime
from fractions import Fraction as Fr
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from bloomberg_reader import sheet_rows  # noqa: E402

B = Path.home() / "Documents" / "volrec-bloomberg"
FILES = ["USO_OMON_2026-09-18.xlsx", "USO_OMON_2026-09-22.xlsx", "TSLA_OMON_2026-09-22.xlsx", "USO_OMON_2026-09-23.xlsx",
         "TSLA_OMON_2026-09-23.xlsx", "USO_OMON_2026-09-23_30Oct.xlsx", "TSLA_OMON_2026-09-23_30Oct.xlsx"]
wide = list(csv.DictReader(open(ROOT / "data/surface_wide.csv")))
band = list(csv.DictReader(open(ROOT / "data/surface.csv")))


def omon(path):
    """{expiry: {(type, strike): (bid, ask)}}, columns located from the header row."""
    rows = sheet_rows(path)
    hdr = next(r for r in rows if "Strike" in r and "Bid" in r)
    strikes = [i for i, v in enumerate(hdr) if v == "Strike"]
    cC = {n: hdr.index(n) for n in ("Strike", "Bid", "Ask")}
    cP = {k: v + (strikes[1] - strikes[0]) for k, v in cC.items()}
    out, exp = {}, None
    for r in rows:
        if r and "CSize" in (r[0] or ""):
            exp = datetime.strptime(r[0].split()[0], "%d-%b-%y").date().isoformat(); continue
        if exp is None:
            continue
        for t, c in (("C", cC), ("P", cP)):
            try:
                k = float(r[c["Strike"]])
            except (ValueError, IndexError):
                continue
            g = lambda i: (float(r[i]) if i < len(r) and r[i] != "" else None)
            out.setdefault(exp, {})[(t, round(k, 2))] = (g(c["Bid"]), g(c["Ask"]))
    return out


raw, cents, two, byd = [], [], [], {}
b0 = f0 = o0 = 0
for fn in FILES:
    sym, _, d = fn.split("_")[:3]; d = d[:10]
    for exp, q in omon(B / fn).items():
        w = [r for r in wide if r["date"] == d and r["symbol"] == sym and r["expiration"] == exp]
        if not w:
            continue
        spot = float(next(r for r in band if r["date"] == d and r["symbol"] == sym and r["expiration"] == exp)["spot"])
        for r in w:
            k, t = float(r["strike"]), r["type"]
            b = q.get((t, round(k, 2)))
            if (t == "P") != (k < spot) or not b or b[1] is None:
                continue
            fb = float(r["bid"]) if r["bid"] not in ("", None) else 0.0
            fa = float(r["ask"]) if r["ask"] not in ("", None) else None
            bb, ba = b[0] or 0.0, b[1]
            b0 += fb == 0 and bb == 0; f0 += fb == 0 and bb > 0; o0 += fb > 0 and bb == 0
            if fa is not None and ba > bb:
                x = abs((fb + fa) / 2 - (bb + ba) / 2) / (ba - bb)
                raw.append(x); byd.setdefault(d, []).append(x)
                c = lambda v: Fr(round(v * 100), 100)
                cents.append(abs((c(fb) + c(fa)) / 2 - (c(bb) + c(ba)) / 2) / (c(ba) - c(bb)))
                if fb > 0 and bb > 0:
                    two.append(x)
print(f"H5a: {len(raw)} wing contracts; pooled median {st.median(raw):.3f} (exact cents {float(st.median(cents)):.3f}); "
      f"by date " + ", ".join(f"{d[5:]} {st.median(v):.2f}" for d, v in sorted(byd.items())) +
      f"; inside half a spread {sum(x <= 0.5 for x in raw) / len(raw):.0%}; both bid n={len(two)} median {st.median(two):.2f}")
print(f"H5b: free no-bid -> Bloomberg no-bid {b0} of {b0 + f0}; Bloomberg-only no-bid {o0}")
print("Bloomberg figures: Source: Bloomberg Finance L.P.")
