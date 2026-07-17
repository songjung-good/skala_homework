"""
stats.py
--------
통계 분석: 기술통계, 상관계수, 독립표본 t-test, Cohen's d 효과크기.

가설 1: AI 사용자와 미사용자의 평균 연봉(ConvertedCompYearly)은 같다 (H0) vs 다르다 (H1)
가설 2: AI 사용자와 미사용자의 평균 직무 만족도(JobSat)는 같다 (H0) vs 다르다 (H1)
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from src.utils import TARGET_SALARY_USD, TARGET_JOBSAT, get_logger

logger = get_logger(__name__)


def cohens_d(a: pd.Series, b: pd.Series) -> float:
    """두 독립표본 간 Cohen's d (pooled standard deviation 기준)."""
    a, b = a.dropna(), b.dropna()
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float("nan")
    pooled_std = np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    if pooled_std == 0:
        return float("nan")
    return (a.mean() - b.mean()) / pooled_std


def interpret_cohens_d(d: float) -> str:
    d = abs(d)
    if np.isnan(d):
        return "계산 불가"
    if d < 0.2:
        return "무시할 수 있는 수준 (negligible)"
    if d < 0.5:
        return "작은 효과 (small)"
    if d < 0.8:
        return "중간 효과 (medium)"
    return "큰 효과 (large)"


def independent_ttest(df: pd.DataFrame, value_col: str, group_col: str = "AI_User") -> dict:
    """AI 사용(1) vs 미사용(0) 그룹 간 독립표본 t-test 수행."""
    sub = df[[value_col, group_col]].dropna()
    group1 = sub.loc[sub[group_col] == 1, value_col]  # AI 사용
    group0 = sub.loc[sub[group_col] == 0, value_col]  # AI 미사용

    if len(group1) < 2 or len(group0) < 2:
        logger.warning("%s: 표본 수 부족으로 t-test 를 수행할 수 없습니다.", value_col)
        return {
            "variable": value_col,
            "n_ai": len(group1),
            "n_non_ai": len(group0),
            "error": "표본 수 부족",
        }

    t_stat, p_value = scipy_stats.ttest_ind(group1, group0, equal_var=False)  # Welch's t-test
    d = cohens_d(group1, group0)

    result = {
        "variable": value_col,
        "n_ai": len(group1),
        "n_non_ai": len(group0),
        "mean_ai": round(group1.mean(), 3),
        "mean_non_ai": round(group0.mean(), 3),
        "std_ai": round(group1.std(), 3),
        "std_non_ai": round(group0.std(), 3),
        "t_statistic": round(float(t_stat), 4),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "cohens_d": round(float(d), 4) if not np.isnan(d) else None,
        "effect_size_label": interpret_cohens_d(d),
    }
    logger.info(
        "%s t-test: t=%.3f, p=%.4g, Cohen's d=%.3f (%s)",
        value_col, t_stat, p_value, d, result["effect_size_label"],
    )
    return result


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in [TARGET_SALARY_USD, "YearsCodePro", TARGET_JOBSAT, "AI_User", "WorkExp"] if c in df.columns]
    return df[cols].corr(method="pearson")


def run_statistical_analysis(df: pd.DataFrame) -> dict:
    logger.info("통계 분석 시작")
    results = {
        "salary_ttest": independent_ttest(df, TARGET_SALARY_USD),
        "jobsat_ttest": independent_ttest(df, TARGET_JOBSAT),
        "correlation": correlation_matrix(df),
    }
    return results


if __name__ == "__main__":
    from src.etl import run_etl

    df, _ = run_etl()
    res = run_statistical_analysis(df)
    print(res["salary_ttest"])
    print(res["jobsat_ttest"])
