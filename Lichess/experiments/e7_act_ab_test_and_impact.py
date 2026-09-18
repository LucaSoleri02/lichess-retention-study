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
# **Status**: implemented as a test-design artifact for the current evidence.

# %%
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config, viz

viz.apply_style()


def main() -> None:
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    pop_b = cohort[cohort.population == "B"]
    baseline = float(pop_b["active_30d"].mean())
    base_n = len(pop_b)
    spec = f"""# E7 test specification

## Hypothesis
For new users flagged after their first 3-5 games, calibrated format guidance or matchmaking support increases 30-day active retention.

## Population and assignment
January-signup-like new users; randomize eligible users to treatment or current experience control. Analyze by intent to treat.

## Metrics
- Primary: 30-day active retention.
- Secondary: 7-day retention, games per user, active days.
- Guardrails: opponent-rating mismatch, abandonment rate, short-game rate, negative feedback.

## Decision rule
Ship only if the treatment improves the primary metric with a pre-specified confidence threshold and does not breach guardrails.

## Limitation
This public observational dataset motivates the test but cannot establish causal lift or monetization economics.
"""
    (config.TABLES_DIR / "e7_test_spec.md").write_text(spec, encoding="utf-8")
    lifts = pd.DataFrame({"hypothetical_lift": [0.01, 0.02, 0.05, 0.10]})
    lifts["baseline_active_30d"] = baseline
    lifts["incremental_retained_per_100k"] = lifts["hypothetical_lift"] * 100_000
    lifts["projected_active_30d"] = baseline + lifts["hypothetical_lift"]
    lifts["cohort_reference_n"] = base_n
    viz.save_table(lifts, "e7_impact_estimate")
    print(f"baseline active_30d={baseline:.1%}; reference Pop-B n={base_n:,}")


if __name__ == "__main__":
    main()
