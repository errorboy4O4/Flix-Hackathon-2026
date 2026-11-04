"""PNG chart generation. Every function writes one file and returns its path."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from chateda.profile import Profile, categorical_columns, numeric_columns  # noqa: E402

MAX_HIST_COLUMNS = 6
MAX_CATEGORY_BARS = 12
MAX_CHARTS = 4
_COLOR = "#2f6fdb"
_DPI = 110


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=_DPI)
    plt.close(fig)
    return path


def missing_chart(profile: Profile, out: Path) -> Path:
    """Horizontal bars of the percent missing per affected column."""
    series = pd.Series(profile.missing_pct).sort_values()
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.45 * len(series) + 1)))
    ax.barh(series.index, series.values, color=_COLOR)
    ax.set_xlabel("% of rows missing")
    ax.set_title("Missing values by column")
    return _save(fig, out / "missing_values.png")


def distributions_chart(df: pd.DataFrame, out: Path) -> Path:
    """Grid of histograms for the first numeric columns."""
    columns = numeric_columns(df)[:MAX_HIST_COLUMNS]
    ncols = min(3, len(columns))
    nrows = -(-len(columns) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows), squeeze=False)
    for ax, column in zip(axes.flat, columns):
        ax.hist(df[column].dropna(), bins=30, color=_COLOR)
        ax.set_title(column)
    for ax in list(axes.flat)[len(columns):]:
        ax.set_visible(False)
    fig.suptitle("Distributions of numeric columns")
    return _save(fig, out / "distributions.png")


def correlation_chart(profile: Profile, out: Path) -> Path:
    """Annotated heatmap of the numeric correlation matrix."""
    corr = profile.correlations
    size = max(5, 0.9 * len(corr))
    fig, ax = plt.subplots(figsize=(size + 1, size))
    image = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr)), corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, shrink=0.8)
    ax.set_title("Correlation between numeric columns")
    return _save(fig, out / "correlations.png")


def categories_chart(df: pd.DataFrame, out: Path) -> Path:
    """Bar charts of value counts for the first categorical columns."""
    columns = categorical_columns(df)[:4]
    fig, axes = plt.subplots(1, len(columns), figsize=(4.2 * len(columns), 3.5), squeeze=False)
    for ax, column in zip(axes[0], columns):
        counts = df[column].value_counts().head(MAX_CATEGORY_BARS)
        ax.bar(counts.index.astype(str), counts.values, color=_COLOR)
        ax.set_title(column)
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Most common values")
    return _save(fig, out / "categories.png")


def bar_chart(labels: list[str], values: list[float], title: str, xlabel: str, path: Path) -> Path:
    """Generic horizontal bar chart used by follow-up analyses."""
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.45 * len(labels) + 1)))
    ax.barh(labels[::-1], values[::-1], color=_COLOR)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    return _save(fig, path)


def overview_charts(df: pd.DataFrame, profile: Profile, out: Path) -> list[Path]:
    """Generate up to MAX_CHARTS charts that are meaningful for this dataset."""
    paths: list[Path] = []
    if numeric_columns(df):
        paths.append(distributions_chart(df, out))
    if profile.correlations is not None:
        paths.append(correlation_chart(profile, out))
    if categorical_columns(df):
        paths.append(categories_chart(df, out))
    if profile.missing_pct:
        paths.append(missing_chart(profile, out))
    return paths[:MAX_CHARTS]
