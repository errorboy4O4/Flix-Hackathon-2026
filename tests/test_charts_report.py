from pathlib import Path

import pandas as pd

from chateda import charts, ops, report
from chateda.profile import build_profile

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def assert_png(path: Path) -> None:
    assert path.exists() and path.read_bytes().startswith(PNG_MAGIC)


def test_overview_charts_are_valid_pngs_and_capped(sample_df: pd.DataFrame, tmp_path: Path):
    paths = charts.overview_charts(sample_df, build_profile(sample_df), tmp_path)
    assert len(paths) == 4
    for path in paths:
        assert_png(path)


def test_overview_skips_charts_that_do_not_apply(tmp_path: Path):
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
    paths = charts.overview_charts(df, build_profile(df), tmp_path)
    assert [p.name for p in paths] == ["distributions.png"]


def test_bar_chart(tmp_path: Path):
    assert_png(charts.bar_chart(["a", "b"], [1.0, 2.0], "t", "x", tmp_path / "bar.png"))


def test_overview_markdown(sample_df: pd.DataFrame):
    text = report.overview_markdown("sample.csv", build_profile(sample_df))
    assert "600 rows x 9 columns" in text
    assert "total_charges 7.5%" in text
    assert "| monthly_charges |" in text
    assert "What stands out" in text


def test_overview_markdown_reports_removed_outliers(sample_df: pd.DataFrame):
    text = report.overview_markdown("s.csv", build_profile(sample_df), {"monthly_charges": 6})
    assert "monthly_charges: 6" in text


def test_overview_markdown_no_missing():
    df = pd.DataFrame({"x": [1, 2, 3]})
    assert "No missing values." in report.overview_markdown("a.csv", build_profile(df))


def test_breakdown_and_drivers_markdown(sample_df: pd.DataFrame):
    table = ops.breakdown(sample_df, "plan", "monthly_charges")
    text = report.breakdown_markdown("plan", table)
    assert "| Premium |" in text
    drivers = report.drivers_markdown("churn", ops.drivers(sample_df, "churn"))
    assert drivers.startswith("**What relates most to churn**")
    assert "not causation" in drivers


def test_drivers_markdown_empty():
    assert "couldn't find any usable" in report.drivers_markdown("t", [])
