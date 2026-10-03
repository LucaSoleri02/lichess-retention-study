# E2 — Response prediction (top-k lift): results

**Notebook:** `Criteo/02_response_prediction_topk_lift.ipynb` (executed top-to-bottom, no errors, ~8 min).
**Question:** who is likely to respond — P(Y=1|X)? The deliberately "wrong-but-useful" practitioner-default targeting rule, later contrasted with uplift (E3).
**Fitting:** train-split treated rows only. LR on a 2M-row deterministic subsample (seed 42, documented); HistGB on the full 8,322,746 treated train rows, no subsampling. All metrics on the 2,096,296-row validation split (treated + control; control never used for fitting). Test split (2,093,909 rows) never scored, counts only.

## Headline numbers (validation)

| model | outcome | ROC-AUC | log loss | precision@10% | lift@10% | Brier |
|---|---|---|---|---|---|---|
| LogisticRegression | visit | 0.9310 | 0.1120 | 0.3554 | 7.55x | 0.0315 |
| **HistGB** | **visit** | **0.9466** | **0.1031** | **0.3678** | **7.81x** | **0.0298** |
| LogisticRegression | conversion | 0.9518 | 0.0124 | 0.0255 | 8.84x | 0.0026 |
| HistGB | conversion | 0.9606 | 0.0116 | 0.0258 | 8.94x | 0.0025 |

## Diagnostics & observations

- **HistGB beats LR on every metric for both outcomes** → selected as the best visit model (hyperparameters + metrics saved to `data/interim/e2_best_visit_model.joblib`; early stopping never triggered for `visit` — ran all 300 iters; stopped at 120 for `conversion`).
- **Decile lift is extremely top-heavy:** observed visit rate 36.8% in the top decile (7.81x base) and 6.8% in D9 (1.44x), but D8 is 1.9% (0.39x) and everything below is far under base. sdResponse is concentrated in ~the top 20% of the score; mid/lower deciles are near-dead. Practical implication of the response-scoring rule: only the top ~2 deciles are worth acting on at all — and even that mixes sure-things with persuadables.
- Calibration of the HistGB visit model on validation is excellent (10 quantile bins sit on the diagonal, 0–0.37 range). Top bin ~0.37 predicted vs ~0.37 observed.
- Permutation importance (neg log loss, 500k validation rows, 5 repeats): dominated by **f8** (0.0744) and **f2** (0.0290); f9, f6, f0 minor; f1, f5, f7, f10 ~zero. Descriptive only — features are anonymized, no meaning invented.
- Validation conversion base rate 0.289% vs headline 0.29% — consistent with E1 snapshot.

## Problems / limitations

- No treatment/exposure/outcome columns were used as features (verified by construction); nonetheless the scores are **predictive associations, not causal** — top-k targeting on P(Y|X) cannot distinguish users who would respond anyway (sure things) from those the ad moves (persuadables). D10 contains both.
- Models are calibrated to the treated environment (trained on treated rows only); applying to the general population subtly assumes ranking stability across arms — untestable here, addressed in E3.
- LR used a 2M subsample (tractability); its gap to HistGB (~0.016 AUC) partly reflects that.
- Test split untouched; final held-out numbers come later.

## Artifacts

- Figures: `outputs/figures/e2_response_roc_calibration.png`, `e2_response_decile_lift.png`
- Tables: `outputs/tables/e2_response_metrics.csv`, `e2_response_lift_deciles.csv`, `e2_feature_importance.csv`
- Model: `data/interim/e2_best_visit_model.joblib` (HistGB visit, full hyperparams + validation metrics)

**Set-up for E3:** predicting conversion ≠ knowing who to target. The relevant quantity is the difference of potential outcomes; sure things must be separated from persuadables before any top-k rule is decided.
