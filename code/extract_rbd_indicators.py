#!/usr/bin/env python3
"""
Extract RBD indicators from converted Test1-10 files.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
results_dir = WORKSPACE / "Results" / "raw"

print("="*70)
print("RBD Indicators from Converted Files (Test1-10)")
print("="*70)
print()

data = []

for i in range(1, 11):
    test_name = f"Test{i}"
    test_dir = results_dir / test_name / "RBDtector output"

    # Find latest result file
    result_files = list(test_dir.glob("RBDtector_results_*.xlsx"))
    if not result_files:
        print(f"⚠️  {test_name}: No result file found")
        continue

    latest_file = max(result_files, key=lambda x: x.stat().st_mtime)

    # Read Excel
    try:
        df = pd.read_excel(latest_file, sheet_name=0, header=None)

        # Row 0: headers, Row 1: sub-headers, Row 3: data
        chin_any_col = None
        rleg_any_col = None
        lleg_any_col = None

        # Find columns (use Row 1 for sub-headers)
        for col_idx in range(df.shape[1]):
            subheader = str(df.iloc[1, col_idx])
            if 'EMG CHIN1-CHINz_any_%' in subheader:
                chin_any_col = col_idx
            elif 'EMG RLEG+_any_%' in subheader:
                rleg_any_col = col_idx
            elif 'EMG LLEG+_any_%' in subheader:
                lleg_any_col = col_idx

        # Extract values
        chin_any = df.iloc[3, chin_any_col] if chin_any_col is not None else None
        rleg_any = df.iloc[3, rleg_any_col] if rleg_any_col is not None else None
        lleg_any = df.iloc[3, lleg_any_col] if lleg_any_col is not None else None

        data.append({
            'Test': test_name,
            'Chin_Any_%': chin_any,
            'RLEG_Any_%': rleg_any,
            'LLEG_Any_%': lleg_any,
            'File': latest_file.name,
            'Modified': datetime.fromtimestamp(latest_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        })

        print(f"{test_name}: Chin={chin_any}% RLEG={rleg_any}% LLEG={lleg_any}% ({latest_file.name})")

    except Exception as e:
        print(f"❌ {test_name}: Error - {e}")

print()
print("="*70)
print("SUMMARY")
print("="*70)
print()

result_df = pd.DataFrame(data)
print(result_df.to_string(index=False))

# Save to CSV
output_csv = WORKSPACE / "Results" / "Test1-10_RBD_Indicators_Converted.csv"
result_df.to_csv(output_csv, index=False)
print()
print(f"✅ Saved to: {output_csv}")
