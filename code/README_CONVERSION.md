# EDF Annotation 변환 시스템

**작성일**: 2025-11-20
**목적**: 다양한 EDF 형식을 RBDtector 분석에 필요한 annotation 파일로 자동 변환

---

## 개요

이 시스템은 3가지 다른 EDF 형식을 자동으로 감지하고 적절한 변환기를 적용합니다:

1. **EDF+C** (Annotations 내장) - Test1-10
2. **EDF+D** (Discontinuous) - Test8 등
3. **Standard EDF + Excel** (Annotations 외부) - PS0140-PS0151

---

## 파일 구조

```
SW/code/
├── auto_convert.py                    # 통합 변환 스크립트 (메인)
├── detect_edf_format.py               # EDF 형식 자동 감지
├── convert_edf_annotations.py         # EDF+C 전용 변환기
├── convert_excel_annotations.py       # Standard EDF + Excel 변환기
└── convert_test8_to_continuous.py     # EDF+D → EDF+C 변환기
```

**코드 독립성**:
- 각 변환기는 완전히 독립적으로 실행 가능
- 공통 함수 없음 (코드 혼선 방지)
- `auto_convert.py`는 subprocess로 변환기 실행 (메모리 격리)

---

## 사용법

### 1. 자동 변환 (권장)

**단일 파일 변환**:
```bash
cd /Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index/SW/code
python3 auto_convert.py <EDF_PATH>
```

**예시**:
```bash
# EDF+C 형식 (Test1-10)
python3 auto_convert.py ../Clinical_DB/Test1.EDF

# Standard EDF + Excel (PS0140-PS0151)
python3 auto_convert.py ../Clinical_DB/additional/PS0140_211029.EDF
```

**디렉토리 전체 변환**:
```bash
python3 auto_convert.py <DIRECTORY>
```

**예시**:
```bash
# additional 폴더의 모든 EDF 파일 변환
python3 auto_convert.py ../Clinical_DB/additional/
```

---

### 2. 형식 감지만 하기

```bash
python3 detect_edf_format.py <EDF_PATH>
```

**출력 예시**:
```
============================================================
EDF Format Detection Result
============================================================
Type: Standard
pyedflib compatible: ✗ No
Has annotations: ✗ No
Excel file: ✓ Found (PS0140_211029.xlsx)
Number of signals: 20
EMG channels found: 3
  [8] Chin1-Chin2
  [9] Lat
  [10] Rat

Recommended converter:
  → convert_excel_annotations.py (Excel annotations)
============================================================
```

---

### 3. 수동 변환 (특정 변환기 직접 실행)

**EDF+C 형식 (annotations 내장)**:
```bash
python3 convert_edf_annotations.py <EDF_PATH>
```

**Standard EDF + Excel**:
```bash
python3 convert_excel_annotations.py <EDF_PATH> [EXCEL_PATH]
```

Excel 파일 경로를 지정하지 않으면 자동으로 같은 이름의 .xlsx 파일을 찾습니다.

**EDF+D → EDF+C 변환**:
```bash
python3 convert_test8_to_continuous.py
```
(현재 Test8 전용, 경로가 하드코딩되어 있음)

---

## 출력 파일

모든 변환기는 EDF 파일과 같은 디렉토리에 3개의 파일을 생성합니다:

1. **`<BASENAME> Sleep profile.txt`**
   - 수면 단계 (W, N1, N2, N3, REM)
   - 30초 epoch 단위

2. **`<BASENAME> Classification Arousals.txt`**
   - Arousal 이벤트
   - onset-end 시간, duration, 유형

3. **`<BASENAME> Flow Events.txt`**
   - 호흡 이벤트 (Apnea, Hypopnea, Desaturation)
   - onset-end 시간, duration, 유형

---

## EDF 형식별 처리 방식

### 1. EDF+C (Test1-10)

**특징**:
- Annotations이 EDF 파일 내부에 저장
- pyedflib로 읽기 가능
- 마이크로초 정밀도 타임스탬프

**변환기**: `convert_edf_annotations.py`

**처리 과정**:
1. pyedflib로 EDF 읽기
2. Annotations 추출
3. Sleep stages, Arousals, Flow events 분류
4. RBDtector 형식으로 저장

**주의사항**:
- 타임스탬프를 초 단위로 반올림 (pandas resample 정렬 문제 방지)
- 첫 번째 sleep stage 시간을 effective start time으로 사용

---

### 2. Standard EDF + Excel (PS0140-PS0151)

**특징**:
- EDF 파일에는 신호만 저장
- Annotations는 별도 Excel 파일 (.xlsx)
- pyedflib 읽기 실패 (Physical Dimension 오류)
- 100분의 1초 정밀도 타임스탬프

**변환기**: `convert_excel_annotations.py`

**처리 과정**:
1. EDF 헤더에서 시작 시간 읽기 (수동 파싱)
2. Excel Sheet1에서 annotations 읽기
3. "Stage -", "Arousal -", "Respiratory Event" 필터링
4. Duration 파싱 및 end time 계산
5. RBDtector 형식으로 저장

**Excel 데이터 구조**:
```
Column 0: NaN
Column 1: Epoch 번호
Column 2: 타임스탬프 (HH:MM:SS.ff)
Column 3: 이벤트 설명
```

**이벤트 유형**:
- `Stage - W/N1/N2/N3/REM`
- `Arousal - Dur: X.X sec. - Type`
- `Respiratory Event - Dur: X.X sec. - Type`

---

### 3. EDF+D (Test8)

**특징**:
- Discontinuous EDF (데이터 기록 중단 구간 존재)
- pyedflib 읽기 가능하지만 RBDtector는 continuous 필요

**변환기**: `convert_test8_to_continuous.py`

**처리 과정**:
1. mne-python으로 EDF+D 읽기
2. Continuous EDF+C로 변환 (pyedflib로 저장)
3. `convert_edf_annotations.py`로 annotations 추출

**주의사항**:
- 현재 Test8 전용 (경로 하드코딩)
- 다른 EDF+D 파일은 스크립트 수정 필요

---

## 실행 예시

### 예시 1: Test1 변환 (EDF+C)

```bash
$ python3 auto_convert.py ../Clinical_DB/Test1.EDF

============================================================
Processing: Test1.EDF
============================================================

[1/3] Detecting EDF format...
  ✓ Type: EDF+C
  ✓ EMG channels: EMG CHIN1-CHINz, EMG RLEG+, EMG LLEG+

[2/3] Running converter...
  → Using: convert_edf_annotations.py

[3/3] Results:
  ✓ Conversion successful!

  Output files:
    → Test1 Sleep profile.txt
    → Test1 Classification Arousals.txt
    → Test1 Flow Events.txt
```

---

### 예시 2: PS0140 변환 (Standard + Excel)

```bash
$ python3 auto_convert.py ../Clinical_DB/additional/PS0140_211029.EDF

============================================================
Processing: PS0140_211029.EDF
============================================================

[1/3] Detecting EDF format...
  ✓ Type: Standard
  ✓ Excel file: PS0140_211029.xlsx
  ✓ EMG channels: Chin1-Chin2, Lat, Rat

[2/3] Running converter...
  → Using: convert_excel_annotations.py

  ✓ Sleep Profile: 170 stages → PS0140_211029 Sleep profile.txt
  ✓ Arousals: 183 events → PS0140_211029 Classification Arousals.txt
  ✓ Flow Events: 121 events → PS0140_211029 Flow Events.txt

[3/3] Results:
  ✓ Conversion successful!

  Output files:
    → PS0140_211029 Sleep profile.txt
    → PS0140_211029 Classification Arousals.txt
    → PS0140_211029 Flow Events.txt
```

---

### 예시 3: 배치 변환

```bash
$ python3 auto_convert.py ../Clinical_DB/additional/

============================================================
Batch Conversion: 2 files
============================================================

[1/2] PS0140_211029.EDF
------------------------------------------------------------
  ✓ Success (convert_excel_annotations.py)

[2/2] PS0141_211030.EDF
------------------------------------------------------------
  ✓ Success (convert_excel_annotations.py)

============================================================
Batch Conversion Summary
============================================================
Total files: 2
Successful: 2
Failed: 0
```

---

## 출력 파일 형식

### 1. Sleep Profile

```
Start Time: 29.10.2021 22:06:29
Version: 1.0

22:44:29,000000; W
22:59:59,000000; N1
23:00:29,000000; W
23:00:59,000000; N1
23:02:59,000000; N2
...
```

### 2. Classification Arousals

```
Signal ID: Arousals
Start Time: 29.10.2021 22:06:29
Unit: s
Signal Type: Impuls

23:00:33,230000-23:00:52,830000; 19.60; Spontaneous
23:01:32,700000-23:01:40,500000; 7.80; Respiratory Event
23:02:00,980000-23:02:08,880000; 7.90; Spontaneous
...
```

### 3. Flow Events

```
Signal ID: Flow Events
Start Time: 29.10.2021 22:06:29
Unit: s
Signal Type: Impuls

23:05:12,960000-23:05:42,960000; 30.00; Hypopnea
23:05:59,920000-23:06:27,320000; 27.40; Hypopnea
...
```

---

## 문제 해결

### pyedflib 오류 발생 시

**증상**:
```
OSError: the file is not EDF(+) or BDF(+) compliant (Physical Dimension)
```

**해결**:
- Standard EDF 형식입니다
- Excel 파일이 필요합니다
- `auto_convert.py`가 자동으로 감지하고 적절한 변환기 사용

---

### Excel 파일을 찾을 수 없음

**증상**:
```
Error: Excel file not found
```

**해결**:
1. EDF 파일과 같은 폴더에 `.xlsx` 파일이 있는지 확인
2. 파일명이 일치하는지 확인 (예: `PS0140_211029.EDF` → `PS0140_211029.xlsx`)
3. 수동으로 Excel 경로 지정:
   ```bash
   python3 convert_excel_annotations.py PS0140.EDF PS0140.xlsx
   ```

---

### 타임스탬프 정렬 문제

**증상**:
- RBDtector에서 0% artifact-free REM
- pandas resample 오류

**원인**:
- 마이크로초 정밀도 타임스탬프가 resample 경계와 불일치

**해결**:
- `convert_edf_annotations.py`는 자동으로 초 단위로 반올림
- RBDtector의 `PSG.py`에 `origin=idx[0]` 추가 필요

---

## 개발 노트

### 코드 분리 원칙

각 변환기는 완전히 독립적:
- 공통 함수 없음
- 각자 독립적으로 import
- subprocess로 실행 (메모리 격리)

이유:
- 코드 혼선 방지
- 한 변환기의 버그가 다른 변환기에 영향 없음
- 각 변환기를 개별적으로 테스트/유지보수 가능

---

### 타임스탬프 정밀도

| EDF 형식 | 정밀도 | 예시 |
|---------|-------|------|
| EDF+C (Test1-10) | 마이크로초 (6자리) | `21:40:02.025781` |
| Standard (PS0140) | 100분의 1초 (2자리) | `22:06:29.00` |

RBDtector는 마이크로초 정밀도를 지원하지만, pandas resample 정렬 문제로 인해 초 단위 반올림 권장.

---

### EMG 채널 매핑

| 데이터셋 | Chin | Left Leg | Right Leg |
|---------|------|----------|-----------|
| Test1-10 | `EMG CHIN1-CHINz` | `EMG LLEG+` | `EMG RLEG+` |
| PS0140-PS0151 | `Chin1-Chin2` | `Lat` | `Rat` |

RBDtector 설정 시 적절한 채널 인덱스 지정 필요.

---

## 다음 단계

변환 후 RBDtector 분석 실행:

```bash
# RBDtector 설정 확인
# - SIGNALS_TO_EVALUATE: EMG 채널명
# - CHIN, LEGS 인덱스

# 분석 실행 (기존 파이프라인)
python3 run_baseline_test.py PS0140
```

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-20
**관련 문서**: `251120_data_structure_comparison.md`
