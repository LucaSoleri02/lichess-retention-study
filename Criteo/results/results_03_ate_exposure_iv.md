# E3 — ATE (ITT) + Exposure IV — results

**Run:** notebook `03_ate_exposure_iv_exploration.ipynb`, git rev `7d58fc9`, 2026-10-03, executed top-to-bottom with 0 errors (~13s notebook wall time).

## Headline ITT effects (full data, n = 13,979,592; 2,096,937 control / 11,882,655 treated)

| outcome | control | treated | ITT (pp) | rel. lift | 95% CI Wald | 95% CI bootstrap |
|---|---|---|---|---|---|---|
| visit | 3.8201% (80,105) | 4.8543% (576,824) | **+1.034** | +27.1% | [+1.006, +1.063] | [+1.0055, +1.0633] |
| conversion | 0.1938% (4,063) | 0.3089% (36,711) | **+0.115** | +59.5% | [+0.108, +0.122] | [+0.1084, +0.1219] |

- Randomization (E1: max |SMD| 0.049) makes these causal ITT (assignment) effects.
- Bootstrap = 5,000 resamples, seed 42, arms resampled independently (implemented as the equivalent vectorized Binomial(n, p̂) draw; identical distribution).
- Wald and bootstrap CIs agree to ~0.0005 pp — asymptotics are excellent at this n; SEs are 0.0146 pp (visit), 0.0034 pp (conversion).

## Fold stability (row_hash % 5)

All 10 fold-level 95% CIs cover the pooled effect. Fold ITT ranges: visit 1.011–1.054 pp, conversion 0.110–0.119 pp. No fold CI excludes the pooled effect → no meaningful heterogeneity.

## Exposure & IV nuance (secondary, suggestive)

- Exposure rate among treated = **3.6037%** (428,212 exposed users); control exposure = **exactly 0** (verified).
- Who gets exposed (associational, treated users only): visit=1 → 30.77% vs visit=0 → 2.22%; conversion=1 → 62.74% vs conversion=0 → 3.42%; f9 positional top decile 14.97% vs bottom decile 1.28%.
- Wald IV (ITT / uptake, delta-method CI) — *effect of exposure among the exposed, assuming exposure follows assignment (monotonicity + no noncompliance-driven confounding); suggestive, secondary:*
  - visit: **+28.70 pp** [27.90, 29.50]
  - conversion: **+3.20 pp** [3.01, 3.38]

## Interpretation

- Assignment to advertising increased visit probability by ~1.03 pp (+27%) and conversion by ~0.12 pp (+59%) — causal, extremely precise.
- The dose is dilute: only 3.6% of treated users were ever exposed, so the IV-scaled "among the exposed" effect (~+28.7 pp visit) is a suggestive upper-frame read conditional on strong assumptions (esp. no noncompliance-driven confounding among treated — unverifiable here). Headline stays ITT.

## DQ (re-echoed in-notebook)

- Treatment share 0.8500 as documented; 0 missing cells; exposure|control exactly 0. PASS.

## Limitations

1. **Benchmark subsampling:** Criteo documented non-uniform subsampling (zero-visit rows downsampled) — absolute rates/effects are benchmark-scale only; true incrementality unknowable. Safe language: relative comparisons and scale-free shares.
2. IV estimates are compliant-local and assumption-dependent; associational exposure patterns (visitors/converters are heavily over-represented among exposed) cannot separate selection from causation — that boundary is exactly what the E7 experiment would test.
3. Conversion is downstream of visit; no multiple-testing concern (two pre-specified effects).

## Artifacts

- Tables: `outputs/tables/e3_ate.csv`, `e3_ate_folds.csv`, `e3_exposure_iv.csv`
- Figures: `outputs/figures/e3_ate_outcomes_by_arm.png` (hero), `e3_ate_forest.png`, `e3_exposure_iv.png`
- Notebook fully executed (23 cells, 0 errors), outputs saved.
