# %% [markdown]
# E7 - Act: the A/B test design and business impact (climax slide)
#
# **Question**: Which intervention would we test first, and what would it be worth?
#
# **Method**: Full test spec on the strongest E3-E5 finding (PLAN section 8): hypothesis, target population (E2 flags after first 3-5 games), treatment/control, primary metric (30-day retention), secondaries, guardrails, ITT analysis. Impact translation: hypothetical lift -> '+N retained users per 100k acquired'; state explicitly that public data has no economics and a real environment would convert to LTV net of cost.
#
# **Inputs**: findings tables from E2-E5
# **Outputs**: tables/e7_test_spec.md, tables/e7_impact_estimate.csv
#
# **Business decision**: Ship/no-ship decision framework
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
