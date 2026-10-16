import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def seed_cards():
    with open(ROOT / "data" / "seed_us_presidents.json", encoding="utf-8") as fh:
        return json.load(fh)
