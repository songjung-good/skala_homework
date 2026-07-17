"""
utils.py
--------
공통 설정, 로깅, 컬럼 그룹 정의 등 프로젝트 전역에서 재사용되는 유틸리티 모음.
"""

import logging
import os
from pathlib import Path

# ------------------------------------------------------------------
# 경로 설정
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = BASE_DIR / "models"

RAW_CSV_PATH = DATA_RAW_DIR / "survey_results_public.csv"
SCHEMA_PATH = DATA_RAW_DIR / "schema.txt"
PROCESSED_CSV_PATH = DATA_PROCESSED_DIR / "survey_processed.csv"
MODEL_PATH = MODELS_DIR / "model.pkl"
REPORT_PATH = REPORTS_DIR / "report.md"

for d in (DATA_RAW_DIR, DATA_PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# 로깅 설정
# ------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    """모듈별로 통일된 포맷의 로거를 반환한다."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
    return logger


# ------------------------------------------------------------------
# 분석에 사용할 컬럼 그룹 정의 (schema.txt / 설계 문서 기준)
# ------------------------------------------------------------------
ID_COL = "ResponseId"

# 핵심 독립변수 (AI 사용 여부)
AI_COLS = ["AISelect", "AISearchDevHaveWorkedWith"]

# 종속변수
TARGET_SALARY_RAW = "CompTotal"          # 응답자가 직접 입력한 원 통화 연봉 (통화가 제각각이라 국가간 비교 부적합)
TARGET_SALARY_USD = "ConvertedCompYearly"  # Stack Overflow가 USD로 환산한 연봉 (비교 분석에 사용)
TARGET_JOBSAT = "JobSat"                 # 0~10 NPS 스타일 만족도 점수

# 통제변수 (모델 feature)
CONTROL_COLS = ["YearsCodePro", "DevType", "Country", "OrgSize", "WorkExp"]

# 최종 분석에 사용할 컬럼 전체
ANALYSIS_COLS = (
    [ID_COL, "AISelect", TARGET_SALARY_RAW, TARGET_SALARY_USD, "Currency", TARGET_JOBSAT]
    + CONTROL_COLS
)

RANDOM_STATE = 42


# ------------------------------------------------------------------
# 한글 폰트 자동 감지 (Seaborn/Matplotlib 그래프 내 한글 라벨 깨짐 방지)
# ------------------------------------------------------------------
# 실행 환경(OS)마다 설치된 한글 폰트 이름이 다르므로, 여러 후보 중
# 시스템에 실제로 설치된 폰트를 자동으로 탐색하여 적용한다.
#   - Windows: Malgun Gothic
#   - macOS  : AppleGothic
#   - Linux  : NanumGothic 또는 Noto Sans/Serif CJK KR (배포판에 따라 상이)
KOREAN_FONT_CANDIDATES = [
    "NanumGothic",
    "Malgun Gothic",
    "AppleGothic",
    "Noto Sans CJK KR",
    "Noto Sans KR",
    "Noto Serif CJK KR",
    # Noto Sans/Serif CJK 는 지역별 배포판(JP/SC/TC/HK)이더라도 통합 글꼴(Super OTC)이라
    # 한글(Hangul) 글리프를 모두 포함하므로, KR 표기가 없는 배포판도 대체 후보로 포함한다.
    "Noto Sans CJK JP",
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans CJK HK",
    "Noto Serif CJK JP",
]


def setup_korean_font() -> str:
    """설치된 한글 지원 폰트를 자동 탐색하여 matplotlib 전역 설정에 적용한다.

    후보 목록(KOREAN_FONT_CANDIDATES)을 순서대로 확인하여 시스템 폰트 목록에
    실제로 존재하는 첫 번째 폰트를 사용한다. 하나도 설치되어 있지 않으면
    경고 로그를 남기고 기본 폰트를 사용한다(이 경우 한글 라벨이 네모(□)로
    깨질 수 있으므로, `apt-get install fonts-nanum` 등으로 폰트 설치를 권장한다).
    """
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    logger = get_logger(__name__)
    installed = {f.name for f in fm.fontManager.ttflist}

    for candidate in KOREAN_FONT_CANDIDATES:
        if candidate in installed:
            plt.rcParams["font.family"] = candidate
            plt.rcParams["axes.unicode_minus"] = False
            logger.info("한글 폰트 적용: %s", candidate)
            return candidate

    plt.rcParams["axes.unicode_minus"] = False
    logger.warning(
        "한글 지원 폰트를 찾지 못했습니다 (후보: %s). "
        "그래프의 한글 라벨이 깨져 보일 수 있습니다. "
        "Linux: `sudo apt-get install fonts-nanum`, "
        "macOS: AppleGothic(기본 내장), Windows: Malgun Gothic(기본 내장) 확인 필요.",
        ", ".join(KOREAN_FONT_CANDIDATES),
    )
    return "DejaVu Sans (한글 미지원)"
