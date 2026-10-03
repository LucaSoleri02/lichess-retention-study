# 06 — Sensitivity (duplicates), uplift segments (E6), experiment design (E7): results

**Notebook:** `Criteo/06_sensitivity_segments_expdesign.ipynb` (9 code cells, executed top-to-bottom, 0 errors).
**Blocks:** A — dedup sensitivity · B — E6 uplift segments · C — E7 experiment design + impact translation.

## Block A — Dedup sensitivity (verdict: ROBUST, with a real magnitude shift)

| outcome | version | treated rate | control rate | ITT (pp) | 95% CI |
|---|---|---|---|---|---|
| visit | full (primary) | 4.854% | 3.820% | **+1.034** | [1.006, 1.062] |
| visit | dedup | 5.405% | 3.912% | **+1.493** | [1.465, 1.523] |
| conversion | full (primary) | 0.309% | 0.194% | **+0.115** | [0.109, 0.122] |
| conversion | dedup | 0.344% | 0.198% | **+0.146** | [0.139, 0.153] |

- Dedup **raises** the ITT by ~44% relative (visit) — exactly what E1's duplicate anatomy predicted (visit=0 rows preferentially duplicated, deflating the contrast). Direction of every conclusion unchanged; the dedup number is arguably the cleaner read, but the frozen contract (full primary) stands — stated, not hidden.
- Treatment ratio barely moves (0.850 → 0.839).
- **Policy ordering survives dedup** (deduped validation, top 10% budget): uplift **67.2** [61.8, 73.0] vs response **48.5** [42.4, 54.8] incremental visits per 1,000 targeted — same >1.3× gap as the full-data validation read.
- Verdict: **conclusions robust to exact-row deduplication**; magnitude sensitivity documented (~+0.46 pp on the visit ITT) and worth one slide callout.

## Block B — E6 segments (validation, full data, S-learner CATE)

| segment | predicted CATE (pp) | observed effect (pp) | 95% CI | n |
|---|---|---|---|---|
| Top 10% | 6.35 | **+6.72** | [6.18, 7.30] | 190,466 |
| 10–25% | 0.71 | +0.54 | [0.24, 0.84] | 285,699 |
| 25–50% | 0.13 | +0.13 | [0.01, 0.23] | 477,212 |
| 50–75% | 0.03 | +0.08 | [0.04, 0.13] | 476,804 |
| Bottom 25% | −0.003 | +0.19 | [0.13, 0.25] | 476,956 |

- Top decile: predicted ≈ observed (6.4 vs 6.7), CI far above pooled ITT — the only segment with a validated actionable effect.
- Mid segments: calibration is excellent (0.13 pp predicted = 0.13 pp observed) but effects are small.
- **Bottom 25%: observed effect is positive (+0.19 pp) despite negative mean predicted CATE** — "avoid" actions there would be wrong; negative estimated CATE ≠ individual harm (explicit slide disclaimer).
- Interpretation labels: Top 10% = target; 10–25% = selective testing; 25%+ = deprioritize (never exclude "to protect").

## Block C — E7 design + impact

- Experiment: uplift top-k vs response top-k (control = current practice), equal budget at the 10% tier, primary metric = incremental visits per 1,000 targeted (slice contrast under randomization); guardrails = exposure/frequency, no economics in public data; pre-registered one-sided success criterion.
- Impact translation (benchmark scale): uplift at 10% budget captures **61.9%** of all incremental visits vs response **44.7%** (+17.2 pp share), ≈ **+12 incremental visits per 1,000 targeted** (68.3 vs 56.0 test-split). No monetary claim invented; bridge sentence: optimize against incremental contribution with internal economics.
- Power sketch (illustrative): slice contrast ~1.9 pp → ~2,400 users/arm at α=0.05/power 0.80 (vs the slice-vs-broadcast 5.7 pp contrast at ~190/arm) — targeted-slice contrasts are experimentally reachable; broadcast effects need millions. Clearly labeled illustrative; ignores clustering/multi-testing/noncompliance.

## Problems / diagnostics

- `core.ate_bootstrap` (row-resampling loop) was too slow on 13.9M rows and hung two runs; replaced with the distribution-identical vectorized Binomial(n,p̂)/n form (documented in `src/core.py`); full vs E3 CI agreement re-verified (1.006–1.062 vs 1.0055–1.0633).
- Deduped-validation joins had to be rebuilt by `row_hash` (row-position joins break after dedup); lengths validated (1,904,659 deduped validation rows).
- E2 response model refit for dedup slice validation: AUC 0.9466 reproduced → faithful.
- Earlier figures pass inspected and regenerated clean after a suptitle/annotation overlap in the dedup figure.

## Limitations

- Deduped population is not the real-world population (no user id; drops are content-identity based) — sensitivity read only.
- Segment effects are group contrasts; per-user CATE has no pointwise guarantees.
- All magnitudes benchmark-scale (non-uniform subsampling caveat E3/E5).
- Power sketch illustrative, not a real power analysis.

## Artifacts

- Figures: `outputs/figures/e6_dedup_sensitivity_itt.png`, `e6_uplift_segments.png`, `e7_experiment_power_sketch.png`
- Tables: `outputs/tables/e6_dedup_itt_sensitivity.csv`, `e6_dedup_policy_sensitivity.csv`, `e6_uplift_segments.csv`
- Notebook fully executed, outputs saved.
