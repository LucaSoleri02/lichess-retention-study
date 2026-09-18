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
# **Status**: stub - implement in P3.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config, viz

viz.apply_style()


def main() -> None:
    if not config.COHORT_PARQUET.exists():
        raise SystemExit("Run P2 first: python -m src.cohort (from Lichess/ dir)")
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    pop_b = cohort[cohort["population"] == "B"]
    print("Pop B label balance:")
    print(pop_b[["active_30d", "active_90d", "active_365d", "patron"]].mean())
    print("segments:", pop_b["segment"].value_counts().to_dict())
    if "played_recent_month" in pop_b:
        print("cross-check (active_90d vs played_recent_month):")
        print(pd.crosstab(pop_b["active_90d"], pop_b["played_recent_month"], normalize="index"))
    # TODO(P3): hero survival curve, concentration chart, summary table


if __name__ == "__main__":
    main()
