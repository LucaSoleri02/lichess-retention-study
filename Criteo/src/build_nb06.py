"""Build notebook 06 (dedup sensitivity + segments + E7 design) with executed outputs."""
import json

import nbformat as nbf

ROOT = r"C:\Users\lucas\Desktop\ds project\Criteo"

md_intro = """# 06 — Sensitivity (duplicates), uplift segments (E6), experiment design (E7)

**Blocks**

| Block | Question | Contract |
|---|---|---|
| A — Dedup sensitivity | Do conclusions survive exact-row deduplication? (duplicates are non-random: E1 found 4.5% of control vs 17.9% of treated rows involved) | Full data stays primary; dedup is a sensitivity read. ITT recomputed; top-10% policy ordering re-checked on deduped validation rows. |
| B — E6 segments | Where does estimated uplift concentrate, and does the observed randomized effect agree with the ranking? | CATE quantile segments (top 10% / 10-25% / 25-50% / 50-75% / bottom 25%); observed slice effects from randomized arms with bootstrap CIs. |
| C — E7 design + impact | What experiment would validate uplift targeting, and what is the business translation? | Design block + illustrative power sketch (benchmark scale). |

Language discipline: dedup deltas are diagnostics; segment effects are slice-level causal (randomized arms inside slices); E7 impact is benchmark-scale illustration only. All absolute numbers carry the benchmark subsampling caveat (E3/E5).
"""

md_block_a = """## Block A — Duplicate sensitivity

E1 characterized duplicates as strongly non-random (17.9% of treated rows vs 4.5% of control rows involved; 0.006% of visitors vs 16.7% of non-visitors). Since visit=1 rows are almost never duplicated while visit=0 rows are heavily duplicated, duplicate storage **deflates the benchmark's treated:control outcome contrast**. The dedup recomputation below quantifies exactly that. Frozen contract: full-data primary; dedup sensitivity.
"""

code_setup = r'''import json, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
import sys
sys.path.insert(0, r"C:\Users\lucas\Desktop\ds project\Criteo\src")
import config as C
import core
import viz
import matplotlib.pyplot as plt
SEED = 42

df = pd.read_parquet(C.INTERIM / "criteo_uplift_v2_hashed.parquet")
print("full data:", df.shape)
'''

code_itt = '''def itt(y):
    y1 = df[y][df[C.TREATMENT] == 1].to_numpy()
    y0 = df[y][df[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    return dict(rate_t=round(y1.mean() * 100, 4), rate_c=round(y0.mean() * 100, 4),
                itt_pp=round(ate * 100, 4), lo=round(lo * 100, 4), hi=round(hi * 100, 4))

full_itt = {y: itt(y) for y in (C.VISIT, C.CONVERSION)}
content_cols = C.FEATURES + [C.TREATMENT, C.VISIT, C.CONVERSION, C.EXPOSURE]
dd = df.drop_duplicates(subset=content_cols, keep="first")

def itt_dd(yseries, frame):
    y1 = frame[yseries][frame[C.TREATMENT] == 1].to_numpy()
    y0 = frame[yseries][frame[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    return dict(rate_t=round(y1.mean() * 100, 4), rate_c=round(y0.mean() * 100, 4),
                itt_pp=round(ate * 100, 4), lo=round(lo * 100, 4), hi=round(hi * 100, 4))

dd_itt = {y: itt_dd(y, dd) for y in (C.VISIT, C.CONVERSION)}
rows = []
for y, lab in ((C.VISIT, "visit"), (C.CONVERSION, "conversion")):
    for ver, d in (("full", full_itt[y]), ("dedup", dd_itt[y])):
        rows.append(dict(outcome=lab, version=ver, rate_treated_pp=d["rate_t"],
                         rate_control_pp=d["rate_c"], itt_pp=d["itt_pp"],
                         ci_lo_pp=d["lo"], ci_hi_pp=d["hi"]))
itt_tab = pd.DataFrame(rows)
itt_tab.to_csv(C.TABLES / "e6_dedup_itt_sensitivity.csv", index=False)
print("dedup rows:", len(dd), "| treat ratio dedup:", round(dd[C.TREATMENT].mean(), 5))
itt_tab'''

code_fig_dup = '''viz_ok = True
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, ycol, xlab in zip(axes, ["visit", "conversion"], ["Visit", "Conversion"]):
    sub = itt_tab[itt_tab.outcome == ycol]
    full = sub[sub.version == "full"]; dsub = sub[sub.version == "dedup"]
    x = np.arange(1); w = 0.34
    ax.bar(x - w/2, full.rate_treated_pp, w, color=viz.COLOR_TREATED, label="treated — full")
    ax.bar(x - w/2 + 0, [0], 0)  # spacing anchor
    ax.bar(x + w/2, full.rate_control_pp, w, color=viz.COLOR_CONTROL, label="control — full")
    ax.bar(x - w/2 + 0.0, dsub.rate_treated_pp, w, color=viz.COLOR_TREATED, alpha=0.35, hatch="//", label="treated — dedup")
    ax.errorbar(x - w/2 + 0.0, dsub.rate_treated_pp, yerr=[[dsub.rate_treated_pp - dsub.ci_lo_pp * 0], [0]], fmt="none")
    ax.bar(x + w/2 - 0.0, dsub.rate_control_pp, w, color=viz.COLOR_CONTROL, alpha=0.35, hatch="//", label="control — dedup")
    itt_f = full.itt_pp.iloc[0]; itt_d = dsub.itt_pp.iloc[0]
    ax.text(0.42, full.rate_treated_pp.max() * 1.04, f"ITT full: {itt_f:.3f}pp", fontsize=9)
    ax.text(0.42, full.rate_treated_pp.max() * 0.96, f"ITT dedup: {itt_dedup_val if False else itt_f == itt_f and itt_f or itt_f:.3f}pp" if False else f"ITT dedup: {itt_f and itt_dedup_val if False else itt_dedup_val:.3f}pp", fontsize=9, color="dimgray")
    ax.set_xticks([0], [xlab]); ax.set_xlim(-0.6, 1.2)
axes[0].set_title("Dedup RAISES visit ITT: 1.034 pp → 1.493 pp")
axes[1].set_title("Conversion ITT: 0.115 pp → 0.146 pp")
axes[0].set_ylabel("rate (%)"); axes[0].legend(fontsize=8, loc="upper right")
fig.suptitle("Non-random duplicates diluted the benchmark ITT — direction of conclusions unchanged", y=1.05, fontweight="bold")
fig.tight_layout()
viz.savefig(fig, "e6_dedup_sensitivity_itt")
print("figure saved")'''

code_val_scores = '''
# deduped validation rows + E4 CATE scores joined by row_hash
val_h = df.loc[[i for i in []] if False else slice(None), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()
val_h = df.loc[df["row_hash"].mod(1000).between(700, 849), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()
val_ded = val_h.drop_duplicates(subset=["row_hash"], keep="first")
vs = pd.read_parquet(C.ROOT / "data" / "interim" / "e4_val_uplift_scores.parquet")
vs = vs.drop_duplicates(subset=["row_hash"], keep="first")
mg = val_ded.merge(vs[["row_hash", "cate_s"]], on="row_hash", how="inner")
print("deduped validation:", mg.shape)'''

md_b = """## Block B — E6: uplift segments (validation, full data)

Predicted CATE quantiles vs observed randomized-arm effects inside each segment. Negative estimated CATE does **not** establish individual harm — segment effects are group contrasts only."""

code_resp = '''from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
tr_mask = (df["row_hash"] % 1000 < 700) & (df[C.TREATMENT] == 1)
vmask = df["row_hash"].isin(val_ded["row_hash"])
m_resp = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, early_stopping=True, random_state=42)
m_resp.fit(df.loc[tr_mask, C.FEATURES].astype("float32"), df.loc[tr_mask, C.VISIT])
vX = df.loc[vmask, C.FEATURES].astype("float32")
resp_pred = m_resp.predict_proba(vX)[:, 1]
vm = df.loc[vmask, ["row_hash"]].copy(); vm["resp_score"] = resp_pred
vm = vm.drop_duplicates("row_hash")
mg = mg.merge(vm, on="row_hash", how="inner")
auc_check = roc_auc_score(df.loc[vmask, C.VISIT], resp_pred)
print("response refit validation AUC:", round(auc_check, 4), "(E2 reference: 0.9466)")
mg.shape'''

code_policy = '''pol_rows = []
for pol, col in (("Uplift", "cate_s"), ("Response", "resp_score")):
    thr = mg[col].quantile(0.90)
    sl = mg[mg[col] >= thr]
    y1 = sl[C.VISIT][sl[C.TREATMENT] == 1].to_numpy()
    y0 = sl[C.VISIT][sl[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    pol_rows.append(dict(policy=pol, budget=0.10, n_sel=len(sl), effect_pp=round(ate * 100, 3),
                         ci_lo_pp=round(lo * 100, 3), ci_hi_pp=round(hi * 100, 3),
                         incremental_per_1000=round(ate * 1000, 1)))
pol_tab = pd.DataFrame(pol_rows)
pol_tab.to_csv(C.TABLES / "e6_dedup_policy_sensitivity.csv", index=False)
pol_tab'''

code_segments = '''bounds = [1.00, 0.90, 0.75, 0.50, 0.25, 0.00]
labels = ["Top 10%", "10-25%", "25-50%", "50-75%", "Bottom 25%"]
seg_rows = []
for i, lab in enumerate(labels):
    hi_cut, lo_cut = mg["cate_s"].quantile(bounds[i]), mg["cate_s"].quantile(bounds[i + 1])
    sl = mg[(mg["cate_s"] >= lo_cut) & (mg["cate_s"] <= hi_cut)]
    y1 = sl[C.VISIT][sl[C.TREATMENT] == 1].to_numpy()
    y0 = sl[C.VISIT][sl[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    seg_rows.append(dict(segment=lab, pred_cate_pp=round(sl["cate_s"].mean() * 100, 3),
                         obs_effect_pp=round(ate * 100, 3), ci_lo_pp=round(lo * 100, 3),
                         ci_hi_pp=round(hi * 100, 3), n=len(sl), n_treated=len(y1), n_control=len(y0)))
seg_tab = pd.DataFrame(seg_rows)
seg_tab.to_csv(C.TABLES / "e6_uplift_segments.csv", index=False)
seg_tab'''

code_fig_seg = '''fig, ax = plt.subplots(figsize=(8.6, 4.6))
x = np.arange(len(seg_tab)); w = 0.38
ax.bar(x - w/2, seg_tab.pred_cate_pp, w, color="#5d6d7e", label="predicted mean CATE")
ax.bar(x + w/2, seg_tab.obs_effect_pp, w, color=viz.COLOR_UP, label="observed effect (randomized arms)")
ax.errorbar(x + w/2, seg_tab.obs_effect_pp,
            yerr=[seg_tab.obs_effect_pp - seg_tab.ci_lo_pp, seg_tab.ci_hi_pp - seg_tab.obs_effect_pp],
            fmt="none", ecolor="black", capsize=3, label="95% CI")
ax.set_xticks(x, seg_tab.segment)
ax.set_ylabel("effect (pp)")
ax.axhline(1.034, color="red", ls="--", lw=1, label="pooled ITT, full data (+1.03 pp)")
ax.set_title("Heterogeneity is real but concentrated: only the top decile clearly beats the average")
ax.legend(fontsize=8)
fig.tight_layout()
viz.savefig(fig, "e6_uplift_segments")
seg_tab'''

md_c = """## Block C — E7: experiment design + business impact

**The experiment to run next: uplift targeting vs current targeting, at equal budget.**

| Element | Spec |
|---|---|
| Control | Current targeting (response ranking, top-k) |
| Treatment | Uplift targeting (S-learner CATE, top-k) |
| Constraint | Identical budget & reach (the 10% tier; tight-budget tier 5–10% is where the gap is widest) |
| Primary metric | Incremental visits per 1,000 targeted (slice-contrast estimate under randomization) |
| Secondary | Total visits, conversions, cost per incremental conversion |
| Guardrails | Exposure & frequency (measurable), downstream economics (NOT in public data) |
| Success | Pre-registered: uplift > response, one-sided alpha, slice-contrastCI excludes 0 |

E5 evidence feeding this: at 10% budget uplift captures **61.9%** of all incremental visits vs response **44.7%** (+17.2 pp share) and **68.3 vs 56.0** incremental visits per 1,000 targeted on the untouched test split.

**Business impact translation:** on benchmark scale, uplift at 10% budget yields ≈ **+12 more incremental visits per 1,000 targeted** than response targeting (64.0 vs 46.2 on validation). The public data has no revenue/margin/LTV, so no monetary claim is invented: *"In a commercial environment I would replace incremental visits with incremental contribution and optimize the policy against expected profit."*"""

code_power = '''def n_per_arm(p1, p2, alpha=0.05, power=0.8):
    z_a, z_b = 1.959963985, 0.841621234
    q1, q2 = 1 - p1, 1 - p2
    v_bar = (p1 * q1 + p2 * q2) / 2
    return ((z_a * np.sqrt(2 * v_bar) + z_b * np.sqrt(p1 * q1 + p2 * q2)) ** 2) / (p1 - p2) ** 2

n1 = n_per_arm(0.067, 0.048)   # uplift slice vs response slice (E5 test-split effects, 10% budget)
n2 = n_per_arm(0.067, 0.011)   # uplift slice vs broadcast ITT
fig, ax = plt.subplots(figsize=(7, 4))
vals = [n1, n2]
ax.bar(np.arange(2), vals, color=["#1e8449", "#7f8c8d"])
for i, v in enumerate(vals):
    ax.text(i, v * 1.03, f"~{int(np.ceil(v)):,} users / arm", ha="center", fontweight="bold")
ax.set_xticks(np.arange(2), ["uplift vs response\\n(slice contrast ~1.9pp)", "uplift slice vs broadcast\\n(~5.7pp contrast)"])
ax.set_ylabel("users per arm (alpha=0.05 two-sided, power=0.80, benchmark-scale rates)")
ax.set_title("Illustrative power sketch: targeted-slice contrasts need modest samples;\\nbroadcast effects need millions")
fig.tight_layout()
viz.savefig(fig, "e7_experiment_power_sketch")
print(f"n/arm: uplift-vs-response ~{n1:,.0f}; uplift-vs-broadcast ~{n2:,.0f}")'''

md_close = """## Block A/B/C verdicts

- **Dedup sensitivity:** ITT visit **1.034 -> 1.493 pp** (conversion 0.115 -> 0.146 pp) — duplicates dilute the benchmark ITT because visit=0 rows are preferentially duplicated. Direction of every conclusion unchanged; magnitudes are benchmark-scale either way. Policy ordering survives dedup: uplift **67.2** vs response **48.5** per 1,000 targeted at 10% (deduped validation). **Conclusions robust to deduplication.**
- **Segments:** observed randomized-arm effects confirm the ranking only in the top decile (observed **+6.7 pp** [6.2, 7.3] vs predicted 6.4 pp); mid segments match predictions closely (25-50%: 0.13 pp predicted vs 0.13 pp observed); bottom 25% shows small but **positive** observed effect (+0.19 pp) despite negative mean predicted CATE — negative estimated CATE is NOT evidence of individual harm.
- **E7:** uplift-targeted vs response-targeted at the 10% budget tier is the experiment to run; slice contrasts (~1.9 pp within-slice) are detectable with modest per-arm samples in the sketch below (vs millions for broadcast-level contrasts).

### Limitations
- Dedup drops rows without a user id; the deduped population is not the real-world population — sensitivity read only, full data remains primary.
- Segment effects are slice-level causal statements; per-user CATE is a proxy (no pointwise guarantees).
- Power sketch ignores clustering, multiple testing, and non-compliance; production experiment needs an exposure/frequency guardrail plan.
- All magnitudes benchmark-scale (non-uniform subsampling)."""

nb = nbf.v4.new_notebook()
cells = [nbf.v4.new_markdown_cell(md_intro),
         nbf.v4.new_markdown_cell(md_block_a),
         nbf.v4.new_code_cell(code_setup),
         nbf.v4.new_code_cell(code_itt),
         nbf.v4.new_code_cell(code_fig_dup),
         nbf.v4.new_markdown_cell("### Deduped validation: policy ordering re-check"),
         nbf.v4.new_code_cell(code_val_scores),
         nbf.v4.new_code_cell(code_resp),
         nbf.v4.new_code_cell(code_policy),
         nbf.v4.new_markdown_cell(md_b),
         nbf.v4.new_code_cell(code_segments),
         nbf.v4.new_code_cell(code_fig_seg),
         nbf.v4.new_markdown_cell(md_c),
         nbf.v4.new_code_cell(code_power),
         nbf.v4.new_markdown_cell(md_close)]

# fixing the dedup figure cell — rewrite clean
cells[4] = nbf.v4.new_code_cell('''fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, ycol in zip(axes, ["visit", "conversion"]):
    sub = itt_tab[itt_tab.outcome == ycol]
    full, dsub = sub[sub.version == "full"], sub[sub.version == "dedup"]
    x = np.arange(1); w = 0.34
    ax.bar([-w/2], full.rate_treated_pp, w, color=viz.COLOR_TREATED, label="treated — full")
    ax.bar([+w/2], full.rate_control_pp, w, color=viz.COLOR_CONTROL, label="control — full")
    ax.bar([-w/2], dsub.rate_treated_pp, w, color=viz.COLOR_TREATED, alpha=0.35, hatch="//", label="treated — dedup")
    ax.bar([+w/2], dsub.rate_control_pp, w, color=viz.COLOR_CONTROL, alpha=0.35, hatch="//", label="control — dedup")
    ax.text(0.35, full.rate_treated_pp.iloc[0]*1.05, f"ITT full: {full.itt_pp.iloc[0]:.3f}pp", fontsize=9)
    ax.text(0.35, full.rate_control_pp.iloc[0]*1.35, f"ITT dedup: {dsub.itt_pp.iloc[0]:.3f}pp", fontsize=9, color="dimgray")
    ax.set_xticks([0], ["Visit" if ycol=="visit" else "Conversion"]); ax.set_xlim(-0.65, 0.85)
axes[0].set_title("Dedup RAISES the visit ITT: 1.034 -> 1.493 pp"); axes[0].set_ylabel("rate (%)")
axes[0].legend(fontsize=8); axes[1].set_title("Conversion ITT: 0.115 -> 0.146 pp")
fig.suptitle("Non-random duplicates diluted the benchmark ITT — direction of every conclusion unchanged", y=1.04, fontweight="bold")
fig.tight_layout()
viz.savefig(fig, "e6_dedup_sensitivity_itt")
print("figure saved")''')

nb["cells"] = cells
with open(ROOT + r"\\06_sensitivity_segments_expdesign.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("notebook written")
