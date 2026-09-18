# %% [markdown]
# Experiment harness CLI — two layers, one entry point.
#
#   DATA-QUALITY layer ("can I trust the inputs?"):
#     python run_harness.py data                      all checks on all built artifacts
#     python run_harness.py data --dataset cohort     one artifact
#     python run_harness.py data --history            past DQ runs
#
#   MODEL layer ("did prediction improve?"):
#     python run_harness.py smoke                     end-to-end self-test on synthetic data
#     python run_harness.py run --target churn --model logreg --features core
#     python run_harness.py run --target patron --model gbdt --features all \
#         --param max_iter=300 --name gbdt_all_v2
#     python run_harness.py batch harness_runs/baseline_pack.json
#     python run_harness.py board [--target churn]
#     python run_harness.py best --target churn
#
# Model runs load cohort + window features (Population B). If the latest DQ run
# for the cohort has FAILs, a prominent warning is printed (warn-only coupling).

# %%
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from src import config, data_quality as dq
from src import harness as hz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PACK = PROJECT_ROOT / "harness_runs" / "baseline_pack.json"


# --- data loading -----------------------------------------------------------------

def load_model_frame() -> pd.DataFrame:
    """Cohort labels + window features, Population B only (PLAN §1)."""
    missing = [p for p in (config.COHORT_PARQUET, config.USER_WINDOW_PARQUET) if not p.exists()]
    if missing:
        raise SystemExit(
            "Model data not built yet. Missing: "
            + ", ".join(str(p) for p in missing)
            + "\nRun P1/P2 first (src.dump, src.cohort, src.features) — or use 'smoke'."
        )
    cohort = pd.read_parquet(config.COHORT_PARQUET)
    feats = pd.read_parquet(config.USER_WINDOW_PARQUET)
    df = cohort.merge(feats, on=["username", "population"], how="inner")
    return df[df["population"] == "B"].reset_index(drop=True)


def warn_if_dq_failing() -> None:
    fails = dq.latest_failures("cohort")
    if fails:
        print("!" * 72)
        print("WARNING: latest data-quality run has FAIL checks on the cohort:")
        for f in fails:
            print(f"  [XX] {f.check}: {f.detail}")
        print("Proceeding anyway (warn-only coupling). Consider: python run_harness.py data")
        print("!" * 72)


def warn_if_git_dirty() -> None:
    if hz._git_dirty():
        print("note: git working tree is dirty — run is logged against the last commit hash.")


# --- synthetic data (smoke test) -----------------------------------------------------

def make_synthetic_frame(n: int = 8000, seed: int = config.RANDOM_SEED) -> pd.DataFrame:
    """Pop-B-like frame with planted signal, so smoke verdicts are meaningful.

    Planted ground truth:
      churn  <- driven by days_active, week1_days_active, max_consecutive_losses
      patron <- driven by games_total, days_active
    """
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "username": [f"user{i:05d}" for i in range(n)],
        "games_total": rng.negative_binomial(5, 0.3, n) + 1,
        "days_active": rng.integers(1, 31, n),
        "sessions": rng.negative_binomial(3, 0.5, n) + 1,
        "week1_days_active": rng.integers(1, 8, n),
        "returned_after_signup_day": rng.random(n) < 0.6,
        "distinct_speeds": rng.integers(1, 5, n),
        "weekend_share": rng.random(n),
        "win_rate": np.clip(rng.normal(0.5, 0.1, n), 0, 1),
        "opp_rating_mismatch": rng.normal(0, 80, n),
        "rating_change": rng.normal(0, 60, n),
        "max_consecutive_losses": rng.negative_binomial(2, 0.4, n),
        "abandonment_share": np.clip(rng.normal(0.03, 0.03, n), 0, 1),
        "short_game_share": np.clip(rng.normal(0.2, 0.1, n), 0, 1),
        "first_rating": rng.normal(1500, 200, n),
    })
    df["games_per_active_day"] = df["games_total"] / df["days_active"]

    logit_churn = (-0.10 * df["days_active"] - 0.35 * df["week1_days_active"]
                   + 0.25 * df["max_consecutive_losses"] + 2.0)
    p_churn = 1 / (1 + np.exp(-logit_churn))
    df["active_90d"] = rng.random(n) > p_churn  # churn = NOT active

    logit_patron = (0.015 * df["games_total"] + 0.05 * df["days_active"] - 4.5)
    df["patron"] = rng.random(n) < 1 / (1 + np.exp(-logit_patron))
    return df


# --- subcommands ------------------------------------------------------------------------

def cmd_smoke(_args) -> None:
    # smoke runs write to a separate directory so synthetic results never
    # pollute the real leaderboard / DQ history (process exits right after).
    hz.HARNESS_DIR = config.OUTPUT_DIR / "harness_smoke"
    hz.LEADERBOARD_CSV = hz.HARNESS_DIR / "leaderboard.csv"
    hz.RUNS_DIR = hz.HARNESS_DIR / "runs"
    dq.DQ_LOG = hz.HARNESS_DIR / "data_quality.jsonl"

    print("== SMOKE TEST: synthetic data, planted signal ==")
    df = make_synthetic_frame()
    print(f"synthetic frame: {len(df):,} users | churn rate {1 - df['active_90d'].mean():.1%} "
          f"| patron rate {df['patron'].mean():.1%}\n")

    print("-- data-quality layer demo (synthetic games frame, one planted FAIL) --")
    good_games = pd.DataFrame({
        "white": ["a", "b", "c"], "black": ["d", "e", "f"],
        "whiteelo": [1500, 1600, 1700], "blackelo": [1500, 1600, 1700],
        "result": ["1-0", "0-1", "1/2-1/2"],
        "datetime": pd.to_datetime(["2016-01-05", "2016-01-06", "2016-01-07"]),
        "speed": ["blitz", "rapid", "bullet"],
        "termination": ["Normal", "Time forfeit", "Normal"],
        "nummoves": [40, 55, 30],
        "timecontrol": ["300+0", "600+0", "60+0"],
        "time_control_initial_s": [300, 600, 60],
    })
    bad_games = good_games.copy()
    bad_games.loc[0, "result"] = "9-9"  # planted integrity failure
    for name, frame in [("synthetic-good", good_games), ("synthetic-bad", bad_games)]:
        print(f"[{name}] (volume.row_count FAIL is expected on a toy 3-row frame)")
        results = dq.check_games(frame, config.COHORT_MONTH)
        dq.print_report(results)
        print()

    print("-- model layer demo (batch on synthetic frame) --")
    pack = json.loads(BASELINE_PACK.read_text())
    experiments = [hz.Experiment(**{**e, "features": hz.resolve_features(e["features"])})
                   for e in pack["experiments"]]
    hz.run_batch(experiments, df)
    print("\nsmoke test complete.")


def cmd_run(args) -> None:
    warn_if_git_dirty()
    df = load_model_frame()
    warn_if_dq_failing()
    params = dict(p.split("=", 1) for p in args.param)
    params = {k: _coerce(v) for k, v in params.items()}
    exp = hz.Experiment(
        name=args.name or f"{args.target}_{args.model}_{args.features.replace('+', '-')}",
        target=args.target, model=args.model,
        features=hz.resolve_features(args.features), params=params,
    )
    record = hz.run_experiment(exp, df)
    print(hz.log_run(record))
    print(json.dumps({k: v for k, v in record.items() if k.startswith("test_")}, indent=2))


def cmd_batch(args) -> None:
    warn_if_git_dirty()
    df = load_model_frame()
    warn_if_dq_failing()
    pack_path = Path(args.pack)
    if not pack_path.is_absolute():
        pack_path = (PROJECT_ROOT / pack_path).resolve()
    pack = json.loads(pack_path.read_text())
    experiments = [hz.Experiment(**{**e, "features": hz.resolve_features(e["features"])})
                   for e in pack["experiments"]]
    print(f"running pack '{pack.get('pack', args.pack)}': {len(experiments)} experiments\n")
    hz.run_batch(experiments, df)


def cmd_board(args) -> None:
    if not hz.LEADERBOARD_CSV.exists():
        raise SystemExit("no runs yet — leaderboard is empty")
    board = pd.read_csv(hz.LEADERBOARD_CSV)
    if args.target:
        board = board[board["target"] == args.target]
    metric = f"test_{args.metric}"
    cols = ["run_at", "name", "target", "model", metric, "test_roc_auc", "n_train", "git"]
    board = board.sort_values(metric, ascending=False)
    print(board[cols].to_string(index=False))


def cmd_best(args) -> None:
    if not hz.LEADERBOARD_CSV.exists():
        raise SystemExit("no runs yet — leaderboard is empty")
    board = pd.read_csv(hz.LEADERBOARD_CSV)
    targets = [args.target] if args.target else board["target"].unique()
    metric = f"test_{hz.PRIMARY_METRIC}"
    for t in targets:
        sub = board[board["target"] == t]
        if sub.empty:
            continue
        best = sub.loc[sub[metric].idxmax()]
        print(f"{t:8s} champion: {best['name']} ({hz.PRIMARY_METRIC}={best[metric]:.3f}, "
              f"auc={best['test_roc_auc']:.3f}, {best['run_at']})")


def cmd_data(args) -> None:
    if args.history:
        if not dq.DQ_LOG.exists():
            raise SystemExit("no DQ runs yet")
        with open(dq.DQ_LOG, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                print(f"{rec['run_at']}  PASS={rec['n_pass']} WARN={rec['n_warn']} "
                      f"FAIL={rec['n_fail']} SKIP={rec['n_skip']}")
        return
    results = dq.run_checks(dataset=args.dataset)
    dq.print_report(results)
    summary = dq.log_results(results)
    print(f"\nDQ run logged: PASS={summary['n_pass']} WARN={summary['n_warn']} "
          f"FAIL={summary['n_fail']} SKIP={summary['n_skip']}")
    if summary["n_fail"]:
        sys.exit(1)


def _coerce(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


# --- CLI wiring ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_harness.py",
        description="Experiment harness: data-quality checks + model experiments with verdicts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="end-to-end self-test on synthetic data")

    p_run = sub.add_parser("run", help="run one model experiment")
    p_run.add_argument("--target", required=True, choices=list(hz.TARGETS))
    p_run.add_argument("--model", default="logreg", choices=["logreg", "gbdt", "rf"])
    p_run.add_argument("--features", default="core",
                       help="preset (core/habit/experience/control/all), 'a+b' combo, or comma list")
    p_run.add_argument("--param", action="append", default=[],
                       help="model param as k=v (repeatable)")
    p_run.add_argument("--name", default=None)
    p_run.set_defaults(fn=cmd_run)

    p_batch = sub.add_parser("batch", help="run a JSON pack of experiments")
    p_batch.add_argument("pack", help="path to pack JSON (e.g. harness_runs/baseline_pack.json)")
    p_batch.set_defaults(fn=cmd_batch)

    p_board = sub.add_parser("board", help="show the leaderboard")
    p_board.add_argument("--target", default=None, choices=list(hz.TARGETS))
    p_board.add_argument("--metric", default=hz.PRIMARY_METRIC,
                         choices=["capture@10pct", "precision@10pct", "lift@10pct",
                                  "roc_auc", "log_loss"])
    p_board.set_defaults(fn=cmd_board)

    p_best = sub.add_parser("best", help="show the current champion per target")
    p_best.add_argument("--target", default=None, choices=list(hz.TARGETS))
    p_best.set_defaults(fn=cmd_best)

    p_data = sub.add_parser("data", help="run data-quality checks")
    p_data.add_argument("--dataset", default=None,
                        choices=dq.DATASETS)
    p_data.add_argument("--history", action="store_true")
    p_data.set_defaults(fn=cmd_data)

    sub.choices["smoke"].set_defaults(fn=cmd_smoke)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
