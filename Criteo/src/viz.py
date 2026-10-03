"""Shared matplotlib style + save helpers (Lichess-project conventions, light version)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as C

plt.rcParams.update({
    "figure.dpi": C.FIG_DPI,
    "savefig.dpi": C.FIG_DPI,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "font.size": 10,
})

COLOR_TREATED = "#c0392b"
COLOR_CONTROL = "#2471a3"
COLOR_UP = "#1e8449"
COLOR_RANDOM = "#7f8c8d"


def savefig(fig, name):
    for ext in ("png",):
        path = C.FIGURES / f"{name}.{ext}"
        fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def savetable(df, name):
    path = C.TABLES / f"{name}.csv"
    df.to_csv(path, index=False)
    return path
