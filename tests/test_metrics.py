"""Acceptance D: metric families with period-over-period deltas."""

from __future__ import annotations

import pytest

from ops.metrics import (
    all_families_summary,
    compute_metric,
    family_metrics,
    period_values,
)


def test_each_family_has_metric_with_delta(populated_store):
    summary = all_families_summary(
        populated_store,
        "2026-06-01", "2026-06-30",
        "2026-07-01", "2026-07-31",
    )
    for family in ("seo", "aeo", "geo", "analytics"):
        assert family in summary
        assert any(
            entry["pre"] is not None and entry["post"] is not None
            for entry in summary[family].values()
        ), f"{family} has no computed delta"


def test_seo_metrics_values(populated_store):
    assert compute_metric(populated_store, "seo", "clicks", "2026-06-01", "2026-06-30") == 15
    assert compute_metric(populated_store, "seo", "clicks", "2026-07-01", "2026-07-31") == 26
    assert compute_metric(populated_store, "seo", "impressions", "2026-06-01", "2026-06-30") == 180
    ctr = compute_metric(populated_store, "seo", "ctr", "2026-06-01", "2026-06-30")
    assert ctr == pytest.approx(15 / 180)
    pos = compute_metric(populated_store, "seo", "avg_position", "2026-07-01", "2026-07-31")
    assert pos == pytest.approx(762 / 250)


def test_crawl_snapshot_metrics(populated_store):
    assert compute_metric(populated_store, "seo", "indexed_pages") == 2
    assert compute_metric(populated_store, "seo", "crawl_errors") == 1
    assert compute_metric(populated_store, "seo", "canonical_valid_pct") == pytest.approx(2 / 3)


def test_geo_metrics(populated_store):
    assert compute_metric(populated_store, "geo", "citation_rate", "2026-07-01", "2026-07-31") == pytest.approx(2 / 3)
    assert compute_metric(populated_store, "geo", "mention_rate", "2026-07-01", "2026-07-31") == pytest.approx(2 / 3)
    assert compute_metric(populated_store, "geo", "share_of_answer", "2026-07-01", "2026-07-31") == pytest.approx(0.5)
    assert compute_metric(populated_store, "geo", "avg_citation_position", "2026-07-01", "2026-07-31") == pytest.approx(1.5)


def test_analytics_metrics(populated_store):
    assert compute_metric(populated_store, "analytics", "sessions", "2026-06-01", "2026-06-30") == 120
    assert compute_metric(populated_store, "analytics", "conversions", "2026-07-01", "2026-07-31") == 4
    conv = compute_metric(populated_store, "analytics", "conversion_rate", "2026-07-01", "2026-07-31")
    assert conv == pytest.approx(4 / 150)


def test_metric_definitions_seeded(populated_store):
    defs = populated_store.list_metric_definitions()
    assert {d.family for d in defs} == {"seo", "aeo", "geo", "analytics"}
    for family in ("seo", "aeo", "geo", "analytics"):
        assert family_metrics(family)
    assert period_values(populated_store, "seo", "2026-07-01", "2026-07-31")["clicks"] == 26
