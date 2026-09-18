# %% [markdown]
# E3 - Explain: which early experiences are associated with each outcome
#
# **Question**: Which first-30-day experiences are associated with retention and with patron status - classified by actionability (PLAN section 5)?
#
# **Method**: Effect sizes with n and CI on every cut: engagement (games/active days/sessions/streaks, controlling for volume), format exploration, experience-quality features. Elo enters only as a control. Populate the actionability table (user characteristic / behavioral signal / product-influenceable experience) with real numbers.
#
# **Inputs**: cohort + user_window_features (Population B)
# **Outputs**: figures/e3_actionability.png, tables/e3_actionability.csv
#
# **Business decision**: Which levers are worth building?
# **Status**: implemented for the current profile checkpoint; rerun after the final API retry.

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
    frame = cohort.loc[cohort["population"] == "B", ["username", "active_90d", "patron"]].merge(
        features.loc[features["population"] == "B"], on="username", how="inner"
    )
    feature_groups = {
        "behavioral_signal": ["games_total", "days_active", "sessions", "week1_days_active",
                              "returned_after_signup_day", "games_per_active_day"],
        "product_influenceable": ["distinct_speeds", "weekend_share", "opp_rating_mismatch",
                                   "max_consecutive_losses", "abandonment_share", "short_game_share"],
        "user_characteristic": ["first_rating"],
    }
    rows = []
    for actionability, columns in feature_groups.items():
        for feature in columns:
            values = pd.to_numeric(frame[feature], errors="coerce")
            valid = frame.loc[values.notna(), ["active_90d", "patron"]].copy()
            valid["feature"] = values[values.notna()].to_numpy()
            if valid["feature"].nunique() < 4:
                continue
            low_cut, high_cut = valid["feature"].quantile([0.25, 0.75])
            low = valid[valid["feature"] <= low_cut]
            high = valid[valid["feature"] >= high_cut]
            for target in ("active_90d", "patron"):
                low_rate, high_rate = low[target].mean(), high[target].mean()
                diff = high_rate - low_rate
                se = np.sqrt(low_rate * (1 - low_rate) / len(low) + high_rate * (1 - high_rate) / len(high))
                rows.append({
                    "actionability": actionability,
                    "feature": feature,
                    "target": target,
                    "low_n": len(low),
                    "high_n": len(high),
                    "low_rate": low_rate,
                    "high_rate": high_rate,
                    "high_minus_low": diff,
                    "ci_low": diff - 1.96 * se,
                    "ci_high": diff + 1.96 * se,
                })

    speed = frame.groupby("dominant_speed", dropna=False).agg(
        n=("username", "size"), active_90d=("active_90d", "mean"), patron=("patron", "mean")
    ).reset_index()
    speed["actionability"] = "product_influenceable"
    speed["feature"] = "dominant_speed"
    speed["target"] = "format_group"
    viz.save_table(pd.DataFrame(rows), "e3_actionability")
    viz.save_table(speed, "e3_format_association")

    result = pd.DataFrame(rows)
    churn = result[result["target"] == "active_90d"].sort_values("high_minus_low")
    plot = churn.tail(8)
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(plot))
    ax.errorbar(plot["high_minus_low"], y,
                xerr=[plot["high_minus_low"] - plot["ci_low"], plot["ci_high"] - plot["high_minus_low"]],
                fmt="o", color=viz.PALETTE["primary"])
    ax.axvline(0, color=viz.PALETTE["muted"], linewidth=1)
    ax.set_yticks(y, plot["feature"])
    ax.set_xlabel("Active-90d rate difference: high quartile minus low quartile")
    ax.set_title("Early experiences associated with later activity")
    viz.save_fig(fig, "e3_actionability")
    plt.close(fig)
    print(f"E3 frame: {len(frame):,} users; format groups: {len(speed)}")


if __name__ == "__main__":
    main()
