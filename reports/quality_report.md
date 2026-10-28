# ANMEDSOS TK-2 Data Collection Pipeline Quality Report

**Verification Status:** `PASS` ✅
**Generated:** 2026-10-28T20:26:50.645698

## 1. Executive Summary & Baseline Reproduction

| Metric | Expected Baseline | Actual Reproduced | Status |
|:---|:---:|:---:|:---:|
| RAW Records Stored | 3,292 | 3,292 | PASS ✅ |
| Unique Valid Tweets (WIB) | 1,781 | 1,781 | PASS ✅ |
| Heuristic Candidates (`candidate_unverified`) | 936 | 936 | PASS ✅ |
| Manually Confirmed Relevant (`confirmed_relevant`) | 64 | 64 | PASS ✅ |
| Total Analysis Candidates (`analysis_ready.csv`) | 1,000 | 1,000 | PASS ✅ |

> [!NOTE]
> `data/processed/analysis_ready.csv` constitutes an **automatically pre-screened candidate corpus (1,000 tweets)** combining 64 human-audited relevant posts and 936 high-confidence heuristic candidates, NOT 1,000 fully human-verified records. No text preprocessing has been performed, preserving exact raw text for downstream BERTopic and sentiment analysis.

## 2. Temporal Distribution (Asia/Jakarta WIB)

Research period covers January 1, 2026 to October 25, 2026 inclusive.

| Month | RAW Posts | Unique Valid | Candidate (Heuristic) | Confirmed Relevant | Needs Review | Auto Excluded | Analysis Ready |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-01** | 434 | 218 | 104 | 11 | 78 | 15 | **115** |
| **2026-02** | 376 | 185 | 107 | 8 | 57 | 10 | **115** |
| **2026-03** | 279 | 131 | 73 | 7 | 43 | 7 | **80** |
| **2026-04** | 298 | 172 | 80 | 6 | 64 | 18 | **86** |
| **2026-05** | 290 | 186 | 84 | 6 | 67 | 24 | **90** |
| **2026-06** | 317 | 196 | 100 | 9 | 69 | 17 | **109** |
| **2026-07** | 317 | 213 | 119 | 6 | 66 | 19 | **125** |
| **2026-08** | 334 | 203 | 104 | 6 | 77 | 15 | **110** |
| **2026-09** | 315 | 137 | 66 | 2 | 60 | 6 | **68** |
| **2026-10** | 321 | 140 | 99 | 3 | 37 | 1 | **102** |

## 3. Screening Rule & Status Breakdown

### Status Counts in `data/interim/screened_candidates.csv`

- **`auto_excluded`**: 132 (7.4%)
- **`candidate_unverified`**: 936 (52.6%)
- **`confirmed_excluded`**: 31 (1.7%)
- **`confirmed_relevant`**: 64 (3.6%)
- **`needs_review`**: 618 (34.7%)

### Heuristic Rules Assignment (`auto_reason`)

- `abroad_without_clear_work`: 230
- `employment_context`: 1,027
- `no_employment_topic`: 90
- `possible_incidental_mention`: 5
- `possible_promo_or_event`: 8
- `possible_recruitment_promotion`: 6
- `too_short`: 42
- `work_context_not_specific`: 373

### Manual Audit Resolution (`manual_labels.csv`)

- **Historical Audit Sample (100 tweets):**
  - **64 relevant** (`confirmed_relevant`)
  - **31 irrelevant** (`confirmed_excluded`)
  - **5 requiring additional context** (borderline/undecided cases documented separately rather than inventing row-level labels)
- **Definitive Labels in `manual_labels.csv`:**
  - **95 definitive labels stored**
  - `exclude`: 31
  - `include`: 64

## 4. Query Group Representation in Analysis Ready Corpus

| Group | Description | Matched Occurrences in Corpus |
|:---|:---|:---:|
| **Group A** | General job seeking & career entry | 151 |
| **Group B** | Employment hardship, unemployment, layoffs, low wages | 538 |
| **Group C** | Working abroad & #KaburAjaDulu migration aspirations | 313 |
| **Group D** | English-language Indonesian employment terms | 8 |

## 5. Data Integrity Audit

- **Missing required fields in raw:** 0
- **Date bounds enforcement:** 100% of unique records fall strictly within `2026-01-01` and `2026-10-25` (WIB).
- **ID Uniqueness:** 0 duplicates in `data/processed/analysis_ready.csv` (1,000 unique `post_id`).
- **Text Integrity:** Raw text preserved without mutation, lowercasing, or regex cleaning.
- **Offline Reproducibility:** Entire pipeline runs in pure offline mode without network dependencies.

## 6. Observed Temporal Coverage vs. Research Window

- **Intended Research Window:** 2026-01-01 to 2026-10-25 (298 days)
- **Actual Observed Coverage:** 2026-01-01 to 2026-10-09 (123 days with sampled posts)
- **Sampling Gap (Days not sampled):** 175 days across periodic crawler windows.
- **October Cutoff Nuance:** Crawler sampled October 1–8, 2026. Days October 9–25 were not sampled.
- **Methodological Note:** *Although the research study design targets January 1 to October 25, 2026 (WIB), the actual data collection executed a weekly window sampling schedule. Specifically, in October 2026, data was sampled between October 1 and October 8. Days from October 9 through October 25, 2026 were not sampled by executed crawler tasks. Therefore, observed coverage must be reported as January 1 to October 7/8, 2026, rather than claiming continuous daily sampling through October 25.*

## 7. Semantic Screening & Research Quality Evaluation

- **Classifier Identifier:** `anmedsos-rule-hybrid-v1` (Deterministic local rule & lexical-discourse classifier; operates offline without external LLM API or neural embedding inference)
- **Total Records Evaluated with Semantic Model:** 1,781
- **Independent Stratified Evaluation Sample Generated:** `/Users/reginaaruan/Documents/ANMEDSOS/data/interim/evaluation_sample.csv` (N=150, seed=42, un-prefilled)
- **Benchmark against Historical Manual Ground Truth (N=95):**
  - True Positives (TP): 63 | False Positives (FP): 25
  - False Negatives (FN): 1 | True Negatives (TN): 6
  - **Precision:** 0.7159 | **Recall:** 0.9844 | **F1-Score:** 0.8289
  - **Abstention / Review Rate:** 0.0000

## 8. Multi-Label Research Question (RQ) Coverage

| Research Question | Core Label | Posts Count | Research Readiness |
|:---|:---|:---:|:---|
| **RQ1 (Employment Concerns)** | `employment_issue` | 713 | Ready for Topic Modeling (BERTopic) |
| **RQ2 (Personal Aspirations)** | `abroad_aspiration` | 189 | Ready for Qualitative & Aspiration Profiling |
| **RQ2 (Public Discourse)** | `abroad_discourse` | 441 | Ready for Societal Discourse Exploration |
| **RQ2 (Domestic-Abroad Link)** | `issue_abroad_link` | 6 | Provisional (6 single-tweet explicit causal links; RQ3 sentiment analysis NOT yet executed) |

## 9. Final Research Corpus Reconciliation

- **Total Final Corpus Records:** 1,492 tweets (`data/processed/final_corpus.csv`)
- **Confirmed Human Relevant:** 64 tweets (protected)
- **Provisional Model Included:** 1,428 tweets (relevance-screened)
- **Human Excluded Kept Out:** 100% (31/31 historical manual excludes excluded)
- **SHA-256 Digest:** `4ea0ae5ea5efd19afa5d9ca8bba995a6a96bfd25bd7105137ae70d1fcd398b9c`
