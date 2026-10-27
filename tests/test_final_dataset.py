"""Integration tests for final corpus and final preprocessed dataset."""
import csv
import unittest

from config.settings import DATA_PROCESSED_DIR
from src.preprocess_text import clean_text, detect_language, evaluate_truncation

FINAL_CORPUS_PATH = DATA_PROCESSED_DIR / "final_corpus.csv"
FINAL_PREPROCESSED_PATH = DATA_PROCESSED_DIR / "final_preprocessed.csv"


class TestFinalDataset(unittest.TestCase):
    """Test suite for final corpus, final preprocessed data integrity, and preprocessing enhancements."""

    def test_html_entity_unescape(self):
        # &amp; should become &, &lt; becomes <
        raw = "Gaji &amp; tunjangan di bawah UMR &lt; kemiskinan"
        cleaned = clean_text(raw)
        self.assertIn("gaji & tunjangan", cleaned)
        self.assertNotIn("&amp;", cleaned)
        self.assertNotIn("&lt;", cleaned)

    def test_language_detection(self):
        id_text = "Aku susah banget cari kerja di Jakarta sekarang."
        en_text = "Looking for a job in software engineering with decent wages."
        mixed_text = "Fresh graduate jaman now susah dapet job karena overqualified requirement."
        self.assertEqual(detect_language(id_text), "indonesian")
        self.assertEqual(detect_language(en_text), "english")
        self.assertEqual(detect_language(mixed_text), "mixed_id_en")

    def test_refined_truncation_detection(self):
        # Normal complete tweet with no terminal period
        heur, exp = evaluate_truncation("Susah banget cari kerja di masa sekarang ini")
        self.assertEqual(heur, 0)
        self.assertEqual(exp, 0)

        # Truncated tweet with ellipsis
        heur_el, exp_el = evaluate_truncation("Susah banget cari kerja sekarang karena syarat umur dan…")
        self.assertEqual(exp_el, 1)

        # Truncated tweet with dangling trailing conjunction
        heur_dan, exp_dan = evaluate_truncation("Kerja lembur tidak dibayar dan bosnya toxic dan")
        self.assertEqual(exp_dan, 1)

    def test_final_corpus_and_preprocessed_reconciliation(self):
        self.assertTrue(FINAL_CORPUS_PATH.exists(), "final_corpus.csv must exist")
        self.assertTrue(FINAL_PREPROCESSED_PATH.exists(), "final_preprocessed.csv must exist")

        with FINAL_CORPUS_PATH.open(encoding="utf-8-sig") as f:
            corpus_rows = list(csv.DictReader(f))

        with FINAL_PREPROCESSED_PATH.open(encoding="utf-8-sig") as f:
            prep_rows = list(csv.DictReader(f))

        # Row counts must match exactly
        self.assertEqual(
            len(corpus_rows), len(prep_rows),
            f"Row count mismatch: final_corpus={len(corpus_rows)} vs final_preprocessed={len(prep_rows)}"
        )

        # Verify exact post_id alignment and text_raw byte preservation
        for c_row, p_row in zip(corpus_rows, prep_rows):
            self.assertEqual(c_row["post_id"], p_row["post_id"])
            self.assertEqual(c_row["text_raw"], p_row["text_raw"])
            self.assertIn("text_clean", p_row)
            self.assertIn("text_topic", p_row)
            self.assertIn("text_sentiment", p_row)
            self.assertIn("detected_language", p_row)
            self.assertIn("explicit_truncation", p_row)

        # Check historical manual inclusions and exclusions
        sources = {r["selection_source"] for r in corpus_rows}
        self.assertIn("historical_manual_include", sources)
        self.assertNotIn("historical_manual_exclude", sources)


if __name__ == "__main__":
    unittest.main()
