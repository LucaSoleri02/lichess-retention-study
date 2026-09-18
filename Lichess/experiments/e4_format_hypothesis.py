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
# **Status**: stub - implement in P4.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config, viz

viz.apply_style()


def main() -> None:
    raise SystemExit("Stub - implement in P4")


if __name__ == "__main__":
    main()
