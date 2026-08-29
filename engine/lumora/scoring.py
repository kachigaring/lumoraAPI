"""
Phase 1, step 4 - score each provider 0-100 and build the call list.

All weights come from config.yaml so they can be tuned without touching code.
Excluded outright: existing clients and anyone on the do-not-contact list.
"""
from __future__ import annotations

import datetime as dt

from .db import connect
from .log import get_logger
from .matching import normalise_name

log = get_logger()


def _years_since(iso_date: str | None) -> float | None:
    if not iso_date:
        return None
    try:
        d = dt.date.fromisoformat(iso_date)
    except ValueError:
        return None
    return (dt.date.today() - d).days / 365.25


def score_providers(config: dict, conn=None) -> list[dict]:
    own = conn is None
    conn = conn or connect()
    try:
        w = config["scoring"]["weights"]
        big_places = int(config["scoring"].get("large_setting_places", 40))
        senior_kw = [s.lower() for s in config["scoring"].get("senior_role_keywords", [])]
        strip_words = [s.lower() for s in config["matching"].get("strip_words", [])]

        # exclusion sets (name + optionally postcode)
        excl = conn.execute("SELECT name_norm, do_not_contact, is_client FROM exclusions").fetchall()
        excluded_names = {e["name_norm"] for e in excl}

        # gather live vacancies per provider (non-agency, matched)
        rows = conn.execute(
            """
            SELECT p.urn, p.provider_name, p.postcode, p.places,
                   p.last_inspection_date, p.inspection_outcome, p.local_authority, p.phone,
                   v.title, v.created_date, v.redirect_url, v.salary_min, v.salary_max
            FROM providers p
            JOIN vacancy_provider_match m ON m.urn = p.urn
            JOIN vacancies v ON v.id = m.vacancy_id
            WHERE v.is_agency = 0
            """
        ).fetchall()

        by_provider: dict[str, dict] = {}
        for r in rows:
            g = by_provider.setdefault(
                r["urn"],
                {
                    "urn": r["urn"],
                    "provider_name": r["provider_name"],
                    "postcode": r["postcode"],
                    "places": r["places"] or 0,
                    "last_inspection_date": r["last_inspection_date"],
                    "inspection_outcome": r["inspection_outcome"],
                    "local_authority": r["local_authority"],
                    "phone": r["phone"] or "",
                    "vacancies": [],
                },
            )
            g["vacancies"].append(
                {
                    "title": r["title"],
                    "created": r["created_date"],
                    "url": r["redirect_url"],
                    "salary_min": r["salary_min"],
                    "salary_max": r["salary_max"],
                }
            )

        # "contacted in last 60 days" set
        recent_contact = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT urn FROM contact_log "
                "WHERE contacted_at >= date('now','-60 day')"
            ).fetchall()
        }

        leads = []
        for urn, g in by_provider.items():
            if normalise_name(g["provider_name"], strip_words) in excluded_names:
                continue

            vlist = g["vacancies"]
            score = 0
            score += w["live_vacancy_7d"]                       # has >=1 live vacancy
            if len(vlist) >= 2:
                score += w["multiple_vacancies"]
            if any(any(k in (v["title"] or "").lower() for k in senior_kw) for v in vlist):
                score += w["senior_role"]
            if (g["places"] or 0) >= big_places:
                score += w["large_setting"]
            if urn not in recent_contact:
                score += w["not_contacted_60d"]
            yrs = _years_since(g["last_inspection_date"])
            if yrs is not None and yrs > 4:
                score += w["stale_inspection"]

            g["score"] = min(100, score)
            g["vacancy_count"] = len(vlist)
            g["vacancy_titles"] = " | ".join(sorted({v["title"] for v in vlist if v["title"]}))
            g["newest_vacancy"] = max((v["created"] for v in vlist if v["created"]), default="")
            g["example_url"] = next((v["url"] for v in vlist if v["url"]), "")
            leads.append(g)

        leads.sort(key=lambda x: (x["score"], x["vacancy_count"]), reverse=True)
        top_n = int(config["scoring"].get("top_n", 50))
        log.info(f"scoring: {len(leads):,} nurseries have a live vacancy; taking top {top_n}.")
        return leads[:top_n]
    finally:
        if own:
            conn.close()
