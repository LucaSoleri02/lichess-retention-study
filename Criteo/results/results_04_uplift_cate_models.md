# E4 — CATE (uplift) models: results

**Run:** notebook `Criteo/04_uplift_cate_models.ipynb`, git rev `230e821`, 2026-10-03, executed top-to-bottom with 0 errors (~7 min wall, 4 cores / 24GB, single process). Metric library: `scikit-uplift` 0.5.1 (pip-installed into the venv; import verified; common-sense checkpoint: all-zero scores → exactly 0.0 coefficient, informed ranking > random on synthetic heterogeneous data).

## Headline (validation n = 2,096,296; visit outcome)

| | S-learner | T-learner |
|---|---|---|
| Qini coefficient (sklift, normalized) | **0.08496** | 0.08269 |
| AUUC (sklift, normalized) | **0.03342** | 0.03252 |
| Top-decile observed effect (pp, treated − control rate inside top 10% CATE) | **+6.399** | +5.796 |
| Top-decile 95% bootstrap CI (1,000 resamples, seed 42) | [+5.905, +6.886] | [+5.281, +6.337] |
| Spearman CATE S-vs-T (1M-row subsample, seed 42) | — | 0.7473 (shared) |
| Top-decile overlap | — | 0.702 Jaccard (172,856 of 209,631 rows) |

Pooled ITT visit effect (E3): **+1.034pp** [+1.006, +1.063]. Both learners' top-decile observed effects exclude it by a wide margin (~6× the pooled effect) → **detectable, concentrated heterogeneity**.

## Ranking-quality reading

- Qini / AUUC ordering S > T confirmed by an independent hand-rolled cross-check of the raw Qini curve (`Yt(q) - Yc(q)·Nt(q)/Nc(q)`, sorted score-descending, ties→treated), both against the analytically derived random-ranking expectation `q · E[treat share] · (μt − μc)`; signs **and** S/T ordering agree with sklift.
- Raw excess-over-random area: S 13.63e9 vs T 13.22e9 (in "treated-attributable visits × rows" units, n = 2,096,296) — S-learner is the better CATE proxy, and the S-learner is also better calibrated in the top decile (pred 5.92pp vs obs 6.40pp; T overpredicts slightly: 6.52 vs 5.80).
- CATE distributions: heavy point mass near 0 with a long right tail — S range [−0.138, +0.313], T range [−0.264, +0.526]; median ≈ 0 for both. Most predicted mass is at "no personal effect"; the tail is where the signal lives.

## Calibration (key table: `e4_uplift_decile_validation.csv`)

- Both learners: observed effect is near-flat (~0.0–0.5pp, several deciles' CIs include 0) across D2–D9, then jumps sharply in D9 (S +0.47pp, T +0.58pp) and D10 (S **+6.40pp** [+5.89, +6.95]; T **+5.80pp** [+5.25, +6.36]).
- Decile-level Spearman(pred, obs): S 0.576, T 0.612; near-monotonicity across the middle range fails under a 0.05pp tolerance (both learners). D1 shows no detectable negative effect either (CI includes 0 for both; all observed decile effects ≥ −0.07pp).
- Interpretation: the heterogeneity that exists is a **sharp top-slice concentration**, not a finely graded surface. Mid-range CATE orderings are not trustworthy; S and T rank those users differently (Spearman 0.747, top-decile Jaccard 0.702 — good but clearly not identical).

## Verdict

- *STRONG, top slice only*: uplift-ranked top decile showed ~6pp observed effect vs 1.03pp pooled, CI well above pooled, independently reproduced by two different learners → heterogeneous treatment effect is detectable where it matters for the "target the top" policy question.
- *Null / flat*: below the top ~2 deciles the ranking carries essentially no validated signal (flat observed effects, non-monotone, learner-dependent ordering) — we do NOT claim person-level effect differences there; they are **negative estimated CATE** rankings with no confirmed corresponding group effect.
- *Sufficient for E7 policy comparison*: yes for the narrow question "top-decile-targeted vs broadcast" — a randomized two-arm experiment comparing those policies is well powered given the ~5pp contrast. Not sufficient to justify fine-grained (below top-decile) targeting tiers, uplift-thresholding at intermediate scores, or any per-user "this ad hurts you" claim.

## Problems during the step (transparency)

- First execution failed on a shape bug in the T-learner raw-Qini cross-check (baseline line built on the other learner's validity-filtered prefix grid); fixed by rebuilding per-learner baseline from its own prefix vector and asserting sign **and** ordering agreement with sklift.
- First-run top-decile/decile bootstrap CIs were mis-centered (resampled arm outcome *sums* differenced, then divided by combined n — a formula error producing CIs near +21pp that didn't bracket the +6.4pp point estimate); fixed by bootstrapping each arm's rate separately (`binomial(n,p)/n`) and differencing; verified CIs now bracket the point estimates. Deterministic (seed 42); final run is the one reported above.
- One cosmetic figure fix (clipped title) and verdict markdown filled from the final executed numbers; final notebook state passes Restart-and-Run-All with 0 errors (20 code cells, deterministic).

## Limitations

1. S-/T-learners are practical CATE proxies — no pointwise consistency guarantee for τ(x); only group contrasts in randomized arms inside score slices are causal.
2. Benchmark non-uniform subsampling (E3) caps absolute pp statements at benchmark scale; the ~6× ratio top-decile/pooled is the safer comparative read.
3. Conversion not modeled (0.29% base: unstable arm-wise slice contrasts); transfer of the visit-based ranking to conversion is untested here.
4. Mid-range uplift ranking is model-dependent (S/T Spearman 0.747); any proposed targeting rule should be evaluated on its *group* effect in a new experiment, not on score-conditional trust below the top slice.
5. Test split (hash%1000 ≥ 850) untouched; final reproducibility run on test is deferred to the wrap-up notebook.

## Artifacts

- Figures: `outputs/figures/e4_uplift_qini_validation.png` (Qini curves vs random-ranking baseline), `e4_uplift_score_distribution.png` (S/T CATE distributions), `e4_uplift_calibration_deciles.png` (pred-vs-obs decile scatter, bonus for the calibration audit)
- Tables: `outputs/tables/e4_uplift_metrics.csv`, `e4_uplift_decile_validation.csv`
- Scores: `data/interim/e4_val_uplift_scores.parquet` (2,096,296 × 3: row_hash, cate_s, cate_t) for downstream policy-comparison work
