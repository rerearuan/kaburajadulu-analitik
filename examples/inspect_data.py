"""Example script to inspect and summarize the analysis_ready corpus."""
import csv
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'processed' / 'analysis_ready.csv'


def main():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} does not exist. Run pipeline first.")
        return

    with DATA_FILE.open(encoding='utf-8-sig', newline='') as f:
        records = list(csv.DictReader(f))

    print(f"Total analysis-ready records: {len(records):,}")
    print("\nFirst 3 sample records:")
    for idx, r in enumerate(records[:3], 1):
        print(f"\n[{idx}] Post ID: {r['post_id']} | Date: {r['timestamp_wib']}")
        print(f"    Status: {r['final_status']} | Source: {r['relevance_source']}")
        print(f"    Queries: {r['matched_queries']}")
        print(f"    Text: {r['text_raw'][:120]}...")


if __name__ == '__main__':
    main()
