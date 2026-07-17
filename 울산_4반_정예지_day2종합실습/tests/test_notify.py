import pytest

import src.notify as notify


def test_notify_slack_skips_silently_without_webhook_url(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    notify.notify_slack("test message")  # 예외 없이 조용히 스킵되어야 함


def test_notify_email_skips_silently_without_smtp_config(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("REPORT_RECIPIENT_EMAIL", raising=False)
    notify.notify_email("subject", "body")  # 예외 없이 조용히 스킵되어야 함


def test_notify_slack_posts_when_webhook_configured(monkeypatch):
    requests = pytest.importorskip("requests")

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/xxx")
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    notify.notify_slack("hello")

    assert calls["url"] == "https://hooks.slack.test/xxx"
    assert calls["json"] == {"text": "hello"}


def test_get_automation_config_summary_reflects_unset_env(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("REPORT_RECIPIENT_EMAIL", raising=False)

    summary = notify.get_automation_config_summary()
    assert summary["slack_configured"] is False
    assert summary["email_configured"] is False
    assert summary["pipeline_order"].startswith("ETL")


def test_get_automation_config_summary_reflects_configured_slack(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.test/xxx")
    summary = notify.get_automation_config_summary()
    assert summary["slack_configured"] is True
