"""Unit tests for deterministic screening heuristic rules."""
import unittest

from src.screen import screen_text


class TestScreeningHeuristics(unittest.TestCase):
    """Tests deterministic pattern matching and priority rules in screening."""

    def test_too_short(self):
        lab, reason = screen_text("pendek")
        self.assertEqual(lab, 'exclude_auto')
        self.assertEqual(reason, 'too_short')

    def test_noise_filter(self):
        lab, reason = screen_text("Ini info giveaway saldo dana untuk pencari kerja yang sedang susah cari kerja")
        self.assertEqual(lab, 'review')
        self.assertEqual(reason, 'possible_promo_or_event')

    def test_promo_filter(self):
        lab, reason = screen_text("Dibutuhkan segera lowongan kerja terbuka untuk posisi staf admin dan customer service")
        self.assertEqual(lab, 'review')
        self.assertEqual(reason, 'possible_recruitment_promotion')

    def test_incidental_filter(self):
        lab, reason = screen_text("Kemalangan di tambak menimpa pekerja tambak yang sedang bekerja di lokasi proyek")
        self.assertEqual(lab, 'review')
        self.assertEqual(reason, 'possible_incidental_mention')

    def test_valid_employment_problem(self):
        lab, reason = screen_text("Banyak fresh graduate yang mengeluh susah cari kerja dan gaji rendah di Indonesia")
        self.assertEqual(lab, 'candidate')
        self.assertEqual(reason, 'employment_context')

    def test_valid_abroad_aspiration(self):
        lab, reason = screen_text("Kondisi kerja dalam negeri makin tidak menentu, lebih baik kerja di Jepang atau Singapura")
        self.assertEqual(lab, 'candidate')
        self.assertEqual(reason, 'employment_context')

    def test_abroad_without_work(self):
        lab, reason = screen_text("Pengen banget liburan ke Jepang atau ke Korea bareng keluarga tahun depan")
        self.assertEqual(lab, 'review')
        self.assertEqual(reason, 'abroad_without_clear_work')

    def test_unrelated_text(self):
        lab, reason = screen_text("Cuaca hari ini di Jakarta sangat cerah dan langit berwarna biru tanpa awan sedikitpun")
        self.assertEqual(lab, 'exclude_auto')
        self.assertEqual(reason, 'no_employment_topic')


if __name__ == '__main__':
    unittest.main()
