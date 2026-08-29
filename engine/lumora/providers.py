"""
Phase 1, step 1 - load the nursery base table from Ofsted data.

Source: "Childcare providers and inspections: management information", provider
level CSV, published on GOV.UK / data.gov.uk. Covers every Ofsted registered
childcare provider in England.

We keep only real settings that could pay an agency fee:
  - provider type "Childcare on non-domestic premises" (excludes childminders)
  - status Active
  - registered places >= config providers.min_places  (default 20)

The loader UPSERTS on URN, so it is safe to re-run when a new file is published.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from .db import connect
from .log import get_logger
from .postcodes import normalise as norm_postcode

log = get_logger()

ENGINE_DIR = Path(__file__).resolve().parent.parent
HEADER_ROW = 2  # the real column names are on the 3rd line of the file

# Ofsted overall-effectiveness grade -> plain text
GRADE = {"1": "Outstanding", "2": "Good", "3": "Requires improvement", "4": "Inadequate"}

COLS = {
    "urn": "Provider URN",
    "name": "Provider name",
    "type": "Provider type",
    "subtype": "Provider subtype",
    "status": "Provider status",
    "postcode": "Provider postcode",
    "town": "Provider town",
    "la": "Local authority",
    "region": "Region",
    "places": "Places",
    "reif_date": "EYR REIF: Most recent: Inspection date",
    "oeif_date": "EYR OEIF: Most recent: Full inspection date",
    "oeif_grade": "EYR OEIF/CIF: Most recent: Overall effectiveness",
}


def _parse_uk_date(value) -> str | None:
    """'28/02/2020' -> '2020-02-28'. Returns None for blanks / bad values."""
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(str(value).strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _latest_date(*values) -> str | None:
    dates = [d for d in (_parse_uk_date(v) for v in values) if d]
    return max(dates) if dates else None


def load_providers(config: dict, conn=None) -> dict:
    """Load / refresh the providers table. Returns a small summary dict."""
    own = conn is None
    conn = conn or connect()
    try:
        source = config["providers"]["source_file"]
        min_places = int(config["providers"].get("min_places", 20))

        path = source if Path(source).is_absolute() else ENGINE_DIR / source
        if not Path(path).exists():
            log.error(
                f"Ofsted file not found at {path}\n"
                f"  -> Download the provider-level CSV from "
                f"gov.uk 'Childcare providers and inspections: management information' "
                f"and save it there, or ask for the loader to fetch it."
            )
            raise FileNotFoundError(path)

        log.info(f"Reading Ofsted provider file: {path}")
        df = pd.read_csv(path, header=HEADER_ROW, dtype=str, low_memory=False)
        total = len(df)

        keep_type = "Childcare on non-domestic premises"
        df = df[df[COLS["type"]] == keep_type]
        df = df[df[COLS["status"]].str.strip().str.lower() == "active"]

        df[COLS["places"]] = pd.to_numeric(df[COLS["places"]], errors="coerce")
        df = df[df[COLS["places"]].fillna(0) >= min_places]

        log.info(
            f"{total:,} rows in file -> {len(df):,} active non-domestic settings "
            f"with {min_places}+ places."
        )

        now = dt.datetime.now().isoformat(timespec="seconds")
        upserted = 0
        for _, r in df.iterrows():
            urn = str(r[COLS["urn"]]).strip()
            if not urn:
                continue
            pc = str(r[COLS["postcode"]] or "").strip()
            last_insp = _latest_date(r.get(COLS["reif_date"]), r.get(COLS["oeif_date"]))
            grade = str(r.get(COLS["oeif_grade"]) or "").strip()
            outcome = GRADE.get(grade, "")

            conn.execute(
                """
                INSERT INTO providers
                  (urn, provider_name, provider_type, postcode, postcode_norm, places,
                   last_inspection_date, inspection_outcome, local_authority, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(urn) DO UPDATE SET
                  provider_name        = excluded.provider_name,
                  provider_type        = excluded.provider_type,
                  postcode             = excluded.postcode,
                  postcode_norm        = excluded.postcode_norm,
                  places               = excluded.places,
                  last_inspection_date = excluded.last_inspection_date,
                  inspection_outcome   = excluded.inspection_outcome,
                  local_authority      = excluded.local_authority,
                  updated_at           = excluded.updated_at
                """,
                (
                    urn,
                    str(r[COLS["name"]] or "").strip(),
                    keep_type,
                    pc,
                    norm_postcode(pc),
                    int(r[COLS["places"]]) if pd.notna(r[COLS["places"]]) else None,
                    last_insp,
                    outcome,
                    str(r.get(COLS["la"]) or "").strip(),
                    now,
                ),
            )
            upserted += 1
        conn.commit()

        with_pc = conn.execute(
            "SELECT COUNT(*) FROM providers WHERE postcode_norm <> ''"
        ).fetchone()[0]
        log.info(f"providers table: {upserted:,} settings loaded, {with_pc:,} have a postcode.")
        return {"in_file": total, "loaded": upserted, "with_postcode": with_pc}
    finally:
        if own:
            conn.close()
