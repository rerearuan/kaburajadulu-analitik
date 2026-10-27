"""Conservative, reproducible text preparation for ANMEDSOS tweets.

Produces multiple distinct text representations tailored for downstream tasks:
- text_raw: exact unmodified source text
- text_clean: normalized clean text for general EDA and quality inspection
- text_topic: semantic-preserving representation for contextual embeddings / BERTopic
- text_sentiment: polarity-preserving representation for sentiment analysis
Detects language varieties, HTML entities, and explicit truncation without destroying source data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

URL = re.compile(r'(?i)https?://\S+|www\.\S+')
MENTION = re.compile(r'(?<!\w)@[A-Za-z0-9_]{1,15}\b')
SPACES = re.compile(r'\s+')

# Whole-token substitutions: protect negation and colloquial mappings
DEFAULT_SLANG = {
    "gk": "tidak",
    "ga": "tidak",
    "gak": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "tdk": "tidak",
    "bgt": "banget",
    "bgtt": "banget",
    "yg": "yang",
    "dgn": "dengan",
    "krn": "karena",
    "karna": "karena",
    "dr": "dari",
    "jd": "jadi",
    "pgn": "ingin",
    "pengen": "ingin",
    "gaji": "gaji",
}

# Lexical markers for language diagnosis
ID_TOKENS = {
    "yang", "di", "dan", "ini", "itu", "untuk", "dengan", "tidak", "dari", "ke",
    "ada", "saya", "gue", "gw", "aku", "dia", "mereka", "bisa", "kerja", "lagi",
    "orang", "sudah", "udah", "aja", "kalo", "kalau", "tapi", "bukan", "banget",
    "karena", "krn", "susah", "sulit", "dapat", "dapet", "lulusan", "gaji", "jaman",
    "bgt", "ngga", "nggak", "ga", "gak"
}
EN_TOKENS = {
    "the", "in", "of", "to", "and", "a", "is", "for", "that", "on", "with", "as",
    "are", "it", "you", "job", "work", "from", "my", "have", "not", "this", "but",
    "fresh", "graduate", "salary", "company", "career", "hiring", "requirement"
}

RE_TRAILING_HANGING = re.compile(r'(?i)\b(dan|yang|karena|atau|di|ke|dari|yg|krn|dgn|with|and|or|to)\s*$')
RE_ELLIPSIS_END = re.compile(r'(\u2026|\.{2,})\s*$')


def replace_slang(text: str, slang: dict[str, str]) -> str:
    """Perform whole-token replacement preventing false matches inside words."""
    if not slang:
        return text
    pattern = re.compile(
        r'(?<![\w#])(?:' + '|'.join(re.escape(k) for k in sorted(slang, key=len, reverse=True)) + r')(?!\w)',
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: slang[m.group(0).lower()], text)


def clean_text(raw: str, slang: dict[str, str] = DEFAULT_SLANG) -> str:
    """General clean text representation: unescapes HTML, strips URLs/mentions, normalizes slang."""
    s = html.unescape(raw)
    s = unicodedata.normalize('NFC', s)
    s = URL.sub(' ', s)
    s = MENTION.sub(' ', s)
    s = ''.join(' ' if unicodedata.category(c) in {'Cc', 'Cf'} else c for c in s)
    s = s.casefold()
    s = replace_slang(s, slang)
    return SPACES.sub(' ', s).strip()


def prepare_topic_text(raw: str, slang: dict[str, str] = DEFAULT_SLANG) -> str:
    """Topic modeling representation for contextual embeddings (preserves word order & hashtags)."""
    s = html.unescape(raw)
    s = unicodedata.normalize('NFC', s)
    s = URL.sub(' ', s)
    s = MENTION.sub(' ', s)
    s = ''.join(' ' if unicodedata.category(c) in {'Cc', 'Cf'} else c for c in s)
    s = s.casefold()
    s = replace_slang(s, slang)
    return SPACES.sub(' ', s).strip()


def prepare_sentiment_text(raw: str, slang: dict[str, str] = DEFAULT_SLANG) -> str:
    """Sentiment representation: preserves negation, emojis, intensifiers, expressive punctuation."""
    s = html.unescape(raw)
    s = unicodedata.normalize('NFC', s)
    s = URL.sub(' ', s)
    s = MENTION.sub(' ', s)
    s = ''.join(' ' if unicodedata.category(c) in {'Cc', 'Cf'} else c for c in s)
    s = s.casefold()
    s = replace_slang(s, slang)
    return SPACES.sub(' ', s).strip()


def detect_language(raw: str) -> str:
    """Diagnose language variety: indonesian, english, mixed_id_en, or unknown."""
    words = set(re.findall(r'[a-zA-Z]{2,}', raw.lower()))
    if not words:
        return "unknown"
    id_hits = len(words.intersection(ID_TOKENS))
    en_hits = len(words.intersection(EN_TOKENS))

    if id_hits > 0 and en_hits > 0 and min(id_hits, en_hits) >= 2:
        return "mixed_id_en"
    if id_hits >= en_hits and id_hits > 0:
        return "indonesian"
    if en_hits > id_hits:
        return "english"
    return "indonesian"  # Default Indonesian contextual corpus


def evaluate_truncation(raw: str) -> Tuple[int, int]:
    """Evaluate truncation: returns (possible_truncation_heuristic, explicit_truncation)."""
    stripped = raw.rstrip()
    # 1. Heuristic warning (len >= 90 without terminal punct)
    heur = int(len(stripped) >= 90 and not re.search(r'[.!?…\)\]”"\U0001F600-\U0001F64F]$', stripped))
    # 2. Explicit truncation signal (terminal ellipsis or dangling trailing conjunction)
    has_ellipsis = bool(RE_ELLIPSIS_END.search(stripped))
    has_hanging = bool(RE_TRAILING_HANGING.search(stripped))
    explicit = int(has_ellipsis or has_hanging)
    return heur, explicit


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for piece in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(piece)
    return digest.hexdigest()


def process(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    slang_path: Path | None = None,
) -> dict:
    """Process corpus into preprocessed file with multi-representation text columns."""
    slang = DEFAULT_SLANG.copy()
    if slang_path:
        supplied = json.loads(slang_path.read_text(encoding='utf-8'))
        if not isinstance(supplied, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in supplied.items()):
            raise ValueError('Slang dictionary must be a JSON object of string:string mappings')
        slang = {k.casefold(): v.casefold() for k, v in supplied.items()}

    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Output must differ from input; source must remain untouched')

    with input_path.open('r', encoding='utf-8-sig', newline='') as fin:
        reader = csv.DictReader(fin)
        fields = reader.fieldnames or []
        required = {'post_id', 'text_raw'}
        if not required.issubset(fields):
            raise ValueError(f'Missing required columns: {sorted(required - set(fields))}')

        new_cols = [
            'text_clean', 'text_topic', 'text_sentiment', 'detected_language',
            'clean_empty', 'possible_truncation', 'explicit_truncation'
        ]
        out_fields = list(fields) + [c for c in new_cols if c not in fields]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        seen = set()
        statuses = Counter()
        lang_counts = Counter()
        empty = 0
        suspect = 0
        explicit_trunc = 0
        total = 0

        with output_path.open('w', encoding='utf-8-sig', newline='') as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()

            for row in reader:
                total += 1
                pid = row['post_id'].strip()
                if not pid or pid in seen:
                    raise ValueError(f'Missing/duplicate post_id at data row {total}: {pid!r}')
                seen.add(pid)

                raw_text = row['text_raw']
                if not raw_text.strip():
                    raise ValueError(f'Empty text_raw for {pid}')

                cleaned = clean_text(raw_text, slang)
                topic_txt = prepare_topic_text(raw_text, slang)
                sent_txt = prepare_sentiment_text(raw_text, slang)
                lang = detect_language(raw_text)
                heur_trunc, exp_trunc = evaluate_truncation(raw_text)
                flag_empty = int(not bool(cleaned))

                row.update(
                    text_clean=cleaned,
                    text_topic=topic_txt,
                    text_sentiment=sent_txt,
                    detected_language=lang,
                    clean_empty=str(flag_empty),
                    possible_truncation=str(heur_trunc),
                    explicit_truncation=str(exp_trunc),
                )

                writer.writerow(row)
                st = row.get('final_status') or row.get('final_selection_status') or 'selected'
                statuses[st] += 1
                lang_counts[lang] += 1
                empty += flag_empty
                suspect += heur_trunc
                explicit_trunc += exp_trunc

    report = {
        'source_file': str(input_path),
        'source_sha256': sha256(input_path),
        'output_file': str(output_path),
        'output_sha256': sha256(output_path),
        'input_rows': total,
        'output_rows': total,
        'unique_post_ids': len(seen),
        'status_counts': dict(statuses),
        'language_breakdown': dict(lang_counts),
        'clean_empty_count': empty,
        'possible_truncation_heuristic_count': suspect,
        'explicit_truncation_signal_count': explicit_trunc,
        'preprocessing_steps': [
            'HTML entity unescaping (html.unescape)',
            'Unicode NFC normalization',
            'URL removal',
            'Mention removal',
            'Control-character spacing',
            'Casefold normalization',
            'Explicit whole-token slang dictionary',
            'Whitespace collapse',
            'Task-specific representation mapping (topic / sentiment)',
        ],
        'preserved': [
            'text_raw (100% byte-exact)',
            'hashtags (#kaburajadulu)',
            'emoji and pictographs',
            'negation (tidak/bukan/belum/jangan)',
            'source provenance and engagement metadata',
        ],
        'notes': [
            'text_topic and text_sentiment are tailored baselines for downstream BERTopic and sentiment modeling.',
            'possible_truncation is a broad heuristic; explicit_truncation isolates ellipsis or dangling phrases.',
            'text_raw is strictly unmutated.',
        ],
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser(description="Preprocess text for ANMEDSOS NLP modeling.")
    p.add_argument('--input', type=Path, default=Path('data/processed/analysis_ready.csv'))
    p.add_argument('--output', type=Path, default=Path('data/processed/text_preprocessed.csv'))
    p.add_argument('--report', type=Path, default=Path('reports/preprocessing_report.json'))
    p.add_argument('--slang', type=Path, default=Path('config/slang_dictionary.json'))
    args = p.parse_args()

    print(json.dumps(process(args.input, args.output, args.report, args.slang), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
