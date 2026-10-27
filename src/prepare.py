"""Data preparation and deduplication module.

Extracts, validates temporal boundaries in Asia/Jakarta (WIB), and deduplicates
raw tweet records while preserving multi-query and multi-run provenance.
"""
import argparse
import json
import pathlib
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from config.settings import (
    END_DATE,
    MONTHS,
    RAW_TWEETS_PATH,
    START_DATE,
    TIMEZONE,
)


def parse_wib_date(stamp: Any) -> Optional[date]:
    """Parse an ISO timestamp string into a local Asia/Jakarta date."""
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
        return dt.astimezone(TIMEZONE).date() if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def parse_wib_iso(stamp: Any) -> Optional[str]:
    """Parse an ISO timestamp string into a full Asia/Jakarta ISO string."""
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
        return dt.astimezone(TIMEZONE).isoformat() if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def load_raw_records(path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load JSONL lines from the specified raw records file."""
    if not path.exists():
        return []
    records = []
    with path.open(encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                records.append(json.loads(line_str))
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
    return records


def prepare_data(
    raw_path: pathlib.Path = RAW_TWEETS_PATH,
    start_date: date = START_DATE,
    end_date: date = END_DATE,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Process and deduplicate raw tweets, returning deduplicated data and stats."""
    raw_records = load_raw_records(raw_path)
    data: Dict[str, Dict[str, Any]] = {}
    valid_occurrences = 0
    invalid_date = 0
    missing = 0

    monthly_raw = {m: 0 for m in MONTHS}
    monthly_unique = {m: 0 for m in MONTHS}

    for wrap in raw_records:
        rec = wrap.get('record', {})
        if not isinstance(rec, dict):
            missing += 1
            continue

        pid = str(rec.get('id') or '')
        raw_text = rec.get('text') or ''
        created_at = rec.get('createdAt')
        dt = parse_wib_date(created_at)

        if not pid or not dt or not str(raw_text).strip():
            missing += 1
            continue

        m_raw = dt.strftime('%Y-%m')
        if m_raw in monthly_raw:
            monthly_raw[m_raw] += 1

        # Check temporal window validity
        # Research period: January 1 – October 25, 2026 inclusive (Asia/Jakarta WIB).
        # Correct off-by-one errors where '< end_date' would improperly exclude October 25 when
        # end_date is specified as date(2026, 10, 25).
        max_bound = end_date if end_date <= date(2026, 10, 25) else (end_date - timedelta(days=1))

        begin = wrap.get('window_start')
        end = wrap.get('window_end')
        if begin and end:
            try:
                b_date = date.fromisoformat(begin)
                e_date = date.fromisoformat(end)
                # If window_end is the final research date (2026-10-25), allow inclusive
                if e_date == date(2026, 10, 25):
                    valid = b_date <= dt <= e_date
                else:
                    valid = b_date <= dt < e_date
                # Global bounds enforcement
                valid = valid and (start_date <= dt <= max_bound)
            except ValueError:
                valid = False
        else:
            mm = wrap.get('month_requested', '')
            valid = (mm == dt.strftime('%Y-%m')) and (start_date <= dt <= max_bound)

        if not valid:
            invalid_date += 1
            continue

        valid_occurrences += 1

        if pid not in data:
            data[pid] = {
                'post_id': pid,
                'text_raw': raw_text,
                'timestamp_wib': dt.isoformat(),
                'timestamp_iso': parse_wib_iso(created_at),
                'permalink': rec.get('url', ''),
                'query_groups': set(),
                'matched_queries': set(),
                'run_ids': set(),
            }
            if m_raw in monthly_unique:
                monthly_unique[m_raw] += 1

        # Track provenance
        if wrap.get('query_group'):
            data[pid]['query_groups'].add(wrap['query_group'])
        if wrap.get('matched_query'):
            data[pid]['matched_queries'].add(wrap['matched_query'])
        if wrap.get('apify_run_id'):
            data[pid]['run_ids'].add(wrap['apify_run_id'])

    stats = {
        'raw_records_stored': len(raw_records),
        'raw_valid_date_occurrences': valid_occurrences,
        'raw_outside_requested_window': invalid_date,
        'raw_missing_required_fields': missing,
        'unique_valid_wib': len(data),
        'monthly_raw': monthly_raw,
        'monthly_unique': monthly_unique,
    }

    return data, stats


def main():
    parser = argparse.ArgumentParser(description='Prepare and deduplicate raw tweet records.')
    parser.add_argument('--raw-file', type=pathlib.Path, default=RAW_TWEETS_PATH, help='Path to raw tweets JSONL file')
    args = parser.parse_args()

    data, stats = prepare_data(args.raw_file)
    print(f"Loaded raw records: {stats['raw_records_stored']}")
    print(f"Valid occurrences: {stats['raw_valid_date_occurrences']}")
    print(f"Outside window: {stats['raw_outside_requested_window']}")
    print(f"Missing required fields: {stats['raw_missing_required_fields']}")
    print(f"Unique valid tweets (WIB): {stats['unique_valid_wib']}")


if __name__ == '__main__':
    main()
