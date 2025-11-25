# RBDtector Clinical Data Bug - Root Cause & Solution

**Date**: 2025-11-06
**Status**: ✅ RESOLVED

---

## Executive Summary

Successfully identified and fixed a critical bug in RBDtector that caused **0% artifact-free REM detection** with clinical data containing microsecond-precision timestamps. After fix, Test1 now shows **97.0% artifact-free REM**, matching expected clinical values.

---

## Problem Statement

### Initial Symptoms
- **Tutorial data**: 97.6% artifact-free REM ✅ (works perfectly)
- **Test1 clinical data**: 0% artifact-free REM ❌ (complete failure)
- Baseline calculation impossible without artifact-free REM

### Clinical Context
Test1 is a clinical RBD patient from SNUH, expected to have:
- ~20-25% REM sleep (measured: 22.8% ✅)
- High arousal rate during REM due to RBD pathology
- BUT still should have some artifact-free REM periods for baseline calculation

---

## Root Cause Analysis

### Investigation Journey

**Phase 1**: Signal Amplitude Hypothesis ❌
- Initially suspected MIN_BASELINE_VOLTAGE threshold (0.05 µV)
- Analysis showed: Tutorial 2.20 µV, Test1 28.20 µV (both pass) ✅
- **Conclusion**: Signal amplitude is NOT the issue

**Phase 2**: Arousal File Format ❌
- Noticed format differences between Tutorial and Test1
- Fixed format to match exactly (headers, spaces, duration field)
- **Result**: Still 0% artifact-free REM

**Phase 3**: Timestamp Alignment ⚠️
- Discovered 3-minute calibration period in Test1 EDF (21:40:02 → 21:43:02)
- Fixed annotation files to use first sleep stage as start time
- **Result**: Alignment improved, but still 0%

**Phase 4**: Deep Dive into pandas Behavior 🎯
- Created debug script to trace RBDtector's calculation step-by-step
- **DISCOVERED**: pandas `resample()` without `origin` parameter causes index mismatch!

---

## The Bug

### Location
File: `RBDtector/app_logic/PSG.py`
Function: `find_artifact_free_REM_sleep_epochs_and_miniepochs()`
Lines: 110-113, 119-122

### Bug Description

**Original Code**:
```python
artifact_in_3s_miniepoch = artifact_signal_series \
    .resample('3s') \
    .sum() \
    .gt(0)
```

**The Problem Chain**:

1. **Signal Index Creation**:
   - RBDtector reads EDF header start time: `2024-08-11 21:43:02.025781`
   - Creates DatetimeIndex at 256 Hz: `21:43:01.998437250, 21:43:02.002343500, ...`
   - Each sample is 3.90625 ms apart (1000/256)
   - **Result**: Nanosecond-precision timestamps

2. **Resample Without Origin**:
   - `artifact_signal_series.resample('3s')` with no `origin` parameter
   - pandas defaults to aligning on epoch 1970-01-01 00:00:00
   - Resampled index: `21:43:00, 21:43:03, 21:43:06, ...` (clean 3s boundaries)
   - **Result**: Resampled timestamps DON'T match signal timestamps

3. **Index Mismatch on Assignment**:
   ```python
   df['miniepoch_contains_artifact'] = artifact_in_3s_miniepoch
   ```
   - pandas tries to align indices
   - Signal index: `21:43:01.998437250, 21:43:02.002343500, ...`
   - Resampled index: `21:43:00, 21:43:03, 21:43:06, ...`
   - NO timestamps match!
   - **Result**: ALL 7,441,921 values become NaN

4. **NaN → True Conversion**:
   ```python
   df['miniepoch_contains_artifact'].ffill().astype(bool)
   ```
   - `ffill()` has nothing to fill → remains NaN
   - `astype(bool)` converts NaN to **True** (!!)
   - **Result**: ALL samples marked as "miniepoch contains artifact"

5. **Final Calculation**:
   ```python
   df['artifact_free_rem_sleep_miniepoch'] = is_REM_series & ~df['miniepoch_contains_artifact']
   ```
   - `~df['miniepoch_contains_artifact']` = all False
   - REM & False = 0 artifact-free REM samples

### Why Tutorial Worked
- Tutorial start time: `01:00:00` (no microseconds!)
- Signal index: `01:00:00.000000000, 01:00:00.003906250, ...`
- Resampled index: `01:00:00, 01:00:03, 01:00:06, ...`
- First timestamp matches perfectly: `01:00:00` ✅
- Subsequent timestamps align well enough due to clean start time

---

## The Fix

### Code Changes

**File**: `RBDtector/app_logic/PSG.py`
**Lines Modified**: 113-114, 122-123

**Fixed Code**:
```python
# BUGFIX: Add origin=idx[0] to align resampled timestamps with signal index
artifact_in_3s_miniepoch = artifact_signal_series \
    .resample('3s', origin=idx[0]) \
    .sum() \
    .gt(0)

# Same fix for 30s epochs
artifact_in_30s_epoch = artifact_signal_series \
    .resample('30s', origin=idx[0]) \
    .sum() \
    .gt(0)
```

**Explanation**:
- `origin=idx[0]` tells pandas to align resampling boundaries to the signal start time
- This ensures resampled timestamps match the signal index timestamps
- Identical approach already used for sleep profile alignment (line 464)

---

## Verification Results

### Before Fix
```
Total REM Samples:              1,697,280
Global Artifact-Free REM:       0
Artifact-Free %:                0.0%
```

### After Fix
```
Total REM Samples:              1,697,280
Global Artifact-Free REM:       1,645,820
Artifact-Free %:                97.0%  ✅
```

### Manual Verification
- Sample-level calculation: 97.8% artifact-free ✅
- Miniepoch-level (3s windows): 96.7% artifact-free ✅
- RBDtector calculation: 97.0% artifact-free ✅
- **All methods now agree!**

---

## Clinical Interpretation

### Test1 Patient (Clinical RBD)
- **Total REM**: 110.5 minutes (22.8% of sleep)
- **Artifacts**: 22.9 minutes (4.7% of sleep)
- **REM with artifacts**: 2.2% (20 arousal events in REM)
- **Artifact-free REM**: 97.0%

This is **excellent** for a clinical RBD patient:
- RBD patients have increased motor activity during REM
- High arousal rate is expected
- 97% artifact-free REM is sufficient for baseline EMG analysis
- Baseline calculation can now proceed ✅

---

## Impact on Other Files

### Files Modified

1. **`convert_edf_annotations.py`**:
   - Added timestamp rounding to seconds (lines 38-40, 69-70)
   - Added first-sleep-stage alignment (lines 53-70)
   - **Note**: Rounding didn't fix the bug, but improves compatibility

2. **`RBDtector/app_logic/PSG.py`**:
   - Added `origin=idx[0]` to resample calls (lines 114, 123)
   - **Critical fix** - resolves the bug

### Test Files Created (for debugging)
- `test_arousal_fix.py` - Verification script
- `debug_arousal_loading.py` - Arousal data inspection
- `detailed_artifact_analysis.py` - Deep dive analysis
- `debug_ffill_issue.py` - pandas behavior investigation

---

## Next Steps

### Immediate
1. ✅ Apply fix to RBDtector
2. ✅ Verify Test1 works correctly
3. ⏳ Run full RBDtector pipeline on Test1
4. ⏳ Calculate Atonia Index for Test1

### Future Work
1. Test remaining clinical files (Test2-Test10)
2. Compare with Tutorial results
3. Validate clinical RBD detection accuracy
4. Consider submitting bugfix to RBDtector upstream

---

## Lessons Learned

### Technical Insights

1. **pandas resample() behavior**:
   - Default origin is epoch 1970-01-01
   - Always use `origin` parameter when resampling time series data
   - Especially critical with microsecond-precision timestamps

2. **NaN coercion**:
   - `pd.Series([np.nan]).astype(bool)` returns `[True]`
   - Silent data corruption with boolean conversion
   - Always check for NaN before type conversion

3. **Clinical data differences**:
   - Lab data (Tutorial): clean timestamps, controlled conditions
   - Clinical data (Test1): microsecond precision, calibration periods
   - Software must handle real-world timestamp precision

### Debugging Process

1. **Systematic elimination**: Test each hypothesis rigorously
2. **Trace calculations step-by-step**: Create debug scripts at each stage
3. **Compare working vs broken**: Tutorial vs Test1 comparison was key
4. **Read source code**: Found the fix by examining working code (sleep profile)

---

## Files Reference

### Modified Files
- `/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/SW/code/convert_edf_annotations.py`
- `/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/SW/RBDtector/RBDtector/app_logic/PSG.py`

### Generated Data
- `/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/Results/raw/Test1/Test1 Sleep profile.txt`
- `/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/Results/raw/Test1/Test1 Classification Arousals.txt`
- `/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/Results/raw/Test1/Test1 Flow Events.txt`

### Log Files
- `SW/log/251106_06_source_code_investigation.md` - MIN_BASELINE_VOLTAGE analysis
- `SW/log/251106_07_final_solution.md` - This document

---

## Conclusion

The bug was a subtle interaction between:
1. Microsecond-precision EDF timestamps (real clinical data)
2. pandas resample() default behavior (epoch alignment)
3. Silent NaN→True coercion in boolean conversion

The fix is simple (add `origin` parameter) but the discovery required deep investigation. This demonstrates the importance of rigorous testing with clinical data that may have different characteristics than lab/tutorial data.

**Status**: ✅ **RESOLVED**
**Test1 Atonia Index calculation**: Ready to proceed
