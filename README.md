# [Day 1] 종합 실습: 실무형 수집·검증·품질 파이프라인
본 프로젝트는 Day 1 종합 실습 과제입니다. 

3개의 오픈 API를 비동기 방식으로 동시에 수집하고, 수집된 데이터를 검증 및 정제하여 여러 파일 포맷으로 저장 및 성능을 비교하는 파이프라인을 구축합니다.

---

## 1. 주요 기능 및 실습 범위

1. **비동기 데이터 수집 (Async Data Collection)**
   - `asyncio`와 `httpx`를 사용하여 아래 3가지 API에서 데이터를 동시에 수집합니다. (`asyncio.gather()` 활용)
     - **Open-Meteo API**: 서울 3일간의 시간대별 기온 및 강수확률 수집
     - **RestCountries API**: 대한민국의 국가 정보 수집
     - **ip-api**: 특정 IP(8.8.8.8) 기반의 위치 및 지역 정보 수집

2. **스키마 검증 (Schema Validation)**
   - 수집된 JSON 데이터에서 필요한 필드만 추출하여 **Pydantic v2** 모델을 정의하고, 데이터의 타입 및 범위를 검증합니다.
   - 예외 상황(타입 오류 등)에 대한 처리 코드를 포함합니다.

3. **데이터 저장 및 성능 비교 (Data Storage & Benchmark)**
   - 검증을 통과한 데이터를 **CSV**와 **Parquet** 두 가지 포맷으로 저장합니다.
   - 저장 및 로드할 때 소요되는 읽기/쓰기 시간을 측정하고 비교합니다.

4. **코드 품질 및 테스트 (Test & Code Quality)**
   - **pytest**를 활용하여 스키마 검증 및 파이프라인 테스트 코드(1건 이상)를 작성합니다.
   - **ruff**를 활용하여 코드의 스타일 검사(Lint)를 수행하고 오류를 해결합니다.

---

## 2. 개발 환경 설정 및 설치

본 프로젝트는 독립된 가상환경(`venv`)에서 필요한 패키지들을 설치하여 실행합니다.

### 요구사항 (Prerequisites)
- Python 3.8 이상

### 의존성 패키지 구성 (`requirements.txt`)
프로젝트 루트 폴더에 생성된 `requirements.txt` 파일에는 다음 라이브러리들이 정의되어 있습니다.

```text
httpx>=0.24.0          # 비동기 HTTP 요청을 위한 라이브러리
pydantic>=2.0.0        # 데이터 타입 및 범위 검증을 위한 Pydantic v2
pandas>=2.0.0          # 데이터 프레임 핸들링 및 포맷 변환
pyarrow>=12.0.0        # Parquet 파일 포맷 저장을 위한 백엔드 엔진
pytest>=7.0.0          # 유닛 테스트 프레임워크
ruff>=0.0.270          # 초고속 Python 린터 및 포매터
```

### 가상환경 활성화 및 패키지 설치
```bash
# 1. 프로젝트 폴더로 이동 (이미 이동한 경우 생략)

# 2. 가상환경 생성
python -m venv venv

# 3. 가상환경 활성화 (OS 환경에 맞게 선택)
# macOS / Linux
source venv/bin/activate
# Windows CMD
# venv\Scripts\activate
# Windows PowerShell
# .\venv\Scripts\Activate.ps1

# 4. 필수 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 실행 방법 (Usage)

### 파이프라인 실행 및 성능 측정
비동기 수집, 스키마 검증, 데이터 파일 저장 및 성능 측정을 일괄 수행합니다.
```bash
python main.py
```

### 테스트 코드 실행
`pytest`를 사용해 작성된 테스트 케이스들을 실행하여 검증 단계가 정상 작동하는지 테스트합니다.
```bash
pytest
```

### 코드 스타일 검사 (ruff)
Ruff를 이용하여 정적 분석 및 포맷팅 검사를 수행합니다.
```bash
# 오류 검사
ruff check .

# 자동 수정 가능한 오류 해결
ruff check --fix .
```

---

## 4. 프로젝트 구조 (Project Structure)

```text
skala_homwork/
├── main.py              # 비동기 수집 및 데이터 저장 파이프라인 메인 실행 파일
├── test_pipeline.py     # pytest를 활용한 스키마 검증 테스트 코드
├── requirements.txt     # 프로젝트 의존성 라이브러리 목록
└── README.md            # 실습 가이드 문서 (본 파일)
```

---

## 5. 코드 품질 및 테스트 검증 의견 (pytest & ruff)

### pytest 테스트 결과 및 의견
- **결과**: 총 6개의 테스트 케이스 실행 완료 및 전체 통과 (`6 passed`)
- **의견**: 
  - `test_pipeline.py`를 통해 3개 API(`Open-Meteo`, `RestCountries`, `IP-API`)의 수집 데이터 포맷에 대한 **정상 시나리오**와 유효하지 않은 임의 데이터 주입 시의 **예외 시나리오**를 균형 있게 검증

### ruff 린팅 결과 및 의견
- **결과**: f-string과 사용하지 않는 라이브러리 등을 확인
- **의견**:
  - `ruff`를 통해 검사한 결과, 미사용 라이브러리 임포트, 미정의 변수 사용, 잘못된 포맷팅 등울 확인하여 수정하였다.