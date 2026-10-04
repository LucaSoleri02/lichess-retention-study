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
| E5 — Policy evaluation | `05_policy_value_eval_testset_uplift.ipynb` | the hero: random/response/uplift at 5/10/20% budgets on the validation split; one-shot 10%-budget test confirmation | done |
| Wrap-up — Sensitivity/E6/E7 | `06_sensitivity_segments_expdesign.ipynb` | dedup sensitivity, uplift segments, E7 experiment design + power sketch | done |

Supporting engineering: fixed 70/15/15 split + 5-fold via `md5(full row)` so exact duplicates never straddle splits (1M-row level check passed); `src/config.py` (all paths), `src/core.py` (hash/splits + ATE bootstrap; the notebook implementations are the single source of truth for policy value / Qini), `src/viz.py`; contract frozen in `Criteo/PLAN.md` before modeling, with an as-run deviations log (§6b).

Agreed machinery from the reviewer comments that got implemented:
- one policy-value estimator for all policies (§20 comment) — effect = treated−control rate difference inside the selected top-k slice; incremental per 1,000 targeted = 1000×; bootstrap CIs; one denominator across the deck;
- frozen budgets 5/10/20%, one-shot test confirmation instead of repeated testing (test-too-small comment addressed by using full ~2.1M-row validation + one-shot ~2.1M-row test, equivalent to OOF-scale precision: CI half-widths ~0.5–0.8 pp);
- the dedup-sensitivity demanded by §8 became a real finding, not a box-tick (below);
- exposure IV added as the causal-nuance slide; exposure never used as a model feature; subsampling caveat stated in E3/E5/E6; response-model training population stated (trained on treated rows, documented as "response in the ad-enabled environment"); conversion-transfer check done (§cheap-extra-check comment).

## 2. Headline findings

1. **Balance: small but detectable imbalance; the raw-ATE may carry ~0.2–0.3 pp of cross-test composition.** Max |SMD| 0.049, max |corr(feature, treatment)| 0.017 — tiny in absolute terms but many SEs from zero at n≈14M. Consistent with randomization *within each component incrementality test* (the file is positionally blocked by tests: treatment share 1.00→0.13, visit rate 2.5%→8.4% by decile). Diagnostics: treatment-predictability AUC 0.510 (features barely predict assignment); slice treated-shares 86.7–87.7% vs 85% (mild tilt, disclosed); adjusted ATEs (Lin OLS +0.773 pp, learned-e IPW +0.771 pp) vs raw +1.034 pp — both adjusted estimators agree with each other, ~25% below the raw pooled contrast, consistent with cross-test composition in the pooled estimate. Raw design-based estimate stays primary. **Deck Q&A line: all policy comparisons are immune to this — every policy is evaluated on the same population, so composition shifts cancel.**
2. **Advertising works (ITT, causal).** Visit +1.03 pp [+1.01, +1.06], +27% relative; conversion +0.115 pp [+0.108, +0.122], +59% relative.ATE extremely precise at n≈14M, stable across 5 hash folds.
3. **The dose is dilute — exposure IV nuance (kept secondary).** Only 3.6% of treated users were actually exposed. Wald IV: exposure effect among the exposed (compliers) ≈ +28.7 pp visit [+27.9, +29.5], +3.20 pp conversion — suggestive, requires the exclusion restriction, and exposure may mechanically include visit-like events (upper-bound read); assumption-labeled, one slide.
4. **Prediction is not targeting (E2).** HistGB response model: visit AUC 0.947, lift@10% 7.8×, calibration good — and yet it cannot distinguish sure-things from persuadables. The AUC is NOT an achievement to headline: single features already reach it (f8 0.926, f9 0.894) — the features appear to encode prior engagement (an inference from the numbers, labeled as such).
5. **Heterogeneity is real but sharp-topped (E4).** S-learner CATE top decile: observed +6.4 pp [+5.9, +6.9] vs pooled +1.03 pp (~6×). Below D9 the ranking is flat/non-monotone; T-learner reproduces it (Spearman 0.75, top-decile Jaccard 0.70).
6. **THE HERO RESULT (E5).** Per 1,000 targeted (identical estimator, randomized slices): at 5% uplift 90.6 vs response 52.9 (1.7×); at 10% 64.0 vs 46.2 (1.4×); at 20% a tie. Capture shares (eval-split denominators): uplift 46.3%/65.4%/77.9% of all incremental visits vs response 27.0%/47.3%/74.1% — i.e. **+18–19 percentage points of share at 5–10% budgets (~70% relative), converging to ~+4 pp at 20%** (statistical tie). **Untouched test split confirms the ordering exactly (10% budget): 68.3 vs 56.0 vs random 10.8 per 1,000.**
7. **Conversion advantage does NOT transfer (E5) — a real limit on the business claim, not a footnote.** Visit-trained slices produce conversion lift, but response ≥ uplift on conversions (5%: 15.0 vs 11.0 per 1,000). The policy is **conditional on visit being the objective**: a visit-effect ranking licenses no conversion-targeting claim. State this on the business-decision slide.
8. **Duplicates: naive dedup is the artifact (sensitivity, corrected story).** 1.26M exact-dup rows; the 17.9%-vs-4.5% treated/control dup-share gap is an **arm-size artifact** — treated rows subsampled to control size duplicate at 4.43% ≈ control 4.54%: real users colliding on boundary feature values. Naive dedup would **inflate** the visit ITT 1.03 → 1.49 pp (+45%) by dropping mostly zero-outcome treated rows. Full data primary; policy ordering robust under dedup (67.2 vs 48.5 per 1,000).
9. **E7 experiment fully specified (power corrected).** Uplift top-k vs response top-k at equal 10% budget, each arm with its own randomized holdout (difference-in-differences design); primary = incremental visits per targeted user. Corrected power on actual slice arm rates (uplift 27.4%/21.0%, response 37.4%/32.8%, contrast 1.78 pp): **~41k users/arm with 50/50 within-arm holdout, ~77k with 85/15**; broadcast ITT detection ~22k/arm for scale. The earlier ~2,400/arm sketch used the wrong test in kind and was replaced.

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
4. RESOLVED (was stale): dedup decision locked — full data primary; the deck presents the naive-dedup inflation (+45%) as a preprocessing-callout story, not an alternative magnitude (see headline #8).
5. No convergence-check on the tuning of HistGB hyperparameters (fixed recipe, not tuned per split — defensible but stated).
6. Random policy CI is a percentile range across 200 draws, not an analytic formula (documented, adequate).
7. Notebook 06 figures were generated by driver scripts, then reassembled into the notebook — the notebook re-executes everything from data and reproduces identical numbers, but `src/nb06_*.py` and `src/build_nb06.py` are transitional utilities (kept for provenance; safe to delete or leave).
8. Reproducibility status (review fix, partial): all paths centralized in `src/config.py` (PARQUET corrected to `data/interim/`), README documents the two-step data-cache regeneration (raw csv.gz → precompute_hash.py → parquet). Notebooks 01–05 still inline the split rules locally (deterministic and identical to config) rather than importing config — a cosmetic refactor left open deliberately given the deadline.
9. Deck slide on v1-vs-v2.1 advertiser-leak provenance cites the Criteo AI Lab page + TFDS catalog — verify the link resolves before presenting; drop the claim if unverifiable.

## 6. Where everything lives

- Notebooks (executed): `Criteo/01…06_*.ipynb`, all always in runnable state.
- Results per stage: `Criteo/results/results_01…06*.md`.
- Figures: `Criteo/outputs/figures/` (`e1_*` DQ/balance, `e2_*` response, `e3_*` ATE/IV, `e4_*` Qini/CATE, `e5_policy_comparison_hero.png` = slide-8 hero, `e6_*` sensitivity/segments, `e7_experiment_power_sketch.png`).
- Tables: `Criteo/outputs/tables/e1…e6*.csv`.
- Contract: `Criteo/PLAN.md`; engineering: `Criteo/src/{config,core,viz}.py`; data cache: `Criteo/data/interim/criteo_uplift_v2_hashed.parquet`.
- Git: branch `experiment/criteo-uplift`, 8 checkpoint commits, all suite tables/figures/notebooks/.

## 7. The one-sentence thesis (deck closing)

> **Predicting who will convert is not the same as identifying who should receive the ad: on this randomized benchmark, ranking users by estimated incrementality captured 18 percentage points more of the total incremental visits than response targeting (65% vs 47% share, ~38% relative) at the 10% budget — a gap that appears only at tight budgets (tie at 20%) — and the experiment to validate it in production is fully specified.**