import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import zipfile, re, sys
import xml.etree.ElementTree as ET
M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
def col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0); n = 0
    for ch in letters: n = n * 26 + ord(ch) - 64
    return n - 1
def sheet_rows(path):
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(M + "si"):
            ss.append("".join(t.text or "" for t in si.iter(M + "t")))
    names = sorted((n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)), key=lambda n: int(re.search(r"(\d+)\.xml", n).group(1)))
    out = []
    for n in names:
        for row in ET.fromstring(z.read(n)).iter(M + "row"):
            cells = {}
            for c in row.iter(M + "c"):
                v = c.find(M + "v"); x = v.text if v is not None else ""
                if c.get("t") == "s" and x: x = ss[int(x)]
                if c.get("t") == "inlineStr":
                    x = "".join(t.text or "" for t in c.iter(M + "t"))
                cells[col_index(c.get("r"))] = x or ""
            w = max(cells) + 1 if cells else 0
            out.append([cells.get(i, "") for i in range(w)])
    return out
if __name__ == "__main__":
    rows = sheet_rows(sys.argv[1])
    for r in rows[:int(sys.argv[2]) if len(sys.argv) > 2 else 25]: print(r)
