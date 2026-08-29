"""SQLite storage for the Lumora lead engine.

One local file at engine/data/lumora.sqlite. It is never committed to GitHub
(see .gitignore) because it will hold provider and, later, candidate data.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lumora.sqlite"

SCHEMA = """
-- Phase 0: cached postcode coordinates (from postcodes.io)
CREATE TABLE IF NOT EXISTS postcodes (
    postcode_norm    TEXT PRIMARY KEY,   -- uppercase, no spaces
    postcode         TEXT,               -- as postcodes.io returns it
    latitude         REAL,
    longitude        REAL,
    admin_district   TEXT,
    region           TEXT,
    valid            INTEGER NOT NULL DEFAULT 1,  -- 0 = postcodes.io has no such postcode
    looked_up_at     TEXT
);

-- Phase 1: Ofsted registered childcare providers
CREATE TABLE IF NOT EXISTS providers (
    urn                   TEXT PRIMARY KEY,
    provider_name         TEXT,
    provider_type         TEXT,
    postcode              TEXT,
    postcode_norm         TEXT,
    places                INTEGER,
    last_inspection_date  TEXT,
    inspection_outcome    TEXT,
    local_authority       TEXT,
    phone                 TEXT,
    ctps_checked          INTEGER NOT NULL DEFAULT 0,
    updated_at            TEXT
);

-- Phase 1: live vacancies (from Adzuna)
CREATE TABLE IF NOT EXISTS vacancies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT,
    external_id     TEXT,
    title           TEXT,
    employer_name   TEXT,
    employer_norm   TEXT,
    location_text   TEXT,
    admin_district  TEXT,
    salary_min      REAL,
    salary_max      REAL,
    created_date    TEXT,
    redirect_url    TEXT,
    is_agency       INTEGER NOT NULL DEFAULT 0,
    fetched_at      TEXT,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS vacancy_provider_match (
    vacancy_id  INTEGER PRIMARY KEY,
    urn         TEXT,
    method      TEXT,      -- 'exact' or 'fuzzy'
    score       REAL
);

CREATE TABLE IF NOT EXISTS unmatched_vacancies (
    vacancy_id  INTEGER PRIMARY KEY,
    reason      TEXT,
    created_at  TEXT
);

-- Phase 1: record of who has been contacted, for the "not contacted in 60 days" signal
CREATE TABLE IF NOT EXISTS contact_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    urn           TEXT,
    contacted_at  TEXT,
    note          TEXT
);

-- Owner-supplied lists: existing clients and do-not-contact
CREATE TABLE IF NOT EXISTS exclusions (
    name_norm       TEXT PRIMARY KEY,
    raw_name        TEXT,
    postcode_norm   TEXT,
    is_client       INTEGER NOT NULL DEFAULT 0,
    do_not_contact  INTEGER NOT NULL DEFAULT 0
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        if own:
            conn.close()
