"""End-to-end pipeline runner: P1 data acquisition → P2 cohort & labels
→ P2b data quality → P3 model experiments. Each step is idempotent
(checks for output files and skips when present), so a restart only
finishes the incomplete portion.

Usage: python run_pipeline.py [--skip model] [--only step]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

STEPS = ["dump", "cohort", "features", "data", "model"]
BASELINE_PACK = PROJECT_ROOT / "harness_runs" / "baseline_pack.json"


def run(module: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"STEP: src.{module}")
    print(f"{'=' * 60}")
    subprocess.run([sys.executable, "-m", f"src.{module}"], check=True, cwd=ROOT)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--skip", nargs="*", default=[], choices=STEPS)
    p.add_argument("--only", default=None, choices=STEPS + [None])
    args = p.parse_args()

    todo = [s for s in STEPS if s not in args.skip]
    if args.only:
        todo = [args.only]

    for step in todo:
        if step == "model":
            # model harness: ensure data exists first
            for dep in ("cohort", "features"):
                if dep not in [s for s in todo]:
                    if dep == "cohort" and not __import__("src.config", fromlist=["COHORT_PARQUET"]).COHORT_PARQUET.exists():
                        print(f"(dep missing: running src.cohort first)")
                        run("cohort")
                    if dep == "features" and not __import__("src.config", fromlist=["USER_WINDOW_PARQUET"]).USER_WINDOW_PARQUET.exists():
                        print(f"(dep missing: running src.features first)")
                        run("features")
            subprocess.run([sys.executable, "run_harness.py", "batch", str(BASELINE_PACK)], check=True, cwd=ROOT)
            continue
        run(step)

    print(f"\n{'=' * 60}")
    print("Pipeline complete.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
