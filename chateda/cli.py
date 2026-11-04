"""Command line entry point the chat agent calls. Always prints one JSON object."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from chateda import charts, ops, report
from chateda.config import Config
from chateda.loader import ChatEdaError, load_csv
from chateda.profile import build_profile

log = logging.getLogger("chateda")

EXIT_USER_ERROR = 2
EXIT_TIMEOUT = 3
EXIT_INTERNAL = 4


def _load(path: Path, config: Config, drop_outliers: bool) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """Load the CSV; optionally drop IQR outlier rows and report what was removed."""
    df = load_csv(path, config)
    if not drop_outliers:
        return df, None
    mask, removed = ops.iqr_outlier_mask(df)
    return df[~mask].reset_index(drop=True), removed


def run_analyze(path: Path, config: Config, drop_outliers: bool = False) -> dict:
    """Overview EDA; optionally drop IQR outliers first and redo everything."""
    df, removed = _load(path, config, drop_outliers)
    profile = build_profile(df)
    folder = _out_folder(config, path, "analyze_clean" if drop_outliers else "analyze")
    images = charts.overview_charts(df, profile, folder)
    return _result(report.overview_markdown(path.name, profile, removed), images)


def run_breakdown(
    path: Path, config: Config, by: str, metric: str | None, agg: str, drop_outliers: bool = False
) -> dict:
    """Summarize a metric (or row counts) per group of a column."""
    df, removed = _load(path, config, drop_outliers)
    table = ops.breakdown(df, by, metric, agg)
    by = ops.require_column(df, by)
    folder = _out_folder(config, path, f"breakdown_{by}")
    image = charts.bar_chart(
        [str(i) for i in table.index],
        [float(v) for v in table.iloc[:, 0]],
        f"{table.columns[0]} by {by}",
        str(table.columns[0]),
        folder / "breakdown.png",
    )
    return _result(report.breakdown_markdown(by, table, removed), [image])


def run_drivers(path: Path, config: Config, target: str, drop_outliers: bool = False) -> dict:
    """Rank which columns relate most strongly to the target column."""
    df, removed = _load(path, config, drop_outliers)
    ranked = ops.drivers(df, target)
    target = ops.require_column(df, target)
    folder = _out_folder(config, path, f"drivers_{target}")
    top = ranked[:8]
    images = []
    if top:
        images.append(
            charts.bar_chart(
                [d.column for d in top],
                [d.score for d in top],
                f"Columns most related to {target}",
                "strength of relationship (0 to 1)",
                folder / "drivers.png",
            )
        )
    return _result(report.drivers_markdown(target, ranked, removed), images)


def _out_folder(config: Config, path: Path, name: str) -> Path:
    return (config.out_dir / path.stem / name).resolve()


def _result(message: str, images: list[Path]) -> dict:
    return {"ok": True, "message": message, "charts": [str(p) for p in images]}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chateda", description="CSV exploratory analysis for chat agents.")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="overview EDA with charts")
    analyze.add_argument("file")
    breakdown = sub.add_parser("breakdown", help="summarize a metric by a column")
    breakdown.add_argument("file")
    breakdown.add_argument("--by", required=True)
    breakdown.add_argument("--metric")
    breakdown.add_argument("--agg", default="mean", choices=ops.VALID_AGGS)
    drivers = sub.add_parser("drivers", help="which columns relate most to a target")
    drivers.add_argument("file")
    drivers.add_argument("--target", required=True)
    for command in (analyze, breakdown, drivers):
        command.add_argument("--drop-outliers", action="store_true", help="remove IQR outliers first")
    return parser


def _dispatch(args: argparse.Namespace, config: Config) -> Callable[[], dict]:
    path = Path(args.file)
    if args.command == "analyze":
        return lambda: run_analyze(path, config, args.drop_outliers)
    if args.command == "breakdown":
        return lambda: run_breakdown(path, config, args.by, args.metric, args.agg, args.drop_outliers)
    return lambda: run_drivers(path, config, args.target, args.drop_outliers)


def _run_with_timeout(task: Callable[[], dict], seconds: float) -> dict | None:
    """Run task in a worker thread; return None if it exceeds the time limit."""
    box: dict = {}

    def worker() -> None:
        try:
            box["result"] = task()
        except BaseException as exc:  # re-raised on the caller's thread
            box["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(seconds)
    if thread.is_alive():
        return None
    if "error" in box:
        raise box["error"]
    return box["result"]


def _fail(message: str, code: int) -> int:
    print(json.dumps({"ok": False, "message": message, "charts": []}))
    return code


def _setup_logging() -> None:
    log_dir = Path(os.environ.get("CHATEDA_LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_dir / "chateda.log", encoding="utf-8")],
    )


def main(argv: list[str] | None = None) -> int:
    """Run one command and print its JSON result. Returns the process exit code."""
    _setup_logging()
    args = _build_parser().parse_args(argv)
    config = Config.from_env()
    log.info("command=%s file=%s", args.command, args.file)
    try:
        result = _run_with_timeout(_dispatch(args, config), config.timeout_s)
    except ChatEdaError as exc:
        log.warning("user error: %s", exc.user_message)
        return _fail(exc.user_message, EXIT_USER_ERROR)
    except Exception:
        log.exception("unexpected failure")
        return _fail(
            "Something went wrong while analyzing that file. I've logged the details; "
            "try a smaller or simpler file.",
            EXIT_INTERNAL,
        )
    if result is None:
        log.error("timed out after %ss", config.timeout_s)
        return _fail(
            f"That analysis took longer than {config.timeout_s:g} seconds, so I stopped it. "
            "Try a smaller file or fewer columns.",
            EXIT_TIMEOUT,
        )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
