"""
Phase 1, step 2 - the buying signal: live vacancies from Adzuna.

One search per keyword (keywords live in config.yaml). Results are stored in the
`vacancies` table, de-duplicated on (source, external_id). Postings from
competitor agencies, job boards and training providers are kept but flagged
is_agency = 1 so they stay off the call list.

Needs ADZUNA_APP_ID and ADZUNA_APP_KEY in engine/.env
(free from https://developer.adzuna.com/).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time

import requests
from dotenv import load_dotenv

from .db import connect
from .log import get_logger

log = get_logger()
load_dotenv()

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
TIMEOUT = 30


def have_keys() -> bool:
    return bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))


def looks_like_agency(employer: str, blocklist: list[str], name_contains: list[str]) -> bool:
    e = f" {(employer or '').lower().strip()} "
    if any(bad in e for bad in blocklist):
        return True
    if any(term in e for term in name_contains):
        return True
    return False


def _area_bits(loc: dict) -> tuple[str, str, str]:
    """Return (admin_district, town, area_json) from an Adzuna location object."""
    area = loc.get("area") or []
    admin_district = area[-1] if area else ""
    town = area[-2] if len(area) >= 2 else admin_district
    return admin_district, town, json.dumps(area)


def fetch_vacancies(config: dict, conn=None) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        if not have_keys():
            log.error(
                "No Adzuna keys found.\n"
                "  -> Copy engine/.env.example to engine/.env and paste your "
                "ADZUNA_APP_ID and ADZUNA_APP_KEY, then run again."
            )
            raise RuntimeError("missing Adzuna keys")

        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")
        vcfg = config["vacancies"]
        country = vcfg.get("adzuna_country", "gb")
        keywords = vcfg.get("nursery_keywords", [])
        blocklist = [b.lower() for b in config.get("agency_blocklist", [])]
        name_contains = [c.lower() for c in config.get("agency_name_contains", [])]

        now = dt.datetime.now().isoformat(timespec="seconds")
        fetched = 0

        # a fresh run replaces the vacancy set so old adverts don't linger
        conn.execute("DELETE FROM vacancies")

        for kw in keywords:
            url = f"{ADZUNA_BASE}/{country}/search/1"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": vcfg.get("results_per_page", 50),
                "what": kw,
                "max_days_old": vcfg.get("max_days_old", 7),
                "sort_by": "date",
                "content-type": "application/json",
            }
            try:
                r = requests.get(url, params=params, timeout=TIMEOUT)
                r.raise_for_status()
            except requests.RequestException as e:
                log.error(f"Adzuna request failed for '{kw}': {e}  (skipping this keyword)")
                continue

            results = r.json().get("results", [])
            log.info(f"'{kw}': {len(results)} vacancies in the last {params['max_days_old']} days.")
            for job in results:
                fetched += 1
                ext_id = str(job.get("id") or "")
                if not ext_id:
                    continue
                employer = (job.get("company") or {}).get("display_name", "")
                loc = job.get("location") or {}
                admin_district, town, area_json = _area_bits(loc)

                conn.execute(
                    """
                    INSERT INTO vacancies
                      (source, external_id, title, employer_name, employer_norm,
                       location_text, admin_district, town, area_json, latitude, longitude,
                       salary_min, salary_max, created_date, redirect_url, is_agency, fetched_at)
                    VALUES ('adzuna', ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, external_id) DO UPDATE SET
                      title=excluded.title, employer_name=excluded.employer_name,
                      location_text=excluded.location_text, admin_district=excluded.admin_district,
                      town=excluded.town, area_json=excluded.area_json,
                      latitude=excluded.latitude, longitude=excluded.longitude,
                      salary_min=excluded.salary_min, salary_max=excluded.salary_max,
                      created_date=excluded.created_date, redirect_url=excluded.redirect_url,
                      is_agency=excluded.is_agency, fetched_at=excluded.fetched_at
                    """,
                    (
                        ext_id,
                        job.get("title", ""),
                        employer,
                        loc.get("display_name", ""),
                        admin_district,
                        town,
                        area_json,
                        job.get("latitude"),
                        job.get("longitude"),
                        job.get("salary_min"),
                        job.get("salary_max"),
                        (job.get("created") or "")[:10],
                        job.get("redirect_url", ""),
                        1 if looks_like_agency(employer, blocklist, name_contains) else 0,
                        now,
                    ),
                )
            time.sleep(0.3)

        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        agencies = conn.execute("SELECT COUNT(*) FROM vacancies WHERE is_agency=1").fetchone()[0]
        log.info(
            f"vacancies table: {total:,} adverts kept "
            f"({agencies:,} filtered out as agency / job board / training provider)."
        )
        return {"fetched": fetched, "in_table": total, "agency": agencies}
    finally:
        if own:
            conn.close()
