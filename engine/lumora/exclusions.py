"""
Load the owner's own lists so they are removed from the call list:

  data/clients.csv           - nurseries you already work with
  data/do_not_contact.csv    - anyone not to be approached

Each file just needs a 'name' column; a 'postcode' column is optional.
Header names are case-insensitive. Missing files are fine - they're skipped.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .db import connect
from .leads import light_norm
from .log import get_logger
from .postcodes import normalise as norm_postcode

log = get_logger()
ENGINE_DIR = Path(__file__).resolve().parent.parent


def _read(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    if "name" not in df.columns:
        log.error(f"{path.name}: needs a column called 'name'. Skipping this file.")
        return None
    return df


def load_exclusions(conn=None) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        conn.execute("DELETE FROM exclusions")
        counts = {"clients": 0, "do_not_contact": 0}

        for fname, col in (("clients.csv", "is_client"), ("do_not_contact.csv", "do_not_contact")):
            df = _read(ENGINE_DIR / "data" / fname)
            if df is None:
                continue
            for _, r in df.iterrows():
                name = r.get("name", "").strip()
                if not name:
                    continue
                nn = light_norm(name)
                pc = norm_postcode(r.get("postcode", ""))
                conn.execute(
                    f"""INSERT INTO exclusions (name_norm, raw_name, postcode_norm, {col})
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(name_norm) DO UPDATE SET {col} = 1""",
                    (nn, name, pc),
                )
                counts["clients" if col == "is_client" else "do_not_contact"] += 1

        conn.commit()
        if counts["clients"] or counts["do_not_contact"]:
            log.info(
                f"exclusions: {counts['clients']} existing clients, "
                f"{counts['do_not_contact']} do-not-contact."
            )
        else:
            log.info("exclusions: none supplied yet (no data/clients.csv or data/do_not_contact.csv).")
        return counts
    finally:
        if own:
            conn.close()
