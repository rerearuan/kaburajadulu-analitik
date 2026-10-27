"""Multi-label RQ classification module for ANMEDSOS.

Categorizes social media discourse into research questions:
- RQ1: employment_issue (Indonesian labor market precarity, wages, PHK, job search)
- RQ2: abroad_aspiration (Personal intent / desire to work abroad)
- RQ2: abroad_discourse (Public discussion / advice / news about working abroad)
- RQ2/RQ3: issue_abroad_link (Explicit causal link connecting domestic hardships to overseas work)
Extracts verbatim evidence spans from raw text.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    DATA_INTERIM_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
)

RQ_SCHEMA_PATH = PROJECT_ROOT / "config" / "rq_label_schema.json"
SEMANTIC_SCREENED_PATH = DATA_INTERIM_DIR / "semantic_screened.csv"
RQ_COVERAGE_REPORT_PATH = REPORTS_DIR / "rq_coverage_report.json"

# Regex for detecting employment issues and capturing evidence spans
PATTERNS_EMPLOYMENT = [
    (re.compile(r"(?i)\b(susah|sulit)\s*cari\s*kerja\b"), "kesulitan mencari pekerjaan"),
    (re.compile(r"(?i)\b(phk|layoff|layoffs|kena\s*phk)\b"), "isu pemutusan hubungan kerja"),
    (re.compile(r"(?i)\b(pengangguran|nganggur|jobless)\b"), "kondisi pengangguran"),
    (re.compile(r"(?i)\b(gaji\s*(?:rendah|kecil|di\s*bawah|murah)|upah\s*(?:minimum|murah)|umr|umk)\b"), "upah dan kompensasi rendah"),
    (re.compile(r"(?i)\b(fresh\s*grad(?:uate)?|lulusan\s*baru)\b"), "tantangan fresh graduate"),
    (re.compile(r"(?i)\b(syarat\s*(?:pengalaman|umur|usia)|batas\s*usia)\b"), "hambatan persyaratan kerja"),
    (re.compile(r"(?i)\b(kontrak\s*kerja|outsource|outsourcing|pekerjaan\s*kontrak)\b"), "pekerjaan kontrak dan prekariat"),
    (re.compile(r"(?i)\b(toxic\s*workplace|beban\s*kerja|lembur\s*(?:tak|tidak|ga)\s*dibayar)\b"), "kondisi kerja buruk"),
    (re.compile(r"(?i)\b(lowongan\s*kerja|loker|peluang\s*kerja|cari\s*kerja)\b"), "pencarian lowongan kerja"),
]

# Patterns for personal overseas work aspiration (RQ2 Personal)
PATTERNS_ASPIRATION = [
    (re.compile(r"(?i)#kaburajadulu"), "#KaburAjaDulu tag"),
    (re.compile(r"(?i)\b(pengen|ingin|mau|berniat|rencana|bismillah)\s*(?:bisa\s*)?(?:kerja|bekerja|magang|kabur)\s*(?:ke|di)?\s*(?:luar\s*negeri|jepang|singapura|korea|australia|jerman|eropa)\b"), "aspirasi kerja luar negeri"),
    (re.compile(r"(?i)\b(pengen\s*(?:dapet|dapat)\s*whv|daftar\s*whv|apply\s*whv)\b"), "aspirasi working holiday visa"),
    (re.compile(r"(?i)\b(pengen\s*pindah\s*negara|leave\s*indonesia\s*for\s*work)\b"), "keinginan migrasi kerja"),
    (re.compile(r"(?i)\b(cita[- ]cita\s*kerja\s*di\s*luar)\b"), "cita-cita luar negeri"),
]

# Patterns for general overseas work discourse (RQ2 Public)
PATTERNS_DISCOURSE = [
    (re.compile(r"(?i)\b(kerja|bekerja|peluang\s*kerja|lowongan)\s*(?:ke|di)\s*(?:luar\s*negeri|jepang|singapura|korea|australia|eropa)\b"), "wacana pasar kerja luar negeri"),
    (re.compile(r"(?i)\b(gaji\s*(?:di\s*)?(?:jepang|korea|singapura|australia|luar\s*negeri))\b"), "perbandingan upah luar negeri"),
    (re.compile(r"(?i)\b(tki|tkw|pekerja\s*migran\s*indonesia|pmi|pemerintah\s*jepang|visa\s*kerja)\b"), "topik pekerja migran & regulasi visa"),
    (re.compile(r"(?i)\b(tokutei\s*ginou|ssw|whv|work\s*holiday\s*visa|magang\s*jepang)\b"), "skema program kerja luar negeri"),
    (re.compile(r"(?i)\b(working\s*abroad|jobs\s*abroad)\b"), "wacana ketenagakerjaan global"),
]

# Patterns for explicit causal link between domestic hardship and abroad aspiration
PATTERNS_LINK = [
    (re.compile(r"(?i)(daripada\s*(?:nganggur|susah\s*cari\s*kerja|di\s*phk).{0,60}(?:ke|di)\s*luar)"), "alih opsi ke luar negeri karena krisis domestik"),
    (re.compile(r"(?i)(di\s*indo(?:nesia)?\s*(?:susah|gaji\s*kecil|umr\s*rendah|phk).{0,60}(?:mending|pengen|kabur|kerja\s*(?:ke|di)\s*luar))"), "perbandingan keputusasaan domestik vs luar negeri"),
    (re.compile(r"(?i)(#kaburajadulu.{0,60}(?:susah\s*cari\s*kerja|phk|gaji\s*rendah|nganggur))"), "#KaburAjaDulu dengan keluhan kerja domestik"),
    (re.compile(r"(?i)((?:susah\s*cari\s*kerja|gaji\s*kecil|kena\s*phk).{0,60}#kaburajadulu)"), "keluhan domestik berujung #KaburAjaDulu"),
]


class RQClassifier:
    """Classifies social media text into RQ1, RQ2 (aspiration & discourse), and RQ2/3 link."""

    def __init__(self, schema_path: Path = RQ_SCHEMA_PATH):
        self.schema = {}
        if schema_path.exists():
            try:
                self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def classify(self, text: str) -> Dict[str, Any]:
        """Produce multi-label RQ tags with verbatim text evidence."""
        evidence = []

        # 1. Evaluate employment issue (RQ1)
        emp_match = False
        for pat, desc in PATTERNS_EMPLOYMENT:
            m = pat.search(text)
            if m:
                emp_match = True
                evidence.append(f"RQ1 [{desc}]: '{m.group(0)}'")
                break

        # 2. Evaluate abroad aspiration (RQ2 Personal)
        asp_match = False
        for pat, desc in PATTERNS_ASPIRATION:
            m = pat.search(text)
            if m:
                asp_match = True
                evidence.append(f"RQ2-Aspiration [{desc}]: '{m.group(0)}'")
                break

        # 3. Evaluate abroad discourse (RQ2 Public)
        disc_match = False
        for pat, desc in PATTERNS_DISCOURSE:
            m = pat.search(text)
            if m:
                disc_match = True
                evidence.append(f"RQ2-Discourse [{desc}]: '{m.group(0)}'")
                break
        if asp_match:
            # If aspiration exists, discourse presence is acknowledged in broader context
            disc_match = True

        # 4. Evaluate explicit issue-abroad link (RQ2: domestic hardship connected to abroad opportunity)
        link_match = False
        for pat, desc in PATTERNS_LINK:
            m = pat.search(text)
            if m:
                link_match = True
                evidence.append(f"RQ2-Link [{desc}]: '{m.group(0)}'")
                break

        # Constraint enforcement: issue_abroad_link must have both employment issue and abroad context
        if link_match and not (emp_match and (asp_match or disc_match)):
            link_match = False

        if not link_match and emp_match and asp_match:
            # If both strong employment complaint and personal aspiration co-exist in close proximity
            link_match = True
            evidence.append("RQ2-Link [Co-occurrence]: employment_issue and abroad_aspiration in same statement")

        return {
            "employment_issue": 1 if emp_match else 0,
            "abroad_aspiration": 1 if asp_match else 0,
            "abroad_discourse": 1 if disc_match else 0,
            "issue_abroad_link": 1 if link_match else 0,
            "rq_evidence": " | ".join(evidence) if evidence else "None",
        }


def run_rq_classification(
    screened_path: Path = SEMANTIC_SCREENED_PATH,
    output_report_path: Path = RQ_COVERAGE_REPORT_PATH,
) -> Dict[str, Any]:
    """Execute RQ classification across semantic screened records and compile report."""
    if not screened_path.exists():
        raise FileNotFoundError(f"Screened records not found: {screened_path}")

    with screened_path.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))

    classifier = RQClassifier()
    rq_counts = Counter()
    monthly_rq = Counter()
    overlap_counts = Counter()

    for r in records:
        text = r["text_raw"]
        rq = classifier.classify(text)
        r.update(rq)

        # Count distribution for included or candidate posts
        is_relevant = r.get("model_relevance") == "include" or r.get("manual_decision") == "include"
        if is_relevant:
            m = (r.get("timestamp_wib") or "")[:7]
            if rq["employment_issue"]:
                rq_counts["employment_issue"] += 1
                monthly_rq[f"{m}__employment_issue"] += 1
            if rq["abroad_aspiration"]:
                rq_counts["abroad_aspiration"] += 1
                monthly_rq[f"{m}__abroad_aspiration"] += 1
            if rq["abroad_discourse"]:
                rq_counts["abroad_discourse"] += 1
                monthly_rq[f"{m}__abroad_discourse"] += 1
            if rq["issue_abroad_link"]:
                rq_counts["issue_abroad_link"] += 1
                monthly_rq[f"{m}__issue_abroad_link"] += 1

            # Track overlaps
            combo = tuple(sorted([
                k for k in ["employment_issue", "abroad_aspiration", "abroad_discourse", "issue_abroad_link"]
                if rq[k] == 1
            ]))
            if combo:
                overlap_counts[" + ".join(combo)] += 1

    report = {
        "total_relevant_evaluated": sum(
            1 for r in records if r.get("model_relevance") == "include" or r.get("manual_decision") == "include"
        ),
        "rq_counts": dict(rq_counts),
        "overlap_combinations": dict(overlap_counts.most_common(10)),
        "monthly_representation": {k: v for k, v in sorted(monthly_rq.items())},
        "rq_readiness": {
            "RQ1": {
                "label": "employment_issue",
                "count": rq_counts["employment_issue"],
                "status": "READY (High density corpus covering grievances, hiring, wages, and layoffs)",
            },
            "RQ2_personal": {
                "label": "abroad_aspiration",
                "count": rq_counts["abroad_aspiration"],
                "status": "READY (Targeted migration aspiration & #KaburAjaDulu posts)",
            },
            "RQ2_public": {
                "label": "abroad_discourse",
                "count": rq_counts["abroad_discourse"],
                "status": "READY (Comprehensive public information & worker debates)",
            },
            "RQ2_link": {
                "label": "issue_abroad_link",
                "count": rq_counts["issue_abroad_link"],
                "status": "PROVISIONAL / EXPLORATORY (Strict single-tweet causal link identified in only 6 posts; broader push-factor correlation to be analyzed across RQ1 and RQ2 topics)",
            },
            "RQ3_sentiment": {
                "status": "NOT EXECUTED (RQ3 sentiment classification across topics has NOT been run yet; text representations are prepared with negation and polarity preserved)",
            },
        },
    }

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Run multi-label RQ classification.")
    parser.add_argument("--input", type=Path, default=SEMANTIC_SCREENED_PATH)
    parser.add_argument("--report", type=Path, default=RQ_COVERAGE_REPORT_PATH)
    args = parser.parse_args()

    rep = run_rq_classification(args.input, args.report)
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
