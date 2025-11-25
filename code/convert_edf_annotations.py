
import pyedflib
import datetime
import os
import numpy as np
import argparse

def convert_edf_annotations(edf_path):
    """
    Reads annotations from an EDF file and converts them into separate .txt files
    for sleep stages, arousals, and flow events, formatted for RBDtector.
    """
    try:
        f = pyedflib.EdfReader(edf_path)
        
        # --- Basic Info ---
        start_datetime = f.getStartdatetime()
        annotations = f.readAnnotations()
        
        # --- Get Base Filename ---
        base_filename = os.path.splitext(os.path.basename(edf_path))[0]
        output_dir = os.path.dirname(edf_path)

        # --- Categorize Annotations ---
        sleep_stages = []
        arousals = []
        flow_events = []

        for i in range(annotations[0].size):
            onset_sec = annotations[0][i]
            duration_sec = annotations[1][i]
            event_text = annotations[2][i]

            # Calculate onset and end datetimes with full precision
            onset_dt_full = start_datetime + datetime.timedelta(seconds=onset_sec)
            end_dt_full = onset_dt_full + datetime.timedelta(seconds=duration_sec)

            # Also create rounded versions for internal use (pandas alignment)
            onset_dt = onset_dt_full.replace(microsecond=0)
            end_dt = end_dt_full.replace(microsecond=0)

            event_data = {
                "onset_dt": onset_dt,  # For internal processing
                "onset_dt_full": onset_dt_full,  # For file writing with full precision
                "end_dt": end_dt,
                "end_dt_full": end_dt_full,
                "event_text": event_text
            }

            if "Sleep stage" in event_text:
                sleep_stages.append(event_data)
            elif "arousal" in event_text.lower():
                arousals.append(event_data)
            elif any(keyword in event_text for keyword in ["Apnea", "Hyp", "Desat"]):
                flow_events.append(event_data)
        
        f.close()

        # --- Determine Effective Start Time ---
        # Use the timestamp of the first sleep stage annotation as the start time
        # This aligns with RBDtector's behavior of trimming signal to sleep stages
        if sleep_stages:
            effective_start = sleep_stages[0]["onset_dt"]
            print(f"  EDF header start: {start_datetime}")
            print(f"  First sleep stage: {effective_start}")
            print(f"  Using first sleep stage as start time")
        else:
            effective_start = start_datetime
            print(f"  Warning: No sleep stages found, using EDF start time")

        # CRITICAL: Round to nearest second to avoid pandas resample() alignment issues
        # pandas resample('3s') aligns to 3-second boundaries, which causes index mismatch
        # if timestamps have microsecond precision. This leads to NaN values that astype(bool)
        # converts to True, marking ALL samples as artifacts!
        effective_start = effective_start.replace(microsecond=0)
        print(f"  Rounded to: {effective_start} (removed microseconds for pandas compatibility)")

        # --- Write Files ---
        write_sleep_profile(output_dir, base_filename, effective_start, sleep_stages)
        write_arousals(output_dir, base_filename, effective_start, arousals)
        write_flow_events(output_dir, base_filename, effective_start, flow_events)
        
        print(f"Successfully converted annotations for {base_filename}")

    except Exception as e:
        print(f"An error occurred while processing {edf_path}: {e}")

def write_sleep_profile(output_dir, base_filename, start_dt, events):
    """Writes the sleep profile txt file."""
    filename = os.path.join(output_dir, f"{base_filename} Sleep profile.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"Start Time: {start_dt.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("Version: 1.0\n\n")
        
        # Write events
        for event in events:
            time_str = event["onset_dt_full"].strftime('%H:%M:%S,%f')  # Use full precision timestamp
            stage = event["event_text"].replace("Sleep stage ", "").strip()
            # RBDtector seems to expect specific stage names
            if stage == 'R':
                stage = 'REM'
            f.write(f"{time_str}; {stage}\n")
    print(f"Created: {filename}")

def write_arousals(output_dir, base_filename, start_dt, events):
    """Writes the classification arousals txt file."""
    filename = os.path.join(output_dir, f"{base_filename} Classification Arousals.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header (matching Tutorial format exactly)
        f.write(f"Signal ID: Arousals\n")
        f.write(f"Start Time: {start_dt.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Unit: s\n")
        f.write(f"Signal Type: Impuls\n\n")

        # Write events (Tutorial format: onset-end; duration;event_name)
        for event in events:
            onset_str = event["onset_dt_full"].strftime('%H:%M:%S,%f')  # Use full precision timestamp
            end_str = event["end_dt_full"].strftime('%H:%M:%S,%f')  # Use full precision timestamp
            duration = (event["end_dt_full"] - event["onset_dt_full"]).total_seconds()
            event_name = event["event_text"]
            # No spaces around dash, include duration field
            f.write(f"{onset_str}-{end_str}; {int(duration)};{event_name}\n")
    print(f"Created: {filename}")

def write_flow_events(output_dir, base_filename, start_dt, events):
    """Writes the flow events txt file."""
    filename = os.path.join(output_dir, f"{base_filename} Flow Events.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        # Write header (matching Tutorial format)
        f.write(f"Signal ID: FlowEvents\n")
        f.write(f"Start Time: {start_dt.strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Unit: s\n")
        f.write(f"Signal Type: Impuls\n\n")

        # Write events (Tutorial format: onset-end; duration;event_name)
        for event in events:
            onset_str = event["onset_dt_full"].strftime('%H:%M:%S,%f')  # Use full precision timestamp
            end_str = event["end_dt_full"].strftime('%H:%M:%S,%f')  # Use full precision timestamp
            duration = (event["end_dt_full"] - event["onset_dt_full"]).total_seconds()
            event_name = event["event_text"]
            # No spaces around dash, include duration field
            f.write(f"{onset_str}-{end_str}; {int(duration)};{event_name}\n")
    print(f"Created: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert EDF annotations to RBDtector TXT format.')
    parser.add_argument('edf_file', type=str, help='Path to the EDF file to process.', default='/Users/hyeongsuk/Desktop/workspace/SNUH/SAI/clinical_db/Test1/test.edf')
    args = parser.parse_args()
    
    convert_edf_annotations(args.edf_file)
