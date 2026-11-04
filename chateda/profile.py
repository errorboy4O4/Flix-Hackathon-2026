"""Dataset profiling: shape, column kinds, missing values, statistics, insights."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

HIGH_CARDINALITY = 50
STRONG_CORRELATION = 0.5
HIGH_MISSING_PCT = 20.0


@dataclass
class Profile:
    """Everything the report and charts need to describe one dataset."""

    rows: int
    cols: int
    duplicates: int
    kinds: dict[str, str]
    missing_pct: dict[str, float]
    describe: pd.DataFrame
    correlations: pd.DataFrame | None
    top_correlations: list[tuple[str, str, float]]
    insights: list[str] = field(default_factory=list)


def column_kind(series: pd.Series) -> str:
    """Classify a column as numeric, datetime, categorical or text."""
    if pd.api.types.is_bool_dtype(series):
        return "categorical"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    return "text" if series.nunique() > HIGH_CARDINALITY else "categorical"


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """Names of numeric columns, in order."""
    return [c for c in df.columns if column_kind(df[c]) == "numeric"]


def categorical_columns(df: pd.DataFrame) -> list[str]:
    """Names of low-cardinality non-numeric columns, in order."""
    return [c for c in df.columns if column_kind(df[c]) == "categorical"]


def build_profile(df: pd.DataFrame) -> Profile:
    """Compute the full profile for a dataframe."""
    kinds = {c: column_kind(df[c]) for c in df.columns}
    numeric = [c for c, k in kinds.items() if k == "numeric"]
    correlations = df[numeric].corr() if len(numeric) >= 2 else None
    profile = Profile(
        rows=len(df),
        cols=df.shape[1],
        duplicates=int(df.duplicated().sum()),
        kinds=kinds,
        missing_pct=_missing_pct(df),
        describe=df[numeric].describe().T if numeric else pd.DataFrame(),
        correlations=correlations,
        top_correlations=_top_correlations(correlations),
    )
    profile.insights = _insights(df, profile)
    return profile


def _missing_pct(df: pd.DataFrame) -> dict[str, float]:
    pct = df.isna().mean() * 100
    return {c: round(float(v), 1) for c, v in pct.items() if v > 0}


def _top_correlations(corr: pd.DataFrame | None, limit: int = 5) -> list[tuple[str, str, float]]:
    if corr is None:
        return []
    names = list(corr.columns)
    pairs = [
        (a, b, float(corr.loc[a, b]))
        for i, a in enumerate(names)
        for b in names[i + 1 :]
        if pd.notna(corr.loc[a, b])
    ]
    return sorted(pairs, key=lambda p: abs(p[2]), reverse=True)[:limit]


def _insights(df: pd.DataFrame, profile: Profile) -> list[str]:
    notes: list[str] = []
    for column, pct in profile.missing_pct.items():
        if pct >= HIGH_MISSING_PCT:
            notes.append(f"'{column}' is missing in {pct:g}% of rows - treat it with caution.")
    if profile.duplicates:
        notes.append(f"{profile.duplicates:,} rows are exact duplicates.")
    for a, b, r in profile.top_correlations:
        if abs(r) >= STRONG_CORRELATION:
            direction = "rise together" if r > 0 else "move in opposite directions"
            notes.append(f"'{a}' and '{b}' {direction} (correlation {r:+.2f}).")
    notes.extend(_skew_notes(df, profile))
    notes.extend(f"'{c}' looks like an identifier (almost every value is unique)."
                 for c, k in profile.kinds.items() if k == "text" and df[c].nunique() > 0.9 * len(df))
    return notes


def _skew_notes(df: pd.DataFrame, profile: Profile) -> list[str]:
    notes = []
    for column in profile.describe.index:
        series = df[column].dropna()
        if len(series) > 10 and abs(float(series.skew())) > 1.5:
            notes.append(f"'{column}' is heavily skewed; the median is more representative than the mean.")
    return notes
