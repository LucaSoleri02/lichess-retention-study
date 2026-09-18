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

## 12. Codebase structure
```
ds project/
  PLAN.md
  .venv/
  Lichess/
    explore_lichess.py
    src/
      config.py                <- paths, API constants, cohort params, churn bands, value-tier cutoffs
      client.py                <- sequential, polite API client; bulk users; aggressive 429 backoff
      dump.py                  <- download + stream-parse PGN headers (2016-01, 2016-02, recent month)
      cohort.py                <- Population A/B construction, bulk profiles (incl. patron), labels
      features.py               <- first-30-day behavior + habit + experience-quality features
      viz.py
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
      raw/ | interim/ | processed/
    outputs/
      figures/                 <- titled with the finding, not the variable
      tables/
```

## 13. Phases
| Phase | Content | Exit criteria |
|---|---|---|
| P0 Scaffolding ✅ | structure, config, client, packages | client sanity test passes |
| P1 Data acquisition | 2016-01 + 2016-02 + recent-month dumps → parquet | counts sanity-checked vs. published totals |
| P2 Cohort & labels | Pop. A/B, bulk profiles (incl. `patron`), retention + monetization + value-tier + voluntary/involuntary labels, behavioral cross-check | label balance reported for both outcomes |
| P3 Core analysis | E1–E3 | figures + tables, actionability table populated |
| P4 Hypotheses & test | E4–E5, E7 test design | test spec complete, causal language audited |
| P5 Survivors, polish, optional depth | E6, deck assembly; appendix items only if time allows | full dry-run under 15 min |

## 14. Risks & mitigations
- `seenAt` incompleteness → recent-month cross-check + explicit survival/censoring framing (§4).
- Unequal observation windows → 2016-02 pull (§3).
- Win-rate/skill cuts confounded by matchmaking/provisional ratings → control for volume; use post-provisional rating.
- No external benchmark for the hero number → read relative to itself, or reframe an optional 2019 cohort as a product-health check, not a validity check.
- Observational findings read as causal → actionability table + language discipline (§5, §8) + E7 as the explicit causal-claim boundary.
- Scope creep → appendix items (§9) are explicitly optional; the story stands on E1–E7.
- Sparse cells in E3–E5 cuts → report n and CI on every cut; prioritize sampling budget toward Population B (§15).

## 15. Open decisions for the user
- **Months to pull:** 2016-01 (cohort) + 2016-02 (window fix) + one recent month (cross-check) — three months total, still small.
- **2019-01 replication:** optional, only if reframed as product-health-over-time and only if there's spare time.
- **Personal API token for micro-behavior:** skip; low return for the format.
- **Sampling:** all Population-B signups + a smaller Population-A slice (~10–15k) than originally planned, reallocating budget toward window/cross-check pulls and toward having enough power in the E3–E5 cuts.

---

### Implementation notes (added during scaffolding, 2026-09-17)
- **Recent-month cross-check is a capped scan, not a full download.** The 2026-08 dump is ~30 GB compressed; we only need username presence, so `dump.py` streams the `.zst` and stops after `RECENT_MONTH_MAX_GAMES` (default 5M games ≈ first days of the month ≈ ~1.5 GB download). This underestimates "played recently" slightly (users whose only session fell later in the month are missed), so the login-vs-behavior gap it yields is a conservative bound — stated on stage.
- **Bulk profiles confirmed to return** `createdAt`, `seenAt`, `perfs`, `playTime`, `title`, `profile`; `patron` expected present when true (verified: field appears on patron accounts) — P2 will assert its presence before relying on it.
- All three target months: `2016-01` (0.87 GB), `2016-02` (~0.9 GB), `2026-08` (capped scan).
- **Experiment harness added (2026-09-17), extending §12.** Two layers, one CLI (`Lichess/run_harness.py`):
  - *Data-quality layer* (`src/data_quality.py`): declared PASS/WARN/FAIL/SKIP checks per pipeline artifact (schema, volume, integrity, distribution, bounds, completeness, drift vs previous build). Thresholds in one in-code dict. History in `outputs/harness/data_quality.jsonl`. Model runs *warn* on DQ FAILs but never block.
  - *Model layer* (`src/harness.py` + `src/metrics.py`): declared experiments (JSON packs in `harness_runs/`, versioned in git), deterministic username-hash split, headline metric `capture@10pct` (PLAN §7), append-only leaderboard, verdict vs best previous run for the same target. `smoke` subcommand self-tests both layers on synthetic data (isolated dir, never pollutes real history).
