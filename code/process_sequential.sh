#!/bin/bash
# Phase 1: Sequential Processing Script for Test4-10
# Processes one test at a time, stops on any error

set -e  # Exit immediately if any command fails

WORKSPACE="/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index"
BACKUP_DIR="$WORKSPACE/Clinical_DB_backup"
RAW_DIR="$WORKSPACE/Results/raw"
CODE_DIR="$WORKSPACE/SW/code"

# Activate conda environment
source ~/miniforge3/etc/profile.d/conda.sh
conda activate atonia

cd "$CODE_DIR"

# Process Test4-10 sequentially
for TEST_NUM in {4..10}; do
    echo ""
    echo "========================================================================"
    echo "PROCESSING TEST${TEST_NUM}"
    echo "========================================================================"
    echo ""

    # Step 1: Create directory and copy EDF
    echo "[Step 1/3] Creating directory and copying EDF..."
    mkdir -p "$RAW_DIR/Test${TEST_NUM}"
    cp "$BACKUP_DIR/Test${TEST_NUM}.EDF" "$RAW_DIR/Test${TEST_NUM}/Test${TEST_NUM}.edf"
    echo "  ✅ EDF copied"

    # Step 2: Generate annotations
    echo "[Step 2/3] Generating annotation files..."
    python3 convert_edf_annotations.py "$RAW_DIR/Test${TEST_NUM}/Test${TEST_NUM}.edf"
    if [ $? -ne 0 ]; then
        echo "  ❌ Failed to generate annotations for Test${TEST_NUM}"
        exit 1
    fi
    echo "  ✅ Annotations generated"

    # Step 3: Run RBDtector analysis
    echo "[Step 3/3] Running RBDtector analysis..."
    python3 generate_results_generic.py ${TEST_NUM}
    if [ $? -ne 0 ]; then
        echo "  ❌ Failed to analyze Test${TEST_NUM}"
        exit 1
    fi
    echo "  ✅ Test${TEST_NUM} complete"
    echo ""
done

echo ""
echo "========================================================================"
echo "✅ ALL TESTS (Test4-10) COMPLETED SUCCESSFULLY"
echo "========================================================================"
