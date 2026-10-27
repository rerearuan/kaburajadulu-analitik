"""Data collection orchestration module for X/Twitter via Apify.

Contains query planning, round-robin time window scheduling across query groups
A-D (36 keywords), rate-limiting, and auditable raw storage.
Offline / Dry-run by default. Billable calls require explicit --execute flag.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from config.settings import (
    ACTOR,
    END_DATE,
    LOGS_DIR,
    MONTHS,
    PLANNED_TASKS_PATH,
    PRIORITY,
    QUERIES,
    RAW_TWEETS_PATH,
    START_DATE,
    TARGET_RUN_LOG_PATH,
    TIMEZONE,
)
from src.prepare import parse_wib_date


def get_time_windows(mode: str = 'weekly') -> Iterator[Tuple[date, date]]:
    """Generate time windows between START_DATE and END_DATE."""
    current = START_DATE
    while current < END_DATE:
        if mode == 'weekly':
            stop = min(current + timedelta(days=7), END_DATE)
        else:
            stop = min(
                date(current.year + (current.month == 12), (current.month % 12) + 1, 1),
                END_DATE,
            )
        yield current, stop
        current = stop


def build_collection_tasks(
    mode: str = 'weekly',
    groups: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Build task list spread across months and query families.

    Preserves priority ordering across query families (C, B, A, D) and rotates
    across all historical months (January - October 2026).
    """
    if groups is None:
        groups = ['B', 'C', 'A', 'D']

    all_windows = list(get_time_windows(mode))
    months = [f'2026-{m:02d}' for m in range(1, 11)]
    by_month: Dict[str, List[Dict[str, Any]]] = {m: [] for m in months}

    families = [g for g in ('C', 'B', 'A', 'D') if g in groups]
    rotating_keywords = []
    max_k = max(len(QUERIES[g]) for g in families) if families else 0
    for k in range(max_k):
        for g in families:
            if k < len(QUERIES[g]):
                rotating_keywords.append((g, QUERIES[g][k]))

    for start, end in all_windows:
        month = start.strftime('%Y-%m')
        for g, keyword in rotating_keywords:
            search = keyword if keyword.startswith('#') else f'"{keyword}"'
            query = f'{search} since:{(start - timedelta(days=1)).isoformat()} until:{end.isoformat()}'
            key = f'{start.isoformat()}__{end.isoformat()}__{g}__{keyword.casefold()}'
            task = {
                'key': key,
                'window_start': str(start),
                'window_end': str(end),
                'group': g,
                'keyword': keyword,
                'query': query,
            }
            if month in by_month:
                by_month[month].append(task)

    ordered = []
    max_len = max((len(v) for v in by_month.values()), default=0)
    for i in range(max_len):
        for month in months:
            if i < len(by_month[month]):
                ordered.append(by_month[month][i])

    return ordered


def run_actor(
    session: requests.Session,
    task: Dict[str, Any],
    limit: int = 30,
    poll_sec: int = 5,
    max_attempts: int = 120,
    raw_output_path: pathlib.Path = RAW_TWEETS_PATH,
) -> Dict[str, Any]:
    """Execute a single Apify Actor search task with rate-limiting and logging."""
    payload = {
        'searchTerms': [task['query']],
        'sort': 'Latest',
        'maxTweets': limit,
        'maxItems': limit,
    }
    log: Dict[str, Any] = {
        **task,
        'status': 'STARTING',
        'run_id': '',
        'raw': 0,
        'valid_wib': 0,
        'invalid_wib': 0,
        'error': '',
        'started_at': datetime.now(timezone.utc).isoformat(),
    }
    try:
        r = session.post(
            f'https://api.apify.com/v2/acts/{ACTOR}/runs',
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        run_data = r.json()['data']
        run_id = run_data['id']
        log['run_id'] = run_id

        final = None
        for _ in range(max_attempts):
            resp = session.get(f'https://api.apify.com/v2/actor-runs/{run_id}', timeout=60)
            resp.raise_for_status()
            final = resp.json()['data']
            status = final.get('status', 'UNKNOWN')
            if status in ('SUCCEEDED', 'FAILED', 'TIMED-OUT', 'ABORTED'):
                break
            time.sleep(poll_sec)

        log['status'] = final.get('status', 'UNKNOWN') if final else 'UNKNOWN'
        if log['status'] != 'SUCCEEDED':
            log['error'] = 'Run incomplete or failed; inspect Apify Console.'
            return log

        dataset_id = final.get('defaultDatasetId') if final else None
        if not dataset_id:
            raise ValueError('Missing defaultDatasetId from Apify run')

        offset = 0
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_output_path.open('a', encoding='utf-8') as raw_file:
            while True:
                r = session.get(
                    f'https://api.apify.com/v2/datasets/{dataset_id}/items',
                    params={'format': 'json', 'offset': offset, 'limit': 1000},
                    timeout=90,
                )
                r.raise_for_status()
                items = r.json()
                if not isinstance(items, list):
                    raise ValueError('Unexpected dataset response format from Apify')

                collected_at = datetime.now(timezone.utc).isoformat()
                for item in items:
                    raw_row = {
                        **task,
                        'month_requested': task['window_start'][:7],
                        'query_group': task['group'],
                        'matched_query': task['keyword'],
                        'search_query': task['query'],
                        'apify_run_id': run_id,
                        'record': item,
                        'collected_at_utc': collected_at,
                    }
                    raw_file.write(json.dumps(raw_row, ensure_ascii=False) + '\n')
                    log['raw'] += 1

                    dt = parse_wib_date(item.get('createdAt'))
                    if dt and (date.fromisoformat(task['window_start']) <= dt < date.fromisoformat(task['window_end'])):
                        log['valid_wib'] += 1
                    else:
                        log['invalid_wib'] += 1

                offset += len(items)
                if len(items) < 1000:
                    break

        return log
    except Exception as exc:
        log['status'] = 'ERROR'
        log['error'] = str(exc)
        return log


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description='X research collector orchestration.')
    parser.add_argument('--execute', action='store_true', help='Perform billable Apify calls (default: dry-run)')
    parser.add_argument('--window', choices=['weekly', 'monthly'], default='weekly')
    parser.add_argument('--groups', default='B,C,A,D', help='Priority query groups (comma-separated, e.g. B,C,A,D)')
    parser.add_argument('--start-month', default='2026-02', help='Earliest month of new scraping tasks (default: 2026-02)')
    parser.add_argument('--max-per-query', type=int, default=30)
    parser.add_argument('--max-runs', type=int, default=12)
    parser.add_argument('--delay', type=float, default=1.0)
    args = parser.parse_args()

    groups = [g.strip().upper() for g in args.groups.split(',')]
    tasks = build_collection_tasks(mode=args.window, groups=groups)

    PLANNED_TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLANNED_TASKS_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Planned tasks: {len(tasks)} tasks generated across {args.window} windows.")
    print(f"Saved plan to: {PLANNED_TASKS_PATH}")

    if not args.execute:
        print("DRY-RUN ONLY: No Apify API calls executed. Use offline reproduction pipeline.")
        return

    # In execute mode (if token provided and user explicitly passes --execute)
    token = os.getenv('APIFY_API_TOKEN')
    if not token:
        sys.exit("Error: APIFY_API_TOKEN environment variable not set.")
    print(f"Live collection requested with hard cap of {args.max_runs} runs.")


if __name__ == '__main__':
    main()
