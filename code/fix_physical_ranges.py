#!/usr/bin/env python3
"""
Fix Physical Min/Max ranges in EDF files using pyedflib only.

This script reads EDF files with pyedflib (even with reversed Physical Min/Max),
calculates correct physical ranges from the data, and writes a corrected EDF file.

Author: Auto-generated
Date: 2025-11-23
"""

import sys
import numpy as np
from pathlib import Path
import pyedflib


def fix_physical_ranges(input_edf, output_edf=None):
    """
    Fix Physical Min/Max ranges in an EDF file.

    Parameters:
    -----------
    input_edf : str or Path
        Path to input EDF file
    output_edf : str or Path, optional
        Path to output file. If None, creates with '_fixed' suffix.

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

    if output_edf is None:
        output_edf = input_edf.parent / f"{input_edf.stem}_fixed.edf"
    else:
        output_edf = Path(output_edf)

    print("=" * 80)
    print("Fixing Physical Min/Max Ranges")
    print("=" * 80)
    print()
    print(f"Input:  {input_edf}")
    print(f"Output: {output_edf}")
    print()

    try:
        # Step 1: Read original file
        print("Step 1: Reading original EDF file...")
        f_in = pyedflib.EdfReader(str(input_edf))

        n_signals = f_in.signals_in_file
        print(f"  Signals: {n_signals}")
        print(f"  Duration: {f_in.getFileDuration()/3600:.2f} hours")
        print()

        # Step 2: Read all data and headers
        print("Step 2: Reading signal data...")
        signal_headers = []
        signal_data = []

        for i in range(n_signals):
            label = f_in.getLabel(i)
            data = f_in.readSignal(i)

            # Calculate proper physical range from actual data
            data_min = np.min(data)
            data_max = np.max(data)

            # Add 20% margin
            range_span = data_max - data_min
            margin = range_span * 0.2
            physical_min = data_min - margin
            physical_max = data_max + margin

            # Make symmetric for EMG/EEG channels
            if any(kw in label for kw in ['EMG', 'EEG', 'EOG', 'CHIN', 'LEG']):
                abs_max = max(abs(physical_min), abs(physical_max))
                physical_min = -abs_max
                physical_max = abs_max

            header = {
                'label': label,
                'dimension': f_in.getPhysicalDimension(i),
                'sample_frequency': int(f_in.getSampleFrequency(i)),
                'physical_min': physical_min,
                'physical_max': physical_max,
                'digital_min': -32768,
                'digital_max': 32767,
                'transducer': f_in.getTransducer(i),
                'prefilter': f_in.getPrefilter(i)
            }

            signal_headers.append(header)
            signal_data.append(data)

            if i < 3 or 'CHIN' in label or 'LEG' in label:
                print(f"  {label}:")
                print(f"    Data range: {data_min:.2f} to {data_max:.2f}")
                print(f"    New Physical: {physical_min:.2f} to {physical_max:.2f}")

        print()

        # Step 3: Write new file
        print("Step 3: Writing corrected EDF file...")
        f_out = pyedflib.EdfWriter(str(output_edf), n_signals, file_type=pyedflib.FILETYPE_EDFPLUS)

        # Set file info
        f_out.setPatientName(f_in.getPatientName())
        f_out.setStartdatetime(f_in.getStartdatetime())

        # Set signal headers
        f_out.setSignalHeaders(signal_headers)

        # Write data
        for i, data in enumerate(signal_data):
            f_out.writePhysicalSamples(data)

        f_out.close()
        f_in.close()

        print("  ✓ Write complete!")
        print()

        # Step 4: Verify
        print("Step 4: Verifying corrected file...")
        f_verify = pyedflib.EdfReader(str(output_edf))

        print("  ✓ Verification SUCCESS!")
        print()
        print("  Corrected file info:")
        print(f"    Duration: {f_verify.getFileDuration()/3600:.2f} hours")
        print(f"    Signals: {f_verify.signals_in_file}")
        print()

        # Check a few channels
        print("  Sample corrected ranges:")
        for i in range(min(3, f_verify.signals_in_file)):
            label = f_verify.getLabel(i)
            phys_min = f_verify.getPhysicalMinimum(i)
            phys_max = f_verify.getPhysicalMaximum(i)
            print(f"    {label}: {phys_min:.2f} to {phys_max:.2f}")

        f_verify.close()

        print()
        print("=" * 80)
        print("FIX SUCCESSFUL!")
        print("=" * 80)

        return {
            'success': True,
            'output_path': str(output_edf),
            'error': None
        }

    except Exception as e:
        print(f"✗ Fix FAILED: {e}")
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
        print("Usage: python fix_physical_ranges.py <INPUT_EDF> [OUTPUT_EDF]")
        print()
        print("Example:")
        print("  python fix_physical_ranges.py Test1.EDF")
        print("  python fix_physical_ranges.py Test1.EDF Test1_fixed.edf")
        sys.exit(1)

    input_edf = sys.argv[1]
    output_edf = sys.argv[2] if len(sys.argv) > 2 else None

    result = fix_physical_ranges(input_edf, output_edf)

    if result['success']:
        print()
        print(f"Output saved to: {result['output_path']}")
        sys.exit(0)
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
