"""Tests for automated independent model evaluation module."""
import json
from pathlib import Path
import pytest

from src.automated_model_evaluator import (
    EVALUATOR_MODEL_ID,
    calculate_agreement_metrics,
)
from config.settings import DATA_INTERIM_DIR, REPORTS_DIR


class TestAutomatedModelEvaluator:
    """Validate evaluator outputs, schemas, and metrics calculation."""

    def test_evaluator_metadata_and_provenance(self):
        assert "mDeBERTa" in EVALUATOR_MODEL_ID
        assert "xnli" in EVALUATOR_MODEL_ID.lower()

    def test_agreement_metrics_calculation_logic(self):
        # Synthetic mock records to verify metric formulas
        records = [
            {"initial_classifier_decision": "include", "evaluator_decision": "include"},
            {"initial_classifier_decision": "include", "evaluator_decision": "include"},
            {"initial_classifier_decision": "include", "evaluator_decision": "exclude"},
            {"initial_classifier_decision": "exclude", "evaluator_decision": "exclude"},
            {"initial_classifier_decision": "exclude", "evaluator_decision": "include"},
            {"initial_classifier_decision": "include", "evaluator_decision": "uncertain"},
            {"initial_classifier_decision": "review", "evaluator_decision": "include"},
        ]
        metrics = calculate_agreement_metrics(records)
        assert metrics["total_records"] == 7
        assert metrics["evaluated_confident_total"] == 5
        assert metrics["agreement_count"] == 3
        assert metrics["disagreement_count"] == 2
        assert metrics["agreement_rate"] == 0.6
        assert metrics["disagreement_rate"] == 0.4
        cm = metrics["relative_confusion_matrix"]
        assert cm["pseudo_true_positive_both_include"] == 2
        assert cm["pseudo_false_positive_init_inc_eval_exc"] == 1
        assert cm["pseudo_false_negative_init_exc_eval_inc"] == 1
        assert cm["pseudo_true_negative_both_exclude"] == 1

    def test_generated_artifacts_integrity(self):
        sample_path = DATA_INTERIM_DIR / "automated_evaluation_sample_v1.csv"
        full_path = DATA_INTERIM_DIR / "automated_evaluation_full_1781_v1.csv"
        report_json = REPORTS_DIR / "automated_model_evaluation_report.json"
        report_md = REPORTS_DIR / "automated_model_evaluation_report.md"

        assert sample_path.exists(), "Sample evaluation output CSV must exist"
        assert full_path.exists(), "Full corpus evaluation output CSV must exist"
        assert report_json.exists(), "Evaluation JSON report must exist"
        assert report_md.exists(), "Evaluation Markdown report must exist"

        with report_json.open(encoding="utf-8") as f:
            data = json.load(f)

        assert "evaluation_sample_150_metrics" in data
        assert "full_corpus_1781_metrics" in data
        assert "rq2_issue_abroad_link_diagnostic" in data
        assert data["evaluation_sample_150_metrics"]["total_records"] == 150
        assert data["full_corpus_1781_metrics"]["total_records"] == 1781
