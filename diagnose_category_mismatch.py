"""
Diagnostic: find labeled rows where the model's category disagrees with
ground truth, even though root_cause was scored as perfect. Run this
after harness.py has produced results_optimized_raw.csv.

Usage:
    python diagnose_category_mismatch.py --data track_a_logs.xlsx \
        --results results_optimized_raw.csv
"""
import argparse
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--data", default="track_a_logs.xlsx")
parser.add_argument("--results", default="results_optimized_raw.csv")
args = parser.parse_args()

df = pd.read_excel(args.data)
results = pd.read_csv(args.results)

labeled = df[df["is_labeled"] == "yes"].merge(
    results[["event_id", "category", "root_cause", "remediation", "confidence"]],
    on="event_id", how="left", suffixes=("_gt", "_pred")
)

mismatches = labeled[labeled["gt_category"] != labeled["category"]]

print(f"Labeled rows: {len(labeled)}")
print(f"Category mismatches: {len(mismatches)}\n")

if len(mismatches) == 0:
    print("No mismatches found — category F1 issue may be a scoring bug, "
          "not a model behavior issue. Re-check compute_metrics.")
else:
    cols = ["message", "gt_category", "category", "gt_root_cause",
            "root_cause", "confidence"]
    print(mismatches[cols].to_string(index=False))
    print("\nIf gt_root_cause == root_cause but gt_category != category "
          "on the same row, the model is getting the root cause right "
          "while assigning an inconsistent category — meaning the "
          "response_format schema doesn't enforce the category<->root_cause "
          "pairing your instructions describe. Fix: either add the pairing "
          "as a hard constraint the harness re-derives from root_cause "
          "(ignore the model's own category field entirely and look it up "
          "from root_cause instead, since that mapping is deterministic), "
          "or tighten the prompt further and re-test.")
