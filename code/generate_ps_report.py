#!/usr/bin/env python3
"""
Generate comprehensive report for PS0140-151 patients in Test1-10 format
Includes true baseline amplitude calculations (Mean ± SD RMS in µV)
"""

import pandas as pd
import numpy as np
import pyedflib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
RESULTS_DIR = BASE_DIR / "Results/raw"
OUTPUT_DIR = BASE_DIR / "Results"

# Patient IDs
PATIENTS = ['PS0140_211029', 'PS0141_211030', 'PS0150_221111', 'PS0151_221112']

def calculate_true_baseline_amplitude(edf_path, channel_name, sleep_profile_path):
    """
    Calculate true baseline amplitude (Mean ± SD of RMS) during artifact-free REM sleep
    """
    print(f"  Processing {channel_name}...")

    try:
        # Read EDF file
        f = pyedflib.EdfReader(str(edf_path))

        # Find channel index
        channel_idx = None
        for i in range(f.signals_in_file):
            label = f.getLabel(i)
            if channel_name in label:
                channel_idx = i
                break

        if channel_idx is None:
            f.close()
            return np.nan, np.nan, "N/A"

        # Read signal and sampling rate
        signal = f.readSignal(channel_idx)
        fs = f.getSampleFrequency(channel_idx)
        start_time = f.getStartdatetime()
        f.close()

        # Parse sleep profile (semicolon-separated format)
        with open(sleep_profile_path, 'r') as f:
            lines = f.readlines()

        # Extract start date from first line
        start_date_line = lines[0].strip()
        # Format: "Start Time: DD.MM.YYYY HH:MM:SS"
        start_date_str = start_date_line.replace('Start Time: ', '').strip()
        file_start_time = pd.to_datetime(start_date_str, format='%d.%m.%Y %H:%M:%S')

        # Parse sleep stages (lines after line 2)
        sleep_stages = []
        for line in lines[3:]:  # Skip first 3 lines (header)
            line = line.strip()
            if not line or ';' not in line:
                continue

            parts = line.split(';')
            if len(parts) != 2:
                continue

            time_str = parts[0].strip()
            stage = parts[1].strip()

            # Parse time (HH:MM:SS,microseconds)
            time_parts = time_str.split(',')
            hms = time_parts[0]  # HH:MM:SS
            microsec = time_parts[1] if len(time_parts) > 1 else '000000'

            # Create timestamp for this stage
            timestamp = pd.to_datetime(
                f"{file_start_time.strftime('%Y-%m-%d')} {hms}.{microsec}",
                format='%Y-%m-%d %H:%M:%S.%f'
            )

            # Handle overnight recordings - if time is before start time, add 1 day
            if timestamp < file_start_time and len(sleep_stages) > 0:
                timestamp = timestamp + pd.Timedelta(days=1)
            elif len(sleep_stages) > 0 and timestamp < sleep_stages[-1]['time']:
                # If time went backwards, we crossed midnight
                timestamp = timestamp + pd.Timedelta(days=1)

            sleep_stages.append({'time': timestamp, 'stage': stage})

        if len(sleep_stages) == 0:
            return np.nan, np.nan, "No sleep stages"

        # Create time index for signal
        signal_index = pd.date_range(start=start_time, periods=len(signal), freq=f'{1/fs}S')
        signal_series = pd.Series(signal, index=signal_index)

        # Find REM periods (stage == 'R' or stage contains 'REM')
        rem_signal_list = []
        for i in range(len(sleep_stages) - 1):
            stage = sleep_stages[i]['stage']

            if stage == 'R' or 'REM' in stage.upper():
                start = sleep_stages[i]['time']
                end = sleep_stages[i + 1]['time']

                # Extract signal in this 30-second epoch
                mask = (signal_series.index >= start) & (signal_series.index < end)
                rem_chunk = signal_series[mask]

                if len(rem_chunk) > 0:
                    rem_signal_list.append(rem_chunk)

        if len(rem_signal_list) == 0:
            return np.nan, np.nan, "No REM"

        # Concatenate all REM periods
        rem_signal_combined = pd.concat(rem_signal_list)

        if len(rem_signal_combined) == 0:
            return np.nan, np.nan, "Empty REM"

        # Calculate RMS in 5-second windows
        window_size = int(5 * fs)  # 5 seconds
        rms_values = []

        for i in range(0, len(rem_signal_combined) - window_size, window_size):
            window = rem_signal_combined.iloc[i:i+window_size].values
            rms = np.sqrt(np.mean(window**2))
            rms_values.append(rms)

        if len(rms_values) == 0:
            return np.nan, np.nan, "Insufficient data"

        # Calculate statistics
        rms_array = np.array(rms_values)
        mean_rms = np.mean(rms_array)
        std_rms = np.std(rms_array)

        # Format string
        formatted = f"{mean_rms:.2f}±{std_rms:.2f}"

        return mean_rms, std_rms, formatted

    except Exception as e:
        print(f"    Error processing {channel_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return np.nan, np.nan, f"Error: {str(e)}"


def extract_rbdtector_data(patient_id):
    """Extract data from RBDtector output Excel file"""
    patient_dir = RESULTS_DIR / patient_id
    rbdtector_dir = patient_dir / "RBDtector output"

    # Find most recent RBDtector results file
    xlsx_files = list(rbdtector_dir.glob("RBDtector_results_*.xlsx"))
    if not xlsx_files:
        print(f"  No RBDtector output found for {patient_id}")
        return None

    # Use the most recent file
    xlsx_file = sorted(xlsx_files)[-1]
    print(f"  Reading: {xlsx_file.name}")

    try:
        # Read the Excel file with no header (raw structure)
        df_raw = pd.read_excel(xlsx_file, sheet_name='Sheet1', header=None, engine='openpyxl')

        # Row 1 (index 1) has field names, Row 3 (index 3) has data
        field_names = df_raw.iloc[1, :].tolist()
        data_values = df_raw.iloc[3, :].tolist()

        # Create dictionary from field names and values
        excel_data = {}
        for name, value in zip(field_names, data_values):
            if pd.notna(name):
                excel_data[name] = value

        # Extract relevant data
        data = {
            'Patient': patient_id.split('_')[0],
            'File': xlsx_file.name
        }

        # Calculate REM duration (in minutes)
        if 'Global_REM_MiniEpochs' in excel_data:
            rem_miniepochs = excel_data['Global_REM_MiniEpochs']
            data['REM_Duration_min'] = (rem_miniepochs * 3) / 60  # 3 seconds per mini-epoch
        else:
            data['REM_Duration_min'] = np.nan

        # Calculate artifact-free percentage
        if 'Global_REM_MiniEpochs' in excel_data and 'Global_REM_MiniEpochs_WO-Artifacts' in excel_data:
            total = excel_data['Global_REM_MiniEpochs']
            artifact_free = excel_data['Global_REM_MiniEpochs_WO-Artifacts']
            data['Artifact_free_%'] = (artifact_free / total) * 100 if total > 0 else 0
        else:
            data['Artifact_free_%'] = np.nan

        # Extract muscle activity data
        muscle_channels = {
            'Chin1-Chin2': 'CHIN',
            'Lat': 'LAT',
            'Rat': 'RAT'
        }

        for edf_name, short_name in muscle_channels.items():
            # Extract metrics for this channel
            for metric in ['tonic', 'phasic', 'any']:
                # Absolute values
                abs_key = f'{edf_name}_{metric}_Abs'
                if abs_key in excel_data:
                    data[f'{short_name}_{metric.capitalize()}_Abs'] = excel_data[abs_key]
                else:
                    data[f'{short_name}_{metric.capitalize()}_Abs'] = 0

                # Percentage values
                pct_key = f'{edf_name}_{metric}_%'
                if pct_key in excel_data:
                    data[f'{short_name}_{metric.capitalize()}_%'] = excel_data[pct_key]
                else:
                    data[f'{short_name}_{metric.capitalize()}_%'] = 0

        return data

    except Exception as e:
        print(f"  Error reading {xlsx_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def calculate_baselines_for_patient(patient_id):
    """Calculate true baseline amplitudes for all channels"""
    patient_dir = RESULTS_DIR / patient_id

    # Find converted EDF file
    edf_files = list(patient_dir.glob("*_converted.edf"))
    if not edf_files:
        # Try original EDF
        edf_files = list(patient_dir.glob("*.edf"))

    if not edf_files:
        print(f"  No EDF file found for {patient_id}")
        return {}

    edf_file = edf_files[0]

    # Find sleep profile
    sleep_files = list(patient_dir.glob("*Sleep profile*.txt"))
    if not sleep_files:
        print(f"  No sleep profile found for {patient_id}")
        return {}

    sleep_file = sleep_files[0]

    print(f"  EDF: {edf_file.name}")
    print(f"  Sleep profile: {sleep_file.name}")

    # Channel mappings
    channels = {
        'Chin1-Chin2': 'CHIN',
        'Lat': 'LAT',
        'Rat': 'RAT'
    }

    baselines = {}

    for channel_edf, channel_short in channels.items():
        mean_rms, std_rms, formatted = calculate_true_baseline_amplitude(
            edf_file, channel_edf, sleep_file
        )

        baselines[f'{channel_short}_Mean'] = mean_rms
        baselines[f'{channel_short}_Std'] = std_rms
        baselines[f'{channel_short}_Baseline'] = formatted

    return baselines


def main():
    print("=" * 80)
    print("Generating PS0140-151 Comprehensive Report")
    print("=" * 80)

    all_data = []

    for patient_id in PATIENTS:
        print(f"\n[{patient_id}]")

        # Extract RBDtector data
        print("  Extracting RBDtector data...")
        rbdtector_data = extract_rbdtector_data(patient_id)

        if rbdtector_data is None:
            continue

        # Calculate baseline amplitudes
        print("  Calculating true baseline amplitudes...")
        baseline_data = calculate_baselines_for_patient(patient_id)

        # Combine all data
        combined_data = {**rbdtector_data, **baseline_data}
        all_data.append(combined_data)

        print(f"  ✓ Completed {patient_id}")

    # Create DataFrame
    df = pd.DataFrame(all_data)

    # Reorder columns to match Test1-10 format
    column_order = [
        'Patient',
        'REM_Duration_min',
        'Artifact_free_%',
        'CHIN_Mean', 'CHIN_Std', 'CHIN_Baseline',
        'LAT_Mean', 'LAT_Std', 'LAT_Baseline',
        'RAT_Mean', 'RAT_Std', 'RAT_Baseline',
        'CHIN_Tonic_Abs', 'CHIN_Tonic_%',
        'CHIN_Phasic_Abs', 'CHIN_Phasic_%',
        'CHIN_Any_Abs', 'CHIN_Any_%',
        'LAT_Tonic_Abs', 'LAT_Tonic_%',
        'LAT_Phasic_Abs', 'LAT_Phasic_%',
        'LAT_Any_Abs', 'LAT_Any_%',
        'RAT_Tonic_Abs', 'RAT_Tonic_%',
        'RAT_Phasic_Abs', 'RAT_Phasic_%',
        'RAT_Any_Abs', 'RAT_Any_%',
        'File'
    ]

    # Reorder (only include columns that exist)
    existing_cols = [col for col in column_order if col in df.columns]
    df = df[existing_cols]

    # Save to CSV
    output_file = OUTPUT_DIR / "PS0140-151_Complete_Analysis.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved comprehensive data to: {output_file}")

    # Save baseline-only file
    baseline_cols = ['Patient', 'REM_Duration_min', 'Artifact_free_%',
                    'CHIN_Mean', 'CHIN_Std', 'CHIN_Baseline',
                    'LAT_Mean', 'LAT_Std', 'LAT_Baseline',
                    'RAT_Mean', 'RAT_Std', 'RAT_Baseline']
    baseline_df = df[[col for col in baseline_cols if col in df.columns]]

    baseline_file = OUTPUT_DIR / "PS0140-151_True_Baseline_Amplitudes.csv"
    baseline_df.to_csv(baseline_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved baseline amplitudes to: {baseline_file}")

    # Save RBD indicators file
    rbd_cols = ['Patient',
                'CHIN_Any_%', 'LAT_Any_%', 'RAT_Any_%',
                'File']
    rbd_df = df[[col for col in rbd_cols if col in df.columns]]

    rbd_file = OUTPUT_DIR / "PS0140-151_RBD_Indicators_Converted.csv"
    rbd_df.to_csv(rbd_file, index=False, encoding='utf-8-sig')
    print(f"✓ Saved RBD indicators to: {rbd_file}")

    print("\n" + "=" * 80)
    print("Summary Statistics:")
    print("=" * 80)
    print(f"\nTotal patients processed: {len(df)}")
    print(f"\nREM Duration (min):")
    print(f"  Mean: {df['REM_Duration_min'].mean():.1f} ± {df['REM_Duration_min'].std():.1f}")
    print(f"  Range: {df['REM_Duration_min'].min():.1f} - {df['REM_Duration_min'].max():.1f}")

    print(f"\nArtifact-free REM (%):")
    print(f"  Mean: {df['Artifact_free_%'].mean():.1f} ± {df['Artifact_free_%'].std():.1f}")
    print(f"  Range: {df['Artifact_free_%'].min():.1f} - {df['Artifact_free_%'].max():.1f}")

    print(f"\nTrue Baseline Amplitude (µV):")
    for muscle in ['CHIN', 'LAT', 'RAT']:
        if f'{muscle}_Mean' in df.columns:
            mean_col = df[f'{muscle}_Mean'].dropna()
            if len(mean_col) > 0:
                print(f"  {muscle}: {mean_col.mean():.2f} ± {mean_col.std():.2f} µV")

    print("\n✓ All files generated successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
