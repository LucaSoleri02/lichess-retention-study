# COMPREHENSIVE RESULTS — Criteo Uplift Modeling Case Study

**Project:** From Conversion Prediction to Incremental Advertising Impact — Bending Spoons DS final round.
**Status at time of writing:** all six notebooks executed top-to-bottom, 0 errors, outputs saved; every analytical stage has its own commit.
**Data:** Criteo Uplift v2.1 (unbiased benchmark, Diemert et al. AdKDD/KDD 2018), 13,979,592 rows × 16 fields + deterministic full-row hash. Treatment randomized (85% treated). Outcomes: visit (4.70%), conversion (0.29%), exposure (3.6% of treated).

---

## 1. What was built (pipeline overview)

| Stage | Notebook | What it does | Status |
|---|---|---|---|
| E1 — Preprocessing/EDA/DQ | `01_preprocessing_eda_rules.ipynb` | schema, missingness, treatment ratio, duplicates anatomy, feature distributions, SMD balance, correlations, impossible-value scan, 11 DQ checks | 11/11 PASS |
| E2 — Response prediction | `02_response_prediction_topk_lift.ipynb` | P(Y=1\|X) baseline, LR vs HistGB, both outcomes, top-k lift | done, ignored test split |
| E3 — ATE + exposure IV | `03_ate_exposure_iv_exploration.ipynb` | ITT effects + CIs, fold stability, exposure Wald IV | done |
| E4 — CATE models | `04_uplift_cate_models.ipynb` | S-learner vs T-learner, Qini/AUUC, top-decile observed effects | done |
| E5 — Policy evaluation | `05_policy_value_eval_testset_uplift.ipynb` | the hero: random/response/uplift at 5/10/20% budgets; test-split confirmation | done |
| Wrap-up — Sensitivity/E6/E7 | `06_sensitivity_segments_expdesign.ipynb` | dedup sensitivity, uplift segments, E7 experiment design + power sketch | done |

Supporting engineering: fixed 70/15/15 split + 5-fold via `md5(full row)` so exact duplicates never straddle splits (1M-row level check passed); `src/config.py`, `src/core.py` (ATE/bootstrap/policy-value estimators), `src/viz.py`; decision contract frozen in `Criteo/PLAN.md` before modeling.

Agreed machinery from the reviewer comments that got implemented:
- one policy-value estimator for all policies (§20 comment) — effect = treated−control rate difference inside the selected top-k slice; incremental per 1,000 targeted = 1000×; bootstrap CIs; one denominator across the deck;
- frozen budgets 5/10/20%, one-shot test confirmation instead of repeated testing (test-too-small comment addressed by using full ~2.1M-row validation + one-shot ~2.1M-row test, equivalent to OOF-scale precision: CI half-widths ~0.5–0.8 pp);
- the dedup-sensitivity demanded by §8 became a real finding, not a box-tick (below);
- exposure IV added as the causal-nuance slide; exposure never used as a model feature; subsampling caveat stated in E3/E5/E6; response-model training population stated (trained on treated rows, documented as "response in the ad-enabled environment"); conversion-transfer check done (§cheap-extra-check comment).

## 2. Headline findings

1. **Randomization holds.** Max |SMD| 0.049 across 12 features, max |corr(feature, treatment)| 0.017. Consistent with the documented incrementality-test design; safe causal contrasts.
2. **Advertising works (ITT, causal).** Visit +1.03 pp [+1.01, +1.06], +27% relative; conversion +0.115 pp [+0.108, +0.122], +59% relative.CTA extremely precise at n≈14M, stable across 5 hash folds.
3. **The dose is dilute — exposure IV nuance.** Only 3.6% of treated users were actually exposed. Wald IV: exposure effect among the exposed ≈ +28.7 pp visit [+27.9, +29.5], +3.20 pp conversion — suggestive, assumption-labeled, kept secondary.
4. **Prediction is not targeting (E2).** HistGB response model: visit AUC 0.947, lift@10% 7.8×, calibration near-perfect — and yet it cannot distinguish sure-things from persuadables.
5. **Heterogeneity is real but sharp-topped (E4).** S-learner CATE top decile: observed +6.4 pp [+5.9, +6.9] vs pooled +1.03 pp (~6×). Below D9 the ranking is flat/non-monotone; T-learner reproduces it (Spearman 0.75, top-decile Jaccard 0.70).
6. **THE HERO RESULT (E5).** Per 1,000 targeted (identical estimator, randomized slices): at 5% uplift 90.6 vs response 52.9 (1.7×); at 10% 64.0 vs 46.2 (1.4×); at 20% a tie. Capture shares: uplift 43.8%/61.9%/73.7% of all incremental visits vs response 25.6%/44.7%/70.1%. **Untouched test split confirms the ordering exactly (10% budget): 68.3 vs 56.0 vs random 10.8 per 1,000.**
7. **Conversion advantage does NOT transfer (E5).** Visit-trained slices produce conversion lift, but response ≥ uplift on conversions (5%: 15.0 vs 11.0). A visit-effect ranking licenses no conversion-targeting claim — the honest piece of the story.
8. **Duplicates materially dilute the benchmark (sensitivity).** E1 found 1.26M exact-dup rows, non-random (17.9% of treated vs 4.5% of control rows involved; ~0% of visitors). Dedup moves ITT visit 1.03 → 1.49 pp and policy ordering still holds (67.2 vs 48.5 per 1,000). Conclusions robust; magnitudes benchmark-scale (subsampling caveat).
9. **E7 experiment fully specified.** Uplift top-k vs response top-k at equal 10% budget; primary = incremental visits per 1,000 targeted; guardrails exposure/frequency; slice contrast ~1.9 pp detectable with ~2,400 users/arm (illustrative sketch) vs millions for broadcast effects.

## 3. What was improved along the way (iterations & fixes)

- **Hash/split design:** naive row hashing was slow/inconsistent → precomputed `row_hash` into the parquet; full-row hashing guarantees exact duplicates always share split/fold (leakage closed; verified 0 inconsistent groups).
- **`ate_bootstrap` rewritten** from a row-resampling loop (would hang at n≈12M) to the distribution-identical vectorized Binomial draw; CI agreement with E3 verified.
- **Reviewer comment on pipeline mechanics** — test-set OOF/global confirmations were folded into single-shot test usage; the two-nested-loop duplicate-merge bug in a first E5 draft was caught (cross-check that the artifact row counts matched before use).
- Refit-fidelity gates: E5 response refit reproduced E2 AUC 0.9466; S-learner refit reproduced E4 CATE ranking (ρ≈1.0) before test-split scoring.
- Figures iterated to presentation grade (hero policy chart with CI error bars + broadcast reference line + "benchmark scale" caveat in subtitle).

## 4. Story spine for the deck (10–15 min)

Financial budget → predict-responders ≠ persuadables (E2/E2b) → randomized experiment (E1/E3) → effect is diluted (exposure IV) → heterogeneity exists but only in the top slice (E4) → at equal budget, uplift targeting beats response (E5 hero) → conversion nuance (advantage doesn't transfer; visit is the reliable outcome) → E7 experiment spec → limitations + "with internal economics I'd optimize against contribution" closing.

## 5. Final gaps / open items (honest)

1. **Deck not assembled yet** (PowerPoint is the deliverable; figures + numbers are ready, deck itself is the remaining work).
2. T-learner/X-learner/DR-learner not benchmarked beyond S vs T (deliberate scope control; nobody asked for a leaderboard).
3. `exposure` analysis kept minimal (rate, IV, association with outcome); no per-user exposure modeling (post-treatment rule upheld).
4. Dedup change (1.03 → 1.49 pp) documented, but the "which magnitudes go on slides" decision is still open — recommendation: present full-data primary with the dedup delta as a callout.
5. No convergence-check on the tuning of HistGB hyperparameters (fixed recipe, not tuned per split — defensible but stated).
6. Random policy CI is a percentile range across 200 draws, not a analytic formula (documented, adequate).
7. Notebook 06 figures were generated by driver scripts, then reassembled into the notebook — the notebook re-executes everything from data and reproduces identical numbers, but `src/nb06_*.py` and `src/build_nb06.py` are transitional utilities (kept for provenance; safe to delete or leave).
8. Deck slide on v1-vs-v2.1 advertiser-leak provenance cites the Criteo AI Lab page + TFDS page only — verify on the le sustained link (dropped if unverifiable).

## 6. Where everything lives

- Notebooks (executed): `Criteo/01…06_*.ipynb`, all always in runnable state.
- Results per stage: `Criteo/results/results_01…06*.md`.
- Figures: `Criteo/outputs/figures/` (`e1_*` DQ/balance, `e2_*` response, `e3_*` ATE/IV, `e4_*` Qini/CATE, `e5_policy_comparison_hero.png` = slide-8 hero, `e6_*` sensitivity/segments, `e7_experiment_power_sketch.png`).
- Tables: `Criteo/outputs/tables/e1…e6*.csv`.
- Contract: `Criteo/PLAN.md`; engineering: `Criteo/src/{config,core,viz}.py`; data cache: `Criteo/data/interim/criteo_uplift_v2_hashed.parquet`.
- Git: branch `experiment/criteo-uplift`, 8 checkpoint commits, all suite tables/figures/notebooks/.

## 7. The one-sentence thesis (deck closing)

> **Predicting who will convert is not the same as identifying who should receive the ad: on this randomized benchmark, ranking users by estimated incrementality captured ~18% more of the total incremental visits than response targeting at the same budget — and the experiment to validate it in production is fully specified.**
