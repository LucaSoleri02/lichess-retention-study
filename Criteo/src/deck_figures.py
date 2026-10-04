"""Slide-ready figures for the Criteo deck (see Criteo/DECK_PLAN.md, section 3).

Built from the result tables in outputs/tables/ only, so it runs on any machine
without the 14M-row parquet:

    pip install -r Criteo/requirements-deck.txt
    python Criteo/src/deck_figures.py            # -> Criteo/outputs/deck/*.png|svg
    python Criteo/src/deck_figures.py --tables X --out Y

Charts (C*) are Altair / Vega-Lite rendered by vl-convert (no browser needed).
Diagrams (D*) are hand-built SVG, rasterised by vl-convert as well.
Every figure is written as a 2x PNG (paste into slides) and an SVG (scalable).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

import altair as alt
import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TABLES = ROOT / "outputs" / "tables"
DEFAULT_OUT = ROOT / "outputs" / "deck"

# ---------------------------------------------------------------- design tokens
FONT = "Inter, Helvetica Neue, Segoe UI, Arial, sans-serif"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8880"
RULE = "#c9c7c0"
GRID = "#ebeae6"
NEUTRAL = "#b4b2a9"
BLUE = "#2a78d6"    # new: most changed by the ad (validated CVD-safe pair with orange)
ORANGE = "#eb6834"  # today: most likely to visit
BLUE_TINT = "#e4eefb"
ORANGE_TINT = "#fdeae2"
GRAY_TINT = "#f2f1ed"

POLICY_LABEL = {
    "Response": "Today: most likely to visit",
    "Uplift": "New: most changed by the ad",
    "Random": "Random",
}
POLICY_COLOR = {"Response": ORANGE, "Uplift": BLUE, "Random": NEUTRAL}
POLICY_ORDER = ["Response", "Uplift"]

FOOTNOTE = "Criteo public benchmark: compare approaches, don't project absolute volumes."
Z_95 = 1.959963984540054
Z_99 = 2.5758293035489004
Z_80_POWER = 0.841621233572914

FULL_W = 1100  # chart canvas widths in px; 2x PNG export -> ~2200 px for a 16:9 slide
HALF_W = 520
PLOT_W = FULL_W - 260  # grouped-bar plot width; leaves room for the outside label

# ---------------------------------------------------------------- loading
REQUIRED = {
    "e3_ate.csv": ["outcome", "n_control", "n_treated", "ev_control", "ev_treated", "rel_lift"],
    "e5_policy_value_visit.csv": ["policy", "budget", "incremental_per_1000", "ci_lo", "ci_hi", "capture_share"],
    "e5_policy_value_conversion.csv": ["policy", "budget", "incremental_per_1000", "ci_lo", "ci_hi"],
    "e5_policy_test_confirmation.csv": ["policy", "budget", "incremental_per_1000"],
    "e5_slice_rates.csv": ["outcome", "policy", "budget", "rate_treated_sel", "rate_control_sel"],
    "e4_uplift_decile_validation.csv": ["learner", "decile", "n", "obs_effect_pp"],
}


def load_tables(tables_dir: Path) -> dict[str, pd.DataFrame]:
    """Read every input CSV and fail loudly if a file or column is missing."""
    tables_dir = Path(tables_dir)
    out = {}
    for name, cols in REQUIRED.items():
        path = tables_dir / name
        if not path.exists():
            raise FileNotFoundError(f"missing input table: {path}")
        df = pd.read_csv(path)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(f"{name}: missing columns {missing}")
        out[name] = df
    return out


# ---------------------------------------------------------------- tidy data
def _pct_label(x: float) -> str:
    return f"{x:.2%}"


def ate_frame(ate: pd.DataFrame) -> pd.DataFrame:
    """One row per (outcome, group): event rate by randomised arm, from raw counts."""
    names = {"visit": "Visits", "conversion": "Purchases"}
    rows = []
    for _, r in ate.iterrows():
        lift = f"{r['rel_lift']:+.0%} with ads"
        for group, ev, n in (("Held out (no ads)", r["ev_control"], r["n_control"]),
                             ("Could be shown ads", r["ev_treated"], r["n_treated"])):
            rate = ev / n
            rows.append({"outcome": names.get(r["outcome"], r["outcome"]), "group": group,
                         "rate": rate, "rate_label": _pct_label(rate), "lift_label": lift})
    return pd.DataFrame(rows)


def anyway_extra_frame(slice_rates: pd.DataFrame, budget: float = 0.10,
                       policies: list[str] = POLICY_ORDER) -> pd.DataFrame:
    """Visits per 1,000 targeted split into 'would have visited anyway' and 'extra'.

    anyway = visit rate of the held-out users inside the slice;
    extra = treated rate - held-out rate (the slice's causal effect).
    """
    r = slice_rates[(slice_rates["outcome"] == "visit_rates") &
                    (slice_rates["budget"].round(4) == round(budget, 4))].set_index("policy")
    rows = []
    for p in policies:
        if p not in r.index:
            raise ValueError(f"e5_slice_rates.csv has no visit_rates row for {p} @ {budget}")
        anyway = 1000 * float(r.loc[p, "rate_control_sel"])
        total = 1000 * float(r.loc[p, "rate_treated_sel"])
        rows.append({"policy": p, "policy_label": POLICY_LABEL[p],
                     "anyway": anyway, "extra": total - anyway, "total": total})
    return pd.DataFrame(rows)


def decile_frame(deciles: pd.DataFrame, learner: str = "S_learner") -> pd.DataFrame:
    """Measured extra visits per 1,000 by group of users ranked on predicted effect."""
    d = deciles[deciles["learner"] == learner].sort_values("decile").copy()
    if d.empty:
        raise ValueError(f"no rows for learner {learner!r} in decile table")
    d["per_1000"] = d["obs_effect_pp"] * 10
    d["is_top"] = d["decile"] == d["decile"].max()
    return d[["decile", "n", "per_1000", "is_top"]].reset_index(drop=True)


def policy_frame(pv: pd.DataFrame) -> pd.DataFrame:
    """Per policy x budget: per-1,000 effect with its 95% CI (CSV CIs are in pp)."""
    d = pv.copy()
    d["per_1000"] = d["incremental_per_1000"]
    d["lo"] = d["ci_lo"] * 10
    d["hi"] = d["ci_hi"] * 10
    d["budget_label"] = d["budget"].map(lambda b: f"{b:.0%}")
    d["policy_label"] = d["policy"].map(POLICY_LABEL)
    d["value_label"] = d["per_1000"].map(lambda v: f"{v:.0f}" if v >= 10 else f"{v:.1f}")
    return d[["policy", "policy_label", "budget", "budget_label", "per_1000", "lo", "hi", "value_label"]]


def compare_badge(new: float, new_lo: float, new_hi: float,
                  today: float, today_lo: float, today_hi: float) -> tuple[str, str]:
    """Badge text + winner for one budget: '1.7x' / 'Today ahead' / 'Tie' / 'Today 1.4x'.

    Ratio badge only when the gap clears 99%; between 95% and 99% the badge just says
    who is ahead, so a borderline result is never shown as a confident multiple.

    Two-sided z-test on the difference, SEs backed out of the 95% CIs and treated as
    independent. The two slices share users, which makes the true SE of the difference
    smaller, so 'Tie' here is a conservative call.
    """
    se = math.hypot(new_hi - new_lo, today_hi - today_lo) / (2 * Z_95)
    z = (new - today) / se if se > 0 else math.copysign(math.inf, new - today)
    if abs(z) < Z_95:
        return "Tie", "tie"
    if abs(z) < Z_99:
        return ("New ahead", "new") if new > today else ("Today ahead", "today")
    if new > today:
        return (f"{new / today:.1f}\u00d7" if today > 0 else "New wins"), "new"
    return (f"Today {today / new:.1f}\u00d7" if new > 0 else "Today wins"), "today"


def badge_frame(pf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for b, g in pf.groupby("budget", sort=True):
        g = g.set_index("policy")
        if not {"Uplift", "Response"} <= set(g.index):
            continue
        u, r = g.loc["Uplift"], g.loc["Response"]
        text, winner = compare_badge(u.per_1000, u.lo, u.hi, r.per_1000, r.lo, r.hi)
        rows.append({"budget": b, "budget_label": u.budget_label, "badge": text,
                     "winner": winner, "y": max(u.hi, r.hi)})
    return pd.DataFrame(rows)


def confirmation_note(test: pd.DataFrame) -> str:
    t = test.set_index("policy")["incremental_per_1000"]
    b = float(test["budget"].iloc[0])
    return (f"Confirmed on locked-away data ({b:.0%} budget): new {t['Uplift']:.0f} vs "
            f"today {t['Response']:.0f} vs random {t['Random']:.0f} extra visits per 1,000.")


def users_per_group(slice_rates: pd.DataFrame, budget: float = 0.10, holdout: float = 0.5,
                    alpha_z: float = Z_95, power_z: float = Z_80_POWER) -> float:
    """Users per group for the head-to-head test (same formula as notebook 06, E7).

    Each group (today's list / new list) keeps a random `holdout` share unexposed;
    the test compares the two groups' extra-visit rates (a difference of differences).
    """
    r = slice_rates[(slice_rates["outcome"] == "visit_rates") &
                    (slice_rates["budget"].round(4) == round(budget, 4))].set_index("policy")
    shown = 1 - holdout
    var, effects = 0.0, []
    for p in POLICY_ORDER:
        p_t, p_c = float(r.loc[p, "rate_treated_sel"]), float(r.loc[p, "rate_control_sel"])
        var += p_t * (1 - p_t) / shown + p_c * (1 - p_c) / holdout
        effects.append(p_t - p_c)
    delta = abs(effects[1] - effects[0])
    return (alpha_z + power_z) ** 2 * var / delta ** 2


# ---------------------------------------------------------------- Altair theme
@alt.theme.register("criteo_deck", enable=False)
def _deck_theme() -> alt.theme.ThemeConfig:
    axis = {"labelFont": FONT, "titleFont": FONT, "labelFontSize": 18, "titleFontSize": 18,
            "labelColor": INK_2, "titleColor": INK_2, "titleFontWeight": "normal",
            "domainColor": RULE, "tickColor": RULE, "gridColor": GRID,
            "labelPadding": 8, "titlePadding": 14}
    return {
        "config": {
            "font": FONT,
            "background": "white",
            "padding": {"left": 12, "right": 24, "top": 16, "bottom": 12},
            "view": {"stroke": None},
            "axis": axis,
            "axisX": {"grid": False},
            "axisY": {"domain": False, "ticks": False},
            "legend": {"labelFont": FONT, "labelFontSize": 18, "labelColor": INK,
                       "symbolType": "square", "symbolSize": 260, "orient": "top",
                       "direction": "horizontal", "title": None, "columnPadding": 28,
                       "labelLimit": 0, "padding": 4},
            "text": {"font": FONT, "fontSize": 18, "color": INK},
            "title": {"font": FONT, "color": INK, "anchor": "start"},
            "concat": {"spacing": 56},
        }
    }


def _footer(text: str | list[str], sub: str | None = None) -> alt.Title:
    return alt.Title(text=text, subtitle=sub or "", orient="bottom", anchor="start",
                     fontSize=17, fontWeight="normal", color=INK_2,
                     subtitleFontSize=15, subtitleColor=MUTED, offset=22, subtitlePadding=6)


# ---------------------------------------------------------------- charts
def chart_ads_work(af: pd.DataFrame) -> alt.HConcatChart:
    """C1: event rate by randomised arm, one panel per outcome (independent y)."""
    panels = []
    for outcome in ["Visits", "Purchases"]:
        d = af[af["outcome"] == outcome]
        if d.empty:
            continue
        top = d["rate"].max() * 1.22
        base = alt.Chart(d).encode(
            x=alt.X("group:N", sort=["Held out (no ads)", "Could be shown ads"], title=None,
                    axis=alt.Axis(labelAngle=0, labelFontSize=18, labelColor=INK, domain=True)),
            y=alt.Y("rate:Q", axis=None, scale=alt.Scale(domain=[0, top])),
        )
        bars = base.mark_bar(cornerRadiusEnd=5, size=110).encode(
            color=alt.Color("group:N", legend=None,
                            scale=alt.Scale(domain=["Held out (no ads)", "Could be shown ads"],
                                            range=[NEUTRAL, INK_2])))
        labels = base.mark_text(dy=-16, fontSize=22, fontWeight="bold").encode(text="rate_label:N")
        panels.append((bars + labels).properties(
            width=HALF_W - 80, height=360,
            title=alt.Title(outcome, subtitle=d["lift_label"].iloc[0], fontSize=24,
                            fontWeight="bold", color=INK, subtitleFontSize=30,
                            subtitleFontWeight="bold", subtitleColor=INK,
                            subtitlePadding=6, offset=18)))
    return alt.hconcat(*panels).resolve_scale(y="independent").properties(
        title=_footer("Share of users who visited / purchased, by randomly assigned group.", FOOTNOTE))


def chart_anyway_extra(df: pd.DataFrame) -> alt.LayerChart:
    """C2: visits per 1,000 targeted, stacked as 'would have visited anyway' + 'extra'."""
    d = df.copy()
    d["fill"] = d["policy"].map(POLICY_COLOR)
    d["anyway_label"] = d["anyway"].map(lambda v: f"{v:.0f} would have visited anyway")
    d["extra_label"] = d["extra"].map(lambda v: f"+{v:.0f} extra")
    d["total_label"] = d["total"].map(lambda v: f"{v:.0f} visits in total")
    order = [POLICY_LABEL[p] for p in POLICY_ORDER if p in set(d["policy"])]
    x_max = d["total"].max() * 1.32
    y = alt.Y("policy_label:N", sort=order, title=None,
              axis=alt.Axis(labelFontSize=20, labelColor=INK, labelLimit=420, labelPadding=14))
    base = alt.Chart(d).encode(y=y)
    x_axis = alt.Axis(grid=True, tickCount=5, title="Visits per 1,000 users shown an ad")
    anyway = base.mark_bar(color=NEUTRAL, height=64, stroke="white", strokeWidth=2).encode(
        x=alt.X("zero:Q", scale=alt.Scale(domain=[0, x_max], nice=False), axis=x_axis),
        x2="anyway:Q").transform_calculate(zero="0")
    extra = base.mark_bar(height=64, stroke="white", strokeWidth=2,
                          cornerRadiusTopRight=5, cornerRadiusBottomRight=5).encode(
        x="anyway:Q", x2="total:Q", color=alt.Color("fill:N", scale=None))
    anyway_txt = base.mark_text(align="left", dx=16, fontSize=19, color=INK).encode(
        x=alt.datum(0), text="anyway_label:N")
    extra_txt = base.mark_text(align="left", dx=14, dy=-11, fontSize=24, fontWeight="bold").encode(
        x="total:Q", text="extra_label:N")
    total_txt = base.mark_text(align="left", dx=14, dy=15, fontSize=16, color=MUTED).encode(
        x="total:Q", text="total_label:N")
    return (anyway + extra + anyway_txt + extra_txt + total_txt).properties(
        width=FULL_W - 380, height=110 * len(d),
        title=_footer("Top 10% of users picked by each approach. 'Anyway' = visit rate of the "
                      "randomly held-out users on the same list.", FOOTNOTE))


def chart_concentration(dd: pd.DataFrame) -> alt.LayerChart:
    """C3: measured extra visits per 1,000 for 10 equal groups ranked by predicted effect."""
    d = dd.copy()
    n_groups = int(d["decile"].max())
    d["group"] = d["decile"].astype(int)
    d["top_label"] = d.apply(lambda r: f"+{r.per_1000:.0f} extra visits per 1,000" if r.is_top else "",
                             axis=1)
    rest_max = d.loc[~d["is_top"], "per_1000"].max()
    first, last = int(d["group"].min()), n_groups
    x = alt.X("group:O", title="Users split into 10 equal groups, ranked by estimated ad effect",
              axis=alt.Axis(labelAngle=0,
                            labelExpr=(f"datum.value == '{first}' ? 'Lowest 10%' : "
                                       f"datum.value == '{last}' ? 'Top 10%' : ''"),
                            labelFontSize=18, labelColor=INK, ticks=False),
              scale=alt.Scale(paddingInner=0.18))
    y = alt.Y("per_1000:Q", title="Extra visits per 1,000 users",
              scale=alt.Scale(domain=[min(0, d["per_1000"].min() * 1.3),
                                      d["per_1000"].max() * 1.18], nice=False),
              axis=alt.Axis(tickCount=4))
    base = alt.Chart(d).encode(x=x, y=y)
    bars = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.condition("datum.is_top", alt.value(BLUE), alt.value(NEUTRAL)))
    top_txt = base.mark_text(dy=-16, fontSize=22, fontWeight="bold", align="right", dx=40).encode(
        text="top_label:N")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=RULE, strokeWidth=1.5).encode(y="y:Q")
    rest = alt.Chart(pd.DataFrame({"t": [f"The other 90%: under {math.ceil(rest_max)} per 1,000"]})).mark_text(
        fontSize=20, color=INK_2, align="center").encode(
        text="t:N", x=alt.value((FULL_W - 120) * 0.45), y=alt.datum(rest_max + 9))
    return (zero + bars + top_txt + rest).properties(
        width=FULL_W - 120, height=420,
        title=_footer("Measured in the randomised groups, on users the model never trained on.", FOOTNOTE))


def chart_policy_by_budget(pf: pd.DataFrame, *, y_title: str, note: str | None = None,
                           random_label: str = "Random") -> alt.LayerChart:
    """C4 / C5: extra outcomes per 1,000 targeted, today vs new, at each budget."""
    d = pf[pf["policy"].isin(POLICY_ORDER)].copy()
    rnd = pf.loc[pf["policy"] == "Random", "per_1000"]
    badges = badge_frame(pf)
    y_top = max(d["hi"].max(), 1e-9) * 1.28
    badges["y"] = badges["y"] + y_top * 0.10
    budget_order = [f"{b:.0%}" for b in sorted(d["budget"].unique())]
    labels_order = [POLICY_LABEL[p] for p in POLICY_ORDER]

    x = alt.X("budget_label:N", sort=budget_order, title="Budget: share of users shown an ad",
              axis=alt.Axis(labelAngle=0, labelFontSize=20, labelColor=INK),
              scale=alt.Scale(paddingInner=0.32, paddingOuter=0.2))
    x_off = alt.XOffset("policy_label:N", sort=labels_order, scale=alt.Scale(paddingInner=0.06))
    y = alt.Y("per_1000:Q", title=y_title,
              scale=alt.Scale(domain=[0, y_top], nice=False), axis=alt.Axis(tickCount=5))
    base = alt.Chart(d).encode(x=x, xOffset=x_off)

    bars = base.mark_bar(cornerRadiusEnd=5).encode(
        y=y,
        color=alt.Color("policy_label:N", sort=labels_order,
                        scale=alt.Scale(domain=labels_order,
                                        range=[POLICY_COLOR[p] for p in POLICY_ORDER])))
    whiskers = base.mark_rule(color=INK_2, strokeWidth=1.5, opacity=0.7).encode(y="lo:Q", y2="hi:Q")
    values = base.mark_text(dy=-14, fontSize=20, fontWeight="bold").encode(y="hi:Q", text="value_label:N")
    badge = alt.Chart(badges).mark_text(fontSize=26, fontWeight="bold", color=INK).encode(
        x=alt.X("budget_label:N", sort=budget_order), y="y:Q", text="badge:N")
    layers = [bars, whiskers, values, badge]
    if not rnd.empty:
        r = pd.DataFrame({"y": [rnd.mean()],
                          "t": [f"{random_label}\n\u2248 {rnd.mean():.0f} per 1,000"]})
        layers.insert(0, alt.Chart(r).mark_rule(color=MUTED, strokeDash=[7, 5], strokeWidth=2).encode(y="y:Q"))
        layers.append(alt.Chart(r).mark_text(align="left", dx=10, fontSize=16, color=INK_2,
                                             lineBreak="\n").encode(
            y="y:Q", x=alt.value(PLOT_W), text="t:N"))
    footer = _footer(note, FOOTNOTE) if note else _footer(FOOTNOTE)
    return alt.layer(*layers).properties(width=PLOT_W, height=440, title=footer,
                                         padding={"left": 12, "right": 150, "top": 16, "bottom": 12})


def chart_capture_share(pv: pd.DataFrame, budget: float = 0.10) -> alt.LayerChart:
    """C4b: share of all extra visits created by the ad that each list catches."""
    d = pv[(pv["budget"].round(4) == round(budget, 4)) & pv["policy"].isin(POLICY_ORDER)].copy()
    d["policy_label"] = d["policy"].map(POLICY_LABEL)
    d["share"] = d["capture_share"] / 100
    d["label"] = d["share"].map(lambda v: f"{v:.0%}")
    order = [POLICY_LABEL[p] for p in POLICY_ORDER]
    base = alt.Chart(d).encode(
        y=alt.Y("policy_label:N", sort=order, title=None,
                axis=alt.Axis(labelFontSize=20, labelColor=INK, labelLimit=420)))
    bars = base.mark_bar(height=56, cornerRadiusEnd=5).encode(
        x=alt.X("share:Q", scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%", grid=True, tickCount=5,
                              title=f"Share of all extra visits caught, at a {budget:.0%} budget")),
        color=alt.Color("policy:N", scale=alt.Scale(domain=POLICY_ORDER,
                                                    range=[POLICY_COLOR[p] for p in POLICY_ORDER]),
                        legend=None))
    txt = base.mark_text(align="left", dx=12, fontSize=24, fontWeight="bold").encode(
        x="share:Q", text="label:N")
    ref = pd.DataFrame({"x": [budget], "t": [f"Random \u2248 {budget:.0%}"]})
    rule = alt.Chart(ref).mark_rule(color=MUTED, strokeDash=[7, 5], strokeWidth=2).encode(x="x:Q")
    rule_txt = alt.Chart(ref).mark_text(align="left", dx=8, fontSize=16, color=INK_2).encode(
        x="x:Q", y=alt.value(-10), text="t:N")
    return (rule + bars + txt + rule_txt).properties(
        width=FULL_W - 420, height=190, title=_footer(FOOTNOTE))


# ---------------------------------------------------------------- SVG diagrams
class Svg:
    """Minimal SVG canvas: rounded boxes, multi-line text, arrows."""

    def __init__(self, width: int, height: int):
        self.w, self.h, self.parts = width, height, []

    def rect(self, x, y, w, h, fill="white", stroke=None, sw: float = 2, rx=14, dash=None):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        s += f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}/>')

    def circle(self, cx, cy, r, fill="white", stroke=None, sw: float = 2):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}/>')

    def text(self, x, y, lines, size=20, weight="normal", fill=INK, anchor="start", lh=1.3,
             rotate=None):
        lines = [lines] if isinstance(lines, str) else lines
        tr = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        spans = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else size * lh:.1f}">{escape(t)}</tspan>'
            for i, t in enumerate(lines))
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{tr}>{spans}</text>')

    def arrow(self, x1, y1, x2, y2, color=INK_2, sw=2.5):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                          f'stroke-width="{sw}" marker-end="url(#head)"/>')

    def path(self, d, color=INK_2, sw=2.5, fill="none"):
        self.parts.append(f'<path d="{d}" stroke="{color}" stroke-width="{sw}" fill="{fill}" '
                          f'stroke-linecap="round" stroke-linejoin="round"/>')

    def to_string(self) -> str:
        defs = ('<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK_2}"/>'
                "</marker></defs>")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">{defs}'
                '<rect width="100%" height="100%" fill="white"/>' + "".join(self.parts) + "</svg>")


def diagram_user_types() -> Svg:
    """D1: the four kinds of users (2x2)."""
    s = Svg(1300, 600)
    x0, y0, w, h, gap = 250, 130, 330, 210, 16
    s.text(x0 + w + gap / 2, 48, "Without the ad, would they visit?", 22, "bold", anchor="middle")
    s.text(x0 + w / 2, 104, "No", 20, fill=INK_2, anchor="middle")
    s.text(x0 + w * 1.5 + gap, 104, "Yes", 20, fill=INK_2, anchor="middle")
    s.text(70, y0 + h + gap / 2, "With the ad, would they visit?", 22, "bold", anchor="middle", rotate=-90)
    s.text(x0 - 24, y0 + h / 2 + 7, "Yes", 20, fill=INK_2, anchor="end")
    s.text(x0 - 24, y0 + h * 1.5 + gap + 7, "No", 20, fill=INK_2, anchor="end")
    cells = [
        (0, 0, "Persuadables", ["Visit only because", "they saw the ad"], "Worth paying for",
         BLUE_TINT, BLUE),
        (0, 1, "Sure things", ["Visit either way"], "Spend wasted", ORANGE_TINT, ORANGE),
        (1, 0, "Lost causes", ["Never visit"], "Spend wasted", GRAY_TINT, RULE),
        (1, 1, "Do-not-disturbs", ["The ad puts them off"], "Spend backfires", GRAY_TINT, RULE),
    ]
    for r, c, title, desc, verdict, fill, stroke in cells:
        x, y = x0 + c * (w + gap), y0 + r * (h + gap)
        s.rect(x, y, w, h, fill, stroke, sw=3 if stroke in (BLUE, ORANGE) else 2)
        s.text(x + 26, y + 50, title, 28, "bold")
        s.text(x + 26, y + 90, desc, 20, fill=INK_2)
        s.text(x + 26, y + h - 26, f"\u2192 {verdict}", 20, "bold")
    bx = x0 + 2 * w + gap + 26
    s.path(f"M{bx},{y0 + 4} h14 v{h - 8} h-14", sw=3)
    s.path(f"M{bx + 14},{y0 + h / 2} h14", sw=3)
    s.text(bx + 44, y0 + h / 2 - 22, ["Today's targeting picks", "from this row, and can't",
                                      "tell the two apart"], 21, fill=INK)
    return s


def diagram_experiment(af: pd.DataFrame) -> Svg:
    """D2: the coin-flip experiment behind the data."""
    v = af[af["outcome"] == "Visits"].set_index("group")
    rate_t, rate_c = v.loc["Could be shown ads", "rate"], v.loc["Held out (no ads)", "rate"]
    s = Svg(1400, 520)
    s.rect(40, 200, 250, 120, GRAY_TINT, RULE)
    s.text(165, 250, "14 million", 30, "bold", anchor="middle")
    s.text(165, 284, "users", 22, fill=INK_2, anchor="middle")
    s.arrow(292, 260, 372, 260)
    s.circle(440, 260, 64, "white", INK_2, sw=2.5)
    s.text(440, 254, "Coin", 22, "bold", anchor="middle")
    s.text(440, 282, "Flip", 22, "bold", anchor="middle")
    s.arrow(500, 236, 592, 150)
    s.arrow(500, 284, 592, 370)
    s.rect(600, 70, 430, 150, "white", INK_2, sw=2.5)
    s.text(628, 118, "85% could be shown ads", 24, "bold")
    s.text(628, 162, f"Visited: {rate_t:.2%}", 22, fill=INK_2)
    s.rect(600, 300, 430, 150, GRAY_TINT, RULE)
    s.text(628, 348, "15% held out, never shown ads", 24, "bold")
    s.text(628, 392, f"Visited: {rate_c:.2%}", 22, fill=INK_2)
    s.arrow(1032, 145, 1072, 220)
    s.arrow(1032, 375, 1072, 300)
    s.rect(1080, 170, 300, 180, BLUE_TINT, BLUE, sw=3)
    s.text(1104, 214, ["The difference is", "what the ads cause"], 21, fill=INK)
    s.text(1104, 290, f"+{(rate_t - rate_c) * 100:.2f} points", 26, "bold")
    s.text(1104, 324, f"{rate_t / rate_c - 1:+.0%} more visits", 20, fill=INK_2)
    s.text(40, 490, "The coin flip makes the two groups alike in every way except the ads, "
                    "so the gap in visits is caused by the ads.", 19, fill=INK_2)
    return s


def diagram_method() -> Svg:
    """D3: how the per-user ad effect is estimated and fairly judged."""
    s = Svg(1400, 560)
    steps = [
        ("Coin-flip data", ["14M users; who could see", "ads was decided at random"]),
        ("Learn visit chance", ["for every user, with the", "ad and without it"]),
        ("Estimate ad effect", ["the difference between", "the two chances"]),
        ("Rank and target", ["show ads to the users", "the ad changes most"]),
    ]
    w, gap, x0, y0, h = 290, 50, 45, 40, 200
    for i, (title, desc) in enumerate(steps):
        x = x0 + i * (w + gap)
        last = i == len(steps) - 1
        s.rect(x, y0, w, h, BLUE_TINT if last else "white", BLUE if last else INK_2,
               sw=3 if last else 2)
        s.circle(x + 40, y0 + 46, 20, BLUE if last else INK_2)
        s.text(x + 40, y0 + 53, str(i + 1), 20, "bold", fill="white", anchor="middle")
        s.text(x + 72, y0 + 54, title, 23, "bold")
        s.text(x + 26, y0 + 112, desc, 19, fill=INK_2)
        if not last:
            s.arrow(x + w + 6, y0 + h / 2, x + w + gap - 6, y0 + h / 2)
    s.text(x0, 320, "How the users were used, so the results are fair:", 21, "bold")
    total = 4 * w + 3 * gap
    segs = [(0.70, "70%", ["Learn"], NEUTRAL, INK),
            (0.15, "15%", ["Compare", "approaches"], BLUE_TINT, INK),
            (0.15, "15%", ["Final check,", "opened once"], INK_2, "white")]
    x = x0
    for frac, pct, label, fill, ink in segs:
        sw = total * frac
        s.rect(x + 1, 344, sw - 2, 64, fill, rx=8)
        s.text(x + sw / 2, 384, pct, 22, "bold", fill=ink, anchor="middle")
        s.text(x + sw / 2, 444, label, 19, fill=INK_2, anchor="middle")
        x += sw
    s.text(x0, 530, "The model never sees the users it is judged on; the final 15% "
                    "was opened only once, after every choice was frozen.", 19, fill=INK_2)
    return s


def diagram_test_design(n_per_group: float) -> Svg:
    """D4: the proposed head-to-head experiment."""
    n_label = f"\u2248{round(n_per_group, -3):,.0f} users"
    s = Svg(1400, 640)
    s.rect(480, 24, 440, 86, GRAY_TINT, RULE)
    s.text(700, 76, "Users eligible for the campaign", 23, "bold", anchor="middle")
    s.arrow(620, 112, 380, 168)
    s.arrow(780, 112, 1020, 168)
    groups = [(60, "A", "Today's list", "top 10% most likely to visit", ORANGE),
              (740, "B", "New list", "top 10% most changed by the ad", BLUE)]
    for x, letter, name, desc, color in groups:
        w = 600
        s.rect(x, 176, w, 270, "white", color, sw=3)
        s.text(x + 30, 222, f"Group {letter}: {name}", 25, "bold")
        s.text(x + 30, 256, f"{desc} \u00b7 {n_label}", 19, fill=INK_2)
        bw = (w - 60) / 2
        s.rect(x + 30, 284, bw - 2, 60, color, rx=8)
        s.text(x + 30 + bw / 2, 321, "50% shown the ad", 19, "bold", fill="white", anchor="middle")
        s.rect(x + 32 + bw, 284, bw - 2, 60, GRAY_TINT, RULE, rx=8)
        s.text(x + 30 + bw * 1.5, 321, "50% held out", 19, "bold", anchor="middle")
        s.text(x + 30, 390, "Extra visits per 1,000 =", 19, fill=INK_2)
        s.text(x + 30, 418, "visits (shown) \u2212 visits (held out)", 19, "bold")
    s.rect(60, 486, 1280, 120, BLUE_TINT, BLUE, sw=2)
    s.text(90, 532, "Decision rule, written down before launch", 22, "bold")
    s.text(90, 570, "Switch to the new list if Group B's extra visits per 1,000 beat Group A's "
                    "by the agreed margin. Track purchases as a guardrail.", 19, fill=INK)
    return s


# ---------------------------------------------------------------- export
def save_chart(chart: alt.TopLevelMixin, out_dir: Path, name: str, scale: float = 2) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{name}.png", out_dir / f"{name}.svg"]
    with alt.theme.enable("criteo_deck"):
        chart.save(paths[0], scale_factor=scale)
        chart.save(paths[1])
    return paths


def save_svg(svg: Svg, out_dir: Path, name: str, scale: float = 2) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = svg.to_string()
    svg_path, png_path = out_dir / f"{name}.svg", out_dir / f"{name}.png"
    svg_path.write_text(text, encoding="utf-8")
    png_path.write_bytes(vlc.svg_to_png(text, scale=scale))
    return [png_path, svg_path]


def build_all(tables_dir: Path = DEFAULT_TABLES, out_dir: Path = DEFAULT_OUT) -> list[Path]:
    """Render every deck figure; returns the written paths."""
    t = load_tables(tables_dir)
    out_dir = Path(out_dir)
    af = ate_frame(t["e3_ate.csv"])
    rates = t["e5_slice_rates.csv"]
    visit = policy_frame(t["e5_policy_value_visit.csv"])
    conv = policy_frame(t["e5_policy_value_conversion.csv"])

    written = []
    written += save_chart(chart_ads_work(af), out_dir, "c1_ads_work")
    written += save_chart(chart_anyway_extra(anyway_extra_frame(rates, policies=["Response"])),
                          out_dir, "c2a_anyway_vs_extra_today")
    written += save_chart(chart_anyway_extra(anyway_extra_frame(rates)),
                          out_dir, "c2b_anyway_vs_extra_both")
    written += save_chart(chart_concentration(decile_frame(t["e4_uplift_decile_validation.csv"])),
                          out_dir, "c3_effect_concentration")
    written += save_chart(chart_policy_by_budget(
        visit,
        y_title="Extra visits per 1,000 users shown an ad",
        note=confirmation_note(t["e5_policy_test_confirmation.csv"])), out_dir, "c4_extra_visits_by_budget")
    written += save_chart(chart_capture_share(t["e5_policy_value_visit.csv"]),
                          out_dir, "c4b_capture_share")
    written += save_chart(chart_policy_by_budget(
        conv,
        y_title="Extra purchases per 1,000 users shown an ad",
        note="Same users and lists as the visits chart, scored on purchases instead."),
        out_dir, "c5_extra_purchases_by_budget")
    written += save_svg(diagram_user_types(), out_dir, "d1_user_types")
    written += save_svg(diagram_experiment(af), out_dir, "d2_experiment")
    written += save_svg(diagram_method(), out_dir, "d3_method")
    written += save_svg(diagram_test_design(users_per_group(rates)), out_dir, "d4_test_design")
    return written


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Render the Criteo deck figures from outputs/tables.")
    ap.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    for p in build_all(args.tables, args.out):
        print(p)


if __name__ == "__main__":
    main()
