# Criteo Uplift Modeling Dataset — project context

## Why this project (context — Bending Spoons DS final round, due in 2 days)
- Switching from the Lichess retention project (kept in this repo as history).
- Deliverable: PowerPoint presentation of a dataset I analyzed.
- Skeleton: Data Preprocessing & Exploration → Machine Learning → Causal Inference.
- This dataset is ideal for that skeleton because **treatment assignment was randomized** (incrementality tests): the causal step is first-class, not an afterthought.

## Source
- TFDS catalog page: https://www.tensorflow.org/datasets/catalog/criteo
- Criteo AI Lab: https://ailab.criteo.com/criteo-uplift-prediction-dataset/
- Paper: Diemert, Betlei, Renaudin, Amini — "A Large Scale Benchmark for Uplift Modeling", AdKDD workshop @ KDD 2018.
- We use **v2.1 = the unbiased version** (same as TFDS): 13,979,592 rows. The original v1 (25.3M rows) had an advertiser-leak where uplift could be inflated by feature distributions being advertiser-dependent.
- Downloaded from Hugging Face mirror (`criteo/criteo-uplift`) → `criteo-research-uplift-v2.1.csv.gz` (297 MB compressed, 3.25 GB CSV) → cached as `criteo_uplift_v2.parquet`.

## Design (official description)
- Assembled from several **incrementality tests**: a randomized trial procedure where a random part of a population is prevented from being targeted by advertising.
- Unit = user. One row per user.
- Treatment = being targeted by advertising.

## Columns (16)
| Column | Type | Meaning |
|---|---|---|
| f0 … f11 | float32 | 12 anonymized features (dense); original 11 + split in v2 numbering — TFDS lists f0–f11 |
| treatment | int64 | 1 = treated (targeted), 0 = control (held out) |
| conversion | int64 (bool) | label: did a purchase-conversion occur |
| visit | int64 (bool) | label: did a visit occur |
| exposure | int64 (bool) | whether user was effectively exposed (only possible if treated; appendage label) |

## Key figures (verified on full local load)
- Shape: 13,979,592 × 16; **no missing values** anywhere.
- Treatment ratio: **85.0% treated / 15.0% control** (paper's stated .85 ✓).
- Visit rate: **4.70%** overall — control 3.82% vs treated 4.85% → naive +1.03 pp ITE.
- Conversion rate: **0.29%** overall — control 0.194% vs treated 0.309% → naive +1.15 pp relative uplift (+0.115 pp absolute).
- Exposure among treated: 3.6%; exposure among control: exactly 0.
- 1,259,545 exact duplicate rows (9% of data) — user-level rows collapsing; dedup decision needed.

## Feature ranges (full-population, computed locally)
| Feature | min | max | mean | std | #unique | notes |
|---|---|---|---|---|---|---|
| f0 | 12.616 | 26.745 | 19.62 | 5.38 | ~2.18M | bimodal: spike at 12.616, long right tail |
| f1 | 10.060 | 16.344 | 10.07 | 0.105 | 60 | mass at 10.060 (≈50%) — behaves like a weak categorical |
| f2 | 8.214 | 9.052 | 8.45 | 0.299 | ~2.05M | spike at 8.214 (≈50%), correlates −0.51 with f0 |
| f3 | −8.398 | 4.680 | 4.18 | 1.34 | 552 | mass at ceiling 4.680; heavy left tail |
| f4 | 10.281 | 21.124 | 10.34 | 0.343 | 260 | mass at floor 10.281 (≈50%) |
| f5 | −9.012 | 4.115 | 4.03 | 0.431 | 132 | mass at ceiling 4.115 |
| f6 | −31.430 | 0.294 | −4.16 | 4.58 | 1,645 | wide, right-skewed toward 0.294 ceiling; corr +0.55 w/ f3 |
| f7 | 4.834 | 12.00 | 5.10 | 1.205 | ~622k | spike at 4.834 (≈75%), long right tail |
| f8 | 3.635 | 3.972 | 3.93 | 0.057 | 3,743 | narrow; cor r −0.75 w/ f9 |
| f9 | 13.190 | 75.295 | 16.03 | 7.02 | 1,594 | spike at 13.190 (≈85%), very long right tail |
| f10 | 5.300 | 6.474 | 5.33 | 0.168 | ~517k | spike at 5.300 |
| f11 | −1.384 | −0.169 | −0.171 | 0.023 | 136 | near-constant, mass at −0.169 |

Interpretation notes:
- Many features are **censored/interval-coded** (masses at min/max boundaries) — features were quantile-normalized/bucketed upstream; several behave as (weak) categoricals.
- Strong pairwise correlations: f8↔f9 (−0.75), f5↔f7 (−0.75), f4↔f11 (−0.68), f4↔f10 (+0.66).
- Randomization sanity: all |corr(feature, treatment)| < 0.02 → treatment looks well-balanced on observables (good setup for causal claims).

## Signal-vs-treatment correlations (for narrative "features predict visits")
Strongest: f9 (+0.50), f8 (−0.46), f4 (+0.27), f11 (−0.22), f3 (−0.21), f10 (+0.21).

## Files here
- `criteo-research-uplift-v2.1.csv.gz` / `.csv` — raw (csv gitignored)
- `data/interim/criteo_uplift_v2_hashed.parquet` — fast-loading cache + deterministic full-row hash
- `data/interim/e4_val_uplift_scores.parquet`, `e2_best_visit_model.joblib` — model artifacts
- `src/` — config paths, estimators (`core.py`), plotting style; `precompute_hash.py` rebuilds the cache
- (analysis scripts + outputs/ to follow)

## Regenerating the data cache (two steps, any machine)
1. Obtain `criteo-research-uplift-v2.1.csv.gz` (Criteo AI Lab / HF mirror `criteo/criteo-uplift`) into this folder.
2. `python src/precompute_hash.py` → writes `data/interim/criteo_uplift_v2_hashed.parquet` (adds the deterministic full-row hash used by every split/fold in the analysis).
