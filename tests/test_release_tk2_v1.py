"""Tests for the frozen TK-2 Release v1 dataset (data/releases/tk2_v1/)."""
import csv
import hashlib
import json
from pathlib import Path
import pytest

from config.settings import PROJECT_ROOT

RELEASE_DIR = PROJECT_ROOT / "data" / "releases" / "tk2_v1"
CORPUS_PATH = RELEASE_DIR / "corpus.csv"
PREPROCESSED_PATH = RELEASE_DIR / "preprocessed.csv"
EXCLUSION_PATH = RELEASE_DIR / "exclusion_log.csv"
MANIFEST_PATH = RELEASE_DIR / "manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TestReleaseTK2V1:
    """Quality and regression assertions for TK-2 Release v1."""

    def test_release_files_exist(self):
        assert CORPUS_PATH.exists(), "corpus.csv must exist in release"
        assert PREPROCESSED_PATH.exists(), "preprocessed.csv must exist in release"
        assert EXCLUSION_PATH.exists(), "exclusion_log.csv must exist in release"
        assert MANIFEST_PATH.exists(), "manifest.json must exist in release"

    def test_record_counts_and_uniqueness(self):
        with CORPUS_PATH.open(encoding="utf-8-sig", newline="") as f:
            corpus_rows = list(csv.DictReader(f))
        with PREPROCESSED_PATH.open(encoding="utf-8-sig", newline="") as f:
            prep_rows = list(csv.DictReader(f))
        with EXCLUSION_PATH.open(encoding="utf-8-sig", newline="") as f:
            excl_rows = list(csv.DictReader(f))

        assert len(corpus_rows) == 1491, f"Expected 1491 rows, got {len(corpus_rows)}"
        assert len(prep_rows) == 1491, f"Expected 1491 rows in preprocessed, got {len(prep_rows)}"
        assert len(excl_rows) == 1, f"Expected 1 row in exclusion log, got {len(excl_rows)}"

        corpus_ids = [r["post_id"] for r in corpus_rows]
        prep_ids = [r["post_id"] for r in prep_rows]

        assert len(set(corpus_ids)) == 1491, "All post_ids in corpus must be unique"
        assert corpus_ids == prep_ids, "Post IDs must be in exact same order across corpus and preprocessed"

    def test_url_only_post_excluded(self):
        with CORPUS_PATH.open(encoding="utf-8-sig", newline="") as f:
            corpus_rows = list(csv.DictReader(f))
        with EXCLUSION_PATH.open(encoding="utf-8-sig", newline="") as f:
            excl_rows = list(csv.DictReader(f))

        corpus_ids = {r["post_id"] for r in corpus_rows}
        assert "2030131219137278032" not in corpus_ids, "URL-only post must not be in final corpus"

        excl_ids = {r["post_id"] for r in excl_rows}
        assert "2030131219137278032" in excl_ids, "URL-only post must be recorded in exclusion log"
        assert excl_rows[0]["exclusion_reason"] == "text_empty_after_preprocessing"

    def test_no_empty_text_in_preprocessed(self):
        with PREPROCESSED_PATH.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                clean = row.get("text_clean", "")
                assert clean and clean.strip() != "", f"Empty text_clean found in post {row['post_id']}"
                assert row.get("clean_empty") == "0" or row.get("clean_empty") == 0

    def test_manifest_integrity_and_hashes(self):
        with MANIFEST_PATH.open(encoding="utf-8") as f:
            m = json.load(f)

        assert m["release_version"] == "tk2_v1"
        assert m["selection_composition"]["total_corpus_rows"] == 1491
        assert m["selection_composition"]["excluded_url_only_count"] == 1

        # Check hashes
        assert m["release_files"]["corpus_csv"]["sha256"] == sha256_file(CORPUS_PATH)
        assert m["release_files"]["preprocessed_csv"]["sha256"] == sha256_file(PREPROCESSED_PATH)
        assert m["release_files"]["exclusion_log_csv"]["sha256"] == sha256_file(EXCLUSION_PATH)

    def test_temporal_bounds_strict(self):
        with CORPUS_PATH.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                d = r["timestamp_wib"][:10]
                assert "2026-01-01" <= d <= "2026-10-07", f"Date {d} outside observed research window"

    def test_rq_coverage_improvement(self):
        with CORPUS_PATH.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        emp = sum(int(r["employment_issue"]) for r in rows)
        asp = sum(int(r["abroad_aspiration"]) for r in rows)
        disc = sum(int(r["abroad_discourse"]) for r in rows)
        link = sum(int(r["issue_abroad_link"]) for r in rows)

        at_least_one = sum(
            1 for r in rows
            if int(r["employment_issue"]) or int(r["abroad_aspiration"]) or int(r["abroad_discourse"]) or int(r["issue_abroad_link"])
        )

        assert emp >= 900, "Refined RQ1 should recover false negatives on hiring/job search"
        assert asp >= 200, "Refined RQ2 should capture unhashtagged personal aspirations"
        assert at_least_one / len(rows) > 0.90, "At least 90% of corpus should have actionable RQ labels"
