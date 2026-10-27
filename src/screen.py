"""Screening module for candidate relevance and manual audit integration.

Applies deterministic keyword/regex heuristic screening rules and integrates
human audit overrides (manual labels) without mutating original raw text.
"""
import argparse
import csv
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from config.settings import (
    ABROAD,
    DATE_RE,
    INCIDENTAL,
    INDONESIA,
    MANUAL_LABELS_PATH,
    MONTHS,
    NOISE,
    PROBLEM,
    PROMO,
    RAW_TWEETS_PATH,
    SCREENED_CANDIDATES_PATH,
    WORK,
)
from src.prepare import prepare_data


def screen_text(text: str) -> Tuple[str, str]:
    """Recall-oriented eligibility pre-screen, NOT a verified research annotation.

    Returns:
        (auto_label, auto_reason)
        auto_label in ('candidate', 'review', 'exclude_auto')
    """
    clean_str = DATE_RE.sub(' ', text or '').strip()
    if len(clean_str) < 24:
        return 'exclude_auto', 'too_short'
    if NOISE.search(clean_str):
        return 'review', 'possible_promo_or_event'
    if PROMO.search(clean_str):
        return 'review', 'possible_recruitment_promotion'
    if INCIDENTAL.search(clean_str):
        return 'review', 'possible_incidental_mention'

    work = bool(WORK.search(clean_str))
    problem = bool(PROBLEM.search(clean_str))
    abroad = bool(ABROAD.search(clean_str))
    indo = bool(INDONESIA.search(clean_str))

    if work and (problem or abroad or indo):
        return 'candidate', 'employment_context'
    if work:
        return 'review', 'work_context_not_specific'
    if abroad:
        return 'review', 'abroad_without_clear_work'
    return 'exclude_auto', 'no_employment_topic'


def load_manual_labels(path: pathlib.Path) -> Dict[str, str]:
    """Load manual review decisions from CSV."""
    if not path.exists():
        return {}
    decisions = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = str(row.get('post_id') or '').strip()
            decision = str(row.get('decision') or '').strip().lower()
            if pid and decision in ('include', 'exclude'):
                decisions[pid] = decision
    return decisions


def run_screening(
    prepared_data: Optional[Dict[str, Dict[str, Any]]] = None,
    raw_path: pathlib.Path = RAW_TWEETS_PATH,
    labels_path: pathlib.Path = MANUAL_LABELS_PATH,
    output_path: pathlib.Path = SCREENED_CANDIDATES_PATH,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Screen prepared data, apply manual labels, and write screened_candidates.csv."""
    if prepared_data is None:
        prepared_data, prep_stats = prepare_data(raw_path)
    else:
        prep_stats = {}

    decisions = load_manual_labels(labels_path)

    statuses: Dict[str, int] = {}
    monthly_breakdown: Dict[str, Dict[str, int]] = {
        m: {
            'unique_valid': 0,
            'candidate_unverified': 0,
            'needs_review': 0,
            'auto_excluded': 0,
            'confirmed_relevant': 0,
            'confirmed_excluded': 0,
        }
        for m in MONTHS
    }

    screened_rows: List[Dict[str, Any]] = []

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
    ]

    # Sort deterministically by timestamp_wib then post_id
    sorted_items = sorted(
        prepared_data.values(),
        key=lambda r: (r['timestamp_wib'], r['post_id']),
    )

    for row in sorted_items:
        text = row['text_raw']
        lab, reason = screen_text(text)
        manual = decisions.get(row['post_id'], '')

        if manual == 'include':
            status = 'confirmed_relevant'
        elif manual == 'exclude':
            status = 'confirmed_excluded'
        elif lab == 'candidate':
            status = 'candidate_unverified'
        elif lab == 'review':
            status = 'needs_review'
        else:
            status = 'auto_excluded'

        statuses[status] = statuses.get(status, 0) + 1

        m_str = row['timestamp_wib'][:7]
        if m_str in monthly_breakdown:
            monthly_breakdown[m_str]['unique_valid'] += 1
            if status in monthly_breakdown[m_str]:
                monthly_breakdown[m_str][status] += 1

        screened_record = {
            'post_id': row['post_id'],
            'text_raw': row['text_raw'],
            'timestamp_wib': row['timestamp_wib'],
            'permalink': row['permalink'],
            'query_groups': json.dumps(sorted(row['query_groups']), ensure_ascii=False),
            'matched_queries': json.dumps(sorted(row['matched_queries']), ensure_ascii=False),
            'run_ids': json.dumps(sorted(row['run_ids'])),
            'auto_label': lab,
            'auto_reason': reason,
            'manual_decision': manual,
            'final_status': status,
        }
        screened_rows.append(screened_record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(screened_rows)

    stats = {
        'total_unique_screened': len(screened_rows),
        'candidate_unverified': statuses.get('candidate_unverified', 0),
        'confirmed_relevant': statuses.get('confirmed_relevant', 0),
        'confirmed_excluded': statuses.get('confirmed_excluded', 0),
        'needs_review': statuses.get('needs_review', 0),
        'auto_excluded': statuses.get('auto_excluded', 0),
        'combined_candidates': statuses.get('candidate_unverified', 0) + statuses.get('confirmed_relevant', 0),
        'statuses': statuses,
        'monthly_breakdown': monthly_breakdown,
    }

    return screened_rows, stats


def main():
    parser = argparse.ArgumentParser(description='Run heuristic screening and apply manual labels.')
    parser.add_argument('--raw-file', type=pathlib.Path, default=RAW_TWEETS_PATH, help='Path to raw tweets JSONL')
    parser.add_argument('--labels-file', type=pathlib.Path, default=MANUAL_LABELS_PATH, help='Path to manual labels CSV')
    parser.add_argument('--output-file', type=pathlib.Path, default=SCREENED_CANDIDATES_PATH, help='Path to output screened CSV')
    args = parser.parse_args()

    rows, stats = run_screening(
        raw_path=args.raw_file,
        labels_path=args.labels_file,
        output_path=args.output_file,
    )
    print(f"Total screened unique records: {stats['total_unique_screened']}")
    print(f"Statuses breakdown: {stats['statuses']}")
    print(f"Combined candidates (unverified + confirmed): {stats['combined_candidates']}")


if __name__ == '__main__':
    main()
