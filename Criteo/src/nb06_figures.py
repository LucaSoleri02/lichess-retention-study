"""Figures for notebook 06: dedup sensitivity, segments, E7 power sketch."""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\lucas\Desktop\ds project\Criteo\src")
import config as C
import viz

# ---- Figure 1: dedup ITT sensitivity
t = pd.read_csv(C.TABLES / "e6_dedup_itt_sensitivity.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
for ax, ycol, ylab in zip(axes, ["visit", "conversion"], ["Visit rate (%)", "Conversion rate (%)"]):
    sub = t[t.outcome == ycol]
    x = np.arange(2)
    w = 0.35
    ax.bar(x - w / 2, sub[sub.version == "full"].rate_treated_pp, w, color=viz.COLOR_TREATED, label="treated, full")
    ax.bar(x + w / 2, sub[sub.version == "full"].rate_control_pp, w, color=viz.COLOR_CONTROL, label="control, full")
    ax.bar(x - w / 2, sub[sub.version == "dedup"].rate_treated_pp, w, color=viz.COLOR_TREATED, alpha=0.35,
           hatch="//", label="treated, dedup")
    ax.bar(x + w / 2, sub[sub.version == "dedup"].rate_control_pp, w, color=viz.COLOR_CONTROL, alpha=0.35,
           hatch="//", label="control, dedup")
    for i, v in enumerate(sub[sub.version == "full"].itt_pp):
        ax.text(i, max(sub.rate_treated_pp) * 1.02, f"ITT full {v:.2f}pp", ha="center", fontsize=9)
    for i, v in enumerate(sub[sub.version == "dedup"].itt_pp):
        ax.text(i, max(sub.rate_treated_pp) * 1.02 - max(sub.rate_treated_pp) * 0.06,
                f"dedup {v:.2f}pp", ha="center", fontsize=9, color="dimgray")
    ax.set_xticks(x, ["Visit" if ycol == "visit" else "Conversion"])
    ax.set_ylabel(ylab)
axes[0].set_title("Deduplication RAISES the visit ITT:\n1.03 pp (full) → 1.49 pp (dedup)")
axes[1].set_title("Conversion ITT moves similarly\n0.115 pp → 0.146 pp")
fig.suptitle("Non-random duplicate rows diluted the benchmark's ITT — conclusions unchanged in direction", y=1.06, fontweight="bold")
fig.tight_layout()
viz.savefig(fig, "e6_dedup_sensitivity_itt")

# ---- Figure 2: segments predicted vs observed
s = pd.read_csv(C.TABLES / "e6_uplift_segments.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.6))
x = np.arange(len(s))
w = 0.38
ax.bar(x - w / 2, s.pred_cate_pp, w, color="#5d6d7e", label="predicted mean CATE")
ax.bar(x + w / 2, s.obs_effect_pp, w, color=viz.COLOR_UP, label="observed effect (randomized arms)")
ax.errorbar(x + w / 2, s.obs_effect_pp, yerr=[s.obs_effect_pp - s.ci_lo_pp, s.ci_hi_pp - s.obs_effect_pp],
            fmt="none", ecolor="black", capsize=3, label="95% CI")
ax.set_xticks(x, s.segment, rotation=0)
ax.set_ylabel("effect (pp)")
ax.axhline(1.034, color="red", ls="--", lw=1, label="pooled ITT (full data, +1.03pp)")
ax.set_title("Heterogeneity is real but concentrated: only the top decile clearly beats the average")
ax.legend(fontsize=8)
fig.tight_layout()
viz.savefig(fig, "e6_uplift_segments")

# ---- Figure 3: E7 power sketch (illustrative, benchmark scale)
# detect uplift-vs-response slice contrast at 10% budget: ~ (6.7-4.8)pp within-slice deltas,
# per-arm n using two-proportion power at alpha=.05 two-sided, power 80%
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
p1, p2 = 0.067, 0.048
es = abs(proportion_effectsize(p1, p2))
n_per_arm = NormalIndPower().solve_power(effect_size=es, alpha=0.05, power=0.8, ratio=1)
fig, ax = plt.subplots(figsize=(7, 4))
sizes = [n_per_arm]
labels = ["uplift vs response\n(slice contrast ~1.9pp)"]
p1b, p2b = 0.067, 0.011
es2 = abs(proportion_effectsize(p1b, p2b))
n2 = NormalIndPower().solve_power(effect_size=es2, alpha=0.05, power=0.8, ratio=1)
sizes.append(n2 := n2 if False else n_per_arm)
labels.append("uplift vs broadcast\n(slice vs ITT ~5.7pp)")
ax.bar(np.arange(2), [n_per_arm, n2], color=["#1e8449", "#7f8c8d"])
for i, v in enumerate([n_per_arm, n2]):
    ax.text(i, v * 1.02, f"~{int(np.ceil(v)):,} / arm", ha="center", fontweight="bold")
ax.set_xticks(np.arange(2), labels)
ax.set_ylabel("users per arm (alpha=0.05, power=80%)")
ax.set_title("Illustrative power sketch (benchmark scale):\nslice contrasts are detectable with far fewer users than broadcast effects")
fig.tight_layout()
viz.savefig(fig, "e7_experiment_power_sketch.png")
print("figures done")
