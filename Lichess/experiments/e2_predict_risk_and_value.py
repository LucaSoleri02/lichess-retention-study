# %% [markdown]
# E2 - Predict: churn risk and payer propensity, early enough to act
#
# **Question**: Can we identify likely churners - and likely payers - from the first 30 days?
#
# **Method**: Two classifiers on first-30-day features (window parquet): churn risk (active_90d) and patron propensity. Headline metric is top-decile capture ('highest-risk 10% accounts for X% of eventual churn'), NOT AUC. Lift/gain curves + precision@k.
#
# **Inputs**: cohort parquet + user_window_features.parquet (Population B only)
# **Outputs**: figures/e2_lift_curves.png, tables/e2_top_decile_capture.csv
#
# **Business decision**: Who to target, and can we afford to reach them?
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
    raise SystemExit("Stub - implement in P3")


if __name__ == "__main__":
    main()
