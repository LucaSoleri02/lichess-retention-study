"""Download and stream-parse Lichess monthly database dumps (PGN headers only).

Full months (2016-01, 2016-02): downloaded to data/raw, parsed to typed games
parquet tables. Recent month (2026-08, ~30 GB): NEVER fully downloaded — we only
need username presence for the seenAt cross-check (PLAN §4), so we stream the
.zst over HTTP and stop after config.RECENT_MONTH_MAX_GAMES (~first days of the
month, ~1.5 GB transfer). The cap underestimates "played recently" slightly, so
the login-vs-behavior gap it yields is a conservative bound.

Header fields kept (standard Lichess PGN tags):
    UTCDate, UTCTime, White, Black, WhiteElo, BlackElo, WhiteRatingDiff,
    BlackRatingDiff, Result, TimeControl, Termination, ECO, Opening
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from typing import IO, Iterator

import pandas as pd
import requests
import zstandard as zstd

from . import config

HEADER_RE = re.compile(r'^\[(\w+) "([^"]*)"\]$')

KEEP_TAGS = (
    "UTCDate", "UTCTime", "White", "Black", "WhiteElo", "BlackElo",
    "WhiteRatingDiff", "BlackRatingDiff", "Result", "TimeControl",
    "Termination", "ECO", "Opening",
)

MOVE_NUMBER_RE = re.compile(r"(\d+)\.")  # last match in movetext = fullmove count


# --- downloading --------------------------------------------------------------

def download_dump(month: str, chunk_mb: int = 8) -> Path:
    """Download a full monthly dump to data/raw (idempotent)."""
    url = config.DUMP_URL_TEMPLATE.format(month=month)
    dest = config.dump_path(month)
    if dest.exists():
        print(f"Dump already present: {dest} ({dest.stat().st_size / 1e9:.2f} GB)")
        return dest
    print(f"Downloading {url} -> {dest}")
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=chunk_mb * 1024 * 1024):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r{done / 1e9:.2f}/{total / 1e9:.2f} GB", end="", flush=True)
    print()
    return dest


# --- header parsing -------------------------------------------------------------

def _iter_headers_from_text(text: IO[str]) -> Iterator[dict[str, str]]:
    """Yield PGN header dicts from a text stream.

    Moves are never stored, but the last move number of each game is captured
    as NumMoves (fullmoves) — needed for the short-game feature in E5.
    """
    headers: dict[str, str] = {}
    in_movetext = False
    max_move = 0
    for line in text:
        line = line.rstrip("\n")
        if not in_movetext:
            m = HEADER_RE.match(line)
            if m:
                headers[m.group(1)] = m.group(2)
            elif line == "" and headers:
                in_movetext = True  # blank line ends the header block
                max_move = 0
        else:
            if line.startswith("["):
                out = {k: v for k, v in headers.items() if k in KEEP_TAGS}
                out["NumMoves"] = str(max_move)
                yield out
                headers = {}
                m = HEADER_RE.match(line)
                if m:
                    headers[m.group(1)] = m.group(2)
                in_movetext = False
            else:
                for m in MOVE_NUMBER_RE.finditer(line):
                    max_move = max(max_move, int(m.group(1)))
    if headers:
        out = {k: v for k, v in headers.items() if k in KEEP_TAGS}
        out["NumMoves"] = str(max_move)
        yield out


def iter_game_headers(month: str) -> Iterator[dict[str, str]]:
    """Stream header dicts from a locally downloaded dump."""
    path = config.dump_path(month)
    dctx = zstd.ZstdDecompressor()
    with open(path, "rb") as fh, dctx.stream_reader(fh) as reader:
        text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
        yield from _iter_headers_from_text(text)


def parse_dump_to_parquet(month: str, report_every: int = 250_000) -> pd.DataFrame:
    """Parse a full monthly dump into a typed games table, saved as parquet."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_path = config.games_parquet(month)
    if out_path.exists():
        existing = pd.read_parquet(out_path, columns=["utcdate"])
        month_end = pd.Period(month, freq="M").end_time.normalize()
        if not existing.empty and pd.to_datetime(existing["utcdate"], errors="coerce").max() >= month_end:
            print(f"Existing parquet found: {out_path}; normalizing schema before continuing")
            df = pd.read_parquet(out_path)
            df = _type_games(df)
            df.to_parquet(out_path, index=False, compression="zstd")
            return df
        print(f"Incomplete parquet found: {out_path}; rebuilding from the raw dump")
        out_path.unlink()

    writer = None
    batch: list[dict] = []
    n = 0

    def flush():
        nonlocal writer, batch
        if not batch:
            return
        table = pa.Table.from_pylist(batch)
        if writer is None:
            writer = pq.ParquetWriter(out_path, table.schema, compression="zstd")
        writer.write_table(table)
        batch = []

    for headers in iter_game_headers(month):
        batch.append(headers)
        n += 1
        if n % report_every == 0:
            print(f"{month}: {n:,} games parsed...")
            flush()
    flush()
    if writer:
        writer.close()

    df = pd.read_parquet(out_path)
    df = _type_games(df)
    df.to_parquet(out_path, index=False, compression="zstd")
    print(f"Saved {len(df):,} games -> {out_path}")
    return df


def normalize_games_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the parquet schema uses the lowercase names expected by downstream code."""
    mapping = {col: col.lower() for col in df.columns if col not in {"__fragment_index", "__batch_index", "__last_in_fragment", "__filename"}}
    normalized = df.rename(columns=mapping)
    if "timecontrol" in normalized.columns and "time_control_initial_s" not in normalized.columns:
        normalized["time_control_initial_s"] = normalized["timecontrol"].str.split("+").str[0].pipe(
            pd.to_numeric, errors="coerce"
        )
    return normalized


def _type_games(df: pd.DataFrame) -> pd.DataFrame:
    """Cast raw string headers to analysis-ready dtypes."""
    df = normalize_games_columns(df)
    df["datetime"] = pd.to_datetime(
        df["utcdate"] + " " + df["utctime"], format="%Y.%m.%d %H:%M:%S", errors="coerce"
    )
    for col in ("whiteelo", "blackelo", "whiteratingdiff", "blackratingdiff", "nummoves"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "time_control_initial_s" not in df.columns:
        df["time_control_initial_s"] = df["timecontrol"].str.split("+").str[0].pipe(
            pd.to_numeric, errors="coerce"
        )
    # Lichess speed buckets from initial clock seconds (mirrors Lichess conventions)
    df["speed"] = pd.cut(
        df["time_control_initial_s"],
        bins=[-1, 29, 179, 479, 1499, float("inf")],
        labels=["ultraBullet", "bullet", "blitz", "rapid", "classical"],
    )
    return df


# --- recent-month capped scan (PLAN §4) -----------------------------------------

def scan_recent_month_active_users(
    month: str = config.RECENT_MONTH,
    max_games: int = config.RECENT_MONTH_MAX_GAMES,
    out_path: Path = config.RECENT_ACTIVE_USERS_PARQUET,
) -> pd.DataFrame:
    """Stream the recent dump over HTTP, collect usernames, stop after max_games.

    Output: one row per distinct username seen, with games observed in the scan
    and the datetime of the last scanned game (documents scan coverage).
    """
    url = config.DUMP_URL_TEMPLATE.format(month=month)
    print(f"Streaming {url} (capped at {max_games:,} games)...")
    counts: dict[str, int] = {}
    last_dt = None
    n = 0
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(resp.raw) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
            for headers in _iter_headers_from_text(text):
                w, b = headers.get("White"), headers.get("Black")
                if w:
                    counts[w] = counts.get(w, 0) + 1
                if b:
                    counts[b] = counts.get(b, 0) + 1
                last_dt = f"{headers.get('UTCDate')} {headers.get('UTCTime')}"
                n += 1
                if n % 500_000 == 0:
                    print(f"{n:,} games scanned, {len(counts):,} users, last game {last_dt}")
                if n >= max_games:
                    break
    print(f"Scan stopped at {n:,} games; last scanned game: {last_dt}")
    df = pd.DataFrame({"username": list(counts), "games_in_scan": list(counts.values())})
    df.to_parquet(out_path, index=False, compression="zstd")
    print(f"Saved {len(df):,} active usernames -> {out_path}")
    return df


if __name__ == "__main__":
    # usage: python -m src.dump 2016-01 | 2016-02 | recent
    which = sys.argv[1] if len(sys.argv) > 1 else config.COHORT_MONTH
    if which == "recent":
        scan_recent_month_active_users()
    else:
        download_dump(which)
        parse_dump_to_parquet(which)
