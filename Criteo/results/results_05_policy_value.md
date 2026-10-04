# E5 — Policy value: uplift vs response vs random — results

**Notebook:** `Criteo/05_policy_value_eval_testset_uplift.ipynb` (17 code cells, executed top-to-bottom, 0 errors).
**Estimator (frozen, identical for all policies):** select top-k rows by score within the evaluation split; `effect(k) = mean(Y|T=1, sel) − mean(Y|T=0, sel)`; **incremental per 1,000 targeted = 1,000 × effect(k)**; 95% CI = 2,000-resample bootstrap (independent arm resampling, seed 42); capture share = effect×n_sel / (pooled ITT×n_eval). Random policy = mean over 200 seed-42 draws.

## Headline — validation split (n = 2,096,296; visit outcome)

| budget | Random | Response | Uplift (S-CATE) |
|---|---|---|---|
| 5% | 9.7 [6.3, 12.9] | 52.9 [43.9, 61.7] | **90.6 [82.5, 98.8]** |
| 10% | 9.6 [7.5, 11.8] | 46.2 [40.1, 52.3] | **64.0 [58.6, 69.3]** |
| 20% | 9.7 [8.4, 11.0] | 36.2 [32.7, 39.7] | 38.1 [34.9, 41.3] |

(incremental visits per 1,000 targeted, 95% CI)

- **5%: uplift = 1.7× response**, CIs disjoint. **10%: 1.4×**, CIs disjoint. **20%: statistical tie** (gap collapses as response's high-score mass overlaps the persuadable slice).
- Capture shares (scale-free, eval-split denominators): uplift 46.3% / 65.4% / 77.9% of all incremental visits vs response 27.0% / 47.3% / 74.1%; random ≈ budget share always.
- **Test-split one-shot confirmation (10%):** ordering reproduced exactly — Uplift **68.3** [63.4, 73.6] vs Response **56.0** [49.8, 62.1] vs Random 10.8 [8.8, 12.9]; uplift's CI excludes response's. Validation result is not a split artifact.

## Conversion transfer (same slices, visit-trained policies)

- All three visit-trained slices DO produce detectable conversion lift (all Wald CIs exclude 0).
- But the uplift **advantage does not transfer**: response ≥ uplift on conversions at every budget (5%: response 15.0 [12.0, 17.9] vs uplift 11.0 [8.4, 13.6] per 1,000, CIs disjoint; 10% and 20%: statistically tied).
- Interpretation (exploratory): persuadable-visitor ≠ persuadable-converter. A visit-effect ranking licenses no conversion-targeting claim. E7 should be powered on visits, not conversion transfer.

## Subsampling caveat

Criteo rows are non-uniformly subsampled (zero-visit rows downsampled): absolute pp / per-1,000 numbers are benchmark-scale, not live-campaign projections. Safe reads: uplift:response ratios (1.7× / 1.4× / ~1.05×) and capture percentages.

## Problems / diagnostics

- E2 saved a fitted model object (`data/interim/e2_best_visit_model.joblib`); E4 saved no model object, so the test-split CATE required a faithful S-learner refit. Refit validation AUC reproduced E2's 0.9466 and refit-vs-saved CATE rank correlation ≈ 1.0 (both verified in-notebook).
- row_hash is not unique within split (~1.9k rows); E4 scores joined **by row position** with length/sequence validation.
- **Tie-breaking fixed (review):** top-k selection now breaks ties by `row_hash` (contract) instead of file order — the raw file is positionally blocked by component incrementality tests, so file-order ties could correlate with arm.
- **Capture-share denominators fixed (review):** computed from the evaluation split's own pooled ITT (validation 1.036 pp / test 1.081 pp), not frozen full-data constants. New capture shares: uplift 46.3% / 65.4% / 77.9% vs response 27.0% / 47.3% / 74.1% at 5/10/20%.
- Random policy CI is a percentile range across 200 draws (selection randomness dominates).

## Limitations

- Slice-level causal contrasts only; CATE remains a per-user proxy.
- Conversion transfer under-powered at small slices (valid finding, reported as such).
- Test split opened once for the frozen best configuration only — reproducibility check, not re-selection.

## Artifacts

- Figures: `outputs/figures/e5_policy_comparison_hero.png`, `e5_policy_conversion_transfer.png`, `e5_policy_capture_share.png`
- Tables: `outputs/tables/e5_policy_value_visit.csv`, `e5_policy_value_conversion.csv`, `e5_policy_test_confirmation.csv`
