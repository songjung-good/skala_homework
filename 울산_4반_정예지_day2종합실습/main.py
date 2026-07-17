"""
main.py
-------
전체 파이프라인 실행 엔트리 포인트.

ETL -> EDA -> Statistics -> ML -> report.md 생성
순서로 자동 실행된다.

실행:
    python main.py
"""

from src.utils import get_logger
from src.etl import run_etl
from src.eda import run_eda
from src.stats import run_statistical_analysis
from src.model import run_modeling
from src.causal import run_psm_analysis
from src.report import generate_report
from src.notify import notify_pipeline_complete, get_automation_config_summary

logger = get_logger("main")


def main():
    logger.info("=" * 60)
    logger.info("AI 도구 활용과 개발자 시장 가치 분석 파이프라인 시작")
    logger.info("=" * 60)

    # 1. ETL
    df, etl_report = run_etl()

    # 2. EDA
    eda_result = run_eda(df)

    # 3. 통계 분석 (단순 독립표본 t-test)
    stats_result = run_statistical_analysis(df)

    # 4. 머신러닝 (다중공선성 처리 + Pipeline + Confusion Matrix 포함)
    ml_result = run_modeling(df)

    # 5. 인과 추론 보강: 성향점수매칭(PSM)으로 경력/국가/직군 등 혼란 변수를 통제한 재비교
    psm_result = run_psm_analysis(df)

    # 6. 자동화(스케줄링/알림) 설계 현황 요약
    automation_info = get_automation_config_summary()

    # 7. 자동 리포트 생성
    generate_report(etl_report, eda_result, stats_result, ml_result, psm_result, automation_info)

    # 8. (선택) Slack/이메일 알림 - .env 설정이 없으면 자동 스킵
    notify_pipeline_complete(
        report_path="reports/report.md",
        summary=f"Accuracy={ml_result['metrics']['accuracy']}, F1={ml_result['metrics']['f1']}",
    )

    logger.info("파이프라인 완료. reports/report.md 를 확인하세요.")


if __name__ == "__main__":
    main()
