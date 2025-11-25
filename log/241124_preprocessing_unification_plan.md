# 전처리 통일화 계획 / Preprocessing Unification Plan

**날짜**: 2025-11-24
**목적**: Test1-10과 PS0140-151 데이터를 동일한 전처리 조건으로 재처리하여 공정한 비교 가능하게 만들기
**상태**: 계획 수립 완료, 실행 준비 중

---

## 📋 문제 상황 / Problem Statement

### 발견된 문제

1. **PS0140-151 Physical Range Clipping**
   - Physical range: -12 to 12 µV (너무 좁음)
   - Actual data: -12.00 to 12.00 µV (clipping 발생)
   - Clipped samples: 33,425개 (0.534%)
   - 큰 EMG burst(>12 µV)가 모두 손실됨

2. **전처리 불일치**
   - Test1-10: Preprocessing 없음 (원본 그대로)
   - PS0140-151: Preprocessing 있음 (High-pass, Low-pass, Notch filter)
   - 비교 불가능한 상태

3. **Baseline 차이**
   - Test1-10 CHIN: 평균 21.0 µV
   - PS0140-151 CHIN: 평균 1.46 µV
   - **14배 차이** → Preprocessing 차이 + Clipping 때문

---

## 🎯 해결 방안 / Solution

### Option 1 선택: 모든 데이터에 동일한 전처리 적용

**근거:**
- AASM 권장: EMG signal preprocessing (10-100 Hz bandpass)
- DC/Low-frequency drift 제거
- 60 Hz power line interference 제거
- 공정한 비교 가능

---

## 🔧 적용할 전처리 / Preprocessing Specifications

### Filter Parameters (preprocess_emg.py)

**CHIN EMG:**
```
High-pass filter: 10 Hz (Butterworth 4th order)
Low-pass filter: 100 Hz
Notch filter: 60 Hz (Q=30)
Method: Zero-phase filtering (scipy.signal.filtfilt)
```

**LEG EMG (Lat, Rat, RLEG, LLEG):**
```
High-pass filter: 15 Hz (Butterworth 4th order)
Low-pass filter: 100 Hz
Notch filter: 60 Hz (Q=30)
Method: Zero-phase filtering (scipy.signal.filtfilt)
```

### Physical Range Policy

**모든 파일:**
- Physical range: **원본 데이터 전체 범위 + 100% margin**
- Clipping 방지
- RSWA 신호 보존

---

## 📝 실행 계획 / Execution Plan

### Phase 1: Test1-10 Preprocessing (10 files)

**대상 파일:**
```
Clinical_DB/Test1.EDF → Results/raw/Test1/Test1_preprocessed.edf
Clinical_DB/Test2.EDF → Results/raw/Test2/Test2_preprocessed.edf
Clinical_DB/Test3.EDF → Results/raw/Test3/Test3_preprocessed.edf
Clinical_DB/Test4.EDF → Results/raw/Test4/Test4_preprocessed.edf
Clinical_DB/Test5.EDF → Results/raw/Test5/Test5_preprocessed.edf
Clinical_DB/Test6.EDF → Results/raw/Test6/Test6_preprocessed.edf
Clinical_DB/Test7.EDF → Results/raw/Test7/Test7_preprocessed.edf
Clinical_DB/Test8.EDF → Results/raw/Test8/Test8_preprocessed.edf
Clinical_DB/Test9.EDF → Results/raw/Test9/Test9_preprocessed.edf
Clinical_DB/Test10.EDF → Results/raw/Test10/Test10_preprocessed.edf
```

**실행 명령:**
```bash
for i in {1..10}; do
  python3 SW/code/preprocess_emg.py Test$i
done
```

**예상 결과:**
- DC/Low-freq power: 감소 (예: 3.6% → 0.2%)
- EMG band power: 증가 (예: 82.8% → 87.0%)
- 60 Hz noise: 감소 (예: 0.75% → 0.18%)

---

### Phase 2: PS0140-151 재변환 및 전처리 (4 files)

**Step 2.1: Physical Range 수정**

`convert_standard_to_edfplus.py` 수정:
```python
# 기존 (99th percentile - 문제 있음):
p1 = np.percentile(ch_data, 1)
p99 = np.percentile(ch_data, 99)
physical_min = p1 * 1.2
physical_max = p99 * 1.2

# 수정 (전체 범위 - clipping 방지):
abs_max = max(abs(ch_data.min()), abs(ch_data.max()))
physical_max = abs_max * 2.0  # 100% margin
physical_min = -physical_max

# 최소 범위 보장 (AASM 권장):
if abs(physical_max) < 500.0:  # µV
    physical_max = 500.0
    physical_min = -500.0
```

**Step 2.2: 재변환**
```bash
python3 SW/code/convert_standard_to_edfplus.py Clinical_DB/additional/PS0140_211029.EDF
python3 SW/code/convert_standard_to_edfplus.py Clinical_DB/additional/PS0141_211110.EDF
python3 SW/code/convert_standard_to_edfplus.py Clinical_DB/additional/PS0150_220425.EDF
python3 SW/code/convert_standard_to_edfplus.py Clinical_DB/additional/PS0151_221121.EDF
```

**Step 2.3: Preprocessing**
```bash
python3 SW/code/preprocess_emg.py PS0140_211029
python3 SW/code/preprocess_emg.py PS0141_211110
python3 SW/code/preprocess_emg.py PS0150_220425
python3 SW/code/preprocess_emg.py PS0151_221121
```

---

### Phase 3: RBDtector 재실행 (14 files)

**Test1-10:**
```bash
for i in {1..10}; do
  # RBDtector input: Test${i}_preprocessed.edf
  python3 SW/code/run_baseline_test.py Test${i} --preprocessed
done
```

**PS0140-151:**
```bash
for ps in PS0140_211029 PS0141_211110 PS0150_220425 PS0151_221121; do
  # RBDtector input: ${ps}_preprocessed.edf
  python3 SW/code/run_baseline_test.py ${ps} --preprocessed
done
```

**RBDtector Configuration:**
- Test1-10: CHIN + 2 LEGS (RLEG, LLEG)
- PS0140-151: CHIN + 2 LEGS (Lat, Rat)
- Sampling rate: 256 Hz (Test1-10), 200 Hz (PS0140-151)
- Artifact removal: 자동 (RBDtector 내장)

---

### Phase 4: 데이터 추출 및 분석

**4.1 True Baseline Amplitudes 계산**
```bash
# Test1-10
python3 SW/code/generate_results_generic.py \
  --input Results/raw/Test{1..10}/RBDtector*/RBDtector_results*.xlsx \
  --output Results/Test1-10_True_Baseline_Amplitudes_Preprocessed.csv

# PS0140-151
python3 SW/code/generate_ps_report.py \
  --output Results/PS0140-151_True_Baseline_Amplitudes_Preprocessed.csv
```

**4.2 Complete RSWA Data 추출**
```bash
# Tonic, Phasic, Any percentages
python3 SW/code/extract_complete_rswa_data.py --all
```

---

### Phase 5: 통합 보고서 생성

**5.1 Markdown Report**
```bash
python3 SW/code/generate_unified_report_markdown.py
# Output: Results/Unified_RBD_Analysis_Report_Preprocessed.md
```

**5.2 PDF Report**
```bash
python3 SW/code/generate_unified_report_pdf.py
# Output: Results/Unified_RBD_Analysis_Report_Preprocessed.pdf
```

**보고서 내용:**
1. Executive Summary
2. Preprocessing Specifications
3. Test1-10 Results (CHIN only)
4. PS0140-151 Results (CHIN only)
5. Comparative Analysis
6. RSWA Diagnostic Criteria
7. Clinical Interpretation Guide
8. Appendix: Technical Details

---

## 📊 예상 결과 / Expected Outcomes

### Baseline 변화 예상

**Test1-10 (preprocessing 후):**
- 현재: 평균 21.0 µV (원본)
- 예상: **5-10 µV** (DC 제거 후)
- 변화: **50-70% 감소**

**PS0140-151 (physical range 수정 후):**
- 현재: 평균 1.46 µV (clipped)
- 예상: **5-10 µV** (clipping 해제 후)
- 변화: **3-7배 증가**

**최종 비교:**
- Test1-10 vs PS0140-151: **유사한 범위** (5-10 µV)
- 차이: 환자 특성, 전극 impedance, RBD 중증도
- 공정한 비교 가능 ✓

---

### RSWA 진단 결과 변화 예상

**Test1-10:**
- High-pass filter → Baseline 낮아짐
- Phasic burst detection 개선 (DC noise 제거)
- RSWA % 약간 증가 가능

**PS0140-151:**
- Physical range 확장 → 큰 burst 복구
- RSWA % 크게 증가 예상
- 정확한 RBD 진단 가능

---

## ✅ 검증 기준 / Validation Criteria

### 1. Physical Range 검증
```python
# 모든 파일이 만족해야 함:
assert physical_max >= 500 µV  # AASM 권장 최소값
assert actual_data.max() < physical_max * 0.95  # No clipping
assert actual_data.min() > physical_min * 0.95  # No clipping
```

### 2. Preprocessing 검증
```python
# Before/After 비교:
assert after['dc_low'] < before['dc_low'] * 0.1  # DC 90% 감소
assert after['emg_band'] > before['emg_band'] * 1.05  # EMG 5% 증가
assert after['hz_60'] < before['hz_60'] * 0.3  # 60Hz 70% 감소
```

### 3. RBDtector 실행 검증
```python
# 모든 파일이 생성되어야 함:
assert RBDtector_results_*.xlsx exists
assert artifact_free_REM > 0%
assert baseline_calculated == True
```

### 4. Baseline 범위 검증
```python
# 정상 범위 확인:
assert 1 < CHIN_baseline < 50 µV  # 정상 REM EMG 범위
assert Test1_10_baseline ~ PS0140_baseline  # 유사한 범위
```

---

## 📁 생성될 파일 / Output Files

### Preprocessed EDF Files (14 files)
```
Results/raw/Test1/Test1_preprocessed.edf
Results/raw/Test2/Test2_preprocessed.edf
...
Results/raw/Test10/Test10_preprocessed.edf
Results/raw/PS0140_211029/PS0140_211029_preprocessed.edf
Results/raw/PS0141_211110/PS0141_211110_preprocessed.edf
Results/raw/PS0150_220425/PS0150_220425_preprocessed.edf
Results/raw/PS0151_221121/PS0151_221121_preprocessed.edf
```

### RBDtector Results (14 files)
```
Results/raw/Test*/RBDtector output/RBDtector_results_*.xlsx
Results/raw/PS0*/RBDtector output/RBDtector_results_*.xlsx
```

### Data Analysis CSV (4 files)
```
Results/Test1-10_True_Baseline_Amplitudes_Preprocessed.csv
Results/Test1-10_RSWA_Complete_Preprocessed.csv
Results/PS0140-151_True_Baseline_Amplitudes_Preprocessed.csv
Results/PS0140-151_RSWA_Complete_Preprocessed.csv
```

### Final Reports (2 files)
```
Results/Unified_RBD_Analysis_Report_Preprocessed.md
Results/Unified_RBD_Analysis_Report_Preprocessed.pdf
```

### Logs (1 file)
```
SW/log/241124_preprocessing_execution_log.md  (실행 후 생성)
```

---

## ⏱️ 예상 소요 시간 / Estimated Timeline

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1 | Test1-10 preprocessing (10 files) | 30-60 min |
| Phase 2 | PS0140-151 재변환 + preprocessing (4 files) | 20-40 min |
| Phase 3 | RBDtector 재실행 (14 files) | 60-120 min |
| Phase 4 | 데이터 추출 및 분석 | 10-20 min |
| Phase 5 | 보고서 생성 (MD + PDF) | 10-20 min |
| **Total** | | **2-4 hours** |

---

## ⚠️ 주의사항 / Important Notes

### 1. 원본 데이터 보존
- 원본 EDF 파일은 그대로 유지
- 새로운 `_preprocessed.edf` 파일 생성
- 기존 결과는 백업 (Results/archive/)

### 2. Sampling Rate 차이
- Test1-10: 256 Hz
- PS0140-151: 200 Hz
- RBDtector가 자동으로 resampling하는지 확인 필요

### 3. 전처리 일관성
- 모든 파일에 정확히 동일한 filter 적용
- Filter parameters 변경 금지
- Preprocessing report 모두 저장

### 4. 보고서 검증
- Baseline 값이 정상 범위(1-50 µV)인지 확인
- Test1-10 vs PS0140-151 비교 가능한지 확인
- 상사에게 제출 전 반드시 검토

---

## 📚 참고 문헌 / References

1. **AASM Scoring Manual**
   - EMG Technical Specifications
   - High-pass filter: 10 Hz recommended
   - Input range: ±50 mV minimum

2. **preprocess_emg.py Documentation**
   - Filter parameters: Line 34-48
   - Evidence-based from signal analysis (251105_02)

3. **RBDtector Paper (Röthenbacher et al., 2022)**
   - SINBAR method
   - Artifact-free REM requirement: ≥150s

4. **Montreal Validation (Joza et al., 2025)**
   - CHIN Any ≥24.0% cutoff
   - Sensitivity 89.8%, Specificity 97.3%

---

**작성자**: Claude Code
**검토 필요**: 실행 전 사용자 최종 승인
**실행 상태**: 계획 완료, 실행 대기 중
