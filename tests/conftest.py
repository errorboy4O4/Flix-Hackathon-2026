from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_path() -> Path:
    return FIXTURES / "sample.csv"


@pytest.fixture
def sample_df(sample_path: Path) -> pd.DataFrame:
    from chateda.loader import load_csv

    return load_csv(sample_path)
