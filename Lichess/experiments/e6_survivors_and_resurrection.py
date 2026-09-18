# %% [markdown]
# E6 - Survivors and resurrection
#
# **Question**: Who are the long-term survivors, and do dormant users come back?
#
# **Method**: Then-vs-now archetypes for retained Population B (first-window vs current perfs: rating, format drift); resurrection rate = played_recent_month among users dormant by seen_at bands ('zombie' reactivation).
#
# **Inputs**: cohort + user_window_features
# **Outputs**: figures/e6_archetypes.png, tables/e6_resurrection.csv
#
# **Business decision**: Winback vs. new-user-activation prioritization
# **Status**: implemented for the current profile checkpoint; rerun after the final API retry.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt

from src import config, viz

viz.apply_style()


def main() -> None:
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    features = pd.read_parquet(config.USER_WINDOW_PARQUET)
    pop_b = cohort[cohort.population == "B"].copy()
    dormant = pop_b[~pop_b.active_90d.fillna(False)]
    resurrection = dormant.played_recent_month.fillna(False).mean()
    archetypes = pop_b.merge(
        features[["username", "dominant_speed", "games_total", "days_active"]],
        on="username", how="inner",
    )
    archetypes["survivor"] = archetypes["active_365d"].fillna(False)
    archetypes = archetypes.groupby(["survivor", "dominant_speed"], dropna=False).agg(
        n=("username", "size"), active_90d=("active_90d", "mean"),
        games_total=("games_total", "median"), days_active=("days_active", "median")
    ).reset_index()
    archetypes["dominant_speed"] = archetypes["dominant_speed"].astype("string").fillna("missing")
    viz.save_table(archetypes, "e6_archetypes")
    summary = pd.DataFrame([
        {"metric": "dormant_users", "value": len(dormant)},
        {"metric": "dormant_recent_activity_rate", "value": resurrection},
        {"metric": "pop_b_recent_activity_rate", "value": pop_b.played_recent_month.fillna(False).mean()},
    ])
    viz.save_table(summary, "e6_resurrection")
    plot = archetypes[archetypes["survivor"]].sort_values("n", ascending=False).head(6)
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = plot["dominant_speed"].astype(str)
    ax.bar(labels, plot["n"], color=viz.PALETTE["retained"])
    ax.set_ylabel("Users")
    ax.set_xlabel("Dominant first-window format")
    ax.set_title("Longer-term survivors by first-window format")
    ax.tick_params(axis="x", rotation=20)
    viz.save_fig(fig, "e6_archetypes")
    plt.close(fig)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
