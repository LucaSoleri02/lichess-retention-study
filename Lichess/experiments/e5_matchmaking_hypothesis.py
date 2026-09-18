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
