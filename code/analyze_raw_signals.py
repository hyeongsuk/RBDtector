#!/usr/bin/env python3
"""
analyze_raw_signals.py
Analyzes raw EMG signals from EDF files for preprocessing parameter determination.

Author: Claude Code
Date: 2025-11-05
"""

import pyedflib
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import sys

# EMG channel names (based on EDF analysis)
EMG_CHANNELS = {
    'CHIN': 'EMG CHIN1-CHINz',
    'RLEG': 'EMG RLEG+',
    'LLEG': 'EMG LLEG+'
}


def extract_edf_specs(edf_path):
    """Extract technical specifications from EDF file."""
    print(f"\n{'='*70}")
    print(f"Analyzing: {Path(edf_path).name}")
    print(f"{'='*70}\n")

    f = pyedflib.EdfReader(edf_path)

    specs = {
        'file': Path(edf_path).name,
        'duration_hours': f.getFileDuration() / 3600,
        'start_datetime': f.getStartdatetime(),
        'channels': {}
    }

    # Find EMG channel indices
    channel_labels = [f.getLabel(i) for i in range(f.signals_in_file)]

    for emg_name, emg_label in EMG_CHANNELS.items():
        try:
            ch_idx = channel_labels.index(emg_label)

            specs['channels'][emg_name] = {
                'index': ch_idx,
                'label': f.getLabel(ch_idx),
                'sample_freq': f.getSampleFrequency(ch_idx),
                'physical_dim': f.getPhysicalDimension(ch_idx),
                'physical_min': f.getPhysicalMinimum(ch_idx),
                'physical_max': f.getPhysicalMaximum(ch_idx),
                'digital_min': f.getDigitalMinimum(ch_idx),
                'digital_max': f.getDigitalMaximum(ch_idx),
                'prefilter': f.getPrefilter(ch_idx),
                'transducer': f.getTransducer(ch_idx)
            }

            # Read signal data
            signal = f.readSignal(ch_idx)
            specs['channels'][emg_name]['signal'] = signal

            # Calculate statistics
            specs['channels'][emg_name]['stats'] = {
                'mean': np.mean(signal),
                'std': np.std(signal),
                'rms': np.sqrt(np.mean(signal**2)),
                'min': np.min(signal),
                'max': np.max(signal),
                'range': np.max(signal) - np.min(signal)
            }

        except ValueError:
            print(f"Warning: Channel {emg_label} not found in {specs['file']}")
            specs['channels'][emg_name] = None

    f.close()
    return specs


def analyze_frequency_content(signal, fs, channel_name):
    """Analyze frequency content using FFT."""
    # Compute FFT
    fft = np.fft.fft(signal)
    fft_freq = np.fft.fftfreq(len(signal), 1/fs)

    # Only keep positive frequencies
    positive_freq_idx = fft_freq > 0
    fft_freq = fft_freq[positive_freq_idx]
    fft_mag = np.abs(fft[positive_freq_idx])

    # Calculate power in different frequency bands
    def band_power(freqs, magnitudes, low, high):
        band_idx = (freqs >= low) & (freqs < high)
        return np.sum(magnitudes[band_idx]**2)

    total_power = np.sum(fft_mag**2)

    bands = {
        '0-10 Hz (DC/motion)': band_power(fft_freq, fft_mag, 0, 10),
        '10-20 Hz (low EMG)': band_power(fft_freq, fft_mag, 10, 20),
        '20-100 Hz (main EMG)': band_power(fft_freq, fft_mag, 20, 100),
        '100-128 Hz (high EMG)': band_power(fft_freq, fft_mag, 100, 128)
    }

    # Convert to percentages
    band_percentages = {k: (v/total_power)*100 for k, v in bands.items()}

    # Find peak frequency
    peak_idx = np.argmax(fft_mag)
    peak_freq = fft_freq[peak_idx]

    return {
        'fft_freq': fft_freq,
        'fft_mag': fft_mag,
        'band_percentages': band_percentages,
        'peak_freq': peak_freq
    }


def create_analysis_plot(specs, freq_analysis, output_path):
    """Create comprehensive analysis plot."""
    fig = plt.figure(figsize=(16, 12))

    channels = ['CHIN', 'RLEG', 'LLEG']
    colors = {'CHIN': 'blue', 'RLEG': 'red', 'LLEG': 'green'}

    for idx, ch_name in enumerate(channels):
        if specs['channels'][ch_name] is None:
            continue

        ch_data = specs['channels'][ch_name]
        signal = ch_data['signal']
        fs = ch_data['sample_freq']

        # Row 1: Time domain (first 30 seconds)
        ax1 = plt.subplot(4, 3, idx + 1)
        time_samples = int(30 * fs)  # 30 seconds
        time_axis = np.arange(time_samples) / fs
        ax1.plot(time_axis, signal[:time_samples], color=colors[ch_name], linewidth=0.5)
        ax1.set_title(f'{ch_name} - First 30s (Wake Period)', fontweight='bold')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel(f'Amplitude ({ch_data["physical_dim"]})')
        ax1.grid(True, alpha=0.3)

        # Row 2: Frequency spectrum
        ax2 = plt.subplot(4, 3, idx + 4)
        freq_data = freq_analysis[ch_name]
        ax2.semilogy(freq_data['fft_freq'][:1000], freq_data['fft_mag'][:1000],
                     color=colors[ch_name], linewidth=0.5)
        ax2.axvline(60, color='red', linestyle='--', alpha=0.5, label='60 Hz')
        ax2.set_title(f'{ch_name} - Frequency Spectrum', fontweight='bold')
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Magnitude (log scale)')
        ax2.set_xlim([0, 128])
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # Row 3: Frequency band distribution
        ax3 = plt.subplot(4, 3, idx + 7)
        bands = freq_data['band_percentages']
        band_names = list(bands.keys())
        band_values = list(bands.values())
        bars = ax3.bar(range(len(bands)), band_values, color=colors[ch_name], alpha=0.7)
        ax3.set_title(f'{ch_name} - Frequency Band Distribution', fontweight='bold')
        ax3.set_ylabel('Power (%)')
        ax3.set_xticks(range(len(bands)))
        ax3.set_xticklabels([b.split()[0] for b in band_names], rotation=45, ha='right')
        ax3.grid(True, alpha=0.3, axis='y')

        # Add percentage labels on bars
        for bar, val in zip(bars, band_values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=8)

        # Row 4: Statistics table
        ax4 = plt.subplot(4, 3, idx + 10)
        ax4.axis('off')

        stats = ch_data['stats']
        stats_text = f"""
        Statistics for {ch_name} EMG:

        Mean:        {stats['mean']:>10.2f} {ch_data['physical_dim']}
        Std Dev:     {stats['std']:>10.2f} {ch_data['physical_dim']}
        RMS:         {stats['rms']:>10.2f} {ch_data['physical_dim']}
        Min:         {stats['min']:>10.2f} {ch_data['physical_dim']}
        Max:         {stats['max']:>10.2f} {ch_data['physical_dim']}
        Range:       {stats['range']:>10.2f} {ch_data['physical_dim']}

        Sampling:    {fs} Hz
        Peak Freq:   {freq_data['peak_freq']:.1f} Hz
        """

        ax4.text(0.1, 0.5, stats_text, transform=ax4.transAxes,
                fontfamily='monospace', fontsize=9, verticalalignment='center')

    plt.suptitle(f'EMG Signal Analysis: {specs["file"]}',
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")
    plt.close()


def print_specs_report(specs):
    """Print detailed specifications report."""
    print(f"\n{'='*70}")
    print("EDF FILE SPECIFICATIONS")
    print(f"{'='*70}\n")

    print(f"File: {specs['file']}")
    print(f"Duration: {specs['duration_hours']:.2f} hours")
    print(f"Start time: {specs['start_datetime']}")
    print()

    for ch_name in ['CHIN', 'RLEG', 'LLEG']:
        if specs['channels'][ch_name] is None:
            continue

        ch = specs['channels'][ch_name]
        print(f"\n{'-'*70}")
        print(f"{ch_name} EMG (Channel {ch['index']}): {ch['label']}")
        print(f"{'-'*70}")
        print(f"  Sampling Rate:      {ch['sample_freq']} Hz")
        print(f"  Physical Dimension: {ch['physical_dim']}")
        print(f"  Physical Min:       {ch['physical_min']:.2f} {ch['physical_dim']}")
        print(f"  Physical Max:       {ch['physical_max']:.2f} {ch['physical_dim']}")
        print(f"  Digital Min:        {ch['digital_min']}")
        print(f"  Digital Max:        {ch['digital_max']}")
        print(f"  Prefiltering:       {ch['prefilter'] if ch['prefilter'] else 'None'}")
        print(f"  Transducer:         {ch['transducer'] if ch['transducer'] else 'Not specified'}")
        print()
        print("  Signal Statistics:")
        stats = ch['stats']
        print(f"    Mean:     {stats['mean']:>10.2f} {ch['physical_dim']}")
        print(f"    Std Dev:  {stats['std']:>10.2f} {ch['physical_dim']}")
        print(f"    RMS:      {stats['rms']:>10.2f} {ch['physical_dim']}")
        print(f"    Range:    {stats['range']:>10.2f} {ch['physical_dim']}")


def print_frequency_report(freq_analysis):
    """Print frequency analysis report."""
    print(f"\n{'='*70}")
    print("FREQUENCY CONTENT ANALYSIS")
    print(f"{'='*70}\n")

    for ch_name in ['CHIN', 'RLEG', 'LLEG']:
        if ch_name not in freq_analysis:
            continue

        freq = freq_analysis[ch_name]
        print(f"\n{ch_name} EMG:")
        print(f"  Peak Frequency: {freq['peak_freq']:.1f} Hz")
        print(f"  Power Distribution:")

        for band, percentage in freq['band_percentages'].items():
            bar_length = int(percentage / 2)  # Scale for display
            bar = '█' * bar_length
            print(f"    {band:25s} {percentage:5.1f}% {bar}")


def main():
    """Main analysis function."""
    # File paths
    workspace = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
    clinical_db = workspace / "Clinical_DB"
    log_dir = workspace / "SW" / "log"
    plots_dir = log_dir / "plots"

    # Files to analyze
    edf_files = [
        clinical_db / "Test1.EDF",
        clinical_db / "Test2.EDF"
    ]

    # Analyze each file
    for edf_path in edf_files:
        if not edf_path.exists():
            print(f"Error: File not found: {edf_path}")
            continue

        # Extract specifications
        specs = extract_edf_specs(str(edf_path))

        # Analyze frequency content
        freq_analysis = {}
        for ch_name in ['CHIN', 'RLEG', 'LLEG']:
            if specs['channels'][ch_name] is not None:
                ch_data = specs['channels'][ch_name]
                freq_analysis[ch_name] = analyze_frequency_content(
                    ch_data['signal'],
                    ch_data['sample_freq'],
                    ch_name
                )

        # Print reports
        print_specs_report(specs)
        print_frequency_report(freq_analysis)

        # Create plot
        plot_path = plots_dir / f"{edf_path.stem}_raw_signal_analysis.png"
        create_analysis_plot(specs, freq_analysis, str(plot_path))

        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
