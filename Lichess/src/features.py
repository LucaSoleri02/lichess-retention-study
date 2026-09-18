"""First-30-day behavior features per user (PLAN §3, §7).

Every Population-B user gets an equal-length window: [created_at, created_at + 30d),
spanning the 2016-01 and 2016-02 dumps. Population A gets simple Jan-month
aggregates for concentration context only.

Feature groups (per user, from their own perspective):
    engagement : games_total, days_active, games_per_active_day, sessions,
                 games_per_session, weekend_share
    habit      : week1_days_active, returned_after_signup_day, distinct_speeds,
                 dominant_speed
    experience : win_rate, opp_rating_mismatch (mean opp - own), rating_change,
                 max_consecutive_losses, abandonment_share, short_game_share
    controls   : first_rating, last_rating, mean_rating (Elo = control, PLAN §5)

Inputs : games parquets for both history months + cohort parquet (created_at)
Outputs: data/interim/user_window_features.parquet
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

RESULT_POINTS = {"1-0": (1.0, 0.0), "0-1": (0.0, 1.0), "1/2-1/2": (0.5, 0.5)}
SESSION_GAP = pd.Timedelta(minutes=30)
SHORT_GAME_MOVES = 10  # fullmoves; <= this counts as a short game (E5)


def load_history_games() -> pd.DataFrame:
    frames = [pd.read_parquet(config.games_parquet(m)) for m in config.HISTORY_MONTHS]
    return pd.concat(frames, ignore_index=True)


def to_long(games: pd.DataFrame) -> pd.DataFrame:
    """One row per (user, game) from that user's perspective."""
    base_cols = ["result", "datetime", "speed", "termination", "nummoves"]
    white = pd.DataFrame({
        "username": games["white"], "opp_rating": games["blackelo"],
        "rating": games["whiteelo"], "color": "white",
        **{c: games[c] for c in base_cols},
    })
    black = pd.DataFrame({
        "username": games["black"], "opp_rating": games["whiteelo"],
        "rating": games["blackelo"], "color": "black",
        **{c: games[c] for c in base_cols},
    })
    long = pd.concat([white, black], ignore_index=True)
    pts = long["result"].map(RESULT_POINTS)
    long["score"] = [p[0] if c == "white" else p[1] for p, c in zip(pts, long["color"])]
    return long


def _session_count(times: pd.Series) -> int:
    t = times.sort_values()
    return int((t.diff() > SESSION_GAP).sum() + 1)


def _max_consecutive_losses(scores: pd.Series) -> int:
    worst = run = 0
    for s in scores:
        run = run + 1 if s == 0 else 0
        worst = max(worst, run)
    return worst


def _window_features(user_games: pd.DataFrame) -> pd.Series:
    g = user_games.sort_values("datetime")
    signup_day = g["datetime"].min().date()
    dates = g["datetime"].dt.date
    speed_mode = g["speed"].dropna().mode()
    week1_end = signup_day + pd.Timedelta(days=7)

    sessions = _session_count(g["datetime"])
    losses = g["score"] == 0
    return pd.Series({
        "games_total": len(g),
        "days_active": dates.nunique(),
        "sessions": sessions,
        "week1_days_active": dates[dates <= week1_end].nunique(),
        "returned_after_signup_day": bool((dates > signup_day).any()),
        "distinct_speeds": g["speed"].nunique(),
        "dominant_speed": speed_mode.iloc[0] if not speed_mode.empty else None,
        "weekend_share": (g["datetime"].dt.dayofweek >= 5).mean(),
        "win_rate": g["score"].mean(),
        "opp_rating_mismatch": (g["opp_rating"] - g["rating"]).mean(),
        "first_rating": g["rating"].iloc[0],
        "last_rating": g["rating"].iloc[-1],
        "rating_change": g["rating"].iloc[-1] - g["rating"].iloc[0],
        "max_consecutive_losses": _max_consecutive_losses(g["score"]),
        "abandonment_share": (g["termination"] == "Abandoned").mean(),
        "short_game_share": (g["nummoves"] <= SHORT_GAME_MOVES).mean(),
        "resign_share_of_losses": (g.loc[losses, "termination"] == "Normal").mean() if losses.any() else np.nan,
    })


def build_window_features(cohort: pd.DataFrame | None = None,
                          games: pd.DataFrame | None = None,
                          out_path=config.USER_WINDOW_PARQUET) -> pd.DataFrame:
    """Per-user first-30-day features for Population B; Jan aggregates for Pop A."""
    if cohort is None:
        cohort = pd.read_parquet(config.COHORT_PARQUET)
    if games is None:
        games = load_history_games()
    long = to_long(games)

    # --- Population B: equal 30-day post-signup windows (PLAN §3) ---
    pop_b = cohort.loc[cohort["population"] == "B", ["username", "created_at"]]
    b_games = long.merge(pop_b, on="username", how="inner")
    window_end = b_games["created_at"] + pd.Timedelta(days=config.WINDOW_DAYS)
    in_window = (b_games["datetime"] >= b_games["created_at"]) & (b_games["datetime"] < window_end)
    b_games = b_games[in_window]

    print(f"computing window features for {b_games['username'].nunique():,} Pop-B users "
          f"({len(b_games):,} games in-window)")
    feats_b = b_games.groupby("username").apply(_window_features, include_groups=False)
    feats_b["games_per_active_day"] = feats_b["games_total"] / feats_b["days_active"]
    feats_b["games_per_session"] = feats_b["games_total"] / feats_b["sessions"]
    feats_b = feats_b.reset_index()

    # --- Population A: Jan-month aggregates (concentration context only) ---
    jan = long[long["datetime"] < pd.Timestamp(config.COHORT_MONTH_END_MS, unit="ms")]
    pop_a_users = cohort.loc[cohort["population"] == "A", "username"]
    a_games = jan[jan["username"].isin(set(pop_a_users))]
    feats_a = a_games.groupby("username").agg(
        games_total=("score", "size"),
        days_active=("datetime", lambda s: s.dt.date.nunique()),
        win_rate=("score", "mean"),
    ).reset_index()
    feats_a["population"] = "A"
    feats_b["population"] = "B"

    feats = pd.concat([feats_b, feats_a], ignore_index=True)
    feats.to_parquet(out_path, index=False, compression="zstd")
    print(f"Saved window features: {len(feats):,} rows -> {out_path}")
    return feats


if __name__ == "__main__":
    build_window_features()
