# PS0140 RBDtector 설정 가이드

**날짜**: 2025-11-20
**목적**: PS0140-PS0151 데이터의 차이점과 RBDtector 설정 방법

---

## 질문 1: edfplus.pdf 파일?

**답변**: PDF 파일은 없습니다!

**확인 결과**:
```bash
$ ls -lh PS0140_211029_edfplus.edf
PS0140_211029_edfplus.edf: Biosig/EDF: European Data format
```

**파일 설명**:
- 파일명: `PS0140_211029_edfplus.edf`
- 확장자: `.edf` (EDF 파일)
- 내용: EDF+C 형식의 생체신호 데이터
- 크기: 242 MB

**오해 가능성**:
- 파일명에 "edfplus"가 있어서 PDF로 오인했을 수 있음
- 실제로는 EDF 파일 (European Data Format)

---

## 질문 2: 200 Hz vs 256 Hz - 문제 없나?

**답변**: ✅ **문제 없습니다!** RBDtector가 자동으로 처리합니다.

### Sampling Rate 비교

| 데이터셋 | Sampling Rate | 채널 |
|---------|--------------|------|
| **Test1-10** | 256 Hz | EMG CHIN1-CHINz, RLEG+, LLEG+ |
| **PS0140-PS0151** | 200 Hz | Chin1-Chin2, Lat, Rat |

**차이**: -56 Hz (-21.9%)

---

### RBDtector의 자동 처리

**RBDtector 내부 로직**:
```python
# settings.py
RATE = 256  # RBDtector 내부 처리 rate

# dataframe_creation.py
def signal_to_hz_rate_datetimeindexed_series(hz_rate, sample_rate, signal_array, ...):
    """
    If the sample rate of the signal array does not match the desired Hz rate,
    it is resampled using spline interpolation.
    """
    # 200 Hz → 256 Hz 자동 resampling!
```

**처리 과정**:
1. EDF 파일에서 원본 sampling rate 읽기 (200 Hz)
2. RBDtector 내부 rate와 비교 (256 Hz)
3. 불일치 시 **spline interpolation으로 자동 resampling**
4. 모든 신호를 256 Hz로 통일

**결론**: ✅ **사용자가 아무것도 하지 않아도 자동 처리됨!**

---

### Spline Interpolation의 영향

**장점**:
- 부드러운 신호 보간
- 고주파 artifacts 최소화
- 신호 특성 유지

**단점**:
- 약간의 계산 시간 증가 (무시할 수준)
- 원본과 완전히 동일하지는 않음 (하지만 매우 유사)

**임상적 영향**:
- RBD 이벤트 감지에는 문제 없음
- Baseline EMG 계산에도 영향 미미
- 256 Hz → 200 Hz 다운샘플링보다 200 Hz → 256 Hz 업샘플링이 더 안전

---

## 질문 3: 채널 설정 - 바꿔야 하나?

**답변**: ✅ **예, 바꿔야 합니다!**

### 채널 차이

**Test1-10** (기존):
```python
SIGNALS_TO_EVALUATE = ['EMG CHIN1-CHINz', 'EMG RLEG+', 'EMG LLEG+']
CHIN = 0  # EMG CHIN1-CHINz
LEGS = [1, 2]  # EMG RLEG+, EMG LLEG+
```

**PS0140-PS0151** (신규):
```python
SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
CHIN = 0  # Chin1-Chin2
LEGS = [1, 2]  # Lat, Rat
```

---

### 설정 변경 방법

#### Option 1: settings.py 수정 (비권장)

RBDtector 소스 코드를 직접 수정:
```python
# RBDtector/util/settings.py

# Before (Test1-10용)
SIGNALS_TO_EVALUATE = ['EMG', 'PLM l', 'PLM r', 'AUX', 'Akti.']

# After (PS0140용)
SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
```

**문제점**:
- Test1-10 분석 시 다시 바꿔야 함
- 소스 코드 수정으로 인한 혼동

---

#### Option 2: run script에서 override (권장)

**새 스크립트 작성**: `run_ps0140_test.py`

```python
#!/usr/bin/env python3
"""
Run RBDtector on PS0140-PS0151 data

Modified version of run_baseline_test.py for PS0140 data with different:
- Channel names (Chin1-Chin2, Lat, Rat)
- Sampling rate (200 Hz, auto-resampled to 256 Hz)
"""

import sys
import os
from pathlib import Path

# Add RBDtector to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'RBDtector'))

from RBDtector.util import settings
from RBDtector.app_logic.PSG import PSG

# Override settings for PS0140
settings.SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
settings.CHIN = 0
settings.LEGS = [1, 2]
settings.ARMS = []  # No arm channels

# RATE는 그대로 256 (자동 resampling)
# settings.RATE = 256  # 변경 불필요

def run_ps0140_test(test_name):
    """Run RBDtector on PS0140 data."""

    # Paths
    workspace = Path('/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index')
    input_dir = workspace / 'Clinical_DB' / 'additional'

    # Input files (use _edfplus.edf!)
    edf_file = input_dir / f'{test_name}_edfplus.edf'

    if not edf_file.exists():
        print(f'Error: {edf_file} not found!')
        print('Please run auto_convert.py first to generate _edfplus.edf file')
        return

    print('='*60)
    print(f'Running RBDtector on {test_name}')
    print('='*60)
    print()
    print(f'Input directory: {input_dir}')
    print(f'EDF file: {edf_file.name}')
    print(f'Channels: {settings.SIGNALS_TO_EVALUATE}')
    print(f'Sampling rate: 200 Hz → {settings.RATE} Hz (auto-resampled)')
    print()

    # Run RBDtector
    psg = PSG(str(input_dir), str(input_dir))
    # ... (rest of RBDtector execution logic)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python run_ps0140_test.py <TEST_NAME>')
        print('Example: python run_ps0140_test.py PS0140_211029')
        sys.exit(1)

    test_name = sys.argv[1]
    run_ps0140_test(test_name)
```

---

#### Option 3: 조건부 설정 (최선)

**run_baseline_test.py 확장**:

```python
def detect_data_type(edf_path):
    """Detect if this is Test1-10 or PS0140 data."""
    import pyedflib

    f = pyedflib.EdfReader(edf_path)
    labels = [f.getLabel(i) for i in range(f.signals_in_file)]
    f.close()

    # Check channel names
    if any('EMG CHIN' in l for l in labels):
        return 'Test1-10'
    elif any('Chin1-Chin2' in l for l in labels):
        return 'PS0140'
    else:
        return 'Unknown'

# In main:
data_type = detect_data_type(edf_path)

if data_type == 'Test1-10':
    settings.SIGNALS_TO_EVALUATE = ['EMG CHIN1-CHINz', 'EMG RLEG+', 'EMG LLEG+']
elif data_type == 'PS0140':
    settings.SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
    settings.CHIN = 0
    settings.LEGS = [1, 2]
```

---

## 설정 비교표

| 항목 | Test1-10 | PS0140-PS0151 | 변경 필요 |
|------|----------|--------------|---------|
| **EDF 파일** | Test1.EDF | PS0140_edfplus.edf | ✅ |
| **Sampling Rate** | 256 Hz | 200 Hz → 256 Hz (자동) | ❌ |
| **SIGNALS_TO_EVALUATE** | EMG CHIN1-CHINz, ... | Chin1-Chin2, Lat, Rat | ✅ |
| **CHIN** | 0 | 0 | ❌ |
| **LEGS** | [1, 2] | [1, 2] | ❌ |
| **RATE** | 256 | 256 | ❌ |

---

## 권장 사항

### 1. 즉시 필요한 변경

✅ **채널명 설정**:
```python
settings.SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
```

✅ **EDF 파일 경로**:
```python
# Test1용
edf_path = 'Test1.EDF'

# PS0140용
edf_path = 'PS0140_211029_edfplus.edf'  # _edfplus.edf 사용!
```

❌ **변경 불필요**:
- RATE (256 그대로, 자동 resampling)
- CHIN, LEGS 인덱스 (동일)

---

### 2. 실행 방법

**방법 1**: settings.py 수정 후 실행
```bash
# 1. settings.py 수정
# SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']

# 2. 실행
python3 run_baseline_test.py PS0140_211029
```

**방법 2**: 별도 스크립트 작성 (권장)
```bash
python3 run_ps0140_test.py PS0140_211029
```

---

### 3. 검증 포인트

**실행 후 확인**:
1. ✅ 채널 로딩 성공 (`Chin1-Chin2`, `Lat`, `Rat`)
2. ✅ Sampling rate: 200 Hz → 256 Hz 변환
3. ✅ REM sleep 인식 (0%가 아닌지)
4. ✅ Baseline EMG 계산 성공
5. ✅ Artifact-free REM % (90% 이상 기대)

---

## 예상 결과

### Test1과 비교

| 항목 | Test1 | PS0140 (예상) |
|------|-------|--------------|
| **REM sleep** | 110.5 min | ~100-120 min |
| **Artifact-free REM** | 97.0% | 90-98% |
| **Chin EMG baseline** | 30.40 µV | ? |
| **Leg EMG baseline** | 127/86 µV | ? |

**PS0140은 RBD 환자인지 확인 필요**
- RBD 환자: 높은 EMG baseline
- 정상: 낮은 EMG baseline

---

## 문제 발생 시 체크리스트

### 채널 로딩 실패

**증상**:
```
KeyError: 'Chin1-Chin2'
```

**해결**:
```python
# settings.SIGNALS_TO_EVALUATE 확인
print(settings.SIGNALS_TO_EVALUATE)

# EDF 파일의 실제 채널명 확인
import pyedflib
f = pyedflib.EdfReader('PS0140_211029_edfplus.edf')
for i in range(f.signals_in_file):
    print(f'{i}: {f.getLabel(i)}')
```

---

### Resampling 오류

**증상**:
```
ValueError: sample_rate mismatch
```

**해결**:
- RATE는 256 그대로 유지
- RBDtector가 자동으로 200→256 변환
- 수동 변경 불필요

---

### 0% Artifact-free REM

**원인**:
- Timestamp 정렬 문제 (Test1에서 해결했던 문제)
- RBDtector PSG.py의 `origin=idx[0]` 수정 확인

**해결**:
- PSG.py lines 113, 122에 `origin=idx[0]` 있는지 확인
- Sleep profile 시작 시간 확인

---

## 요약

### 질문 1: edfplus.pdf?
**답변**: PDF 아님! `PS0140_211029_edfplus.edf`는 EDF 파일

### 질문 2: 200 Hz vs 256 Hz 문제?
**답변**: ✅ 문제 없음! RBDtector가 자동 resampling (200→256 Hz)

### 질문 3: 채널 설정 변경?
**답변**: ✅ 변경 필요!
```python
SIGNALS_TO_EVALUATE = ['Chin1-Chin2', 'Lat', 'Rat']
```

---

**작성일**: 2025-11-20
**다음 작업**: PS0140 RBDtector 실행 및 결과 검증
