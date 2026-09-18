# %% [markdown]
# Spotify charts via kworb.net
# Why: charts.spotify.com only exposes the latest weekly global snapshot anonymously
# (/public/v0/charts); everything else requires a Spotify user login.
# kworb.net publishes the same chart data (daily/weekly, ~70 countries) WITH stream
# counts, plus full per-track chart history. This script builds tidy extracts to
# judge whether Spotify can carry a story-first final presentation.

# %%
from __future__ import annotations

import re
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).with_name("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

BASE = "https://kworb.net"
HEADERS = {"User-Agent": "Mozilla/5.0 (personal data-science exploration)"}
DELAY_S = 0.5

COUNTRIES = ["global", "us", "gb", "de", "br", "mx", "jp", "kr", "in", "ng", "se"]
TOP_N_HISTORY = 50  # track-history pages to pull from the current global daily chart

session = requests.Session()
session.headers.update(HEADERS)

# %%

def get_soup(url: str) -> BeautifulSoup:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    time.sleep(DELAY_S)
    return BeautifulSoup(resp.text, "html.parser")


def parse_int(text: str) -> int | None:
    text = text.replace(",", "").strip()
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def parse_country_snapshot(code: str, freq: str = "daily") -> pd.DataFrame:
    """Parse kworb's Top-200 table for one country/frequency into a tidy frame."""
    soup = get_soup(f"{BASE}/spotify/country/{code}_{freq}.html")
    table = soup.find("table")
    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 11:
            continue
        track_link = tr.find("a", href=re.compile(r"/track/"))
        artist_links = tr.find_all("a", href=re.compile(r"/artist/"))
        rows.append(
            {
                "country": code,
                "freq": freq,
                "pos": parse_int(tds[0].get_text()),
                "pos_change": tds[1].get_text(strip=True),
                "track_name": track_link.get_text(strip=True) if track_link else None,
                "track_id": track_link["href"].split("/")[-1].removesuffix(".html") if track_link else None,
                "artists": "; ".join(a.get_text(strip=True) for a in artist_links),
                "lead_artist_id": artist_links[0]["href"].split("/")[-1].removesuffix(".html") if artist_links else None,
                "days_on_chart": parse_int(tds[3].get_text()),
                "peak_pos": parse_int(tds[4].get_text()),
                "streams_daily": parse_int(tds[6].get_text()),
                "streams_7d": parse_int(tds[8].get_text()),
                "streams_total": parse_int(tds[10].get_text()),
            }
        )
    return pd.DataFrame(rows)


def _parse_history_table(table, track_id: str, freq: str) -> pd.DataFrame:
    header = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all(["th", "td"])]
    records = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["th", "td"])
        date_txt = cells[0].get_text(strip=True)
        if not re.fullmatch(r"\d{4}/\d{2}/\d{2}", date_txt):
            continue  # skip Total/Peak rows
        for country, cell in zip(header[1:], cells[1:]):
            m = re.fullmatch(r"(\d+)\(([\d,]+)\)", cell.get_text(strip=True))
            if not m:
                continue
            records.append(
                {
                    "track_id": track_id,
                    "freq": freq,
                    "date": pd.Timestamp(date_txt),
                    "country": country.lower(),
                    "rank": int(m.group(1)),
                    "streams": parse_int(m.group(2)),
                }
            )
    return pd.DataFrame(records)


def parse_track_history(track_id: str) -> pd.DataFrame:
    """Parse a kworb track page. Table 0 = weekly (FULL history), table 1 = daily (last ~31 days)."""
    soup = get_soup(f"{BASE}/spotify/track/{track_id}.html")
    tables = soup.find_all("table")
    if len(tables) < 2:
        return pd.DataFrame()
    weekly = _parse_history_table(tables[0], track_id, "weekly")
    daily = _parse_history_table(tables[1], track_id, "daily")
    return pd.concat([weekly, daily], ignore_index=True)

# %%
# 1) Current snapshots: global + selected countries (daily Top 200 with streams)
snapshots = []
for code in COUNTRIES:
    df = parse_country_snapshot(code, "daily")
    print(f"{code:>7}: {len(df)} rows")
    snapshots.append(df)
snap = pd.concat(snapshots, ignore_index=True)
snap.to_csv(OUTPUT_DIR / "kworb_daily_snapshots.csv", index=False)
print(f"\nSaved {len(snap)} rows -> kworb_daily_snapshots.csv")

# %%
# 2) History for the current global Top-N tracks
#    weekly = full chart-run history; daily = last ~31 days only (kworb page design)
top_tracks = snap[snap.country == "global"].nsmallest(TOP_N_HISTORY, "pos")
histories = []
for i, row in enumerate(top_tracks.itertuples(), 1):
    h = parse_track_history(row.track_id)
    h["track_name"] = row.track_name
    h["artists"] = row.artists
    histories.append(h)
    if i % 10 == 0 or i == len(top_tracks):
        print(f"histories: {i}/{len(top_tracks)}")
hist = pd.concat(histories, ignore_index=True)
hist.to_csv(OUTPUT_DIR / "kworb_track_histories.csv", index=False)
print(f"Saved {len(hist)} rows ({hist.track_id.nunique()} tracks) -> kworb_track_histories.csv")

# %%
# 3) Sanity checks + quick story-feasibility plots
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

g = snap[snap.country == "global"]
axes[0].scatter(g.pos, g.streams_daily, s=14, alpha=0.7)
axes[0].set_yscale("log")
axes[0].set_title("Global daily: streams vs rank")
axes[0].set_xlabel("rank")
axes[0].set_ylabel("daily streams (log)")

axes[1].hist(g.days_on_chart.dropna(), bins=40, color="teal")
axes[1].set_title("Global daily: days-on-chart distribution")
axes[1].set_xlabel("days on chart")

top50_by_country = {
    c: set(d.track_id) for c, d in snap.groupby("country") for d in [d.nsmallest(50, "pos")]
}
countries = [c for c in COUNTRIES if c != "global"]
overlap = [
    len(top50_by_country["global"] & top50_by_country[c]) / 50 for c in countries
]
axes[2].bar(countries, overlap, color="coral")
axes[2].set_title("Share of global Top-50 present in country Top-50")
axes[2].set_ylim(0, 1)
for i, v in enumerate(overlap):
    axes[2].text(i, v + 0.02, f"{v:.0%}", ha="center", fontsize=9)

fig.tight_layout()
fig.savefig(OUTPUT_DIR / "spotify_kworb_sanity.png", dpi=120)
print(f"\nSaved plot -> spotify_kworb_sanity.png")

# %%
# 4) Headline numbers for the story check (weekly = full chart runs)
glob_weekly = hist[(hist.country == "global") & (hist.freq == "weekly")]
runs = glob_weekly.groupby("track_id").agg(
    weeks=("date", "nunique"),
    best_rank=("rank", "min"),
    total_streams=("streams", "sum"),
    first_date=("date", "min"),
)
print("\nChart-run stats for current global Top-50 tracks (weekly history):")
print(runs.describe()[["weeks", "best_rank", "total_streams"]].round(1))
print("\nMedian days on chart (current Top 200 global):", int(g.days_on_chart.median()))
print("Tracks on chart > 1 year in current Top 200:", int((g.days_on_chart > 365).sum()))

# %% [markdown]
# Takeaway
# - charts.spotify.com anonymous API = latest weekly global snapshot only; full data needs user login.
# - kworb.net = frictionless public mirror WITH stream counts, ~70 countries.
# - Track pages: weekly table = FULL chart-run history (back to 2016); daily table = last ~31 days only.
# - The extracts above test the storyline: hit lifecycle (rise/peak/decay), stream concentration,
#   and global-vs-local diffusion of hits.
