"""Acceptance A: client isolation by store."""

from __future__ import annotations

from ops.clients import open_client_store
from ops.ingest import import_file
from ops.scorecard import generate_scorecard

from conftest import FIXTURES, ingest_all


def test_no_client_id_column_in_any_domain_table(store, client_a):
    for table in store.tables():
        assert "client_id" not in store.columns(table), f"{table} leaks client_id"


def test_records_unreachable_across_clients(data_root, client_a, client_b):
    store_a = open_client_store(data_root, client_a.id)
    store_b = open_client_store(data_root, client_b.id)
    import_file(store_a, "search_console", FIXTURES / "search-console.csv")
    import_file(store_b, "analytics", FIXTURES / "analytics.csv")

    a_rows = store_a.rows_for_metrics(["clicks"])
    b_rows = store_b.rows_for_metrics(["sessions"])
    assert len(a_rows) == 4
    assert len(b_rows) == 2

    a_ids = {r.id for r in a_rows}
    for row in store_b.rows_for_metrics(["clicks"]):
        assert row.id not in a_ids
    for row in store_a.rows_for_metrics(["sessions"]):
        assert row.id not in {r.id for r in b_rows}


def test_no_cross_client_aggregate_view(data_root, client_a, client_b):
    store_a = open_client_store(data_root, client_a.id)
    store_b = open_client_store(data_root, client_b.id)
    ingest_all(store_a)
    ingest_all(store_b)
    # Registry holds identity only: no metric rows in registry.db
    import sqlite3

    with sqlite3.connect(data_root / "registry.db") as con:
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
    assert tables == ["clients"]


def test_scorecard_export_writes_only_under_own_client_dir(
    data_root, client_a, client_b
):
    store_a = open_client_store(data_root, client_a.id)
    store_b = open_client_store(data_root, client_b.id)
    ingest_all(store_a)
    ingest_all(store_b)
    generate_scorecard(
        store_a,
        data_root / "clients" / client_a.id,
        "2026-07-01",
        "2026-07-31",
    )
    a_exports = list((data_root / "clients" / client_a.id / "exports").glob("*"))
    b_exports = list((data_root / "clients" / client_b.id / "exports").glob("*"))
    assert len(a_exports) == 2
    assert b_exports == []
