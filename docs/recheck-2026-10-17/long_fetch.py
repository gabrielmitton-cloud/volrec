"""Fetch the public inputs for the long-sample re-check (H1, H2, H6) into RECHECK_WORK - never into the repo:
Yahoo Finance daily bars (split/dividend-adjusted close, raw high/low/close) for the eleven Sample A funds, Cboe's
index history files, and FRED's copies of EVZ and VXXLE (Cboe withdrew those files)."""
import os as _os
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))
import requests, json, time, csv, io
from datetime import datetime, timezone
_os.makedirs(WORK, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) research-verification"}
p1, p2 = int(datetime(2015, 12, 1, tzinfo=timezone.utc).timestamp()), int(datetime(2026, 10, 17, tzinfo=timezone.utc).timestamp())
px = {}
for s in ["SPY", "QQQ", "IWM", "DIA", "USO", "GLD", "SLV", "GDX", "XLE", "EEM", "FXE"]:
    j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}", params={"period1": p1, "period2": p2, "interval": "1d",
                     "events": "div,split"}, headers=UA, timeout=30).json()["chart"]["result"][0]
    ts = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") for t in j["timestamp"]]
    adj, q = j["indicators"]["adjclose"][0]["adjclose"], j["indicators"]["quote"][0]
    px[s] = {k: {d: v for d, v in zip(ts, col) if v} for k, col in (("adj", adj), ("high", q["high"]), ("low", q["low"]), ("close", q["close"]))}
    time.sleep(0.5)
json.dump(px, open(f"{WORK}/yahoo.json", "w"))
iv = {}
for n in ["VIX", "VXN", "RVX", "VXD", "OVX", "GVZ", "VXSLV", "VXGDX", "VXEEM", "VIX9D", "VIX3M"]:
    lines = requests.get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{n}_History.csv", headers=UA, timeout=30).text.strip().split("\n")
    h = [x.strip().upper() for x in lines[0].split(",")]; ci = h.index("CLOSE") if "CLOSE" in h else len(h) - 1
    iv[n] = {}
    for ln in lines[1:]:
        c = ln.split(",")
        try:
            iv[n][datetime.strptime(c[0].strip(), "%m/%d/%Y").strftime("%Y-%m-%d")] = float(c[ci])
        except (ValueError, IndexError):
            pass
for n, sid in (("EVZ", "EVZCLS"), ("VXXLE", "VXXLECLS")):
    t = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=30).text
    iv[n] = {r[0]: float(r[1]) for r in csv.reader(io.StringIO(t)) if r and r[0][:2] in ("19", "20") and r[1] not in ("", ".")}
json.dump(iv, open(f"{WORK}/iv.json", "w"))
print("fetched into", WORK)
