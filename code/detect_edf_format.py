#!/usr/bin/env python3
"""
EDF Format Detection Utility

Detects EDF file format and characteristics to determine the appropriate
conversion strategy for RBDtector analysis.

Author: Auto-generated for SNUH Atonia Index Project
Date: 2025-11-20
"""

import os
import sys
from pathlib import Path


def detect_edf_format(edf_path):
    """
    Detect EDF file format and return characteristics.

    Parameters:
    -----------
    edf_path : str or Path
        Path to EDF file

    Returns:
    --------
    dict with keys:
        - type: 'EDF+C' | 'EDF+D' | 'Standard' | 'Invalid'
        - has_annotations: bool
        - pyedflib_compatible: bool
        - excel_file: str or None (path to accompanying Excel file)
        - num_signals: int or None
        - emg_channels: list of (index, name) tuples
        - error: str or None (error message if detection failed)
    """
    edf_path = Path(edf_path)

    if not edf_path.exists():
        return {
            'type': 'Invalid',
            'has_annotations': False,
            'pyedflib_compatible': False,
            'excel_file': None,
            'num_signals': None,
            'emg_channels': [],
            'error': f"File not found: {edf_path}"
        }

    result = {
        'type': 'Unknown',
        'has_annotations': False,
        'pyedflib_compatible': False,
        'excel_file': None,
        'num_signals': None,
        'emg_channels': [],
        'error': None
    }

    # Try to detect with pyedflib first
    try:
        import pyedflib

        f = pyedflib.EdfReader(str(edf_path))

        # Successfully opened - pyedflib compatible
        result['pyedflib_compatible'] = True
        result['num_signals'] = f.signals_in_file

        # Determine EDF type
        filetype = f.filetype
        if filetype == 1:
            result['type'] = 'EDF+C'
        elif filetype == 2:
            result['type'] = 'EDF+D'
        else:
            result['type'] = 'Standard'

        # Check for annotations
        num_annotations = f.annotations_in_file
        result['has_annotations'] = num_annotations > 0

        # Detect EMG channels
        emg_channels = []
        for i in range(f.signals_in_file):
            label = f.getLabel(i)
            # Look for EMG, CHIN, LEG, Chin, Lat, Rat
            if any(keyword in label for keyword in ['EMG', 'CHIN', 'LEG', 'Chin', 'Lat', 'Rat']):
                emg_channels.append((i, label))

        result['emg_channels'] = emg_channels

        f.close()

    except Exception as e:
        # pyedflib failed - likely Standard EDF with non-compliant header
        result['pyedflib_compatible'] = False
        result['type'] = 'Standard'

        # Try manual header reading
        try:
            with open(edf_path, 'rb') as f:
                header = f.read(256)

                # Read basic info from header
                num_signals_str = header[252:256].decode('ascii', errors='ignore').strip()
                if num_signals_str.isdigit():
                    result['num_signals'] = int(num_signals_str)

                # Read signal labels
                if result['num_signals']:
                    label_bytes = f.read(16 * result['num_signals'])
                    emg_channels = []

                    for i in range(result['num_signals']):
                        label = label_bytes[i*16:(i+1)*16].decode('ascii', errors='ignore').strip()
                        if any(keyword in label for keyword in ['EMG', 'CHIN', 'LEG', 'Chin', 'Lat', 'Rat']):
                            emg_channels.append((i, label))

                    result['emg_channels'] = emg_channels

        except Exception as header_error:
            result['error'] = f"pyedflib error: {str(e)}, header read error: {str(header_error)}"

    # Check for accompanying Excel file
    excel_patterns = [
        edf_path.with_suffix('.xlsx'),
        edf_path.with_suffix('.XLSX'),
    ]

    for excel_path in excel_patterns:
        if excel_path.exists():
            result['excel_file'] = str(excel_path)
            break

    return result


def print_detection_result(result):
    """Pretty print detection result."""
    print("="*60)
    print("EDF Format Detection Result")
    print("="*60)

    print(f"Type: {result['type']}")
    print(f"pyedflib compatible: {'✓ Yes' if result['pyedflib_compatible'] else '✗ No'}")
    print(f"Has annotations: {'✓ Yes' if result['has_annotations'] else '✗ No'}")

    if result['excel_file']:
        print(f"Excel file: ✓ Found ({Path(result['excel_file']).name})")
    else:
        print(f"Excel file: ✗ Not found")

    if result['num_signals']:
        print(f"Number of signals: {result['num_signals']}")

    if result['emg_channels']:
        print(f"EMG channels found: {len(result['emg_channels'])}")
        for idx, name in result['emg_channels']:
            print(f"  [{idx}] {name}")
    else:
        print("EMG channels: ✗ None found")

    if result['error']:
        print(f"Error: {result['error']}")

    print()
    print("Recommended converter:")
    if result['type'] == 'EDF+C' and result['has_annotations']:
        print("  → convert_edf_annotations.py (annotations embedded)")
    elif result['type'] == 'EDF+D':
        print("  → convert_test8_to_continuous.py (discontinuous → continuous)")
        print("  → then convert_edf_annotations.py")
    elif result['type'] == 'Standard' and result['excel_file']:
        print("  → convert_excel_annotations.py (Excel annotations)")
    else:
        print("  ⚠ No suitable converter found")
        if result['type'] == 'Standard' and not result['excel_file']:
            print("    (Standard EDF requires Excel file with annotations)")

    print("="*60)


def main():
    """Command line interface for detection utility."""
    if len(sys.argv) < 2:
        print("Usage: python detect_edf_format.py <EDF_FILE>")
        print()
        print("Example:")
        print("  python detect_edf_format.py Clinical_DB/Test1.EDF")
        print("  python detect_edf_format.py Clinical_DB/additional/PS0140_211029.EDF")
        sys.exit(1)

    edf_path = sys.argv[1]
    result = detect_edf_format(edf_path)
    print_detection_result(result)

    # Exit code based on result
    if result['type'] == 'Invalid':
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
