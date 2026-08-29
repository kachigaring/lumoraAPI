"""
Phase 0 - the postcode layer.

Looks up UK postcodes on postcodes.io (free, no API key), stores the coordinates
in a local table so the same postcode is never fetched twice, and measures the
straight-line distance between any two postcodes in miles.

Everything else in the engine depends on this.
"""
from __future__ import annotations

import math
import time

import requests

from .db import connect
from .log import get_logger

log = get_logger()

API_BASE = "https://api.postcodes.io"
TIMEOUT = 20
EARTH_RADIUS_MILES = 3958.7613


def normalise(postcode: str) -> str:
    """'  ec1a 1bb ' -> 'EC1A1BB'"""
    return "".join((postcode or "").split()).upper()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _get_cached(conn, norm: str):
    return conn.execute(
        "SELECT * FROM postcodes WHERE postcode_norm = ?", (norm,)
    ).fetchone()


def _store(conn, norm: str, result: dict | None) -> None:
    if result is None:
        conn.execute(
            "INSERT OR REPLACE INTO postcodes "
            "(postcode_norm, postcode, latitude, longitude, admin_district, region, valid, looked_up_at) "
            "VALUES (?, ?, NULL, NULL, NULL, NULL, 0, ?)",
            (norm, norm, _now()),
        )
    else:
        conn.execute(
            "INSERT OR REPLACE INTO postcodes "
            "(postcode_norm, postcode, latitude, longitude, admin_district, region, valid, looked_up_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (
                norm,
                result.get("postcode"),
                result.get("latitude"),
                result.get("longitude"),
                result.get("admin_district"),
                result.get("region"),
                _now(),
            ),
        )
    conn.commit()


def _http_single(postcode: str) -> dict | None:
    """One postcode from postcodes.io. Returns the 'result' dict, or None for 404 (unknown postcode)."""
    url = f"{API_BASE}/postcodes/{requests.utils.quote(postcode)}"
    r = requests.get(url, timeout=TIMEOUT)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json().get("result")


def lookup(postcode: str, conn=None) -> dict | None:
    """
    Return {postcode, latitude, longitude, admin_district, region} for one postcode,
    or None if postcodes.io does not recognise it.

    Reads the local cache first; only calls the network on a miss.
    """
    own = conn is None
    conn = conn or connect()
    try:
        norm = normalise(postcode)
        if not norm:
            return None

        row = _get_cached(conn, norm)
        if row is None:
            log.info(f"Looking up postcode {norm} on postcodes.io ...")
            try:
                result = _http_single(norm)
            except requests.RequestException as e:
                log.error(
                    f"Could not reach postcodes.io for {norm}: {e}\n"
                    f"  -> Check your internet connection and run the command again. "
                    f"Postcodes already looked up are cached, so it will resume."
                )
                raise
            _store(conn, norm, result)
            row = _get_cached(conn, norm)

        if not row or not row["valid"]:
            return None
        return {
            "postcode": row["postcode"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "admin_district": row["admin_district"],
            "region": row["region"],
        }
    finally:
        if own:
            conn.close()


def bulk_warm(postcodes: list[str], conn=None) -> int:
    """
    Fetch many postcodes in batches of 100 and fill the cache. Call this before a
    big join so the per-row lookups are all local. Returns how many new postcodes
    were fetched.
    """
    own = conn is None
    conn = conn or connect()
    fetched = 0
    try:
        todo: list[str] = []
        seen: set[str] = set()
        for pc in postcodes:
            norm = normalise(pc)
            if norm and norm not in seen and _get_cached(conn, norm) is None:
                seen.add(norm)
                todo.append(norm)

        if not todo:
            return 0

        log.info(f"Bulk looking up {len(todo)} new postcodes on postcodes.io ...")
        for i in range(0, len(todo), 100):
            chunk = todo[i : i + 100]
            try:
                r = requests.post(
                    f"{API_BASE}/postcodes", json={"postcodes": chunk}, timeout=TIMEOUT
                )
                r.raise_for_status()
            except requests.RequestException as e:
                log.error(
                    f"Bulk postcode lookup failed for one batch: {e}\n"
                    f"  -> Not fatal. Those postcodes will be looked up one at a time later."
                )
                continue
            for item in r.json().get("result", []):
                q = normalise(item.get("query", ""))
                if q:
                    _store(conn, q, item.get("result"))
                    fetched += 1
            time.sleep(0.2)  # be polite to the free API
        return fetched
    finally:
        if own:
            conn.close()


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def distance_miles(postcode_a: str, postcode_b: str, conn=None) -> float | None:
    """
    Straight-line (great-circle) distance between two UK postcodes, in miles.
    Returns None if either postcode is invalid.
    """
    own = conn is None
    conn = conn or connect()
    try:
        a = lookup(postcode_a, conn)
        b = lookup(postcode_b, conn)
        if not a or not b:
            return None
        return _haversine_miles(
            a["latitude"], a["longitude"], b["latitude"], b["longitude"]
        )
    finally:
        if own:
            conn.close()
