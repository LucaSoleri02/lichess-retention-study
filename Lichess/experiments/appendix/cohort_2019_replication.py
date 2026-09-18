# %% [markdown]
# Appendix - 2019 cohort replication (product health over time)
#
# **Question**: Is the product getting better at retaining cohorts over time?
#
# **Method**: Rerun P1-P2 + E1 on the 2019-01 dump (10 GB). Only if reframed as a product-health check, not a robustness footnote (PLAN section 9). Optional.
#
# **Inputs**: 2019-01 dump + full pipeline rerun
# **Outputs**: figures/appendix_cohort_comparison.png
#
# **Business decision**: product-health trend
# **Status**: stub - implement in P5 (optional).

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd

from src import config, viz

viz.apply_style()


def main() -> None:
    raise SystemExit("Optional appendix - only with spare time")


if __name__ == "__main__":
    main()
