# ✅ 완전한 솔루션: Standard EDF → RBDtector 분석 가능

**날짜**: 2025-11-20
**상태**: ✅ 완료
**목표**: PS0140-PS0151 데이터를 RBDtector로 분석 가능하게 만들기

---

## 요약

`convert_test8_to_continuous.py`의 로직을 활용하여 **완전한 변환 시스템** 구축 완료!

**핵심**: convert_excel_annotations.py는 annotation만 변환했지만, 이제 **EDF 파일도 변환**하여 RBDtector가 사용 가능한 형태로 만듦

---

## 문제 발견

### convert_excel_annotations.py의 한계

**기존 상태**:
```
✅ Annotation 변환 (Excel → txt 파일)
  - Sleep profile.txt
  - Classification Arousals.txt
  - Flow Events.txt

❌ EDF 파일 변환 없음
  - PS0140.EDF는 여전히 pyedflib가 읽을 수 없음
  - RBDtector 실행 불가능!
```

**비교**:

| 변환기 | Annotation | EDF 파일 | RBDtector 가능 |
|-------|-----------|---------|---------------|
| convert_edf_annotations.py | ✅ EDF→txt | ❌ 불필요 (이미 호환) | ✅ Yes |
| convert_test8_to_continuous.py | ❌ 불필요 | ✅ **EDF+D→EDF+C** | ✅ Yes |
| convert_excel_annotations.py (구) | ✅ Excel→txt | ❌ **없음!** | ❌ **No** |

---

## 해결 방안

### convert_test8_to_continuous.py 로직 활용

**convert_test8_to_continuous.py의 핵심 처리**:
1. mne-python으로 읽기 (pyedflib 우회)
2. 신호 데이터 변환 (V → µV)
3. Physical ranges 재계산
4. pyedflib로 EDF+C 쓰기

**이 방법을 PS0140에도 적용!**

---

## 구현 내용

### 1. convert_standard_to_edfplus.py (신규 작성)

**기능**: Standard EDF → EDF+C 변환

**처리 과정**:
```python
# Step 1: mne-python으로 읽기
raw = mne.io.read_raw_edf(input_edf, preload=True)

# Step 2: 단위 변환 (EMG/EEG channels)
data[i] = data[i] * 1e6  # V → µV

# Step 3: Physical ranges 계산
p1 = np.percentile(ch_data, 1)
p99 = np.percentile(ch_data, 99)
physical_min = p1 * 1.2
physical_max = p99 * 1.2

# Step 4: pyedflib로 EDF+C 쓰기
f = pyedflib.EdfWriter(output_edf, file_type=FILETYPE_EDFPLUS)
f.setSignalHeaders(signal_headers)
f.writePhysicalSamples(record_data)
```

**입력**: PS0140_211029.EDF (pyedflib 불가)
**출력**: PS0140_211029_edfplus.edf (pyedflib 가능!)

---

### 2. auto_convert.py 업데이트

**변경 사항**: Standard EDF 처리 로직 확장

**Before**:
```python
# Standard EDF + Excel
→ convert_excel_annotations.py만 실행
→ Annotation 파일만 생성
→ EDF 파일 그대로 (RBDtector 불가!)
```

**After**:
```python
# Standard EDF + Excel
→ [Step 1/2] convert_standard_to_edfplus.py 실행
    → EDF+C 파일 생성 (pyedflib 호환)
→ [Step 2/2] convert_excel_annotations.py 실행
    → Annotation 파일 생성
→ RBDtector 실행 가능!
```

---

## 검증 결과

### PS0140 변환 테스트

**실행**:
```bash
python3 auto_convert.py PS0140_211029.EDF
```

**출력**:
```
Processing: PS0140_211029.EDF

[1/3] Detecting EDF format...
  ✓ Type: Standard
  ✓ Excel file: PS0140_211029.xlsx
  ✓ EMG channels: Chin1-Chin2, Lat, Rat

[2/3] Running converter...
  → Using: convert_excel_annotations.py + convert_standard_to_edfplus.py

  [Step 1/2] Converting EDF to EDF+C (pyedflib compatible)...
    Duration: 8.69 hours
    Sampling frequency: 200.0 Hz
    EMG channels: 3
    Writing 31284 data records...
    ✓ EDF+C file created: PS0140_211029_edfplus.edf

  [Step 2/2] Converting annotations from Excel...
    ✓ Sleep Profile: 170 stages
    ✓ Arousals: 183 events
    ✓ Flow Events: 121 events

[3/3] Results:
  ✓ Conversion successful!
```

**생성된 파일**:
```
PS0140_211029_edfplus.edf              242 MB  ← pyedflib 호환 EDF+C
PS0140_211029 Sleep profile.txt        3.3 KB
PS0140_211029 Classification Arousals.txt  9.6 KB
PS0140_211029 Flow Events.txt          6.0 KB
```

---

### EDF+C 검증

**pyedflib로 읽기 테스트**:
```python
import pyedflib

f = pyedflib.EdfReader('PS0140_211029_edfplus.edf')

print(f'Duration: {f.getFileDuration()} seconds')
print(f'Signals: {f.signals_in_file}')
print(f'Start time: {f.getStartdatetime()}')

# EMG channels
for i in [8, 9, 10]:
    label = f.getLabel(i)
    fs = f.getSampleFrequency(i)
    print(f'{i}: {label} @ {fs} Hz')
```

**결과**:
```
Duration: 31284.0 seconds (8.69 hours)
Signals: 20
Start time: 2021-10-29 22:06:29

8: Chin1-Chin2 @ 200.0 Hz  ✓
9: Lat @ 200.0 Hz  ✓
10: Rat @ 200.0 Hz  ✓
```

✅ **완벽하게 pyedflib로 읽을 수 있음!**

---

## 기존 변환기 vs 신규 변환기 비교

### convert_test8_to_continuous.py (참고)

**입력**: Test8.edf (EDF+D, pyedflib 가능하지만 discontinuous)
**출력**: Test8.edf (EDF+C, continuous)

**처리**:
- mne으로 읽기 ✅
- V → µV 변환 ✅
- Physical ranges 계산 ✅
- pyedflib로 쓰기 ✅

**용도**: Discontinuous → Continuous

---

### convert_standard_to_edfplus.py (신규)

**입력**: PS0140.EDF (Standard, pyedflib 불가)
**출력**: PS0140_edfplus.edf (EDF+C, pyedflib 가능)

**처리**:
- mne으로 읽기 ✅ (동일 로직)
- V → µV 변환 ✅ (동일 로직)
- Physical ranges 계산 ✅ (동일 로직)
- pyedflib로 쓰기 ✅ (동일 로직)

**용도**: Non-compliant Standard → Compliant EDF+C

---

## 완전한 데이터 처리 흐름

### PS0140 데이터 (Standard EDF + Excel)

```
원본 파일:
  PS0140_211029.EDF      (239 MB, pyedflib 불가)
  PS0140_211029.xlsx     (43 KB)

↓ auto_convert.py 실행

Step 1: EDF 변환
  mne으로 읽기
  V → µV 변환
  Physical ranges 재계산
  pyedflib로 EDF+C 쓰기
  ↓
  PS0140_211029_edfplus.edf  (242 MB, pyedflib 가능!)

Step 2: Annotation 변환
  Excel 읽기
  Sleep stages, Arousals, Flow events 추출
  RBDtector 형식으로 저장
  ↓
  PS0140_211029 Sleep profile.txt
  PS0140_211029 Classification Arousals.txt
  PS0140_211029 Flow Events.txt

↓ RBDtector 실행 준비 완료!

RBDtector 입력:
  - PS0140_211029_edfplus.edf  ← 변환된 EDF+C
  - PS0140_211029 Sleep profile.txt
  - PS0140_211029 Classification Arousals.txt
  - PS0140_211029 Flow Events.txt

✓ 모든 파일이 RBDtector 호환 형식!
```

---

## 파일 구조 비교

### Test1 (EDF+C)

```
Test1.EDF (이미 pyedflib 호환)
  ↓
  convert_edf_annotations.py
  ↓
  Test1 Sleep profile.txt
  Test1 Classification Arousals.txt
  Test1 Flow Events.txt

RBDtector 입력:
  - Test1.EDF (원본 그대로)
  - annotation 파일들
```

### PS0140 (Standard + Excel)

```
PS0140_211029.EDF (pyedflib 불가!)
PS0140_211029.xlsx
  ↓
  auto_convert.py
    ├─ convert_standard_to_edfplus.py
    └─ convert_excel_annotations.py
  ↓
  PS0140_211029_edfplus.edf (변환됨!)
  PS0140_211029 Sleep profile.txt
  PS0140_211029 Classification Arousals.txt
  PS0140_211029 Flow Events.txt

RBDtector 입력:
  - PS0140_211029_edfplus.edf (변환된 파일)
  - annotation 파일들
```

---

## 주요 차이점 정리

### Annotation 변환

**Test1-10**:
- EDF 내부 annotations → txt 파일

**PS0140-PS0151**:
- Excel → txt 파일

**→ 동일한 형식으로 변환됨** ✅

---

### EDF 파일 처리

**Test1-10**:
- EDF 변환 불필요
- 원본 그대로 사용

**PS0140-PS0151**:
- ❌ EDF 변환 필요!
- Standard EDF → EDF+C
- mne + pyedflib 활용

**→ `convert_test8_to_continuous.py` 로직 활용** ✅

---

## 다음 단계

### 1. RBDtector 설정

**PS0140-PS0151용 채널 설정**:
```python
# settings.py 또는 run script
SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
CHIN = 0
LEGS = [1, 2]
RATE = 256  # 또는 200?
```

**주의**: Sampling rate가 200 Hz인데 RBDtector는 256 Hz 가정
- Resampling 필요한지 확인
- 또는 RATE 설정 조정

---

### 2. RBDtector 실행

```bash
# 방법 1: 수동 실행
cd RBDtector
python3 -m RBDtector.main \
  --input /path/to/PS0140_211029_edfplus.edf \
  --output /path/to/results/

# 방법 2: run_baseline_test.py 수정
# PS0140용 채널 설정 추가
python3 run_baseline_test.py PS0140
```

---

### 3. 검증

**비교 항목**:
- Test1 (EDF+C, 256 Hz) vs PS0140 (Standard→EDF+C, 200 Hz)
- Artifact-free REM %
- Baseline EMG 값
- RBD 이벤트 수

---

## 작성된 파일

### 신규 코드

```
SW/code/
├── convert_standard_to_edfplus.py  (NEW!)
│     - Standard EDF → EDF+C 변환
│     - convert_test8 로직 기반
│     - 독립 실행 가능
│
├── auto_convert.py  (UPDATED!)
│     - Standard EDF 처리 로직 확장
│     - 2단계 변환 (EDF + Annotation)
│     - 완전한 RBDtector 준비
│
└── convert_excel_annotations.py
      - 변경 없음
      - annotation 변환만 담당
```

### 로그 문서

```
SW/log/
├── 251120_data_structure_comparison.md
│     - 데이터 구조 차이 분석
│
├── 251120_conversion_system_complete.md
│     - Annotation 변환 시스템 (불완전)
│
├── 251120_critical_issue_edf_reading.md
│     - EDF 읽기 문제 발견
│
└── 251120_complete_solution.md  (THIS FILE)
      - 완전한 솔루션
```

---

## 결론

### 달성한 목표

✅ **PS0140 EDF를 RBDtector가 사용 가능한 형태로 변환**
- Standard EDF → EDF+C (pyedflib 호환)
- Excel → annotation 파일

✅ **convert_test8_to_continuous.py 로직 활용**
- 동일한 변환 방식 적용
- mne-python + pyedflib

✅ **auto_convert.py 통합**
- 2단계 자동 변환
- 단일 명령으로 모든 파일 생성

✅ **완전한 데이터 준비**
- EDF+C 파일: ✅
- Sleep profile: ✅
- Arousals: ✅
- Flow events: ✅

---

### 핵심 차이

| 항목 | 이전 (불완전) | 현재 (완전) |
|------|------------|-----------|
| **Annotation** | ✅ Excel → txt | ✅ Excel → txt |
| **EDF 파일** | ❌ 변환 없음 | ✅ **Standard → EDF+C** |
| **RBDtector** | ❌ 실행 불가 | ✅ **실행 가능** |
| **참조 로직** | - | ✅ **convert_test8** |

---

### 사용자가 해야 할 일

1. **채널 설정 확인**:
   - SIGNALS_TO_EVALUATE
   - CHIN, LEGS 인덱스

2. **Sampling rate 확인**:
   - PS0140은 200 Hz
   - RBDtector는 256 Hz 가정
   - Resample 필요한지 확인

3. **RBDtector 실행**:
   - `_edfplus.edf` 파일 사용
   - annotation 파일들과 함께

---

**작성일**: 2025-11-20
**상태**: ✅ 완전한 솔루션 구축 완료
**다음 작업**: RBDtector 실행 및 결과 검증
