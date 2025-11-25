#!/usr/bin/env python3
"""
preprocess_emg.py
EMG signal preprocessing for clinical PSG data to improve RBDtector artifact detection.

Purpose: Remove DC/low-frequency contamination and 60 Hz power line interference
         from clinical EMG signals while preserving the EMG band (20-100 Hz).

Evidence-based filter parameters determined from signal analysis (251105_02):
- CHIN: High-pass 10 Hz, Low-pass 100 Hz, Notch 60 Hz (Q=30)
- LEGS: High-pass 15 Hz, Low-pass 100 Hz, Notch 60 Hz (Q=30)
- Filter type: Butterworth 4th order (zero-phase via filtfilt)

Author: Research Team
Date: 2025-11-05
"""

import sys
import os
from pathlib import Path
import numpy as np
from scipy import signal
import pyedflib
import matplotlib.pyplot as plt
from datetime import datetime

# ============================================================================
# Configuration / 설정
# ============================================================================

# Sampling rate (from EDF specification)
FS = 256  # Hz

# Filter parameters based on signal analysis
FILTER_PARAMS = {
    'CHIN': {
        'highpass': 10,   # Hz - Remove DC and low-frequency drift
        'lowpass': 100,   # Hz - Preserve EMG band, remove high-frequency noise
        'notch': 60,      # Hz - Remove power line interference
        'notch_q': 30     # Q factor for notch filter
    },
    'LEG': {
        'highpass': 15,   # Hz - More aggressive for legs (higher contamination)
        'lowpass': 100,   # Hz
        'notch': 60,      # Hz
        'notch_q': 30
    }
}

# Channel identification patterns
CHANNEL_PATTERNS = {
    'CHIN': 'CHIN',
    'RLEG': 'RLEG',
    'LLEG': 'LLEG'
}

# Butterworth filter order
FILTER_ORDER = 4

# ============================================================================
# Filter Design Functions / 필터 설계 함수
# ============================================================================

def design_bandpass_filter(lowcut, highcut, fs, order=4):
    """
    Design Butterworth bandpass filter.

    Parameters:
        lowcut: High-pass cutoff frequency (Hz)
        highcut: Low-pass cutoff frequency (Hz)
        fs: Sampling frequency (Hz)
        order: Filter order

    Returns:
        b, a: Filter coefficients
    """
    nyq = 0.5 * fs

    # Ensure cutoff frequencies are within valid range (0 < Wn < 1)
    # Leave some margin: max 95% of Nyquist frequency
    max_freq = nyq * 0.95

    if highcut >= max_freq:
        highcut_adjusted = max_freq
        print(f"  ⚠️  Lowpass {highcut} Hz adjusted to {highcut_adjusted:.1f} Hz (Nyquist limit: {nyq} Hz)")
        highcut = highcut_adjusted

    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return b, a

def design_notch_filter(f0, fs, Q=30):
    """
    Design notch filter for power line interference.

    Parameters:
        f0: Frequency to remove (Hz)
        fs: Sampling frequency (Hz)
        Q: Quality factor (higher = narrower notch)

    Returns:
        b, a: Filter coefficients
    """
    w0 = f0 / (fs / 2)  # Normalized frequency
    b, a = signal.iirnotch(w0, Q)
    return b, a

def apply_filters(data, channel_type, fs):
    """
    Apply bandpass and notch filters to EMG signal.

    Parameters:
        data: Signal data (1D numpy array)
        channel_type: 'CHIN' or 'LEG'
        fs: Sampling frequency (Hz)

    Returns:
        filtered_data: Filtered signal
    """
    # Get filter parameters for this channel type
    params = FILTER_PARAMS[channel_type]

    # Step 1: Bandpass filter (combines high-pass and low-pass)
    b_bp, a_bp = design_bandpass_filter(
        params['highpass'],
        params['lowpass'],
        fs,
        order=FILTER_ORDER
    )
    filtered = signal.filtfilt(b_bp, a_bp, data)

    # Step 2: Notch filter for 60 Hz
    b_notch, a_notch = design_notch_filter(
        params['notch'],
        fs,
        Q=params['notch_q']
    )
    filtered = signal.filtfilt(b_notch, a_notch, filtered)

    return filtered

# ============================================================================
# Frequency Analysis Functions / 주파수 분석 함수
# ============================================================================

def analyze_frequency_content(data, fs, label=""):
    """
    Analyze frequency content of signal using FFT.

    Parameters:
        data: Signal data
        fs: Sampling frequency
        label: Label for printing

    Returns:
        freqs: Frequency bins
        psd: Power spectral density
        stats: Dictionary of frequency band statistics
    """
    # Compute FFT
    n = len(data)
    fft = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(n, d=1/fs)
    psd = np.abs(fft) ** 2

    # Normalize PSD
    total_power = np.sum(psd)
    psd_norm = psd / total_power * 100  # Percentage

    # Calculate power in different bands
    dc_low = np.sum(psd_norm[(freqs >= 0) & (freqs < 10)])
    emg_band = np.sum(psd_norm[(freqs >= 20) & (freqs <= 100)])
    hz_60 = np.sum(psd_norm[(freqs >= 58) & (freqs <= 62)])

    stats = {
        'dc_low': dc_low,
        'emg_band': emg_band,
        'hz_60': hz_60
    }

    if label:
        print(f"\n  {label}:")
        print(f"    DC/Low-freq (0-10 Hz): {dc_low:.1f}%")
        print(f"    EMG band (20-100 Hz): {emg_band:.1f}%")
        print(f"    60 Hz (58-62 Hz): {hz_60:.1f}%")

    return freqs, psd_norm, stats

# ============================================================================
# EDF Processing Functions / EDF 처리 함수
# ============================================================================

def identify_channel_type(label):
    """
    Identify channel type from label.

    Parameters:
        label: Channel label string

    Returns:
        'CHIN', 'LEG', or None
    """
    label_upper = label.upper()
    if 'CHIN' in label_upper:
        return 'CHIN'
    elif 'RLEG' in label_upper or 'LLEG' in label_upper or 'RAT' in label_upper or 'LAT' in label_upper:
        return 'LEG'
    return None

def read_edf(edf_path):
    """
    Read EDF file and extract signal data and metadata.

    Parameters:
        edf_path: Path to EDF file

    Returns:
        signals: Dictionary of {channel_label: signal_data}
        header: EDF header information (including signal headers)
        fs: Sampling rate (Hz) from first EMG channel
    """
    print(f"\n{'='*70}")
    print(f"Reading EDF file: {Path(edf_path).name}")
    print(f"{'='*70}")

    f = pyedflib.EdfReader(str(edf_path))

    # Get header info
    n_channels = f.signals_in_file
    signal_labels = f.getSignalLabels()

    print(f"\nChannels found: {n_channels}")
    for i, label in enumerate(signal_labels):
        print(f"  [{i}] {label}")

    # Detect sampling rate from first EMG channel
    fs = None
    for i, label in enumerate(signal_labels):
        if identify_channel_type(label):
            fs = f.getSampleFrequency(i)
            print(f"\n⚙️  Detected sampling rate: {fs} Hz (from {label})")
            break

    if fs is None:
        # Fallback to default if no EMG channels found
        fs = FS
        print(f"\n⚠️  No EMG channels found, using default: {fs} Hz")

    # Read signals
    signals = {}
    signal_headers = {}
    for i, label in enumerate(signal_labels):
        data = f.readSignal(i)
        signals[label] = data

        # Get signal header info
        signal_headers[label] = {
            'label': label,
            'dimension': f.getPhysicalDimension(i),
            'sample_rate': f.getSampleFrequency(i),
            'physical_max': f.getPhysicalMaximum(i),
            'physical_min': f.getPhysicalMinimum(i),
            'digital_max': f.getDigitalMaximum(i),
            'digital_min': f.getDigitalMinimum(i),
            'transducer': f.getTransducer(i),
            'prefilter': f.getPrefilter(i)
        }

        print(f"\n  {label}: {len(data)} samples, "
              f"{len(data)/f.getSampleFrequency(i):.1f} seconds")

    # Get header for writing new EDF
    header = {
        'technician': f.getTechnician(),
        'recording_additional': f.getRecordingAdditional(),
        'patientname': f.getPatientName(),
        'patient_additional': f.getPatientAdditional(),
        'patientcode': f.getPatientCode(),
        'equipment': f.getEquipment(),
        'admincode': f.getAdmincode(),
        'sex': f.getSex(),
        'startdate': f.getStartdatetime(),
        'birthdate': f.getBirthdate(),
        'signal_headers': signal_headers
    }

    f.close()
    return signals, header, fs

def preprocess_edf(input_path, output_path):
    """
    Preprocess EDF file: apply filters to EMG channels.

    Parameters:
        input_path: Input EDF file path
        output_path: Output EDF file path (preprocessed)

    Returns:
        success: Boolean indicating success
        report: Dictionary with preprocessing statistics
    """
    print(f"\n{'='*70}")
    print(f"EMG PREPROCESSING / EMG 전처리")
    print(f"{'='*70}")
    print(f"\nInput:  {Path(input_path).name}")
    print(f"Output: {Path(output_path).name}")

    # Read EDF (now returns fs as well)
    signals, header, fs = read_edf(input_path)

    # Process each EMG channel
    preprocessed_signals = {}
    report = {
        'input_file': str(input_path),
        'output_file': str(output_path),
        'timestamp': datetime.now().isoformat(),
        'sampling_rate': float(fs),
        'channels': {}
    }

    print(f"\n{'='*70}")
    print("FILTER APPLICATION / 필터 적용")
    print(f"{'='*70}")
    print(f"Using sampling rate: {fs} Hz")

    for label, data in signals.items():
        channel_type = identify_channel_type(label)

        if channel_type:
            print(f"\n[{label}] - {channel_type} channel")
            print(f"  Filter: {FILTER_PARAMS[channel_type]['highpass']}-"
                  f"{FILTER_PARAMS[channel_type]['lowpass']} Hz bandpass + "
                  f"{FILTER_PARAMS[channel_type]['notch']} Hz notch")

            # Analyze before
            print(f"\n  Before preprocessing:")
            _, _, stats_before = analyze_frequency_content(
                data, fs, label="Original"
            )

            # Apply filters (use actual fs from EDF)
            filtered_data = apply_filters(data, channel_type, fs)

            # Analyze after
            print(f"\n  After preprocessing:")
            _, _, stats_after = analyze_frequency_content(
                filtered_data, fs, label="Filtered"
            )

            # Calculate improvement
            dc_reduction = stats_before['dc_low'] - stats_after['dc_low']
            emg_change = stats_after['emg_band'] - stats_before['emg_band']
            notch_reduction = stats_before['hz_60'] - stats_after['hz_60']

            print(f"\n  Improvement:")
            print(f"    DC/Low-freq reduction: {dc_reduction:+.1f}%")
            print(f"    EMG band change: {emg_change:+.1f}%")
            print(f"    60 Hz reduction: {notch_reduction:+.1f}%")

            preprocessed_signals[label] = filtered_data

            # Store in report
            report['channels'][label] = {
                'type': channel_type,
                'before': stats_before,
                'after': stats_after,
                'improvement': {
                    'dc_reduction': float(dc_reduction),
                    'emg_change': float(emg_change),
                    'notch_reduction': float(notch_reduction)
                }
            }

        else:
            # Non-EMG channels: keep original
            print(f"\n[{label}] - Non-EMG channel (kept original)")
            preprocessed_signals[label] = data
            report['channels'][label] = {'type': 'non-EMG', 'processed': False}

    # Write preprocessed EDF
    print(f"\n{'='*70}")
    print("WRITING PREPROCESSED EDF / 전처리된 EDF 작성")
    print(f"{'='*70}")

    write_edf(output_path, preprocessed_signals, header, fs)

    print(f"\n✅ Preprocessing complete!")
    print(f"   Output: {output_path}")

    return True, report

def write_edf(output_path, signals_dict, header, fs):
    """
    Write signals to new EDF file.

    Parameters:
        output_path: Output file path
        signals_dict: Dictionary of {label: signal_data} (in order)
        header: Header information from original EDF (includes signal_headers)
        fs: Sampling rate (Hz)
    """
    # Create EDF writer
    n_channels = len(signals_dict)

    f = pyedflib.EdfWriter(str(output_path), n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)

    # Set patient header
    f.setPatientName(header.get('patientname', ''))
    f.setPatientCode(header.get('patientcode', ''))
    f.setPatientAdditional(header.get('patient_additional', ''))
    f.setTechnician(header.get('technician', ''))
    f.setEquipment(header.get('equipment', ''))
    f.setRecordingAdditional(header.get('recording_additional', ''))
    f.setStartdatetime(header.get('startdate'))

    if header.get('birthdate'):
        f.setBirthdate(header.get('birthdate'))
    if header.get('sex') is not None:
        f.setSex(header.get('sex'))

    # Set signal headers (use original headers, update prefilter for processed channels)
    signal_headers_orig = header.get('signal_headers', {})
    channel_info = []

    for label in signals_dict.keys():
        orig_header = signal_headers_orig.get(label, {})

        # Update prefilter string for EMG channels
        channel_type = identify_channel_type(label)
        if channel_type:
            prefilter = (f"HP:{FILTER_PARAMS[channel_type]['highpass']}Hz "
                        f"LP:{FILTER_PARAMS[channel_type]['lowpass']}Hz "
                        f"N:{FILTER_PARAMS[channel_type]['notch']}Hz")
        else:
            prefilter = orig_header.get('prefilter', '')

        ch_dict = {
            'label': orig_header.get('label', label),
            'dimension': orig_header.get('dimension', 'uV'),
            'sample_frequency': orig_header.get('sample_rate', fs),
            'physical_max': orig_header.get('physical_max', 1000),
            'physical_min': orig_header.get('physical_min', -1000),
            'digital_max': orig_header.get('digital_max', 32767),
            'digital_min': orig_header.get('digital_min', -32768),
            'transducer': orig_header.get('transducer', ''),
            'prefilter': prefilter
        }
        channel_info.append(ch_dict)

    f.setSignalHeaders(channel_info)

    # Write signals (all at once)
    data_list = list(signals_dict.values())
    f.writeSamples(data_list)

    f.close()
    print(f"  Written: {n_channels} channels, {len(data_list[0])} samples")

# ============================================================================
# Main Processing Function / 메인 처리 함수
# ============================================================================

def process_test_file(test_name):
    """
    Process a single test file.

    Parameters:
        test_name: Test name (e.g., 'Test1')

    Returns:
        success: Boolean
        report: Processing report
    """
    # Paths
    workspace = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
    test_dir = workspace / "Results" / "raw" / test_name

    input_edf = test_dir / f"{test_name}.edf"
    output_edf = test_dir / f"{test_name}_preprocessed.edf"

    if not input_edf.exists():
        print(f"\n❌ ERROR: Input EDF not found: {input_edf}")
        return False, None

    # Preprocess
    success, report = preprocess_edf(input_edf, output_edf)

    # Save report
    if success:
        import json
        report_path = test_dir / f"{test_name}_preprocessing_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved: {report_path.name}")

    return success, report

def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Preprocess EMG signals in clinical PSG EDF files'
    )
    parser.add_argument(
        'test_name',
        help='Test name (e.g., Test1, Test2)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Generate validation plots'
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("EMG PREPROCESSING TOOL / EMG 전처리 도구")
    print(f"{'='*70}")
    print(f"Test: {args.test_name}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    # Process
    success, report = process_test_file(args.test_name)

    # Summary
    print(f"\n{'='*70}")
    print("PREPROCESSING SUMMARY / 전처리 요약")
    print(f"{'='*70}")

    if success:
        print(f"\n✅ SUCCESS: {args.test_name} preprocessed successfully")
        print(f"\nFilter parameters applied:")
        print(f"  CHIN: {FILTER_PARAMS['CHIN']['highpass']}-{FILTER_PARAMS['CHIN']['lowpass']} Hz "
              f"+ {FILTER_PARAMS['CHIN']['notch']} Hz notch")
        print(f"  LEGS: {FILTER_PARAMS['LEG']['highpass']}-{FILTER_PARAMS['LEG']['lowpass']} Hz "
              f"+ {FILTER_PARAMS['LEG']['notch']} Hz notch")
        print(f"\nNext step:")
        print(f"  Run RBDtector on preprocessed data:")
        print(f"  → Use: {args.test_name}_preprocessed.edf")
        return 0
    else:
        print(f"\n❌ FAILED: Could not preprocess {args.test_name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
