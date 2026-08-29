"""
The working list: every individual nursery vacancy, newest first.

This is what the owner works from day to day:
  - show the freshest roles to candidates (so they engage)
  - call the nursery that posted it, pitch a candidate, agree a fee

One row per advert. Agency / job-board posts and non-England roles are excluded.
Each row includes a ready-made Google search link to find the nursery's phone.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse

from .db import connect
from .leads import _in_england, light_norm
from .log import get_logger

log = get_logger()


def _phone_lookup_url(employer: str, town: str) -> str:
    q = f'"{employer}" {town} nursery phone number'
    return "https://www.google.com/search?q=" + urllib.parse.quote(q)


def _days_old(iso_date: str) -> int | None:
    try:
        return (dt.date.today() - dt.date.fromisoformat(iso_date)).days
    except (ValueError, TypeError):
        return None


def build_fresh_roles(config: dict, conn=None) -> list[dict]:
    own = conn is None
    conn = conn or connect()
    try:
        max_days = int(config["vacancies"].get("fresh_roles_max_days", 4))
        england_only = bool(config["vacancies"].get("england_only", True))

        excl = {light_norm(r[0]) for r in conn.execute("SELECT raw_name FROM exclusions")}

        rows = conn.execute(
            "SELECT employer_name, town, admin_district, location_text, area_json, title, "
            "created_date, redirect_url, salary_min, salary_max "
            "FROM vacancies WHERE is_agency = 0 ORDER BY created_date DESC"
        ).fetchall()

        seen: set[tuple] = set()
        out: list[dict] = []
        for v in rows:
            emp = (v["employer_name"] or "").strip()
            if not emp or light_norm(emp) in excl:
                continue
            if england_only and not _in_england(v["area_json"]):
                continue
            age = _days_old(v["created_date"])
            if age is None or age > max_days:
                continue
            town = (v["town"] or v["admin_district"] or "").strip()
            key = (light_norm(emp), (v["title"] or "").lower().strip(), town.lower())
            if key in seen:
                continue
            seen.add(key)

            lo, hi = v["salary_min"], v["salary_max"]
            if lo and hi and int(lo) != int(hi):
                salary = f"£{int(lo):,}-£{int(hi):,}"
            elif lo or hi:
                salary = f"£{int(lo or hi):,}"
            else:
                salary = ""

            out.append({
                "posted": v["created_date"],
                "days_old": age,
                "job_title": v["title"] or "",
                "employer": emp,
                "town": town,
                "area": v["admin_district"] or "",
                "salary": salary,
                "advert_link": v["redirect_url"] or "",
                "find_phone": _phone_lookup_url(emp, town),
            })

        log.info(f"fresh_roles: {len(out)} individual roles posted in the last {max_days} days.")
        return out
    finally:
        if own:
            conn.close()
