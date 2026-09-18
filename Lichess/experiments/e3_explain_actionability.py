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
