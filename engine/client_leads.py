"""
Lumora - Phase 1 - build the nursery client call list.

Run:   python client_leads.py
       python client_leads.py --reload-providers      (after a new Ofsted file)

Produces, in output/:
   client_leads_YYYY-MM-DD.csv          <- open this and start calling
   review_vacancies_YYYY-MM-DD.csv      <- agency / job-board posts, for reference
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

import yaml

from lumora.db import connect, init_schema
from lumora.emailer import send_report
from lumora.exclusions import load_exclusions
from lumora.fresh_roles import build_fresh_roles
from lumora.leads import build_client_leads
from lumora.log import get_logger
from lumora.providers import load_providers
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
        have_providers = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
        if reload_providers or not have_providers:
            load_providers(cfg, conn)
        else:
            log.info(f"Using existing Ofsted data ({have_providers:,} nurseries). "
                     f"Run with --reload-providers after downloading a newer file.")

        load_exclusions(conn)

        if not have_keys():
            log.error(
                "Cannot build the list without live vacancies.\n"
                "  -> Put your Adzuna keys in engine/.env (copy from .env.example) and run again."
            )
            return 2
        fetch_vacancies(cfg, conn)

        fresh = build_fresh_roles(cfg, conn)
        leads = build_client_leads(cfg, conn)

        # ---- 1. FRESH ROLES - the main working list, one row per advert ----
        fresh_path = out_dir / f"fresh_roles_{today}.csv"
        with fresh_path.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow([
                "posted", "days_old", "job_title", "employer", "town", "area",
                "salary", "advert_link", "find_phone",
            ])
            for r in fresh:
                wr.writerow([
                    r["posted"], r["days_old"], r["job_title"], r["employer"], r["town"],
                    r["area"], r["salary"], r["advert_link"], r["find_phone"],
                ])

        # ---- 2. BY EMPLOYER - a call sheet grouped by nursery group ----
        leads_path = out_dir / f"by_employer_{today}.csv"
        with leads_path.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow([
                "rank", "score", "employer", "town", "live_vacancies", "vacancy_titles",
                "newest_advert", "salary_hint", "ofsted_match", "ofsted_setting",
                "postcode", "places", "rating", "example_advert",
            ])
            for i, g in enumerate(leads, 1):
                wr.writerow([
                    i, g["score"], g["employer"], g["town"], g["vacancy_count"],
                    g["vacancy_titles"], g["newest_vacancy"], g["salary_hint"],
                    g["ofsted_match"], g["ofsted_name"], g["postcode"], g["places"],
                    g["rating"], g["example_advert"],
                ])

        # ---- 3. reference: what was filtered out as agency / job board ----
        review_path = out_dir / f"agency_posts_{today}.csv"
        rows = conn.execute(
            "SELECT employer_name, title, location_text, created_date, redirect_url "
            "FROM vacancies WHERE is_agency = 1 ORDER BY created_date DESC"
        ).fetchall()
        with review_path.open("w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(["employer", "title", "location", "posted", "advert"])
            for r in rows:
                wr.writerow(list(r))

    log.info("")
    log.info(f"DONE.")
    log.info(f"  1. WORK FROM THIS:  {fresh_path.name}   ({len(fresh)} fresh roles, newest first)")
    log.info(f"  2. Call sheet:      {leads_path.name}   ({len(leads)} nursery groups)")
    log.info(f"  3. Ignored (agencies): {review_path.name}   ({len(rows)} posts)")
    log.info(f"  Files are in: {out_dir}")

    body = (
        f"Lumora lead engine - {today}\n\n"
        f"  {len(fresh)} fresh nursery roles (last few days), newest first  -> fresh_roles CSV\n"
        f"  {len(leads)} nursery groups hiring, scored                       -> by_employer CSV\n"
        f"  {len(rows)} agency / job-board posts set aside                   -> agency_posts CSV\n\n"
        f"Work from fresh_roles. The 'find_phone' column links to a Google search "
        f"for each nursery's number. The 'advert_link' column opens the real job ad.\n"
    )
    send_report(f"Lumora leads {today} - {len(fresh)} fresh roles", body,
                [fresh_path, leads_path, review_path])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
