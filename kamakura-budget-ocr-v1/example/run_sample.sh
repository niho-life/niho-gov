#!/usr/bin/env bash
set -e
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
GCS_IN="gs://kamakura-budget-input/議会費_sample5.pdf"
GCS_OUT_PREFIX="gs://kamakura-budget-output/vision-results-test/"

python ocr_pipeline.py --gcs_input ${GCS_IN} --gcs_output_prefix ${GCS_OUT_PREFIX} --local ./output_test
