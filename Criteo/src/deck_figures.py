"""Deck figures C1-C5 (+C4b) — stakeholder-grade, built ONLY from outputs/tables CSVs.

Design system (deck plan §3):
- blue #2a78d6 = New (most changed by the ad); orange #eb6834 = Today (most likely to visit);
  neutral gray #b4b2a9 = random / would-visit-anyway; text #52514e.
- one message per chart; no in-image titles; no top/right spines; light horizontal grid;
  direct labels, no legends; plain-language axes; per-1,000 units; thin gray CI whiskers;
  labels >= 14pt, annotations >= 16pt; 200 dpi; half-width 6.5x5in or full-width band.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\lucas\Desktop\ds project\Criteo")
TAB = ROOT / "outputs" / "tables"
DECK = ROOT / "outputs" / "deck"
DECK.mkdir(exist_ok=True)

BLUE = "#2a78d6"      # New: most changed by the ad
ORANGE = "#eb6834"    # Today: most likely to visit
GRAY = "#b4b2a9"      # random / would visit anyway
TEXT = "#52514e"
FOOTER = "Criteo public benchmark — compare approaches, don't project absolute volumes."

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": TEXT, "axes.labelcolor": TEXT,
    "xtick.color": TEXT, "ytick.color": TEXT,
    "text.color": TEXT, "font.size": 14,
    "axes.grid": True, "axes.grid.axis": "y", "grid.alpha": 0.35, "grid.linewidth": 0.7,
    "axes.axisbelow": True,
})


def footer(fig):
    fig.text(0.01, 0.008, FOOTER, fontsize=9, color="#8a8983", ha="left")


def strip_title(ax):
    ax.set_title("")


def save(fig, name):
    fig.savefig(DECK / f"{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


# ============================================================ C1 — the ads work
ate = pd.read_csv(TAB / "e3_ate.csv")
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
spec = [("visit", "Visits", "+27%"), ("conversion", "Purchases", "+59%")]
for ax, (outc, ylab, badge) in zip(axes, spec):
    r = ate[ate.outcome == outc].iloc[0]
    vals = [r.rate_control * 100, r.rate_treated * 100]
    bars = ax.bar(["Held out", "Ad-eligible"], vals,
                  width=0.55, color=[GRAY, TEXT])
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:.2f}%", (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=17, fontweight="bold",
                    xytext=(0, 14), textcoords="offset points")
    ax.annotate(badge, (0.5, 1.02), xycoords="axes fraction", ha="center",
                fontsize=20, fontweight="bold", color=TEXT,
                xytext=(0, 26), textcoords="offset points")
    ax.set_ylabel(f"Share of users who {'visit' if outc=='visit' else 'purchase'} (%)")
    ax.set_ylim(0, max(vals) * 1.45)
    ax.tick_params(axis="x", labelsize=14)
fig.subplots_adjust(wspace=0.3, bottom=0.3)
footer(fig)
save(fig, "c1_ads_work")

# ============================================================ C2 — anyway vs extra (slides 7 & 10)
sr = pd.read_csv(TAB / "e5_slice_rates.csv")
vr = sr[sr.outcome == "visit_rates"].set_index(["policy", "budget"])

def segments(policy, budget=0.10):
    r = vr.loc[(policy, budget)]
    anyway = r.rate_control_sel * 1000
    extra = (r.rate_treated_sel - r.rate_control_sel) * 1000
    return anyway, extra

# slide 7: today only
anyway_t, extra_t = segments("Response")
fig, ax = plt.subplots(figsize=(9.0, 3.6))
ax.barh(["Users on today's list"], [anyway_t], color=GRAY, label=None)
ax.barh(["Users on today's list"], [extra_t], left=[anyway_t], color=ORANGE)
ax.annotate(f"{anyway_t:.0f} would have visited anyway", (anyway_t / 2, 0), ha="center", va="center",
            fontsize=16, color="white", fontweight="bold")
ax.annotate(f"{extra_t:.0f} extra", (anyway_t + extra_t, 0), ha="left", va="center",
            fontsize=16, color=ORANGE, fontweight="bold", xytext=(10, 0), textcoords="offset points")
ax.annotate(f"{anyway_t + extra_t:.0f} total", (anyway_t + extra_t, 0.32), ha="left", va="center",
            fontsize=14, color=TEXT, xytext=(10, 0), textcoords="offset points")
ax.set_xlabel("Visits per 1,000 users shown an ad (top-10% list)", labelpad=28)
ax.set_xlim(0, (anyway_t + extra_t) * 1.32)
ax.set_ylim(-0.75, 0.55)
ax.grid(axis="x", visible=False); ax.grid(axis="y", visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0, labelsize=15)
fig.subplots_adjust(bottom=0.30)
footer(fig)
save(fig, "c2_slide7_today_only")

# slide 10: both approaches
anyway_n, extra_n = segments("Uplift")
fig, ax = plt.subplots(figsize=(9.5, 4.6))
rows = [("New: most changed\nby the ad", extra_n, anyway_n, BLUE),
        ("Today: most likely\nto visit", extra_t, anyway_t, ORANGE)]
ypos = [1, 0]
for (lab, extra, anyway, color), y in zip(rows, ypos):
    ax.barh([y], [anyway], color=GRAY)
    ax.barh([y], [extra], left=[anyway], color=color)
    ax.annotate(f"{anyway:.0f}", (anyway / 2, y), ha="center", va="center",
                fontsize=16, color="white", fontweight="bold")
    ax.annotate(f"{extra:.0f} extra", (anyway + extra, y), ha="left", va="center",
                fontsize=16, color=color, fontweight="bold", xytext=(10, 0), textcoords="offset points")
ax.set_yticks(ypos, [r[0] for r in rows])
ax.annotate("gray = would have visited anyway", (0.99, 1.06), xycoords="axes fraction",
            ha="right", fontsize=13, color=TEXT)
ax.set_xlabel("Visits per 1,000 users shown an ad (top-10% list)", labelpad=28)
ax.set_xlim(0, max(anyway_t + extra_t, anyway_n + extra_n) * 1.18)
ax.set_ylim(-0.75, 1.75)
ax.grid(visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0, labelsize=16)
fig.subplots_adjust(bottom=0.26)
footer(fig)
save(fig, "c2_slide10_both")

# ============================================================ C3 — concentration
dec = pd.read_csv(TAB / "e4_uplift_decile_validation.csv")
s_dec = dec[dec.learner == "S_learner"].sort_values("decile")
vals = (s_dec.obs_effect_pp * 10).to_numpy()  # pp -> per 1,000
avg_line = 10.36  # validation pooled ITT per 1,000 (1.036 pp)
fig, ax = plt.subplots(figsize=(9.0, 5.2))
colors = [GRAY] * 9 + [BLUE]
bars = ax.bar(np.arange(1, 11), vals, width=0.72, color=colors)
ax.axhline(avg_line, color=TEXT, ls="--", lw=1.3)
ax.annotate("average effect (10 per 1,000)", (0.01, avg_line), xycoords=("axes fraction", "data"),
            ha="left", va="bottom", fontsize=14, color=TEXT, xytext=(0, 3), textcoords="offset points")
top = vals[-1]
ax.annotate(f"Top 10%: +{top:.0f} per 1,000", (10, top), xytext=(0, 8), textcoords="offset points",
            ha="center", fontsize=16, fontweight="bold", color=BLUE)
for i, v in enumerate(vals[:-1]):
    ax.annotate(f"{v:+.0f}" if abs(v) >= 0.5 else "", (i + 1, max(v, 0)),
                ha="center", va="bottom", fontsize=12, color=TEXT, xytext=(0, 2), textcoords="offset points")
ax.set_xlabel("Ten equal groups of users, ranked by the ad's estimated effect on them (lowest → highest)")
ax.set_ylabel("Extra visits per 1,000\n(measured in the coin-flip groups)")
ax.set_xticks(np.arange(1, 11), [f"{i}" for i in range(1, 11)])
ax.set_ylim(min(0, vals.min()) - 3, top * 1.14)
ax.grid(axis="x", visible=False)
fig.subplots_adjust(bottom=0.28)
footer(fig)
save(fig, "c3_concentration")

# ============================================================ C4 — hero: extra visits by budget
pv = pd.read_csv(TAB / "e5_policy_value_visit.csv")
tc = pd.read_csv(TAB / "e5_policy_test_confirmation.csv")
budgets = [0.05, 0.10, 0.20]
resp = pv[pv.policy == "Response"].set_index("budget").loc[budgets]
upl = pv[pv.policy == "Uplift"].set_index("budget").loc[budgets]
rand = pv[pv.policy == "Random"].set_index("budget").loc[budgets].incremental_per_1000.mean()

fig, ax = plt.subplots(figsize=(9.5, 5.8))
x = np.arange(3)
w = 0.34
b_resp = ax.bar(x - w / 2, resp.incremental_per_1000, w, color=ORANGE,
                yerr=[resp.incremental_per_1000 - resp.ci_lo * 10, resp.ci_hi * 10 - resp.incremental_per_1000],
                error_kw=dict(ecolor="#9a9994", lw=1.2, capsize=4))
b_upl = ax.bar(x + w / 2, upl.incremental_per_1000, w, color=BLUE,
               yerr=[upl.incremental_per_1000 - upl.ci_lo * 10, upl.ci_hi * 10 - upl.incremental_per_1000],
               error_kw=dict(ecolor="#9a9994", lw=1.2, capsize=4))
for b, v in zip(b_resp, resp.incremental_per_1000):
    ax.annotate(f"{v:.0f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                fontsize=17, fontweight="bold", xytext=(0, 10), textcoords="offset points")
for b, v in zip(b_upl, upl.incremental_per_1000):
    ax.annotate(f"{v:.0f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                fontsize=17, fontweight="bold", xytext=(0, 10), textcoords="offset points")
ratios = ["1.7\u00d7", "1.4\u00d7", "tie"]
for i, (rtxt, rv, uv) in enumerate(zip(ratios, resp.incremental_per_1000, upl.incremental_per_1000)):
    top_y = max(rv, uv) + (upl.ci_hi.iloc[i] * 10 if uv >= rv else resp.ci_hi.iloc[i] * 10)
    ax.annotate(rtxt, (i, top_y), ha="center", va="bottom", fontsize=19, fontweight="bold",
                color=TEXT, xytext=(0, 30), textcoords="offset points")
ax.axhline(rand, color="#8a8983", lw=1.6)
ax.annotate(f"random ≈ {rand:.0f}", (2.52, rand), ha="right", va="bottom", fontsize=13.5,
            color="#8a8983", xytext=(0, 4), textcoords="offset points", bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
box = tc.set_index("policy").loc[["Uplift", "Response", "Random"]]
box_txt = (f"Confirmed on locked-away data (10% budget):\n"
           f"new {box.loc['Uplift','incremental_per_1000']:.0f} vs today {box.loc['Response','incremental_per_1000']:.0f} "
           f"vs random {box.loc['Random','incremental_per_1000']:.0f} per 1,000")
ax.text(0.985, 0.965, box_txt, transform=ax.transAxes, ha="right", va="top", fontsize=13.5,
        bbox=dict(boxstyle="round,pad=0.45", fc="#f4f3ef", ec="#c9c8c2", lw=1))
fig.text(0.055, 0.985, "New: most changed by the ad", ha="left", va="top",
         fontsize=15, fontweight="bold", color=BLUE)
fig.text(0.055, 0.935, "Today: most likely to visit", ha="left", va="top",
         fontsize=15, fontweight="bold", color=ORANGE)
ax.set_xticks(x, ["5%", "10%", "20%"])
ax.set_xlabel("Share of users shown an ad (budget)")
ax.set_ylabel("Extra visits per 1,000\nusers shown an ad")
ax.set_ylim(0, (upl.incremental_per_1000 + upl.ci_hi * 10).max() * 1.42)
ax.set_xlim(-0.55, 2.55)
ax.grid(axis="x", visible=False)
fig.subplots_adjust(bottom=0.22, top=0.85)
footer(fig)
save(fig, "c4_hero_extra_visits")

# ============================================================ C4b — capture share (optional panel)
cap_b = pv[pv.budget == 0.10].set_index("policy")
fig, ax = plt.subplots(figsize=(9.0, 3.2))
rows = [("New: most changed by the ad", cap_b.loc["Uplift", "capture_share"], BLUE),
        ("Today: most likely to visit", cap_b.loc["Response", "capture_share"], ORANGE)]
for (lab, v, color), y in zip(rows, [1, 0]):
    ax.barh([y], [v], color=color, height=0.55)
    ax.annotate(f"{v:.0f}% of all extra visits", (v, y), ha="left", va="center",
                fontsize=16, fontweight="bold", xytext=(8, 0), textcoords="offset points", color=TEXT)
ax.set_yticks([1, 0], [r[0] for r in rows])
ax.axvline(10, color="#8a8983", ls=":", lw=1.6)
ax.annotate("random = 10%", (10, 1.5), ha="center", fontsize=13, color="#8a8983")
ax.set_xlim(0, 100)
ax.set_ylim(-0.55, 1.62)
ax.set_xlabel("Share of all extra visits the ad creates, caught by the list (top-10% budget)", labelpad=6)
ax.grid(visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0, labelsize=15)
fig.subplots_adjust(bottom=0.31)
footer(fig)
save(fig, "c4b_capture_share")

# ============================================================ C5 — same chart, purchases
pc = pd.read_csv(TAB / "e5_policy_value_conversion.csv")
resp_c = pc[pc.policy == "Response"].set_index("budget").loc[budgets]
upl_c = pc[pc.policy == "Uplift"].set_index("budget").loc[budgets]
rand_c = pc[pc.policy == "Random"].set_index("budget").loc[budgets].incremental_per_1000.mean()

fig, ax = plt.subplots(figsize=(9.5, 5.6))
b_resp = ax.bar(x - w / 2, resp_c.incremental_per_1000, w, color=ORANGE,
                yerr=[resp_c.incremental_per_1000 - resp_c.wald_lo * 10, resp_c.wald_hi * 10 - resp_c.incremental_per_1000],
                error_kw=dict(ecolor="#9a9994", lw=1.2, capsize=4))
b_upl = ax.bar(x + w / 2, upl_c.incremental_per_1000, w, color=BLUE,
               yerr=[upl_c.incremental_per_1000 - upl_c.wald_lo * 10, upl_c.wald_hi * 10 - upl_c.incremental_per_1000],
               error_kw=dict(ecolor="#9a9994", lw=1.2, capsize=4))
for b, v in zip(b_resp, resp_c.incremental_per_1000):
    ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                fontsize=17, fontweight="bold", xytext=(0, 8), textcoords="offset points")
for b, v in zip(b_upl, upl_c.incremental_per_1000):
    ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom",
                fontsize=17, fontweight="bold", xytext=(0, 8), textcoords="offset points")
badges = ["today wins", "tie", "tie"]
for i, (bt, rv, uv) in enumerate(zip(badges, resp_c.incremental_per_1000, upl_c.incremental_per_1000)):
    top_y = max(rv, uv)
    hi_ci = (resp_c.wald_hi.iloc[i] if rv >= uv else upl_c.wald_hi.iloc[i]) * 10
    ax.annotate(bt, (i, hi_ci), ha="center", va="bottom", fontsize=18, fontweight="bold",
                color=TEXT, xytext=(0, 22), textcoords="offset points")
ax.axhline(rand_c, color="#8a8983", lw=1.6)
ax.annotate(f"random ≈ {rand_c:.1f}", (2.52, rand_c), ha="right", va="bottom", fontsize=13.5,
            color="#8a8983", xytext=(0, 4), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
ax.set_xticks(x, ["5%", "10%", "20%"])
ax.set_xlabel("Share of users shown an ad (budget)")
ax.set_ylabel("Extra purchases per 1,000\nusers shown an ad")
ax.set_ylim(0, resp_c.wald_hi.max() * 10 * 1.32)
ax.grid(axis="x", visible=False)
fig.text(0.055, 0.985, "New: most changed by the ad", ha="left", va="top",
         fontsize=15, fontweight="bold", color=BLUE)
fig.text(0.055, 0.935, "Today: most likely to visit", ha="left", va="top",
         fontsize=15, fontweight="bold", color=ORANGE)
fig.subplots_adjust(bottom=0.22, top=0.85)
footer(fig)
save(fig, "c5_purchases")

print("ALL DECK FIGURES DONE")
