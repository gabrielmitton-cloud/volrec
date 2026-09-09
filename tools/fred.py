"""Minimal FRED client. Free API key, registered at fredaccount.stlouisfed.org.

Deliberately generic. As of 9 Sep 2026 nothing in the analysis consumes this
yet, on purpose: a meeting with a volatility researcher on Fri 11 Sep is
expected to name specific series, and wiring series in before knowing which
ones matter is how a project ends up with a pile of macro regressors fitted to
six independent episodes. See HANDOFF section 11.1.

So: the transport is built and tested, the choice of series is not made.

  export FRED_KEY=...
  python tools/fred.py VIXCLS                # print a summary of one series
  python tools/fred.py --check               # verify the key works

In code:
  from tools.fred import series
  obs = series("VIXCLS")                     # {"YYYY-MM-DD": float}

LICENCE. FRED redistributes Cboe indices under permission and requires
citation. Cite the source; do NOT mirror raw series into this public repo.
Derived values only. The cache below is gitignored for exactly this reason.
"""
import json, os, sys, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

BASE = "https://api.stlouisfed.org/fred"
CACHE = Path(__file__).resolve().parent.parent / "data" / "fred_cache.json"
UA = "volrec-research/1.0 (github.com/gabrielmitton-cloud/volrec)"


def _key():
    k = os.environ.get("FRED_KEY")
    if not k:
        sys.exit("FRED_KEY not set. Free key: https://fredaccount.stlouisfed.org/apikeys\n"
                 "Store it as a GitHub Actions secret, never in a file.")
    return k


def _get(path, **params):
    params.update(api_key=_key(), file_type="json")
    req = Request(f"{BASE}/{path}?{urlencode(params)}", headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def series(series_id, start=None, end=None, use_cache=True):
    """Daily observations as {"YYYY-MM-DD": float}. Missing values dropped.

    FRED encodes a missing observation as "." rather than null or 0. Coercing
    that to 0.0 would silently inject a zero-volatility day, so it is dropped.
    """
    cache = json.loads(CACHE.read_text()) if (use_cache and CACHE.exists()) else {}
    ck = f"{series_id}|{start or ''}|{end or ''}"
    if use_cache and ck in cache:
        return cache[ck]
    p = {"series_id": series_id}
    if start: p["observation_start"] = start
    if end:   p["observation_end"] = end
    j = _get("series/observations", **p)
    out = {}
    for o in j.get("observations", []):
        v = o.get("value")
        if v and v != ".":
            try:
                out[o["date"]] = float(v)
            except ValueError:
                pass
    if use_cache:
        cache[ck] = out
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
    return out


def meta(series_id):
    """Title, units, frequency, coverage, and whether FRED marks it discontinued.

    Worth calling before designing around any series: FRED's DISCONTINUED tag
    was verified stale for VXSLV and VXGDX on 6 Sep 2026 (both relaunched in
    2025 and Cboe still publishes them). Treat the tag as a prompt to check the
    source, not as fact.
    """
    s = (_get("series", series_id=series_id).get("seriess") or [{}])[0]
    return {
        "id": s.get("id"), "title": s.get("title"), "units": s.get("units_short"),
        "frequency": s.get("frequency_short"),
        "start": s.get("observation_start"), "end": s.get("observation_end"),
        "last_updated": s.get("last_updated"),
        "discontinued": "DISCONTINUED" in (s.get("title") or "").upper(),
    }


def main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] == "--check":
        m = meta("VIXCLS")
        obs = series("VIXCLS", start="2026-01-01", use_cache=False)
        print(f"FRED key works.\n  {m['id']}: {m['title']}")
        print(f"  coverage {m['start']} to {m['end']}, {m['frequency']}, "
              f"updated {m['last_updated']}")
        print(f"  {len(obs)} observations since 2026-01-01, "
              f"latest {max(obs)} = {obs[max(obs)]}")
        return
    for sid in args:
        m = meta(sid)
        obs = series(sid, use_cache=False)
        flag = "  [FRED SAYS DISCONTINUED - verify against Cboe]" if m["discontinued"] else ""
        print(f"{sid}: {m['title']}{flag}")
        print(f"  {len(obs)} obs, {min(obs) if obs else '-'} to {max(obs) if obs else '-'}, "
              f"units {m['units']}, freq {m['frequency']}")


if __name__ == "__main__":
    main()
