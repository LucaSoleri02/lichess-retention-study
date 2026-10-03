"""Row hashing, splits, folds, ATE/bootstrap, policy-value estimator."""
import hashlib
import numpy as np
import pandas as pd

import config as C


def row_hash(df: pd.DataFrame) -> pd.Series:
    """Stable md5 hash of the full row tuple -> int64 in [0, 2**32).

    Includes ALL columns (features + treatment + outcomes + exposure) so that
    exact duplicate rows always share the same split/fold (no leakage through dups).
    """
    cols = list(df.columns)
    out = np.empty(len(df), dtype=np.int64)
    rows = df[cols].astype(str).agg("|".join, axis=1)
    for i, v in enumerate(rows):
        out[i] = int.from_bytes(hashlib.md5(v.encode()).digest()[:4], "big")
    return pd.Series(out, index=df.index)


def split_kind(df: pd.DataFrame) -> pd.Series:
    """'train' | 'validation' | 'test' from full-row hash (~70/15/15)."""
    b = row_hash(df) % 1000
    out = np.where(b < C.TRAIN_MAX, "train", np.where(b < C.VAL_MAX, "validation", "test"))
    return pd.Series(out, index=df.index)


def fold_id(df: pd.DataFrame) -> pd.Series:
    """0..4 fold from full-row hash, independent of split usage; OOF evaluation."""
    return row_hash(df) % C.N_FOLDS


def ate_bootstrap(y1: np.ndarray, y0: np.ndarray, n_boot: int = 1000, seed: int = 0):
    """ATE point estimate + percentile bootstrap CI + SE from boot dist."""
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        b1 = y1[rng.integers(0, len(y1), len(y1))]
        b0 = y0[rng.integers(0, len(y0), len(y0))]
        boot[i] = b1.mean() - b0.mean()
    ate = y1.mean() - y0.mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    se = boot.std()
    return float(ate), float(lo), float(hi), float(se)


def policy_value(df_eval: pd.DataFrame, scores: np.ndarray, budget: float,
                 y_col: str = C.VISIT, treat_col: str = C.TREATMENT,
                 n_boot: int = 1000, seed: int = 0):
    """Top-k targeting policy value estimated on randomized data (PLAN §2/§3).

    Same estimator for every policy (random / response / uplift):
      1. rank rows by score desc (ties: stable order)
      2. select top budget-fraction
      3. effect(k) = mean(Y | T=1, selected) - mean(Y | T=0, selected)
         ^= effect of targeting within the selected group via randomized arms
      4. incremental per 1,000 targeted = 1000 * effect(k)
      5. bootstrap CI over selected rows (resample arms independently)
      6. capture = incremental total in selected / incremental total full eval
    Returns dict.
    """
    y = df_eval[y_col].to_numpy()
    t = df_eval[treat_col].to_numpy()
    order = np.argsort(-scores, kind="stable")
    n_sel = int(round(len(df_eval) * budget))
    sel = order[:n_sel]

    y1, y0 = y[sel][t[sel] == 1], y[sel][t[sel] == 0]
    ate, lo, hi, se = ate_bootstrap(y1, y0, n_boot=n_boot, seed=seed)

    # scale-free capture share: effect * n_sel / total estimated incremental outcomes
    y1_all, y0_all = y[t == 1], y[t == 0]
    total_inc = (y1_all.mean() - y0_all.mean()) * len(df_eval)
    inc_sel = ate * n_sel
    capture = inc_sel / total_inc if total_inc != 0 else np.nan

    return {
        "budget": budget,
        "n_selected": n_sel,
        "n_treated_sel": len(y1),
        "n_control_sel": len(y0),
        "rate_treated_sel": float(y1.mean()),
        "rate_control_sel": float(y0.mean()),
        "effect": ate,
        "ci_lo": lo,
        "ci_hi": hi,
        "se": se,
        "incremental_per_1000": ate * 1000,
        "ci_per_1000": (lo * 1000, hi * 1000),
        "capture_share": capture,
    }


def random_policy_baseline(df_eval: pd.DataFrame, budget: float, seed: int = 0):
    """Random targeting baseline: expectation = ATE (randomization), but we
    draw a random subset to preserve sampling variance the same way."""
    rng = np.random.default_rng(seed)
    y = df_eval[C.VISIT].to_numpy()
    t = df_eval[C.TREATMENT].to_numpy()
    n_sel = int(round(len(df_eval) * budget))
    sel = rng.choice(len(df_eval), size=n_sel, replace=False)
    y1, y0 = y[sel][t[sel] == 1], y[sel][t[sel] == 0]
    ate, lo, hi, se = ate_bootstrap(y1, y0, n_boot=1000, seed=seed)
    y1_all, y0_all = y[t == 1], y[t == 0]
    total_inc = (y1_all.mean() - y0_all.mean()) * len(df_eval)
    return {
        "budget": budget, "n_selected": n_sel,
        "effect": float(ate), "ci_lo": float(lo), "ci_hi": float(hi), "se": float(se),
        "incremental_per_1000": float(ate * 1000),
        "capture_share": float(ate * n_sel / total_inc) if total_inc else np.nan,
    }
