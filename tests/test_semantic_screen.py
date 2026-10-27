"""Unit tests for semantic relevance screening."""
import csv
import tempfile
import unittest
from pathlib import Path

from src.semantic_screen import SemanticScreenClassifier, run_semantic_screening


class TestSemanticScreening(unittest.TestCase):
    """Test suite for semantic classifier, schema validation, and mock mode."""

    def setUp(self):
        self.classifier = SemanticScreenClassifier(mode="mock")

    def test_mock_classification_schema(self):
        res = self.classifier.classify_record("GAK kerja kena PHK di Indonesia 😭")
        self.assertEqual(res["model_relevance"], "include")
        self.assertEqual(res["relevance_reason_code"], "employment_concern")
        self.assertIn("relevance_reason", res)
        self.assertIn("uncertainty", res)
        self.assertEqual(res["model_id"], "mock-classifier-v1")
        self.assertEqual(res["classification_source"], "mock_engine")
        self.assertFalse(res["needs_context"])

    def test_mock_exclusion_sports(self):
        res = self.classifier.classify_record("Pertandingan sepak bola Liga 1 malam ini seru")
        self.assertEqual(res["model_relevance"], "exclude")
        self.assertEqual(res["relevance_reason_code"], "sports_entertainment_exclusion")

    def test_mock_review_neutral(self):
        res = self.classifier.classify_record("Pagi semua apa kabar?")
        self.assertEqual(res["model_relevance"], "review")
        self.assertTrue(res["needs_context"])

    def test_historical_manual_protection(self):
        with tempfile.TemporaryDirectory() as d:
            d_path = Path(d)
            in_csv = d_path / "cand.csv"
            lbl_csv = d_path / "labels.csv"
            out_csv = d_path / "out.csv"
            rev_csv = d_path / "rev.csv"

            # Create test input with 1 include and 1 exclude in manual labels
            with in_csv.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["post_id", "text_raw"])
                w.writeheader()
                w.writerow({"post_id": "1", "text_raw": "Kena PHK butuh kerja"})
                w.writerow({"post_id": "2", "text_raw": "Sepak bola timnas menang"})

            with lbl_csv.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["post_id", "decision"])
                w.writeheader()
                w.writerow({"post_id": "1", "decision": "include"})
                w.writerow({"post_id": "2", "decision": "exclude"})

            summary = run_semantic_screening(
                input_path=in_csv,
                manual_labels_path=lbl_csv,
                output_path=out_csv,
                review_queue_path=rev_csv,
                mode="mock",
                force_recompute=True,
            )
            self.assertEqual(summary["total_records_processed"], 2)

            with out_csv.open(encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["historical_manual_decision"], "include")
            self.assertEqual(rows[1]["historical_manual_decision"], "exclude")


if __name__ == "__main__":
    unittest.main()
