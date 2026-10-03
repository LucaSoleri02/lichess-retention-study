# Results — E1: Preprocessing, quality control & EDA (Criteo uplift v2, hashed parquet)

**Notebook:** `Criteo/01_preprocessing_eda_rules.ipynb` (executed top-to-bottom, no errors; execution counts 1–14)
**Data:** `criteo_uplift_v2_hashed.parquet` — 13,979,592 rows × 17 cols
**Language discipline:** treatment was randomized → treated-vs-control contrasts are causal (ITT); all feature/outcome/duplicate comparisons are associations only.

## Headline findings

- **Randomization & outcome rates (causal, ITT):** treated share **0.850000** (11,882,655 treated vs 2,096,937 control; expected 0.850±0.001). Visit: control **3.8201%** → treated **4.8543%** (**+1.034 pp**, +27.1% relative). Conversion: control **0.1938%** → treated **0.3089%** (**+0.115 pp**, +59.5% relative). Matches published v2.1 rates (control 0.194% / treated 0.309%).
- **Covariate balance is excellent (full 13,979,592 rows, no sampling):** max |SMD| = **0.0488 (f3)**, all 12 features < 0.1; max |corr(feature, treatment)| = **0.01744 (f3)**. Randomization verified — safe for unadjusted causal contrasts, and any treated-vs-control feature shift cannot explain the outcome gap.
- **Duplicates are massive and structurally non-random:** 2,221,150 rows involved (~15.9%) in 961,605 exact-duplicate groups = 1,259,545 redundant copies (matches known facts). Dup rate differs sharply by arm — control **4.54%** vs treated **17.89%** — and collapses to near zero among visitors (**0.0064% vs 16.67%** among non-visitors). Duplication is entangled with both treatment and the outcome; a dedup-sensitivity experiment must test whether this inflates ITT effects (decision frozen for now: **keep all rows**).
- **Features f0–f11 are quantile-coded upstream:** heavy boundary masses at exact min/max — e.g. f1 has **98.8%** of rows at its min, f11 98.6% at its max, f4 95.7% at min, f5 94.7% at max. Multiple features have a single spike plus a long sparse tail; most are nearly bimodal (spike at one endpoint, mass near the other). Consequence: expect weak linear signal from raw features; trees/binning or rank-based handling preferable in E2.
- **Feature redundancy is real but bounded:** max pairwise |r| = **0.750**; 7 of 66 pairs exceed |r| = 0.5. Correlated clusters exist, so a regularized/monotone model or feature screening is prudent, but no pair is a pure duplicate.
- **No data corruption found:** zero missing cells, zero infinities, zero out-of-range values, all bin columns strictly {0,1}, dtypes exactly as documented (float64 features, int64 flags, int64 row_hash).

## Problems found

- No FAILs, no WARNs: **11/11 DQ checks PASS** (`outputs/tables/e1_data_quality.csv`).
- Two *characterization flags* (not corruption): (1) duplicate creation is strongly non-random across arms/outcomes; (2) boundary masses confirm quantile coding — effectively compressing all feature variance into ranks plus endpoint masses. Both change modeling choices, not data validity.

## Diagnostics performed

- Shape/dtype audit vs expected (13,979,592 × 17, exact dtypes). Missingness per column (all 0).
- Treatment ratio check on full data; per-arm outcome rates with event counts.
- Duplicate analysis on all 16 content columns (`row_hash` excluded): group counts, multiplicity distribution (max group size, ~2–3 typical), dup-rate by treatment arm and by visit outcome vs overall share.
- Feature distributions (12-panel histogram, deterministic 2M-row sample, seed 42); boundary-mass shares on **full data**.
- Covariate balance: SMD + Pearson corr(feature, treatment) computed vectorized on the full dataset; SMD forest plot.
- Feature correlation heatmap and strongest-pair scan.
- Impossible-value scan: infs, min/max violations, non-{0,1} flags — all 0.

## Sensitivity items pending (deferred, not forgotten)

- **Dedup sensitivity:** rerun ITT rates (and later uplift models) dropping duplicate rows to test whether the non-random duplication inflates or deflates the ITT gap (E-later experiment; effect could be material given dup-rate 4.5% vs 17.9% by arm).
- Multiplicity weighting (1 row vs k−1 redundant copies) as an alternative dedup variant.
- Boundary-mass / quantile-coding handling in E2: rank-transform vs raw vs tree models.
- Exposure column is fully characterized (94.7% of rows at max on f5 relates to exposure patterns) but not yet used as an analytic stratum — exposure-level effects (visit without exposure etc.) deferred to E2/E3.

## Limitations

- Randomized assignment licenses only the **unconditional ITT** claims above; any feature-outcome statements remain associations.
- Exact-duplicate definition ignores near-duplicates; row_hash confirms content hashing, so exact matching suffices here.
- Histograms use a 2M-row deterministic sample (full-data boundary/balance tables are exact); correlation heatmap computed on the same 2M sample.
- 15.9% duplicate involvement means effective sample is smaller than nominal; CIs later should use design-aware or dedup-sensitivity checks.
