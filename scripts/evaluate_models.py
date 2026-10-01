"""Run two (or more) models on the same weeks and score them.

  python scripts/evaluate_models.py --models "$MODEL_A" "$MODEL_B" --weeks all
"""
import argparse
import os

import pandas as pd
from _common import ARTIFACTS

import generate_briefs
from mia.evaluation import score, summarise, to_markdown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=[m for m in (os.getenv("MODEL_A"), os.getenv("MODEL_B")) if m])
    ap.add_argument("--weeks", default="all")
    args = ap.parse_args()
    if len(args.models) < 1:
        raise SystemExit("Pass --models A B or set MODEL_A / MODEL_B")
    rows = []
    for model in args.models:
        print(f"\n=== {model} ===")
        for result, payload in generate_briefs.run(model, args.weeks):
            rows.append(score(result, payload))
    out = ARTIFACTS / "eval"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "model_eval_runs.csv", index=False)
    summary = summarise(rows)
    (out / "model_eval.md").write_text(to_markdown(summary))
    pd.set_option("display.width", 220)
    print("\n" + summary.to_string(index=False))
    print(f"\nSaved artifacts/eval/model_eval.md and model_eval_runs.csv")


if __name__ == "__main__":
    main()
