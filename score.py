"""Recalculate single-stream 4090 rates from the accompanying request receipts."""
import csv
from pathlib import Path
from statistics import median

ROOT = Path(__file__).parent
with (ROOT / "requests.csv").open() as stream:
    rows = list(csv.DictReader(stream))
FRESH = {"creation", "swift_creation"}
COPY = {"swift_edit"}
SELECTED = {"rewrite"}

def sample(run, cohorts, blocks, arm):
    selected = {}
    for row in rows:
        if row["run"] != run or row["arm"] != arm or row["cohort"] not in cohorts:
            continue
        if int(row["block"]) > blocks:
            continue
        key = (row["block"], row["case"], row["rep"])
        if key in selected:
            raise ValueError(f"Duplicate request {key} for {run}/{arm}")
        selected[key] = row
    return selected

def stats(records):
    values = list(records.values())
    seconds = sum(float(r["decode_s"]) for r in values)
    tokens = sum(int(r["n"]) - 1 for r in values)
    return tokens / seconds, median(float(r["file_s"]) for r in values)

def compare(label, before, after, cohorts, blocks, before_arm="auto"):
    a = sample(before, cohorts, blocks, before_arm)
    b = sample(after, cohorts, blocks, "auto")
    if not a or a.keys() != b.keys():
        raise ValueError(f"Unpaired rows for {label}")
    same = sum((a[k]["token_hash"], a[k]["file_hash"]) ==
               (b[k]["token_hash"], b[k]["file_hash"]) for k in a)
    passed = sum(r["passed"] == "True" for r in b.values())
    rate_a, time_a = stats(a)
    rate_b, time_b = stats(b)
    print(f"{label}: {rate_a:.2f} -> {rate_b:.2f} tok/s; median file "
          f"{time_a:.3f} -> {time_b:.3f} s; {same}/{len(b)} matched, {passed} passed")

if __name__ == "__main__":
    compare("Automatic copy path vs neural", "confirm-combined-01", "confirm-combined-01", COPY, 8, "reference")
    compare("191-proposal source graph", "five-stock-02", "five-graph-01", COPY, 2)
    compare("Fused source scoring added to graph", "five-graph-01", "five-edit-combo-01", COPY, 2)
    compare("8,704-row DSpark shortlist", "improve-stock-01", "screen-short-bank-01", FRESH, 4)
    compare("Retiled verifier on repository creation", "five-stock-02", "five-moe-01", {"creation"}, 3)
    for run in dict.fromkeys(r["run"] for r in rows if r["run"].startswith(("confirm-combined", "reddit-"))):
        for name, cohorts in [("fresh", FRESH), ("copy", COPY), ("selected", SELECTED),
                              ("broad rewrite", {"fallback"}), ("short rewrite", {"short_rewrite"})]:
            compare(f"{run} {name}", "improve-stock-01", run, cohorts, 8)
