"""
B1 — Scheduled ETL: Auto-fetch NAV from mfapi.in every weekday at 8 PM
=======================================================================
Usage:
    python b1_cron_etl.py              # Run once immediately
    python b1_cron_etl.py --schedule   # Run as Python scheduler (weekdays 20:00)

Cron alternative (add via `crontab -e`):
    0 20 * * 1-5 /usr/bin/python3 /path/to/b1_cron_etl.py >> /path/to/logs/etl.log 2>&1
"""

import sys
import sqlite3
import logging
import argparse
import requests
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from time import sleep

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent.parent
DB_PATH   = BASE_DIR / "data" / "bluestock_mf.db"
LOG_DIR   = BASE_DIR / "logs"
LOG_PATH  = LOG_DIR / "etl_cron.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("etl_cron")

# ── Retry config ───────────────────────────────────────────────────────────────
MAX_RETRIES   = 3       # number of attempts per fund
RETRY_DELAY   = 5       # seconds to wait between retries
FETCH_TIMEOUT = 30      # seconds per request (increased from 15)

# ── Fund universe (scheme codes from mfapi.in) ─────────────────────────────────
# Format: { scheme_code: "Friendly Name" }
FUND_UNIVERSE: dict[int, str] = {
    119551: "Axis Bluechip Fund - Growth",
    120503: "Mirae Asset Large Cap Fund - Regular Growth",
    125498: "HDFC Top 100 Fund - Regular Plan - Growth",   # fixed: 100016 was stale
    112090: "Parag Parikh Flexi Cap Fund - Regular Growth",
    118989: "SBI Small Cap Fund - Regular Growth",
    101305: "ICICI Prudential Value Discovery Fund - Growth",
    122639: "Kotak Emerging Equity Fund - Regular Growth",
    118825: "Nippon India Small Cap Fund - Growth",
    110234: "DSP Midcap Fund - Regular Growth",
    125354: "Canara Robeco Bluechip Equity Fund - Regular Growth",
}

MFAPI_BASE = "https://api.mfapi.in/mf"


# ── Helpers ────────────────────────────────────────────────────────────────────

def is_weekday() -> bool:
    return date.today().weekday() < 5          # Mon–Fri = 0–4


def fetch_nav(scheme_code: int) -> pd.DataFrame | None:
    """
    Pull full NAV history for one scheme from mfapi.in.
    Retries up to MAX_RETRIES times on timeout or connection errors.
    """
    url = f"{MFAPI_BASE}/{scheme_code}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()

            meta = payload.get("meta", {})
            rows = payload.get("data", [])

            if not rows:
                log.warning("No data returned for scheme %d", scheme_code)
                return None

            df = pd.DataFrame(rows)                          # date, nav
            df["scheme_code"] = scheme_code
            df["scheme_name"] = meta.get("scheme_name", FUND_UNIVERSE.get(scheme_code, "Unknown"))
            df["fund_house"]  = meta.get("fund_house", "")
            df["scheme_type"] = meta.get("scheme_type", "")
            df["scheme_category"] = meta.get("scheme_category", "")
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
            df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")
            df.dropna(subset=["date", "nav"], inplace=True)
            df.sort_values("date", inplace=True)
            df.reset_index(drop=True, inplace=True)
            return df

        except requests.exceptions.Timeout:
            log.warning(
                "Timeout for scheme %d (attempt %d/%d) — retrying in %ds …",
                scheme_code, attempt, MAX_RETRIES, RETRY_DELAY,
            )
            if attempt < MAX_RETRIES:
                sleep(RETRY_DELAY)
            else:
                log.error("All %d attempts timed out for scheme %d", MAX_RETRIES, scheme_code)
                return None

        except requests.RequestException as exc:
            log.error("HTTP error for scheme %d: %s", scheme_code, exc)
            return None

        except Exception as exc:
            log.error("Unexpected error for scheme %d: %s", scheme_code, exc)
            return None


def upsert_to_db(df: pd.DataFrame, conn: sqlite3.Connection) -> int:
    """
    Insert-or-ignore NAV rows into nav_data table.
    Returns number of newly inserted rows.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nav_data (
            scheme_code   INTEGER,
            scheme_name   TEXT,
            fund_house    TEXT,
            scheme_type   TEXT,
            scheme_category TEXT,
            date          TEXT,
            nav           REAL,
            fetched_at    TEXT,
            PRIMARY KEY (scheme_code, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS etl_log (
            run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at      TEXT,
            funds_ok    INTEGER,
            funds_err   INTEGER,
            rows_added  INTEGER,
            status      TEXT
        )
    """)
    conn.commit()

    fetched_at = datetime.now().isoformat(timespec="seconds")
    df = df.copy()
    df["fetched_at"] = fetched_at
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    before = conn.execute("SELECT COUNT(*) FROM nav_data").fetchone()[0]
    df.to_sql("nav_data_staging", conn, if_exists="replace", index=False)

    conn.execute("""
        INSERT OR IGNORE INTO nav_data
            (scheme_code, scheme_name, fund_house, scheme_type,
             scheme_category, date, nav, fetched_at)
        SELECT scheme_code, scheme_name, fund_house, scheme_type,
               scheme_category, date, nav, fetched_at
        FROM nav_data_staging
    """)
    conn.execute("DROP TABLE IF EXISTS nav_data_staging")
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM nav_data").fetchone()[0]
    return after - before


# ── Core ETL job ───────────────────────────────────────────────────────────────

def run_etl() -> None:
    log.info("=" * 60)
    log.info("ETL JOB STARTED — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if not DB_PATH.exists():
        log.info("Database not found; will be created at %s", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    all_frames: list[pd.DataFrame] = []
    funds_ok = 0
    funds_err = 0

    for code, name in FUND_UNIVERSE.items():
        log.info("  Fetching  [%d]  %s", code, name[:55])
        df = fetch_nav(code)
        if df is not None:
            all_frames.append(df)
            funds_ok += 1
        else:
            funds_err += 1
        sleep(0.3)                                  # polite rate-limit

    rows_added = 0
    status = "SUCCESS"

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        rows_added = upsert_to_db(combined, conn)
        log.info("Upserted %d new rows into nav_data", rows_added)
    else:
        log.error("No data fetched — all funds failed.")
        status = "FAILED"

    # Write audit row
    conn.execute(
        "INSERT INTO etl_log (run_at, funds_ok, funds_err, rows_added, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), funds_ok, funds_err, rows_added, status),
    )
    conn.commit()
    conn.close()

    log.info(
        "ETL COMPLETE — funds_ok=%d  funds_err=%d  rows_added=%d  status=%s",
        funds_ok, funds_err, rows_added, status,
    )
    log.info("=" * 60)


# ── Scheduler wrapper ──────────────────────────────────────────────────────────

def run_with_python_scheduler() -> None:
    """Run via the `schedule` library — useful when cron is unavailable."""
    if not HAS_SCHEDULE:
        log.error("`schedule` package not installed. Run: pip install schedule")
        sys.exit(1)

    log.info("Python scheduler started. Job will run weekdays at 20:00.")
    log.info("(Ctrl+C to stop)")

    schedule.every().monday.at("20:00").do(run_etl)
    schedule.every().tuesday.at("20:00").do(run_etl)
    schedule.every().wednesday.at("20:00").do(run_etl)
    schedule.every().thursday.at("20:00").do(run_etl)
    schedule.every().friday.at("20:00").do(run_etl)

    while True:
        schedule.run_pending()
        sleep(30)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bluestock MF Cron ETL")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run as a persistent Python scheduler (weekdays 20:00)",
    )
    args = parser.parse_args()

    if args.schedule:
        run_with_python_scheduler()
    else:
        run_etl()
