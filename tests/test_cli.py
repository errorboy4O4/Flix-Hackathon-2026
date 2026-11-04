"""Integration tests: run the real CLI in a subprocess, exactly as the chat agent does."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from chateda import cli

ROOT = Path(__file__).parent.parent


def run_cli(tmp_path: Path, *args: str, **env: str) -> tuple[int, dict]:
    full_env = {
        **os.environ,
        "CHATEDA_OUT_DIR": str(tmp_path / "out"),
        "CHATEDA_LOG_DIR": str(tmp_path / "logs"),
        **env,
    }
    proc = subprocess.run(
        [sys.executable, "-m", "chateda", *args],
        cwd=ROOT, env=full_env, capture_output=True, text=True, timeout=120,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_analyze_end_to_end(tmp_path: Path, sample_path: Path):
    code, result = run_cli(tmp_path, "analyze", str(sample_path))
    assert code == 0 and result["ok"]
    assert "600 rows x 9 columns" in result["message"]
    assert len(result["charts"]) == 4
    assert all(Path(p).is_absolute() and Path(p).exists() for p in result["charts"])


def test_analyze_drop_outliers_redoes_analysis(tmp_path: Path, sample_path: Path):
    _, base = run_cli(tmp_path, "analyze", str(sample_path))
    code, clean = run_cli(tmp_path, "analyze", str(sample_path), "--drop-outliers")
    assert code == 0
    assert "Outliers removed" in clean["message"]
    assert set(clean["charts"]).isdisjoint(base["charts"])


def test_breakdown_end_to_end(tmp_path: Path, sample_path: Path):
    code, result = run_cli(
        tmp_path, "breakdown", str(sample_path), "--by", "region", "--metric", "monthly_charges"
    )
    assert code == 0 and "Breakdown by region" in result["message"]
    assert len(result["charts"]) == 1


def test_drivers_end_to_end(tmp_path: Path, sample_path: Path):
    code, result = run_cli(tmp_path, "drivers", str(sample_path), "--target", "churn")
    assert code == 0 and "What relates most to churn" in result["message"]


def test_bad_file_gives_friendly_message_not_traceback(tmp_path: Path):
    bad = tmp_path / "x.csv"
    bad.write_text("")
    code, result = run_cli(tmp_path, "analyze", str(bad))
    assert code == cli.EXIT_USER_ERROR
    assert result == {"ok": False, "message": "That file is empty.", "charts": []}


def test_unknown_column_message(tmp_path: Path, sample_path: Path):
    code, result = run_cli(tmp_path, "drivers", str(sample_path), "--target", "chrn")
    assert code == cli.EXIT_USER_ERROR and "Did you mean: churn" in result["message"]


def test_oversize_limit_comes_from_env(tmp_path: Path, sample_path: Path):
    code, result = run_cli(tmp_path, "analyze", str(sample_path), CHATEDA_MAX_MB="0.001")
    assert code == cli.EXIT_USER_ERROR and "limit is 0.001 MB" in result["message"]


def test_errors_are_logged_server_side(tmp_path: Path):
    run_cli(tmp_path, "analyze", str(tmp_path / "missing.csv"))
    assert "user error" in (tmp_path / "logs" / "chateda.log").read_text()


def test_timeout_returns_plain_message(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_path: Path, capsys):
    monkeypatch.setenv("CHATEDA_TIMEOUT_S", "0.05")
    monkeypatch.setenv("CHATEDA_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(cli, "run_analyze", lambda *a, **k: time.sleep(2))
    code = cli.main(["analyze", str(sample_path)])
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_TIMEOUT and "took longer than 0.05 seconds" in out["message"]


def test_unexpected_exception_hides_stack_trace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_path: Path, capsys, caplog):
    monkeypatch.setenv("CHATEDA_LOG_DIR", str(tmp_path / "logs"))

    def boom(*a, **k):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(cli, "run_analyze", boom)
    code = cli.main(["analyze", str(sample_path)])
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_INTERNAL and "secret internals" not in out["message"]
    assert "secret internals" in caplog.text
