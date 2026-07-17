"""
model.py
--------
머신러닝 파이프라인.

목표: AISelect(AI 사용 여부)를 포함한 feature 로 "고연봉 여부"(중앙값 초과)를 분류 예측하고,
     AISelect 가 얼마나 중요한 예측 변수인지 Feature Importance 로 확인한다.

Pipeline: sklearn.pipeline.Pipeline(
            ColumnTransformer(OneHotEncoder + StandardScaler) -> DecisionTree / RandomForest
          )
평가: Accuracy, Precision, Recall, F1-score, Confusion Matrix
저장: joblib.dump(pipeline, MODEL_PATH)  # 전처리+모델이 하나로 묶인 Pipeline 객체를 통째로 저장

다중공선성(Multicollinearity) 처리
----------------------------------
EDA 단계 상관관계 분석 결과 YearsCodePro(개발 경력)와 WorkExp(총 업무 경력)의
피어슨 상관계수가 0.9 이상으로 극도로 높게 나타난다(사실상 같은 정보를 중복 측정).
두 변수를 동시에 트리 기반 모델에 투입하면 변수 중요도가 두 변수로 인위적으로
분산되어 실제 중요도가 과소평가되고 해석력이 저하될 수 있다.
-> 결측치가 더 적은 YearsCodePro(개발 전문 경력, "개발자 시장 가치" 분석 목적에
   더 부합)만 남기고 WorkExp는 모델 입력에서 제외한다. 제외된 변수는
   COLLINEAR_FEATURES_DROPPED 에 기록하여 report.md 에 근거와 함께 명시한다.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.utils import MODEL_PATH, RANDOM_STATE, TARGET_SALARY_USD, get_logger

logger = get_logger(__name__)

CATEGORICAL_FEATURES = ["AISelect", "DevType", "Country", "OrgSize"]
# 다중공선성 처리: WorkExp 는 YearsCodePro 와 상관계수 0.9+ 로 중복 정보이므로 모델 입력에서 제외
NUMERIC_FEATURES = ["YearsCodePro"]
COLLINEAR_FEATURES_DROPPED = {
    "WorkExp": "YearsCodePro 와 피어슨 상관계수 0.9 이상 (다중공선성) -> 모델 입력에서 제외, "
    "YearsCodePro(개발 전문 경력)를 대표 변수로 채택"
}
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def build_pipeline(model_type: str = "random_forest") -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    if model_type == "decision_tree":
        clf = DecisionTreeClassifier(max_depth=6, random_state=RANDOM_STATE, class_weight="balanced")
    else:
        clf = RandomForestClassifier(
            n_estimators=300, max_depth=8, random_state=RANDOM_STATE, class_weight="balanced", n_jobs=-1
        )

    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])


def prepare_ml_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """모델 입력용 X, y 를 구성한다. y = 연봉이 중앙값을 초과하는지 여부(0/1)."""
    sub = df.dropna(subset=[TARGET_SALARY_USD] + FEATURES).copy()
    median_salary = sub[TARGET_SALARY_USD].median()
    sub["HighEarner"] = (sub[TARGET_SALARY_USD] > median_salary).astype(int)

    X = sub[FEATURES]
    y = sub["HighEarner"]
    logger.info(
        "ML 데이터셋 구성: %d행, 중앙값 연봉=%.0f USD, 고연봉 비율=%.1f%%",
        len(sub), median_salary, y.mean() * 100,
    )
    return X, y, median_salary


def train_and_evaluate(X: pd.DataFrame, y: pd.Series, model_type: str = "random_forest") -> dict:
    if len(X) < 20 or y.nunique() < 2:
        logger.warning("표본 수가 부족하여 모델 학습을 신뢰하기 어렵습니다 (n=%d).", len(X))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y if y.nunique() > 1 else None
    )

    # Pipeline: 전처리(ColumnTransformer: OneHotEncoder + StandardScaler)와
    # 분류기(classifier)를 하나의 sklearn.pipeline.Pipeline 객체로 묶어
    # fit/predict 시 데이터 누수(data leakage) 없이 학습/추론이 일관되게 처리되도록 한다.
    pipeline = build_pipeline(model_type)
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    cm = confusion_matrix(y_test, y_pred)
    if cm.size == 4:
        tn, fp, fn, tp = (int(v) for v in cm.ravel())
    else:
        tn = fp = fn = tp = None

    metrics = {
        "model_type": model_type,
        "pipeline_steps": [name for name, _ in pipeline.steps],
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }
    logger.info(
        "모델 평가 (%s): Accuracy=%.3f, F1=%.3f, ConfusionMatrix=%s",
        model_type, metrics["accuracy"], metrics["f1"], cm.tolist(),
    )

    feature_importance = extract_feature_importance(pipeline)

    # joblib 을 이용해 전처리+모델이 결합된 Pipeline 객체 전체를 저장
    # (추론 시 원본 데이터를 그대로 넣으면 저장된 전처리 로직이 동일하게 재현됨)
    joblib.dump(pipeline, MODEL_PATH)
    metrics["model_saved_path"] = str(MODEL_PATH)
    logger.info("모델 저장 완료 (joblib.dump): %s", MODEL_PATH)

    return {"pipeline": pipeline, "metrics": metrics, "feature_importance": feature_importance}


def extract_feature_importance(pipeline: Pipeline) -> pd.DataFrame:
    preprocessor = pipeline.named_steps["preprocessor"]
    clf = pipeline.named_steps["classifier"]

    cat_names = preprocessor.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
    all_names = list(cat_names) + NUMERIC_FEATURES

    importances = clf.feature_importances_
    imp_df = pd.DataFrame({"feature": all_names, "importance": importances})
    imp_df = imp_df.sort_values("importance", ascending=False).reset_index(drop=True)

    # AISelect 관련 원핫 피처들의 중요도 합계 (원 변수 단위 중요도)
    ai_importance = imp_df.loc[imp_df["feature"].str.startswith("AISelect_"), "importance"].sum()
    imp_df.attrs["AISelect_total_importance"] = ai_importance

    # 원 변수(raw variable) 단위로 그룹핑한 중요도 랭킹도 함께 계산
    def _raw_var(feat_name: str) -> str:
        for cat in CATEGORICAL_FEATURES:
            if feat_name.startswith(cat + "_"):
                return cat
        return feat_name

    imp_df["raw_variable"] = imp_df["feature"].apply(_raw_var)
    grouped = imp_df.groupby("raw_variable")["importance"].sum().sort_values(ascending=False)
    imp_df.attrs["grouped_importance"] = grouped

    ranked_vars = list(grouped.index)
    imp_df.attrs["AISelect_rank_among_raw_vars"] = (
        ranked_vars.index("AISelect") + 1 if "AISelect" in ranked_vars else None
    )

    return imp_df


def run_modeling(df: pd.DataFrame, model_type: str = "random_forest") -> dict:
    logger.info("머신러닝 파이프라인 시작 (%s)", model_type)
    X, y, median_salary = prepare_ml_dataset(df)
    result = train_and_evaluate(X, y, model_type=model_type)
    result["median_salary"] = median_salary
    result["n_samples"] = len(X)
    result["collinear_features_dropped"] = COLLINEAR_FEATURES_DROPPED
    return result


if __name__ == "__main__":
    from src.etl import run_etl

    df, _ = run_etl()
    out = run_modeling(df)
    print(out["metrics"])
    print(out["feature_importance"].head(10))
