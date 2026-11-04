from pathlib import Path

import pandas as pd
import pytest

from chateda.config import Config
from chateda.loader import ChatEdaError, load_csv


def write(tmp_path: Path, name: str, content: bytes | str) -> Path:
    path = tmp_path / name
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    return path


def message(path: Path, config: Config | None = None) -> str:
    with pytest.raises(ChatEdaError) as info:
        load_csv(path, config)
    return info.value.user_message


def test_loads_sample_and_parses_dates(sample_df: pd.DataFrame):
    assert sample_df.shape == (600, 9)
    assert pd.api.types.is_datetime64_any_dtype(sample_df["signup_date"])


def test_rejects_missing_file(tmp_path: Path):
    assert "couldn't find" in message(tmp_path / "nope.csv")


def test_rejects_non_csv_extension(tmp_path: Path):
    assert "only analyze CSV" in message(write(tmp_path, "report.pdf", "%PDF"))


def test_rejects_empty_file(tmp_path: Path):
    assert "empty" in message(write(tmp_path, "a.csv", ""))


def test_rejects_headers_only(tmp_path: Path):
    assert "no data rows" in message(write(tmp_path, "a.csv", "a,b\n"))


def test_rejects_binary(tmp_path: Path):
    assert "binary" in message(write(tmp_path, "a.csv", b"a,b\n\x00\x01"))


def test_rejects_oversize_file(tmp_path: Path):
    path = write(tmp_path, "a.csv", "a,b\n" + "1,2\n" * 1000)
    assert "limit is 0.001 MB" in message(path, Config(max_mb=0.001))


def test_rejects_too_many_rows(tmp_path: Path):
    path = write(tmp_path, "a.csv", "a\n" + "1\n" * 20)
    assert "20 rows" in message(path, Config(max_rows=10))


def test_rejects_ragged_rows(tmp_path: Path):
    path = write(tmp_path, "a.csv", "a,b,c\n1,2,3\n1,2,3,4,5\n1,2\n")
    assert "couldn't parse" in message(path)


def test_falls_back_to_latin1(tmp_path: Path):
    df = load_csv(write(tmp_path, "a.csv", "name,n\ncaf\xe9,1\n".encode("latin-1")))
    assert df.loc[0, "name"] == "caf\xe9"


def test_sniffs_semicolon_separator(tmp_path: Path):
    df = load_csv(write(tmp_path, "a.csv", "a;b\n1;2\n3;4\n"))
    assert list(df.columns) == ["a", "b"]
