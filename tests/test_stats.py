import numpy as np
import pandas as pd
import pytest

from src.stats import cohens_d, correlation_matrix, independent_ttest, interpret_cohens_d


def test_cohens_d_is_zero_when_means_are_equal():
    a = pd.Series([1, 2, 3, 4, 5])
    b = pd.Series([1, 2, 3, 4, 5])
    assert cohens_d(a, b) == pytest.approx(0.0)


def test_cohens_d_is_positive_when_group_a_has_higher_mean():
    a = pd.Series([10, 11, 12, 13])
    b = pd.Series([1, 2, 3, 4])
    assert cohens_d(a, b) > 0


def test_cohens_d_nan_with_fewer_than_two_samples():
    a = pd.Series([1])
    b = pd.Series([1, 2, 3])
    assert np.isnan(cohens_d(a, b))


def test_cohens_d_nan_when_pooled_std_is_zero():
    a = pd.Series([5, 5, 5])
    b = pd.Series([5, 5, 5])
    assert np.isnan(cohens_d(a, b))


@pytest.mark.parametrize(
    "d, label",
    [
        (0.1, "무시할 수 있는 수준 (negligible)"),
        (0.3, "작은 효과 (small)"),
        (0.6, "중간 효과 (medium)"),
        (1.0, "큰 효과 (large)"),
        (-0.9, "큰 효과 (large)"),
    ],
)
def test_interpret_cohens_d_thresholds(d, label):
    assert interpret_cohens_d(d) == label


def test_interpret_cohens_d_returns_error_label_for_nan():
    assert interpret_cohens_d(float("nan")) == "계산 불가"


def test_independent_ttest_detects_significant_difference():
    df = pd.DataFrame(
        {
            "salary": [50000, 52000, 51000, 49000, 90000, 92000, 91000, 89000],
            "AI_User": [0, 0, 0, 0, 1, 1, 1, 1],
        }
    )
    result = independent_ttest(df, "salary")
    assert result["n_ai"] == 4
    assert result["n_non_ai"] == 4
    assert result["mean_ai"] > result["mean_non_ai"]
    assert result["significant"] is True
    assert result["p_value"] < 0.05


def test_independent_ttest_reports_error_on_insufficient_sample():
    df = pd.DataFrame({"salary": [50000], "AI_User": [1]})
    result = independent_ttest(df, "salary")
    assert "error" in result


def test_correlation_matrix_diagonal_is_one(analysis_df):
    corr = correlation_matrix(analysis_df)
    assert np.allclose(np.diag(corr.values), 1.0)
    assert "AI_User" in corr.columns
