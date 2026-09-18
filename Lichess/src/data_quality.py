"""Data-quality harness: sanity checks on pipeline artifacts, with history.

Same philosophy as the model harness: declared checks, append-only history,
explicit verdicts. Statuses: PASS / WARN / FAIL / SKIP (artifact not built yet).

Coupling to the model harness (decided 2026-09-17): model runs *warn* when the
latest DQ run for their input artifact has FAILs, but never block.

Thresholds live in the THRESHOLDS dict below (decided 2026-09-17: one dict, in
code, versioned with the repo). Row-count ranges are first-pass estimates —
tighten them in P1 against Lichess's published monthly totals.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config

# --- thresholds (tune here) ---------------------------------------------------

THRESHOLDS = {
    "games": {
        # first-pass estimates; tighten in P1 vs published monthly totals
        "row_count_range": {"2016-01": (2_000_000, 4_500_000),
                            "2016-02": (2_000_000, 4_500_000)},
        "max_null_rate": 0.01,
        "elo_range": (600, 3200),
        "max_single_speed_share": 0.95,
        "min_timecontrol_parse_rate": 0.95,
    },
    "cohort": {
        "pop_b_share_range": (0.01, 0.30),
        "active_90d_range": (0.005, 0.40),
        "patron_max": 0.15,
        "max_null_rate": 0.01,
    },
    "window": {
        "max_days_active": 31,
        "max_games_per_active_day": 500,
        "pop_b_min_coverage": 0.95,  # share of Pop-B users with >=1 in-window game
    },
    "drift": {
        "row_count_warn_pct": 5.0,
        "rate_warn_pp": 2.0,  # percentage points
    },
}

DQ_LOG = config.OUTPUT_DIR / "harness" / "data_quality.jsonl"

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"


@dataclass
class CheckResult:
    dataset: str
    check: str
    status: str
    detail: str
    value: float | None = None


def _r(dataset: str, check: str, ok: bool, detail: str, value=None,
       warn: bool = False) -> CheckResult:
    status = PASS if ok else (WARN if warn else FAIL)
    return CheckResult(dataset, check, status, detail, value)


# --- games parquet checks -------------------------------------------------------

GAME_REQUIRED_COLS = ["white", "black", "whiteelo", "blackelo", "result",
                      "datetime", "speed", "termination", "nummoves", "timecontrol"]
VALID_RESULTS = {"1-0", "0-1", "1/2-1/2"}


def check_games(df: pd.DataFrame, month: str) -> list[CheckResult]:
    t = THRESHOLDS["games"]
    ds = f"games_{month}"
    out: list[CheckResult] = []

    missing = [c for c in GAME_REQUIRED_COLS if c not in df.columns]
    out.append(_r(ds, "schema.required_columns", not missing,
                  f"missing: {missing}" if missing else "all present"))
    if missing:
        return out  # downstream checks would be meaningless

    lo, hi = t["row_count_range"].get(month, (0, float("inf")))
    out.append(_r(ds, "volume.row_count", lo <= len(df) <= hi,
                  f"{len(df):,} rows (expected {lo:,}-{hi:,})", len(df)))

    null_rate = float(df[GAME_REQUIRED_COLS].isna().mean().max())
    out.append(_r(ds, "integrity.null_rates", null_rate <= t["max_null_rate"],
                  f"worst column null rate {null_rate:.2%}", null_rate))

    dupes = int(df.duplicated(subset=["white", "black", "datetime"]).sum())
    out.append(_r(ds, "integrity.no_duplicates", dupes == 0,
                  f"{dupes:,} duplicate (white,black,datetime) rows", dupes))

    start = pd.Timestamp(month + "-01")
    end = start + pd.offsets.MonthBegin(1)
    in_month = df["datetime"].between(start, end - pd.Timedelta(seconds=1)).mean()
    out.append(_r(ds, "integrity.datetimes_in_month", in_month >= 0.999,
                  f"{in_month:.3%} of games inside {month}", float(in_month)))

    bad_results = int((~df["result"].isin(VALID_RESULTS)).sum())
    out.append(_r(ds, "integrity.result_enum", bad_results == 0,
                  f"{bad_results:,} rows outside {sorted(VALID_RESULTS)}", bad_results))

    elo_lo, elo_hi = t["elo_range"]
    elo_ok = (df["whiteelo"].between(elo_lo, elo_hi) & df["blackelo"].between(elo_lo, elo_hi)).mean()
    out.append(_r(ds, "integrity.elo_range", elo_ok >= 0.999,
                  f"{elo_ok:.3%} of games with both Elos in [{elo_lo},{elo_hi}]", float(elo_ok)))

    min_moves = float(df["nummoves"].min())
    out.append(_r(ds, "integrity.nummoves_positive", min_moves >= 1,
                  f"min nummoves = {min_moves:g}", min_moves))

    top_speed = float(df["speed"].value_counts(normalize=True).iloc[0])
    out.append(_r(ds, "distribution.speed_mix", top_speed <= t["max_single_speed_share"],
                  f"largest speed share {top_speed:.1%}", top_speed, warn=True))

    parsed = float(df["time_control_initial_s"].notna().mean())
    out.append(_r(ds, "distribution.timecontrol_parse", parsed >= t["min_timecontrol_parse_rate"],
                  f"{parsed:.1%} time controls parsed", parsed))
    return out


# --- cohort parquet checks --------------------------------------------------------

def check_cohort(df: pd.DataFrame) -> list[CheckResult]:
    t = THRESHOLDS["cohort"]
    ds = "cohort"
    out: list[CheckResult] = []

    dupes = int(df["username"].duplicated().sum())
    out.append(_r(ds, "integrity.unique_username", dupes == 0, f"{dupes:,} duplicate users", dupes))

    null_users = int(df["username"].isna().sum())
    out.append(_r(ds, "integrity.no_null_usernames", null_users == 0,
                  f"{null_users:,} null usernames", null_users))

    bad_order = int((df["created_at"] > df["seen_at"]).sum())
    out.append(_r(ds, "integrity.created_before_seen", bad_order == 0,
                  f"{bad_order:,} users with created_at > seen_at", bad_order))

    pop_b_share = float((df["population"] == "B").mean())
    lo, hi = t["pop_b_share_range"]
    out.append(_r(ds, "labels.pop_b_share", lo <= pop_b_share <= hi,
                  f"Pop B = {pop_b_share:.1%} (expected {lo:.0%}-{hi:.0%})", pop_b_share))

    active = float(df["active_90d"].mean())
    lo, hi = t["active_90d_range"]
    out.append(_r(ds, "labels.active_90d_rate", lo <= active <= hi,
                  f"active_90d = {active:.1%} (expected {lo:.1%}-{hi:.0%})", active))

    patron = float(df["patron"].mean())
    out.append(_r(ds, "labels.patron_rate", patron <= t["patron_max"],
                  f"patron = {patron:.1%} (max {t['patron_max']:.0%})", patron))

    seg_sum = int(df["segment"].value_counts().sum())
    out.append(_r(ds, "labels.segments_cover_all", seg_sum == len(df),
                  f"segments cover {seg_sum:,}/{len(df):,}"))

    if "played_recent_month" in df.columns:
        coverage = float(df["played_recent_month"].notna().mean())
        out.append(_r(ds, "coverage.recent_month_crosscheck", coverage >= 0.99,
                      f"cross-check populated for {coverage:.1%}", coverage))
    else:
        out.append(CheckResult(ds, "coverage.recent_month_crosscheck", WARN,
                               "column missing (recent scan not merged yet)"))
    return out


# --- window-feature checks ---------------------------------------------------------

def check_window_features(df: pd.DataFrame, cohort: pd.DataFrame | None) -> list[CheckResult]:
    t = THRESHOLDS["window"]
    ds = "window_features"
    out: list[CheckResult] = []

    rate_cols = [c for c in df.columns if c.endswith("_share") or c == "win_rate"]
    if rate_cols:
        bad = int(((df[rate_cols] < 0) | (df[rate_cols] > 1)).sum().sum())
        out.append(_r(ds, "bounds.rates_in_unit_interval", bad == 0,
                      f"{bad:,} out-of-range values across {rate_cols}", bad))

    max_days = float(df["days_active"].max())
    out.append(_r(ds, "bounds.days_active", max_days <= t["max_days_active"],
                  f"max days_active = {max_days:g} (window cap {t['max_days_active']})", max_days))

    min_games = float(df["games_total"].min())
    out.append(_r(ds, "bounds.games_total_positive", min_games >= 1,
                  f"min games_total = {min_games:g}", min_games))

    if cohort is not None:
        pop_b = cohort.loc[cohort["population"] == "B", "username"]
        covered = pop_b.isin(set(df.loc[df["population"] == "B", "username"])).mean()
        out.append(_r(ds, "completeness.pop_b_coverage",
                      covered >= t["pop_b_min_coverage"],
                      f"{covered:.1%} of Pop-B users have window features", float(covered)))
    return out


# --- drift vs previous DQ run -------------------------------------------------------

def _previous_values(dataset: str) -> dict[str, float]:
    """Last recorded numeric values per check for this dataset, from the DQ log."""
    if not DQ_LOG.exists():
        return {}
    prev: dict[str, float] = {}
    with open(DQ_LOG, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            for c in rec["checks"]:
                if c["dataset"] == dataset and c["value"] is not None:
                    prev[c["check"]] = c["value"]
    return prev


def check_drift(dataset: str, results: list[CheckResult]) -> list[CheckResult]:
    """Compare row counts / key rates against the previous DQ run (WARN only)."""
    t = THRESHOLDS["drift"]
    prev = _previous_values(dataset)
    out: list[CheckResult] = []
    for res in results:
        if res.value is None or res.check not in prev:
            continue
        old = prev[res.check]
        if old == 0:
            continue
        delta_pct = (res.value - old) / old * 100
        drifted = abs(delta_pct) > t["row_count_warn_pct"]
        out.append(_r(dataset, f"drift.{res.check}", not drifted,
                      f"{res.check}: {old:,.4g} -> {res.value:,.4g} ({delta_pct:+.1f}%)",
                      res.value, warn=True))
    return out


# --- registry & runner -----------------------------------------------------------------

def _load(dataset: str):
    if dataset == f"games_{config.COHORT_MONTH}":
        p = config.games_parquet(config.COHORT_MONTH)
        return (pd.read_parquet(p), config.COHORT_MONTH) if p.exists() else None
    if dataset == f"games_{config.WINDOW_MONTH}":
        p = config.games_parquet(config.WINDOW_MONTH)
        return (pd.read_parquet(p), config.WINDOW_MONTH) if p.exists() else None
    if dataset == "cohort":
        return (pd.read_parquet(config.COHORT_PARQUET), None) if config.COHORT_PARQUET.exists() else None
    if dataset == "window_features":
        return (pd.read_parquet(config.USER_WINDOW_PARQUET), None) if config.USER_WINDOW_PARQUET.exists() else None
    raise ValueError(f"unknown dataset: {dataset}")


DATASETS = [f"games_{config.COHORT_MONTH}", f"games_{config.WINDOW_MONTH}",
            "cohort", "window_features"]


def run_checks(dataset: str | None = None, with_drift: bool = True) -> list[CheckResult]:
    """Run all registered checks (or one dataset). Missing artifacts -> SKIP."""
    targets = [dataset] if dataset else DATASETS
    results: list[CheckResult] = []
    for ds in targets:
        loaded = _load(ds)
        if loaded is None:
            results.append(CheckResult(ds, "artifact.exists", SKIP, "not built yet"))
            continue
        df, month = loaded
        if month is not None:
            res = check_games(df, month)
        elif ds == "cohort":
            res = check_cohort(df)
        else:
            cohort = pd.read_parquet(config.COHORT_PARQUET) if config.COHORT_PARQUET.exists() else None
            res = check_window_features(df, cohort)
        if with_drift:
            res = res + check_drift(ds, res)
        results.extend(res)
    return results


def log_results(results: list[CheckResult]) -> dict:
    """Append one DQ run to the jsonl history; return its summary."""
    DQ_LOG.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_pass": sum(r.status == PASS for r in results),
        "n_warn": sum(r.status == WARN for r in results),
        "n_fail": sum(r.status == FAIL for r in results),
        "n_skip": sum(r.status == SKIP for r in results),
        "checks": [asdict(r) for r in results],
    }
    with open(DQ_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")
    return summary


def latest_failures(dataset: str) -> list[CheckResult]:
    """FAIL checks from the most recent DQ run covering `dataset` (for gating)."""
    if not DQ_LOG.exists():
        return []
    with open(DQ_LOG, encoding="utf-8") as fh:
        runs = [json.loads(line) for line in fh if line.strip()]
    for rec in reversed(runs):
        checks = [CheckResult(**c) for c in rec["checks"] if c["dataset"] == dataset]
        if checks:
            return [c for c in checks if c.status == FAIL]
    return []


def print_report(results: list[CheckResult]) -> None:
    width = max(len(r.check) for r in results) if results else 10
    for r in results:
        icon = {PASS: "ok", WARN: "!!", FAIL: "XX", SKIP: "--"}[r.status]
        print(f"  [{icon}] {r.dataset:22s} {r.check:{width}s}  {r.detail}")
