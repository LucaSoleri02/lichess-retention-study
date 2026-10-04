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
- Response model: fitted on **train-split treated rows only** (scores "response in the ad-enabled environment"); rationale: control rows would contaminate calibration with Y(0) outcomes. Control-only "sure-thing" score = future sensitivity, not in scope.
- Final policy evaluation (**as run**): validation-split selection (~2.1M rows, CIs ~±0.5–0.8 pp on slice effects) + **one-shot 10% budget test confirmation**. Test used once, after all decisions frozen. See "Deviations" below for why this replaced the OOF plan.
- Primary uplift metric: incremental outcomes per 1,000 targeted users at 5/10/20% budgets. Secondary: Qini/AUUC, top-20% capture share.
- Policy budgets frozen: 5%, 10%, 20%.

## 3. Outcomes & estimators (explicit)
- Response model: fitted on **all rows** (treated+control pool) with treatment excluded — scores "likely to convert when marketing is present", the standard practitioner score; control-only "sure-thing" score built as sensitivity (E5c).
- ATE: `mean(Y|T=1) − mean(Y|T=0)` with CLT/Wald CI; randomized design ⇒ unbiased ITT. Both outcomes.
- **Exposure IV (Wald)**: ATE/exposure-rate-among-treated ⇒ effect of exposure on exposed (LATE-style, report honestly as diluted-ATE correction, exposure rate among treated ~3.6%).
- Uplift: S-learner and T-learner (visit primary; conversion secondary only if stable). No advanced learners unless S/T show signal and time allows.
- Policy value at budget k% (same estimator for all policies): select top-k rows by score (ties → row-hash order, NOT file order — the raw file is positionally blocked by component incrementality tests); effectπ(k) = mean(Y|T=1,selected) − mean(Y|T=0,selected); incremental per 1,000 targeted = 1,000 × effectπ(k); bootstrap CI (2,000 resamples, arms resampled independently). Capture share denominator = pooled ITT **of the evaluation split** (computed in-notebook), not a frozen full-data constant.
- Capture share (scale-free): incremental outcomes captured by policy at budget k ÷ total incremental outcomes in evaluation set.
- Conversion-transfer check: visit-trained policy evaluated on conversion.

## 4. Subsampling caveat (Criteo-documented)
Data sub-sampled non-uniformly (true incrementality level unknowable). All "+X%" relative effects and "per 100K" projections = relative/benchmark-scale results, never real campaign numbers. Scale-free shares ("top 20% captures X% of total incremental outcomes") preferred in the deck.

## 5. New-experiment design (deck close)
Current targeting vs uplift targeting, equal budget/reach, primary = incremental outcome per targeted user, secondary = total visits/conversions, guardrails = exposure/frequency/economics when internal data available.

## 6. Notebook map (all fully executed, outputs saved) — as run
1. `01_preprocessing_eda_rules.ipynb` — DQ, balance, duplicate anatomy + collision check, distributions, figures + tables.
2. `02_response_prediction_topk_lift.ipynb` — LR + HistGB, visit+conversion, top-k lift, single-feature AUC context.
3. `03_ate_exposure_iv_exploration.ipynb` — ATE + CIs, fold stability, adjustment diagnostics (predictability AUC, Lin OLS, IPW), exposure Wald IV.
4. `04_uplift_cate_models.ipynb` — S/T-learner CATEs, Qini/AUUC, top-decile observed effects, calibration deciles.
5. `05_policy_value_eval_testset_uplift.ipynb` — policy comparison on validation, one-shot test confirmation, slice-rates export.
6. `06_sensitivity_segments_expdesign.ipynb` — dedup sensitivity (corrected story), uplift segments (E6), E7 experiment design + corrected power sketch.

## 6b. Deviations from the frozen contract (honesty log)
1. **Policy evaluation design.** Frozen contract said 5-fold OOF on all 13.98M rows; as-run uses validation-split evaluation + one-shot 10% test confirmation. Rationale: at the observed effect sizes, 2.1M-row splits give CI half-widths of ~0.5–0.8 pp (tight vs the 1.8–4.4 pp contrasts being compared); the one-shot test confirmation guards split-instability; full OOF re-fitting (5× full model refits) added machine-time without decision-relevant precision. The reviewer-prompted OOF concern (small control counts in tight slices) is addressed by the slice sizes actually used (~31k controls in the 10% slice).
2. **Response-model population.** Frozen contract said "all rows pooled"; as-run trains on train-split treated rows only (documented above) — practitioner score for the ad-enabled environment.
3. **Notebook contents.** The as-run notebook map (§6) replaces earlier planned names (no Airflow/ADF content exists — that line was scaffolding noise, removed).

## 7. results.md per notebook
`Criteo/results/results_01...md` etc., with problems, diagnostics, sensitivity.

## 8. Decision gates
- Gate 1 (data): balance/structure anomalies → fix or carry the caveat before modeling.
- Gate 2 (ATE): tiny/uncertain ATE alone does not kill heterogeneity work.
- Gate 3 (uplift): if uplift ≤ response targeting on held-out eval → report honestly, reframe E7 as "validate uplift targeting".
- Gate 4 (production): only if stability + held-out value + interpretability pass.

## 9. Deck figures (target set)
A balance, B rates, C response top-k lift, D uplift quantiles, E Qini/AUUC, F hero policy comparison (with CIs), G transfer + IV slide, H sensitivity slide (dedup see 03).
