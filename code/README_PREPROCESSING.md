# EMG 신호 전처리 가이드 (초보자용)

**작성일**: 2025-11-21
**대상**: EMG 신호 처리 초보자
**목적**: RBDtector 분석을 위한 EMG 신호 전처리 이해하기

---

## 1. 전처리가 뭔가요? 🤔

**전처리 (Preprocessing)** = 원본 신호에서 잡음을 제거하는 과정

### 비유로 이해하기

라디오 주파수를 맞추는 것과 비슷합니다:
- 원본 녹음: 여러 라디오 방송이 섞여서 들림 (잡음 포함)
- 전처리: 원하는 방송 주파수만 골라서 들음 (잡음 제거)

### EMG 신호에서는?

```
원본 EMG 신호 = 진짜 근육 신호 + 잡음들

잡음 종류:
1. DC 오프셋 (전극의 일정한 전압)
2. 저주파 드리프트 (천천히 변하는 기준선)
3. 60 Hz 잡음 (전원선에서 나오는 간섭)
4. 고주파 잡음 (전자 장비 노이즈)
```

**전처리 목표**: 잡음은 버리고 진짜 근육 신호(20-100 Hz)만 남기기!

---

## 2. 왜 전처리가 필요한가요? 🎯

### 문제 상황

전처리 없이 RBDtector를 돌리면:
```
❌ 결과: Artifact-free REM = 0%
→ 모든 신호가 "잡음"으로 판정
→ RBD 분석 불가능
```

### 전처리 후

```
✅ 결과: Artifact-free REM = 97%
→ 깨끗한 신호 확보
→ RBD 분석 가능
```

### 왜 이런 차이가?

원본 신호에 있는 DC 오프셋과 저주파 드리프트가 너무 커서:
- RBDtector가 "신호가 이상하다"고 판단
- 모든 구간을 artifact(잡음)로 분류

---

## 3. 전처리는 무엇을 하나요? 🔧

### 3단계 필터링 과정

```
원본 신호
    ↓
[1단계] High-pass Filter (고역통과 필터)
    → DC와 저주파 잡음 제거
    ↓
[2단계] Low-pass Filter (저역통과 필터)
    → 고주파 잡음 제거
    ↓
[3단계] Notch Filter (대역 제거 필터)
    → 60 Hz 전원선 잡음 제거
    ↓
깨끗한 EMG 신호 (20-100 Hz만 남음)
```

---

## 4. 각 필터를 쉽게 이해하기 📊

### (1) High-pass Filter - "낮은 주파수는 통과시키지 않아!"

**목적**: DC 오프셋과 저주파 드리프트 제거

**비유**:
- 고음만 들리게 하는 이어폰
- 저음은 차단, 고음은 통과

**설정**:
```python
CHIN: 10 Hz 이상만 통과  (10 Hz 미만 차단)
LEGS: 15 Hz 이상만 통과  (15 Hz 미만 차단)
```

**왜 다른가요?**
- 다리 근육이 턱보다 DC 오염이 심함
- 더 공격적으로 제거 필요 (15 Hz > 10 Hz)

**효과**:
```
전: ~~~~~~~~~ (천천히 움직이는 기준선)
후: ━━━━━━━━━ (평평한 기준선 = 0)
```

---

### (2) Low-pass Filter - "높은 주파수는 통과시키지 않아!"

**목적**: 고주파 전자 잡음 제거

**비유**:
- 저음만 들리게 하는 서브우퍼
- 고음은 차단, 저음은 통과

**설정**:
```python
모든 채널: 100 Hz 이하만 통과 (100 Hz 초과 차단)
```

**왜 100 Hz?**
- 진짜 EMG 신호: 20-100 Hz 범위
- 100 Hz 이상은 대부분 전자 잡음

**효과**:
```
전: ━━v━v━v━v━━  (고주파 떨림 많음)
후: ━━━∧━∧━━━━  (부드러운 신호)
```

---

### (3) Notch Filter - "특정 주파수만 골라서 제거!"

**목적**: 60 Hz 전원선 간섭 제거

**비유**:
- 특정 라디오 주파수만 차단하는 필터
- 60 Hz만 정확히 제거, 나머지는 유지

**설정**:
```python
모든 채널: 60 Hz 제거 (Q=30)
```

**Q=30이 뭔가요?**
- Q가 클수록 더 좁은 범위만 제거
- Q=30: 59-61 Hz만 제거, 58 Hz나 62 Hz는 유지

**왜 60 Hz?**
- 한국/미국 전원선 주파수 = 60 Hz
- 모든 전자 장비에서 60 Hz 간섭 발생
- (유럽은 50 Hz 사용)

**효과**:
```
전: ━∿∿∿∿∿∿∿━  (60 Hz 진동 보임)
후: ━━━━━━━━━  (60 Hz만 제거됨)
```

---

## 5. 전처리 전 vs 후 비교 📈

### 주파수 분포 변화

#### CHIN (턱 근육)

**전처리 전**:
```
0-10 Hz:  ████████████████ 63%  ← DC/저주파 오염
10-30 Hz: ██████ 23%
30-60 Hz: ███ 11%
60-70 Hz: ██ 3%  ← 60 Hz 전원 잡음
```

**전처리 후**:
```
0-10 Hz:  (제거됨)
10-30 Hz: █████████████ 47%  ← EMG 신호
30-60 Hz: ████████ 29%
60-70 Hz: (제거됨)
```

#### RLEG (오른쪽 다리)

**전처리 전**:
```
0-10 Hz:  ███████████████████ 68%  ← 매우 심한 DC 오염!
10-30 Hz: ████ 15%
60-70 Hz: ██ 6%
```

**전처리 후**:
```
0-10 Hz:  (제거됨)
10-30 Hz: ██████████ 35%  ← 깨끗한 EMG
30-60 Hz: ████████ 28%
60-70 Hz: (제거됨)
```

---

## 6. 사용 방법 💻

### 기본 사용법

```bash
# 가상환경 활성화
conda activate atonia

# 전처리 실행
python3 preprocess_emg.py <입력_EDF_파일>

# 예시
python3 preprocess_emg.py ../Clinical_DB/Test1.EDF
```

### 출력 파일

```
입력: Test1.EDF
출력: Test1_preprocessed.edf

생성 위치: 입력 파일과 같은 폴더
```

### 처리 과정 화면

```
Reading EDF file...
  Duration: 8.1 hours
  EMG channels: CHIN, RLEG, LLEG

Processing CHIN...
  [1/3] High-pass filter (10 Hz)
  [2/3] Low-pass filter (100 Hz)
  [3/3] Notch filter (60 Hz)
  ✓ DC reduction: 63.4%
  ✓ EMG preservation: 95.7%

Processing RLEG...
  ...

Writing preprocessed EDF...
✅ Complete: Test1_preprocessed.edf
```

---

## 7. 주의사항 ⚠️

### (1) 원본 파일은 보존됩니다

```
✅ 안전: 원본 파일 건드리지 않음
✅ 출력: 새 파일(_preprocessed.edf)로 저장
```

### (2) Test1-10 vs PS0140 차이

**Test1-10 데이터**:
```python
샘플링 레이트: 256 Hz
채널명: EMG CHIN1-CHINz, EMG RLEG+, EMG LLEG+
```

**PS0140 데이터**:
```python
샘플링 레이트: 200 Hz (자동 감지)
채널명: Chin1-Chin2, Lat, Rat
```

→ **코드가 자동으로 인식하고 처리합니다!**

### (3) 처리 시간

```
파일 크기: ~75 MB (8시간 녹음)
처리 시간: 약 30-60초
```

### (4) 메모리 사용

```
권장 RAM: 최소 4 GB
대용량 파일(>500 MB): 8 GB 이상
```

---

## 8. 문제 해결 🔍

### 오류 1: "No EMG channels found"

**원인**: 채널명 인식 실패

**해결**:
```python
# preprocess_emg.py 의 CHANNEL_PATTERNS 확인
CHANNEL_PATTERNS = {
    'CHIN': 'CHIN',  # 여기에 실제 채널명 포함되어야 함
    'RLEG': 'RLEG',
    'LLEG': 'LLEG'
}
```

### 오류 2: "Nyquist frequency warning"

**원인**: Low-pass 100 Hz가 샘플링 레이트에 비해 너무 높음

**예시**:
```
샘플링: 200 Hz
Nyquist: 100 Hz
100 Hz low-pass: Nyquist와 같음 (경계!)

→ 자동으로 95 Hz로 조정됨
```

**해결**: 경고만 뜸, 자동 조정되므로 문제없음

### 오류 3: "Memory error"

**원인**: 파일이 너무 큼

**해결**:
1. 큰 파일은 분할해서 처리
2. 또는 더 많은 RAM 확보

---

## 9. 결과 검증 방법 ✅

### (1) 파일 크기 확인

```bash
ls -lh Test1.EDF Test1_preprocessed.edf

# 비슷한 크기여야 함 (±10%)
# 너무 작으면: 뭔가 잘못됨
# 너무 크면: 정상 (압축 차이)
```

### (2) RBDtector로 테스트

```bash
# 전처리 전
python3 run_baseline_test.py Test1
# → Artifact-free REM: 0%

# 전처리 후
python3 run_baseline_test.py Test1_preprocessed
# → Artifact-free REM: 97%
```

**기대 결과**:
- Artifact-free REM: 90% 이상 (문헌 기준 없음, 경험상 90% 이상이면 양호)
- Baseline 계산 성공

### (3) 시각적 확인 (선택사항)

전처리 스크립트는 자동으로 비교 그래프를 생성합니다:
- 위치: 출력 파일과 같은 폴더
- 파일명: `Test1_preprocessing_comparison.png`

---

## 10. 기술 배경 (심화) 🎓

### Butterworth Filter를 사용하는 이유

**특징**:
- 통과 대역에서 평탄한 주파수 응답
- 위상 왜곡 없음 (filtfilt 사용 시)
- 생체신호 처리 표준

**대안들**:
- Chebyshev: 더 가파른 차단, 하지만 리플 발생
- Elliptic: 가장 가파름, 하지만 위상 왜곡
- Bessel: 위상 특성 우수, 하지만 완만한 차단

→ **Butterworth가 EMG 처리에 가장 적합**

### 4th Order를 사용하는 이유

```
Order가 높을수록:
- 더 가파른 차단 (좋음)
- 더 많은 계산 (나쁨)
- 불안정해질 수 있음 (나쁨)

4th Order:
- 충분히 가파른 차단 (-24 dB/octave)
- 계산 효율적
- 안정적
```

**문헌 근거**:
- 대부분의 EMG 연구에서 4th order Butterworth 사용
- Montreal validation study (Joza et al., 2025)도 유사한 설정

### filtfilt의 의미

**일반 filter (forward only)**:
```
문제: 위상 지연 (Phase delay)
→ 신호가 시간축에서 뒤로 밀림
```

**filtfilt (forward-backward)**:
```
1. Forward 필터링
2. Backward 필터링
결과: 위상 지연 상쇄
→ Zero-phase filtering
```

**장점**:
- 시간 정렬 유지 (중요!)
- REM sleep annotation과 신호가 정확히 맞음

---

## 11. 관련 문서 📚

### 프로젝트 내 문서

- **CLAUDE.md**: 프로젝트 전체 개요
- **README_CONVERSION.md**: EDF 형식 변환 가이드
- **log/251105_02_signal_analysis.md**: 신호 분석 결과 (전처리 파라미터 결정 근거)
- **log/251105_11_preprocessing_results.md**: 전처리 결과 상세 분석

### 외부 참고 자료

**필터링 기초**:
- "Filtering the surface EMG signal" - PubMed 20206934
- "Reducing Noise, Artifacts and Interference in Single-Channel EMG Signals" - PMC10059683

**RBDtector 관련**:
- Joza et al., 2025, "Validation of RBDtector", Journal of Sleep Research
- Röthenbacher et al., 2022, "RBDtector: an open-source software", Scientific Reports

---

## 12. 요약 정리 📝

### 핵심 3줄 요약

1. **전처리 = 잡음 제거**: DC, 저주파, 60 Hz, 고주파 제거
2. **3단계 필터**: High-pass → Low-pass → Notch
3. **결과**: Artifact-free REM 0% → 97% 개선

### 초보자 체크리스트

- [ ] 가상환경 활성화 (`conda activate atonia`)
- [ ] 입력 EDF 파일 경로 확인
- [ ] `python3 preprocess_emg.py <파일명>` 실행
- [ ] `_preprocessed.edf` 파일 생성 확인
- [ ] RBDtector로 테스트
- [ ] Artifact-free REM이 90% 이상인지 확인

---

**작성일**: 2025-11-21
**마지막 수정**: 2025-11-21
**문의**: 로그 파일 참조 또는 CLAUDE.md 확인

**면책**: 이 문서는 초보자의 이해를 돕기 위해 작성되었습니다. 기술적으로 엄밀한 표현보다 쉬운 설명을 우선했습니다.
