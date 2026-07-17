import pandas as pd

from src.causal import estimate_propensity_scores, match_nearest_neighbor, run_psm_analysis


def test_estimate_propensity_scores_returns_valid_probabilities(analysis_df):
    scores = estimate_propensity_scores(analysis_df)
    assert len(scores) == len(analysis_df)
    assert scores.between(0, 1).all()


def test_match_nearest_neighbor_produces_balanced_pairs(analysis_df):
    df = analysis_df.copy()
    df["propensity_score"] = estimate_propensity_scores(df)
    matched = match_nearest_neighbor(df, caliper=1.0)  # 넉넉한 caliper로 매칭 보장

    n_treated_matched = (matched["AI_User"] == 1).sum()
    n_control_matched = (matched["AI_User"] == 0).sum()
    assert n_treated_matched == n_control_matched
    assert n_treated_matched > 0


def test_match_nearest_neighbor_returns_empty_when_one_group_missing(analysis_df):
    only_treated = analysis_df[analysis_df["AI_User"] == 1].copy()
    only_treated["propensity_score"] = 0.5
    matched = match_nearest_neighbor(only_treated)
    assert len(matched) == 0


def test_run_psm_analysis_returns_before_and_after_comparison(analysis_df):
    result = run_psm_analysis(analysis_df)
    assert result["skipped"] is False
    assert "before_matching" in result
    assert "after_matching" in result
    assert result["n_matched_pairs"] >= 0


def test_run_psm_analysis_skips_on_insufficient_sample():
    tiny_df = pd.DataFrame(
        {
            "AI_User": [1, 0],
            "ConvertedCompYearly": [50000, 40000],
            "Country": ["USA", "USA"],
            "DevType": ["Backend", "Backend"],
            "OrgSize": ["1-9", "1-9"],
            "YearsCodePro": [3, 4],
        }
    )
    result = run_psm_analysis(tiny_df)
    assert result["skipped"] is True
