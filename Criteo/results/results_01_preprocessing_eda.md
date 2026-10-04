# Results — E1: Preprocessing, quality control & EDA (Criteo uplift v2, hashed parquet)

**Notebook:** `Criteo/01_preprocessing_eda_rules.ipynb` (executed top-to-bottom, no errors; execution counts 1–14)
**Data:** `criteo_uplift_v2_hashed.parquet` — 13,979,592 rows × 17 cols
**Language discipline:** treatment was randomized → treated-vs-control contrasts are causal (ITT); all feature/outcome/duplicate comparisons are associations only.

## Headline findings

- **Randomization & outcome rates (causal, ITT):** treated share **0.850000** (11,882,655 treated vs 2,096,937 control; expected 0.850±0.001). Visit: control **3.8201%** → treated **4.8543%** (**+1.034 pp**, +27.1% relative). Conversion: control **0.1938%** → treated **0.3089%** (**+0.115 pp**, +59.5% relative). Matches published v2.1 rates (control 0.194% / treated 0.309%).
- **Covariate balance: small but detectable imbalance, consistent with the design (full 13,979,592 rows):** max |SMD| = **0.0488 (f3)**, all 12 features < 0.1; max |corr(feature, treatment)| = **0.01744 (f3)**. At n≈14M these are many SEs from zero — the correct wording is *small but detectable imbalance*, consistent with randomization within each component incrementality test (the file is positionally blocked by tests: treatment share by positional decile runs 1.00 → 0.13). Adjustment diagnostics in E3 quantify the impact on the ITT (raw +1.034 pp vs adjusted +0.77 pp).
- **Duplicates are feature collisions between real users, NOT storage artifacts (story corrected by the collision check below):** 1,259,545 exact-repeated rows; dup-involved share control **4.54%** vs treated **17.89%** — but treated rows **subsampled to control size** duplicate at **4.43%**, statistically identical to control. The treated arm is ~5.7× larger, and identical feature vectors (users on boundary values of quantile-coded features) collide proportionally to group size. Visitors ~0.006% dup rate simply because visitors sit off the boundary spikes. Naive dedup would drop mostly zero-outcome treated rows and *inflate* the ITT (quantified in notebook 06: 1.034 → 1.493 pp); **full data stays primary**.
- **Features f0–f11 are quantile-coded upstream:** heavy boundary masses at exact min/max — e.g. f1 has **98.8%** of rows at its min, f11 98.6% at its max, f4 95.7% at min, f5 94.7% at max. Multiple features have a single spike plus a long sparse tail; most are nearly bimodal (spike at one endpoint, mass near the other). Consequence: expect weak linear signal from raw features; trees/binning or rank-based handling preferable in E2.
- **Feature redundancy is real but bounded:** max pairwise |r| = **0.750**; 7 of 66 pairs exceed |r| = 0.5. Correlated clusters exist, so a regularized/monotone model or feature screening is prudent, but no pair is a pure duplicate.
- **No data corruption found:** zero missing cells, zero infinities, zero out-of-range values, all bin columns strictly {0,1}, dtypes exactly as documented (float64 features, int64 flags, int64 row_hash).

## Problems found

- No FAILs, no WARNs: **11/11 DQ checks PASS** (`outputs/tables/e1_data_quality.csv`).
- Two *characterization flags* (not corruption): (1) duplicates = arm-size-driven feature collisions between real users (collision check: `e1_duplicate_collision_check.csv`); (2) boundary masses confirm quantile coding. Both change modeling choices, not data validity.
- Positional blocking discovered: the raw file stacks component incrementality tests (treatment share 1.00 → 0.13, visit rate 2.5% → 8.4% by positional decile). All splits are hash-based and immune; flagged for the E3 adjustment diagnostics.

## Diagnostics performed

- Shape/dtype audit vs expected (13,979,592 × 17, exact dtypes). Missingness per column (all 0).
- Treatment ratio check on full data; per-arm outcome rates with event counts.
- Duplicate analysis on all 16 content columns (`row_hash` excluded): group counts, multiplicity distribution (max group size, ~2–3 typical), dup-rate by treatment arm and by visit outcome vs overall share.
- Feature distributions (12-panel histogram, deterministic 2M-row sample, seed 42); boundary-mass shares on **full data**.
- Covariate balance: SMD + Pearson corr(feature, treatment) computed vectorized on the full dataset; SMD forest plot.
- Feature correlation heatmap and strongest-pair scan.
- Impossible-value scan: infs, min/max violations, non-{0,1} flags — all 0.

## Sensitivity items pending (deferred, not forgotten)

- **Dedup sensitivity:** run in notebook 06 with the corrected interpretation — naive dedup *inflates* the ITT (1.034 → 1.493 pp) because dedup removes mostly zero-outcome treated rows; full data stays primary.
- Multiplicity weighting (1 row vs k−1 redundant copies) as an alternative dedup variant.
- Boundary-mass / quantile-coding handling in E2: rank-transform vs raw vs tree models.
- Exposure column is fully characterized (94.7% of rows at max on f5 relates to exposure patterns) but not yet used as an analytic stratum — exposure-level effects (visit without exposure etc.) deferred to E2/E3.

## Limitations

- Randomized assignment licenses only the **unconditional ITT** claims above; any feature-outcome statements remain associations.
- Exact-duplicate definition ignores near-duplicates; row_hash confirms content hashing, so exact matching suffices here.
- Histograms use a 2M-row deterministic sample (full-data boundary/balance tables are exact); correlation heatmap computed on the same 2M sample.
- 15.9% duplicate involvement means effective sample is smaller than nominal; CIs later should use design-aware or dedup-sensitivity checks.
