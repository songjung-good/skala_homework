import pytest
from sklearn.pipeline import Pipeline

import src.model as model_module
from src.model import FEATURES, build_pipeline, extract_feature_importance, prepare_ml_dataset, train_and_evaluate


def test_build_pipeline_defaults_to_random_forest():
    pipeline = build_pipeline()
    assert isinstance(pipeline, Pipeline)
    assert type(pipeline.named_steps["classifier"]).__name__ == "RandomForestClassifier"


def test_build_pipeline_supports_decision_tree_variant():
    pipeline = build_pipeline("decision_tree")
    assert type(pipeline.named_steps["classifier"]).__name__ == "DecisionTreeClassifier"


def test_prepare_ml_dataset_builds_binary_high_earner_label(analysis_df):
    X, y, median_salary = prepare_ml_dataset(analysis_df)
    assert set(X.columns) == set(FEATURES)
    assert set(y.unique()) <= {0, 1}
    assert median_salary == pytest.approx(analysis_df["ConvertedCompYearly"].median())


def test_train_and_evaluate_returns_metrics_and_saves_model(analysis_df, tmp_path, monkeypatch):
    monkeypatch.setattr(model_module, "MODEL_PATH", tmp_path / "model.pkl")

    X, y, _ = prepare_ml_dataset(analysis_df)
    result = train_and_evaluate(X, y, model_type="decision_tree")

    metrics = result["metrics"]
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["n_train"] + metrics["n_test"] == len(X)
    assert (tmp_path / "model.pkl").exists()


def test_extract_feature_importance_sums_to_one(analysis_df, tmp_path, monkeypatch):
    monkeypatch.setattr(model_module, "MODEL_PATH", tmp_path / "model.pkl")

    X, y, _ = prepare_ml_dataset(analysis_df)
    result = train_and_evaluate(X, y, model_type="decision_tree")
    imp_df = extract_feature_importance(result["pipeline"])

    assert imp_df["importance"].sum() == pytest.approx(1.0, abs=1e-6)
    assert "AISelect_total_importance" in imp_df.attrs
    assert "grouped_importance" in imp_df.attrs
