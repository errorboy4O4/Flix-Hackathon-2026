"""Render analysis results as chat-ready markdown."""

from __future__ import annotations

import pandas as pd

from chateda.ops import Driver
from chateda.profile import Profile

_TOP_DRIVERS = 8


def overview_markdown(name: str, profile: Profile, removed: dict[str, int] | None = None) -> str:
    """Summary of a dataset: shape, types, missing values, stats, insights."""
    kinds = _count_kinds(profile)
    lines = [
        f"**{name}** - {profile.rows:,} rows x {profile.cols} columns ({kinds})",
        "",
    ]
    if removed is not None:
        lines += [_removed_line(removed), ""]
    lines += [_missing_line(profile), ""]
    if not profile.describe.empty:
        lines += ["**Key statistics**", _stats_table(profile.describe), ""]
    if profile.insights:
        lines += ["**What stands out**"] + [f"- {note}" for note in profile.insights]
    return "\n".join(lines).strip()


def breakdown_markdown(by: str, table: pd.DataFrame, removed: dict[str, int] | None = None) -> str:
    """Markdown table for a group breakdown."""
    header = f"**Breakdown by {by}**" + _removed_suffix(removed)
    rows = [f"| {by} | " + " | ".join(table.columns) + " |", "|---|" + "---|" * len(table.columns)]
    for label, row in table.iterrows():
        cells = " | ".join(_fmt(v) for v in row)
        rows.append(f"| {label} | {cells} |")
    return "\n".join([header, "", *rows])


def drivers_markdown(target: str, ranked: list[Driver], removed: dict[str, int] | None = None) -> str:
    """Ranked list of columns most associated with the target."""
    if not ranked:
        return f"I couldn't find any usable columns to compare with '{target}'."
    top = ranked[:_TOP_DRIVERS]
    lines = [f"**What relates most to {target}** (0 = unrelated, 1 = perfectly related)" + _removed_suffix(removed), ""]
    lines += [f"{i}. `{d.column}` - {d.score:.2f} ({d.method})" for i, d in enumerate(top, 1)]
    lines += ["", "_Association is not causation; use this to decide where to look next._"]
    return "\n".join(lines)


def _removed_line(removed: dict[str, int]) -> str:
    detail = ", ".join(f"{c}: {n}" for c, n in removed.items()) or "none found"
    return f"Outliers removed before analysis (1.5xIQR rule): {detail}."


def _removed_suffix(removed: dict[str, int] | None) -> str:
    return "" if removed is None else f"\n\n_{_removed_line(removed)}_"


def _count_kinds(profile: Profile) -> str:
    counts: dict[str, int] = {}
    for kind in profile.kinds.values():
        counts[kind] = counts.get(kind, 0) + 1
    return ", ".join(f"{n} {kind}" for kind, n in counts.items())


def _missing_line(profile: Profile) -> str:
    if not profile.missing_pct:
        return "No missing values."
    items = ", ".join(f"{c} {p:g}%" for c, p in profile.missing_pct.items())
    return f"**Missing values:** {items}."


def _stats_table(describe: pd.DataFrame) -> str:
    rows = ["| column | mean | median | min | max |", "|---|---|---|---|---|"]
    for column, row in describe.iterrows():
        rows.append(
            f"| {column} | {_fmt(row['mean'])} | {_fmt(row['50%'])} | {_fmt(row['min'])} | {_fmt(row['max'])} |"
        )
    return "\n".join(rows)


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    return f"{value:,}" if isinstance(value, int) else str(value)
