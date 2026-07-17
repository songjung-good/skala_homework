"""
notify.py
---------
정기 실행(Cron/Scheduler) 이후 결과를 Slack 또는 이메일로 통지하는 선택적 모듈.
.env 에 관련 값이 설정되어 있지 않으면 조용히 스킵한다 (필수 의존성 아님).

사용 예 (crontab, 매일 오전 8시 실행):
    0 8 * * * cd /path/to/project && /usr/bin/python3 main.py >> logs/cron.log 2>&1
"""

import os
import smtplib
from email.mime.text import MIMEText

from src.utils import get_logger

logger = get_logger(__name__)


def notify_slack(message: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL 미설정 -> Slack 알림 스킵")
        return
    try:
        import requests

        resp = requests.post(webhook_url, json={"text": message}, timeout=10)
        resp.raise_for_status()
        logger.info("Slack 알림 전송 완료")
    except Exception as e:  # noqa: BLE001
        logger.warning("Slack 알림 전송 실패: %s", e)


def notify_email(subject: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    to_addr = os.environ.get("REPORT_RECIPIENT_EMAIL")
    if not host or not to_addr:
        logger.info("SMTP 설정 미완료 -> 이메일 알림 스킵")
        return
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        logger.info("이메일 알림 전송 완료: %s", to_addr)
    except Exception as e:  # noqa: BLE001
        logger.warning("이메일 알림 전송 실패: %s", e)


def notify_pipeline_complete(report_path: str, summary: str = "") -> None:
    message = f"[AI 도구-연봉 분석] 파이프라인 실행 완료\nreport: {report_path}\n{summary}"
    notify_slack(message)
    notify_email("AI 도구-연봉 분석 리포트 생성 완료", message)


def get_automation_config_summary() -> dict:
    """운영 자동화 설계 현황을 report.md 에 기록하기 위해 요약한다.

    - 스케줄링: cron_example.txt 에 정의된 대로 매일 08:00 에 main.py 전체 파이프라인
      (ETL -> EDA -> Stats -> ML -> report.md 생성) 을 재실행하도록 설계되어 있다.
    - 알림: 실행 완료 후 notify.py 가 Slack Webhook / 이메일(SMTP) 로 결과를 전달한다.
      .env 에 관련 값이 설정되지 않은 경우 알림은 자동으로 스킵되며 파이프라인 자체는
      정상적으로 완료된다(알림은 선택 기능이며 필수 의존성이 아님).
    """
    return {
        "schedule": "매일 08:00 (cron: `0 8 * * * cd /path/to/project && python3 main.py`)",
        "schedule_source": "cron_example.txt",
        "pipeline_order": "ETL -> EDA -> 통계 분석 -> 머신러닝 -> report.md 자동 생성 -> 알림",
        "slack_configured": bool(os.environ.get("SLACK_WEBHOOK_URL")),
        "email_configured": bool(os.environ.get("SMTP_HOST") and os.environ.get("REPORT_RECIPIENT_EMAIL")),
        "log_file": "logs/cron.log (cron 표준출력/에러 리다이렉트)",
    }


if __name__ == "__main__":
    notify_pipeline_complete("reports/report.md", "테스트 알림입니다.")
