"""
Conftest tests/ — Phase 0.

- Ajoute la racine du projet et tests/ au sys.path.
- Session hors-ligne : data.loader._fetch lit tests/fixtures/, load_crm est
  neutralise, horloge figee au 2026-10-05 (voir baseline_lib.offline_env).
- Aucun test ne pousse sur GitHub (push_csv_to_github jamais importe ici).
"""
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TESTS_DIR.parent
for p in (str(ROOT_DIR), str(TESTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402

from baseline_lib import offline_env  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _offline_env():
    """Toute la session de tests tourne hors-ligne, sur snapshot, horloge figee."""
    with offline_env():
        yield


@pytest.fixture(scope="session")
def prepared():
    """Donnees preparees par le pipeline reel (prepare_data) sur fixtures."""
    from baseline_lib import load_prepared

    return load_prepared()


@pytest.fixture(scope="session")
def baseline():
    """Contenu de tests/baseline.json (versionne)."""
    import json

    from baseline_lib import BASELINE_PATH

    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
