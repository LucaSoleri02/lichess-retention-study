# Cross-Project Comparison: Lichess · In-game Currency · Ad Performance

Three product-analytics case studies built in this repo, compared on framing, evidence,
and what each would actually change. All three are **observational**; causal claims are
reserved for the experiment each one designs. Numbers are from the latest local runs
(`Lichess/outputs/`, `In-game Currency/outputs/`, `Ad Performance Dataset/outputs/`).

## 1. At a glance

| | **Lichess** | **In-game Currency** | **Ad Performance** |
|---|---|---|---|
| Central question | Which early experiences predict long-term retention / payment, and which can we influence? | Where does the monetization funnel break, and what lifts long-term payer value without deepening whale dependence? | At what point does extra ad spend stop paying for itself, and what fixes it? |
| Type | Retention + monetization (subscription-analog) | Monetization journey | Growth / unit economics |
| Data | Public 10-yr history + API; Jan-2016 signups (Pop B n=22,566) | Fixed cohort: 6,838 installs (Mar 1–7), observed to Apr 30 | 86 campaign-days, Oct 7–Dec 31, $90/day cap |
| Unit | User (signup cohort) | User / payer / purchase (explicitly switched) | Campaign-day |
| Outcome(s) | active_90d, patron | First purchase, repeat purchase, revenue | CPI, ARPD, contribution |
| Maturity | Full harness: model leaderboard, DQ history, run registry | Experiment suite (E1–E8) + A/B design | Experiment suite (E1–E8) + A/B design |
| Headline experiment | Targeted first-week onboarding A/B | Second-purchase retention A/B | Creative-refresh A/B |

## 2. Headline findings, side by side

### 2.1 Concentration is the common structural fact — but its shape differs

| Project | Concentration evidence | Reading |
|---|---|---|
| Lichess | Power tier = 11.3% of observed play time from 630 users; casual+core ≈ 85% | Engagement is **broad-based**; value less whale-dependent |
| Currency | Top 1% of users = **78.5%** of net revenue; top decile of payers = 57.8%; payer Gini 0.70 | Revenue is **whale-dependent**; base-broadening and whale-deepening are different bets |
| Ads | Contribution declines through the campaign; cumulative profit peaks at day 63 then slips | Value is **time-concentrated**, not user-concentrated |

Interpretation: "concentration" means three different things. Lichess concentrates
*attention*, Currency concentrates *revenue*, Ads concentrate *value in time*. A single
"concentration is bad" slide would be wrong for all three.

### 2.2 The early window dominates in all three

| Project | Early-window evidence |
|---|---|
| Lichess | `week1_days_active` high-vs-low → active_90d **+17.5 pp** (CI 16.3–18.7); games_total **+22.6 pp**; survival still 49.6% at year 1 |
| Currency | **52%** of eventual payers convert within **1 h**; 66% same-day; median 43 min; D1 = 51% of D30 revenue/installer |
| Ads | CPI rises steadily with campaign age (r=0.92); CTR falls (r=−0.56); implied post-click conversion 68.5%→48.3% |

All three say the critical decisions happen early. The three differ in *what to do* about
it: Lichess → onboarding/activation; Currency → offer timing vs second purchase;
Ads → creative refresh before acquisition economics erode.

### 2.3 The payer journey has its steepest step at purchase #1 → #2

Currency's repeat funnel is the clearest single actionable result across the three:
`275 → 150 (54.5%) → 111 (74%) → 79 (71%)`. One-time payers are 45.5% of payers but
only 10.6% of revenue. This is why the currency experiment targets **second-purchase
retention** rather than first conversion.

### 2.4 Where prediction fails (usefully)

| Project | Predictive attempt | Result |
|---|---|---|
| Lichess | Churn classifier | Works modestly: capture@10% ≈ 0.114, AUC 0.71–0.74 vs 84% base churn |
| Lichess | Patron (payer) classifier | **Fails**: capture@10% 0–0.2, AUC 0.45–0.65 on a 0.11% base |
| Ads | Budget-response curve | **Not estimable**: 73/86 days at the $90 cap — no dose variation |
| Currency | (Avoided by design) | Framed as journey, not "predict who pays" |

The two "failures" are findings, not dead ends: Lichess says *value* is not predictable
from early behavior even when *retention* is; Ads says the campaign never generated the
variation needed to answer its own scaling question. Both redirect the next experiment.

## 3. Methodological comparison

### 3.1 Causal discipline (all three)
- **Lichess:** actionability taxonomy separates user characteristics, behavioral
  signals, and product-influenceable features; E4/E5 are framed as "associated with".
- **Currency:** E2 timing ≠ malleability; the offer-timing claim is deferred to E7.
- **Ads:** E4 is "age-or-season", never "fatigue"; no "optimal budget" claim because
  APPD ≡ ARPD − CPI is an accounting identity, not a response curve.

### 3.2 Data-quality issues that shaped conclusions
| Project | DQ finding | Effect on analysis |
|---|---|---|
| Lichess | `seenAt` is last-activity only; DQ FAIL on `days_active`=32 > 31 cap | Hero chart reframed as survival to last observed activity; 1 remaining FAIL noted |
| Currency | 246 exact full-row duplicates (3.1%) | Raw kept primary; dedup sensitivity: revenue −6.2%, purchases/payer 4.25→3.36, payers unchanged |
| Ads | Sheets' scopes don't align (`Total downloads` unspecified) | Organic-halo claim suspended (residual 855/day vs 13/day baseline) |

### 3.3 Reproducibility
- **Lichess:** deterministic hash split, append-only leaderboard with git hash + data
  fingerprint, DQ history (`data_quality.jsonl`), warn-only gating.
- **Currency / Ads:** lighter `src/` + `experiments/` suites, each with a DQ table
  (`e0_data_quality.csv`) and a single runner; outputs named for the finding.

The Lichess project is the only one where model comparisons are formally governed;
the other two are deliberately lightweight because their datasets are small and static
(AGENTS.md §13: don't add infra that doesn't improve correctness).

## 4. What each project would do next

| Project | Selected intervention | Primary metric | Guardrail that matters |
|---|---|---|---|
| Lichess | First-week guidance / matchmaking for flagged new users | 30-day active retention | Match quality, abandonment |
| Currency | Post-first-purchase touchpoint | 1st→2nd purchase conversion (14d) | **Revenue concentration** must not worsen |
| Ads | Creative refresh (A/B); budget step-test next campaign | Contribution per $1,000 spend | ARPD of acquired installs (not just cheap installs) |

## 5. Synthesis — what the three together demonstrate

1. **Concentration is the default, and its type determines the strategy.** Attention
   (Lichess) is broad; revenue (Currency) is extreme; value (Ads) is time-bound.
2. **The early window is where leverage lives**, but leverage is not the same as
   influence: Lichess can test onboarding, Currency can test post-purchase timing,
   Ads can test creative — none can be assumed causal without the experiment.
3. **Prediction is not the point.** The strongest results are journey/timing/economic
   diagnostics; the most useful nulls are the failed payer classifier (Lichess) and the
   absent budget response (Ads).
4. **Honest data limits are part of the deliverable.** Censored activity, duplicate
   events, and mismatched sheet scopes each changed a conclusion — and identifying that
   is more valuable than a cleaner-looking but wrong number.

## 6. Limitations of this comparison
- The three datasets describe different products, platforms, and periods; the parallel
  structure (funnel → timing → concentration → experiment) is a **method**, not evidence
  that the products behave alike.
- Lichess results are from a profile checkpoint (P2 incomplete; one open API retry), so
  its numbers are preliminary; Currency/Ads results are final for the supplied files.
- Currency and Ads are single-cohort/single-campaign snapshots with no randomized
  variation — no cross-project causal claim is supported.
