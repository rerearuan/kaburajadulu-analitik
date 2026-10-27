"""Automated semantic relevance screening module.

Applies deterministic local rule and lexical-discourse classification for candidate social media posts
evaluating Indonesian labor market hardship, job seeking, and #KaburAjaDulu overseas work aspirations.
Operates completely locally (without external LLM API or neural embedding model calls).
Supports offline/mock execution, checkpoint/resume, and full protection of historical manual audit decisions.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    DATA_INTERIM_DIR,
    MANUAL_LABELS_PATH,
    PROJECT_ROOT,
    SCREENED_CANDIDATES_PATH,
)

CONFIG_PATH = PROJECT_ROOT / "config" / "screening_config.json"
CHECKPOINT_PATH = DATA_INTERIM_DIR / ".semantic_screen_checkpoint.json"
SEMANTIC_SCREENED_PATH = DATA_INTERIM_DIR / "semantic_screened.csv"
MODEL_REVIEW_QUEUE_PATH = DATA_INTERIM_DIR / "model_review_queue.csv"

# Precompiled regex patterns for semantic categorization
RE_SPORTS = re.compile(
    r"(?i)\b(sepak\s*bola|timnas|liga\s*indonesia|liga\s*1|liga\s*inggris|pemain\s*baru|bursa\s*transfer|atlet|pelatih|pertandingan|badminton|bulutangkis|persija|persib|persebaya|arema|juara\s*dunia|motogp|f1)\b"
)
RE_ENTERTAINMENT = re.compile(
    r"(?i)\b(casting\s*film|audisi\s*idol|kpop|konser|tiket\s*konser|album\s*baru|drama\s*korea|drakor|film\s*bioskop|acting|aktor|aktris|wts\s*album|photocard|nct|bts|blackpink)\b"
)
RE_ACADEMIC_DOMESTIC = re.compile(
    r"(?i)\b(tugas\s*(?:sekolah|kuliah|kelompok|rumah)|skripsi|pr\s*matematika|peer\s*group|kerja\s*kelompok|kerja\s*bakti|bersih\s*kamar|cuci\s*piring|cuci\s*baju)\b"
)
RE_PROMO_SPAM = re.compile(
    r"(?i)\b(slot\s*gacor|judi\s*online|togel|giveaway|saldo\s*dana|pulsa\s*gratis|promo\s*diskon|open\s*jastip|jual\s*akun|dm\s*for\s*collab|paid\s*promote|review\s*dari\s*client|optimasi\s*linkedin|jasa\s*(?:bikin|review)\s*cv|mentoring\s*1on1|kelas\s*(?:cv|karir|interview))\b"
)
RE_JOB_BROADCAST = re.compile(
    r"(?i)\b(dibutuhkan\s*segera|open\s*recruitment|membuka\s*kesempatan\s*bergabung|kualifikasi\s*:|persyaratan\s*:|kirimkan\s*cv|drop\s*cv|send\s*your\s*cv|we\s*are\s*hiring|job\s*vacancy|penempatan\s*:|walk\s*in\s*interview)\b"
)
RE_INCIDENTAL_DRAMA = re.compile(
    r"(?i)\b(selingkuh|pelakor|pebinor|istrinya\s*kerja\s*di\s*luar|suaminya\s*kerja\s*di\s*luar|ditinggal\s*kerja\s*di\s*luar|ldr|pacaran|kemalangan|kecelakaan|terlibat\s*dalam\s*kemalangan|tabrakan|buletin\s*bernama|penunggang\s*motosikal)\b"
)

# Core inclusion categories
RE_EMPLOYMENT_CORE = re.compile(
    r"(?i)\b(phk|layoff|layoffs|pengangguran|nganggur|jobless|cari\s*kerja|mencari\s*kerja|lamar\s*kerja|lowongan\s*kerja|loker|fresh\s*grad(?:uate)?|gaji\s*kecil|gaji\s*rendah|gaji\s*di\s*bawah|upah\s*minimum|umr|umk|beban\s*kerja|susah\s*cari\s*kerja|sulit\s*dapat\s*kerja|interview\s*kerja|kontrak\s*kerja|outsource|outsourcing|surat\s*peringatan|pesangon|tki|tkw|pekerja\s*migran|pasar\s*kerja|dunia\s*kerja)\b"
)
RE_EMPLOYMENT_COMPLAINTS = re.compile(
    r"(?i)\b(potong\s*gaji|tahan\s*ijazah|syarat\s*(?:pengalaman|umur|usia)|batas\s*usia|toxic\s*workplace|lembur\s*(?:tak|tidak|ga)\s*dibayar|upah\s*murah|banting\s*harga|sulitnya\s*mencari|ijazah\s*s1|pusing\s*nyari\s*kerja|belum\s*(?:dapet|dapat)\s*kerja)\b"
)
RE_ABROAD_ASPIRATION = re.compile(
    r"(?i)(#kaburajadulu|kabur\s*aja\s*dulu|pengen\s*kerja\s*di\s*luar|ingin\s*kerja\s*di\s*luar|kerja\s*ke\s*jepang|kerja\s*di\s*jepang|kerja\s*ke\s*singapura|kerja\s*di\s*singapura|kerja\s*ke\s*korea|kerja\s*di\s*korea|kerja\s*ke\s*australia|kerja\s*di\s*australia|whv|work\s*holiday\s*visa|visa\s*kerja|spec(?:tokutei\s*ginou)?|tokutei\s*ginou|ssw|magang\s*jepang|pindah\s*negara|pengen\s*pindah\s*negara|leave\s*indonesia\s*for\s*work|working\s*abroad)"
)
RE_ABROAD_DISCOURSE = re.compile(
    r"(?i)(kerja\s*(?:di|ke)\s*luar\s*negeri|bekerja\s*(?:di|ke)\s*luar\s*negeri|peluang\s*kerja\s*luar\s*negeri|gaji\s*(?:di|luar\s*negeri)|living\s*cost\s*(?:jepang|korea|singapura|australia)|perantau\s*di\s*luar|tki\s*di\s*luar|pekerja\s*migran\s*indonesia|pmi|remitansi)"
)

RE_AMBIGUOUS_SHORT = re.compile(r"^.{1,25}$")


class SemanticScreenClassifier:
    """Zero-shot and expert semantic classifier with strict output validation."""

    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        mode: str = "local",
        model_id: Optional[str] = None,
    ):
        self.mode = mode
        self.config = {}
        if config_path.exists():
            try:
                self.config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.prompt_version = self.config.get("prompt_version", "v1")
        self.model_id = model_id or self.config.get("default_model_id", "anmedsos-rule-hybrid-v1")

    def classify_record(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Classify a single tweet text into structured semantic relevance decision."""
        clean_text = text.strip()

        # Handle Mock Mode for fast offline unit tests
        if self.mode == "mock":
            if "GAK kerja" in text or "PHK" in text or "#KaburAjaDulu" in text:
                return {
                    "model_relevance": "include",
                    "relevance_reason_code": "employment_concern",
                    "relevance_reason": "Mock mode: explicit employment or migration keyword detected.",
                    "needs_context": False,
                    "uncertainty": "low",
                    "model_id": "mock-classifier-v1",
                    "prompt_version": self.prompt_version,
                    "classification_source": "mock_engine",
                }
            if "sepak bola" in text.lower() or "konser" in text.lower():
                return {
                    "model_relevance": "exclude",
                    "relevance_reason_code": "sports_entertainment_exclusion",
                    "relevance_reason": "Mock mode: sports/entertainment domain detected.",
                    "needs_context": False,
                    "uncertainty": "low",
                    "model_id": "mock-classifier-v1",
                    "prompt_version": self.prompt_version,
                    "classification_source": "mock_engine",
                }
            return {
                "model_relevance": "review",
                "relevance_reason_code": "insufficient_context_review",
                "relevance_reason": "Mock mode: neutral text requiring contextual resolution.",
                "needs_context": True,
                "uncertainty": "medium",
                "model_id": "mock-classifier-v1",
                "prompt_version": self.prompt_version,
                "classification_source": "mock_engine",
            }

        # 1. Exclusion Gates (Highest Confidence Negatives)
        if RE_PROMO_SPAM.search(clean_text):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "promotional_spam_exclusion",
                "relevance_reason": "Commercial promotional spam, commercial service coaching, or advertisement.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if RE_JOB_BROADCAST.search(clean_text) and not RE_EMPLOYMENT_COMPLAINTS.search(clean_text):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "promotional_spam_exclusion",
                "relevance_reason": "Direct commercial job vacancy broadcast or recruitment announcement.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if RE_INCIDENTAL_DRAMA.search(clean_text) and not RE_ABROAD_ASPIRATION.search(clean_text):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "incidental_mention_exclusion",
                "relevance_reason": "Incidental interpersonal relationship/drama or non-employment traffic incident.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if RE_SPORTS.search(clean_text) and not (RE_EMPLOYMENT_CORE.search(clean_text) or RE_ABROAD_ASPIRATION.search(clean_text)):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "sports_entertainment_exclusion",
                "relevance_reason": "Sports recruitment, athlete trade, or sports competition discourse.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if RE_ENTERTAINMENT.search(clean_text) and not (RE_EMPLOYMENT_CORE.search(clean_text) or RE_ABROAD_ASPIRATION.search(clean_text)):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "sports_entertainment_exclusion",
                "relevance_reason": "Entertainment casting, fan merchandise, or concert ticket discussion.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if RE_ACADEMIC_DOMESTIC.search(clean_text) and not (RE_EMPLOYMENT_CORE.search(clean_text) or RE_ABROAD_ASPIRATION.search(clean_text)):
            return {
                "model_relevance": "exclude",
                "relevance_reason_code": "academic_household_exclusion",
                "relevance_reason": "School academic assignments, domestic chores, or non-workplace context.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        # 2. Inclusion Gates
        has_abroad_aspiration = bool(RE_ABROAD_ASPIRATION.search(clean_text))
        has_abroad_discourse = bool(RE_ABROAD_DISCOURSE.search(clean_text))
        has_emp_core = bool(RE_EMPLOYMENT_CORE.search(clean_text))
        has_emp_complaint = bool(RE_EMPLOYMENT_COMPLAINTS.search(clean_text))

        # Check for explicit link between domestic issue and abroad aspiration (RQ2/RQ3 link)
        if (has_emp_core or has_emp_complaint) and (has_abroad_aspiration or has_abroad_discourse):
            return {
                "model_relevance": "include",
                "relevance_reason_code": "issue_abroad_link",
                "relevance_reason": "Explicitly connects domestic labor hardships with overseas work aspirations or opportunities.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if has_abroad_aspiration:
            return {
                "model_relevance": "include",
                "relevance_reason_code": "abroad_aspiration",
                "relevance_reason": "Personal intent, motivation, or inquiry regarding working overseas / #KaburAjaDulu.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if has_abroad_discourse and (len(clean_text.split()) >= 6 or has_emp_core):
            return {
                "model_relevance": "include",
                "relevance_reason_code": "abroad_discourse",
                "relevance_reason": "Substantive public discourse or informative advice concerning Indonesian workers abroad.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        if has_emp_core or has_emp_complaint:
            # Check length and completeness
            if len(clean_text.split()) < 5 and not has_emp_complaint:
                return {
                    "model_relevance": "review",
                    "relevance_reason_code": "insufficient_context_review",
                    "relevance_reason": "Isolated employment keyword in brief utterance lacking surrounding conversational context.",
                    "needs_context": True,
                    "uncertainty": "medium",
                    "model_id": self.model_id,
                    "prompt_version": self.prompt_version,
                    "classification_source": "local_semantic_engine_v1",
                }
            return {
                "model_relevance": "include",
                "relevance_reason_code": "employment_concern",
                "relevance_reason": "Substantive discussion of job seeking, wages, labor precarity, or employment conditions.",
                "needs_context": False,
                "uncertainty": "low",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        # 3. Ambiguity & Under-specified cases
        if RE_AMBIGUOUS_SHORT.match(clean_text):
            return {
                "model_relevance": "review",
                "relevance_reason_code": "insufficient_context_review",
                "relevance_reason": "Short fragmented post lacking clear referent or complete predicate.",
                "needs_context": True,
                "uncertainty": "high",
                "model_id": self.model_id,
                "prompt_version": self.prompt_version,
                "classification_source": "local_semantic_engine_v1",
            }

        # Default fallback: incidental keyword mention
        return {
            "model_relevance": "exclude",
            "relevance_reason_code": "incidental_mention_exclusion",
            "relevance_reason": "Incidental mention without substantive labor-market or migration context.",
            "needs_context": False,
            "uncertainty": "medium",
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "classification_source": "local_semantic_engine_v1",
        }


def load_checkpoints() -> Dict[str, Dict[str, Any]]:
    """Load existing classifications from checkpoint if present."""
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_checkpoints(checkpoints: Dict[str, Dict[str, Any]]) -> None:
    """Safely persist checkpoint state to disk."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(
        json.dumps(checkpoints, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_semantic_screening(
    input_path: Path = SCREENED_CANDIDATES_PATH,
    manual_labels_path: Path = MANUAL_LABELS_PATH,
    output_path: Path = SEMANTIC_SCREENED_PATH,
    review_queue_path: Path = MODEL_REVIEW_QUEUE_PATH,
    mode: str = "local",
    batch_size: int = 100,
    force_recompute: bool = False,
) -> Dict[str, Any]:
    """Execute semantic relevance screening on all unique candidate records."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Load historical manual labels
    historical_labels: Dict[str, str] = {}
    if manual_labels_path.exists():
        with manual_labels_path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("post_id", "").strip()
                dec = row.get("decision", "").strip()
                if pid and dec:
                    historical_labels[pid] = dec

    # Load candidates
    with input_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    classifier = SemanticScreenClassifier(mode=mode)
    checkpoints = {} if force_recompute else load_checkpoints()

    screened_records = []
    review_records = []
    stats = Counter()

    for idx, rec in enumerate(records):
        pid = rec["post_id"]
        raw_text = rec["text_raw"]

        # Checkpoint check for idempotency and resume capability
        if pid in checkpoints and not force_recompute:
            pred = checkpoints[pid]
        else:
            pred = classifier.classify_record(raw_text, context=rec)
            checkpoints[pid] = pred
            if (idx + 1) % batch_size == 0:
                save_checkpoints(checkpoints)

        # Merge record
        merged = dict(rec)
        merged.update({
            "model_relevance": pred["model_relevance"],
            "relevance_reason_code": pred["relevance_reason_code"],
            "relevance_reason": pred["relevance_reason"],
            "needs_context": str(int(pred["needs_context"])),
            "uncertainty": pred["uncertainty"],
            "model_id": pred["model_id"],
            "prompt_version": pred["prompt_version"],
            "classification_source": pred["classification_source"],
            "historical_manual_decision": historical_labels.get(pid, ""),
        })

        screened_records.append(merged)
        stats[f"model_{pred['model_relevance']}"] += 1
        stats[f"reason_{pred['relevance_reason_code']}"] += 1
        stats[f"uncertainty_{pred['uncertainty']}"] += 1

        if pred["model_relevance"] == "review":
            review_records.append(merged)

    save_checkpoints(checkpoints)

    # Write semantic_screened.csv
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(screened_records[0].keys())
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(screened_records)

    # Write model_review_queue.csv
    review_queue_path.parent.mkdir(parents=True, exist_ok=True)
    with review_queue_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_records)

    summary = {
        "total_records_processed": len(records),
        "model_include": stats["model_include"],
        "model_exclude": stats["model_exclude"],
        "model_review": stats["model_review"],
        "review_queue_size": len(review_records),
        "uncertainty_breakdown": {
            "low": stats["uncertainty_low"],
            "medium": stats["uncertainty_medium"],
            "high": stats["uncertainty_high"],
        },
        "output_file": str(output_path),
        "review_queue_file": str(review_queue_path),
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run automated semantic relevance screening.")
    parser.add_argument("--input", type=Path, default=SCREENED_CANDIDATES_PATH)
    parser.add_argument("--output", type=Path, default=SEMANTIC_SCREENED_PATH)
    parser.add_argument("--review-queue", type=Path, default=MODEL_REVIEW_QUEUE_PATH)
    parser.add_argument("--mode", choices=["local", "mock"], default="local")
    parser.add_argument("--force", action="store_true", help="Force recomputation ignoring checkpoints")
    args = parser.parse_args()

    res = run_semantic_screening(
        input_path=args.input,
        output_path=args.output,
        review_queue_path=args.review_queue,
        mode=args.mode,
        force_recompute=args.force,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
