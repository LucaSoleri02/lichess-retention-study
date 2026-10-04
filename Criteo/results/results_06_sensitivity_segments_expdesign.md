# 06 — Sensitivity (duplicates), uplift segments (E6), experiment design (E7): results

**Notebook:** `Criteo/06_sensitivity_segments_expdesign.ipynb` (10 code cells, executed top-to-bottom, 0 errors).
**Blocks:** A — dedup sensitivity (corrected story) · B — E6 uplift segments · C — E7 experiment design + impact translation.

## Block A — Dedup sensitivity (verdict: ROBUST, story corrected)

**Mechanism (from E1's collision check):** treated rows subsampled to control size duplicate at **4.43%** ≈ control's **4.54%** → the 17.9% treated-arm dup share is an **arm-size artifact**: identical feature vectors (real users on the boundary values of quantile-coded features) collide proportionally to group size (treated arm ~5.7× larger). Duplicates are **real users, not storage artifacts**.

| outcome | version | treated rate | control rate | ITT (pp) | 95% CI |
|---|---|---|---|---|---|
| visit | full (primary) | 4.854% | 3.820% | **+1.034** | [1.006, 1.062] |
| visit | naive dedup | 5.405% | 3.912% | **+1.493** | [1.465, 1.523] |
| conversion | full (primary) | 0.309% | 0.194% | **+0.115** | [0.109, 0.122] |
| conversion | naive dedup | 0.344% | 0.198% | **+0.146** | [0.139, 0.153] |

- Naive dedup **inflates** the ITT by ~45% relative (visit): it drops mostly zero-outcome treated rows, mechanically raising the treated rate. **Full data stays primary — the naive-dedup number is the artifact, not the fix.** This inversion is the deck's data-preprocessing story: *"a naive dedup would have inflated the effect by 45%."*
- Treatment ratio barely moves (0.850 → 0.839).
- **Policy ordering survives dedup** (deduped validation, top 10% budget): uplift **67.2** [61.8, 73.0] vs response **48.5** [42.4, 54.8] incremental visits per 1,000 targeted — same >1.3× gap as the full-data validation read. Every comparative conclusion is robust.
- Hash note: the validation-slice re-check dedups by 32-bit `row_hash` (content dedup for the full-data sensitivity); ~20k colliding distinct-row pairs are expected at 14M rows, so a few distinct rows merge — negligible at these effect sizes.

## Block B — E6 segments (validation, full data, S-learner CATE)

| segment | predicted CATE (pp) | observed effect (pp) | 95% CI | n |
|---|---|---|---|---|
| Top 10% | 6.35 | **+6.72** | [6.18, 7.30] | 190,466 |
| 10–25% | 0.71 | +0.54 | [0.24, 0.84] | 285,699 |
| 25–50% | 0.13 | +0.13 | [0.01, 0.23] | 477,212 |
| 50–75% | 0.03 | +0.08 | [0.04, 0.13] | 476,804 |
| Bottom 25% | −0.003 | +0.19 | [0.13, 0.25] | 476,956 |

- Top decile: predicted ≈ observed (6.4 vs 6.7), CI far above pooled ITT — the only segment with a validated actionable effect.
- Mid segments: calibration is good (0.13 pp predicted = 0.13 pp observed) but effects are small.
- **Bottom 25%: observed effect is positive (+0.19 pp) despite negative mean predicted CATE** — "avoid" actions there would be wrong; negative estimated CATE ≠ individual harm (explicit slide disclaimer).
- Interpretation labels: Top 10% = target; 10–25% = selective testing; 25%+ = deprioritize (never exclude "to protect").
- Slice treatment-share diagnostic: top-5%/top-10% uplift slices have treated share **87.7% / 86.7%** (population 83.9% on validation) — mild tilt, disclosed; slice contrasts remain causal under within-test randomization.

## Block C — E7 design + impact (power corrected per review)

- **The experiment:** two arms — current targeting (response top-k) vs uplift top-k — at equal budget (10% tier), **each arm carrying its own randomized holdout** (that holdout is what identifies the arm's incremental effect). Primary metric = incremental visits per targeted user; the comparison is the difference of the two arms' incremental effects (a difference-in-differences), not a simple two-proportion test.
- **Corrected power (actual slice arm rates from E5, `e5_slice_rates.csv`; uplift slice 27.4%/21.0%, response slice 37.4%/32.8%; contrast 1.78 pp):**
  - 50/50 within-arm holdout: **~41k users/arm**
  - 85/15 within-arm holdout: **~77k users/arm**
  - honest reference: detecting the broadcast ITT (+1.03 pp, 85/15) needs ~22k/arm — so the policy comparison costs only ~2–3.5× a broadcast test.
  - (The earlier "~2,400/arm" sketch fed the two policies' *effect sizes* into a two-proportion formula as if they were raw outcome rates — wrong in kind, understating n by ~15–30×. Replaced.)
- Impact translation (benchmark scale): uplift at 10% budget captures **65.4%** of all incremental visits vs response **47.3%** (+18.2 pp share), ≈ **+18 incremental visits per 1,000 targeted** (64.0 vs 46.2 validation; 68.3 vs 56.0 test). No monetary claim invented; bridge sentence: optimize against incremental contribution with internal economics.

## Problems / diagnostics

- `core.ate_bootstrap` (row-resampling loop) was too slow on 13.9M rows and hung two runs; replaced with the distribution-identical vectorized Binomial(n,p̂)/n form (documented in `src/core.py`); full vs E3 CI agreement re-verified.
- Deduped-validation joins rebuilt by `row_hash`; lengths validated (1,904,659 deduped validation rows).
- E2 response model refit for dedup slice validation: AUC 0.9466 reproduced → faithful.
- Power cell rewritten to the corrected design and re-executed; figure regenerated from actual slice rates.

## Limitations

- Deduped population is not the real-world population (no user id; drops are content-identity based) — sensitivity read only.
- Segment effects are group contrasts; per-user CATE is a proxy (no pointwise guarantees).
- Power calc ignores clustering, multiple testing, and non-compliance; rates are benchmark-scale.
- All magnitudes benchmark-scale (non-uniform subsampling caveat).

## Artifacts

- Figures: `outputs/figures/e6_dedup_sensitivity_itt.png`, `e6_uplift_segments.png`, `e7_experiment_power_sketch.png` (regenerated, corrected design)
- Tables: `outputs/tables/e6_dedup_itt_sensitivity.csv`, `e6_dedup_policy_sensitivity.csv`, `e6_uplift_segments.csv`, `e6_slice_treated_share.csv`
- Notebook fully executed, outputs saved.
