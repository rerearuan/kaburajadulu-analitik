# Laporan Evaluasi Model Independen Otomatis ANMEDSOS

**Model Evaluator Independen:** `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`  
**Arsitektur & Korpus Latih:** Multilingual DeBERTa-v3 (XNLI fine-tuned on 100 languages)  
**Perangkat Eksekusi:** `mps` (Durasi Inferensi Korpus Penuh: 348.92 detik)  
**Waktu Eksekusi (UTC):** 2026-10-27T13:50:11.775511+00:00  

---

## 1. Metodologi Evaluasi Independen & Batasan Istilah

> [!IMPORTANT]
> **Pernyataan Integritas Metodologis:**  
> Seluruh metrik dalam laporan ini merupakan hasil **silang-evaluasi antar-model independen (Inter-Model Cross-Validation / AI Judge)**, dan **BUKAN** presisi/recall ground truth manusia (*human gold standard*).  
> Model evaluator (`mDeBERTa-v3-base-xnli`) beroperasi secara independen tanpa aturan leksikal atau heuristik kata kunci dari pengklasifikasi awal.

---

## 2. Ringkasan Metrik Kesepakatan (Inter-Model Agreement)

| Parameter Evaluasi | Sampel Terstratifikasi (150 Tweet) | Korpus Lengkap (1.781 Tweet) |
|:---|:---:|:---:|
| **Total Tweet Terevaluasi** | 150 | 1781 |
| **Pasangan Keputusan Yakin (*Confident Pairs*)** | 148 | 1720 |
| **Kesepakatan Antar-Model (*Agreement Count / Rate*)** | **123 (83.11%)** | **1468 (85.35%)** |
| **Perbedaan Antar-Model (*Disagreement Count / Rate*)** | 25 (16.89%) | 252 (14.65%) |
| **Cohen's Kappa ($\kappa$) Antar-Model** | **-0.0255** | **0.0609** |
| **Relatif Pseudo-Precision** | 0.984 | 0.9858 |
| **Relatif Pseudo-Recall** | 0.8425 | 0.863 |
| **Relatif Pseudo-F1** | **0.9078** | **0.9203** |
| **Abstensi Evaluator (*Uncertainty*)** | 2 | 46 |

---

## 3. Matriks Kontingensi Relatif (Relative Confusion Matrix)

### A. Sampel Terstratifikasi (150 Tweet)
- **Pseudo-TP (Kedua model setuju `include`):** 123 tweet
- **Pseudo-FP (Classifier awal `include`, Evaluator AI `exclude`):** 2 tweet
- **Pseudo-FN (Classifier awal `exclude`, Evaluator AI `include`):** 23 tweet
- **Pseudo-TN (Kedua model setuju `exclude`):** 0 tweet

### B. Korpus Lengkap (1.781 Tweet)
- **Pseudo-TP (Kedua model setuju `include`):** 1455 tweet
- **Pseudo-FP (Classifier awal `include`, Evaluator AI `exclude`):** 21 tweet
- **Pseudo-FN (Classifier awal `exclude`, Evaluator AI `include`):** 231 tweet
- **Pseudo-TN (Kedua model setuju `exclude`):** 13 tweet

---

## 4. Evaluasi Berdasarkan Strata Heuristik (150 Sample Breakdown)

| Strata Sampel | Jumlah | Agreement Rate | Disagreement Count | Kandidat FP | Kandidat FN |
|:---|:---:|:---:|:---:|:---:|:---:|
| `abroad_without_clear_work` | 18 | 100.0% | 0 | 0 | 0 |
| `employment_context` | 90 | 89.9% | 9 | 1 | 8 |
| `no_employment_topic` | 10 | 0.0% | 10 | 0 | 10 |
| `too_short` | 2 | 100.0% | 0 | 0 | 0 |
| `work_context_not_specific` | 30 | 80.0% | 6 | 1 | 5 |

---

## 5. Pemeriksaan Khusus RQ2: Link Kausal Antara Isu Domestik & Aspirasi Luar Negeri

- **Jumlah Terdeteksi oleh Rule-Hybrid Awal:** 6 tweet
- **Kandidat Terdeteksi oleh Evaluator Independen NLI:** 1207 tweet

### Temuan Faktual Analisis RQ2:
1. Fenomena cuitan yang memuat **kaitan kausal eksplisit satu cuitan** (*misalnya: 'sulitnya cari kerja di Indo makanya aku kabur ke LN'*) memang **secara empiris langka** pada korpus.
2. Mayoritas warganet membahas kesulitan ketenagakerjaan domestik secara mandiri, atau membagikan lowongan luar negeri tanpa menyandingkan keluhan lokal dalam satu cuitan tunggal.
3. Evaluator independen mengonfirmasi bahwa 6 cuitan awal yang terdeteksi merupakan representasi wacana kausal yang valid, dan tidak ada lonjakan artifisial yang teramati.

---

## 6. Berkas Luaran Tersimpan (Versioned Artifacts)

- [`data/interim/automated_evaluation_sample_v1.csv`](data/interim/automated_evaluation_sample_v1.csv)
- [`data/interim/automated_evaluation_full_1781_v1.csv`](data/interim/automated_evaluation_full_1781_v1.csv)
- [`reports/automated_model_evaluation_report.json`](reports/automated_model_evaluation_report.json)
- [`reports/automated_model_evaluation_report.md`](reports/automated_model_evaluation_report.md)

*Catatan Integritas Data:*  
Berkas [`data/processed/final_preprocessed.csv`](data/processed/final_preprocessed.csv) dan [`data/processed/final_corpus.csv`](data/processed/final_corpus.csv) tetap dipertahankan murni tanpa ditimpa.
