# AGENTS.md — Project Conventions: Agent Instructions

`PLAN.md` defines **what** the project is trying to learn. This file defines **how** it gets executed.

## 0. Deliverable format — Jupyter notebooks (NEW)

From now on, **all analysis work is done in Jupyter notebooks**.
- Every new experiment, analysis, plot, or model step goes in a `.ipynb` (e.g. `Criteo/01_preprocessing_eda.ipynb`, `Criteo/02_ml_benchmark.ipynb`, `Criteo/03_causal_inference.ipynb`).
- Agents must **leave notebooks in a fully run state** (all cells executed top-to-bottom, outputs saved) so the user can just open them in Jupyter to view results or present them.
- Before finishing a notebook: **Restart & Run All must succeed** with no errors, and the saved notebook must contain the outputs.
- Do not create standalone `.py` experiment scripts for analysis work; notebooks are the deliverable. (Only shared utility code, if genuinely needed, may live in a small `.py` module imported by the notebooks.)
- Outputs/figures still get saved to `outputs/` where relevant so they are packed into slides.

## 1. Mission
Optimize for: **correct data → valid analysis → clear evidence → useful product insight → convincing experiment design.**
Not for: model count, experiment count, code volume, infra complexity, or benchmark scores without product relevance. A technically elegant pipeline with a weak or incoherent product story is not a successful outcome.

## 2. Source-of-truth hierarchy
1. Explicit user instruction
2. `PLAN.md` (the analytical/product contract)
3. `AGENTS.md` (execution conventions)
4. Existing code architecture
5. Implementation convenience

Never let code silently redefine the research question. If the analytical contract needs to change: log the issue, update `PLAN.md`, update affected code/tests, rerun checks.

## 3. Working loop
`INSPECT → DEFINE NEXT CHECKPOINT → IMPLEMENT → VALIDATE → INSPECT OUTPUT (figure/table) → COHERENCE CHECK → RECORD → CONTINUE`

Work in small increments (implement cohort change → run → inspect row counts/sample rows — not a rewrite of cohort+features+models+plots at once). A successful exit code is never sufficient evidence of progress — check the actual artifact: row counts, DQ status, figure rendered and inspected, table shape as expected.

Checkpoint discipline: after every meaningful iteration — a fixed bug, a data milestone, a completed figure, or a model benchmark — create a concise commit with a coherent message and a clear checkpoint summary. Do not let work pile up uncommitted across major analytical stages. The default rule is: commit after each checkpoint, then move to the next stage.

New branch discipline: larger analytical experiments or exploratory branches should start from a dedicated git branch (for example, `experiment/e4-format-hypothesis` or `experiment/e5-matchmaking`). Keep the base branch for stable pipeline checkpoints; do not mix unrelated experiment work into the same branch without a separate commit boundary.

Checkpoint after: cohort construction, label construction, feature construction, each of E1–E5, and E7 design. At each: *What did we learn? Did anything contradict the plan? Is the story stronger or weaker? What's the next highest-value uncertainty?* If unclear, stop and inspect evidence before writing more code. Don't let more than one analytical stage pass without opening the actual figure.

## 4. When blocked
Blocked = same failure repeats without a changed diagnosis, an implementation assumption is inconsistent, or a task has grown past its decision value.
1. Inspect the actual error/output, find root cause.
2. Try the smallest targeted fix.
3. Still stuck → stop, record `BLOCKER / EVIDENCE / LIKELY CAUSE / NEXT ACTION`, then fix, reduce scope, defer, or switch to an independent task. Never burn budget on a low-value blocker.

### Unattended runs
- When explicitly asked to work unattended, continue through the assigned task without waiting for user replies or stopping at routine checkpoints. Validate and record each checkpoint, then proceed to the next in-scope step.
- Prefer non-interactive command options. Do not launch commands that wait for input; if a required step cannot run non-interactively, record the blocker and continue with independent in-scope work.
- Do not treat user unavailability as permission for destructive or externally consequential actions. Preserve existing data and follow all source-of-truth, validation, and checkpoint rules above.

## 5. Unexpected or null results
Before an unexpected result enters the story, check in order: cohort definition, row counts, missingness, feature timing, duplicate users, target prevalence, bin sizes, model leakage, preprocessing, figure construction.

A null result is useful when it changes a decision (e.g. "format shows little association after controlling for X → eliminates the personalization hypothesis"). Don't manufacture a story from noise. When results disagree across reasonable definitions, don't force one conclusion — present the uncertainty and make the recommendation more cautious, not more confident.

## 6. Leakage prevention (strict)
Every feature has an explicit availability point. Maintain separate `operational_features` (only what's known by the intended intervention point, e.g. game 5 / day 7) and `diagnostic_features` (full first-30-day window). The operational model — the one that justifies "we could act on this in time" — must only use operational features. Never use diagnostic features to justify operational claims, current-state variables as historical predictors, or test-set performance to pick a model.

Train / validation / test: validation drives feature/model/threshold selection; test is for final evaluation only, reported separately, never used to pick a winner.

## 7. Statistics & hypothesis discipline
Report n, effect size, and uncertainty on every comparison; check distribution shape and missingness; avoid post-hoc binning chosen because it looks best; check robustness across reasonable definitions (e.g. multiple inactivity thresholds). Label anything discovered after looking at results as exploratory, not pre-specified.

Write the hypothesis before the result and don't retroactively edit it once you've seen the outcome — record instead that it became post-hoc.

## 8. Language: association vs. causation
Default language: *associated with, differs between, correlated with, consistent with the hypothesis.* Avoid *causes, drives, leads to, increases, reduces* unless backed by randomized evidence. The A/B test (E7) is the explicit boundary where causal language becomes appropriate. This applies everywhere: figure titles, code comments, checkpoint notes, final deck.

Bad: "Rapid users retain better, so recommend Rapid."
Good: "Rapid usage is associated with higher retention — investigate whether this is format fit, selection effect, or habit, and only formulate a recommendation experiment if there's a plausible influenceable mechanism."

## 9. Product-thinking loop
Every result that matters passes: `OBSERVATION → INTERPRETATION → ACTIONABILITY → PRODUCT HYPOTHESIS → EXPERIMENT`. Never jump straight from correlation to "ship it."

After E1–E3, draft this explicitly:
```
Observed: ...
Potential mechanism: ...
Influenceable: ...
Not influenceable: ...
Product hypothesis: ...
Evidence still needed: ...
```
If it can't be filled in with evidence, the project isn't ready for E7.

## 10. Figures
Generate a provisional figure early for every core experiment, inspect it, then polish. Check: correct population/window/denominator, no accidental filtering, sample size visible, uncertainty shown, causal language avoided unless earned, readable without zooming, no overcrowding. If a result looks surprising, investigate the data before explaining it in the deck.

Title the finding, not the variable: not "Retention by format" but "Users who settled into one format showed higher long-term activity."

## 11. Experiment contract
Every experiment script states: `Question / Decision / Population / Unit / Time window / Outcome / Features / Method / Assumptions / Outputs / Limitations / Phase`, and writes to `outputs/figures/` and `outputs/tables/` with names describing the finding (`e5_mismatch_churn_association.png`, not `plot7.png`).

Run each experiment as soon as its upstream artifact exists — don't wait for the whole pipeline to "finish." After each: classify the result as `STRONG ACTIONABLE / WEAK ACTIONABLE / STRONG BUT NON-ACTIONABLE / EXPLORATORY / NULL / DATA QUALITY ISSUE` (working labels, not deck claims) and use that to decide the next task — don't run experiments in order once one branch shows no product value.

## 12. Reproducibility & data quality
Every analytical run records: git revision, timestamp, target, model, params, feature set, split definition, data fingerprint, result metrics. Unreproducible-from-config is a defect. Use deterministic splitting.

Run DQ after rebuilding any major artifact. `FAIL` = genuine invariant violation (duplicate keys, malformed fields, impossible dates). `WARN` = suspicious but not necessarily wrong (large row-count swing, unusual prevalence). `SKIP` = artifact doesn't exist yet. Don't let an unfinished pipeline read as a wall of meaningless FAILs.

Fix all current-state analysis to one `ANALYSIS_AS_OF` snapshot. Re-pulling data later = a new snapshot, documented in the manifest, with affected labels/DQ rerun — never silently merged with the old snapshot.

## 13. Engineering hygiene
Check `src/` before writing a new plotting/metric/DQ/retry/feature utility — extend, don't fork, unless there's a clear reason. Priority order when trading off: `analysis correctness > statistical validity > product insight > reproducibility > engineering elegance > extra infra`. Before adding infra, ask whether it improves correctness, reproducibility, or the interview story — if not, defer it; the pipeline, DQ, harness, and registry that already exist are enough.

Comments explain *why*, not syntax (`# freeze cutoff so all current-state labels share one snapshot`, not `# set the cutoff variable`). Don't commit raw dumps, parquet, credentials, tokens, or large outputs. Commit source, config templates, experiment defs, docs, fixtures. Coherent commits (`fix user-relative 30-day window`), not `update stuff`.

Git workflow: every checkpoint is a commit, and each new product experiment or distinct analytical branch starts from a fresh branch. The branch should be named for the decision or experiment, and the commit should summarize what changed and what was validated. This keeps the project traceable, resumable, and ready for clean handoff between iterations.

## 14. Default execution sequence
```bash
python run_harness.py smoke
python run_harness.py data
```
Then the smallest valid pipeline step. After rebuilding artifacts: `python run_harness.py data`. Before changing a model: `python run_harness.py board --target churn` then `python run_harness.py best --target churn`. CLI specifics may evolve; the principle doesn't: **run → inspect → validate → compare → decide.**

## 15. Scope control
Before adding a feature, endpoint, experiment, or model: *What decision could this change? What uncertainty does it resolve? Can current data already answer it? What's the smallest implementation that answers it?* Unclear → don't build it yet.

Appendix work (2019 replication, extra endpoints, etc.) is fine once the core story is complete, if it answers a plausible interviewer question — but never at the cost of delaying data correctness, E1–E3, an identified actionable hypothesis, or the E7 experiment design.

## 16. Final deck audit
Walk every slide: *Why is this here? What's the one-sentence takeaway? What evidence actually supports it? What does it motivate next? Is the language causal only where earned? Does the conclusion survive the limitations section?* Prefer one excellent figure to three mediocre ones.

## 17. Definition of done
```
DATA        cohort reproducible · snapshot frozen · windows correct · labels documented
ANALYSIS    E1 done · operational E2 leakage-safe · diagnostic E2/E3 interpretable · E4/E5 evidence-based
STATISTICS  val/test separated · uncertainty reported · no test-set tuning · practical magnitude assessed
PRODUCT     actionable finding identified · mechanism documented · one intervention selected · A/B test fully specified
VISUALS     core figures generated, inspected · titles = takeaways · nothing misleading
ENGINEERING pipeline resumable · DQ passes · run provenance recorded · no secrets/raw-data leaks
NARRATIVE   every slide answers "so what?" · association/causal language audited · limitations stated · fits 10–15 min
```
Prefer **one complete, validated, well-explained product insight** over five partially implemented analyses.