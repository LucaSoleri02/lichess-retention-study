# %% [markdown]
# Lichess data scoping
# Goal: understand whether a public source is rich enough for a product-style analysis.

# %%
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests

OUTPUT_DIR = Path(__file__).with_name("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Lichess public API endpoint for top players by rating.
API_URL = "https://lichess.org/api/player/top/200/classical"
RAW_PATH = OUTPUT_DIR / "lichess_top_players_raw.json"

# %%
response = requests.get(API_URL, timeout=30)
response.raise_for_status()
payload = response.json()
RAW_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Fetched status: {response.status_code}")
print(f"Saved raw payload to: {RAW_PATH}")
print(f"Top-level keys: {list(payload.keys())}")
print(f"Users returned: {len(payload.get('users', []))}")

# %%
users = payload.get("users", [])
rows = []
for user in users:
    perf = user.get("perfs", {}).get("classical", {})
    rows.append(
        {
            "id": user.get("id"),
            "username": user.get("username"),
            "title": user.get("title"),
            "online": user.get("online", False),
            "patron": user.get("patron", False),
            "rating": perf.get("rating"),
            "progress": perf.get("progress"),
        }
    )

# %%
df = pd.DataFrame(rows)
print("\nSchema:")
print(df.dtypes)
print("\nFirst rows:")
print(df.head(10).to_string(index=False))
print("\nSummary stats:")
print(df[["rating", "progress"]].describe().to_string())

# %%
print("\nTop title counts:")
print(df["title"].value_counts(dropna=False).head(10).to_string())

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(df["rating"].dropna(), bins=20, color="#1f77b4")
axes[0].set_title("Distribution of classical ratings")
axes[0].set_xlabel("Rating")
axes[0].set_ylabel("Count")

axes[1].hist(df["progress"].dropna(), bins=20, color="#2ca02c")
axes[1].set_title("Distribution of rating progress")
axes[1].set_xlabel("Progress")
axes[1].set_ylabel("Count")

fig.tight_layout()
fig.savefig(OUTPUT_DIR / "lichess_top_ratings.png", dpi=160)
plt.show(fig)
plt.close(fig)

print("\nSaved chart:", OUTPUT_DIR / "lichess_top_ratings.png")

# %% [markdown]
# Interpretation
# - Data are public and richly described.
# - The schema is clean enough for a cohort/retention or engagement-oriented analysis.
# - This is a strong candidate for a public-dataset presentation because it is both product-relevant and well documented.
