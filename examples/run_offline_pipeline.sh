#!/usr/bin/env bash
# End-to-end offline pipeline reproduction and research-grade preprocessing script
set -euo pipefail

echo "=========================================================="
echo "ANMEDSOS End-to-End Pipeline Reproduction & QA"
echo "=========================================================="

echo "[1/7] Preparing and deduplicating raw records..."
python3 -m src.prepare

echo "[2/7] Screening candidates and integrating manual audit..."
python3 -m src.screen

echo "[3/7] Running automated semantic relevance screening..."
python3 src/semantic_screen.py

echo "[4/7] Multi-label Research Question (RQ) classification..."
python3 src/classify_rq.py

echo "[5/7] Evaluating screening quality and generating stratified sample..."
python3 src/evaluate_screening.py

echo "[6/7] Exporting analysis candidates & final research corpus..."
python3 src/export.py --final-corpus

echo "[7/7] Executing final text preprocessing (multi-representation)..."
python3 src/preprocess_text.py \
  --input data/processed/analysis_ready.csv \
  --output data/processed/text_preprocessed.csv \
  --report reports/preprocessing_report.json \
  --slang config/slang_dictionary.json

python3 src/preprocess_text.py \
  --input data/processed/final_corpus.csv \
  --output data/processed/final_preprocessed.csv \
  --report reports/final_preprocessing_report.json \
  --slang config/slang_dictionary.json

echo "Generating quality and verification reports..."
python3 -m src.quality_report

echo "Running complete test suite..."
python3 -m pytest -v tests/

echo "=========================================================="
echo "Pipeline execution finished successfully!"
echo "Final corpus:       data/processed/final_corpus.csv"
echo "Final preprocessed: data/processed/final_preprocessed.csv"
echo "Quality report:     reports/quality_report.md"
echo "=========================================================="
