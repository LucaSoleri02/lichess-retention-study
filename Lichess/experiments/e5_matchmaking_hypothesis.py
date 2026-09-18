# %% [markdown]
# E5 - Matchmaking hypothesis (association only)
#
# **Question**: Is early difficulty mismatch - not just losing - associated with churn?
#
# **Method**: opp_rating_mismatch, max_consecutive_losses, abandonment_share, short_game_share vs churn, controlling for volume (win-rate alone is confounded by matchmaking; use post-provisional ratings where possible).
#
# **Inputs**: cohort + user_window_features (Population B)
# **Outputs**: figures/e5_mismatch_association.png, tables/e5_mismatch.csv
#
# **Business decision**: Matchmaking/beginner-protection experiment candidate
# **Status**: implemented for the current profile checkpoint; association only.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from src import config, viz

viz.apply_style()


def main() -> None:
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    features = pd.read_parquet(config.USER_WINDOW_PARQUET)
    columns = ["username", "games_total", "opp_rating_mismatch", "max_consecutive_losses",
               "abandonment_share", "short_game_share"]
    frame = cohort.loc[cohort.population == "B", ["username", "active_90d"]].merge(
        features.loc[features.population == "B", columns], on="username", how="inner"
    )
    rows = []
    volume = np.log1p(frame["games_total"])
    for feature in columns[2:]:
        valid = frame[["active_90d", feature]].dropna().copy()
        # Residualize the signal against log activity volume before binning.
        x = np.column_stack([np.ones(len(valid)), volume.loc[valid.index]])
        valid["residual"] = valid[feature] - x @ np.linalg.lstsq(x, valid[feature], rcond=None)[0]
        valid["band"] = pd.qcut(valid["residual"], q=4, duplicates="drop")
        grouped = valid.groupby("band", observed=False).agg(
            n=("active_90d", "size"), active_90d=("active_90d", "mean"), residual_mean=("residual", "mean")
        ).reset_index()
        grouped["feature"] = feature
        rows.append(grouped)
    summary = pd.concat(rows, ignore_index=True)
    summary["churn_rate"] = 1 - summary["active_90d"]
    viz.save_table(summary, "e5_mismatch_association")
    fig, ax = plt.subplots(figsize=(8, 4))
    for feature, group in summary.groupby("feature"):
        ax.plot(group["residual_mean"], group["churn_rate"], marker="o", label=feature)
    ax.set_xlabel("Volume-adjusted signal (quartile mean)")
    ax.set_ylabel("Churn rate")
    ax.set_title("Difficulty and experience signals are associated with churn")
    ax.legend(fontsize=8)
    viz.save_fig(fig, "e5_mismatch_association")
    plt.close(fig)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
