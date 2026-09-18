"""Shared plotting style + save helpers so all experiment figures look consistent."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from . import config

PALETTE = {
    "retained": "#2ca02c",
    "churned": "#d62728",
    "primary": "#1f77b4",
    "accent": "#ff7f0e",
    "muted": "#7f7f7f",
}


def apply_style() -> None:
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 160,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "font.size": 10,
    })


def save_fig(fig: plt.Figure, name: str) -> Path:
    path = config.FIGURES_DIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path)
    print(f"Saved figure -> {path}")
    return path


def save_table(df, name: str) -> Path:
    path = config.TABLES_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"Saved table  -> {path}")
    return path
