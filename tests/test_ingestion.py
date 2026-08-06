"""Acceptance B: ingestion."""

from __future__ import annotations

import pytest

from ops.ingest import import_file

from conftest import FIXTURES

SOURCES = [
    ("search_console", "search-console.csv"),
    ("crawl", "crawl.csv"),
    ("analytics", "analytics.csv"),
    ("geo", "geo.json"),
    ("aeo", "aeo.json"),
]


@pytest.mark.parametrize("source,fixture", SOURCES)
def test_each_fixture_ingests(store, source, fixture):
    batch = import_file(store, source, FIXTURES / fixture)
    assert batch.row_count > 0
    assert store.row_count() == batch.row_count


def test_reingest_same_file_is_idempotent(store):
    path = FIXTURES / "search-console.csv"
    first = import_file(store, "search_console", path)
    before = store.row_count()
    second = import_file(store, "search_console", path)
    assert second.id == first.id
    assert store.row_count() == before
    batches = store.list_batches()
    assert len(batches) == 1
    assert "idempotent" in batches[0].rule


def test_new_content_creates_new_batch(store, tmp_path):
    path = tmp_path / "sc-new.csv"
    path.write_text(
        "Query,Page,Date,Clicks,Impressions,CTR,Position\n"
        "kydex,https://x.ch/,2026-08-01,1,5,0.2,1.0\n",
        encoding="utf-8",
    )
    first = import_file(store, "search_console", FIXTURES / "search-console.csv")
    second = import_file(store, "search_console", path)
    assert second.id != first.id
    assert len(store.list_batches()) == 2
