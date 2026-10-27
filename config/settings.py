"""Configuration and constants for ANMEDSOS TK2 Data Collection Pipeline."""
import os
import pathlib
import re
from datetime import date
from zoneinfo import ZoneInfo

# Root Paths
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / 'config'
SRC_DIR = PROJECT_ROOT / 'src'
DATA_DIR = PROJECT_ROOT / 'data'
DATA_RAW_DIR = DATA_DIR / 'raw'
DATA_INTERIM_DIR = DATA_DIR / 'interim'
DATA_PROCESSED_DIR = DATA_DIR / 'processed'
LOGS_DIR = PROJECT_ROOT / 'logs'
REPORTS_DIR = PROJECT_ROOT / 'reports'
TESTS_DIR = PROJECT_ROOT / 'tests'
EXAMPLES_DIR = PROJECT_ROOT / 'examples'
ARCHIVE_DIR = PROJECT_ROOT / 'archive'

# File Paths
RAW_TWEETS_PATH = DATA_RAW_DIR / 'raw_tweets.jsonl'
MANUAL_LABELS_PATH = DATA_INTERIM_DIR / 'manual_labels.csv'
SCREENED_CANDIDATES_PATH = DATA_INTERIM_DIR / 'screened_candidates.csv'
ANALYSIS_READY_PATH = DATA_PROCESSED_DIR / 'analysis_ready.csv'
PLANNED_TASKS_PATH = DATA_INTERIM_DIR / 'planned_tasks.json'
TARGET_RUN_LOG_PATH = LOGS_DIR / 'target_run_log.jsonl'
RUN_LOG_PATH = LOGS_DIR / 'run_log.jsonl'
QUALITY_REPORT_MD = REPORTS_DIR / 'quality_report.md'
QUALITY_REPORT_JSON = REPORTS_DIR / 'quality_report.json'
PIPELINE_VERIFICATION_JSON = REPORTS_DIR / 'pipeline_verification.json'

# Temporal Configuration (WIB: Asia/Jakarta)
TIMEZONE = ZoneInfo('Asia/Jakarta')
START_DATE = date(2026, 1, 1)
# Upper exclusive bound 2026-10-26 covers up to 2026-10-25 23:59:59 WIB
END_DATE = date(2026, 10, 26)
MONTHS = [f'2026-{m:02d}' for m in range(1, 11)]

# 36 Discovery terms across 4 groups (A-D) as formulated in TK-1 / TK-2
QUERIES = {
    'A': [
        'cari kerja', 'mencari kerja', 'lowongan kerja', 'lamar kerja',
        'rekrutmen', 'fresh graduate', 'peluang kerja', 'karier'
    ],
    'B': [
        'susah cari kerja', 'sulit cari kerja', 'pengangguran', 'PHK', 'kena PHK',
        'gaji rendah', 'upah minimum', 'syarat pengalaman', 'pengalaman kerja',
        'pekerjaan kontrak', 'kerja tidak sesuai jurusan', 'pasar kerja Indonesia'
    ],
    'C': [
        'kerja di luar negeri', 'bekerja di luar negeri', 'kerja ke luar negeri',
        'cari kerja di luar negeri', 'kabur aja dulu', '#KaburAjaDulu',
        'kerja di Jepang', 'kerja di Singapura'
    ],
    'D': [
        'jobs in Indonesia', 'job market Indonesia', 'unemployment Indonesia',
        'layoffs Indonesia', 'low wages Indonesia',
        'working abroad from Indonesia', 'Indonesians working abroad',
        'leave Indonesia for work'
    ]
}

PRIORITY = {'B': 0, 'C': 1, 'A': 2, 'D': 3}
ACTOR = os.getenv('APIFY_ACTOR_ID', 'scrapesmith~x-twitter-search-scraper')

# Deterministic screening regex rules
DATE_RE = re.compile(r'https?://\S+|@\w+')
WORK = re.compile(r'(?i)\b(kerja|bekerja|pekerjaan|pekerja|pencari kerja|pengangguran|nganggur|karier|career|job|jobs|employment|unemploy\w*|recruit\w*|rekrut\w*|lamar|lowongan|upah|gaji|salary|wage\w*|phk|layoff\w*|fresh grad\w*|kontrak|karyawan|magang|interview|loker|honorer|visa kerja|work visa|perusahaan|company|perantau|working abroad)\b')
PROBLEM = re.compile(r'(?i)(susah|sulit|susahnya|susah banget|frustrasi|cemas|resah|krisis|terbatas|kurang|tidak ada|ga ada|nggak ada|gak ada|belum dapat|belum dapet|pengangguran|nganggur|phk|layoff|upah rendah|gaji rendah|pengalaman kerja|ketidakpastian|kontrak|tidak sesuai jurusan|penuh persaingan|jobless|unemploy|low wages|low salary)')
ABROAD = re.compile(r'(?i)(luar negeri|mancanegara|overseas|abroad|kabur\s*aja\s*dulu|#kaburajadulu|ke jepang|di jepang|ke singapura|di singapura|ke korea|di korea|ke australia|di australia|pindah negara|kerja di (?:japan|singapore|korea|china|belanda|eropa)|work(?:ing)? (?:in|at|for) (?:japan|singapore|china|korea)|visa sponsorship)')
INDONESIA = re.compile(r'(?i)(indonesia|\bindo\b|\bri\b|\bui\b|jakarta|surabaya|bandung|jogja|jogjakarta|yogyakarta|rupiah|\bidr\b|\bbpjs\b|\bumr\b|\bumk\b|\bwni\b|anak bangsa|di sini|di negara ini)')
NOISE = re.compile(r'(?i)(giveaway|diskon|promo kode|slot gacor|togel|seminar|webinar|event study abroad|register now|pendaftaran seminar|pertandingan|la liga|jual akun|open jastip)')
PROMO = re.compile(r'(?i)(lowongan kerja.{0,40}(dibutuhkan|terbuka)|dibutuhkan segera|daftar sekarang|pendaftaran dibuka|rekrutmen dibuka|join (?:our|us)|program penempatan|pendaftaran program|apply now|open recruitment)')
INCIDENTAL = re.compile(r'(?i)(selingkuh|privacy pasien|privasi pasien|kecelakaan lalu lintas|kemalangan di tambak|kisah percintaan)')

# Baseline Metrics for Pipeline Verification
BASELINE_METRICS = {
    'raw_records_stored': 3292,
    'raw_valid_date_occurrences': 1829,
    'raw_outside_requested_window': 1463,
    'raw_missing_required_fields': 0,
    'unique_valid_wib': 1781,
    'candidate_unverified': 936,
    'confirmed_relevant': 64,
    'confirmed_excluded': 31,
    'needs_review': 618,
    'auto_excluded': 132,
    'combined_analysis_candidates': 1000
}
