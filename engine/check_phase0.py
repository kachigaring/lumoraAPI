"""
Phase 0 acceptance check.

Confirms the two things the spec requires of the postcode layer:

  1. distance_miles() between two known postcodes is within half a mile of the
     true straight-line distance (checked with a second, independent formula).
  2. The second call for the same postcodes makes NO network request
     (i.e. the cache works).

Run:  python check_phase0.py        (or double-click run_phase0_test.bat)
"""
from __future__ import annotations

import math
import sys

from lumora import postcodes
from lumora.db import connect, init_schema

# Two well-known postcodes: central London and central Manchester.
A = "WC2N 5DN"   # Trafalgar Square
B = "M1 1AE"     # Manchester Piccadilly


def independent_distance(lat1, lon1, lat2, lon2) -> float:
    """Spherical law of cosines - a DIFFERENT formula from the module's haversine,
    so this is a genuine cross-check rather than the same code run twice."""
    r = 3958.7613
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    ang = math.acos(
        min(
            1.0,
            math.sin(lat1) * math.sin(lat2)
            + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1),
        )
    )
    return r * ang


def main() -> int:
    init_schema()

    # Start from cold for these two postcodes so we really test a fresh lookup.
    with connect() as conn:
        conn.execute(
            "DELETE FROM postcodes WHERE postcode_norm IN (?, ?)",
            (postcodes.normalise(A), postcodes.normalise(B)),
        )
        conn.commit()

    print("1) First call (network allowed) ...")
    a = postcodes.lookup(A)
    b = postcodes.lookup(B)
    if not a or not b:
        print("   FAIL: one of the test postcodes did not resolve. Check internet access.")
        return 1

    true_d = independent_distance(
        a["latitude"], a["longitude"], b["latitude"], b["longitude"]
    )
    d1 = postcodes.distance_miles(A, B)
    print(f"   distance_miles({A!r}, {B!r}) = {d1:.2f} miles")
    print(f"   independent cross-check        = {true_d:.2f} miles")
    if d1 is None or abs(d1 - true_d) > 0.5:
        print("   FAIL: more than half a mile from the independent distance.")
        return 1
    if not (120 < d1 < 200):
        print("   FAIL: distance is not in a sane range for London <-> Manchester.")
        return 1
    print("   OK: within half a mile of the true straight-line distance.")

    print("2) Second call must NOT touch the network ...")
    real_get, real_post = postcodes.requests.get, postcodes.requests.post

    def blocked(*_args, **_kwargs):
        raise AssertionError("network was used on the second call - the cache is not working")

    postcodes.requests.get = blocked
    postcodes.requests.post = blocked
    try:
        d2 = postcodes.distance_miles(A, B)
    finally:
        postcodes.requests.get = real_get
        postcodes.requests.post = real_post

    if d2 is None or abs(d2 - d1) > 0.001:
        print("   FAIL: second call did not return the same cached answer.")
        return 1
    print(f"   distance_miles(...) = {d2:.2f} miles, no network call. OK.")

    print("\nPHASE 0 PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
