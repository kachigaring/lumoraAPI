"""
Phase 1, step 3 - join vacancies to Ofsted providers.

Two passes, per the spec:
  1. Exact match on a normalised employer name.
  2. Fuzzy match (rapidfuzz >= threshold) but ONLY when the vacancy's district
     looks like the provider's local authority - so we don't fuzzy-match
     "Little Stars" in Leeds to "Little Stars" in Cornwall.

Anything that doesn't clear the bar goes to `unmatched_vacancies` for the owner
to eyeball. We do not guess.
"""
from __future__ import annotations

import datetime as dt
import re

from rapidfuzz import fuzz, process

from .db import connect
from .log import get_logger

log = get_logger()

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")


def normalise_name(name: str, strip_words: list[str]) -> str:
    s = (name or "").lower()
    s = _PUNCT.sub(" ", s)
    s = _SPACE.sub(" ", s).strip()
    if strip_words:
        tokens = [t for t in s.split(" ") if t and t not in strip_words]
        # also strip multi-word phrases like "day nursery"
        s = " ".join(tokens)
        for phrase in strip_words:
            if " " in phrase:
                s = s.replace(phrase, " ")
        s = _SPACE.sub(" ", s).strip()
    return s


def _district_matches(vac_district: str, provider_la: str) -> bool:
    if not vac_district or not provider_la:
        return False
    a, b = vac_district.lower().strip(), provider_la.lower().strip()
    return a == b or a in b or b in a


def match_vacancies(config: dict, conn=None) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        strip_words = [w.lower() for w in config["matching"].get("strip_words", [])]
        threshold = int(config["matching"].get("fuzzy_threshold", 88))

        providers = conn.execute(
            "SELECT urn, provider_name, local_authority FROM providers WHERE provider_name <> ''"
        ).fetchall()
        prov_norm = {p["urn"]: normalise_name(p["provider_name"], strip_words) for p in providers}
        prov_la = {p["urn"]: (p["local_authority"] or "") for p in providers}
        # exact-match index: normalised name -> list of urns
        exact_index: dict[str, list[str]] = {}
        for urn, n in prov_norm.items():
            if n:
                exact_index.setdefault(n, []).append(urn)

        # only match non-agency vacancies to providers; agency ones stay as their own leads
        vacancies = conn.execute(
            "SELECT id, employer_name, admin_district FROM vacancies WHERE is_agency = 0"
        ).fetchall()

        now = dt.datetime.now().isoformat(timespec="seconds")
        exact_hits = fuzzy_hits = unmatched = 0

        # clear previous run's matches so re-running is clean
        conn.execute("DELETE FROM vacancy_provider_match")
        conn.execute("DELETE FROM unmatched_vacancies")

        urns = list(prov_norm.keys())
        norm_list = [prov_norm[u] for u in urns]

        for v in vacancies:
            vn = normalise_name(v["employer_name"], strip_words)
            if not vn:
                conn.execute(
                    "INSERT INTO unmatched_vacancies (vacancy_id, reason, created_at) VALUES (?, ?, ?)",
                    (v["id"], "no usable employer name", now),
                )
                unmatched += 1
                continue

            # pass 1: exact
            if vn in exact_index:
                candidates = exact_index[vn]
                # if several providers share the name, prefer one in the same district
                pick = next(
                    (u for u in candidates if _district_matches(v["admin_district"], prov_la[u])),
                    candidates[0],
                )
                conn.execute(
                    "INSERT INTO vacancy_provider_match (vacancy_id, urn, method, score) VALUES (?, ?, 'exact', 100)",
                    (v["id"], pick),
                )
                exact_hits += 1
                continue

            # pass 2: fuzzy, district-guarded
            best = process.extractOne(vn, norm_list, scorer=fuzz.token_sort_ratio)
            if best and best[1] >= threshold:
                urn = urns[best[2]]
                if _district_matches(v["admin_district"], prov_la[urn]):
                    conn.execute(
                        "INSERT INTO vacancy_provider_match (vacancy_id, urn, method, score) VALUES (?, ?, 'fuzzy', ?)",
                        (v["id"], urn, float(best[1])),
                    )
                    fuzzy_hits += 1
                    continue

            conn.execute(
                "INSERT INTO unmatched_vacancies (vacancy_id, reason, created_at) VALUES (?, ?, ?)",
                (v["id"], "no confident provider match", now),
            )
            unmatched += 1

        conn.commit()
        log.info(
            f"matching: {exact_hits:,} exact, {fuzzy_hits:,} fuzzy, "
            f"{unmatched:,} left for manual review."
        )
        return {"exact": exact_hits, "fuzzy": fuzzy_hits, "unmatched": unmatched}
    finally:
        if own:
            conn.close()
