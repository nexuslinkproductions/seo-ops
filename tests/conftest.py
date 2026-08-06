from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ops.clients import create_client, open_client_store  # noqa: E402
from ops.ingest import import_file  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def make_client(data_root: Path):
    def _make(name: str, client_id: str | None = None):
        return create_client(data_root, name, explicit_id=client_id)

    return _make


@pytest.fixture
def client_a(data_root: Path, make_client):
    return make_client("Acme Web", client_id="acme-web")


@pytest.fixture
def client_b(data_root: Path, make_client):
    return make_client("Beta Shop", client_id="beta-shop")


@pytest.fixture
def store(data_root: Path, client_a):
    return open_client_store(data_root, client_a.id)


def ingest_all(store) -> None:
    import_file(store, "search_console", FIXTURES / "search-console.csv")
    import_file(store, "crawl", FIXTURES / "crawl.csv")
    import_file(store, "analytics", FIXTURES / "analytics.csv")
    import_file(store, "geo", FIXTURES / "geo.json")
    import_file(store, "aeo", FIXTURES / "aeo.json")


@pytest.fixture
def populated_store(data_root: Path, client_a):
    store = open_client_store(data_root, client_a.id)
    ingest_all(store)
    return store
