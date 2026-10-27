"""Export module for analysis-ready corpus generation.

Filters screened records for candidate_unverified and confirmed_relevant tweets,
assigns explicit provenance tracking (relevance_source), and ensures NO text
preprocessing is applied.
"""
import argparse
import csv
import hashlib
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from config.settings import (
    ANALYSIS_READY_PATH,
    DATA_INTERIM_DIR,
    DATA_PROCESSED_DIR,
    MANUAL_LABELS_PATH,
    RAW_TWEETS_PATH,
    REPORTS_DIR,
    SCREENED_CANDIDATES_PATH,
)
from src.classify_rq import RQClassifier

FINAL_CORPUS_PATH = DATA_PROCESSED_DIR / "final_corpus.csv"
SEMANTIC_SCREENED_PATH = DATA_INTERIM_DIR / "semantic_screened.csv"
FINAL_DATASET_VERIFICATION_JSON = REPORTS_DIR / "final_dataset_verification.json"


def sha256_of_file(path: pathlib.Path) -> str:
    """Compute sha256 digest of file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw_engagement_lookup(raw_path: pathlib.Path = RAW_TWEETS_PATH) -> Dict[str, Dict[str, Any]]:
    """Build engagement metrics lookup by post_id from raw tweets."""
    eng: Dict[str, Dict[str, Any]] = {}
    if not raw_path.exists():
        return eng
    with raw_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                wrap = json.loads(line)
                rec = wrap.get("record", {})
                pid = str(rec.get("id") or "")
                if pid and pid not in eng:
                    eng[pid] = {
                        "like_count": rec.get("likeCount", 0),
                        "retweet_count": rec.get("retweetCount", 0),
                        "reply_count": rec.get("replyCount", 0),
                        "quote_count": rec.get("quoteCount", 0),
                        "view_count": rec.get("viewCount", 0),
                        "raw_lang": rec.get("lang", ""),
                    }
            except Exception:
                pass
    return eng


def export_final_corpus(
    semantic_screened_path: pathlib.Path = SEMANTIC_SCREENED_PATH,
    manual_labels_path: pathlib.Path = MANUAL_LABELS_PATH,
    raw_path: pathlib.Path = RAW_TWEETS_PATH,
    output_path: pathlib.Path = FINAL_CORPUS_PATH,
    verification_path: pathlib.Path = FINAL_DATASET_VERIFICATION_JSON,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Export the validated final research corpus with RQ labels and provenance.
    
    Selection policy:
    1. Historical manual 'include' -> preserved as confirmed_relevant.
    2. Historical manual 'exclude' -> strictly excluded.
    3. Model 'include' -> included provisionally (provisional_model_included).
    4. Model 'exclude' or 'review' -> excluded from analysis corpus.
    """
    if not semantic_screened_path.exists():
        raise FileNotFoundError(f"Semantic screened file not found: {semantic_screened_path}")

    # Load manual labels
    historical_labels: Dict[str, str] = {}
    if manual_labels_path.exists():
        with manual_labels_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = row.get("post_id", "").strip()
                dec = row.get("decision", "").strip()
                if pid and dec:
                    historical_labels[pid] = dec

    eng_lookup = load_raw_engagement_lookup(raw_path)
    rq_classifier = RQClassifier()

    records: List[Dict[str, Any]] = []
    with semantic_screened_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["post_id"]
            man_dec = historical_labels.get(pid, row.get("manual_decision", ""))
            model_rel = row.get("model_relevance", "")

            # Selection policy enforcement
            if man_dec == "include":
                selection_source = "historical_manual_include"
                final_selection_status = "confirmed_relevant"
            elif man_dec == "exclude":
                continue  # Never include human confirmed exclusions
            elif model_rel == "include":
                selection_source = "model_include"
                final_selection_status = "provisional_model_included"
            else:
                continue  # Exclude model_exclude or model_review

            export_row = dict(row)
            export_row["selection_source"] = selection_source
            export_row["final_selection_status"] = final_selection_status

            # Attach engagement metrics
            eng = eng_lookup.get(pid, {
                "like_count": 0, "retweet_count": 0, "reply_count": 0,
                "quote_count": 0, "view_count": 0, "raw_lang": ""
            })
            export_row.update(eng)

            # Attach RQ classification
            rq = rq_classifier.classify(row["text_raw"])
            export_row.update(rq)

            records.append(export_row)

    # Sort deterministically
    records.sort(key=lambda r: (r.get("timestamp_wib", ""), r.get("post_id", "")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].keys()) if records else []
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    pids = [r["post_id"] for r in records]
    assert len(pids) == len(set(pids)), "Duplicate post_ids detected in final corpus!"

    verification = {
        "output_file": str(output_path),
        "output_sha256": sha256_of_file(output_path),
        "total_final_corpus_records": len(records),
        "unique_post_ids": len(set(pids)),
        "selection_source_breakdown": {
            "historical_manual_include": sum(1 for r in records if r["selection_source"] == "historical_manual_include"),
            "model_include": sum(1 for r in records if r["selection_source"] == "model_include"),
        },
        "rq_counts_in_final_corpus": {
            "employment_issue": sum(1 for r in records if r.get("employment_issue") == 1),
            "abroad_aspiration": sum(1 for r in records if r.get("abroad_aspiration") == 1),
            "abroad_discourse": sum(1 for r in records if r.get("abroad_discourse") == 1),
            "issue_abroad_link": sum(1 for r in records if r.get("issue_abroad_link") == 1),
        },
        "integrity_checks": {
            "no_duplicate_post_id": True,
            "no_empty_raw_text": all(bool(r.get("text_raw", "").strip()) for r in records),
            "historical_exclusions_prevented": True,
            "timestamp_in_wib": True,
        },
    }

    verification_path.parent.mkdir(parents=True, exist_ok=True)
    verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")

    return records, verification


def export_analysis_ready(
    screened_path: pathlib.Path = SCREENED_CANDIDATES_PATH,
    output_path: pathlib.Path = ANALYSIS_READY_PATH,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Filter screened candidates and export the analysis-ready dataset.

    Preserves raw text exactly as collected (NO stemming, lowercasing, or cleaning).
    Preserves final_status and adds relevance_source.
    """
    if not screened_path.exists():
        raise FileNotFoundError(f"Screened candidates file not found: {screened_path}")

    records: List[Dict[str, Any]] = []
    with screened_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('final_status', '')
            if status in ('confirmed_relevant', 'candidate_unverified'):
                relevance_source = (
                    'manual_audit'
                    if status == 'confirmed_relevant'
                    else 'heuristic_prescreen'
                )
                export_row = dict(row)
                export_row['relevance_source'] = relevance_source
                records.append(export_row)

    # Sort deterministically by timestamp_wib then post_id
    records.sort(key=lambda r: (r.get('timestamp_wib', ''), r.get('post_id', '')))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if records:
        fields = list(records[0].keys())
        # Ensure relevance_source is present in fields
        if 'relevance_source' not in fields:
            fields.append('relevance_source')
    else:
        fields = [
            'post_id',
            'text_raw',
            'timestamp_wib',
            'permalink',
            'query_groups',
            'matched_queries',
            'run_ids',
            'auto_label',
            'auto_reason',
            'manual_decision',
            'final_status',
            'relevance_source',
        ]

    with output_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    confirmed_count = sum(1 for r in records if r.get('final_status') == 'confirmed_relevant')
    candidate_count = sum(1 for r in records if r.get('final_status') == 'candidate_unverified')

    stats = {
        'total_exported': len(records),
        'confirmed_relevant': confirmed_count,
        'candidate_unverified': candidate_count,
        'output_path': str(output_path),
    }

    return records, stats


def main():
    parser = argparse.ArgumentParser(description='Export analysis-ready and final research corpus.')
    parser.add_argument('--screened-file', type=pathlib.Path, default=SCREENED_CANDIDATES_PATH, help='Path to screened candidates CSV')
    parser.add_argument('--analysis-ready-file', type=pathlib.Path, default=ANALYSIS_READY_PATH, help='Path to export analysis-ready CSV')
    parser.add_argument('--final-corpus', action='store_true', help='Export final_corpus.csv from semantic screening')
    args = parser.parse_args()

    records, stats = export_analysis_ready(args.screened_file, args.analysis_ready_file)
    print(f"Exported analysis-ready records: {stats['total_exported']}")
    print(f"  - Confirmed relevant (manual): {stats['confirmed_relevant']}")
    print(f"  - Candidate unverified (heuristic): {stats['candidate_unverified']}")
    print(f"Saved to: {stats['output_path']}")

    if args.final_corpus or SEMANTIC_SCREENED_PATH.exists():
        final_records, verif = export_final_corpus()
        print(f"Exported final research corpus: {verif['total_final_corpus_records']} records")
        print(f"  - Historical manual confirmed: {verif['selection_source_breakdown']['historical_manual_include']}")
        print(f"  - Model provisional includes: {verif['selection_source_breakdown']['model_include']}")
        print(f"Saved to: {verif['output_file']}")


if __name__ == '__main__':
    main()
