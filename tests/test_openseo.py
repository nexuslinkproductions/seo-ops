"""OpenSEO adapter: sanitized import, mapping, idempotency, isolation."""

from __future__ import annotations

import json

import pytest

from ops import openseo as oe
from ops.clients import open_client_store
from ops.ingest import IngestError
from ops.metrics import compute_metric

from conftest import FIXTURES


def test_json_import_maps_metrics(store):
    result = oe.import_openseo_export(
        store,
        store.db_path.parent,
        FIXTURES / "openseo-keywords.json",
        capture_evidence=False,
    )
    assert result["idempotent"] is False
    assert result["new_rows"] == 10
    assert result["batch"].row_count == 10
    assert compute_metric(store, "seo", "keyword_search_volume") == 2100
    assert compute_metric(store, "seo", "keyword_cpc") == pytest.approx(1.2)
    assert compute_metric(store, "seo", "keyword_competition") == pytest.approx(0.9)
    assert compute_metric(store, "seo", "keyword_difficulty") == 75
    assert compute_metric(store, "seo", "serp_position") == pytest.approx(8.5)


def test_csv_import_maps_metrics(store):
    result = oe.import_openseo_export(
        store,
        store.db_path.parent,
        FIXTURES / "openseo-serp.csv",
        capture_evidence=False,
    )
    assert result["new_rows"] == 4
    assert compute_metric(store, "seo", "keyword_search_volume") == 1650
    assert compute_metric(store, "seo", "serp_position") == pytest.approx(10.5)


def test_reimport_is_idempotent(data_root, store, client_a):
    path = FIXTURES / "openseo-keywords.json"
    first = oe.import_openseo_export(store, data_root / "clients" / client_a.id, path)
    before = store.row_count()
    second = oe.import_openseo_export(store, data_root / "clients" / client_a.id, path)
    assert second["idempotent"] is True
    assert second["batch"].id == first["batch"].id
    assert store.row_count() == before
    assert len(store.list_batches()) == 1
    assert len(store.list_evidence()) == 1


def test_evidence_captured_sanitized_and_content_addressed(data_root, store, client_a):
    result = oe.import_openseo_export(
        store, data_root / "clients" / client_a.id, FIXTURES / "openseo-keywords.json"
    )
    items = store.list_evidence()
    assert len(items) == 1
    assert items[0].id in result["evidence"]
    stored = data_root / "clients" / client_a.id / "evidence" / f"{items[0].sha256}.json"
    assert stored.exists()
    assert items[0].path == str(stored)
    content = json.loads(stored.read_text(encoding="utf-8"))
    text = json.dumps(content).lower()
    assert "api_key" not in text
    assert "token" not in text
    assert content["source"] == "openseo"


def test_rejects_credential_fields(store):
    with pytest.raises(IngestError):
        oe.import_openseo_export(
            store, store.db_path.parent, FIXTURES / "openseo-credentials.json"
        )
    assert store.row_count() == 0
    assert store.list_batches() == []


def test_isolated_across_clients(data_root, client_a, client_b):
    store_a = open_client_store(data_root, client_a.id)
    store_b = open_client_store(data_root, client_b.id)
    oe.import_openseo_export(
        store_a, data_root / "clients" / client_a.id, FIXTURES / "openseo-serp.csv"
    )
    assert len(store_a.rows_for_metrics(["keyword_search_volume"])) == 2
    assert store_b.rows_for_metrics(["keyword_search_volume"]) == []
    a_evidence = list((data_root / "clients" / client_a.id / "evidence").glob("*"))
    b_evidence = list((data_root / "clients" / client_b.id / "evidence").glob("*"))
    assert len(a_evidence) == 1
    assert b_evidence == []


def test_no_evidence_flag(data_root, store, client_a):
    oe.import_openseo_export(
        store,
        data_root / "clients" / client_a.id,
        FIXTURES / "openseo-serp.csv",
        capture_evidence=False,
    )
    assert store.list_evidence() == []


def test_backlog_from_poor_rankings(data_root, store, client_a):
    result = oe.import_openseo_export(
        store,
        data_root / "clients" / client_a.id,
        FIXTURES / "openseo-serp.csv",
        build_backlog=True,
    )
    items = store.list_backlog()
    assert len(result["backlog"]) == 1
    assert len(items) == 1
    assert "iwb holster" in items[0].title
    assert items[0].score > 0


def test_adapter_ignores_environment_credentials(store, monkeypatch):
    monkeypatch.setenv("OPENSEO_API_KEY", "dummy-value-that-must-not-be-used")
    result = oe.import_openseo_export(
        store, store.db_path.parent, FIXTURES / "openseo-keywords.json"
    )
    assert result["new_rows"] == 10
    assert compute_metric(store, "seo", "keyword_search_volume") == 2100
