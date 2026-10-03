"""Notebook 06 driver: dedup sensitivity + E6 segments + E7 design/impact (part 1: compute)."""
import json
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import config as C
import core

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

SEED = 42
t00 = time.time()

df = pd.read_parquet(C.INTERIM / "criteo_uplift_v2_hashed.parquet")
print("loaded", df.shape)

# full ITT
full_itt = {}
for y in (C.VISIT, C.CONVERSION):
    y1 = df[y][df[C.TREATMENT] == 1].to_numpy()
    y0 = df[y][df[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    full_itt[y] = dict(rate_t=round(y1.mean() * 100, 4), rate_c=round(y0.mean() * 100, 4),
                       ate_pp=round(ate * 100, 4), lo=round(lo * 100, 4), hi=round(hi * 100, 4))
print("full ITT:", json.dumps(full_itt))

# dedup
dd = df.drop_duplicates(subset=C.FEATURES + [C.TREATMENT, C.VISIT, C.CONVERSION, C.EXPOSURE], keep="first")
print("deduped:", dd.shape, round(time.time() - t00, 1))

dd_itt = {}
for y in (C.VISIT, C.CONVERSION):
    y1 = dd[y][dd[C.TREATMENT] == 1].to_numpy()
    y0 = dd[y][dd[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    dd_itt[y] = dict(rate_t=round(y1.mean() * 100, 4), rate_c=round(y0.mean() * 100, 4),
                     ate_pp=round(ate * 100, 4), lo=round(lo * 100, 4), hi=round(hi * 100, 4))
print("dedup ITT:", json.dumps(dd_itt))
print("dedup treat ratio:", round(dd[C.TREATMENT].mean(), 5))
del y1, y0

# deduped ITT table save
rows = []
for y in (C.VISIT, C.CONVERSION):
    rows.append(dict(outcome=y, version="full", rate_treated_pp=full_itt[y]["rate_t"],
                     rate_control_pp=full_itt[y]["rate_c"], itt_pp=full_itt[y]["ate_pp"],
                     ci_lo_pp=full_itt[y]["lo"], ci_hi_pp=full_itt[y]["hi"]))
    rows.append(dict(outcome=y, version="dedup", rate_treated_pp=dd_itt[y]["rate_t"],
                     rate_control_pp=dd_itt[y]["rate_c"], itt_pp=dd_itt[y]["ate_pp"],
                     ci_lo_pp=dd_itt[y]["lo"], ci_hi_pp=dd_itt[y]["hi"]))
pd.DataFrame(rows).to_csv(C.TABLES / "e6_dedup_itt_sensitivity.csv", index=False)

# dedup validation rows
val_h = df.loc[core.is_val(df), ["row_hash", C.TREATMENT, C.VISIT, C.CONVERSION]].copy()
val_dedup = val_h.drop_duplicates(subset=["row_hash"], keep="first")
print("validation dedup rows:", val_dedup.shape)

# E4 scores: join by row_hash (dedup by hash first)
val_scores = pd.read_parquet(C.ROOT / "data" / "interim" / "e4_val_uplift_scores.parquet")
vs = val_scores.drop_duplicates(subset=["row_hash"], keep="first")
mg = val_dedup.merge(vs[["row_hash", "cate_s"]], on="row_hash", how="inner")
print("merged cate:", mg.shape)
del val_scores, vs

# response scores: refit E2 recipe on train treated
tr_mask = (df["row_hash"] % 1000 < 700) & (df[C.TREATMENT] == 1)
X_cols = C.FEATURES
t0 = time.time()
model_resp = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05,
                                            early_stopping=True, random_state=42)
model_resp.fit(df.loc[tr_mask, X_cols].astype("float32"), df.loc[tr_mask, C.VISIT])
print("resp refit", round(time.time() - t0, 1), "s")

vmask = df["row_hash"].isin(val_dedup["row_hash"]) & (df["row_hash"] % 1000 >= 700) & (df["row_hash"] % 1000 < 850)
valX = df.loc[vmask, X_cols].astype("float32")
resp_pred = model_resp.predict_proba(valX)[:, 1]
vm = df.loc[vmask, ["row_hash"]].copy()
vm["resp_score"] = resp_pred
vm = vm.drop_duplicates("row_hash")
mg = mg.merge(vm, on="row_hash", how="inner")
print("merged resp:", mg.shape, "total elapsed", round(time.time() - t00, 1))
del df, dd, valX, resp_pred, vm, val_h

# top-10% slices + segments (B) in one pass
df2 = mg
N = len(df2)
pooled_itt_pp = 1.0342  # E3 full-data reference for capture share on validation scale

seg_bounds = [1.0, 0.90, 0.75, 0.50, 0.25, 0.0]
seg_labels = ["Top 10%", "10-25%", "25-50%", "50-75%", "Bottom 25%"]

seg_rows = []
for i, lab in enumerate(seg_labels):
    hi_b, lo_b = seg_bounds[i], seg_bounds[i + 1]
    hi_cut = df2["cate_s"].quantile(hi_b)
    lo_cut = df2["cate_s"].quantile(lo_b)
    sl = df2[(df2["cate_s"] >= lo_cut) & (df2["cate_s"] <= hi_cut)]
    y1 = sl[C.VISIT][sl[C.TREATMENT] == 1].to_numpy()
    y0 = sl[C.VISIT][sl[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    seg_rows.append(dict(segment=lab, pred_cate_pp=round(sl["cate_s"].mean() * 100, 3),
                         obs_effect_pp=round(ate * 100, 3), ci_lo_pp=round(lo * 100, 3),
                         ci_hi_pp=round(hi * 100, 3), n=len(sl), n_t=len(y1), n_c=len(y0)))
    print(lab, seg_rows[-1])
segdf = pd.DataFrame(seg_rows)
segdf.to_csv(C.TABLES / "e6_uplift_segments.csv", index=False)
print(segdf)

# dedup top-10% policy slices
pol_rows = []
for pol, col in (("Uplift", "cate_s"), ("Response", "resp_score")):
    thr = df2[col].quantile(0.90)
    sl = df2[df2[col] >= thr]
    y1 = sl[C.VISIT][sl[C.TREATMENT] == 1].to_numpy()
    y0 = sl[C.VISIT][sl[C.TREATMENT] == 0].to_numpy()
    ate, lo, hi, se = core.ate_bootstrap(y1, y0, n_boot=2000, seed=SEED)
    pol_rows.append(dict(policy=pol, budget=0.10, n_sel=len(sl),
                         effect_pp=round(ate * 100, 4), ci_lo=round(lo * 100, 4), ci_hi=round(hi * 100, 4),
                         inc_per_1000=round(ate * 1000, 2)))
    print(pol, "dedup top10%:", round(ate * 100, 3), f"[{lo*100:.2f},{hi*100:.2f}]")
poldf = pd.DataFrame(pol_rows)
poldf.to_csv(C.TABLES / "e6_dedup_policy_sensitivity.csv", index=False)
print(poldf)
print("ALL DONE", round(time.time() - t00, 1), "s")
