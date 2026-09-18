"""Paths, API constants, cohort parameters and label definitions.

Implements the data strategy in PLAN.md:
- three dumps: cohort month (2016-01), window-fix month (2016-02), recent month (2026-08, capped scan)
- Population A (existing users active in cohort month) vs Population B (new signups in cohort month)
- two outcomes: retention (seenAt bands) and monetization (patron)
- voluntary vs involuntary churn segments; value tiers from playTime
"""
from __future__ import annotations

from pathlib import Path

# --- project layout ---------------------------------------------------------
LICHESS_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = LICHESS_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = LICHESS_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

for _d in (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- dumps ------------------------------------------------------------------
COHORT_MONTH = "2016-01"          # defines Populations A and B
WINDOW_MONTH = "2016-02"          # completes the equal 30-day post-signup window (PLAN §3)
RECENT_MONTH = "2026-08"          # behavioral cross-check for seenAt (PLAN §4)
RECENT_MONTH_MAX_GAMES = 5_000_000  # capped scan: stop after N games (~first days, ~1.5 GB)

DUMP_URL_TEMPLATE = (
    "https://database.lichess.org/standard/lichess_db_standard_rated_{month}.pgn.zst"
)
HISTORY_MONTHS = (COHORT_MONTH, WINDOW_MONTH)  # fully parsed into games tables


def dump_path(month: str) -> Path:
    return RAW_DIR / f"lichess_db_standard_rated_{month}.pgn.zst"


def games_parquet(month: str) -> Path:
    return INTERIM_DIR / f"games_{month.replace('-', '_')}.parquet"


RECENT_ACTIVE_USERS_PARQUET = INTERIM_DIR / f"active_users_{RECENT_MONTH.replace('-', '_')}.parquet"
USER_WINDOW_PARQUET = INTERIM_DIR / "user_window_features.parquet"
COHORT_PARQUET = PROCESSED_DIR / f"cohort_{COHORT_MONTH.replace('-', '_')}.parquet"

# --- cohort month boundaries (ms epoch) -------------------------------------
COHORT_MONTH_START_MS = 1451606400000  # 2016-01-01T00:00:00Z
COHORT_MONTH_END_MS = 1454284800000    # 2016-02-01T00:00:00Z

# --- observation window (PLAN §3) -------------------------------------------
# Every Population-B user gets an equal-length window: [createdAt, createdAt + N days).
WINDOW_DAYS = 30

# --- outcome labels ---------------------------------------------------------
# Retention: seenAt within N days of the profile pull date (robustness across bands).
ACTIVITY_BANDS_DAYS = (30, 90, 365)
DEFAULT_BAND_DAYS = 90
# Monetization: bulk profile `patron` flag (PLAN §6).

# --- churn segments (PLAN §4) ------------------------------------------------
# voluntary   = inactive by seenAt, account not disabled/ToS
# involuntary = disabled or tosViolation (analog of payment-failure churn)
# active      = within the activity band

# --- value tiers (PLAN §7, E1) -----------------------------------------------
# From bulk `playTime.total` (seconds of rated play, lifetime). Cutoffs are
# placeholders to be set from the observed distribution in P2 — do not hardcode
# business meaning into them before looking at the data.
VALUE_TIER_QUANTILES = (0.5, 0.9, 0.99)  # dormant/casual/core/power split points
VALUE_TIER_NAMES = ("dormant", "casual", "core", "power")

# --- API --------------------------------------------------------------------
API_BASE = "https://lichess.org"
BULK_USERS_URL = f"{API_BASE}/api/users"
BULK_MAX_IDS = 300
# Etiquette (PLAN §2): strictly sequential; honor Retry-After; aggressive backoff.
REQUEST_INTERVAL_S = 1.0           # minimum gap between any two requests
BULK_REQUEST_INTERVAL_S = 2.0      # bulk endpoint is heavier
BACKOFF_429_DEFAULT_S = 60.0       # Lichess guidance: wait ~a minute on 429
USER_AGENT = "lichess-retention-study (personal data-science project)"

# --- sampling (PLAN §15) ------------------------------------------------------
# All Population-B signups get profiles; Population A is sampled.
POP_A_SAMPLE = 12_000
RANDOM_SEED = 42

# --- exclusions ---------------------------------------------------------------
BOT_TITLE = "BOT"  # bot accounts are excluded from all populations
