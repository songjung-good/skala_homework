"""
causal.py
---------
인과 추론(Causal Inference) 보강 모듈: 성향점수매칭 (Propensity Score Matching, PSM)

배경
----
단순 독립표본 t-test(stats.py)는 "경력"이라는 강력한 혼란 변수(Confounder)를
통제하지 못한다. 실제로는 경력이 많은 개발자일수록 (a) 연봉이 높고 (b) AI 도구를
더 일찍 받아들였을 가능성이 있어, "AI 사용 -> 고연봉"이라는 관계가 AI 자체의
효과가 아니라 경력 차이에 의한 선택 편향(selection bias)일 수 있다.

방법
----
1. 통제변수(YearsCodePro, Country, DevType, OrgSize)로 로지스틱 회귀를 학습해
   각 응답자의 "AI 도구를 사용할 성향(propensity score)"을 추정한다.
2. AI 사용자 각각에 대해, 성향점수가 가장 유사한 미사용자를 1:1 최근접 이웃으로
   매칭한다(caliper 이내인 경우만 채택하여 무리한 매칭을 방지).
3. 매칭된 두 그룹(경력·국가·직군 분포가 유사해진 표본)에서 다시 독립표본 t-test와
   Cohen's d 를 계산해, 혼란 변수를 통제한 뒤에도 AI 효과가 유지되는지 확인한다.

주의: 이는 관찰 데이터 기반의 준실험적(quasi-experimental) 방법으로, 무작위
배정 실험(RCT)과 같은 수준의 인과적 확증을 제공하지는 않는다. 다만 통제되지
않은 t-test보다는 혼란 변수의 영향을 줄여 더 신뢰할 수 있는 비교를 제공한다.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.stats import cohens_d, interpret_cohens_d
from src.utils import RANDOM_STATE, TARGET_SALARY_USD, get_logger
from scipy import stats as scipy_stats

logger = get_logger(__name__)

PSM_CATEGORICAL = ["Country", "DevType", "OrgSize"]
PSM_NUMERIC = ["YearsCodePro"]  # WorkExp 는 model.py 와 동일한 사유로 제외 (다중공선성)
CALIPER = 0.05  # 성향점수 거리 허용 오차(caliper): 이보다 먼 매칭은 기각


def estimate_propensity_scores(df: pd.DataFrame) -> pd.Series:
    """AI_User(0/1)를 통제변수로 예측하는 로지스틱 회귀로 성향점수를 추정한다."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), PSM_CATEGORICAL),
            ("num", StandardScaler(), PSM_NUMERIC),
        ]
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("logit", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        ]
    )
    X = df[PSM_CATEGORICAL + PSM_NUMERIC]
    y = df["AI_User"]
    pipeline.fit(X, y)
    scores = pipeline.predict_proba(X)[:, 1]
    return pd.Series(scores, index=df.index, name="propensity_score")


def match_nearest_neighbor(df: pd.DataFrame, caliper: float = CALIPER) -> pd.DataFrame:
    """AI 사용자 1명당 성향점수가 가장 유사한 미사용자 1명을 caliper 이내에서, 비복원(greedy) 방식으로 매칭한다."""
    treated = df[df["AI_User"] == 1]
    control = df[df["AI_User"] == 0]

    if len(treated) == 0 or len(control) == 0:
        logger.warning("PSM: 처리군 또는 대조군 표본이 없어 매칭을 수행할 수 없습니다.")
        return df.iloc[0:0]

    # 성능을 위해 대조군 전체에 대해 한 번만 NearestNeighbors 를 학습하고,
    # 처리군마다 후보(k개)를 한 번에 조회한 뒤, 이미 사용된 대조군은 건너뛰며
    # 순차적으로 배정하는 비복원(greedy) 방식을 사용한다.
    k = min(50, len(control))
    nn = NearestNeighbors(n_neighbors=k)
    nn.fit(control[["propensity_score"]])
    treated_sorted = treated.sort_values("propensity_score")
    distances, positions = nn.kneighbors(treated_sorted[["propensity_score"]])

    used_control = set()
    matched_treated_idx = []
    matched_control_idx = []

    for row_i, t_idx in enumerate(treated_sorted.index):
        for dist, pos in zip(distances[row_i], positions[row_i]):
            c_idx = control.index[pos]
            if c_idx in used_control:
                continue
            if dist <= caliper:
                matched_treated_idx.append(t_idx)
                matched_control_idx.append(c_idx)
                used_control.add(c_idx)
            break  # 가장 가까운 미사용 후보 하나만 시도(캘리퍼 초과면 해당 처리군은 매칭 실패)

    matched = pd.concat([df.loc[matched_treated_idx], df.loc[matched_control_idx]])
    logger.info(
        "PSM 매칭 결과: 처리군(AI 사용) %d명 중 %d명 매칭 성공 (caliper=%.3f)",
        len(treated), len(matched_treated_idx), caliper,
    )
    return matched


def run_psm_analysis(df: pd.DataFrame, value_col: str = TARGET_SALARY_USD) -> dict:
    """PSM 매칭 전/후 연봉(또는 지정 변수) 차이를 비교해 선택 편향 통제 효과를 확인한다."""
    logger.info("PSM(성향점수매칭) 분석 시작: 대상 변수=%s", value_col)

    needed_cols = ["AI_User", value_col] + PSM_CATEGORICAL + PSM_NUMERIC
    sub = df.dropna(subset=needed_cols).copy()

    if sub["AI_User"].nunique() < 2 or len(sub) < 20:
        logger.warning("PSM: 유효 표본이 부족하여 분석을 건너뜁니다.")
        return {"skipped": True, "reason": "표본 수 부족"}

    sub["propensity_score"] = estimate_propensity_scores(sub)
    matched = match_nearest_neighbor(sub)

    if len(matched) < 10:
        logger.warning("PSM: 매칭된 표본이 너무 적어(%d) 결과 해석에 유의해야 합니다.", len(matched))

    def _group_stats(data: pd.DataFrame) -> dict:
        g1 = data.loc[data["AI_User"] == 1, value_col]
        g0 = data.loc[data["AI_User"] == 0, value_col]
        if len(g1) < 2 or len(g0) < 2:
            return {"n_ai": len(g1), "n_non_ai": len(g0), "error": "표본 수 부족"}
        t_stat, p_value = scipy_stats.ttest_ind(g1, g0, equal_var=False)
        d = cohens_d(g1, g0)
        return {
            "n_ai": len(g1),
            "n_non_ai": len(g0),
            "mean_ai": round(float(g1.mean()), 3),
            "mean_non_ai": round(float(g0.mean()), 3),
            "diff": round(float(g1.mean() - g0.mean()), 3),
            "t_statistic": round(float(t_stat), 4),
            "p_value": float(p_value),
            "significant": bool(p_value < 0.05),
            "cohens_d": round(float(d), 4) if not np.isnan(d) else None,
            "effect_size_label": interpret_cohens_d(d),
        }

    before = _group_stats(sub)
    after = _group_stats(matched) if len(matched) >= 10 else {"error": "매칭 표본 부족"}

    result = {
        "skipped": False,
        "value_col": value_col,
        "n_total": len(sub),
        "n_matched_pairs": len(matched) // 2 if len(matched) else 0,
        "caliper": CALIPER,
        "control_variables": PSM_CATEGORICAL + PSM_NUMERIC,
        "before_matching": before,
        "after_matching": after,
    }
    logger.info("PSM 분석 완료: 매칭 전 diff=%.2f, 매칭 후 diff=%s",
                before.get("diff", float("nan")), after.get("diff", "N/A"))
    return result


if __name__ == "__main__":
    from src.etl import run_etl

    df, _ = run_etl()
    out = run_psm_analysis(df)
    print(out)
