# Criteo Uplift Case — Analysis Contract

Interview project, Bending Spoons DS final round. Skeleton: Preprocessing/EDA → ML → Causal Inference → Targeting Policy → Next Experiment.
Deliverable: notebooks (fully run) + figures/tables in `Criteo/outputs/` + per-section `results.md`.

## 1. Dataset
- `criteo-research-uplift-v2.1.csv.gz` (Hugging Face mirror `criteo/criteo-uplift`), 13,979,592 rows × 16 cols, no missing values. Cached `criteo_uplift_v2.parquet`.
- 12 anonymized pre-treatment features f0–f11; treatment (85/15 randomized); outcomes visit (4.70%), conversion (0.29%); exposure (post-treatment, treated-only).
- Unit = user-row (no user id). Duplicates: 1,259,545 exact rows (9%): keep primary, run dedup sensitivity.

## 2. Frozen contract (locked before modeling)
- Dataset version: v2.1 (13.98M rows). Snapshot fixed on disk; no re-download.
- Population: all rows (full-data primary; dedup version sensitivity only).
- Feature set: f0–f11 only. Never `treatment`, never `exposure` (post-treatment).
- Treatment definition: randomized assignment `treatment`. Causal treatment ≠ exposure.
- Outcomes: primary = `visit`; secondary = `conversion` (sparse → careful).
- Splits: deterministic row-hash: `md5(full row tuple) % 1000` → [0,700) train / [700,850) validation / [850,1000) test (~70/15/15). Full-row hash so exact duplicates share a split (no train/test leakage through dups).
- Final policy evaluation: **5-fold out-of-fold predictions on all 13.98M rows** (fold = `row_hash % 5`, folds independent of tr/val/test usage at prediction time). Test set kept as untouched sanity check.
- Primary uplift metric: incremental outcomes per 1,000 targeted users at 5/10/20% budgets. Secondary: Qini/AUUC, top-20% capture share.
- Policy budgets frozen: 5%, 10%, 20%.

## 3. Outcomes & estimators (explicit)
- Response model: fitted on **all rows** (treated+control pool) with treatment excluded — scores "likely to convert when marketing is present", the standard practitioner score; control-only "sure-thing" score built as sensitivity (E5c).
- ATE: `mean(Y|T=1) − mean(Y|T=0)` with CLT/Wald CI; randomized design ⇒ unbiased ITT. Both outcomes.
- **Exposure IV (Wald)**: ATE/exposure-rate-among-treated ⇒ effect of exposure on exposed (LATE-style, report honestly as diluted-ATE correction, exposure rate among treated ~3.6%).
- Uplift: S-learner and T-learner (visit primary; conversion secondary only if stable). No advanced learners unless S/T show signal and time allows.
- Policy value at budget k% (same estimator for all policies, OOF set): select top-k rows by score (ties → row-hash order); effectπ(k) = mean(Y|T=1,selected) − mean(Y|T=0,selected); incremental per 1,000 targeted = 1,000 × effectπ(k); bootstrap CI (1,000 resamples over selected rows within each arm). Same estimator for random/response/uplift.
- Capture share (scale-free): incremental outcomes captured by policy at budget k ÷ total incremental outcomes in evaluation set.
- Conversion-transfer check: visit-trained policy evaluated on conversion.

## 4. Subsampling caveat (Criteo-documented)
Data sub-sampled non-uniformly (true incrementality level unknowable). All "+X%" relative effects and "per 100K" projections = relative/benchmark-scale results, never real campaign numbers. Scale-free shares ("top 20% captures X% of total incremental outcomes") preferred in the deck.

## 5. New-experiment design (deck close)
Current targeting vs uplift targeting, equal budget/reach, primary = incremental outcome per targeted user, secondary = total visits/conversions, guardrails = exposure/frequency/economics when internal data available.

## 6. Notebook map (all fully executed, outputs saved)
1. `01_preprocessing_eda_rules.ipynb` — DQ, balance, duplicates, distributions, figures A/B + tables.
2. `02_response_prediction_topk_lift.ipynb` — LR + HistGB, visit+conversion, top-k lift.
3. `03_ate_exposure_iv_exploration.ipynb` — ATE, CIs, IV/one-slide exposure analysis, dup-sensitivity (E1).
4. `04_uplift_CATE_quantiles.ipynb` — S/T-learner CATEs, segments, uplift quantiles table (E2, E4).
5. `05_policy_value_eval_testset_uplift.ipynb` — validation-set S/T-learner comparison, final policy comparison on OOF full data (E5).
6. `06_ab_design_impact_airflow.ipynb` — experiment design, business impact, ADF EDA, Airflow DAG write (E6–E7).
Notebooks numbered as: E0 gates in 01; E1 in 03; E2 in 02; E3 in 03; E4 in 04; E5 in 05; E6/E7 in 06.

## 7. results.md per notebook
`Criteo/results/results_01...md` etc., with problems, diagnostics, sensitivity.

## 8. Decision gates
- Gate 1 (data): balance/structure anomalies → fix or带上 caveat before modeling.
- Gate 2 (ATE): tiny/uncertain ATE alone does not kill heterogeneity work.
- Gate 3 (uplift): if uplift ≤ response targeting on held-out eval → report honestly, reframe E7 as "validate uplift targeting".
- Gate 4 (production): only if stability + held-out value + interpretability pass.

## 9. Deck figures (target set)
A balance, B rates, C response top-k lift, D uplift quantiles, E Qini/AUUC, F hero policy comparison (with CIs), G transfer + IV slide, H sensitivity slide (dedup see 03).
