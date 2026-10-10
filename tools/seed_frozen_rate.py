"""Give a fresh clone the frozen risk-free rate every registered number was computed with (added 10 Oct 2026).

Every registered reading discounts at the 1-month Treasury rate as last cached on 10 Sep 2026:
3.91% (DGS1MO). That rate is frozen on purpose (tools/calibrate.py says why), and it lives in
data/fred_cache.json, which is git-ignored because FRED's Cboe series may not be mirrored here. So a
stranger's clone had no way to reproduce the registered numbers: without the cache, risk_free()
falls back to r = 0 (no FRED_KEY) or to today's rate (a real key).

This writes the one observation the readings use - the last one - and nothing else, and only when no
cache exists, so it can never overwrite the real one. Then run with the placeholder key:

    python tools/seed_frozen_rate.py
    FRED_KEY=use-cache python modelfree.py

Source: Board of Governors of the Federal Reserve System (US), Market Yield on U.S. Treasury
Securities at 1-Month Constant Maturity [DGS1MO], retrieved from FRED, Federal Reserve Bank of St. Louis.
"""
import json
import sys
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "data" / "fred_cache.json"
FROZEN = {"DGS1MO||": {"2026-09-10": 3.91}}   # the last observation in the registered cache


def main():
    if CACHE.exists():
        have = json.loads(CACHE.read_text()).get("DGS1MO||") or {}
        last = max(have) if have else None
        same = last == "2026-09-10" and have[last] == 3.91
        print(f"{CACHE.name} already exists (DGS1MO last {last}"
              + (f" = {have[last]}%" if last else "") + ("" if same else " - NOT the registered value")
              + "); left untouched.")
        sys.exit(0 if same else 1)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(FROZEN))
    print(f"wrote {CACHE}: DGS1MO 2026-09-10 = 3.91% (the registered rate). Now run with FRED_KEY=use-cache.")


if __name__ == "__main__":
    main()
