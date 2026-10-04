"""Shared config for the Criteo uplift case study."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PARQUET = DATA / "interim" / "criteo_uplift_v2_hashed.parquet"  # 13.98M rows + row_hash
CSV_GZ = ROOT / "criteo-research-uplift-v2.1.csv.gz"
INTERIM = DATA / "interim"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"
RESULTS = ROOT / "results"

FEATURES = [f"f{i}" for i in range(12)]
TREATMENT = "treatment"
VISIT = "visit"
CONVERSION = "conversion"
EXPOSURE = "exposure"

# treatment share P(T=1) in the benchmark (~0.85); used for OOF/IPW diagnostics
P_TREAT = 0.85

# budgets for policy evaluation
BUDGETS = [0.05, 0.10, 0.20]

# deterministic row-hash: md5(full row tuple) % 1000
# [0,700) train | [700,850) validation | [850,1000) test
# full row incl. outcomes+exposure so exact duplicates share a split
TRAIN_MAX, VAL_MAX = 700, 850
N_FOLDS = 5

FIG_DPI = 150
