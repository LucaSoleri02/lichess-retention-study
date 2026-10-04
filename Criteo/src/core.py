"""Row hashing, splits, folds, ATE/bootstrap.

Note: the notebook implementations of policy value / Qini (05, 04) are the
authoritative versions of those estimators; this module deliberately does not
duplicate them (single source of truth, per review).
"""
import hashlib

import numpy as np
import pandas as pd

import config as C


def row_hash(df: pd.DataFrame) -> pd.Series:
    """Stable md5 hash of the full row tuple -> int64 in [0, 2**32).

    Includes ALL columns (features + treatment + outcomes + exposure) so that
    exact duplicate rows always share the same split/fold (no leakage through dups).
    NOTE: 32-bit space -> ~20k colliding distinct-row pairs expected at 14M rows;
    content-based dedup (not hash dedup) is the exact procedure.
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


def is_train(df: pd.DataFrame) -> pd.Series:
    return df["row_hash"] % 1000 < C.TRAIN_MAX


def is_val(df: pd.DataFrame) -> pd.Series:
    b = df["row_hash"] % 1000
    return (b >= C.TRAIN_MAX) & (b < C.VAL_MAX)


def is_test(df: pd.DataFrame) -> pd.Series:
    return df["row_hash"] % 1000 >= C.VAL_MAX


def ate_bootstrap(y1: np.ndarray, y0: np.ndarray, n_boot: int = 1000, seed: int = 0):
    """ATE point estimate + percentile bootstrap CI + SE from boot dist.

    Vectorized: bootstrap SE of a proportion from n draws is exactly
    Binomial(n, p)/n, so arms are resampled as binomial counts (identical
    distribution to row-resampling, 1e5x faster at n in the millions).
    """
    rng = np.random.default_rng(seed)
    p1, p0 = y1.mean(), y0.mean()
    b1 = rng.binomial(len(y1), p1, n_boot) / len(y1)
    b0 = rng.binomial(len(y0), p0, n_boot) / len(y0)
    boot = b1 - b0
    ate = p1 - p0
    lo, hi = np.percentile(boot, [2.5, 97.5])
    se = boot.std()
    return float(ate), float(lo), float(hi), float(se)
