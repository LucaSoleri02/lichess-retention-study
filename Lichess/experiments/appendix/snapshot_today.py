# %% [markdown]
# Appendix - the product today
#
# **Question**: What does Lichess look like right now (levels, formats)?
#
# **Method**: Leaderboards per time control via public API. Produce on request only (PLAN section 9) - never main-deck minutes.
#
# **Inputs**: live API only
# **Outputs**: tables/appendix_leaderboards.csv
#
# **Business decision**: context
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
    from src.client import LichessClient
    client = LichessClient()
    for perf in ("bullet", "blitz", "rapid", "classical"):
        users = client.top_players(perf=perf)
        print(perf, len(users))


if __name__ == "__main__":
    main()
