#!/usr/bin/env python3
"""
Extract COMPLETE RSWA data including Tonic, Phasic, Any from RBDtector Excel files
"""

import pandas as pd
from pathlib import Path
import glob

BASE_DIR = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
RESULTS_DIR = BASE_DIR / "Results"

def extract_rbdtector_data(excel_file):
    """Extract all RSWA metrics from RBDtector Excel file"""
    df = pd.read_excel(excel_file, sheet_name='Sheet1', header=None, engine='openpyxl')

    # Row 1: Field names, Row 3: Data
    field_names = df.iloc[1, :].tolist()
    data_values = df.iloc[3, :].tolist()

    # Create dict
    data_dict = {}
    for i, field in enumerate(field_names):
        if pd.notna(field):
            data_dict[field] = data_values[i]

    return data_dict

def main():
    print("="*80)
    print("Extracting COMPLETE RSWA Data from RBDtector Excel Files")
    print("="*80)

    # Test1-10 data
    test_data = []

    for test_num in range(1, 11):
        test_name = f"Test{test_num}"
        # Find RBDtector Excel files - prefer "RBDtector output" over "RBDtector output_raw"
        pattern_main = str(RESULTS_DIR / f"raw/{test_name}/RBDtector output/RBDtector_results*.xlsx")
        pattern_raw = str(RESULTS_DIR / f"raw/{test_name}/RBDtector*/RBDtector_results*.xlsx")

        files = glob.glob(pattern_main)
        if not files:
            files = glob.glob(pattern_raw)

        if not files:
            print(f"⚠ No RBDtector file for {test_name}")
            continue

        # Use most recent file
        excel_file = sorted(files)[-1]
        print(f"\n{test_name}: {Path(excel_file).name}")

        data = extract_rbdtector_data(excel_file)

        # Extract CHIN metrics
        chin_tonic_pct = data.get('EMG CHIN1-CHINz_tonic_%', None)
        chin_phasic_pct = data.get('EMG CHIN1-CHINz_phasic_%', None)
        chin_any_pct = data.get('EMG CHIN1-CHINz_any_%', None)

        print(f"  CHIN Tonic: {chin_tonic_pct}%")
        print(f"  CHIN Phasic: {chin_phasic_pct}%")
        print(f"  CHIN Any: {chin_any_pct}%")

        test_data.append({
            'Test': test_name,
            'CHIN_Tonic_%': chin_tonic_pct,
            'CHIN_Phasic_%': chin_phasic_pct,
            'CHIN_Any_%': chin_any_pct,
            'File': Path(excel_file).name
        })

    # Save to CSV
    df_test = pd.DataFrame(test_data)
    output_file = RESULTS_DIR / "Test1-10_RSWA_Complete.csv"
    df_test.to_csv(output_file, index=False, encoding='utf-8-sig')

    print("\n" + "="*80)
    print(f"✓ Saved to: {output_file}")
    print("="*80)

    # Display summary
    print("\n### Test1-10 RSWA Summary ###")
    print(df_test.to_string(index=False))

if __name__ == "__main__":
    main()
