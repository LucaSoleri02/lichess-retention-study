# %% [markdown]
# E4 - Format hypothesis (association only)
#
# **Question**: Is the dominant first-window format associated with retention?
#
# **Method**: Retention by dominant_speed, overall and within week-1-only players; control for games_total via stratification. Language discipline: 'associated with', never 'causes' (PLAN section 8).
#
# **Inputs**: cohort + user_window_features (Population B)
# **Outputs**: figures/e4_format_association.png, tables/e4_format_association.csv
#
# **Business decision**: Onboarding/recommendation experiment candidate
# **Status**: implemented for the current profile checkpoint; association only.

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
    frame = cohort.loc[cohort.population == "B", ["username", "active_90d"]].merge(
        features.loc[features.population == "B", ["username", "dominant_speed", "games_total"]],
        on="username", how="inner",
    )
    frame["volume_band"] = pd.qcut(frame["games_total"], q=4, duplicates="drop")
    summary = frame.groupby(["dominant_speed", "volume_band"], dropna=False, observed=False).agg(
        n=("username", "size"), active_90d=("active_90d", "mean")
    ).reset_index()
    viz.save_table(summary, "e4_format_association")
    overall = frame.groupby("dominant_speed", dropna=False).agg(
        n=("username", "size"), active_90d=("active_90d", "mean")
    ).reset_index()
    overall["dominant_speed"] = overall["dominant_speed"].astype("string").fillna("missing")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(overall["dominant_speed"].astype("string"), overall["active_90d"], color=viz.PALETTE["primary"])
    ax.set_ylabel("Active within 90 days")
    ax.set_xlabel("Dominant first-window format")
    ax.set_title("Format usage is associated with later activity")
    ax.tick_params(axis="x", rotation=20)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    viz.save_fig(fig, "e4_format_association")
    plt.close(fig)
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
