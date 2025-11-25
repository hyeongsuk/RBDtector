#!/usr/bin/env python3
"""
Convert Standard EDF to EDF+C (pyedflib compatible)

For Standard EDF files that cannot be read by pyedflib due to non-compliant headers.
Converts to EDF+C format that RBDtector can process.

Based on convert_test8_to_continuous.py logic.

Author: Auto-generated for SNUH Atonia Index Project
Date: 2025-11-20

Usage:
    python convert_standard_to_edfplus.py <INPUT_EDF> [OUTPUT_EDF]
"""

import sys
import mne
import numpy as np
from pathlib import Path
import pyedflib


def convert_standard_to_edfplus(input_edf, output_edf=None):
    """
    Convert Standard EDF to EDF+C format.

    Parameters:
    -----------
    input_edf : str or Path
        Path to input Standard EDF file
    output_edf : str or Path, optional
        Path to output EDF+C file. If None, creates in same directory with '_edfplus' suffix.

    Returns:
    --------
    dict with keys:
        - success: bool
        - output_path: str
        - error: str or None
    """
    input_edf = Path(input_edf)

    if not input_edf.exists():
        return {'success': False, 'output_path': None, 'error': f'Input file not found: {input_edf}'}

    # Determine output path
    if output_edf is None:
        output_edf = input_edf.parent / f"{input_edf.stem}_edfplus.edf"
    else:
        output_edf = Path(output_edf)

    print("="*80)
    print("Converting Standard EDF → EDF+C")
    print("="*80)
    print()
    print(f"Input:  {input_edf}")
    print(f"Output: {output_edf}")
    print()

    try:
        # Step 1: Read with MNE
        print("Step 1: Reading Standard EDF with MNE...")
        raw = mne.io.read_raw_edf(str(input_edf), preload=True, verbose=False)

        print(f"  ✓ Successfully read")
        print(f"    Duration: {raw.times[-1]/3600:.2f} hours")
        print(f"    Sampling frequency: {raw.info['sfreq']} Hz")
        print(f"    Number of channels: {len(raw.ch_names)}")
        print()

        # Check EMG channels
        emg_channels = [ch for ch in raw.ch_names if any(kw in ch for kw in ['EMG', 'Chin', 'Lat', 'Rat', 'EEG', 'EOG'])]
        print(f"  EMG/EEG channels found: {len(emg_channels)}")
        for ch in emg_channels:
            print(f"    - {ch}")
        print()

        # Step 2: Convert to microvolts
        print("Step 2: Converting units to µV...")
        data = raw.get_data()
        ch_names = raw.ch_names
        sfreq = raw.info['sfreq']

        # Convert EMG/EEG/EOG channels to µV
        channels_converted = []
        for i, ch_name in enumerate(ch_names):
            # Identify channel type from name
            ch_type = None
            for keyword in ['EMG', 'EEG', 'EOG', 'Chin', 'Lat', 'Rat']:
                if keyword in ch_name:
                    ch_type = 'biosignal'
                    break

            if ch_type == 'biosignal':
                data[i] = data[i] * 1e6  # V → µV
                channels_converted.append(ch_name)

        print(f"  ✓ Converted {len(channels_converted)} channels to µV")
        print()

        # Step 3: Prepare signal headers
        print("Step 3: Preparing pyedflib headers...")
        signal_headers = []

        for i, ch_name in enumerate(ch_names):
            ch_data = data[i]

            # Calculate physical range using FULL data range (not percentile)
            # Previous 99th percentile method caused clipping of large EMG bursts
            # AASM recommends ±50 mV input range to prevent signal saturation
            abs_max = max(abs(ch_data.min()), abs(ch_data.max()))

            # Add 100% margin to accommodate signal variations during sleep
            # This ensures no clipping of phasic/tonic EMG bursts
            physical_max = abs_max * 2.0
            physical_min = -physical_max

            # Ensure minimum range of ±500 µV for EMG channels (AASM guidelines)
            if ch_name in channels_converted:  # EMG/EEG/EOG channels
                min_range = 500.0  # µV
                if abs(physical_max) < min_range:
                    physical_max = min_range
                    physical_min = -min_range

            # Digital range (16-bit EDF)
            digital_min = -32768
            digital_max = 32767

            # Set dimension based on channel type
            dimension = 'uV' if ch_name in channels_converted else ''

            header = {
                'label': ch_name,
                'dimension': dimension,
                'sample_frequency': int(sfreq),
                'physical_min': physical_min,
                'physical_max': physical_max,
                'digital_min': digital_min,
                'digital_max': digital_max,
                'transducer': '',
                'prefilter': ''
            }
            signal_headers.append(header)

        print(f"  ✓ Prepared {len(signal_headers)} signal headers")
        print()

        # Step 4: Write EDF+C file
        print("Step 4: Writing EDF+C file...")
        f = pyedflib.EdfWriter(str(output_edf), len(ch_names), file_type=pyedflib.FILETYPE_EDFPLUS)

        # Set patient and recording info
        patient_name = input_edf.stem
        f.setPatientName(patient_name)
        f.setStartdatetime(raw.info['meas_date'].replace(tzinfo=None))

        # Set signal headers
        f.setSignalHeaders(signal_headers)

        # Write data in records
        record_duration = 1  # second
        samples_per_record = int(sfreq * record_duration)
        n_records = int(np.ceil(data.shape[1] / samples_per_record))

        print(f"  Writing {n_records} data records...")
        for record_idx in range(n_records):
            start_sample = record_idx * samples_per_record
            end_sample = min((record_idx + 1) * samples_per_record, data.shape[1])

            # Write this record for all channels
            for ch_idx in range(len(ch_names)):
                record_data = data[ch_idx, start_sample:end_sample]

                # Pad last record if needed
                if len(record_data) < samples_per_record and record_idx == n_records - 1:
                    pad_length = samples_per_record - len(record_data)
                    record_data = np.pad(record_data, (0, pad_length), mode='edge')

                f.writePhysicalSamples(record_data)

            if (record_idx + 1) % 1000 == 0:
                print(f"    Progress: {record_idx + 1}/{n_records} records")

        f.close()

        print(f"  ✓ Export complete!")
        print()

        # Step 5: Verify
        print("Step 5: Verifying converted file...")
        try:
            f_verify = pyedflib.EdfReader(str(output_edf))

            print("  ✓ Verification SUCCESS!")
            print()
            print("  Converted file can be read by pyedflib:")
            print(f"    Duration: {f_verify.getFileDuration()} seconds ({f_verify.getFileDuration()/3600:.2f} hours)")
            print(f"    Number of signals: {f_verify.signals_in_file}")
            print(f"    Start time: {f_verify.getStartdatetime()}")
            print()

            # Check EMG channels
            labels = [f_verify.getLabel(i) for i in range(f_verify.signals_in_file)]
            emg_labels = [l for l in labels if any(kw in l for kw in ['EMG', 'Chin', 'Lat', 'Rat'])]
            print("  EMG channels in converted file:")
            for label in emg_labels:
                idx = labels.index(label)
                print(f"    {idx}: {label} @ {f_verify.getSampleFrequency(idx)} Hz")

            f_verify.close()

            print()
            print("="*80)
            print("CONVERSION SUCCESSFUL!")
            print("="*80)
            print()
            print("Next steps:")
            print("  1. This EDF+C file can be used with RBDtector")
            print("  2. Use converted EDF with existing annotation files")
            print("  3. Run RBDtector analysis")

            return {
                'success': True,
                'output_path': str(output_edf),
                'error': None
            }

        except Exception as e:
            print(f"  ✗ Verification FAILED: {e}")
            print()
            print("  The converted file cannot be read by pyedflib.")
            return {
                'success': False,
                'output_path': str(output_edf),
                'error': f'Verification failed: {e}'
            }

    except Exception as e:
        print(f"✗ Conversion FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'output_path': None,
            'error': str(e)
        }


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python convert_standard_to_edfplus.py <INPUT_EDF> [OUTPUT_EDF]")
        print()
        print("Example:")
        print("  python convert_standard_to_edfplus.py PS0140_211029.EDF")
        print("  python convert_standard_to_edfplus.py PS0140_211029.EDF PS0140_211029_converted.edf")
        sys.exit(1)

    input_edf = sys.argv[1]
    output_edf = sys.argv[2] if len(sys.argv) > 2 else None

    result = convert_standard_to_edfplus(input_edf, output_edf)

    if result['success']:
        sys.exit(0)
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
