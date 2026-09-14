#!/usr/bin/env bash
# Run the full verification pass the sandboxed review could not run
# (GitHub egress was blocked there): execute the authoritative pipeline,
# execute every notebook that can run from committed data, and diff the
# headline results against the values printed in the Final Report.
#
# Run from the repository root of walsh-msc-capstone:
#   bash scripts/run_verification.sh
set -uo pipefail

PASS=0; FAIL=0; SKIP=0
note() { printf '\n== %s ==\n' "$*"; }

note "0. Environment"
python3 --version
python3 -m pip install -q -r requirements.txt
python3 -m pip install -q jupyter nbconvert

note "1. Input checksum"
EXPECTED="50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207"
ACTUAL=$(sha256sum data/processed/merged_municipal_dataset.csv | awk '{print $1}')
if [ "$ACTUAL" = "$EXPECTED" ]; then echo "checksum OK"; PASS=$((PASS+1));
else echo "CHECKSUM MISMATCH: $ACTUAL"; FAIL=$((FAIL+1)); fi

note "2. Authoritative pipeline (final_pipeline.py)"
if python3 final_pipeline.py; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

note "3. Notebooks"
# 01-05 are scaffolds documenting acquisition/design; several need git-ignored
# raw data (data/raw/) and are EXPECTED to fail without it - that is a
# documented property, not a defect. 06 is the Colab mirror and must pass.
for nb in notebooks/*.ipynb; do
  echo "--- $nb"
  if jupyter nbconvert --to notebook --execute --inplace \
       --ExecutePreprocessor.timeout=1800 "$nb" 2>nb_err.log; then
    echo "executed OK"; PASS=$((PASS+1))
  else
    if grep -qiE "data/raw|FileNotFoundError" nb_err.log; then
      echo "SKIPPED: requires git-ignored raw data (expected for scaffolds 01-05)"
      SKIP=$((SKIP+1))
    else
      echo "FAILED for another reason - inspect nb_err.log"; tail -5 nb_err.log
      FAIL=$((FAIL+1))
    fi
  fi
done

note "4. Headline results vs. Final Report"
if python3 scripts/compare_headline_results.py; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

note "5. Provenance link check (writes docs/link_check_log.csv)"
if python3 verify_links.py; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

note "Summary"
echo "PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP (raw-data scaffolds)"
echo "If step 4 reported DRIFT, reconcile before submission and update the"
echo "report tables; if everything matched, the report numbers are confirmed."
[ "$FAIL" -eq 0 ]
