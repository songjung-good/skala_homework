# [Day 1]종합 실습: 실무형 수집·검증·품질 파이프라인

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

4. **코드 품질 및 테스트 (Test & Code Quality)**

---

## 2. 개발 환경 설정 및 설치

본 프로젝트는 독립된 가상환경(`venv`)에서 필요한 패키지들을 설치하여 실행합니다.

### 요구사항 (Prerequisites)
- Python 3.8 이상

### 가상환경 및 패키지 설치
```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화 (macOS / Linux)
source venv/bin/activate
# Windows CMD: venv\Scripts\activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1

# 3. 필수 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

*(필요 패키지 예시: `httpx`, `pydantic>=2.0`, `pandas`, `pyarrow`, `pytest`, `ruff` 등)*

---

## 3. 실행 방법 (Usage)


---

## 4. 프로젝트 구조 (Project Structure)
