# Which Early Experiences Predict Long-Term Retention? A Product Analytics Study on Lichess

## Central question
"Which early user experiences predict long-term retention — and among those, which ones can the product actually influence, and what would we test first?"

Not "what predicts retention" (a modeling question) and not "I analyzed Lichess" (a dataset question). The project is framed as diligence on a mature consumer product with a large, partly-dormant user base — Bending Spoons' own domain — using Lichess's public 10-year history as the natural experiment.

## Story spine
**Problem → Diagnosis → Opportunity → Intervention → Experiment → Impact.**

Everyone can play chess online for free. Most products lose users within weeks. Some Lichess players from 2016 are still here in 2026. Could we have told who, from their first month — and if we could, what would we actually do about it?

The presentation must get all the way from "here's an interesting relationship in the data" to "here's the product lever, here's the test I'd run, here's how I'd measure whether it worked." Stopping at the relationship is the single biggest risk to cut before presenting.

## 0. Why this works as the final-interview project
- Diligence/product-flavored question, not a Kaggle-style modeling exercise.
- Public, documented, lawful data: Lichess database dumps + public API.
- A real longitudinal design: a complete signup cohort (population, not a sample of survivors) + status today, with a clean post-signup observation window.
- Two outcome variables, not one: who stayed, and (via `patron`) who paid — genuinely relevant to a subscription-model acquirer, and free in data already pulled.
- Every finding is classified by whether the product can actually act on it, and the closing slide is an experiment design, not a chart.

## 1. Two populations — define both, but Population B carries the story
- **Population A — existing users active in Jan 2016.** Mixed tenure; used only for "where does today's activity/value come from" (concentration), not as the retention denominator.
- **Population B — new signups in Jan 2016 (`createdAt` in-month).** The primary population for every early-experience → outcome question. Someone three years into Lichess who happened to play in January is a different subject than someone who signed up on the 12th; conflating them was the biggest structural flaw to fix.

## 2. Data strategy (all endpoints verified live on 2026-09-17)

| Source | Auth | What it gives us | Role |
|---|---|---|---|
| PGN dump, **2016-01** (0.87 GB .zst) | none | Every rated standard game: players, Elos, result, time control, termination | Population A/B frame |
| PGN dump, **2016-02** | none | Same, one more month | Completes the post-signup window — see §3 |
| PGN dump, one **recent month** (e.g. 2026-08) | none | Usernames active that month | Behavioral cross-check against `seenAt` (see §4) |
| `POST /api/users` (bulk, 300 ids/call) | none | `createdAt`, `seenAt`, `perfs`, `playTime`, `title`, **`patron`** | Retention label, current value tier, **monetization label** |
| `GET /api/user/{u}` | none (works despite spec saying OAuth) | Full profile | Subsample enrichment / fallback for missing bulk fields |
| `GET /api/tournament`, `/api/player/top/200/{perf}`, `/api/user/{u}/rating-history` (empty for most users), `/api/games/user/{u}` (OAuth2), `/api/user/{u}/activity` (7-day only) | — | Product-today snapshot / not usable / needs token / not longitudinal | Appendix only or dropped, see §9 |

**API etiquette (corrected):** sequential requests, one at a time; honor `Retry-After`; back off aggressively (Lichess's own guidance is closer to a full minute) on 429s; use the bulk endpoint wherever possible. Not "~1 req/s."

## 3. Fixing the observation window
January-only data gives a Jan-30 signup one or two days of "first month" and a Jan-1 signup a full 31 — not comparable. Pull **2016-02** as well so every Population-B signup gets a clean, equal-length 30-day post-signup window regardless of signup date. This is a correctness fix, not scope creep — it directly strengthens every early-behavior experiment (E3–E5 below).

## 4. Fixing the retention label itself
`seenAt` is the timestamp of last observed activity, not a full activity trajectory — a user who played in 2016, vanished for two years, returned in 2019, and vanished again in 2023 collapses to one number. Two consequences, both stated on stage rather than buried:
- **Don't call the hero chart a "10-year retention curve."** Call it **10-year survival to last observed activity**, state the right-censoring assumption explicitly, and note this reads as more rigorous, not less.
- **Cross-check it.** Parse the recent-month dump for username presence and compare login-based "still here" against behavior-based "played recently." Report the gap as a finding about measurement quality, not just a caveat — and it gives you a fully independent read on the true churn rate.
- **Split voluntary from involuntary.** Currently-excluded ToS-closed/disabled accounts should be broken out as their own segment rather than dropped — it's the direct analog of payment-failure churn in a subscription business, and Lichess exposes it for free.

## 5. The actionability taxonomy — the single most important slide
Classify every variable before presenting it, and put this table on stage:

| Type | Example | Product usefulness |
|---|---|---|
| User characteristic | Initial Elo, "enjoys chess more" | Mostly descriptive — control for it, don't headline it |
| Behavioral signal | Games played, active days | Useful for identifying risk, not for choosing an intervention |
| Product-influenceable experience | Format guidance, matchmaking difficulty, onboarding | High — this is where a test can actually change the outcome |

This reframes the whole project from "what predicts retention" to "what predicts retention, and which of those things can the product change." Drop the standalone "are strong players stickier" cut (old E3) — keep Elo only as a control variable in models, not a dedicated section; it's descriptive, not actionable, and costs presentation time for a low-value myth-bust.

## 6. Second outcome: retention isn't the only thing worth predicting
The bulk profile pull already returns `patron` (paid-supporter status) at zero extra cost. Run the same first-month features against **two** outcomes — stayed, and paid — and compare. Are "sticky" and "valuable" the same population, or different ones? For a company whose model is converting free mature user bases into subscription revenue, this is arguably the single most on-brand question the dataset can answer, and it doesn't appear if you only ever ask "did they stay."

## 7. Experiment map — a product funnel, not a list of research questions
Each row states the business decision it feeds, not just the analytical question.

| # | Question | Method | Output | Business decision |
|---|---|---|---|---|
| E1 — Diagnose | How quickly do new users disappear, where's the biggest drop-off, and where is today's value concentrated? | Survival curve (Pop. B) + behavioral cross-check (§4); voluntary/involuntary split; value-tier concentration of Pop. A today (dormant/casual/core/power) | Hero survival curve + "N% of today's activity traces to 2016" | When and whom should the product intervene for? |
| E2 — Predict | Can we identify likely churners, and likely payers, early enough to act? | Classifier(s) on first-30-day features (§3) → two outcomes: churn risk, `patron` propensity. Report **top-decile capture** ("highest-risk 10% accounts for X% of eventual churn"), not AUC as headline | Lift/gain curve, precision@k | Who to target, and can we afford to reach them? |
| E3 — Explain | Which early experiences are associated with each outcome, classified by actionability (§5)? | Effect sizes for engagement (games/active days/sessions/streaks, controlling for volume), format exploration, and experience-quality features | Actionability table populated with real numbers | Which levers are worth building? |
| E4 — Format hypothesis | Does first format correlate with retention? | Retention by dominant first-window format, stated as association only | "Format is associated with retention → motivates a personalization hypothesis" | Onboarding/recommendation experiment candidate |
| E5 — Matchmaking hypothesis | Does early difficulty mismatch — not just losing — predict churn? | Opponent-rating mismatch, consecutive losses, abandonment/short-game rate vs. churn, controlling for volume (win-rate alone is confounded by matchmaking) | "Difficulty mismatch is associated with churn → motivates a calibration hypothesis" | Matchmaking/beginner-protection experiment candidate |
| E6 — Survivors & resurrection | Who are the long-term survivors, and do dormant users come back? | Then-vs-now archetypes for retained Pop. B; recent-month presence among previously-dormant users ("zombie" reactivation rate) | Archetype slopegraph + resurrection rate | Winback vs. new-user-activation prioritization |
| E7 — Act (climax) | Which intervention would I test first, and what would it be worth? | Full A/B test design on the strongest E3–E5 finding + business-impact translation (see §8) | Test spec + impact estimate | Ship/no-ship decision framework |

## 8. E7 in full — the slide that turns analysis into a decision
**Hypothesis:** e.g. "Personalized first-week guidance for high-risk new users increases long-term retention."
**Target population:** new users flagged by E2 after their first 3–5 games.
**Treatment / control:** intervention (e.g. format recommendation, calibrated matchmaking) vs. current experience.
**Primary metric:** 30-day active retention. **Secondary:** 7-day retention, games/user, active days.
**Guardrails:** match quality, abandonment rate, negative feedback.
**Analysis:** intent-to-treat.
**Business impact:** translate a hypothetical lift into "+N retained users per 100k acquired," and say explicitly: *"The public dataset doesn't provide the economics needed to estimate monetary impact — in a real environment I'd convert incremental retained users into incremental LTV/revenue net of intervention cost."* That sentence is the answer, not a hedge.

Throughout E3–E7, discipline the language on stage: **association** for what the data shows ("associated with retention"), **hypothesis** for what you'd try ("could improve retention"), **causal claim** reserved only for what E7's test, if run, would establish.

## 9. What to cut from presentation time
Leaderboards, current tournaments, API endpoint exploration, directory structure, download mechanics, and the micro-behavior/OAuth-token analysis (old E8) all move to appendix or get dropped — produce on request, never spend main-deck minutes on them. A 2019-01 replication (old E9) is optional and only worth keeping if reframed as "is the product getting better at retaining cohorts over time," not as a robustness footnote.

## 10. Decision table (put this directly in the deck)

| Business question | Analysis | Possible finding | Product decision |
|---|---|---|---|
| Where do users disappear, and where is value today? | E1 | Early drop-off; value concentrated in a small tier | When/whom to intervene for |
| Can we identify risk (and value) early? | E2 | High-risk/high-value segments captured in top decile | Who to target, feasibility |
| Does early engagement matter? | E3 | Frequency > volume; habit signals | Activation strategy |
| Does format matter? | E4 | Format differences in retention | Recommendation experiment |
| Does difficulty matter? | E5 | Mismatch → churn | Matchmaking experiment |
| Who are the long-term survivors, do dormant users return? | E6 | Archetypes; resurrection rate | Winback vs. activation priority |
| Does the intervention work? | E7 | Projected retention lift | Ship/no-ship + impact model |

## 11. Presentation flow (10–15 min)
1. Business question, not "I analyzed Lichess."
2. The product lifecycle: signup → first game → first week → first month → habit → long-term retention/pay.
3. Data — concise: two populations, the Feb-2016 window fix, what isn't measurable.
4. E1 — one hero survival chart, one concentration number, one takeaway.
5. E2 — risk/lift, headline is top-decile capture, not AUC.
6. E3 — engagement, format, experience-quality, presented through the actionability table.
7. **The actionability table itself as its own slide** — influenceable vs. not.
8. E4/E5 as hypotheses, explicitly "associated with," not "causes."
9. E7 — the A/B test design. This is the climax, not an appendix.
10. Business impact translation (§8).
11. Limitations: `seenAt` incompleteness (mitigated, not solved, by the recent-month cross-check); no economics in public data; observational ≠ causal; rated-standard-only coverage; 2016 era vs. today. Close with: *"These limitations define what I can conclude and what I'd test next with internal product data."*

Close, once, without forcing it: *"I approached this as a product analytics problem — start from a business outcome, identify drivers, separate actionable from non-actionable factors, and design the experiment that would validate the intervention"* — and let it map itself onto the role rather than naming Bending Spoons' job description out loud.

## 12. Technical architecture (AGENTS.md source of truth)

### 12.1 Layout

```
ds project/
  PLAN.md                  <- this file (product plan + technical architecture)
  .venv/                   <- uv-managed Python 3.12 venv (shared across repos)
  .gitignore               <- excludes .venv, all data/outputs, interview-internal datasets
  .gitattributes           <- LF normalization for tracked text files
  Lichess/
    explore_lichess.py     <- original scoping script (kept as history)
    run_pipeline.py        <- end-to-end runner: P1→P2→P2b→P3, idempotent, resumable
    run_harness.py         <- CLI entry point (smoke / run / batch / board / best / data)
    harness_runs/          <- experiment packs (JSON), versioned in git
      baseline_pack.json
    src/
      __init__.py
      config.py            <- paths, API constants, cohort params, churn bands, value-tier cutoffs, sampling
      client.py            <- LichessClient: sequential, polite, aggressive 429 backoff, bulk users (checkpointed)
      dump.py              <- download + stream-parse PGN headers → typed games parquet; recent-month capped username scan
      cohort.py            <- Population A/B construction, bulk profiles (resume-friendly checkpoint), labels, segments, value tiers
      features.py          <- equal 30-day post-signup windows, engagement/habit/experience-quality features
      metrics.py           <- capture@10pct, precision@k, lift@k, roc_auc, log_loss
      harness.py           <- Experiment spec, deterministic username-hash split, model factory, runner, append-only leaderboard, verdict
      data_quality.py      <- PASS/WARN/FAIL/SKIP checks per artifact, drift, jsonl history, warn-only gating
      viz.py               <- shared matplotlib style + save helpers
    experiments/
      e1_diagnose_survival_and_concentration.py
      e2_predict_risk_and_value.py
      e3_explain_actionability.py
      e4_format_hypothesis.py
      e5_matchmaking_hypothesis.py
      e6_survivors_and_resurrection.py
      e7_act_ab_test_and_impact.py
      appendix/
        snapshot_today.py
        cohort_2019_replication.py
    data/
      raw/                 <- .zst dumps (reproducible via dump.py)
      interim/             <- games parquets, user aggregates, active-user scan
      processed/           <- final cohort table with labels
    outputs/               <- all generated artifacts (gitignored)
      figures/             <- charts, titled with the finding
      tables/              <- csv summaries
      harness/             <- model leaderboard.csv + per-run JSON sidecars
        data_quality.jsonl <- append-only DQ history
      harness_smoke/       <- isolated smoke-test outputs (never touches real history)
  Spotify/                 <- parallel exploration (public data candidates), kept as history
```

### 12.2 The two-layer harness

Everything is designed around one loop: **change something → run → know if it helped.** Two layers share the same CLI and the same append-only registry philosophy.

#### Data-quality layer (`src/data_quality.py`)
Declared checks per pipeline artifact; each returns PASS / WARN / FAIL / SKIP.

| Artifact | Check categories |
|---|---|
| `games_<month>.parquet` | schema (required columns present); volume (row count vs expected range); integrity (null rates, no duplicates, datetimes in month, result ∈ {1-0, 0-1, ½-½}, Elo ∈ [600, 3200], nummoves ≥ 1); distribution (speed mix not degenerate, timecontrol parse rate) |
| `cohort_<month>.parquet` | integrity (unique username, no null usernames, created_at ≤ seen_at); label sanity (Pop-B share, active_90d rate, patron rate < 15%, segments cover all); coverage (`played_recent_month` populated) |
| `user_window_features.parquet` | bounds (rates/shares ∈ [0,1], days_active ≤ 31, games_total ≥ 1); completeness (Pop-B coverage ≥ 95%) |
| any rebuilt artifact | **drift** vs previous DQ run: row-count Δ% and label-rate drift → WARN beyond tolerance |

- Thresholds live in **one dict** (`THRESHOLDS`) at the top of `data_quality.py`, tuned in code, versioned with the repo. Row-count ranges are first-pass estimates to tighten in P1 against Lichess's published monthly totals.
- **History**: every DQ run appends one JSON line to `outputs/harness/data_quality.jsonl` with timestamp, counts, and full check records — you can see over time whether the pipeline is degrading.
- **Gating (warn-only)**: `run`/`batch` calls check the latest DQ verdict for the cohort; if any FAILs, a prominent banner prints but execution continues. This is deliberate (decided 2026-09-17): DQ gates the *inputs* but the experiment harness stays independent during exploration.
- **SKU** artifact-not-built checks become `SKIP` (not FAIL) so early-stage runs are informative, not broken.

#### Model layer (`src/harness.py` + `src/metrics.py`)
| Component | Detail |
|---|---|
| **Deterministic split** | `md5(username) % 1000 < 200` → train/test. Same split across every run (no stored split files), so any two runs with the same target are directly comparable. |
| **Headline metric** | **`capture@10pct`** = share of all positives in the top 10% scored (PLAN §7). AUC is reported but never headlined. Plus precision@k, lift@k, roc_auc, log_loss. |
| **Verdict** | compares the new run to the **best previous run for the same target** on `capture@10pct` → `IMPROVED` / `NO IMPROVEMENT` / `FIRST RUN`. |
| **Registry** | append-only `outputs/harness/leaderboard.csv` + one JSON sidecar per run in `outputs/harness/runs/`. Each run records: git hash, timestamp, target, model, params, features, data fingerprint (row count + hash of input frame). |
| **Models** | `logreg` (impute+scale), `gbdt` (`HistGradientBoostingClassifier`, native NaN), `rf`. Wrapped in sklearn Pipelines. |
| **Feature presets** | `core` / `habit` / `experience` / `control` / `all`, composable via `+` (e.g. `core+habit`) or explicit comma list. Elo enters only as `control` (descriptive, not a headline — PLAN §5). |
| **Targets** | `churn` = `~active_90d` (1 = churned); `patron` = `patron` flag (1 = paid supporter). |
| **Smoke mode** | `smoke` subcommand generates a synthetic Pop-B-like frame with planted linear signal, runs the DQ layer (including a deliberately-broken frame to prove FAIL detection), and runs the baseline pack. Writes to an **isolated** directory (`outputs/harness_smoke/`) so synthetic results never pollute the real leaderboard or DQ history. |
| **Comparison rule** | two runs are comparable iff they share the same target + split (guaranteed by the hash) and the same data fingerprint (guaranteed by logging). |

#### CLI reference (`run_harness.py`)
```
python run_harness.py smoke                                        # self-test on synthetic data
python run_harness.py data                                         # DQ checks on all built artifacts
python run_harness.py data --dataset <dataset>                     # one artifact
python run_harness.py data --history                               # past DQ runs (timestamped summary)
python run_harness.py run --target <churn|patron> --model <logreg|gbdt|rf> --features <preset|list> [--param k=v] [--name ...]
python run_harness.py batch harness_runs/baseline_pack.json        # run a declared pack
python run_harness.py board [--target <t>] [--metric <capture@10pct|precision@10pct|lift@10pct|roc_auc|log_loss>]
python run_harness.py best [--target <t>]                          # current champion per target
```
- `run`/`batch` warn on DQ FAILs; `warn if git dirty` note printed when the working tree is unclean.

### 12.3 Pipeline runner (`run_pipeline.py`)
End-to-end: P1 → P2 → P2b → P3. Each step is **idempotent** (skips when its output file exists) and checkpointed, so a restart only finishes the incomplete portion.
- Step `dump`: downloads the .zst (idempotent) and parses to parquet.
- Step `cohort`: bulk-profiles all distinct cohort-month users (checkpointed to `data/interim/profiles_checkpoint.jsonl`; re-runs fetch nothing).
- Step `features`: window features for Population B; Jan aggregates for Population A.
- Step `data`: runs DQ checks and appends the run to history.
- Step `model`: runs the baseline pack (`harness_runs/baseline_pack.json`).

### 12.4 Experiment stub contract (`experiments/`)
Each stub is a standalone, runnable script (imports `src`, writes to `outputs/figures` and `outputs/tables`). Each documents: **Question · Method · Inputs · Outputs · Business decision · Phase**. The experiment map is in PLAN §7; each stub implements its slice.

### 12.5 Data strategy recap (PLAN §2)
| Source | Auth | Role | Size |
|---|---|---|---|
| `2016-01` dump | none | Population A/B frame | ~0.87 GB |
| `2016-02` dump | none | equal 30-day post-signup window | ~0.9 GB |
| `2026-08` dump | none | capped username scan (PLAN §4 cross-check) | ~30 GB (only ~1.5 GB transferred, 5M-game cap) |
| `POST /api/users` (bulk, 300/call) | none | profiles + labels | ~200k users (~20 min, checkpointed) |

`gh` CLI: authenticated as `LucaSoleri02` (`repo`, `gist`, `read:org`, `workflow` scopes). `gh` is on PATH in new shells (machine PATH set by installer; `~/.bashrc` also exports it); old shells can refresh with `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`.

## 13. Phases (current status in parentheses)
| Phase | Content | Exit criteria |
|---|---|---|
| **P0** ✅ | structure, config, client, packages | client sanity test passes |
| **P1** 🔄 in progress | 2016-01 ✅ parsed (75 MB parquet), 2016-02 parsing, then `recent` capped scan | counts sanity-checked vs. published totals |
| P2 | Pop. A/B, bulk profiles (incl. `patron`), retention + monetization + value-tier + voluntary/involuntary labels, behavioral cross-check | label balance reported for both outcomes |
| P3 | E1–E3 | figures + tables, actionability table populated |
| P4 | E4–E5, E7 test design | test spec complete, causal language audited |
| P5 | E6, deck assembly; appendix items only if time allows | full dry-run under 15 min |

## 14. Risks & mitigations
- `seenAt` incompleteness → recent-month cross-check + explicit survival/censoring framing (§4).
- Unequal observation windows → 2016-02 pull (§3).
- Win-rate/skill cuts confounded by matchmaking/provisional ratings → control for volume; use post-provisional rating.
- No external benchmark for the hero number → read relative to itself, or reframe an optional 2019 cohort as a product-health check, not a validity check.
- Observational findings read as causal → actionability table + language discipline (§5, §8) + E7 as the explicit causal-claim boundary.
- Scope creep → appendix items (§9) are explicitly optional; the story stands on E1–E7.
- Sparse cells in E3–E5 cuts → report n and CI on every cut; prioritize sampling budget toward Population B (§15).
- **Metric comparability** → deterministic hash split + data fingerprint in every run record (§12.2).
- **DQ gate staleness** → warn-only coupling; re-run `data` if the pipeline artifacts change.
- **Long P2 pull (~20 min, 200k profiles)** → checkpointed; a restart fetches nothing.

## 15. Open decisions for the user
- **Months to pull:** 2016-01 (cohort) + 2016-02 (window fix) + one recent month (cross-check) — three months total, still small.
- **2019-01 replication:** optional, only if reframed as product-health-over-time and only if there's spare time.
- **Personal API token for micro-behavior:** skip; low return for the format.
- **Sampling:** P2 pulls **all** distinct cohort-month users (~200k, ~20 min via checkpointed bulk) — this yields complete Population B plus the full Population A; experiments then report/aggregate as needed (the plan's "~10–15k Pop-A slice" is applied downstream in experiment reporting).
- **TODO — latest profile fetch:** Retry the remaining 2,524 January-player profiles after the Lichess bulk API rate limit clears; rebuild the cohort, features, DQ, and affected experiment outputs from the final checkpoint.
- **P1 in progress** — 2016-02 is still being parsed when you read this; `recent` and P2 follow.

---

### Implementation notes
- **Recent-month cross-check is a capped scan, not a full download** (§12.5). `dump.py` streams the `.zst` over HTTP and stops after `RECENT_MONTH_MAX_GAMES` (default 5M games ≈ first days of the month ≈ ~1.5 GB download). This underestimates "played recently" slightly (users whose only session fell later in the month are missed), so the login-vs-behavior gap it yields is a conservative bound — stated on stage.
- **Bulk profiles confirmed to return** `createdAt`, `seenAt`, `perfs`, `playTime`, `title`, `profile`; `patron` present on patron accounts — `cohort.py` normalizes flags to boolean.
- All three target months: `2016-01` (0.87 GB), `2016-02` (~0.9 GB), `2026-08` (capped scan).
- **Harness smoke-tested end-to-end** (2026-09-17): DQ catches a planted FAIL (`9-9` result) and PASS checks pass; model verdicts fire correctly (`FIRST RUN` → `IMPROVED` → `NO IMPROVEMENT`). Synthetic pack runs in isolated `harness_smoke/`, never touching the real leaderboard.
