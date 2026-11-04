import pandas as pd
import pytest

from chateda import ops
from chateda.loader import ChatEdaError


def test_breakdown_counts_rows(sample_df: pd.DataFrame):
    table = ops.breakdown(sample_df, "region")
    assert table["rows"].sum() == 600
    assert set(table.index) == {"North", "South", "East", "West"}


def test_breakdown_metric_is_case_insensitive(sample_df: pd.DataFrame):
    table = ops.breakdown(sample_df, "PLAN", "monthly_charges", "mean")
    assert table.index[0] == "Premium"
    assert table.columns[0] == "mean of monthly_charges"


def test_breakdown_bins_high_cardinality_numeric(sample_df: pd.DataFrame):
    table = ops.breakdown(sample_df, "tenure_months")
    assert 2 <= len(table) <= 5


def test_breakdown_rejects_non_numeric_metric(sample_df: pd.DataFrame):
    with pytest.raises(ChatEdaError, match="isn't numeric"):
        ops.breakdown(sample_df, "region", "plan")


def test_unknown_column_suggests_close_match(sample_df: pd.DataFrame):
    with pytest.raises(ChatEdaError, match="Did you mean: monthly_charges"):
        ops.breakdown(sample_df, "region", "monthly_charge")


def test_unknown_column_without_match_lists_columns(sample_df: pd.DataFrame):
    with pytest.raises(ChatEdaError, match="Columns:"):
        ops.require_column(sample_df, "zzzzzz")


def test_outlier_mask_finds_injected_values(sample_df: pd.DataFrame):
    mask, counts = ops.iqr_outlier_mask(sample_df)
    assert counts["monthly_charges"] >= 6
    assert (sample_df.loc[mask, "monthly_charges"] > 500).sum() == 6


def test_drivers_for_categorical_target(sample_df: pd.DataFrame):
    ranked = ops.drivers(sample_df, "churn")
    names = [d.column for d in ranked]
    assert "customer_id" not in names and "signup_date" not in names
    assert all(0 <= d.score <= 1 for d in ranked)
    assert ranked == sorted(ranked, key=lambda d: d.score, reverse=True)


def test_drivers_for_numeric_target(sample_df: pd.DataFrame):
    ranked = ops.drivers(sample_df, "total_charges")
    assert ranked[0].column in {"tenure_months", "monthly_charges"}
    assert ranked[0].score > 0.5


def test_drivers_rejects_constant_target():
    df = pd.DataFrame({"a": range(20), "t": [1] * 20})
    with pytest.raises(ChatEdaError, match="only one distinct value"):
        ops.drivers(df, "t")
