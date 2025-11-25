# RBDtector Execution Guide for Preprocessed Files

**Date**: 2025-11-24
**Purpose**: Manual RBDtector execution instructions for preprocessed datasets
**Status**: Preprocessing complete, ready for RBDtector analysis

---

## ⚠️ Important Notice

RBDtector uses a **GUI interface** and does not support command-line batch processing. All 14 preprocessed files must be analyzed manually through the RBDtector GUI.

**Estimated Time**: 60-120 minutes (depending on file size and REM duration)

---

## 📁 Files Ready for Analysis

### Test1-10 (Preprocessed)

All files located in: `Results/raw/Test*/`

| Test | Preprocessed EDF | Sleep Profile | Status |
|------|------------------|---------------|--------|
| Test1 | Test1_preprocessed.edf | Sleep profile - test1.txt | ✅ Ready |
| Test2 | Test2_preprocessed.edf | Sleep profile - test2.txt | ✅ Ready |
| Test3 | Test3_preprocessed.edf | Sleep profile - test3.txt | ✅ Ready |
| Test4 | Test4_preprocessed.edf | Sleep profile - test4.txt | ✅ Ready |
| Test5 | Test5_preprocessed.edf | Sleep profile - test5.txt | ✅ Ready |
| Test6 | Test6_preprocessed.edf | Sleep profile - test6.txt | ✅ Ready |
| Test7 | Test7_preprocessed.edf | Sleep profile - test7.txt | ✅ Ready |
| Test8 | Test8_preprocessed.edf | Sleep profile - test8.txt | ✅ Ready |
| Test9 | Test9_preprocessed.edf | Sleep profile - test9.txt | ✅ Ready |
| Test10 | Test10_preprocessed.edf | Sleep profile - test10.txt | ✅ Ready |

### PS0140-151 (Fixed + Preprocessed)

All files located in: `Results/raw/PS*/`

| Patient | Preprocessed EDF | Sleep Profile | Status |
|---------|------------------|---------------|--------|
| PS0140_211029 | PS0140_211029_preprocessed.edf | PS0140_211029 Sleep profile.txt | ✅ Ready |
| PS0141_211030 | PS0141_211030_preprocessed.edf | PS0141_211030 Sleep profile.txt | ✅ Ready |
| PS0150_221111 | PS0150_221111_preprocessed.edf | PS0150_221111 Sleep profile.txt | ✅ Ready |
| PS0151_221112 | PS0151_221112_preprocessed.edf | PS0151_221112 Sleep profile.txt | ✅ Ready |

---

## 🚀 Execution Steps

### Step 1: Launch RBDtector

```bash
cd SW/RBDtector
python RBDtector/main.py
```

### Step 2: Configure Channel Settings

**For Test1-10:**
```
SIGNALS_TO_EVALUATE = ['EMG CHIN1-CHINz', 'EMG RLEG+', 'EMG LLEG+']
CHIN = 0
LEGS = [1, 2]
ARMS = []
```

**For PS0140-151:**
```
SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
CHIN = 0
LEGS = [1, 2]
ARMS = []
```

### Step 3: Process Each File

For each of the 14 files:

1. **Load Files:**
   - EDF file: `{test}_preprocessed.edf`
   - Sleep profile: `{test} Sleep profile.txt`
   - Arousal/Flow files: Load if available

2. **Verify Settings:**
   - Check channel detection is correct
   - Verify REM periods are identified
   - Ensure artifact-free REM ≥150 seconds

3. **Run Analysis:**
   - Click "Run RBDtector"
   - Wait for completion (~5-10 minutes per file)

4. **Save Results:**
   - Output directory: `Results/raw/{test}/RBDtector output_preprocessed/`
   - Excel file: `RBDtector_results_YYYY-MM-DD_HH-MM-SS.xlsx`

5. **Verify Output:**
   - Check Excel file contains all fields
   - Verify EMG CHIN*_any_%, *_tonic_%, *_phasic_%
   - Confirm baseline amplitude is calculated

---

## 📊 Expected Results

### Test1-10 (After Preprocessing)

**Baseline Changes:**
- **Before**: ~21 µV (original, with DC component)
- **After**: ~5-10 µV (DC removed, true EMG baseline)
- **Change**: 50-70% reduction

**RSWA Changes:**
- High-pass filtering improves phasic burst detection
- Slight increase in RSWA % expected (better sensitivity)
- Tonic/Phasic ratio may shift slightly

### PS0140-151 (After Physical Range Fix + Preprocessing)

**Baseline Changes:**
- **Before**: ~1.46 µV (clipped, artificially low)
- **After**: ~5-10 µV (clipping removed, true baseline)
- **Change**: 3-7x increase

**RSWA Changes:**
- Large EMG bursts (>12 µV) now detected (were clipped before)
- **Significant increase in RSWA % expected**
- More accurate RBD diagnosis possible

---

## ✅ Validation Criteria

After running RBDtector on all 14 files, verify:

### 1. File Completeness
```bash
# Check all results exist
ls Results/raw/Test*/RBDtector*output_preprocessed/RBDtector_results*.xlsx
ls Results/raw/PS*/RBDtector*output_preprocessed/RBDtector_results*.xlsx
```

Expected: 14 Excel files (10 Test + 4 PS)

### 2. Artifact-Free REM
All files should have:
- Artifact-free REM ≥150 seconds (RBDtector requirement)
- Artifact-free REM % ≥30% (typical for good quality data)

### 3. Baseline Values
All CHIN baselines should be:
- Between 1-50 µV (normal REM atonia range)
- Test1-10: ~5-10 µV (after preprocessing)
- PS0140-151: ~5-10 µV (after unclipping)
- **Similar ranges** (fair comparison achieved!)

### 4. RSWA Components
All files should have:
- Tonic % ≥0 and ≤100
- Phasic % ≥0 and ≤100
- Any % ≥0 and ≤100
- Any % = max(Tonic %, Phasic %) approximately

---

## 📈 Post-RBDtector Analysis

After all 14 files are processed, run data extraction:

### Extract Baseline Amplitudes

```bash
# Test1-10
python3 SW/code/generate_results_generic.py \
  --input "Results/raw/Test*/RBDtector*output_preprocessed/RBDtector_results*.xlsx" \
  --output Results/Test1-10_Preprocessed_Baselines.csv

# PS0140-151
python3 SW/code/generate_results_generic.py \
  --input "Results/raw/PS*/RBDtector*output_preprocessed/RBDtector_results*.xlsx" \
  --output Results/PS0140-151_Preprocessed_Baselines.csv
```

### Extract Complete RSWA Data

```bash
# Modify extract_complete_rswa_data.py to use preprocessed results
# Then run:
python3 SW/code/extract_complete_rswa_data.py --all
```

This will generate:
- `Results/Test1-10_RSWA_Preprocessed.csv`
- `Results/PS0140-151_RSWA_Preprocessed.csv`

---

## 📊 Comparison Analysis

After data extraction, compare:

### Baseline Comparison

| Dataset | Original (µV) | Preprocessed (µV) | Change |
|---------|---------------|-------------------|--------|
| Test1-10 | ~21 | ~5-10 | -50 to -70% |
| PS0140-151 | ~1.46 | ~5-10 | +300 to +700% |

### RSWA Diagnostic Status

Compare diagnostic calls before/after preprocessing:

```bash
# Using Montreal cutoff: CHIN Any ≥24.0%
# Check how many change diagnostic status (Normal ↔ RSWA+)
```

---

## ⚠️ Common Issues

### Issue 1: Channel Names Not Detected

**Symptom**: RBDtector doesn't recognize EMG channels

**Solution**:
- Manually configure `config.ini` in RBDtector directory
- Add channel names exactly as they appear in EDF file
- Restart RBDtector

### Issue 2: Insufficient REM Sleep

**Symptom**: "Artifact-free REM <150s" error

**Cause**: File has too little REM or too many artifacts

**Solution**:
- Check sleep profile annotation quality
- Verify REM periods are marked correctly
- Accept limitation (some patients have limited REM)

### Issue 3: Baseline Calculation Fails

**Symptom**: Baseline shows as NaN or 0

**Cause**: Insufficient continuous REM periods

**Solution**:
- Check for continuous REM segments ≥150s
- Verify signal quality during REM
- May need to adjust artifact thresholds

---

## 📝 Output Files Expected

After completion, each test should have:

```
Results/raw/Test1/
├── Test1_preprocessed.edf
├── Test1_preprocessing_report.json
├── Sleep profile - test1.txt
└── RBDtector output_preprocessed/
    ├── RBDtector_results_2025-11-24_XX-XX-XX.xlsx
    ├── graphs/
    ├── indices/
    └── report/
```

---

## 🎯 Next Steps After RBDtector Execution

1. **Data Extraction**: Run extraction scripts (baselines + RSWA)
2. **Comparative Analysis**: Compare original vs preprocessed results
3. **Report Generation**: Generate final markdown + PDF reports
4. **Clinical Validation**: Review with clinical team

---

## 📚 References

1. **RBDtector Documentation**: SW/RBDtector/README.md
2. **Preprocessing Plan**: SW/log/241124_preprocessing_unification_plan.md
3. **Execution Progress**: SW/log/241124_execution_progress.md
4. **SINBAR Method**: Frauscher et al., 2012
5. **Montreal Validation**: Joza et al., 2025

---

**Author**: Preprocessing Pipeline
**Last Updated**: 2025-11-24
**Status**: Ready for manual RBDtector execution
