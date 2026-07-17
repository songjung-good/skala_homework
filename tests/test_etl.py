import numpy as np
import pandas as pd

from src.etl import _years_to_numeric, clean_data, engineer_features


def test_years_to_numeric_maps_known_text_values():
    s = pd.Series(["Less than 1 year", "More than 50 years", "5", None])
    result = _years_to_numeric(s)
    assert result.iloc[0] == 0.5
    assert result.iloc[1] == 51
    assert result.iloc[2] == 5
    assert pd.isna(result.iloc[3])


def test_clean_data_removes_exact_duplicate_rows(raw_survey_df):
    _, stats = clean_data(raw_survey_df)
    assert stats["duplicates_removed"] == 1


def test_clean_data_drops_rows_with_missing_ai_select(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    assert cleaned["AISelect"].isna().sum() == 0


def test_clean_data_treats_non_positive_salary_as_missing(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    row = cleaned.loc[cleaned["ResponseId"] == 5]
    assert row["ConvertedCompYearly"].isna().all()


def test_clean_data_clips_salary_within_reported_bounds(raw_survey_df):
    cleaned, stats = clean_data(raw_survey_df)
    low, high = stats["salary_clip_bounds"]
    valid = cleaned["ConvertedCompYearly"].dropna()
    assert valid.max() <= high
    assert valid.min() >= low


def test_clean_data_converts_years_code_pro_to_numeric_dtype(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    assert pd.api.types.is_numeric_dtype(cleaned["YearsCodePro"])


def test_engineer_features_creates_binary_ai_user_column(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    features = engineer_features(cleaned)
    assert set(features["AI_User"].unique()) <= {0, 1}
    assert (features.loc[features["AISelect"] == "Yes", "AI_User"] == 1).all()
    assert (features.loc[features["AISelect"] != "Yes", "AI_User"] == 0).all()


def test_engineer_features_relabels_negative_ai_select_values(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    features = engineer_features(cleaned)
    assert "No, and I don't plan to" not in features["AISelect_clean"].values
    assert "No" in features["AISelect_clean"].values


def test_engineer_features_adds_log_transformed_salary(raw_survey_df):
    cleaned, _ = clean_data(raw_survey_df)
    features = engineer_features(cleaned)
    non_na = features.dropna(subset=["ConvertedCompYearly"])
    np.testing.assert_allclose(
        non_na["Salary_log"], np.log1p(non_na["ConvertedCompYearly"]), rtol=1e-9
    )
