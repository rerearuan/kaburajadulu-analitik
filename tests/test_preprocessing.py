import csv
import tempfile
import unittest
from pathlib import Path
from src.preprocess_text import clean_text, process, DEFAULT_SLANG

class PreprocessingTests(unittest.TestCase):
    def test_negation_and_hashtag(self):
        s = clean_text('GAK kerja 😭 #KaburAjaDulu https://t.co/abc', DEFAULT_SLANG)
        self.assertIn('tidak kerja', s)
        self.assertIn('😭', s)
        self.assertIn('#kaburajadulu', s)
        self.assertNotIn('https:', s)

    def test_mentions_removed_not_text(self):
        s = clean_text('@someone PHK di Indonesia', DEFAULT_SLANG)
        self.assertEqual(s, 'phk di indonesia')

    def test_whole_token_replacement_not_substring(self):
        # Tokens like 'dr' should not replace inside 'drama', 'yg' inside 'sayang'
        s = clean_text('sayang drama mandiri dgn dr kawan', DEFAULT_SLANG)
        self.assertIn('sayang', s)
        self.assertIn('drama', s)
        self.assertIn('mandiri', s)
        self.assertIn('dengan', s)
        self.assertIn('dari', s)

    def test_input_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / 'input.csv'
            with src.open('w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=['post_id', 'text_raw', 'final_status'])
                w.writeheader()
                w.writerow({'post_id': '1', 'text_raw': 'GAK kerja 😭', 'final_status': 'candidate_unverified'})
            before = src.read_bytes()
            r = process(src, d / 'out.csv', d / 'report.json')
            self.assertEqual(before, src.read_bytes())
            self.assertEqual(r['output_rows'], 1)
            with (d / 'out.csv').open(encoding='utf-8-sig') as f:
                row = list(csv.DictReader(f))[0]
            self.assertEqual(row['text_raw'], 'GAK kerja 😭')
            self.assertEqual(row['text_clean'], 'tidak kerja 😭')
            self.assertIn('text_topic', row)
            self.assertIn('text_sentiment', row)
            self.assertIn('clean_empty', row)
            self.assertIn('possible_truncation', row)

    def test_deterministic_reproducibility(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = d / 'input.csv'
            with src.open('w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=['post_id', 'text_raw', 'final_status'])
                w.writeheader()
                w.writerow({'post_id': '1', 'text_raw': 'Udah gk kerja di sini', 'final_status': 'confirmed_relevant'})
            r1 = process(src, d / 'out1.csv', d / 'report1.json')
            r2 = process(src, d / 'out2.csv', d / 'report2.json')
            self.assertEqual(r1['output_sha256'], r2['output_sha256'])
            self.assertEqual((d / 'out1.csv').read_bytes(), (d / 'out2.csv').read_bytes())

if __name__ == '__main__':
    unittest.main()
