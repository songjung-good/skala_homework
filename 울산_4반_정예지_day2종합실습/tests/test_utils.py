import logging
from pathlib import Path

from src import utils


def test_get_logger_returns_same_instance_for_same_name():
    logger1 = utils.get_logger("test_logger_x")
    logger2 = utils.get_logger("test_logger_x")
    assert logger1 is logger2


def test_get_logger_does_not_duplicate_handlers_on_repeat_calls():
    utils.get_logger("test_logger_dup")
    utils.get_logger("test_logger_dup")
    logger = utils.get_logger("test_logger_dup")
    assert len(logger.handlers) == 1


def test_get_logger_defaults_to_info_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    logger = utils.get_logger("test_logger_level_new")
    assert logger.level == logging.INFO


def test_project_directories_exist():
    for d in (
        utils.DATA_RAW_DIR,
        utils.DATA_PROCESSED_DIR,
        utils.REPORTS_DIR,
        utils.FIGURES_DIR,
        utils.MODELS_DIR,
    ):
        assert Path(d).is_dir()


def test_analysis_cols_includes_id_and_targets():
    assert utils.ID_COL in utils.ANALYSIS_COLS
    assert utils.TARGET_SALARY_USD in utils.ANALYSIS_COLS
    assert utils.TARGET_JOBSAT in utils.ANALYSIS_COLS


def test_setup_korean_font_returns_non_empty_string():
    font_name = utils.setup_korean_font()
    assert isinstance(font_name, str)
    assert font_name
