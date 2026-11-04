import pandas as pd

from chateda.profile import build_profile, categorical_columns, column_kind, numeric_columns


def test_column_kinds(sample_df: pd.DataFrame):
    profile = build_profile(sample_df)
    assert profile.kinds["tenure_months"] == "numeric"
    assert profile.kinds["signup_date"] == "datetime"
    assert profile.kinds["region"] == "categorical"
    assert profile.kinds["customer_id"] == "text"


def test_shape_and_missing(sample_df: pd.DataFrame):
    profile = build_profile(sample_df)
    assert (profile.rows, profile.cols) == (600, 9)
    assert profile.missing_pct == {"total_charges": 7.5}


def test_describe_and_correlations(sample_df: pd.DataFrame):
    profile = build_profile(sample_df)
    assert "monthly_charges" in profile.describe.index
    assert profile.correlations is not None
    a, b, r = profile.top_correlations[0]
    assert {a, b} == {"tenure_months", "total_charges"} and r > 0.5


def test_insights_flag_skew_and_identifier(sample_df: pd.DataFrame):
    text = " ".join(build_profile(sample_df).insights)
    assert "'monthly_charges' is heavily skewed" in text
    assert "'customer_id' looks like an identifier" in text


def test_single_numeric_column_has_no_correlations():
    profile = build_profile(pd.DataFrame({"x": [1, 2, 3, 4]}))
    assert profile.correlations is None and profile.top_correlations == []


def test_bool_is_categorical():
    assert column_kind(pd.Series([True, False, True])) == "categorical"


def test_column_helpers(sample_df: pd.DataFrame):
    assert "plan" in categorical_columns(sample_df)
    assert "plan" not in numeric_columns(sample_df)
