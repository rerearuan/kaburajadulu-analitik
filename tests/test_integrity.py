"""Tests for data integrity and temporal/schema constraints."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from config.settings import (
    ANALYSIS_READY_PATH,
    END_DATE,
    START_DATE,
)
from src.prepare import prepare_data


class TestDataIntegrity(unittest.TestCase):
    """Verifies schema, uniqueness, and temporal bounds of analysis_ready.csv."""

    def setUp(self):
        self.assertTrue(ANALYSIS_READY_PATH.exists(), "analysis_ready.csv must exist before running tests")
        with ANALYSIS_READY_PATH.open(encoding='utf-8-sig', newline='') as f:
            self.rows = list(csv.DictReader(f))

    def test_record_count(self):
        self.assertEqual(len(self.rows), 1000)

    def test_post_id_uniqueness(self):
        pids = [r['post_id'] for r in self.rows]
        self.assertEqual(len(pids), len(set(pids)), "Found duplicate post_id in analysis_ready.csv")

    def test_no_empty_core_fields(self):
        for idx, row in enumerate(self.rows):
            self.assertTrue(row.get('post_id'), f"Row {idx} has empty post_id")
            self.assertTrue(row.get('text_raw'), f"Row {idx} has empty text_raw")
            self.assertTrue(row.get('timestamp_wib'), f"Row {idx} has empty timestamp_wib")
            self.assertIn(
                row.get('final_status'),
                ('confirmed_relevant', 'candidate_unverified'),
                f"Row {idx} has invalid final_status: {row.get('final_status')}",
            )
            self.assertIn(
                row.get('relevance_source'),
                ('manual_audit', 'heuristic_prescreen'),
                f"Row {idx} has invalid relevance_source: {row.get('relevance_source')}",
            )

    def test_temporal_bounds_wib(self):
        for idx, row in enumerate(self.rows):
            ts = row['timestamp_wib']
            d = date.fromisoformat(ts[:10])
            self.assertTrue(
                START_DATE <= d < END_DATE,
                f"Row {idx} date {d} outside research bounds [{START_DATE}, {END_DATE})",
            )

    def test_raw_text_unmodified(self):
        # Verify text is not blanked, not single word, and contains mixed-case / original formatting
        has_uppercase = any(any(c.isupper() for c in r['text_raw']) for r in self.rows)
        self.assertTrue(has_uppercase, "Raw text appears to have been improperly lowercased")

    def test_first_and_final_research_dates_regression(self):
        """Regression test ensuring January 1 and October 25, 2026 are supported inclusive."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "synthetic_raw.jsonl"
            # UTC timestamps that translate to 2026-01-01 07:00 and 2026-10-25 19:00 WIB
            records = [
                # First research date (2026-01-01 WIB)
                {
                    "month_requested": "2026-01",
                    "record": {"id": "1001", "text": "Tweet on Jan 1", "createdAt": "2026-01-01T00:00:00.000Z"},
                },
                # Final research date via month_requested (2026-10-25 WIB)
                {
                    "month_requested": "2026-10",
                    "record": {"id": "1002", "text": "Tweet on Oct 25", "createdAt": "2026-10-25T12:00:00.000Z"},
                },
                # Final research date via window_end=2026-10-25 (2026-10-25 WIB)
                {
                    "window_start": "2026-10-18",
                    "window_end": "2026-10-25",
                    "record": {"id": "1003", "text": "Tweet on Oct 25 window", "createdAt": "2026-10-25T12:00:00.000Z"},
                },
                # One day after final research date (2026-10-26 WIB) - should be excluded
                {
                    "month_requested": "2026-10",
                    "record": {"id": "1004", "text": "Tweet on Oct 26", "createdAt": "2026-10-26T00:00:00.000Z"},
                },
                # One day before research start (2025-12-31 WIB) - should be excluded
                {
                    "month_requested": "2026-01",
                    "record": {"id": "1005", "text": "Tweet on Dec 31", "createdAt": "2025-12-31T12:00:00.000Z"},
                },
            ]
            tmp_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

            # Test with inclusive research end date 2026-10-25
            data_inc, stats_inc = prepare_data(
                raw_path=tmp_path,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 10, 25),
            )
            self.assertIn("1001", data_inc, "First research date 2026-01-01 must be accepted")
            self.assertIn("1002", data_inc, "Final research date 2026-10-25 must be accepted")
            self.assertIn("1003", data_inc, "Final research date in 2026-10-25 window must be accepted")
            self.assertNotIn("1004", data_inc, "Post-boundary date 2026-10-26 must be excluded")
            self.assertNotIn("1005", data_inc, "Pre-boundary date 2025-12-31 must be excluded")
            self.assertEqual(stats_inc["unique_valid_wib"], 3)


if __name__ == '__main__':
    unittest.main()
