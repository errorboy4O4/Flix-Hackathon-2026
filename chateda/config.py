"""Runtime limits, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Limits applied to every analysis run."""

    max_mb: float = 25.0
    max_rows: int = 500_000
    timeout_s: float = 120.0
    out_dir: Path = Path("out")

    @classmethod
    def from_env(cls) -> Config:
        """Build a Config from CHATEDA_* variables, falling back to defaults."""
        defaults = cls()
        return cls(
            max_mb=float(os.environ.get("CHATEDA_MAX_MB", defaults.max_mb)),
            max_rows=int(os.environ.get("CHATEDA_MAX_ROWS", defaults.max_rows)),
            timeout_s=float(os.environ.get("CHATEDA_TIMEOUT_S", defaults.timeout_s)),
            out_dir=Path(os.environ.get("CHATEDA_OUT_DIR", defaults.out_dir)),
        )
