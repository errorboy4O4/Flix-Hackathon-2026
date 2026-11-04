"""Validate and load CSV files, turning every failure into a chat-friendly message."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from chateda.config import Config

log = logging.getLogger("chateda.loader")

_ENCODINGS = ("utf-8-sig", "latin-1")
_DATE_SAMPLE = 20


class ChatEdaError(Exception):
    """An expected failure whose message is safe to show a non-engineer."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


def load_csv(path: str | Path, config: Config | None = None) -> pd.DataFrame:
    """Load a CSV after checking type, size, emptiness and shape.

    Raises ChatEdaError with a plain-language message for anything unusable.
    """
    config = config or Config.from_env()
    path = Path(path)
    _check_file(path, config)
    df = _read(path)
    if df.empty or df.shape[1] == 0:
        raise ChatEdaError("That CSV has headers but no data rows, so there is nothing to analyze.")
    if len(df) > config.max_rows:
        raise ChatEdaError(
            f"That file has {len(df):,} rows; the limit is {config.max_rows:,}. "
            "Try sending a smaller extract or a sample."
        )
    df = _parse_dates(df)
    log.info("loaded %s rows=%d cols=%d", path.name, len(df), df.shape[1])
    return df


def _check_file(path: Path, config: Config) -> None:
    if not path.is_file():
        raise ChatEdaError("I couldn't find that file. Please upload the CSV again.")
    if path.suffix.lower() not in {".csv", ".tsv", ".txt"}:
        raise ChatEdaError(
            f"I can only analyze CSV files, but this looks like a {path.suffix or 'unknown'} file."
        )
    size_mb = path.stat().st_size / 1_000_000
    if size_mb > config.max_mb:
        raise ChatEdaError(
            f"That file is {size_mb:.1f} MB; the limit is {config.max_mb:g} MB. "
            "Try a smaller extract."
        )
    if size_mb == 0:
        raise ChatEdaError("That file is empty.")
    with path.open("rb") as handle:
        if b"\x00" in handle.read(4096):
            raise ChatEdaError("That file looks binary, not like a text CSV.")


def _read(path: Path) -> pd.DataFrame:
    for encoding in _ENCODINGS:
        try:
            sep = _sniff_separator(path, encoding)
            return pd.read_csv(path, sep=sep, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError as exc:
            raise ChatEdaError("That file is empty.") from exc
        except (pd.errors.ParserError, csv.Error) as exc:
            log.warning("parse failure for %s: %s", path.name, exc)
            raise ChatEdaError(
                "I couldn't parse that file as a table - rows seem to have different "
                "numbers of columns. Could you check the export and resend it?"
            ) from exc
    raise ChatEdaError("I couldn't read the text encoding of that file. Try saving it as UTF-8.")


def _sniff_separator(path: Path, encoding: str) -> str:
    with path.open(encoding=encoding, newline="") as handle:
        sample = handle.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string columns that clearly hold dates into datetimes."""
    for name in df.columns:
        column = df[name]
        if not pd.api.types.is_string_dtype(column) and column.dtype != object:
            continue
        sample = column.dropna().astype(str).head(_DATE_SAMPLE)
        if sample.empty or not sample.str.match(r"^\d{4}-\d{2}-\d{2}").all():
            continue
        parsed = pd.to_datetime(column, errors="coerce")
        if parsed.notna().sum() >= 0.9 * column.notna().sum():
            df[name] = parsed
    return df
