"""Screening quality evaluation module for ANMEDSOS.

Evaluates semantic classifier predictions against historical human ground truth,
generates a stratified independent evaluation sample for audit, and compiles
error diagnostics, confusion matrices, and research limitations.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    DATA_INTERIM_DIR,
    MANUAL_LABELS_PATH,
    PROJECT_ROOT,
    REPORTS_DIR,
)

SEMANTIC_SCREENED_PATH = DATA_INTERIM_DIR / "semantic_screened.csv"
EVALUATION_SAMPLE_PATH = DATA_INTERIM_DIR / "evaluation_sample.csv"
SCREENING_EVALUATION_JSON = REPORTS_DIR / "screening_evaluation.json"


def generate_stratified_evaluation_sample(
    records: List[Dict[str, Any]],
    output_path: Path = EVALUATION_SAMPLE_PATH,
    sample_size: int = 150,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Generate an independent stratified sample across heuristic statuses, months, and query groups.
    
    CRITICAL: Never prefill human gold labels with model predictions.
    """
    rng = random.Random(seed)

    # Group by stratum: (final_status, month)
    strata: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        st = r.get("final_status") or r.get("auto_label") or "unknown"
        m = (r.get("timestamp_wib") or "")[:7] or "unknown"
        strata[(st, m)].append(r)

    sampled: List[Dict[str, Any]] = []
    # Allocate proportionally
    total = len(records)
    for (st, m), group in sorted(strata.items()):
        stratum_n = max(1, round(len(group) / total * sample_size))
        sample_k = min(len(group), stratum_n)
        chosen = rng.sample(group, sample_k)
        sampled.extend(chosen)

    # If over or under sample_size due to rounding, adjust deterministically
    if len(sampled) > sample_size:
        sampled = rng.sample(sampled, sample_size)

    # Sort deterministically
    sampled.sort(key=lambda x: (x.get("timestamp_wib", ""), x.get("post_id", "")))

    output_rows = []
    for r in sampled:
        output_rows.append({
            "post_id": r["post_id"],
            "timestamp_wib": r.get("timestamp_wib", ""),
            "text_raw": r["text_raw"],
            "query_groups": r.get("query_groups", ""),
            "matched_queries": r.get("matched_queries", ""),
            "heuristic_status": r.get("final_status", ""),
            "stratum_group": r.get("auto_reason", ""),
            # Blank fields for independent human annotation
            "annotator_relevance": "",
            "annotator_reason_code": "",
            "annotator_notes": "",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    return output_rows


def evaluate_against_manual_ground_truth(
    records: List[Dict[str, Any]],
    manual_labels_path: Path = MANUAL_LABELS_PATH,
) -> Dict[str, Any]:
    """Calculate confusion matrix, precision, recall, and error breakdown."""
    historical: Dict[str, str] = {}
    if manual_labels_path.exists():
        with manual_labels_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = row.get("post_id", "").strip()
                dec = row.get("decision", "").strip()
                if pid and dec:
                    historical[pid] = dec

    eval_set = [r for r in records if r["post_id"] in historical]
    tp, fp, tn, fn = 0, 0, 0, 0
    disagreements = []
    abstentions = 0

    for r in eval_set:
        gold = historical[r["post_id"]]
        pred = r.get("model_relevance", "review")

        if pred == "review":
            abstentions += 1

        if gold == "include":
            if pred == "include":
                tp += 1
            else:
                fn += 1
                disagreements.append({
                    "post_id": r["post_id"],
                    "gold": gold,
                    "pred": pred,
                    "reason_code": r.get("relevance_reason_code", ""),
                    "text_sample": r["text_raw"][:120],
                    "error_type": "False Negative (Under-inclusion)",
                })
        elif gold == "exclude":
            if pred == "include":
                fp += 1
                disagreements.append({
                    "post_id": r["post_id"],
                    "gold": gold,
                    "pred": pred,
                    "reason_code": r.get("relevance_reason_code", ""),
                    "text_sample": r["text_raw"][:120],
                    "error_type": "False Positive (Over-inclusion)",
                })
            else:
                tn += 1

    total_decided = tp + fp + tn + fn
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    acc = (tp + tn) / total_decided if total_decided > 0 else 0.0
    abstention_rate = abstentions / len(eval_set) if eval_set else 0.0

    return {
        "ground_truth_sample_size": len(eval_set),
        "contingency_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "accuracy": round(acc, 4),
            "abstention_rate": round(abstention_rate, 4),
        },
        "disagreements_count": len(disagreements),
        "disagreement_samples": disagreements[:10],
        "limitations": [
            "Historical manual labels (95 records) may have slight contamination from earlier rule tuning.",
            "Independent stratified sample (data/interim/evaluation_sample.csv) is provided for external validation.",
            "Quality gate target precision of 0.85 requires continuous refinement on domain-specific ambiguity.",
        ],
    }


def run_evaluation(
    screened_path: Path = SEMANTIC_SCREENED_PATH,
    manual_labels_path: Path = MANUAL_LABELS_PATH,
    sample_output_path: Path = EVALUATION_SAMPLE_PATH,
    report_output_path: Path = SCREENING_EVALUATION_JSON,
    sample_size: int = 150,
) -> Dict[str, Any]:
    """Execute complete screening evaluation and compile JSON report."""
    if not screened_path.exists():
        raise FileNotFoundError(f"Screened dataset not found: {screened_path}")

    with screened_path.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))

    # 1. Generate Stratified Independent Evaluation Sample
    sample = generate_stratified_evaluation_sample(
        records, output_path=sample_output_path, sample_size=sample_size, seed=42
    )

    # 2. Evaluate against ground truth
    eval_res = evaluate_against_manual_ground_truth(records, manual_labels_path)

    full_report = {
        "evaluation_title": "Semantic Relevance Classifier Evaluation",
        "total_records_screened": len(records),
        "independent_evaluation_sample_created": {
            "path": str(sample_output_path),
            "sample_size": len(sample),
            "sampling_method": "Stratified random sampling across heuristic statuses and calendar months (seed=42)",
            "gold_labels_prefilled": False,
        },
        "historical_ground_truth_benchmark": eval_res,
    }

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return full_report


def main():
    parser = argparse.ArgumentParser(description="Evaluate screening quality and generate stratified sample.")
    parser.add_argument("--input", type=Path, default=SEMANTIC_SCREENED_PATH)
    parser.add_argument("--labels", type=Path, default=MANUAL_LABELS_PATH)
    parser.add_argument("--sample-output", type=Path, default=EVALUATION_SAMPLE_PATH)
    parser.add_argument("--report-output", type=Path, default=SCREENING_EVALUATION_JSON)
    parser.add_argument("--sample-size", type=int, default=150)
    args = parser.parse_args()

    rep = run_evaluation(
        screened_path=args.input,
        manual_labels_path=args.labels,
        sample_output_path=args.sample_output,
        report_output_path=args.report_output,
        sample_size=args.sample_size,
    )
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
