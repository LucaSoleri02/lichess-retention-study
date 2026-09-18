"""Experiment harness: run a declared experiment, log it, and say whether it helped.

Design rules:
- **Deterministic split**: username-hash train/test split, identical for every run.
  Two runs are comparable iff they use the same target and split — the hash
  guarantees that without storing split files.
- **Append-only registry**: every run appends to outputs/harness/leaderboard.csv
  and writes a JSON sidecar with params. Nothing is ever overwritten.
- **Verdict**: a run is compared against the best previous run *for the same
  target* on the primary metric (top-decile capture). Output is explicit:
  IMPROVED / NO IMPROVEMENT / FIRST RUN.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config, metrics

HARNESS_DIR = config.OUTPUT_DIR / "harness"
LEADERBOARD_CSV = HARNESS_DIR / "leaderboard.csv"
RUNS_DIR = HARNESS_DIR / "runs"

PRIMARY_METRIC = "capture@10pct"
TEST_FRAC = 0.20

# Targets the harness knows how to derive from the cohort table.
TARGETS = {
    "churn": lambda df: (~df["active_90d"]).astype(int),   # 1 = churned
    "patron": lambda df: df["patron"].astype(int),         # 1 = paid supporter
}

# Feature presets (PLAN §7): composable with '+', e.g. "core+habit".
# Elo appears only in 'control' — a control variable, never a headline (PLAN §5).
FEATURE_PRESETS = {
    "core": ["games_total", "days_active", "games_per_active_day", "sessions"],
    "habit": ["week1_days_active", "returned_after_signup_day", "distinct_speeds", "weekend_share"],
    "experience": ["win_rate", "opp_rating_mismatch", "rating_change",
                   "max_consecutive_losses", "abandonment_share", "short_game_share"],
    "control": ["first_rating"],
}
FEATURE_PRESETS["all"] = sum(FEATURE_PRESETS.values(), [])


def resolve_features(spec: str) -> list[str]:
    """'core+habit' -> preset columns; 'a,b,c' -> explicit list (escape hatch)."""
    if "+" in spec:
        cols: list[str] = []
        for part in spec.split("+"):
            cols.extend(resolve_features(part))
        return list(dict.fromkeys(cols))
    if spec in FEATURE_PRESETS:
        return list(FEATURE_PRESETS[spec])
    return [c.strip() for c in spec.split(",") if c.strip()]


@dataclass
class Experiment:
    """One harness run: a model + a feature set + a target."""
    name: str
    target: str                      # key into TARGETS
    features: list[str]
    model: str = "logreg"            # logreg | gbdt | rf
    params: dict = field(default_factory=dict)


def make_model(exp: Experiment) -> Pipeline:
    if exp.model == "logreg":
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, **exp.params)),
        ])
    if exp.model == "gbdt":
        # native NaN handling, no scaling needed
        return Pipeline([
            ("clf", HistGradientBoostingClassifier(random_state=config.RANDOM_SEED, **exp.params)),
        ])
    if exp.model == "rf":
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_jobs=-1, random_state=config.RANDOM_SEED, **exp.params)),
        ])
    raise ValueError(f"unknown model: {exp.model}")


def deterministic_split(usernames: pd.Series, test_frac: float = TEST_FRAC) -> pd.Series:
    """True = test row. Stable across runs/machines (md5 of username)."""
    def bucket(u: str) -> int:
        return int(hashlib.md5(u.encode()).hexdigest(), 16) % 1000
    return usernames.map(lambda u: bucket(u) < test_frac * 1000)


def _git_hash() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "nogit"


def _git_dirty() -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return bool(out)
    except Exception:
        return False


def _data_fingerprint(df: pd.DataFrame) -> str:
    """Row count + content hash, so a silently rebuilt input table is visible."""
    content = pd.util.hash_pandas_object(df, index=False).values.tobytes()
    return f"{len(df)}:{hashlib.md5(content).hexdigest()[:10]}"


def run_experiment(exp: Experiment, df: pd.DataFrame) -> dict:
    """Train on train split, score test split, return the full run record."""
    missing = [f for f in exp.features if f not in df.columns]
    if missing:
        raise ValueError(f"{exp.name}: missing features {missing}")

    y = TARGETS[exp.target](df)
    is_test = deterministic_split(df["username"])
    X_train, X_test = df.loc[~is_test, exp.features], df.loc[is_test, exp.features]
    y_train, y_test = y[~is_test], y[is_test]

    model = make_model(exp)
    model.fit(X_train, y_train)
    score = model.predict_proba(X_test)[:, 1]

    record = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": _git_hash(),
        "name": exp.name,
        "target": exp.target,
        "model": exp.model,
        "params": json.dumps(exp.params),
        "features": json.dumps(exp.features),
        "n_train": int(len(y_train)),
        **{f"test_{k}": v for k, v in metrics.evaluate(y_test.to_numpy(), score).items()},
    }
    return record


def log_run(record: dict) -> str:
    """Append to leaderboard CSV + JSON sidecar. Returns the verdict string."""
    HARNESS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    sidecar = RUNS_DIR / f"{record['run_at'].replace(':', '')}_{record['name']}.json"
    sidecar.write_text(json.dumps(record, indent=2), encoding="utf-8")

    if LEADERBOARD_CSV.exists():
        board = pd.read_csv(LEADERBOARD_CSV)
    else:
        board = pd.DataFrame()
    board = pd.concat([board, pd.DataFrame([record])], ignore_index=True)
    board.to_csv(LEADERBOARD_CSV, index=False)

    return verdict(board, record)


def verdict(board: pd.DataFrame, record: dict) -> str:
    """Compare this run to the best previous run for the same target."""
    metric = f"test_{PRIMARY_METRIC}"
    same_target = board[(board["target"] == record["target"]) & (board["name"] != record["name"])]
    this = record[metric]
    if same_target.empty:
        return f"FIRST RUN for target '{record['target']}' ({PRIMARY_METRIC}={this:.3f})"
    best_prev = same_target[metric].max()
    best_name = same_target.loc[same_target[metric].idxmax(), "name"]
    if this > best_prev:
        return (f"IMPROVED: {PRIMARY_METRIC} {this:.3f} > previous best {best_prev:.3f} "
                f"({best_name}) for target '{record['target']}'")
    return (f"NO IMPROVEMENT: {PRIMARY_METRIC} {this:.3f} <= best {best_prev:.3f} "
            f"({best_name}) for target '{record['target']}'")


def run_batch(experiments: list[Experiment], df: pd.DataFrame) -> pd.DataFrame:
    """Run a list of experiments, log each, print verdicts, return the board."""
    records = []
    for exp in experiments:
        record = run_experiment(exp, df)
        v = log_run(record)
        records.append(record)
        print(f"[{exp.target:6s}] {exp.name:34s} -> {v}")
    return pd.DataFrame(records)
