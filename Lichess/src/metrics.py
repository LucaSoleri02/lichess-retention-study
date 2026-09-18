"""Evaluation metrics for the experiment harness.

Headline metric per PLAN §7 (E2): **top-decile capture** — "the highest-risk 10%
of users accounts for X% of eventual churn". AUC is reported but never headlined.
All functions take (y_true binary, y_score in [0,1]) and are threshold-free.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import log_loss, roc_auc_score


def _top_mask(y_score: np.ndarray, frac: float) -> np.ndarray:
    n = max(1, int(round(len(y_score) * frac)))
    order = np.argsort(-np.asarray(y_score, dtype=float))
    mask = np.zeros(len(y_score), dtype=bool)
    mask[order[:n]] = True
    return mask


def capture_at_frac(y_true: np.ndarray, y_score: np.ndarray, frac: float = 0.10) -> float:
    """Share of all positives captured by the top `frac` of scored users."""
    y_true = np.asarray(y_true)
    if y_true.sum() == 0:
        return float("nan")
    return float(y_true[_top_mask(y_score, frac)].sum() / y_true.sum())


def precision_at_frac(y_true: np.ndarray, y_score: np.ndarray, frac: float = 0.10) -> float:
    y_true = np.asarray(y_true)
    return float(y_true[_top_mask(y_score, frac)].mean())


def lift_at_frac(y_true: np.ndarray, y_score: np.ndarray, frac: float = 0.10) -> float:
    base = float(np.asarray(y_true).mean())
    if base == 0:
        return float("nan")
    return precision_at_frac(y_true, y_score, frac) / base


def evaluate(y_true: np.ndarray, y_score: np.ndarray, frac: float = 0.10) -> dict[str, float]:
    """Full metric bundle for one scored holdout."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    out = {
        f"capture@{int(frac * 100)}pct": capture_at_frac(y_true, y_score, frac),
        f"precision@{int(frac * 100)}pct": precision_at_frac(y_true, y_score, frac),
        f"lift@{int(frac * 100)}pct": lift_at_frac(y_true, y_score, frac),
        "roc_auc": float(roc_auc_score(y_true, y_score)) if y_true.any() else float("nan"),
        "log_loss": float(log_loss(y_true, np.clip(y_score, 1e-7, 1 - 1e-7))),
        "base_rate": float(y_true.mean()),
        "n": int(len(y_true)),
    }
    return out
