# %% [markdown]
# E1 - Diagnose: survival to last observed activity + value concentration
#
# **Question**: How quickly do new users disappear, where is the biggest drop-off, and where is today's value concentrated?
#
# **Method**: Survival-style curve of seen_at for Population B (10-year survival to last observed activity, right-censoring stated, PLAN section 4); behavioral cross-check vs played_recent_month; voluntary/involuntary churn split; value-tier concentration of Population A today.
#
# **Inputs**: data/processed/cohort_2016_01.parquet
# **Outputs**: figures/e1_survival_to_last_activity.png, figures/e1_value_concentration.png, tables/e1_summary.csv
#
# **Business decision**: When and whom should the product intervene for?
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
    if not config.COHORT_PARQUET.exists():
        raise SystemExit("Run P2 first: python -m src.cohort (from Lichess/ dir)")
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    pop_b = cohort[cohort["population"] == "B"]
    observed_at = pd.Timestamp.now(tz="UTC").tz_localize(None)
    days_since_signup = (pop_b["seen_at"] - pop_b["created_at"]).dt.days
    days_since_signup = days_since_signup.fillna(0).clip(lower=0)
    horizons = [30, 90, 365, 730, 1825, 3650]
    survival = pd.DataFrame({
        "days": horizons,
        "share_surviving_to_last_observed_activity": [
            float((days_since_signup >= horizon).mean()) for horizon in horizons
        ],
    })

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(survival["days"], survival["share_surviving_to_last_observed_activity"],
            marker="o", color=viz.PALETTE["primary"])
    ax.set_xscale("symlog", linthresh=30)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Days from signup")
    ax.set_ylabel("Share with activity observed at or after horizon")
    ax.set_title("New-user survival to last observed activity")
    ax.grid(axis="y", alpha=0.25)
    viz.save_fig(fig, "e1_survival_to_last_activity")
    plt.close(fig)

    pop_a = cohort[cohort["population"] == "A"].copy()
    value = pop_a.groupby("value_tier", dropna=False).agg(
        users=("username", "size"),
        lifetime_play_time_s=("play_time_total_s", "sum"),
    ).reset_index()
    value["value_tier"] = value["value_tier"].astype("string").fillna("missing")
    value = value.sort_values("lifetime_play_time_s", ascending=False)
    total_value = value["lifetime_play_time_s"].sum()
    value["share_of_observed_play_time"] = value["lifetime_play_time_s"] / total_value
    value["cumulative_share"] = value["share_of_observed_play_time"].cumsum()

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(value["value_tier"], value["share_of_observed_play_time"], color=viz.PALETTE["accent"])
    ax.set_ylabel("Share of observed lifetime play time")
    ax.set_xlabel("Population A value tier")
    ax.set_title("Current observed play time is concentrated in a few tiers")
    ax.tick_params(axis="x", rotation=20)
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    viz.save_fig(fig, "e1_value_concentration")
    plt.close(fig)

    summary = survival.rename(columns={
        "share_surviving_to_last_observed_activity": "value",
    })
    summary["metric"] = "survival_to_last_observed_activity"
    summary = summary[["metric", "days", "value"]]
    labels = pop_b[["active_30d", "active_90d", "active_365d", "patron"]].mean()
    label_rows = pd.DataFrame({"metric": labels.index, "days": pd.NA, "value": labels.values})
    segments = pop_b["segment"].value_counts(normalize=True).rename_axis("metric").reset_index(name="value")
    segments["days"] = pd.NA
    crosscheck = pd.crosstab(pop_b["active_90d"], pop_b["played_recent_month"], normalize="all")
    crosscheck_rows = crosscheck.stack().rename("value").reset_index()
    crosscheck_rows["metric"] = "active_90d_vs_played_recent_month"
    crosscheck_rows["days"] = crosscheck_rows["active_90d"].astype("string") + ":" + crosscheck_rows["played_recent_month"].astype("string")
    crosscheck_rows = crosscheck_rows[["metric", "days", "value"]]
    summary = pd.concat([summary, label_rows, segments[["metric", "days", "value"]], crosscheck_rows], ignore_index=True)
    viz.save_table(summary, "e1_summary")
    viz.save_table(value, "e1_value_concentration")

    print("Pop B label balance:")
    print(labels)
    print("segments:", pop_b["segment"].value_counts().to_dict())
    print("cross-check:")
    print(pd.crosstab(pop_b["active_90d"], pop_b["played_recent_month"], normalize="all"))


if __name__ == "__main__":
    main()
