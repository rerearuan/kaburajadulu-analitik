"""Unit and integration tests for the ANMEDSOS data collection pipeline."""
import csv
import json
import unittest
from pathlib import Path

from config.settings import (
    ANALYSIS_READY_PATH,
    BASELINE_METRICS,
    MANUAL_LABELS_PATH,
    QUALITY_REPORT_JSON,
    RAW_TWEETS_PATH,
    SCREENED_CANDIDATES_PATH,
)
from src.export import export_analysis_ready
from src.prepare import prepare_data
from src.quality_report import generate_quality_metrics, write_reports
from src.screen import run_screening


class TestPipelineReproduction(unittest.TestCase):
    """Verifies that the offline pipeline reproduces exact baseline metrics."""

    def test_prepare_data_counts(self):
        data, stats = prepare_data(RAW_TWEETS_PATH)
        self.assertEqual(stats['raw_records_stored'], BASELINE_METRICS['raw_records_stored'])
        self.assertEqual(stats['unique_valid_wib'], BASELINE_METRICS['unique_valid_wib'])
        self.assertEqual(stats['raw_missing_required_fields'], 0)
        self.assertEqual(stats['raw_valid_date_occurrences'], BASELINE_METRICS['raw_valid_date_occurrences'])
        self.assertEqual(stats['raw_outside_requested_window'], BASELINE_METRICS['raw_outside_requested_window'])

    def test_screening_counts(self):
        prepared_data, _ = prepare_data(RAW_TWEETS_PATH)
        screened_rows, stats = run_screening(
            prepared_data=prepared_data,
            raw_path=RAW_TWEETS_PATH,
            labels_path=MANUAL_LABELS_PATH,
            output_path=SCREENED_CANDIDATES_PATH,
        )
        self.assertEqual(stats['total_unique_screened'], BASELINE_METRICS['unique_valid_wib'])
        self.assertEqual(stats['candidate_unverified'], BASELINE_METRICS['candidate_unverified'])
        self.assertEqual(stats['confirmed_relevant'], BASELINE_METRICS['confirmed_relevant'])
        self.assertEqual(stats['confirmed_excluded'], BASELINE_METRICS['confirmed_excluded'])
        self.assertEqual(stats['needs_review'], BASELINE_METRICS['needs_review'])
        self.assertEqual(stats['auto_excluded'], BASELINE_METRICS['auto_excluded'])
        self.assertEqual(stats['combined_candidates'], BASELINE_METRICS['combined_analysis_candidates'])

    def test_export_analysis_ready_counts(self):
        records, stats = export_analysis_ready(
            screened_path=SCREENED_CANDIDATES_PATH,
            output_path=ANALYSIS_READY_PATH,
        )
        self.assertEqual(len(records), BASELINE_METRICS['combined_analysis_candidates'])
        self.assertEqual(stats['total_exported'], 1000)
        self.assertEqual(stats['confirmed_relevant'], 64)
        self.assertEqual(stats['candidate_unverified'], 936)

    def test_quality_report_verification_pass(self):
        report = generate_quality_metrics(
            raw_path=RAW_TWEETS_PATH,
            screened_path=SCREENED_CANDIDATES_PATH,
            analysis_ready_path=ANALYSIS_READY_PATH,
        )
        self.assertEqual(report['overall_status'], 'PASS')
        for metric, check in report['verification'].items():
            self.assertTrue(check['pass'], f"Metric failed verification: {metric}")


if __name__ == '__main__':
    unittest.main()
