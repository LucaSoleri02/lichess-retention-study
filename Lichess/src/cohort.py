"""Build the cohort table (P2): populations, profiles, labels, segments, value tiers.

Inputs : data/interim/games_2016_01.parquet (+ games_2016_02 for user listing only)
         data/interim/active_users_2026_08.parquet (behavioral cross-check, PLAN §4)
Outputs: data/processed/cohort_2016_01.parquet

Populations (PLAN §1):
    B = new signups in the cohort month (createdAt in-month) — carries the story
    A = existing users active in the cohort month — concentration context only

Labels per user:
    active_30d/90d/365d   retention bands from seenAt (PLAN §4: "survival to last
                          observed activity", right-censored — not a true trajectory)
    patron                monetization label (PLAN §6)
    played_recent_month   behavioral cross-check from the capped recent-month scan
    segment               active / voluntary_churn / involuntary_churn (PLAN §4)
    value_tier            dormant/casual/core/power from lifetime playTime (E1)

Bulk pulls are resume-friendly: each batch is appended to a jsonl checkpoint so
a crashed run re-fetches nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config
from .client import LichessClient

PROFILE_CHECKPOINT = config.INTERIM_DIR / "profiles_checkpoint.jsonl"


# --- user listing ---------------------------------------------------------------

def list_cohort_users() -> pd.Series:
    """Distinct usernames appearing in the cohort month (Population A ∪ B frame)."""
    games = pd.read_parquet(config.games_parquet(config.COHORT_MONTH),
                            columns=["white", "black"])
    users = pd.Series(pd.concat([games["white"], games["black"]]).unique(),
                      name="username")
    return users


# --- profile pulling (resume-friendly) -------------------------------------------

def _load_checkpoint() -> list[dict]:
    if not PROFILE_CHECKPOINT.exists():
        return []
    with open(PROFILE_CHECKPOINT, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def pull_profiles(usernames: list[str], client: LichessClient | None = None) -> pd.DataFrame:
    """Bulk-pull profiles with checkpointing; safe to re-run after a crash."""
    client = client or LichessClient()
    done = _load_checkpoint()
    seen = {u.get("id", "").lower() for u in done}
    remaining = [u for u in usernames if u.lower() not in seen]
    print(f"profiles: {len(done):,} checkpointed, {len(remaining):,} to fetch")

    # Use a smaller checkpoint block than the absolute API max so the cohort pull
    # remains resumable under Lichess traffic shaping.
    batch_size = max(500, min(config.BULK_MAX_IDS * 2, 1500))
    for i in range(0, len(remaining), batch_size):
        chunk = remaining[i:i + batch_size]
        rows = client.bulk_users(chunk)
        with open(PROFILE_CHECKPOINT, "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        done.extend(rows)
        print(f"profiles: {len(done):,}/{len(usernames):,}")
    return pd.DataFrame(done)


# --- normalization ----------------------------------------------------------------

MAIN_PERFS = ("bullet", "blitz", "rapid", "classical")


def normalize_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Raw bulk profiles -> tidy columns, including patron + playTime + current perfs."""
    perfs = df.get("perfs")
    play_time = df.get("playTime")

    def perf_field(perf: str, field: str):
        if perfs is None:
            return None
        return perfs.apply(lambda p: (p.get(perf) or {}).get(field) if isinstance(p, dict) else None)

    if isinstance(play_time, pd.Series):
        play_time_total = play_time.apply(lambda p: p.get("total") if isinstance(p, dict) else None)
    else:
        play_time_total = None

    out = pd.DataFrame({
        "username": df["username"],
        "created_at": pd.to_datetime(df["createdAt"], unit="ms", errors="coerce"),
        "seen_at": pd.to_datetime(df["seenAt"], unit="ms", errors="coerce"),
        "title": df.get("title"),
        "patron": df.get("patron", False),
        "disabled": df.get("disabled", False),
        "tos_violation": df.get("tosViolation", False),
        "play_time_total_s": play_time_total,
    })
    # flags are absent (not False) when not set -> normalize to boolean
    for flag in ("patron", "disabled", "tos_violation"):
        out[flag] = out[flag].fillna(False).astype(bool)
    for perf in MAIN_PERFS:
        out[f"now_{perf}_rating"] = perf_field(perf, "rating")
        out[f"now_{perf}_games"] = perf_field(perf, "games")
    return out


# --- labels ------------------------------------------------------------------------

def attach_labels(cohort: pd.DataFrame, pull_time: pd.Timestamp) -> pd.DataFrame:
    """Add population flags, retention bands, churn segments, value tiers."""
    cohort = cohort.copy()

    cohort_start = pd.to_datetime(config.COHORT_MONTH_START_MS, unit="ms")
    cohort_end = pd.to_datetime(config.COHORT_MONTH_END_MS, unit="ms")
    cohort["is_new_user"] = cohort["created_at"].ge(cohort_start) & cohort["created_at"].lt(cohort_end)
    cohort["population"] = cohort["is_new_user"].map({True: "B", False: "A"})

    days_since_seen = (pull_time - cohort["seen_at"]).dt.days
    for band in config.ACTIVITY_BANDS_DAYS:
        cohort[f"active_{band}d"] = days_since_seen <= band

    # voluntary vs involuntary churn (PLAN §4)
    band = config.DEFAULT_BAND_DAYS
    involuntary = cohort["disabled"].fillna(False) | cohort["tos_violation"].fillna(False)
    cohort["segment"] = "active"
    cohort.loc[~cohort[f"active_{band}d"] & ~involuntary, "segment"] = "voluntary_churn"
    cohort.loc[involuntary, "segment"] = "involuntary_churn"

    # value tiers from lifetime play time (E1 concentration); cutoffs from quantiles
    pt = pd.to_numeric(cohort["play_time_total_s"], errors="coerce")
    qs = pt.quantile(config.VALUE_TIER_QUANTILES)
    cohort["value_tier"] = pd.cut(
        pt,
        bins=[-1, *qs.tolist(), float("inf")],
        labels=config.VALUE_TIER_NAMES,
    )
    print("value-tier cutoffs (seconds):", qs.round(0).to_dict())
    return cohort


def merge_recent_month_crosscheck(cohort: pd.DataFrame) -> pd.DataFrame:
    """Flag users observed playing in the recent-month scan (PLAN §4)."""
    path = config.RECENT_ACTIVE_USERS_PARQUET
    if not path.exists():
        print("recent-month scan not found; skipping cross-check merge")
        cohort["played_recent_month"] = pd.NA
        return cohort
    recent = pd.read_parquet(path)
    active_users = set(recent["username"].str.lower())
    cohort = cohort.copy()
    cohort["played_recent_month"] = cohort["username"].str.lower().isin(active_users)
    return cohort


# --- pipeline ------------------------------------------------------------------------

def build_cohort(out_path: Path = config.COHORT_PARQUET) -> pd.DataFrame:
    """Full P2 pipeline: users -> profiles -> labels -> cross-check -> parquet."""
    users = list_cohort_users()
    print(f"{len(users):,} distinct users in cohort month {config.COHORT_MONTH}")

    profiles = pull_profiles(list(users))
    cohort = normalize_profiles(profiles)

    pull_time = pd.Timestamp.now(tz="UTC").tz_localize(None)
    cohort = attach_labels(cohort, pull_time)
    cohort = merge_recent_month_crosscheck(cohort)

    # bots are excluded from all populations (config.BOT_TITLE)
    n_bots = (cohort["title"].fillna("") == config.BOT_TITLE).sum()
    cohort = cohort[cohort["title"].fillna("") != config.BOT_TITLE]
    print(f"excluded {n_bots:,} bot accounts")

    cohort.to_parquet(out_path, index=False, compression="zstd")

    pop_b = cohort[cohort["population"] == "B"]
    pop_a = cohort[cohort["population"] == "A"]
    print(f"\nSaved cohort: {len(cohort):,} rows -> {out_path}")
    print(f"Population B (new signups): {len(pop_b):,} | active_90d: {pop_b['active_90d'].mean():.1%} "
          f"| patron: {pop_b['patron'].mean():.1%}")
    print(f"Population A (existing):    {len(pop_a):,} | active_90d: {pop_a['active_90d'].mean():.1%} "
          f"| patron: {pop_a['patron'].mean():.1%}")
    print("segments:", cohort["segment"].value_counts().to_dict())
    return cohort


if __name__ == "__main__":
    build_cohort()
