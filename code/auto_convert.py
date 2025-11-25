#!/usr/bin/env python3
"""
Automatic EDF Annotation Converter

Automatically detects EDF format and applies the appropriate conversion strategy.
Supports:
  - EDF+C (annotations embedded) → convert_edf_annotations.py
  - EDF+D (discontinuous) → convert_test8_to_continuous.py + convert_edf_annotations.py
  - Standard EDF + Excel → convert_excel_annotations.py

Author: Auto-generated for SNUH Atonia Index Project
Date: 2025-11-20

Usage:
    python auto_convert.py <EDF_PATH>
    python auto_convert.py <DIRECTORY>  # Process all EDF files in directory
"""

import os
import sys
import subprocess
from pathlib import Path

# Import detection utility
from detect_edf_format import detect_edf_format


def convert_single_file(edf_path, verbose=True):
    """
    Convert a single EDF file using appropriate converter.

    Parameters:
    -----------
    edf_path : str or Path
        Path to EDF file
    verbose : bool
        Print detailed progress

    Returns:
    --------
    dict with keys:
        - success: bool
        - converter_used: str
        - output_files: list of str
        - error: str or None
    """
    edf_path = Path(edf_path)

    if verbose:
        print("="*60)
        print(f"Processing: {edf_path.name}")
        print("="*60)
        print()

    # Step 1: Detect format
    if verbose:
        print("[1/3] Detecting EDF format...")

    result = detect_edf_format(edf_path)

    if result['type'] == 'Invalid':
        return {
            'success': False,
            'converter_used': None,
            'output_files': [],
            'error': result['error']
        }

    if verbose:
        print(f"  ✓ Type: {result['type']}")
        if result['excel_file']:
            print(f"  ✓ Excel file: {Path(result['excel_file']).name}")
        if result['emg_channels']:
            print(f"  ✓ EMG channels: {', '.join([name for _, name in result['emg_channels']])}")
        print()

    # Step 2: Select and run appropriate converter
    if verbose:
        print("[2/3] Running converter...")

    converter_used = None
    output_files = []
    error = None

    try:
        if result['type'] == 'EDF+C' and result['has_annotations']:
            # Use convert_edf_annotations.py
            converter_used = 'convert_edf_annotations.py'
            if verbose:
                print(f"  → Using: {converter_used}")
                print()

            script_path = Path(__file__).parent / converter_used
            cmd = [sys.executable, str(script_path), str(edf_path)]

            proc = subprocess.run(cmd, capture_output=True, text=True)

            if proc.returncode != 0:
                error = f"Converter failed: {proc.stderr}"
            else:
                # Expected output files
                base_name = edf_path.stem
                output_dir = edf_path.parent
                output_files = [
                    str(output_dir / f"{base_name} Sleep profile.txt"),
                    str(output_dir / f"{base_name} Classification Arousals.txt"),
                    str(output_dir / f"{base_name} Flow Events.txt")
                ]

        elif result['type'] == 'EDF+D':
            # Use convert_test8_to_continuous.py then convert_edf_annotations.py
            converter_used = 'convert_test8_to_continuous.py + convert_edf_annotations.py'
            error = "EDF+D conversion not yet fully automated. Please use convert_test8_to_continuous.py manually."

        elif result['type'] == 'Standard' and result['excel_file']:
            # Use convert_excel_annotations.py + convert_standard_to_edfplus.py
            converter_used = 'convert_excel_annotations.py + convert_standard_to_edfplus.py'
            if verbose:
                print(f"  → Using: {converter_used}")
                print()

            # Step 1: Convert EDF to EDF+C
            if verbose:
                print("  [Step 1/2] Converting EDF to EDF+C (pyedflib compatible)...")

            edf_converter_path = Path(__file__).parent / 'convert_standard_to_edfplus.py'
            edfplus_output = edf_path.parent / f"{edf_path.stem}_edfplus.edf"

            cmd_edf = [sys.executable, str(edf_converter_path), str(edf_path), str(edfplus_output)]
            proc_edf = subprocess.run(cmd_edf, capture_output=True, text=True)

            if proc_edf.returncode != 0:
                error = f"EDF conversion failed: {proc_edf.stderr}"
            else:
                if verbose:
                    print(f"    ✓ EDF+C file created: {edfplus_output.name}")
                    print()

                # Step 2: Convert annotations from Excel
                if verbose:
                    print("  [Step 2/2] Converting annotations from Excel...")

                annotation_converter_path = Path(__file__).parent / 'convert_excel_annotations.py'
                cmd_anno = [sys.executable, str(annotation_converter_path), str(edf_path), result['excel_file']]

                proc_anno = subprocess.run(cmd_anno, capture_output=True, text=True)

                if proc_anno.returncode != 0:
                    error = f"Annotation conversion failed: {proc_anno.stderr}"
                else:
                    # Expected output files
                    base_name = edf_path.stem
                    output_dir = edf_path.parent
                    output_files = [
                        str(edfplus_output),  # Converted EDF+C
                        str(output_dir / f"{base_name} Sleep profile.txt"),
                        str(output_dir / f"{base_name} Classification Arousals.txt"),
                        str(output_dir / f"{base_name} Flow Events.txt")
                    ]

                    # Print converter output
                    if verbose and proc_anno.stdout:
                        for line in proc_anno.stdout.split('\n'):
                            if '✓' in line or 'events' in line.lower():
                                print(f"    {line}")

        else:
            error = "No suitable converter found for this EDF format"

    except Exception as e:
        error = str(e)

    if verbose:
        print()

    # Step 3: Report results
    if verbose:
        print("[3/3] Results:")

    success = error is None

    if success:
        if verbose:
            print("  ✓ Conversion successful!")
            print()
            print("  Output files:")
            for output_file in output_files:
                if Path(output_file).exists():
                    print(f"    → {Path(output_file).name}")
    else:
        if verbose:
            print(f"  ✗ Conversion failed: {error}")

    if verbose:
        print()

    return {
        'success': success,
        'converter_used': converter_used,
        'output_files': output_files,
        'error': error
    }


def convert_directory(directory_path, verbose=True):
    """
    Convert all EDF files in a directory.

    Parameters:
    -----------
    directory_path : str or Path
        Path to directory containing EDF files
    verbose : bool
        Print detailed progress

    Returns:
    --------
    dict with keys:
        - total: int
        - success: int
        - failed: int
        - results: list of dict (per-file results)
    """
    directory_path = Path(directory_path)

    if not directory_path.is_dir():
        print(f"Error: Not a directory: {directory_path}")
        return None

    # Find all EDF files
    edf_files = list(directory_path.glob('*.EDF')) + list(directory_path.glob('*.edf'))

    if not edf_files:
        print(f"No EDF files found in: {directory_path}")
        return None

    print("="*60)
    print(f"Batch Conversion: {len(edf_files)} files")
    print("="*60)
    print()

    results = []
    success_count = 0
    failed_count = 0

    for i, edf_file in enumerate(edf_files, 1):
        print(f"[{i}/{len(edf_files)}] {edf_file.name}")
        print("-"*60)

        result = convert_single_file(edf_file, verbose=False)
        results.append({
            'file': str(edf_file),
            'result': result
        })

        if result['success']:
            print(f"  ✓ Success ({result['converter_used']})")
            success_count += 1
        else:
            print(f"  ✗ Failed: {result['error']}")
            failed_count += 1

        print()

    # Summary
    print("="*60)
    print("Batch Conversion Summary")
    print("="*60)
    print(f"Total files: {len(edf_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print()

    return {
        'total': len(edf_files),
        'success': success_count,
        'failed': failed_count,
        'results': results
    }


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("Automatic EDF Annotation Converter")
        print("="*60)
        print()
        print("Usage:")
        print("  python auto_convert.py <EDF_FILE>")
        print("  python auto_convert.py <DIRECTORY>")
        print()
        print("Examples:")
        print("  # Convert single file")
        print("  python auto_convert.py Clinical_DB/Test1.EDF")
        print("  python auto_convert.py Clinical_DB/additional/PS0140_211029.EDF")
        print()
        print("  # Convert all files in directory")
        print("  python auto_convert.py Clinical_DB/additional/")
        print()
        print("Supported formats:")
        print("  - EDF+C (annotations embedded)")
        print("  - EDF+D (discontinuous)")
        print("  - Standard EDF + Excel annotations")
        sys.exit(1)

    target_path = Path(sys.argv[1])

    if not target_path.exists():
        print(f"Error: Path not found: {target_path}")
        sys.exit(1)

    if target_path.is_file():
        # Single file conversion
        result = convert_single_file(target_path, verbose=True)
        sys.exit(0 if result['success'] else 1)

    elif target_path.is_dir():
        # Directory batch conversion
        batch_result = convert_directory(target_path, verbose=True)
        if batch_result is None:
            sys.exit(1)
        sys.exit(0 if batch_result['failed'] == 0 else 1)

    else:
        print(f"Error: Invalid path: {target_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
