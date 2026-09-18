# %% [markdown]
# Spotify charts scoping
# Goal: find a public, stable data source and inspect whether it is rich enough for an analysis.

# %%
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).with_name("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

CHART_URL = "https://charts.spotify.com/charts/view/viral-global-daily/latest"
RAW_HTML_PATH = OUTPUT_DIR / "spotify_charts_page.html"
RAW_JSON_PATH = OUTPUT_DIR / "spotify_charts_next_data.json"

# %%
response = requests.get(CHART_URL, timeout=30)
response.raise_for_status()
RAW_HTML_PATH.write_text(response.text, encoding="utf-8")
print(f"Fetched status: {response.status_code}")
print(f"Saved page HTML to: {RAW_HTML_PATH}")

# %%
soup = BeautifulSoup(response.text, "html.parser")
script = soup.find("script", {"id": "__NEXT_DATA__"})
if script is None:
    raise RuntimeError("__NEXT_DATA__ not found in Spotify page; source may have changed.")

payload = json.loads(script.string)
RAW_JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Saved Next.js payload to: {RAW_JSON_PATH}")
print(f"Top-level JSON keys: {list(payload.keys())}")

# %%

def walk(node, path="root"):
    if isinstance(node, dict):
        keys = list(node.keys())
        if any(k.lower() in {"chart", "tracks", "items", "data", "entries"} for k in keys):
            print(f"\nCandidate node at: {path}")
            print("Keys:", keys[:20])
        for key, value in node.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node[:10]):
            yield from walk(item, f"{path}[{i}]")

# %%
print("\nTraversing JSON structure to find chart-like nodes...\n")
for _ in walk(payload):
    pass

# Fallback: search the raw JSON for likely track names and artist names.
text = json.dumps(payload)
for marker in ["trackName", "artistName", "title", "name", "streams", "position"]:
    print(f"Marker '{marker}' found: {marker in text}")

# %%
# If the page embeds chart data in a nested object, flatten the most likely track-like entries.
# This is intentionally defensive: we want to know whether the data is usable, not assume a fixed schema.


def find_chart_like_records(node):
    records = []

    if isinstance(node, dict):
        keys = set(node.keys())
        if {"trackName", "artistName"}.issubset(keys):
            records.append(node)
        if {"title", "artistName"}.issubset(keys):
            records.append(node)
        if {"name", "artistName"}.issubset(keys) and "rank" in keys:
            records.append(node)
        for value in node.values():
            records.extend(find_chart_like_records(value))
    elif isinstance(node, list):
        for item in node:
            records.extend(find_chart_like_records(item))
    return records

records = find_chart_like_records(payload)
print(f"\nChart-like records found: {len(records)}")
if records:
    first = records[0]
    print("Example record keys:", list(first.keys())[:20])
    print("Example record:", json.dumps(first, ensure_ascii=False)[:1000])
else:
    print("No chart-like records were found in the embedded payload; the page likely renders charts client-side via a secondary fetch.")

# %%
# If no chart rows are found at all, we still have a useful scoping result: the data source exists, but the schema is not as cleanly exposed as Lichess.
print("\nTakeaway:")
print("- Spotify provides a public chart page, but chart content is less straightforward to download in one clean bundle than Lichess.")
print("- It is still viable for a public-data presentation, especially if using charts or artist-level time series.")
print("- For a more structured analysis, the better route may be Spotify's public charts endpoints or a curated external dataset.")
