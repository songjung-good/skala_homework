# AI 도구 활용과 개발자 시장 가치의 실상

2024 Stack Overflow Developer Survey 데이터를 이용해 **AI 개발 도구 사용 여부가 연봉·직무 만족도에
실질적인 영향을 주는지**를 CRISP-DM 절차에 따라 검증하는 분석 프로젝트입니다.

## 1. 프로젝트 목적

- AI 도구 사용자와 미사용자의 연봉 차이를 독립표본 t-test 로 검증 (Q1)
- AI 도구 사용자와 미사용자의 직무 만족도 차이를 t-test + Cohen's d 로 검증 (Q2)
- AI 사용 여부가 연봉 예측에 중요한 변수인지 Feature Importance 로 확인 (Q3)
- 경력·국가·직무를 통제해도 AI 사용 효과가 유의한지 성향점수매칭(PSM)으로 재검토 (Q4)

## 2. 프로젝트 구조

```
project/
├── data/
│   ├── raw/                  # 원본 survey_results_public.csv, schema.txt
│   └── processed/            # 정제된 데이터 (survey_processed.csv)
├── notebooks/                # 탐색용 노트북 (선택)
├── src/
│   ├── etl.py                # 로드(Pandas/Polars 비교) · 결측치 · 이상치 · 파생변수
│   ├── eda.py                # 기술통계, Seaborn/Plotly 시각화, 상관관계, 한글 폰트 자동 설정
│   ├── stats.py               # 독립표본 t-test, Cohen's d
│   ├── model.py               # 다중공선성 처리 + ColumnTransformer + RandomForest/DecisionTree Pipeline
│   ├── causal.py               # 성향점수매칭(PSM) 기반 인과 추론 보강 분석
│   ├── report.py              # Jinja2 기반 report.md 자동 생성
│   ├── notify.py              # (선택) Slack/이메일 완료 알림 + 자동화 설계 요약
│   └── utils.py                # 공통 경로/로깅/컬럼/한글 폰트 자동 감지 설정
├── reports/
│   ├── report.md              # 자동 생성된 최종 분석 보고서
│   └── figures/                # 생성된 그래프 (png / interactive html)
├── models/
│   └── model.pkl               # 학습된 모델 (joblib)
├── requirements.txt
├── .env.example
├── cron_example.txt            # 정기 실행(Scheduler) 설정 예시
├── main.py                     # 전체 파이프라인 실행 엔트리포인트
└── README.md
```

## 3. 실행 방법

```bash
# 1) 가상환경 생성 (선택)
python3 -m venv venv
source venv/bin/activate

# 2) 의존성 설치
pip install -r requirements.txt

# 3) 전체 파이프라인 실행 (ETL -> EDA -> Stats -> ML -> report.md)
python main.py
```

실행이 끝나면 `reports/report.md` 에서 전체 분석 결과를, `reports/figures/` 에서 시각화 자료를,
`models/model.pkl` 에서 학습된 모델을 확인할 수 있습니다.

### 개별 모듈만 실행하고 싶을 때

```bash
python -m src.etl      # 데이터 정제까지만
python -m src.eda      # EDA까지 (ETL 포함)
python -m src.stats    # 통계 분석까지 (ETL 포함)
python -m src.model    # 모델링까지 (ETL 포함)
python -m src.causal   # PSM 인과 추론 분석까지 (ETL 포함)
```

## 4. 개발 환경 및 의존성

- Python 3.10+
- pandas, numpy, scipy, scikit-learn, matplotlib, seaborn, jinja2, joblib, tabulate (필수)
- polars, plotly (선택: 미설치 시 각각 로드 비교/인터랙티브 시각화를 자동으로 건너뛰거나
  matplotlib 대체 이미지를 생성합니다 — `requirements.txt` 참고)
- **한글 폰트**: 그래프에 한글 라벨을 표시하려면 시스템에 한글 지원 폰트가 설치되어 있어야
  합니다. `src/utils.py`의 `setup_korean_font()`가 NanumGothic → Malgun Gothic → AppleGothic
  → Noto Sans/Serif CJK(KR/JP/SC/TC/HK) 순으로 설치된 폰트를 자동 탐색해 적용하며, 하나도 없으면
  한글이 네모(□)로 깨질 수 있다는 경고를 로그로 남깁니다.
  Linux에서 폰트가 없다면 `sudo apt-get install fonts-nanum` 설치를 권장합니다.

`.env.example` 을 `.env` 로 복사한 뒤 필요한 값을 채우면 `main.py` 실행 후
Slack/이메일로 완료 알림을 받을 수 있습니다. `cron_example.txt` 는 매일 정해진 시각에
파이프라인을 자동 실행하는 crontab 설정 예시입니다(자동화 설계 현황은 `report.md` 9절에
매 실행마다 자동으로 기록됩니다).

## 5. 데이터 관련 주의사항

- 본 저장소에 포함된 CSV는 **원본 설문의 일부를 샘플링한 축소 버전**입니다.
  실제 배포/제출 시에는 전체 `survey_results_public.csv` 로 교체해 재실행하는 것을 권장합니다.
- 연봉 비교에는 국가별 통화가 제각각인 `CompTotal` 대신, Stack Overflow가 USD로 표준화한
  `ConvertedCompYearly` 를 사용했습니다.
- 표본 크기가 작을 경우 t-test 의 통계적 검정력이 낮아지고 신뢰구간이 넓어질 수 있으므로,
  `report.md` 의 결론은 반드시 표본 크기와 함께 해석해야 합니다.

## 6. 다중공선성 및 인과 추론 보강

- **다중공선성**: `YearsCodePro`(개발 전문 경력)와 `WorkExp`(총 업무 경력)의 피어슨 상관계수가
  0.9 이상으로 매우 높게 나타나, 머신러닝 모델(`src/model.py`) 입력에서는 결측치가 더 적고
  분석 목적에 더 부합하는 `YearsCodePro`만 사용하고 `WorkExp`는 제외했습니다.
- **인과 추론(PSM)**: 단순 t-test 는 경력이라는 혼란 변수를 통제하지 못하므로, `src/causal.py`
  에서 성향점수매칭(Propensity Score Matching)으로 경력·국가·직군이 유사한 AI 사용자/미사용자
  쌍을 매칭해 재비교합니다. 결과는 `report.md` 8절에서 확인할 수 있습니다.

## 7. 산출물 요약

| 산출물 | 위치 |
|---|---|
| 정제된 데이터 | `data/processed/survey_processed.csv` |
| 최종 분석 보고서 (다중공선성·PSM·자동화 현황 포함) | `reports/report.md` |
| 시각화 | `reports/figures/*.png`, `*.html` |
| 학습된 모델 (Pipeline 전체, joblib) | `models/model.pkl` |
