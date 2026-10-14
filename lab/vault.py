#!/usr/bin/env python3
"""The sealed vault for the discovery system (sealed 14 Oct 2026, before any exploration).

Design (docs/superpowers/specs/2026-10-14-discovery-system-design.md): future explorer agents may hunt
for patterns only in the OPEN half of the lab's history; every pattern worth keeping is registered
before the SEALED half is read, and confirmed again on data that does not yet exist (H8's window, the
live panel after November). The split is by calendar quarter (adjacent days are correlated, so a
day-level split would leak), with the stress quarters divided evenly, and fixed by a seed and a hash
committed to git. Changing the split changes the hash and fails the pressure test.

This applies to NEW questions only. The lab's registered questions (lab/REGISTRATION.md) were answered
on the whole history before the vault existed and are unaffected.

  python lab/vault.py          # prints the split and its fingerprint
"""
import hashlib
import random

SEED = 20261014
FIRST, LAST = (2016, 1), (2026, 3)                       # 2016Q1 .. 2026Q3 (lab data ends 31 Aug 2026)
STRESS = ("2018Q1", "2018Q4", "2020Q1", "2022Q2", "2024Q3", "2025Q2")   # the lab's registered stress months
FINGERPRINT = "e4a02cd5dbdc3f80ef708ad837aba2f36dd21eac15cd7ed2b5ca970c3f2bd988"   # sealed 14 Oct 2026


def quarters():
    out, (y, q) = [], FIRST
    while (y, q) <= LAST:
        out.append(f"{y}Q{q}")
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def split():
    """(open, sealed): sorted lists of quarter labels. Deterministic."""
    rnd = random.Random(SEED)
    stress = list(STRESS)
    rest = [q for q in quarters() if q not in STRESS]
    rnd.shuffle(stress)
    rnd.shuffle(rest)
    sealed = stress[:len(stress) // 2] + rest[:len(rest) // 2]
    open_ = [q for q in quarters() if q not in sealed]
    return sorted(open_), sorted(sealed)


def fingerprint():
    return hashlib.sha256(",".join(split()[1]).encode()).hexdigest()


def quarter_of(day):
    return f"{day[:4]}Q{(int(day[5:7]) - 1) // 3 + 1}"


def is_sealed(day):
    """True if a date (YYYY-MM-DD) falls in the vault. Explorers must skip these."""
    return quarter_of(day) in set(split()[1])


if __name__ == "__main__":
    o, s = split()
    print(f"open ({len(o)}): {', '.join(o)}\nsealed ({len(s)}): {', '.join(s)}\nfingerprint {fingerprint()}")
