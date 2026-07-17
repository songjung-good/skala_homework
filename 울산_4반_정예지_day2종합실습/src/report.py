"""
report.py
---------
Jinja2 템플릿을 이용해 전체 분석 결과를 report.md 로 자동 생성한다.

포함 내용: 데이터 개요, 결측치 처리 결과, 기술통계, 시각화 결과(경로),
          다중공선성 처리 내역, t-test 결과, 머신러닝 결과(Pipeline 구성·
          Confusion Matrix·모델 저장 경로 포함), 성향점수매칭(PSM) 기반
          인과 추론 보강 분석, 자동화(스케줄링/알림) 설계 현황, 결론.
"""

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from src.utils import REPORT_PATH, TARGET_SALARY_USD, TARGET_JOBSAT, get_logger

logger = get_logger(__name__)

REPORT_TEMPLATE = """\
# AI 도구 활용과 개발자 시장 가치 분석 보고서

- 생성 일시: {{ generated_at }}
- 데이터 출처: 2024 Stack Overflow Developer Survey (샘플, n={{ etl.final_rows }})

---

## 1. 데이터 개요

| 항목 | 값 |
|---|---|
| 원본 행 수 | {{ etl.clean_stats.raw_rows }} |
| 중복 제거 행 수 | {{ etl.clean_stats.duplicates_removed }} |
| 정제 후 행 수 | {{ etl.clean_stats.rows_after_clean }} |
| 최종 컬럼 수 | {{ etl.final_cols }} |

### Pandas vs Polars 로드 비교

| 라이브러리 | 로드 시간(초) | 피크 메모리(MB) |
|---|---|---|
| Pandas | {{ etl.load_comparison.pandas.load_time_sec }} | {{ etl.load_comparison.pandas.peak_memory_mb }} |
{%- if etl.load_comparison.polars %}
| Polars | {{ etl.load_comparison.polars.load_time_sec }} | {{ etl.load_comparison.polars.peak_memory_mb }} |
{%- else %}
| Polars | 미설치로 비교 불가 (`pip install polars` 후 재실행 시 비교됨) | - |
{%- endif %}

---

## 2. 결측치 처리 결과

| 변수 | 처리 전 결측 수 |
|---|---|
{%- for col, cnt in etl.clean_stats.missing_before.items() %}
| {{ col }} | {{ cnt }} |
{%- endfor %}

- 핵심 독립변수인 `AISelect` 결측 응답은 분석에서 제외했습니다.
- `{{ salary_col }}`(USD 환산 연봉)은 0 이하 값을 제거하고 1~99 퍼센타일로 클리핑(winsorize)하여 극단 이상치의 영향을 완화했습니다.

---

## 3. 기술통계

{{ descriptive_stats_md }}

---

## 4. 시각화 결과

### AI 사용 여부별 연봉 Boxplot (Seaborn)
![salary_boxplot]({{ figures.salary_boxplot }})

### AI 사용 여부별 만족도 Violin Plot (Seaborn)
![jobsat_violin]({{ figures.jobsat_violin }})

### 상관관계 Heatmap (Seaborn)
![correlation_heatmap]({{ figures.correlation_heatmap }})

### 국가별 AI 사용률 / 연봉 분포 (Plotly Interactive, 미설치 시 정적 이미지로 대체)
- 국가별 AI 사용률: `{{ figures.country_ai_rate }}`
- 연봉 분포 Histogram: `{{ figures.salary_histogram }}`

---

## 5. 상관관계 (Pearson) 및 다중공선성 처리

{{ correlation_md }}

{% if collinearity.years_workexp_corr is defined and collinearity.years_workexp_corr >= 0.7 -%}
> ⚠️ **다중공선성(Multicollinearity) 진단**: `YearsCodePro`(개발 전문 경력)와 `WorkExp`(총 업무 경력)의
> 피어슨 상관계수가 **{{ '%.3f' | format(collinearity.years_workexp_corr) }}**로 기준치(0.7) 이상 높게 나타났습니다.
> 두 변수를 트리 기반 모델에 동시에 투입할 시 변수 중요도가 왜곡되고 모델의 해석력이 저하될 수 있어,
> 머신러닝 파이프라인(7절)에서는 결측치가 상대적으로 적은 `YearsCodePro`만 남기고 `WorkExp`를 모델 입력에서 **제외**하였습니다.
{%- else -%}
> ℹ️ **다중공선성(Multicollinearity) 진단**: 주요 수치형 변수 간의 상관계수는 안정적인 수준이며,
> 분석 목적과 데이터의 밀집도를 고려하여 필요한 변수들을 선별적으로 파이프라인에 활용했습니다.
{%- endif %}
{% if collinearity.dropped_features -%}
> 제외된 변수 및 사유:
{%- for var, reason in collinearity.dropped_features.items() %}
> - `{{ var }}` — {{ reason }}
{%- endfor %}
{%- endif %}

---

## 6. 독립표본 t-test 결과

### 가설 1 — 연봉 ({{ salary_col }})

- H0: AI 사용자와 미사용자의 평균 연봉은 같다.
- H1: 두 그룹의 평균 연봉은 다르다.

| 지표 | 값 |
|---|---|
| AI 사용자 수 (n) | {{ salary_test.n_ai }} |
| AI 미사용자 수 (n) | {{ salary_test.n_non_ai }} |
| AI 사용자 평균 | {{ salary_test.mean_ai }} |
| AI 미사용자 평균 | {{ salary_test.mean_non_ai }} |
| t-statistic | {{ salary_test.t_statistic }} |
| p-value | {{ '%.4g' | format(salary_test.p_value) }} |
| 유의성 (α=0.05) | {{ '유의함' if salary_test.significant else '유의하지 않음' }} |
| Cohen's d | {{ salary_test.cohens_d }} ({{ salary_test.effect_size_label }}) |

### 가설 2 — 직무 만족도 ({{ jobsat_col }})

- H0: AI 사용자와 미사용자의 평균 만족도는 같다.
- H1: 두 그룹의 평균 만족도는 다르다.

| 지표 | 값 |
|---|---|
| AI 사용자 수 (n) | {{ jobsat_test.n_ai }} |
| AI 미사용자 수 (n) | {{ jobsat_test.n_non_ai }} |
| AI 사용자 평균 | {{ jobsat_test.mean_ai }} |
| AI 미사용자 평균 | {{ jobsat_test.mean_non_ai }} |
| t-statistic | {{ jobsat_test.t_statistic }} |
| p-value | {{ '%.4g' | format(jobsat_test.p_value) }} |
| 유의성 (α=0.05) | {{ '유의함' if jobsat_test.significant else '유의하지 않음' }} |
| Cohen's d | {{ jobsat_test.cohens_d }} ({{ jobsat_test.effect_size_label }}) |

> **해석**: p-value 가 통계적으로 유의하더라도 효과 크기(Cohen's d)가 작게 관찰된다면,
> 표본 크기가 충분히 커서 유의미함이 포착되었으나 실제 격차 수준은 제한적일 수 있음에 유의해야 합니다.

---

## 7. 머신러닝 결과

- 예측 목표: 연봉이 표본 중앙값(**{{ '{:,.0f}'.format(ml.median_salary) }} USD**)을 초과하는 고연봉 여부 (이진 분류)
- 사용 모델: {{ ml.metrics.model_type }}
- Pipeline 구성: `sklearn.pipeline.Pipeline([{{ ml.metrics.pipeline_steps | join(' -> ') }}])`
  (전처리 단계 `preprocessor` = `ColumnTransformer`(범주형: `OneHotEncoder`, 수치형: `StandardScaler`)로,
  학습/추론 시 데이터 누수 없이 하나의 객체로 일관되게 처리됩니다.)
- 학습/평가 데이터 수: train={{ ml.metrics.n_train }}, test={{ ml.metrics.n_test }}
- 모델 저장 경로 (`joblib.dump`): `{{ ml.metrics.model_saved_path }}`

| 지표 | 값 |
|---|---|
| Accuracy | {{ ml.metrics.accuracy }} |
| Precision | {{ ml.metrics.precision }} |
| Recall | {{ ml.metrics.recall }} |
| F1-score | {{ ml.metrics.f1 }} |

### Confusion Matrix

4가지 평가지표(Accuracy/Precision/Recall/F1)는 모두 아래 Confusion Matrix 로부터 계산된 값으로,
지표만 나열하는 것보다 원본 분류 결과를 함께 제시하면 어떤 유형의 오류(과대/과소 예측)가
발생했는지 확인할 수 있어 결과의 신뢰도를 높일 수 있습니다.

| 실제 \\ 예측 | 저연봉(0) 예측 | 고연봉(1) 예측 |
|---|---|---|
| 실제 저연봉(0) | TN = {{ ml.metrics.confusion_matrix_labels.tn }} | FP = {{ ml.metrics.confusion_matrix_labels.fp }} |
| 실제 고연봉(1) | FN = {{ ml.metrics.confusion_matrix_labels.fn }} | TP = {{ ml.metrics.confusion_matrix_labels.tp }} |

### Feature Importance (원 변수 단위 합산)

| 변수 | 중요도 |
|---|---|
{%- for var, imp in grouped_importance.items() %}
| {{ var }} | {{ '%.4f' | format(imp) }} |
{%- endfor %}

- `AISelect`(AI 사용 여부)의 중요도는 전체 {{ ml.num_features }}개 변수 중 **{{ ai_rank }}위**로 나타났습니다.
- 경력(YearsCodePro), 국가(Country), 직군(DevType) 등 통제변수의 상대적 중요도와 비교했을 때
  AI 사용 여부 단독의 예측력은 {{ ai_relative_conclusion }}.

---

## 8. 인과 추론 보강: 성향점수매칭 (Propensity Score Matching, PSM)

단순 t-test 는 "경력"이라는 강력한 혼란 변수(Confounder)를 통제하지 못합니다. 경력이 많은
개발자일수록 연봉도 높고 AI 도구를 먼저 받아들였을 가능성이 있어, 6절의 연봉 차이가 AI 자체의
효과가 아니라 **경력·국가·직군 차이에 의한 선택 편향**일 수 있습니다. 이를 보완하기 위해
통제변수({{ psm.control_variables | join(', ') if not psm.skipped else '' }})가 유사한 AI 사용자·
미사용자를 성향점수 기준으로 1:1 매칭한 뒤 재비교했습니다.

{% if psm.skipped %}
> PSM 분석은 유효 표본 부족({{ psm.reason }})으로 생략되었습니다.
{% else %}
| 구분 | 매칭 전 (전체 표본) | 매칭 후 (경력·국가·직군 유사 표본) |
|---|---|---|
| AI 사용자 수 (n) | {{ psm.before_matching.n_ai }} | {{ psm.after_matching.n_ai }} |
| AI 미사용자 수 (n) | {{ psm.before_matching.n_non_ai }} | {{ psm.after_matching.n_non_ai }} |
| AI 사용자 평균 연봉 | {{ psm.before_matching.mean_ai }} | {{ psm.after_matching.mean_ai }} |
| AI 미사용자 평균 연봉 | {{ psm.before_matching.mean_non_ai }} | {{ psm.after_matching.mean_non_ai }} |
| 평균 차이 | {{ psm.before_matching.diff }} | {{ psm.after_matching.diff }} |
| p-value | {{ '%.4g' | format(psm.before_matching.p_value) }} | {{ '%.4g' | format(psm.after_matching.p_value) if psm.after_matching.p_value is defined else 'N/A' }} |
| Cohen's d | {{ psm.before_matching.cohens_d }} | {{ psm.after_matching.cohens_d if psm.after_matching.cohens_d is defined else 'N/A' }} |

- 매칭 성공 쌍: {{ psm.n_matched_pairs }}쌍 (caliper={{ psm.caliper }})
- **해석**: 
  {%- if psm.after_matching.significant is defined %}
    {%- if salary_test.significant and not psm.after_matching.significant %}
    경력·국가·직군을 통제하기 전에는 유의했던 연봉 차이가 매칭 후 유사 표본 집단 간의 비교에서는 통계적 유의성을 잃었습니다. 이는 원래 관찰되었던 연봉 격차가 AI 사용의 순수 효과라기보다는 경력 등 주요 혼란 변수의 차이에 따른 선택 편향일 가능성을 강력하게 지지합니다.
    {%- elif salary_test.significant and psm.after_matching.significant %}
    혼란 변수들을 통제한 이후에도 유의미한 연봉 차이가 안정적으로 유지되는 점은, 유사한 조건을 가진 집단 내에서도 AI 사용 여부가 독자적인 연봉 격차와 연결되어 있음을 시사합니다.
    {%- else %}
    통제 적용 전후 검정 패턴을 고려할 때, 본 데이터 세트 하에서는 신중한 해석적 유보가 요구됩니다.
    {%- endif %}
  {%- else %}
    매칭 후 사후 검정 결과가 누락되었거나 완전하지 않아 해석 시 유의해야 합니다.
  {%- endif %}
{% endif %}

> 본 PSM 분석은 관찰 데이터 기반의 준실험적 방법으로, 무작위 배정 실험(RCT) 수준의 인과적
> 확증을 제공하지는 않으며 어디까지나 통제되지 않은 t-test보다 신뢰도를 보강하는 참고 지표입니다.

---

## 9. 자동화(운영) 설계 현황

CRISP-DM 의 배포(Deployment) 단계에 해당하는 운영 자동화 설계는 다음과 같이 구성되어 있습니다.

| 항목 | 내용 |
|---|---|
| 실행 순서 | {{ automation.pipeline_order }} |
| 스케줄링 | {{ automation.schedule }} (`{{ automation.schedule_source }}` 참고) |
| 로그 | {{ automation.log_file }} |
| Slack 알림 | {{ '설정됨 (SLACK_WEBHOOK_URL)' if automation.slack_configured else '미설정 — .env 구성 시 자동 활성화' }} |
| 이메일 알림 | {{ '설정됨 (SMTP)' if automation.email_configured else '미설정 — .env 구성 시 자동 활성화' }} |

- 알림 채널이 설정되지 않아도 파이프라인 본체(ETL~report.md 생성)는 정상적으로 완료되며,
  `notify.py` 가 `.env` 미설정을 감지해 알림만 조용히 건너뜁니다(필수 의존성 아님).
- 본 report.md 자체가 Jinja2 템플릿(`src/report.py`)을 통해 매 실행마다 자동 생성되는
  산출물로, 별도 수작업 없이 최신 분석 결과가 반영됩니다.

---

## 10. 결론

1. **연봉**: AI 도구 사용자와 미사용자 간 평균 연봉 차이는 {{ '통계적으로 유의' if salary_test.significant else '통계적으로 유의하지 않음' }}하며
   (p={{ '%.4g' | format(salary_test.p_value) }}), 평균값 상으로는 AI 사용자의 연봉이 상대적으로 {{ '높게' if salary_test.mean_ai >= salary_test.mean_non_ai else '낮게' }} 나타났습니다.
   효과 크기는 **{{ salary_test.effect_size_label }}** 수준입니다.
2. **직무 만족도**: AI 도구 사용자와 미사용자 간 평균 만족도 차이는 {{ '통계적으로 유의' if jobsat_test.significant else '통계적으로 유의하지 않음' }}하며
   (p={{ '%.4g' | format(jobsat_test.p_value) }}), 평균값 상으로는 AI 사용자의 만족도가 상대적으로 {{ '높게' if jobsat_test.mean_ai >= jobsat_test.mean_non_ai else '낮게' }} 나타났습니다.
   효과 크기는 **{{ jobsat_test.effect_size_label }}** 수준입니다.
3. **머신러닝 관점**: 고연봉 여부 예측에서 AI 사용 여부의 Feature Importance 순위는 전체 {{ ml.num_features }}개 중 {{ ai_rank }}위로,
   경력·국가·직군 등 다른 통제변수 대비 상대적 예측력이 {{ ai_relative_conclusion }}.
4. **PSM 인과 추론 관점**: 
   {%- if psm.skipped %}
   표본 부족 등으로 인해 PSM을 통한 추가적인 편향 통제 분석을 수행하지 못했습니다.
   {%- else %}
   경력·국가·직군을 통제한 매칭 표본에서 연봉 차이는 {{ '통계적으로 유의' if psm.after_matching.significant else '통계적으로 유의하지 않음' }}한 것으로 나타났습니다.
     {%- if salary_test.significant and not psm.after_matching.significant %}
     매칭 전에 관찰된 유의미한 차이가 통제 적용 후 사라진 양상은, 원래의 연봉 격차가 AI 선택에 기인했다기보다 인구통계학적·경력적 배경 차이에 의한 편향이었음을 뒷받침합니다.
     {%- elif salary_test.significant and psm.after_matching.significant %}
     외부 변수를 보정한 매칭 표본에서도 통계적 유의성이 유지되어, AI 도구의 활용과 실제 보상 가치 간에 독자적인 연결고리가 있을 가능성을 제시합니다.
     {%- else %}
     매칭 전후에 걸쳐 뚜렷하고 일관된 차이가 나타나지 않아, AI 도구 단독의 기여도를 정량화하기 위해서는 추가 연구가 필요합니다.
     {%- endif %}
   {%- endif %}
5. **종합 해석**:
   {%- if salary_test.significant %}
     통계 검정상 집단 간의 연봉 격차가 관찰되었으나,
     {%- if not psm.skipped and not psm.after_matching.significant %}
     혼란 변수를 통제한 PSM 분석에서 차이가 사라진 점과 주요 Feature Importance의 순위를 고려할 때, 이를 AI 도구 도입에 따른 직접적인 연봉 상승 효과로 단정하기는 어려우며 **고경력 혹은 특정 우호 환경의 개발자들이 AI 도구를 더 선제적으로 수용하는 선택 편향(selection bias)**의 영향일 가능성이 큽니다.
     {%- elif not psm.skipped and psm.after_matching.significant %}
     환경적 조건과 경력을 유사하게 정렬한 매칭 집단에서도 유의한 차이가 잔존한 점을 고려할 때, AI 활용이 개발 환경의 효율성 향상 및 실질적인 생산성 연계로 나타났을 가능성이 있습니다. 단, 측정하지 못한 숨은 혼란 변수가 있을 수 있어 확장 해석에는 주의가 필요합니다.
     {%- else %}
     실질 효과 크기(Cohen's d: {{ salary_test.cohens_d }})가 미미하다면 실제 실무 상황에서 체감할 수 있는 격차는 제한적일 수 있으므로 정량적 지표를 복합적으로 고려하여 해석할 것을 권장합니다.
     {%- endif %}
   {%- else %}
     데이터 내에서 집단 간의 유의미한 격차가 발견되지 않았거나 효과의 크기가 작으므로, 현시점에서는 AI 사용 유무 자체가 개발자의 직접적인 가치 상승이나 만족도 격차로 직접 이어진다고 규정하기는 어려우며 다른 역량적 요소가 더 주요하게 작용하고 있음을 시사합니다.
   {%- endif %}

> ⚠️ 본 보고서는 데이터(n={{ etl.final_rows }})를 기반으로 하며, 표본 크기가 작을 경우
> 통계 검정력이 낮아 결과 해석에 유의해야 합니다.
> 그래프의 한글 라벨은 `{{ korean_font }}` 폰트로 렌더링되었습니다.
"""


def _df_to_markdown(df, index_name="변수"):
    try:
        return df.round(3).to_markdown()
    except ImportError:
        # tabulate 미설치 시 대체 렌더링
        return "```\n" + df.round(3).to_string() + "\n```"


def generate_report(
    etl_report: dict,
    eda_result: dict,
    stats_result: dict,
    ml_result: dict,
    psm_result: dict | None = None,
    automation_info: dict | None = None,
) -> str:
    logger.info("report.md 생성 시작")

    desc_md = _df_to_markdown(eda_result["descriptive_stats"])
    corr_md = _df_to_markdown(stats_result["correlation"])

    # report.md 는 reports/ 폴더에 위치하므로, 같은 폴더 기준 상대경로로 변환
    figures_relative = {
        k: "figures/" + Path(v).name for k, v in eda_result["figures"].items()
    }

    grouped_importance = ml_result["feature_importance"].attrs.get("grouped_importance")
    ai_rank = None
    num_features = 0
    if grouped_importance is not None:
        ranked = list(grouped_importance.index)
        num_features = len(ranked)
        ai_rank = ranked.index("AISelect") + 1 if "AISelect" in ranked else "N/A"
        
        if isinstance(ai_rank, int) and num_features > 0:
            percentile = (ai_rank / num_features) * 100
            if percentile <= 30:
                ai_relative_conclusion = "상대적으로 상위에 위치하여 모델 내 중요도가 다소 높은 편입니다"
            else:
                ai_relative_conclusion = "다른 통제변수들에 비해 영향력이 상대적으로 미미하거나 제한적인 수준입니다"
        else:
            ai_relative_conclusion = "확인할 수 없습니다"
    else:
        ai_relative_conclusion = "판단 불가"

    ml_result["num_features"] = num_features

    # 다중공선성(YearsCodePro vs WorkExp) 정보: 상관행렬에서 직접 조회하여 표시
    corr = stats_result["correlation"]
    years_workexp_corr = float("nan")
    if "YearsCodePro" in corr.columns and "WorkExp" in corr.columns:
        years_workexp_corr = corr.loc["YearsCodePro", "WorkExp"]
    collinearity = {
        "years_workexp_corr": years_workexp_corr,
        "dropped_features": ml_result.get("collinear_features_dropped", {}),
    }

    if psm_result is None:
        psm_result = {"skipped": True, "reason": "PSM 분석 결과가 전달되지 않았습니다."}
    elif "skipped" not in psm_result:
        psm_result["skipped"] = False

    automation_info = automation_info or {}

    template = Template(REPORT_TEMPLATE)
    content = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        etl=etl_report,
        descriptive_stats_md=desc_md,
        correlation_md=corr_md,
        figures=figures_relative,
        salary_col=TARGET_SALARY_USD,
        jobsat_col=TARGET_JOBSAT,
        salary_test=stats_result["salary_ttest"],
        jobsat_test=stats_result["jobsat_ttest"],
        ml=ml_result,
        grouped_importance=grouped_importance,
        ai_rank=ai_rank,
        ai_relative_conclusion=ai_relative_conclusion,
        collinearity=collinearity,
        psm=psm_result,
        automation=automation_info,
        korean_font=eda_result.get("korean_font", "N/A"),
    )

    REPORT_PATH.write_text(content, encoding="utf-8")
    logger.info("report.md 저장 완료: %s", REPORT_PATH)
    return content


if __name__ == "__main__":
    from src.etl import run_etl
    from src.eda import run_eda
    from src.stats import run_statistical_analysis
    from src.model import run_modeling
    from src.causal import run_psm_analysis
    from src.notify import get_automation_config_summary

    df, etl_report = run_etl()
    eda_result = run_eda(df)
    stats_result = run_statistical_analysis(df)
    ml_result = run_modeling(df)
    psm_result = run_psm_analysis(df)
    automation_info = get_automation_config_summary()
    generate_report(etl_report, eda_result, stats_result, ml_result, psm_result, automation_info)