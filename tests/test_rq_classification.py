"""Unit tests for multi-label RQ classification."""
import unittest

from src.classify_rq import RQClassifier


class TestRQClassification(unittest.TestCase):
    """Test suite for RQ1, RQ2 (aspiration vs discourse), and RQ2/3 link constraints."""

    def setUp(self):
        self.classifier = RQClassifier()

    def test_rq1_employment_issue(self):
        res = self.classifier.classify("Susah banget cari kerja sekarang, udah 6 bulan nganggur kena PHK.")
        self.assertEqual(res["employment_issue"], 1)
        self.assertEqual(res["abroad_aspiration"], 0)
        self.assertIn("RQ1", res["rq_evidence"])

    def test_rq2_abroad_aspiration_personal(self):
        res = self.classifier.classify("Bismillah pengen kerja ke Jepang tahun ini lewat tokutei ginou #KaburAjaDulu")
        self.assertEqual(res["abroad_aspiration"], 1)
        self.assertEqual(res["abroad_discourse"], 1)
        self.assertIn("RQ2-Aspiration", res["rq_evidence"])

    def test_rq2_abroad_discourse_public_only(self):
        # General informative sharing about overseas jobs without personal intent
        res = self.classifier.classify("Pemerintah Jepang membuka peluang kerja luar negeri untuk pekerja migran Indonesia.")
        self.assertEqual(res["abroad_aspiration"], 0)
        self.assertEqual(res["abroad_discourse"], 1)
        self.assertIn("RQ2-Discourse", res["rq_evidence"])

    def test_rq2_link_explicit(self):
        # Stated connection between domestic precarity and overseas work (mapped strictly to RQ2)
        res = self.classifier.classify("Daripada nganggur dan susah cari kerja di Indo, mending coba kerja ke luar negeri #KaburAjaDulu")
        self.assertEqual(res["employment_issue"], 1)
        self.assertEqual(res["abroad_aspiration"], 1)
        self.assertEqual(res["issue_abroad_link"], 1)
        self.assertIn("RQ2-Link", res["rq_evidence"])

    def test_no_false_link_without_employment(self):
        # Mention of abroad without employment complaint should not be issue_abroad_link
        res = self.classifier.classify("Pagi semua, salam dari perantau di luar negeri!")
        self.assertEqual(res["employment_issue"], 0)
        self.assertEqual(res["issue_abroad_link"], 0)


if __name__ == "__main__":
    unittest.main()
