"""
Lumora - Phase 1 - build the nursery client call list.

Run:   python client_leads.py
       python client_leads.py --reload-providers      (after a new Ofsted file)

Produces, in output/:
   client_leads_YYYY-MM-DD.csv          <- open this and start calling
   unmatched_vacancies_YYYY-MM-DD.csv   <- vacancies we could not tie to a nursery
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

import yaml

from lumora.db import connect, init_schema
from lumora.exclusions import load_exclusions
from lumora.log import get_logger
from lumora.matching import match_vacancies
from lumora.providers import load_providers
from lumora.scoring import score_providers
from lumora.vacancies import fetch_vacancies, have_keys

log = get_logger()
ENGINE_DIR = Path(__file__).resolve().parent


def main() -> int:
    reload_providers = "--reload-providers" in sys.argv
    cfg = yaml.safe_load((ENGINE_DIR / "config.yaml").read_text(encoding="utf-8"))
    init_schema()

    today = dt.date.today().isoformat()
    out_dir = ENGINE_DIR / cfg["output"].get("dir", "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    with connect() as conn:
        # 1. nursery base table
        have_providers = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
        if reload_providers or not have_providers:
            load_providers(cfg, conn)
        else:
            log.info(f"Using existing providers table ({have_providers:,} nurseries). "
                     f"Add --reload-providers after downloading a new Ofsted file.")

        # 2. owner's own lists
        load_exclusions(conn)

        # 3. live vacancies
        if not have_keys():
            log.error(
                "Cannot build the list without live vacancies.\n"
                "  -> Put your Adzuna keys in engine/.env (copy from .env.example) and run again."
            )
            return 2
        fetch_vacancies(cfg, conn)

        # 4. join vacancies to nurseries
        match_vacancies(cfg, conn)

        # 5. score and rank
        leads = score_providers(cfg, conn)

        # ---- write the call list ----
        leads_path = out_dir / f"client_leads_{today}.csv"
        with leads_path.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow([
                "rank", "score", "nursery", "postcode", "local_authority", "phone",
                "live_vacancies", "vacancy_titles", "newest_vacancy",
                "inspection_outcome", "places", "example_advert",
            ])
            for i, g in enumerate(leads, 1):
                wr.writerow([
                    i, g["score"], g["provider_name"], g["postcode"], g["local_authority"],
                    g["phone"], g["vacancy_count"], g["vacancy_titles"], g["newest_vacancy"],
                    g["inspection_outcome"], g["places"], g["example_url"],
                ])

        # ---- write the review file ----
        unmatched_path = out_dir / f"unmatched_vacancies_{today}.csv"
        rows = conn.execute(
            """SELECT v.employer_name, v.title, v.location_text, v.created_date,
                      v.redirect_url, u.reason
               FROM unmatched_vacancies u JOIN vacancies v ON v.id = u.vacancy_id
               WHERE v.is_agency = 0
               ORDER BY v.created_date DESC"""
        ).fetchall()
        with unmatched_path.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(["employer", "title", "location", "posted", "advert", "reason"])
            for r in rows:
                wr.writerow(list(r))

    log.info("")
    log.info(f"DONE.  Call list:  {leads_path}")
    log.info(f"       To review:  {unmatched_path}  ({len(rows)} rows)")
    log.info(f"       {len(leads)} nurseries on the call list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
