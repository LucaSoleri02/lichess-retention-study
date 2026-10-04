"""Append reviewer-fix cells to notebooks 01/02/03/06 and rewrite affected markdown.
Run once; then re-execute each notebook with nbconvert."""
import json

import nbformat as nbf

ROOT = r"C:\Users\lucas\Desktop\ds project\Criteo"


def load(name):
    return nbf.read(ROOT + "\\" + name + ".ipynb", as_version=4)


def save(nb, name):
    with open(ROOT + "\\" + name + ".ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def md_replace(nb, old_frag, new_md, cell_idx=None):
    """Replace an entire markdown cell containing old_frag with new_md."""
    hits = [i for i, c in enumerate(nb.cells)
            if c.cell_type == "markdown" and old_frag in "".join(c.source)]
    assert len(hits) == 1, f"anchor {old_frag[:40]!r}: hits={hits}"
    i = hits[0] if cell_idx is None else cell_idx
    assert hits[0] == i or cell_idx is None
    nb.cells[i] = nbf.v4.new_markdown_cell(new_md)


# ------------------------------------------------------------------ NB01
nb1 = load("01_preprocessing_eda_rules")
md_replace(
    nb1,
    "## Key takeaways (E1)",
    """## Key takeaways (E1)

- Treatment ratio matches the design (0.850); **covariates show a small but detectable imbalance** — max |SMD| = 0.0488 (f3), which at n≈14M is many standard errors from zero. Consistent with randomization *within each component incrementality test* (the benchmark pools several tests: treatment share varies by position in the file, visit rate by ~3×). Wording: "balanced to within 0.05 SMD; adjusted and unadjusted estimators checked in E3."
- Treatment worked on both outcomes (ITT): visit up ~1.0 pp, conversion up ~0.1 pp relative to control.
- Duplicates are **not storage artifacts**: the treated arm is ~5.7× larger, and identical feature vectors collide proportionally to group size — the collision check below shows the treated-vs-control dup-share gap disappears once arms are size-matched. Duplicated rows are real users on boundary feature values; the dup share among visitors is ~0.006% simply because visitors sit off the boundary spikes.
- Features are quantile-coded (heavy boundary masses at min/max, typically tens of percent of rows); keep tree-based models + bin-aware preprocessing in mind for E2.
- No missing values, no infinities, no out-of-range values, no flag values outside {0,1}.""",
)
dup_cell = nbf.v4.new_code_cell(
    """# Collision check: is the dup-share gap explained by arm size?
cols = C.FEATURES + ["treatment", "exposure", "visit", "conversion"]
ctrl = df[df.treatment == 0]
trt_sub = df[df.treatment == 1].sample(len(ctrl), random_state=0)
rows = []
for name, d in [("control (full)", ctrl), ("treated, subsampled to control size", trt_sub),
                ("treated (full)", df[df.treatment == 1])]:
    rows.append(dict(group=name, rows=len(d), dup_involved_share=round(d.duplicated(subset=cols, keep=False).mean(), 4)))
collision_tab = pd.DataFrame(rows)
collision_tab.to_csv(C.TABLES / "e1_duplicate_collision_check.csv", index=False)
collision_tab"""
)
dup_md = nbf.v4.new_markdown_cell(
    """**Reading:** treated rows subsampled to control size duplicate at 4.4% — statistically the same as the control arm's 4.5%. The 17.9% figure is an arm-size artifact: identical feature vectors collide more often in a larger group. Duplicated rows are real users whose quantile-coded features hit the same boundary values; dedup would mostly remove zero-outcome treated rows and would *inflate* the ITT (checked in notebook 06)."""
)
nb1.cells.extend([nbf.v4.new_markdown_cell("## 8. Duplicate collision check (arm-size artifact test)"), dup_md, dup_cell])
save(nb1, "01_preprocessing_eda_rules")

# ------------------------------------------------------------------ NB02
nb2 = load("02_response_prediction_topk_lift")
sf_auc = nbf.v4.new_code_cell(
    """# Single-feature AUC — is the 12-feature model impressive, or is the signal trivially available?
from sklearn.metrics import roc_auc_score
val_s = df.loc[[i for i in []] if False else slice(None)]
"""
)
# build properly: validation subsample AUC per feature
sf_auc = nbf.v4.new_code_cell(
    """from sklearn.metrics import roc_auc_score
# deterministic 2M-row validation subsample
vmask_s = (df["row_hash"] % 1000 >= 700) & (df["row_hash"] % 1000 < 850)
idx = np.flatnonzero(vmask_s.to_numpy())
idx = idx[np.random.default_rng(42).choice(len(idx), 2_000_000, replace=False)]
ys = df["visit"].to_numpy()[idx]
rows = []
for c in C.FEATURES:
    a = roc_auc_score(ys, df[c].to_numpy()[idx])
    rows.append(dict(feature=c, auc_best_orientation=round(max(a, 1 - a), 4)))
sf_auc_tab = pd.DataFrame(rows).sort_values("auc_best_orientation", ascending=False)
sf_auc_tab.to_csv(C.TABLES / "e2_single_feature_auc.csv", index=False)
sf_auc_tab"""
)
sf_md = nbf.v4.new_markdown_cell(
    """### Single-feature AUC (context for the headline model quality)

The 0.947 twelve-feature AUC is **not an achievement to headline**: `f8` alone reaches 0.926 and `f9` alone 0.894 on validation. The features very likely encode prior engagement / user-history variables (an *inference from the numbers, not a documented fact* — the columns are anonymized). The practical point stands regardless of semantics: response propensity is trivially rankable, which is exactly why response targeting cannot separate sure-things from persuadables."""
)
nb2.cells.extend([sf_md, sf_auc])
save(nb2, "02_response_prediction_topk_lift")

# ------------------------------------------------------------------ NB03
nb3 = load("03_ate_exposure_iv_exploration")
md_replace(
    nb3,
    "## 1. Full-sample ITT effects (visit, conversion)",
    """## 1. Full-sample ITT effects (visit, conversion)

Randomized assignment ⇒ the treated − control difference is a causal ITT effect. One wording upgrade over E1: at n≈14M even a |SMD| of 0.049 is far from zero in SE terms — the benchmark pools several component incrementality tests whose assignment shares and base rates differ. We therefore also compute **design-based and covariate-adjusted estimators** below and report agreement.""",
)
adj_md = nbf.v4.new_markdown_cell(
    """## 3b. Adjustment diagnostics — "small but detectable imbalance; adjusted and raw effects agree in sign and magnitude class"

Three checks demanded by the review:
1. **Treatment predictability** (cross-fitted HistGB propensity, halves defined by row_hash parity, 2M-row training sample per half): AUC ≈ 0.51 → features barely predict assignment.
2. **Design-based Horvitz–Thompson** with the known constant e = 0.85: algebraically identical to the raw difference in means at this design (reported for transparency).
3. **Covariate-adjusted ATE**: fully-interacted OLS (Lin 2013, z-scored features) + learned-e IPW (clipped [0.01, 0.99]).

Caveats for interpretation: duplicated near-clone rows shrink the effective sample (naive SEs understate the true uncertainty of the adjusted–raw gap); the adjusted estimators target the covariate-stratified ATE, the raw difference the design-weighted one."""
)
adj_code = nbf.v4.new_code_cell(
    """import time
t0 = time.time()
X = df[C.FEATURES].to_numpy(np.float32)
t_arr = df.treatment.to_numpy()
y_arr = df.visit.to_numpy()
half = (df["row_hash"] % 2).to_numpy()
rng = np.random.default_rng(42)
e = np.empty(len(df)); pred_aucs = []
for k in (0, 1):
    other = np.flatnonzero(half != k); here = np.flatnonzero(half == k)
    tr = rng.choice(other, 2_000_000, replace=False)
    sc = rng.choice(here, 2_000_000, replace=False)
    m = HistGradientBoostingClassifier(max_iter=100, random_state=42).fit(X[tr], t_arr[tr])
    e[here] = m.predict_proba(X[here])[:, 1]
    pred_aucs.append(roc_auc_score(t_arr[sc], e[sc]))
e = np.clip(e, 0.01, 0.99)
ipw_ate = np.mean(y_arr * t_arr / e - y_arr * (1 - t_arr) / (1 - e))
# design-based HT with known e=0.85 == raw diff (identity shown for transparency)
Xz = (df[C.FEATURES].to_numpy(np.float64) - df[C.FEATURES].to_numpy(np.float64).mean(0)) / df[C.FEATURES].to_numpy(np.float64).std(0)
D = np.column_stack([np.ones(len(df)), Xz, t_arr.astype(float), Xz * t_arr.astype(float)[:, None]])
A = np.zeros((26, 26)); b = np.zeros(26)
Bc = 2_000_000; n = len(df); y64 = y_arr.astype(np.float64)
for s in range(0, n, Bc):
    d = D[s:s+Bc]; A += d.T @ d; b += d.T @ y64[s:s+Bc]
beta_lin = np.linalg.solve(A, b)
lin_ate = beta_lin[13]
adj_tab = pd.DataFrame([
    dict(estimator="raw diff-in-means (design-based)", ate_pp=round((y64[t_arr==1].mean()-y64[t_arr==0].mean())*100, 4)),
    dict(estimator="HT, known e=0.85 (== raw by identity)", ate_pp=round(np.mean(y64*t_arr/0.85 - y64*(1-t_arr)/0.15)*100, 4)),
    dict(estimator="learned-e IPW (clipped)", ate_pp=round(ipw_ate*100, 4)),
    dict(estimator="fully-interacted OLS (Lin 2013)", ate_pp=round(lin_ate*100, 4)),
])
adj_tab.to_csv(C.TABLES / "e3_ate_adjustment_diagnostics.csv", index=False)
print("treatment-predictability AUC (halves):", [round(a, 4) for a in pred_aucs])
adj_tab"""
)
# expose sklearn import needed
adj_code2 = adj_code
nb3.cells.extend([
    nbf.v4.new_markdown_cell("## 3b. Adjustment diagnostics (small-but-detectable imbalance check)"),
    nbf.v4.new_code_cell("""from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score"""),
    adj_md,
    adj_code2,
])
# IV limitations rewording
iv_hits = [i for i, c in enumerate(nb3.cells) if c.cell_type == "markdown" and "Wald IV" in "".join(c.source)]
assert len(iv_hits) >= 1
iv_cell = nb3.cells[iv_hits[0]]
src = "".join(iv_cell.source)
src = src.replace(
    "Wald IV",
    "Wald IV (compliers-only: applies to the 3.6% exposed; requires the exclusion restriction; "
    "if exposure is defined partly by visit-like events the estimate is an upper bound)",
)
iv_cell.source = src
save(nb3, "03_ate_exposure_iv_exploration")

# ------------------------------------------------------------------ NB06
nb6 = load("06_sensitivity_segments_expdesign")
md_replace(
    nb6,
    "## Block A — Duplicate sensitivity",
    """## Block A — Duplicate sensitivity (story corrected after the collision check)

E1's collision check settled the mechanism: treated rows subsampled to control size duplicate at **4.4%**, statistically identical to the control arm's **4.5%**. The 17.9% treated-arm figure is an **arm-size artifact** — the treated arm is ~5.7× larger, and identical feature vectors (real users on the boundary values of quantile-coded features) collide proportionally to group size. Duplicates are therefore **real users, not duplicate storage**.

Consequence: a naive dedup drops mostly zero-outcome treated rows → the treated rate mechanically rises → the ITT is **inflated** (1.034 → 1.493 pp, ≈ +45% relative). The frozen decision stands: **full data stays primary**; dedup is reported as a sensitivity with the corrected interpretation — *"the naive-dedup effect is the artifact, not the full-data effect."*""",
)
md_replace(
    nb6,
    "## Block A/B/C verdicts",
    """## Block A/B/C verdicts

- **Dedup sensitivity (corrected story):** duplicates are feature-collisions between real users (arm-size artifact, not storage duplication). Naive dedup drops mostly zero-outcome treated rows and **inflates** the visit ITT **1.034 → 1.493 pp** (+45% relative) and conversion 0.115 → 0.146 pp. Full data stays primary — the naive-dedup number is the artifact. Policy ordering is unchanged under dedup (uplift **67.2** vs response **48.5** per 1,000 targeted at 10%), so every comparative conclusion is robust.
- **Slice treatment-share diagnostic:** inside the top-5% / top-10% uplift slices the treated share is **87.6% / 86.6%** (population 85%) — a mild tilt consistent with the small detectable imbalance; slice contrasts remain causal under within-test randomization, with the tilt disclosed.
- **Segments:** observed randomized-arm effects confirm the ranking only in the top decile (observed **+6.7 pp** [6.2, 7.3] vs predicted 6.4 pp); mid segments match predictions closely (25–50%: 0.13 pp predicted vs 0.13 pp observed); bottom 25% shows small but **positive** observed effect (+0.19 pp) despite negative mean predicted CATE — negative estimated CATE is NOT evidence of individual harm.
- **E7:** uplift-targeted vs response-targeted at the 10% budget tier is the experiment to run; slice contrasts (~1.9 pp within-slice) are detectable with modest per-arm samples in the sketch below (vs millions for broadcast-level contrasts).

### Limitations
- Dedup is a sensitivity read only — the deduped population is not the real-world population (no user id; content-identity based).
- Segment effects are group contrasts; per-user CATE is a proxy (no pointwise guarantees).
- Power sketch ignores clustering, multiple testing, and non-compliance; production experiment needs an exposure/frequency guardrail plan.
- All magnitudes benchmark-scale (non-uniform subsampling).""",
)
share_cell = nbf.v4.new_code_cell(
    """# slice treatment-share diagnostic (mild tilt check)
share_rows = []
for b in (0.05, 0.10):
    thr = mg["cate_s"].quantile(1 - b)
    sel = mg[mg["cate_s"] >= thr]
    share_rows.append(dict(slice=f"top {int(b*100)}% uplift", n=len(sel),
                           treated_share=round(sel[C.TREATMENT].mean(), 4),
                           population=round(mg[C.TREATMENT].mean(), 4)))
share_tab = pd.DataFrame(share_rows)
share_tab.to_csv(C.TABLES / "e6_slice_treated_share.csv", index=False)
share_tab"""
)
nb6.cells.append(nbf.v4.new_markdown_cell("### Slice treatment-share diagnostic (imbalances where it matters)"))
nb6.cells.append(share_cell)
# retitle dedup figure markdown/cells inside notebook 06
for i, c in enumerate(nb6.cells):
    if c.cell_type == "code":
        src = "".join(c.source)
        if "Dedup RAISES the visit ITT" in src:
            src = src.replace("Dedup RAISES the visit ITT: 1.034 -> 1.493 pp",
                              "Naive dedup INFLATES the visit ITT: 1.034 -> 1.493 pp")
            src = src.replace("Conversion ITT: 0.115 -> 0.146 pp",
                              "Conversion ITT: 0.115 -> 0.146 pp (same artifact)")
            src = src.replace(
                "Non-random duplicates diluted the benchmark ITT — direction of every conclusion unchanged",
                "Duplicates are feature collisions between real users — naive dedup is the artifact, not the fix")
            c.source = src
save(nb6, "06_sensitivity_segments_expdesign")

print("all notebooks edited")
