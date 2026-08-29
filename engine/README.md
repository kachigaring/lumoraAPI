# Lumora lead engine

The money part: produces a ranked **client call list** each morning — nurseries
that are hiring right now, sorted by how likely they are to pay an agency fee.

Python 3.11+ · SQLite · CSV output · driven by `config.yaml` · secrets in `.env`.

## Build order

| Phase | What | Status |
|---|---|---|
| **0** | Postcode layer — distance between any two UK postcodes, cached | ✅ done, `check_phase0.py` passes |
| **1** | Nursery client leads CSV — Ofsted providers + Adzuna vacancies + scoring | ✅ built, needs Adzuna keys to run live |
| 2+ | Biomed lab leads, candidate supply, matching, compliance | later (see the spec) |

## Running it

**Test the postcode layer:** double-click `run_phase0_test.bat`
(or `python check_phase0.py`). It should end with `PHASE 0 PASSED.`

**Build the nursery call list:** double-click `run_client_leads.bat`
(or `python client_leads.py`). Writes into `output/`:
- `client_leads_YYYY-MM-DD.csv` — open this and start calling
- `unmatched_vacancies_YYYY-MM-DD.csv` — vacancies we couldn't tie to a nursery

Needs `engine/.env` with your Adzuna keys first. After Ofsted publish a new
data file, run `python client_leads.py --reload-providers` once.

### Optional: your own lists

Drop either of these in `engine/data/` and they're removed from the call list:
- `clients.csv` — nurseries you already work with (column: `name`, optional `postcode`)
- `do_not_contact.csv` — anyone not to approach (same columns)

## First-time setup

1. Install Python from <https://python.org> (the installer, tick "Add to PATH").
2. In this `engine` folder: `python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and paste your Adzuna keys.

## Files

| Path | What |
|---|---|
| `config.yaml` | every setting — keywords, thresholds, score weights |
| `.env` | your API keys (never committed) |
| `lumora/postcodes.py` | Phase 0: postcodes.io lookup, cache, `distance_miles()` |
| `lumora/db.py` | the SQLite database and its tables |
| `lumora/log.py` | plain-English logging to screen + `logs/` |
| `check_phase0.py` | Phase 0 acceptance test |
| `data/` | the local database + downloaded source files (git-ignored) |
| `output/` | the CSVs it produces (git-ignored) |

## What the owner still needs to supply for Phase 1

- Adzuna App ID + Key → `.env`
- Existing client list (name, postcode) → to exclude current clients
- Do-not-contact list (name, postcode) → to exclude
- (Ofsted provider data is downloaded by the loader)
