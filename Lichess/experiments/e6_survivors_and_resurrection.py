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
# **Status**: stub - implement in P5.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config, viz

viz.apply_style()


def main() -> None:
    raise SystemExit("Stub - implement in P5")


if __name__ == "__main__":
    main()
