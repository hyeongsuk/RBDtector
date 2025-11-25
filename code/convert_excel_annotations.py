#!/usr/bin/env python3
"""
Convert Excel Annotations to RBDtector Format

For Standard EDF files with separate Excel annotation files.
Converts sleep stages, arousals, and respiratory events to RBDtector format.

Author: Auto-generated for SNUH Atonia Index Project
Date: 2025-11-20

Usage:
    python convert_excel_annotations.py <EDF_PATH> [EXCEL_PATH]

    If EXCEL_PATH is not provided, will look for .xlsx file with same base name.
"""

import os
import sys
import datetime
import pandas as pd
from pathlib import Path


def convert_excel_annotations(edf_path, excel_path=None):
    """
    Convert Excel annotations to RBDtector format files.

    Parameters:
    -----------
    edf_path : str or Path
        Path to EDF file
    excel_path : str or Path, optional
        Path to Excel file. If None, will auto-detect.

    Returns:
    --------
    dict with keys:
        - success: bool
        - sleep_profile: str (path to generated file)
        - arousals: str (path to generated file)
        - flow_events: str (path to generated file)
        - error: str or None
    """
    edf_path = Path(edf_path)

    if not edf_path.exists():
        return {'success': False, 'error': f"EDF file not found: {edf_path}"}

    # Auto-detect Excel file if not provided
    if excel_path is None:
        excel_path = edf_path.with_suffix('.xlsx')
        if not excel_path.exists():
            excel_path = edf_path.with_suffix('.XLSX')

    excel_path = Path(excel_path)

    if not excel_path.exists():
        return {'success': False, 'error': f"Excel file not found: {excel_path}"}

    try:
        # Read EDF start time from header
        edf_start_time = read_edf_start_time(edf_path)

        # Read Excel annotations
        df = pd.read_excel(excel_path, sheet_name='Sheet1', header=None)

        # Extract different event types
        sleep_stages = extract_sleep_stages(df, edf_start_time)
        arousals = extract_arousals(df, edf_start_time)
        flow_events = extract_flow_events(df, edf_start_time)

        # Get output directory and base filename
        output_dir = edf_path.parent
        base_filename = edf_path.stem

        # Write output files
        sleep_profile_path = write_sleep_profile(output_dir, base_filename, edf_start_time, sleep_stages)
        arousals_path = write_arousals(output_dir, base_filename, edf_start_time, arousals)
        flow_events_path = write_flow_events(output_dir, base_filename, edf_start_time, flow_events)

        return {
            'success': True,
            'sleep_profile': str(sleep_profile_path),
            'arousals': str(arousals_path),
            'flow_events': str(flow_events_path),
            'error': None
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def read_edf_start_time(edf_path):
    """Read start time from EDF header."""
    with open(edf_path, 'rb') as f:
        header = f.read(256)

        # Start date: bytes 168-176 (dd.mm.yy)
        # Start time: bytes 176-184 (hh.mm.ss)
        start_date_str = header[168:176].decode('ascii', errors='ignore').strip()
        start_time_str = header[176:184].decode('ascii', errors='ignore').strip()

        # Parse date (dd.mm.yy format)
        day, month, year = start_date_str.split('.')
        year = int(year)
        if year < 100:
            year += 2000  # Assume 21st century

        # Parse time (hh.mm.ss format)
        hour, minute, second = start_time_str.split('.')

        start_datetime = datetime.datetime(
            int(year), int(month), int(day),
            int(hour), int(minute), int(second)
        )

        return start_datetime


def extract_sleep_stages(df, edf_start_time):
    """Extract sleep stage annotations from Excel."""
    # Filter rows containing "Stage -"
    stage_rows = df[df[3].astype(str).str.contains('Stage -', case=False, na=False)]

    stages = []

    for _, row in stage_rows.iterrows():
        timestamp_str = str(row[2])  # Column 2: timestamp (HH:MM:SS.ff)
        event_text = str(row[3])     # Column 3: event description

        # Parse timestamp
        onset_time = parse_timestamp(timestamp_str, edf_start_time)

        # Extract stage name
        stage_name = event_text.replace('Stage -', '').strip()

        stages.append({
            'onset_time': onset_time,
            'stage': stage_name
        })

    return stages


def extract_arousals(df, edf_start_time):
    """Extract arousal events from Excel."""
    arousal_rows = df[df[3].astype(str).str.contains('Arousal -', case=False, na=False)]

    arousals = []

    for _, row in arousal_rows.iterrows():
        timestamp_str = str(row[2])
        event_text = str(row[3])

        # Parse timestamp
        onset_time = parse_timestamp(timestamp_str, edf_start_time)

        # Extract duration from text: "Arousal - Dur: 19.6 sec. - Type"
        duration_sec = 0.0
        if 'Dur:' in event_text:
            try:
                dur_part = event_text.split('Dur:')[1].split('sec.')[0].strip()
                duration_sec = float(dur_part)
            except (IndexError, ValueError):
                pass

        # Extract type (last part after final dash)
        event_type = "Arousal"
        if ' - ' in event_text:
            parts = event_text.split(' - ')
            if len(parts) >= 3:
                event_type = parts[-1].strip()

        # Calculate end time
        end_time = onset_time + datetime.timedelta(seconds=duration_sec)

        arousals.append({
            'onset_time': onset_time,
            'end_time': end_time,
            'duration': duration_sec,
            'type': event_type
        })

    return arousals


def extract_flow_events(df, edf_start_time):
    """Extract respiratory/flow events from Excel."""
    flow_rows = df[df[3].astype(str).str.contains('Respiratory Event|Desaturation', case=False, na=False)]

    events = []

    for _, row in flow_rows.iterrows():
        timestamp_str = str(row[2])
        event_text = str(row[3])

        onset_time = parse_timestamp(timestamp_str, edf_start_time)

        # Extract duration
        duration_sec = 0.0
        if 'Dur:' in event_text:
            try:
                dur_part = event_text.split('Dur:')[1].split('sec.')[0].strip()
                duration_sec = float(dur_part)
            except (IndexError, ValueError):
                pass

        end_time = onset_time + datetime.timedelta(seconds=duration_sec)

        # Extract event type
        event_type = "Flow Event"
        if 'Hyp' in event_text:
            event_type = "Hypopnea"
        elif 'Apnea' in event_text:
            event_type = "Apnea"
        elif 'Desaturation' in event_text or 'Desat' in event_text:
            event_type = "Desaturation"

        events.append({
            'onset_time': onset_time,
            'end_time': end_time,
            'duration': duration_sec,
            'type': event_type
        })

    return events


def parse_timestamp(timestamp_str, edf_start_time):
    """
    Parse timestamp string from Excel and convert to datetime.

    Excel format: HH:MM:SS.ff (centiseconds)
    """
    try:
        # Split time components
        parts = timestamp_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])

        # Handle seconds and centiseconds
        sec_parts = parts[2].split('.')
        second = int(sec_parts[0])
        centisecond = 0

        if len(sec_parts) > 1:
            # Convert centiseconds to microseconds
            cs_str = sec_parts[1][:2]  # Take only first 2 digits
            centisecond = int(cs_str)

        microsecond = centisecond * 10000  # Convert centiseconds to microseconds

        # Combine with EDF start date
        timestamp = datetime.datetime(
            edf_start_time.year,
            edf_start_time.month,
            edf_start_time.day,
            hour, minute, second, microsecond
        )

        return timestamp

    except Exception as e:
        print(f"Warning: Failed to parse timestamp '{timestamp_str}': {e}")
        return edf_start_time


def write_sleep_profile(output_dir, base_filename, start_time, stages):
    """Write sleep profile file."""
    filename = output_dir / f"{base_filename} Sleep profile.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"Start Time: {start_time.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("Version: 1.0\n\n")

        # Write stages
        for stage in stages:
            # Format: HH:MM:SS,ffffff; STAGE
            time_str = stage['onset_time'].strftime('%H:%M:%S,%f')
            stage_name = stage['stage']

            # Normalize stage names
            if stage_name in ['No Stage', 'NoStage']:
                continue  # Skip "No Stage" entries
            elif stage_name == 'W':
                stage_name = 'W'
            elif stage_name in ['N1', 'N2', 'N3']:
                stage_name = stage_name
            elif stage_name in ['R', 'REM']:
                stage_name = 'REM'  # Convert "R" to "REM"

            f.write(f"{time_str}; {stage_name}\n")

    print(f"  ✓ Sleep Profile: {len(stages)} stages → {filename.name}")
    return filename


def write_arousals(output_dir, base_filename, start_time, arousals):
    """Write arousals file."""
    filename = output_dir / f"{base_filename} Classification Arousals.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        # Write header (matching RBDtector format)
        f.write("Signal ID: Arousals\n")
        f.write(f"Start Time: {start_time.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("Unit: s\n")
        f.write("Signal Type: Impuls\n\n")

        # Write events
        for arousal in arousals:
            # Format: HH:MM:SS,ffffff-HH:MM:SS,ffffff; DURATION; TYPE
            onset_str = arousal['onset_time'].strftime('%H:%M:%S,%f')
            end_str = arousal['end_time'].strftime('%H:%M:%S,%f')
            duration = arousal['duration']
            event_type = arousal['type']

            f.write(f"{onset_str}-{end_str}; {duration:.2f}; {event_type}\n")

    print(f"  ✓ Arousals: {len(arousals)} events → {filename.name}")
    return filename


def write_flow_events(output_dir, base_filename, start_time, events):
    """Write flow events file."""
    filename = output_dir / f"{base_filename} Flow Events.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        # Write header
        f.write("Signal ID: Flow Events\n")
        f.write(f"Start Time: {start_time.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("Unit: s\n")
        f.write("Signal Type: Impuls\n\n")

        # Write events
        for event in events:
            onset_str = event['onset_time'].strftime('%H:%M:%S,%f')
            end_str = event['end_time'].strftime('%H:%M:%S,%f')
            duration = event['duration']
            event_type = event['type']

            f.write(f"{onset_str}-{end_str}; {duration:.2f}; {event_type}\n")

    print(f"  ✓ Flow Events: {len(events)} events → {filename.name}")
    return filename


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python convert_excel_annotations.py <EDF_PATH> [EXCEL_PATH]")
        print()
        print("Example:")
        print("  python convert_excel_annotations.py PS0140_211029.EDF")
        print("  python convert_excel_annotations.py PS0140_211029.EDF PS0140_211029.xlsx")
        sys.exit(1)

    edf_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else None

    print("="*60)
    print("Excel to RBDtector Annotation Converter")
    print("="*60)
    print()
    print(f"EDF file: {edf_path}")
    if excel_path:
        print(f"Excel file: {excel_path}")
    else:
        print(f"Excel file: Auto-detect")
    print()

    result = convert_excel_annotations(edf_path, excel_path)

    if result['success']:
        print()
        print("✓ Conversion successful!")
        print()
        print("Output files:")
        print(f"  → {Path(result['sleep_profile']).name}")
        print(f"  → {Path(result['arousals']).name}")
        print(f"  → {Path(result['flow_events']).name}")
        sys.exit(0)
    else:
        print()
        print(f"✗ Conversion failed: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
