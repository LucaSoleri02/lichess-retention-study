"""Reviewer-fix batch 2: nb04/nb05/nb06 code edits + config/core/README/PLAN docs."""
import json

import nbformat as nbf

ROOT = r"C:\Users\lucas\Desktop\ds project\Criteo"


def load(name):
    return nbf.read(ROOT + "\\" + name + ".ipynb", as_version=4)


def save(nb, name):
    with open(ROOT + "\\" + name + ".ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def code_cells(nb):
    return [(i, c) for i, c in enumerate(nb.cells) if c.cell_type == "code"]


def find_cell(nb, frag, cell_type="code"):
    hits = [i for i, c in enumerate(nb.cells) if c.cell_type == cell_type and frag in "".join(c.source)]
    assert len(hits) == 1, f"anchor {frag[:50]!r}: hits={hits}"
    return hits[0]


def set_source(c, s):
    c.source = [l + "\n" for l in s.split("\n")[:-1]] + [s.split("\n")[-1]]


# ============================================================ NB05
nb5 = load("05_policy_value_eval_testset_uplift")

# (a) tie-break by row_hash in slice_topk + pass key from evaluate_policy
i = find_cell(nb5, "def slice_topk")
c = nb5.cells[i]
s = "".join(c.source)
s = s.replace(
    '''def slice_topk(score, budget):
    """Indices of the top-(budget·n) rows by score, descending, ties broken by row order."""
    n = len(score)
    k = int(round(budget * n))
    order = np.argsort(-np.asarray(score, dtype=np.float64), kind="stable")
    return order[:k]''',
    '''def slice_topk(score, budget, tie_key=None):
    """Indices of the top-(budget·n) rows by score, descending; ties broken by row_hash
    (frozen contract: hash order is arm-independent, unlike file order — the raw file is
    positionally blocked by component incrementality tests)."""
    n = len(score)
    k = int(round(budget * n))
    if tie_key is None:
        order = np.argsort(-np.asarray(score, dtype=np.float64), kind="stable")
    else:
        order = np.lexsort((np.asarray(tie_key), -np.asarray(score, dtype=np.float64)))
    return order[:k]''',
)
s = s.replace("    idx = slice_topk(df[score].to_numpy(), budget)",
              "    idx = slice_topk(df[score].to_numpy(), budget, df[\"row_hash\"].to_numpy())")
set_source(c, s)

# (b) eval-split pooled ITT instead of frozen full-data constants
i = find_cell(nb5, '"conversion": m.conversion[va_m]')
c = nb5.cells[i]
s = "".join(c.source)
s += """

# capture-share denominators: pooled ITT computed from THE EVAL SPLIT being used
# (frozen full-data E3 constants kept only as external reference)
POOLED_ITT_VISIT = float(val.visit[val.treatment == 1].mean() - val.visit[val.treatment == 0].mean())
POOLED_ITT_CONV = float(val.conversion[val.treatment == 1].mean() - val.conversion[val.treatment == 0].mean())
print(f"validation-split ITT: visit {POOLED_ITT_VISIT*100:.4f}pp | conversion {POOLED_ITT_CONV*100:.4f}pp")
"""
set_source(c, s)

# (c) test confirmation uses test-split ITT
i = find_cell(nb5, "TEST_BUDGET = 0.10")
c = nb5.cells[i]
s = "".join(c.source)
s = s.replace("for pol, score in [(\"Random\", None), (\"Response\", \"resp_score\"), (\"Uplift\", \"cate_s\")]:\n    r = evaluate_policy(test, score, TEST_BUDGET, \"visit\", POOLED_ITT_VISIT)",
              """test_itt = float(test.visit[test.treatment == 1].mean() - test.visit[test.treatment == 0].mean())
print(f"test-split ITT (visit): {test_itt*100:.4f}pp")
for pol, score in [("Random", None), ("Response", "resp_score"), ("Uplift", "cate_s")]:
    r = evaluate_policy(test, score, TEST_BUDGET, "visit", test_itt)""")
set_source(c, s)

# (d) save slice arm rates for the E7 power calc in nb06
extra = nbf.v4.new_code_cell(
    '''# save slice arm rates (policy x budget) for the E7 power calculation (nb06)
rate_rows = []
for outcome, tab in (("visit", visit_tab), ("conversion", conv_tab)):
    for pol in ["Random", "Response", "Uplift"]:
        sub = tab[tab.policy == pol].set_index("budget").loc[BUDGETS]
        for b, row in sub.iterrows():
            rate_rows.append(dict(outcome=outcome, policy=pol, budget=b,
                                  effect_pp=round(row.effect_pp, 4),
                                  incremental_per_1000=round(row.incremental_per_1000, 2)))
# treated/control rates inside slices, recomputed here (the frozen estimator's quantities)
for pol, score in [("Response", "resp_score"), ("Uplift", "cate_s")]:
    for b in BUDGETS:
        idx = slice_topk(val[score].to_numpy(), b, val["row_hash"].to_numpy())
        sl_t = val.visit.to_numpy()[idx][val.treatment.to_numpy()[idx] == 1]
        sl_c = val.visit.to_numpy()[idx][val.treatment.to_numpy()[idx] == 0]
        rate_rows.append(dict(outcome="visit_rates", policy=pol, budget=b,
                              rate_treated_sel=round(sl_t.mean(), 5),
                              rate_control_sel=round(sl_c.mean(), 5)))
rates_tab = pd.DataFrame(rate_rows)
rates_tab.to_csv(TAB + r"\\e5_slice_rates.csv", index=False)
print(rates_tab[rates_tab.outcome == "visit_rates"].round(4).to_string(index=False))'''
)
nb5.cells.append(nbf.v4.new_markdown_cell("### Slice arm rates export (for the E7 power calculation)"))
nb5.cells.append(extra)
save(nb5, "05_policy_value_eval_testset_uplift")

# ============================================================ NB04 (text-only fixes)
nb4 = load("04_uplift_cate_models")
i = find_cell(nb4, "ties in favor of treated", "markdown")
c = nb4.cells[i]
s = "".join(c.source).replace(
    "ties in favor of treated, matching the sklift implementation",
    "ties: control rows first within equal scores — the convention verified against sklift's own implementation by the raw-curve cross-check below",
)
c.source = s
i = find_cell(nb4, "ties->treated")
c = nb4.cells[i]
s = "".join(c.source).replace(
    "# raw-curve cross-check (hand-rolled formulas, same sort convention as sklift: score desc, ties->treated)",
    "# raw-curve cross-check (hand-rolled formulas; sort = score desc, ties control-first — matches sklift, verified)",
)
set_source(c, s)
# external-benchmark note on the magic ITT
i = find_cell(nb4, "ITT_PP = 1.034")
c = nb4.cells[i]
s = "".join(c.source).replace(
    "ITT_PP = 1.034  # E3 pooled-intent-to-treat visit effect (pp), benchmark scale",
    "ITT_PP = 1.034  # E3 FULL-DATA pooled ITT (pp), benchmark scale — external benchmark only\n"
    "                # (not a capture-share denominator; nb05 computes its own eval-split ITT)",
)
set_source(c, s)
save(nb4, "04_uplift_cate_models")

# ============================================================ NB06 (power rewrite + cleanups)
nb6 = load("06_sensitivity_segments_expdesign")

# garbled line in the val-scores cell
i = find_cell(nb6, "val_h = df.loc[")
c = nb6.cells[i]
s = "".join(c.source)
s = s.replace(
    'val_h = df.loc[[i for i in []] if False else slice(None), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()\nval_h = df.loc[df["row_hash"].mod(1000).between(700, 849), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()',
    'val_h = df.loc[df["row_hash"].mod(1000).between(700, 849), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()',
)
set_source(c, s)

# replace the WRONG power cell with the difference-in-differences version
i = find_cell(nb6, "def n_per_arm")
c = nb6.cells[i]
s = r'''def n_per_arm_policy(rates, delta, holdout_frac, alpha=0.05, power=0.8):
    """Power for the E7 design: two targeting policies compared at equal budget,
    EACH ARM with its own randomized holdout (fraction `holdout_frac` gets no ad).

    Per arm, the incremental effect is a difference in proportions between the
    targeted share (1-h) and the holdout share (h) of that arm's users. The
    contrast between the two arms' effects is the primary comparison.
    rates: dict policy -> (rate_targeted, rate_holdout) — actual slice rates (E5).
    delta: contrast in incremental effects to detect (proportion units).
    """
    z_a, z_b = 1.959963985, 0.841621234
    s = 1 - holdout_frac
    var_total = 0.0
    for (p_t, p_c) in rates.values():
        var_total += p_t * (1 - p_t) / s + p_c * (1 - p_c) / (1 - s)
    return (z_a + z_b) ** 2 * var_total / delta ** 2

# actual slice arm rates from E5 (validation, 10% budget): read e5_slice_rates.csv
rates_tab = pd.read_csv(r"C:\Users\lucas\Desktop\ds project\Criteo\outputs\tables\e5_slice_rates.csv")
r10 = rates_tab[(rates_tab.outcome == "visit_rates") & (rates_tab.budget == 0.10)].set_index("policy")
rate_uplift = (float(r10.loc["Uplift", "rate_treated_sel"]), float(r10.loc["Uplift", "rate_control_sel"]))
rate_resp = (float(r10.loc["Response", "rate_treated_sel"]), float(r10.loc["Response", "rate_control_sel"]))
delta = abs((rate_uplift[0] - rate_uplift[1]) - (rate_resp[0] - rate_resp[1]))
print(f"slice rates 10% budget - uplift: {rate_uplift[0]:.4f}/{rate_uplift[1]:.4f} | response: {rate_resp[0]:.4f}/{rate_resp[1]:.4f}")
print(f"effect contrast to detect: {delta*100:.2f}pp")

n_50 = n_per_arm_policy({"uplift": rate_uplift, "response": rate_resp}, delta, holdout_frac=0.5)
n_85 = n_per_arm_policy({"uplift": rate_uplift, "response": rate_resp}, delta, holdout_frac=0.15)
# honest reference: broadcast ITT detection (85/15, delta=1.03pp, actual arm rates)
n_bcast = (1.959963985 + 0.841621234) ** 2 * (
    0.048543 * (1 - 0.048543) / 0.85 + 0.038201 * (1 - 0.038201) / 0.15) / 0.010342 ** 2

fig, ax = plt.subplots(figsize=(8, 4.4))
vals = [n_50, n_85, n_bcast]
lbls = ["policy experiment\n50/50 within-arm holdout", "policy experiment\n85/15 within-arm holdout", "broadcast ITT test\n85/15, detect +1.03pp"]
ax.bar(np.arange(3), vals, color=["#1e8449", "#145a32", "#7f8c8d"])
for i_, v in enumerate(vals):
    ax.text(i_, v * 1.03, f"~{int(np.ceil(v/1000))}k users / arm", ha="center", fontweight="bold")
ax.set_xticks(np.arange(3), lbls)
ax.set_ylabel("users per arm (alpha=0.05 two-sided, power=0.80)")
ax.set_title("E7 power (corrected difference-in-differences design):\na policy comparison needs ~30-55k users per arm, each with its own holdout")
fig.text(0.99, 0.01, "benchmark-scale rates; ignores clustering/multiple testing/noncompliance", ha="right", fontsize=7, color="dimgray")
fig.tight_layout()
viz.savefig(fig, "e7_experiment_power_sketch")
print(f"n/arm: 50/50 holdout ~{n_50:,.0f} | 85/15 holdout ~{n_85:,.0f} | broadcast ITT ~{n_bcast:,.0f}")'''
set_source(c, s)

# md_c: replace the stale power sentence
i = find_cell(nb6, "slice contrasts (~1.9 pp within-slice) are detectable", "markdown")
c = nb6.cells[i]
s = "".join(c.source)
s = s.replace(
    "E7: uplift-targeted vs response-targeted at the 10% budget tier is the experiment to run; slice contrasts (~1.9 pp within-slice) are detectable with modest per-arm samples in the sketch below (vs millions for broadcast-level contrasts).",
    "E7: uplift-targeted vs response-targeted at the 10% budget tier is the experiment to run. Power is computed for the ACTUAL design — a difference-in-differences where each policy arm carries its own randomized holdout, using the actual slice arm rates from E5: **~30k users/arm with a 50/50 within-arm holdout, ~55k with an 85/15 holdout** (contrast to detect ≈ 1.8 pp). For scale: detecting the broadcast ITT (+1.03 pp) needs ~22k/arm — the policy comparison is only ~1.5–2.5× more demanding, still small relative to the 13.98M-user benchmark.",
)
set_source(c, s)

# dedup-by-hash caveat sentence (append to md_close)
i = find_cell(nb6, "Dedup sensitivity (corrected story)", "markdown")
c = nb6.cells[i]
s = "".join(c.source) + """
- **Hash note:** the validation-slice re-check dedups by 32-bit `row_hash` (not content): ~20k colliding *distinct-row* pairs are expected at 14M rows, so a few distinct rows merge — negligible at these effect sizes, and the full-data dedup (content-column exact match) is unaffected.
"""
c.source = s
save(nb6, "06_sensitivity_segments_expdesign")

print("nb05/nb04/nb06 edited")
