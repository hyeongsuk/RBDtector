#!/usr/bin/env python3
"""
Generate RBDtector results for any Test file (Phase 1: Sequential Processing)
Usage: python3 generate_results_generic.py <test_number>
Example: python3 generate_results_generic.py 3
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

if len(sys.argv) != 2:
    print("Usage: python3 generate_results_generic.py <test_number>")
    print("Example: python3 generate_results_generic.py 3")
    sys.exit(1)

test_num = sys.argv[1]
test_id = f"Test{test_num}"

# Add RBDtector to path
WORKSPACE = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
RBDTECTOR_PATH = WORKSPACE / "SW" / "RBDtector" / "RBDtector"
sys.path.insert(0, str(RBDTECTOR_PATH))

# Import RBDtector
from app_logic.PSG import PSG
from input_handling import input_reader as ir
from util import settings

# Configure settings
settings.SIGNALS_TO_EVALUATE = ['EMG CHIN1-CHINz', 'EMG RLEG+', 'EMG LLEG+']
settings.CHIN = 0
settings.LEGS = [1, 2]
settings.ARMS = []
settings.HUMAN_BASELINE = False
settings.SNORE = True
settings.FLOW = False
settings.HUMAN_ARTIFACTS = False
settings.RATE = 256

# Input/output paths
input_dir = str(WORKSPACE / "Results" / "raw" / test_id)
output_dir = Path(input_dir) / "RBDtector_Results_Phase1"

# Check if input directory exists
if not Path(input_dir).exists():
    print(f"❌ Error: Input directory not found: {input_dir}")
    sys.exit(1)

# Check if EDF file exists
edf_file = Path(input_dir) / f"{test_id}.edf"
if not edf_file.exists():
    print(f"❌ Error: EDF file not found: {edf_file}")
    sys.exit(1)

output_dir.mkdir(exist_ok=True)

print("="*80)
print(f"Phase 1: Sequential Processing - {test_id}")
print("="*80)
print(f"\nInput: {input_dir}")
print(f"Output: {output_dir}")
print(f"\nSignals: {settings.SIGNALS_TO_EVALUATE}")
print(f"Chin: {settings.CHIN}, Legs: {settings.LEGS}\n")

try:
    # Step 1: Read input
    print("Step 1: Reading EDF and annotations...")
    raw_data, annotation_data = ir.read_input(
        directory_name=input_dir,
        signals_to_load=settings.SIGNALS_TO_EVALUATE.copy(),
        read_human_rating=False,
        read_baseline=False
    )
    print("  ✅ Data loaded")

    # Step 2: Create PSG object
    psg = PSG(input_dir, test_id)

    # Step 3: Prepare evaluation
    print("\nStep 2: Preparing evaluation...")
    df_signals, is_REM_series, is_global_artifact_series, signal_names, sleep_phase_series = \
        psg.prepare_evaluation(raw_data, annotation_data, settings.SIGNALS_TO_EVALUATE.copy(), settings.FLOW)
    print("  ✅ Evaluation prepared")

    # Step 4: Find global artifact-free REM
    print("\nStep 3: Finding artifact-free REM periods...")
    is_global_artifact_free_rem_sleep_epoch_series, is_global_artifact_free_rem_sleep_miniepoch_series = \
        psg.find_artifact_free_REM_sleep_epochs_and_miniepochs(
            idx=df_signals.index,
            artifact_signal_series=is_global_artifact_series,
            is_REM_series=is_REM_series
        )

    # Global statistics
    total_rem_miniepochs = is_REM_series.sum()
    artifact_free_rem_miniepochs = is_global_artifact_free_rem_sleep_miniepoch_series.sum()
    total_rem_epochs = is_REM_series.resample('30s').sum().gt(0).sum()
    artifact_free_rem_epochs = is_global_artifact_free_rem_sleep_epoch_series.resample('30s').sum().gt(0).sum()

    print(f"  Total REM miniepochs: {total_rem_miniepochs:,}")
    print(f"  Artifact-free REM miniepochs: {artifact_free_rem_miniepochs:,} ({artifact_free_rem_miniepochs/total_rem_miniepochs*100:.1f}%)")
    print(f"  Total REM epochs (30s): {total_rem_epochs:,}")
    print(f"  Artifact-free REM epochs: {artifact_free_rem_epochs:,} ({artifact_free_rem_epochs/total_rem_epochs*100:.1f}%)")

    # Step 5: Calculate per-channel baselines
    print("\nStep 4: Calculating baselines and detecting events...")

    results = {
        'Subject ID': test_id,
        'Global_REM_MiniEpochs': int(total_rem_miniepochs),
        'Global_REM_MacroEpochs': int(total_rem_epochs),
        'Global_REM_MiniEpochs_WO-Artifacts': int(artifact_free_rem_miniepochs),
        'Global_REM_MacroEpochs_WO-Artifacts': int(artifact_free_rem_epochs),
        'Artifact_Free_Percentage': float(artifact_free_rem_miniepochs/total_rem_miniepochs*100 if total_rem_miniepochs > 0 else 0)
    }

    for i, signal_name in enumerate(signal_names):
        print(f"\n  Processing {signal_name}...")

        # Get signal data
        signal_series = df_signals[signal_name]

        # Calculate baseline in artifact-free REM
        baseline_signal = signal_series[is_global_artifact_free_rem_sleep_miniepoch_series]

        if len(baseline_signal) > 0:
            # Calculate RMS in 5-second windows
            baseline_rms = baseline_signal.rolling(window=int(5*settings.RATE), center=True).apply(
                lambda x: np.sqrt(np.mean(x**2)), raw=True
            )
            baseline_mean = baseline_rms.mean()
            baseline_std = baseline_rms.std()

            print(f"    Baseline RMS: {baseline_mean:.2f} ± {baseline_std:.2f} µV")

            # Store results
            results[f'{signal_name}_REM_MiniEpochs_WO-Artifacts'] = int(artifact_free_rem_miniepochs)
            results[f'{signal_name}_REM_MacroEpochs_WO-Artifacts'] = int(artifact_free_rem_epochs)
            results[f'{signal_name}_Baseline_Mean'] = float(baseline_mean)
            results[f'{signal_name}_Baseline_Std'] = float(baseline_std)

            print(f"    ✅ Baseline calculated successfully")
        else:
            print(f"    ⚠️  No artifact-free REM data")
            results[f'{signal_name}_REM_MiniEpochs_WO-Artifacts'] = 0
            results[f'{signal_name}_REM_MacroEpochs_WO-Artifacts'] = 0

    # Step 6: Save results
    print("\nStep 5: Saving results...")

    # Create results DataFrame
    results_df = pd.DataFrame([results])

    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = output_dir / f"{test_id}_Results_Phase1_{timestamp}.csv"
    results_df.to_csv(csv_path, index=False)
    print(f"  ✅ Results saved to: {csv_path}")

    # Print summary
    print("\n" + "="*80)
    print(f"SUMMARY - {test_id}")
    print("="*80)
    print(f"\nGlobal Statistics:")
    print(f"  Total REM:          {total_rem_miniepochs:,} miniepochs ({total_rem_miniepochs/256/60:.1f} min)")
    print(f"  Artifact-free REM:  {artifact_free_rem_miniepochs:,} miniepochs ({artifact_free_rem_miniepochs/total_rem_miniepochs*100:.1f}%)")
    print(f"\nPer-Channel Baselines:")
    for signal_name in signal_names:
        if f'{signal_name}_Baseline_Mean' in results:
            mean = results[f'{signal_name}_Baseline_Mean']
            std = results[f'{signal_name}_Baseline_Std']
            print(f"  {signal_name:20s}: {mean:6.2f} ± {std:5.2f} µV")

    print(f"\n✅ {test_id} Analysis Complete!")
    print(f"\nResults location:")
    print(f"  {csv_path}")

    # Validation check
    if artifact_free_rem_miniepochs == 0:
        print("\n⚠️  WARNING: 0% artifact-free REM - Bug may still exist!")
        sys.exit(1)
    elif artifact_free_rem_miniepochs / total_rem_miniepochs > 0.9:
        print("\n✅ VALIDATION PASSED: >90% artifact-free REM")
    else:
        print(f"\n⚠️  NOTE: {artifact_free_rem_miniepochs/total_rem_miniepochs*100:.1f}% artifact-free REM")

except Exception as e:
    print(f"\n❌ Error processing {test_id}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
