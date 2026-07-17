"""공용 pytest fixture 모음.

실제 survey_results_public.csv(대용량)를 사용하지 않고, 각 모듈이 기대하는
컬럼 구조를 그대로 갖춘 소규모 합성 데이터로 테스트한다.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def raw_survey_df():
    """src.etl.clean_data / engineer_features 테스트용 원시 데이터(ANALYSIS_COLS 형태).

    - ResponseId 4번 행이 완전히 중복되어 있다 (중복 제거 검증용).
    - AISelect 결측 행이 하나 있다 (결측 제외 검증용).
    - ConvertedCompYearly 에 음수(0 이하)와 극단적으로 큰 값이 섞여 있다 (이상치 처리 검증용).
    - YearsCodePro 에 텍스트 응답("Less than 1 year" 등)이 섞여 있다 (숫자 변환 검증용).
    """
    return pd.DataFrame(
        {
            "ResponseId": [1, 2, 3, 4, 4, 5, 6, 7, 8],
            "AISelect": [
                "Yes",
                "No",
                "Yes",
                "No, and I don't plan to",
                "No, and I don't plan to",
                "Yes",
                None,
                "No, but I plan to soon",
                "Yes",
            ],
            "CompTotal": [50000, 60000, 70000, 40000, 40000, 80000, 90000, 30000, 100000],
            "ConvertedCompYearly": [50000, 60000, 70000, 40000, 40000, -5, 1_000_000, 30000, 85000],
            "Currency": ["USD"] * 9,
            "JobSat": [7, 6, 8, 5, 5, 9, 4, 6, 8],
            "YearsCodePro": ["5", "Less than 1 year", "10", "3", "3", "More than 50 years", "7", "2", "12"],
            "DevType": ["Backend"] * 9,
            "Country": ["USA"] * 9,
            "OrgSize": ["100-999"] * 9,
            "WorkExp": [5, 1, 10, 3, 3, 51, 7, 2, 12],
        }
    )


@pytest.fixture
def analysis_df():
    """ETL 이후 형태(AI_User 등 파생 변수 포함)의 합성 데이터.

    stats / model / causal 모듈 테스트에 공용으로 사용한다. AI 사용자가 평균적으로
    연봉과 만족도가 더 높도록 설계하여, 통계/모델 검증에서 의미 있는 신호가 나오게 한다.
    """
    rng = np.random.default_rng(42)
    n = 120
    ai_user = rng.integers(0, 2, size=n)
    years_code = rng.uniform(0, 20, size=n)
    base_salary = 40000 + years_code * 3000 + ai_user * 8000
    salary = base_salary + rng.normal(0, 5000, size=n)
    jobsat = np.clip(5 + ai_user * 0.8 + rng.normal(0, 1.5, size=n), 0, 10)

    return pd.DataFrame(
        {
            "AISelect": np.where(ai_user == 1, "Yes", "No"),
            "AI_User": ai_user,
            "AISelect_clean": np.where(ai_user == 1, "Yes", "No"),
            "ConvertedCompYearly": salary,
            "Salary_log": np.log1p(salary),
            "JobSat": jobsat,
            "YearsCodePro": years_code,
            "DevType": rng.choice(["Backend", "Frontend", "Fullstack"], size=n),
            "Country": rng.choice(["USA", "Korea", "Germany", "India"], size=n),
            "OrgSize": rng.choice(["1-9", "10-99", "100-999"], size=n),
            "WorkExp": years_code + rng.normal(0, 1, size=n),
        }
    )
