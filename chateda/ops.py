"""Follow-up analyses teammates ask for in-thread: breakdowns, outliers, drivers."""

from __future__ import annotations

import difflib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from chateda.loader import ChatEdaError
from chateda.profile import categorical_columns, column_kind, numeric_columns

MAX_GROUPS = 15
BIN_THRESHOLD = 15
VALID_AGGS = ("mean", "median", "sum", "count")


@dataclass
class Driver:
    """How strongly one column is associated with the target (0 to 1)."""

    column: str
    score: float
    method: str


def require_column(df: pd.DataFrame, name: str) -> str:
    """Return the matching column name, tolerating case; suggest near misses."""
    lookup = {c.lower(): c for c in df.columns}
    if name.lower() in lookup:
        return lookup[name.lower()]
    close = difflib.get_close_matches(name, list(df.columns), n=3, cutoff=0.5)
    hint = f" Did you mean: {', '.join(close)}?" if close else f" Columns: {', '.join(df.columns)}."
    raise ChatEdaError(f"I don't see a column called '{name}'.{hint}")


def breakdown(df: pd.DataFrame, by: str, metric: str | None = None, agg: str = "mean") -> pd.DataFrame:
    """Group rows by a column and summarize a metric (or count rows)."""
    by = require_column(df, by)
    if agg not in VALID_AGGS:
        raise ChatEdaError(f"I can summarize with: {', '.join(VALID_AGGS)}.")
    groups = _group_labels(df[by])
    if metric is None or agg == "count":
        result = groups.value_counts().rename("rows").to_frame()
    else:
        metric = require_column(df, metric)
        if column_kind(df[metric]) != "numeric":
            raise ChatEdaError(f"'{metric}' isn't numeric, so I can't take its {agg}.")
        result = df[metric].groupby(groups, observed=True).agg(agg).rename(f"{agg} of {metric}").to_frame()
        result["rows"] = groups.value_counts()
    return result.sort_values(result.columns[0], ascending=False).head(MAX_GROUPS)


def _group_labels(series: pd.Series) -> pd.Series:
    if column_kind(series) == "numeric" and series.nunique() > BIN_THRESHOLD:
        return pd.qcut(series, q=5, duplicates="drop").astype(str)
    return series.astype(str)


def iqr_outlier_mask(df: pd.DataFrame, k: float = 1.5) -> tuple[pd.Series, dict[str, int]]:
    """Flag rows outside Tukey fences in any numeric column.

    Returns the per-row mask and the number of outliers found per column.
    """
    mask = pd.Series(False, index=df.index)
    counts: dict[str, int] = {}
    for column in numeric_columns(df):
        q1, q3 = df[column].quantile([0.25, 0.75])
        spread = q3 - q1
        flagged = (df[column] < q1 - k * spread) | (df[column] > q3 + k * spread)
        if flagged.any():
            counts[column] = int(flagged.sum())
            mask |= flagged
    return mask, counts


def drivers(df: pd.DataFrame, target: str) -> list[Driver]:
    """Rank other columns by how strongly they relate to the target."""
    target = require_column(df, target)
    if df[target].dropna().nunique() < 2:
        raise ChatEdaError(f"'{target}' has only one distinct value, so nothing can predict it.")
    target_is_numeric = column_kind(df[target]) == "numeric"
    scores = []
    for column in df.columns.drop(target):
        kind = column_kind(df[column])
        if kind in ("text", "datetime"):
            continue
        scores.append(_score(df, column, kind, target, target_is_numeric))
    return sorted((s for s in scores if s), key=lambda d: d.score, reverse=True)


def _score(df: pd.DataFrame, column: str, kind: str, target: str, target_numeric: bool) -> Driver | None:
    pair = df[[column, target]].dropna()
    if len(pair) < 10:
        return None
    if kind == "numeric" and target_numeric:
        return Driver(column, abs(float(pair[column].corr(pair[target]))), "correlation")
    if kind == "numeric":
        return Driver(column, _correlation_ratio(pair[target].astype(str), pair[column]), "group differences")
    if target_numeric:
        return Driver(column, _correlation_ratio(pair[column].astype(str), pair[target]), "group differences")
    return Driver(column, _cramers_v(pair[column].astype(str), pair[target].astype(str)), "association")


def _correlation_ratio(groups: pd.Series, values: pd.Series) -> float:
    """Share of the variance in `values` explained by `groups` (eta, 0 to 1)."""
    total = ((values - values.mean()) ** 2).sum()
    if total == 0:
        return 0.0
    means = values.groupby(groups).transform("mean")
    return float(np.sqrt(((means - values.mean()) ** 2).sum() / total))


def _cramers_v(a: pd.Series, b: pd.Series) -> float:
    table = pd.crosstab(a, b)
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / table.values.sum()
    chi2 = ((table.values - expected) ** 2 / expected).sum()
    dof = min(table.shape) - 1
    return float(np.sqrt(chi2 / (table.values.sum() * dof))) if dof > 0 else 0.0
