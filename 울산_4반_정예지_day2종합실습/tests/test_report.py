import pandas as pd

from src.report import _df_to_markdown


def test_df_to_markdown_rounds_values():
    df = pd.DataFrame({"a": [1.23456, 2.34567]}, index=["x", "y"])
    md = _df_to_markdown(df)
    assert "1.235" in md
    assert "2.346" in md


def test_df_to_markdown_returns_non_empty_string():
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    md = _df_to_markdown(df)
    assert isinstance(md, str)
    assert md.strip()
