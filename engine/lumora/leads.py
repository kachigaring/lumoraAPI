"""
Phase 1, step 3+4 - turn live vacancies into a scored client call list.

Design note: nursery adverts on Adzuna are usually posted under the group brand
("Kids Planet", "Busy Bees", "Storal"...), not the individual Ofsted setting
name, and Adzuna gives no full address. So the lead is built at the level the
owner actually phones: EMPLOYER + TOWN + their live roles + the advert link.

Ofsted details (registered places, latest rating, postcode) are attached only
when an Ofsted setting in the same town matches the employer name confidently.
Unmatched leads are still kept - they're real vacancies.
"""
from __future__ import annotations

import json
import re
from collections import Counter

from rapidfuzz import fuzz

from .db import connect
from .log import get_logger

log = get_logger()

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")
_TRAILING = (" ltd", " limited", " llp", " uk", " group")
# extra words trimmed only when building the grouping key, so brand variants
# like "Busy Bees" and "Busy Bees Nurseries" land in the same lead
_KEY_TRAILING = (
    "day nurseries", "day nursery", "nurseries", "nursery",
    "childcare", "day care", "daycare", "pre school", "preschool",
)
_NON_ENGLAND = {"scotland", "wales", "northern ireland"}


def light_norm(name: str) -> str:
    """Lowercase, strip punctuation and a few trailing corporate words. Keeps
    distinguishing words like 'nursery' / 'montessori'."""
    s = _PUNCT.sub(" ", (name or "").lower())
    s = _SPACE.sub(" ", s).strip()
    for t in _TRAILING:
        if s.endswith(t):
            s = s[: -len(t)].strip()
    return s


def _key_name(employer: str) -> str:
    s = light_norm(employer)
    changed = True
    while changed:
        changed = False
        for t in _KEY_TRAILING:
            if s.endswith(" " + t) or s == t:
                s = s[: -len(t)].strip()
                changed = True
    return s or light_norm(employer)


def _key(employer: str, town: str) -> str:
    return f"{_key_name(employer)}@@{(town or '').lower().strip()}"


def _in_england(area_json: str) -> bool:
    try:
        area = [a.lower() for a in json.loads(area_json or "[]")]
    except (ValueError, TypeError):
        return True
    return not any(x in _NON_ENGLAND for x in area)


def build_client_leads(config: dict, conn=None) -> list[dict]:
    own = conn is None
    conn = conn or connect()
    try:
        w = config["scoring"]["weights"]
        big_places = int(config["scoring"].get("large_setting_places", 40))
        senior_kw = [s.lower() for s in config["scoring"].get("senior_role_keywords", [])]
        top_n = int(config["scoring"].get("top_n", 120))
        enrich_min = int(config.get("ofsted_enrich", {}).get("name_score_min", 88))

        # ---- exclusions (existing clients / do-not-contact) ----
        excl_norms = {
            light_norm(r[0]) for r in conn.execute("SELECT raw_name FROM exclusions").fetchall()
        }

        # ---- all providers, for best-effort enrichment ----
        all_providers = [dict(r) for r in conn.execute(
            "SELECT urn, provider_name, postcode, places, local_authority, "
            "last_inspection_date, inspection_outcome FROM providers WHERE provider_name <> ''"
        )]
        for p in all_providers:
            p["_la_lc"] = (p["local_authority"] or "").lower().strip()
            p["_name_norm"] = light_norm(p["provider_name"])

        # ---- recent contact (for the 'not contacted in 60 days' point) ----
        recent = {
            r[0] for r in conn.execute(
                "SELECT DISTINCT urn FROM contact_log WHERE contacted_at >= date('now','-60 day')"
            )
        }

        england_only = bool(config["vacancies"].get("england_only", True))

        # ---- group non-agency vacancies ----
        groups: dict[str, dict] = {}
        dropped_region = 0
        for v in conn.execute(
            "SELECT employer_name, town, admin_district, location_text, area_json, title, "
            "created_date, redirect_url, salary_min, salary_max "
            "FROM vacancies WHERE is_agency = 0"
        ):
            emp = (v["employer_name"] or "").strip()
            if not emp:
                continue
            if england_only and not _in_england(v["area_json"]):
                dropped_region += 1
                continue
            g = groups.setdefault(
                _key(emp, v["town"]),
                {
                    "names": Counter(),
                    "town": (v["town"] or "").strip(),
                    "area": (v["admin_district"] or "").strip(),
                    "location_text": v["location_text"] or "",
                    "titles": set(),
                    "count": 0,
                    "newest": "",
                    "url": "",
                    "sal_min": None,
                    "sal_max": None,
                },
            )
            g["names"][emp] += 1
            g["count"] += 1
            if v["title"]:
                g["titles"].add(v["title"])
            if (v["created_date"] or "") > g["newest"]:
                g["newest"] = v["created_date"] or ""
            if not g["url"] and v["redirect_url"]:
                g["url"] = v["redirect_url"]
            if v["salary_min"] and (g["sal_min"] is None or v["salary_min"] < g["sal_min"]):
                g["sal_min"] = v["salary_min"]
            if v["salary_max"] and (g["sal_max"] is None or v["salary_max"] > g["sal_max"]):
                g["sal_max"] = v["salary_max"]

        leads = []
        for g in groups.values():
            employer = g["names"].most_common(1)[0][0]
            if light_norm(employer) in excl_norms or _key_name(employer) in excl_norms:
                continue

            emp_norm = light_norm(employer)
            loc_lc = g["location_text"].lower()

            # try to enrich from Ofsted: a setting whose town/LA appears in the
            # advert location AND whose name matches the employer well
            best = None
            best_score = 0
            for p in all_providers:
                la = p["_la_lc"]
                if not la or (la not in loc_lc and g["town"].lower() != la):
                    continue
                s = fuzz.token_set_ratio(emp_norm, p["_name_norm"])
                if s > best_score:
                    best_score, best = s, p
            matched = best if best_score >= enrich_min else None

            titles = sorted(g["titles"])
            score = w["live_vacancy_7d"]
            if g["count"] >= 2:
                score += w["multiple_vacancies"]
            if any(any(k in t.lower() for k in senior_kw) for t in titles):
                score += w["senior_role"]
            if matched and (matched["places"] or 0) >= big_places:
                score += w["large_setting"]
            if not matched or matched["urn"] not in recent:
                score += w["not_contacted_60d"]
            if matched and matched["last_inspection_date"]:
                try:
                    import datetime as _dt
                    yrs = (_dt.date.today() - _dt.date.fromisoformat(matched["last_inspection_date"])).days / 365.25
                    if yrs > 4:
                        score += w["stale_inspection"]
                except ValueError:
                    pass

            leads.append(
                {
                    "score": min(100, score),
                    "employer": employer,
                    "town": g["town"] or g["area"],
                    "location": g["location_text"],
                    "vacancy_count": g["count"],
                    "vacancy_titles": " | ".join(titles),
                    "newest_vacancy": g["newest"],
                    "salary_hint": _salary_hint(g["sal_min"], g["sal_max"]),
                    "ofsted_match": "Y" if matched else "",
                    "ofsted_name": matched["provider_name"] if matched else "",
                    "postcode": matched["postcode"] if matched else "",
                    "places": matched["places"] if matched else "",
                    "rating": matched["inspection_outcome"] if matched else "",
                    "example_advert": g["url"],
                }
            )

        leads.sort(key=lambda x: (x["score"], x["vacancy_count"]), reverse=True)
        enriched = sum(1 for x in leads if x["ofsted_match"] == "Y")
        if dropped_region:
            log.info(f"leads: dropped {dropped_region} adverts outside England.")
        log.info(
            f"leads: {len(leads):,} employer/town leads "
            f"({enriched:,} matched to an Ofsted setting); taking top {top_n}."
        )
        return leads[:top_n]
    finally:
        if own:
            conn.close()


def _salary_hint(lo, hi) -> str:
    if not lo and not hi:
        return ""
    if lo and hi and int(lo) != int(hi):
        return f"£{int(lo):,}-£{int(hi):,}"
    return f"£{int(lo or hi):,}"
