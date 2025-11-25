
import pyedflib
import numpy as np

def inspect_edf(file_path):
    try:
        f = pyedflib.EdfReader(file_path)
        
        print("EDF File Information:")
        print("=====================")
        
        # Print general header information
        print(f"Start Date: {f.getStartdatetime()}")
        header = f.getHeader()
        print(f"Patient Info: {header.get('patientname', 'N/A')}")
        print(f"Recording Info: {header.get('recording_additional', 'N/A')}")
        print(f"Admin Code: {header.get('admincode', 'N/A')}")
        print(f"Technician: {header.get('technician', 'N/A')}")
        print(f"Number of signals: {f.signals_in_file}")
        print(f"File duration (seconds): {f.file_duration}")
        
        print("\nSignal Headers:")
        print("===============")
        signal_labels = f.getSignalLabels()
        for i in range(f.signals_in_file):
            print(f"  - Signal {i}:")
            print(f"    Label: {signal_labels[i]}")
            print(f"    Dimension: {f.getPhysicalDimension(i)}")
            print(f"    Sample Frequency: {f.getSampleFrequency(i)}")
            print(f"    Physical Min/Max: {f.getPhysicalMinimum(i)} / {f.getPhysicalMaximum(i)}")
            print(f"    Digital Min/Max: {f.getDigitalMinimum(i)} / {f.getDigitalMaximum(i)}")
            print(f"    Transducer: {f.getTransducer(i)}")
            print(f"    Prefilter: {f.getPrefilter(i)}")

        print("\nAnnotations in file:")
        print("======================")
        annotations = f.readAnnotations()
        if annotations[0].size > 0:
            for n in np.arange(annotations[0].size):
                print(f"- Onset: {annotations[0][n]}s, Duration: {annotations[1][n]}s, Event: {annotations[2][n]}")
        else:
            print("No annotations found in the file.")

        f.close()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    edf_file = "/Users/hyeongsuk/Desktop/workspace/SNUH/SAI/clinical_db/Test1.EDF"
    inspect_edf(edf_file)
