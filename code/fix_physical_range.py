#!/usr/bin/env python3
"""
Fix physical range in existing EDF files to prevent clipping.

Reads an existing EDF+C file, recalculates physical ranges using full data range + margin,
and writes a new file with corrected ranges.

This bypasses the need for mne-python and avoids the scipy compatibility issue.
"""

import sys
import numpy as np
from pathlib import Path
import pyedflib


def fix_physical_range(input_edf, output_edf):
    """
    Fix physical range in existing EDF file.

    Parameters:
    -----------
    input_edf : str or Path
        Path to input EDF+C file
    output_edf : str or Path
        Path to output EDF+C file with fixed ranges

    Returns:
    --------
    dict with keys:
        - success: bool
        - error: str or None
    """
    input_edf = Path(input_edf)
    output_edf = Path(output_edf)

    if not input_edf.exists():
        return {'success': False, 'error': f'Input file not found: {input_edf}'}

    print("="*80)
    print("Fixing Physical Range in EDF File")
    print("="*80)
    print()
    print(f"Input:  {input_edf}")
    print(f"Output: {output_edf}")
    print()

    try:
        # Step 1: Read existing EDF file
        print("Step 1: Reading existing EDF file...")
        f_in = pyedflib.EdfReader(str(input_edf))

        n_channels = f_in.signals_in_file
        ch_names = f_in.getSignalLabels()

        print(f"  ✓ Successfully read")
        print(f"    Duration: {f_in.getFileDuration()/3600:.2f} hours")
        print(f"    Sampling frequency: {f_in.getSampleFrequency(0)} Hz")
        print(f"    Number of channels: {n_channels}")
        print()

        # Read all signals and headers
        signals = []
        old_headers = []
        for i in range(n_channels):
            data = f_in.readSignal(i)
            signals.append(data)

            old_headers.append({
                'label': f_in.getLabel(i),
                'dimension': f_in.getPhysicalDimension(i),
                'sample_frequency': int(f_in.getSampleFrequency(i)),
                'physical_min': f_in.getPhysicalMinimum(i),
                'physical_max': f_in.getPhysicalMaximum(i),
                'digital_min': f_in.getDigitalMinimum(i),
                'digital_max': f_in.getDigitalMaximum(i),
                'transducer': f_in.getTransducer(i),
                'prefilter': f_in.getPrefilter(i)
            })

        # Get header info
        patient_name = f_in.getPatientName()
        start_datetime = f_in.getStartdatetime()

        f_in.close()

        # Step 2: Recalculate physical ranges
        print("Step 2: Recalculating physical ranges...")

        new_headers = []
        emg_channels = []

        for i, ch_name in enumerate(ch_names):
            ch_data = signals[i]

            # Identify EMG/EEG/EOG channels
            is_biosignal = any(kw in ch_name for kw in ['EMG', 'EEG', 'EOG', 'Chin', 'Lat', 'Rat'])

            if is_biosignal:
                emg_channels.append(ch_name)

                # Calculate physical range using FULL data range (not percentile)
                # Previous 99th percentile method caused clipping of large EMG bursts
                # AASM recommends ±50 mV input range to prevent signal saturation
                abs_max = max(abs(ch_data.min()), abs(ch_data.max()))

                # Add 100% margin to accommodate signal variations during sleep
                # This ensures no clipping of phasic/tonic EMG bursts
                physical_max = abs_max * 2.0
                physical_min = -physical_max

                # Ensure minimum range of ±500 µV for EMG channels (AASM guidelines)
                min_range = 500.0  # µV
                if abs(physical_max) < min_range:
                    physical_max = min_range
                    physical_min = -min_range

                # Check for improvement
                old_range = old_headers[i]['physical_max'] - old_headers[i]['physical_min']
                new_range = physical_max - physical_min

                print(f"  {ch_name}:")
                print(f"    Old range: [{old_headers[i]['physical_min']:.2f}, {old_headers[i]['physical_max']:.2f}] µV (span: {old_range:.2f})")
                print(f"    New range: [{physical_min:.2f}, {physical_max:.2f}] µV (span: {new_range:.2f})")
                print(f"    Data range: [{ch_data.min():.2f}, {ch_data.max():.2f}] µV")

                # Check for clipping in old range
                old_phys_min = old_headers[i]['physical_min']
                old_phys_max = old_headers[i]['physical_max']
                tolerance = abs(old_phys_max) * 0.01  # 1% tolerance

                clipped_low = np.sum(ch_data <= (old_phys_min + tolerance))
                clipped_high = np.sum(ch_data >= (old_phys_max - tolerance))

                if clipped_low > 0 or clipped_high > 0:
                    print(f"    ⚠️  Old range had clipping: {clipped_low + clipped_high} samples ({100*(clipped_low + clipped_high)/len(ch_data):.3f}%)")
                else:
                    print(f"    ✓ Old range had no clipping")

                print()
            else:
                # Non-EMG channels: keep original range
                physical_min = old_headers[i]['physical_min']
                physical_max = old_headers[i]['physical_max']

            # Create new header
            header = {
                'label': ch_name,
                'dimension': old_headers[i]['dimension'],
                'sample_frequency': old_headers[i]['sample_frequency'],
                'physical_min': physical_min,
                'physical_max': physical_max,
                'digital_min': old_headers[i]['digital_min'],
                'digital_max': old_headers[i]['digital_max'],
                'transducer': old_headers[i]['transducer'],
                'prefilter': old_headers[i]['prefilter']
            }
            new_headers.append(header)

        print(f"  ✓ Recalculated {len(emg_channels)} EMG/EEG/EOG channels")
        print()

        # Step 3: Write new EDF file
        print("Step 3: Writing EDF file with corrected ranges...")
        f_out = pyedflib.EdfWriter(str(output_edf), n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)

        # Set patient and recording info
        f_out.setPatientName(patient_name)
        f_out.setStartdatetime(start_datetime)

        # Set signal headers
        f_out.setSignalHeaders(new_headers)

        # Write data
        sfreq = new_headers[0]['sample_frequency']
        record_duration = 1  # second
        samples_per_record = int(sfreq * record_duration)
        n_records = int(np.ceil(signals[0].shape[0] / samples_per_record))

        print(f"  Writing {n_records} data records...")
        for record_idx in range(n_records):
            start_sample = record_idx * samples_per_record
            end_sample = min((record_idx + 1) * samples_per_record, signals[0].shape[0])

            for ch_idx in range(n_channels):
                record_data = signals[ch_idx][start_sample:end_sample]

                # Pad last record if needed
                if len(record_data) < samples_per_record and record_idx == n_records - 1:
                    pad_length = samples_per_record - len(record_data)
                    record_data = np.pad(record_data, (0, pad_length), mode='edge')

                f_out.writePhysicalSamples(record_data)

            if (record_idx + 1) % 1000 == 0:
                print(f"    Progress: {record_idx + 1}/{n_records} records")

        f_out.close()

        print(f"  ✓ Export complete!")
        print()

        # Step 4: Verify
        print("Step 4: Verifying corrected file...")
        try:
            f_verify = pyedflib.EdfReader(str(output_edf))

            print("  ✓ Verification SUCCESS!")
            print()
            print("  Corrected file can be read by pyedflib:")
            print(f"    Duration: {f_verify.getFileDuration()} seconds ({f_verify.getFileDuration()/3600:.2f} hours)")
            print(f"    Number of signals: {f_verify.signals_in_file}")
            print(f"    Start time: {f_verify.getStartdatetime()}")
            print()

            # Check EMG channels
            labels = [f_verify.getLabel(i) for i in range(f_verify.signals_in_file)]
            emg_labels = [l for l in labels if any(kw in l for kw in ['EMG', 'Chin', 'Lat', 'Rat'])]
            print("  EMG channels in corrected file:")
            for label in emg_labels:
                idx = labels.index(label)
                phys_min = f_verify.getPhysicalMinimum(idx)
                phys_max = f_verify.getPhysicalMaximum(idx)
                print(f"    {idx}: {label}")
                print(f"       Range: [{phys_min:.2f}, {phys_max:.2f}] µV")

            f_verify.close()

            print()
            print("="*80)
            print("PHYSICAL RANGE FIX SUCCESSFUL!")
            print("="*80)
            print()
            print("Next steps:")
            print("  1. This EDF file now has correct physical ranges")
            print("  2. Run preprocessing on this file")
            print("  3. Use preprocessed file with RBDtector")

            return {
                'success': True,
                'error': None
            }

        except Exception as e:
            print(f"  ✗ Verification FAILED: {e}")
            print()
            print("  The corrected file cannot be read by pyedflib.")
            return {
                'success': False,
                'error': f'Verification failed: {e}'
            }

    except Exception as e:
        print(f"✗ Physical range fix FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python fix_physical_range.py <INPUT_EDF> [OUTPUT_EDF]")
        print()
        print("Example:")
        print("  python fix_physical_range.py PS0140_211029.edf PS0140_211029_fixed.edf")
        sys.exit(1)

    input_edf = sys.argv[1]
    output_edf = sys.argv[2] if len(sys.argv) > 2 else None

    if output_edf is None:
        # Default: add _fixed suffix
        input_path = Path(input_edf)
        output_edf = input_path.parent / f"{input_path.stem}_fixed.edf"

    result = fix_physical_range(input_edf, output_edf)

    if result['success']:
        sys.exit(0)
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
