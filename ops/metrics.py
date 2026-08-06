"""Metric definitions and computation with period-over-period deltas.

All metric values are computed on demand from the client's raw rows, so
definitions can change without touching stored data. Every metric has a
definition entry that scorecards reference.
"""

from __future__ import annotations

import json
from typing import Optional

from .models import MetricDefinition
from .store import ClientStore


def default_metric_definitions() -> list[MetricDefinition]:
    return [
        MetricDefinition(id="clicks", family="seo", name="Clicks", source="search_console", grain="date/query/page", formula="sum(clicks)", freshness="daily"),
        MetricDefinition(id="impressions", family="seo", name="Impressions", source="search_console", grain="date/query/page", formula="sum(impressions)", freshness="daily"),
        MetricDefinition(id="ctr", family="seo", name="Click-through rate", source="search_console", grain="date/query/page", formula="clicks / impressions", freshness="daily"),
        MetricDefinition(id="avg_position", family="seo", name="Average position", source="search_console", grain="date/query/page", formula="weighted avg(position by impressions)", freshness="daily"),
        MetricDefinition(id="indexed_pages", family="seo", name="Indexed pages", source="crawl", grain="page", formula="count(indexable pages)", freshness="weekly"),
        MetricDefinition(id="crawl_errors", family="seo", name="Crawl errors", source="crawl", grain="page", formula="count(status >= 400)", freshness="weekly"),
        MetricDefinition(id="canonical_valid_pct", family="seo", name="Valid canonicals", source="crawl", grain="page", formula="valid canonicals / crawled pages", freshness="weekly"),
        MetricDefinition(id="keyword_search_volume", family="seo", name="Keyword search volume", source="openseo", grain="keyword", formula="sum(search volume)", freshness="monthly"),
        MetricDefinition(id="keyword_cpc", family="seo", name="Keyword CPC", source="openseo", grain="keyword", formula="avg(cpc)", freshness="monthly"),
        MetricDefinition(id="keyword_competition", family="seo", name="Keyword competition", source="openseo", grain="keyword", formula="sum(competition)", freshness="monthly"),
        MetricDefinition(id="keyword_difficulty", family="seo", name="Keyword difficulty", source="openseo", grain="keyword", formula="sum(difficulty)", freshness="monthly"),
        MetricDefinition(id="serp_position", family="seo", name="SERP position", source="openseo", grain="keyword/url", formula="avg(rank absolute)", freshness="monthly"),
        MetricDefinition(id="snippet_owned_pct", family="aeo", name="Featured snippet ownership", source="aeo_audit", grain="query", formula="owned snippets / tracked queries", freshness="monthly"),
        MetricDefinition(id="paa_presence", family="aeo", name="People Also Ask presence", source="aeo_audit", grain="query", formula="count(paa present)", freshness="monthly"),
        MetricDefinition(id="structured_data_coverage_pct", family="aeo", name="Structured data coverage", source="aeo_audit", grain="query", formula="valid markup / tracked queries", freshness="monthly"),
        MetricDefinition(id="citation_rate", family="geo", name="Citation rate", source="geo_probe", grain="prompt/engine", formula="answers citing client / answers", freshness="monthly"),
        MetricDefinition(id="mention_rate", family="geo", name="Mention rate", source="geo_probe", grain="prompt/engine", formula="answers mentioning brand / answers", freshness="monthly"),
        MetricDefinition(id="share_of_answer", family="geo", name="Share of answer", source="geo_probe", grain="prompt/engine", formula="client citations / total citations", freshness="monthly"),
        MetricDefinition(id="avg_citation_position", family="geo", name="Average citation position", source="geo_probe", grain="prompt/engine", formula="avg(citation position)", freshness="monthly"),
        MetricDefinition(id="sessions", family="analytics", name="Sessions", source="analytics", grain="date/landing page", formula="sum(sessions)", freshness="daily"),
        MetricDefinition(id="conversions", family="analytics", name="Conversions", source="analytics", grain="date/landing page", formula="sum(conversions)", freshness="daily"),
        MetricDefinition(id="conversion_rate", family="analytics", name="Conversion rate", source="analytics", grain="date/landing page", formula="conversions / sessions", freshness="daily"),
        MetricDefinition(id="engaged_sessions", family="analytics", name="Engaged sessions", source="analytics", grain="date/landing page", formula="sum(engaged sessions)", freshness="daily"),
    ]


def _sum(rows) -> float:
    return sum(r.value for r in rows)


def _count(rows) -> float:
    return float(len(rows))


def _rate(rows) -> Optional[float]:
    total = _count(rows)
    if total == 0:
        return None
    return _sum(rows) / total


RAW_METRICS = {
    "clicks": "clicks",
    "impressions": "impressions",
    "avg_position": "position",
    "indexed_pages": "crawl_indexable",
    "crawl_errors": "crawl_error",
    "canonical_valid_pct": "canonical_valid",
    "keyword_search_volume": "keyword_search_volume",
    "keyword_cpc": "keyword_cpc",
    "keyword_competition": "keyword_competition",
    "keyword_difficulty": "keyword_difficulty",
    "serp_position": "serp_position",
    "snippet_owned_pct": "aeo_snippet_owned",
    "paa_presence": "aeo_paa",
    "structured_data_coverage_pct": "aeo_sd_valid",
    "citation_rate": "geo_citation",
    "mention_rate": "geo_mention",
    "avg_citation_position": "geo_citation_position",
    "sessions": "sessions",
    "conversions": "conversions",
    "engaged_sessions": "engaged_sessions",
}

SUM_METRICS = {
    "clicks", "impressions", "sessions", "conversions", "engaged_sessions",
    "indexed_pages", "crawl_errors", "paa_presence",
    "keyword_search_volume", "keyword_competition", "keyword_difficulty",
}
RATE_METRICS = {
    "snippet_owned_pct", "structured_data_coverage_pct",
    "canonical_valid_pct", "citation_rate", "mention_rate",
}
AVG_METRICS = {"keyword_cpc", "serp_position"}


def compute_metric(
    store: ClientStore, family: str, metric: str,
    start: Optional[str] = None, end: Optional[str] = None,
) -> Optional[float]:
    if metric == "ctr":
        clicks = _sum(store.rows_for_metrics(["clicks"], start, end))
        impressions = _sum(store.rows_for_metrics(["impressions"], start, end))
        return clicks / impressions if impressions else None
    if metric == "conversion_rate":
        conversions = _sum(store.rows_for_metrics(["conversions"], start, end))
        sessions = _sum(store.rows_for_metrics(["sessions"], start, end))
        return conversions / sessions if sessions else None
    raw_metric = RAW_METRICS.get(metric, metric)
    rows = store.rows_for_metrics([raw_metric], start, end)
    if metric in SUM_METRICS:
        return _sum(rows)
    if metric in RATE_METRICS:
        return _rate(rows)
    if metric in AVG_METRICS:
        values = [r.value for r in rows if r.value is not None]
        return sum(values) / len(values) if values else None
    if metric == "avg_position":
        weighted = 0.0
        weight_total = 0.0
        for row in rows:
            try:
                impressions = float(json.loads(row.payload).get("Impressions") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                impressions = 0.0
            weighted += row.value * impressions
            weight_total += impressions
        return weighted / weight_total if weight_total else None
    if metric == "share_of_answer":
        citations = _sum(store.rows_for_metrics(["geo_citation"], start, end))
        total = _sum(store.rows_for_metrics(["geo_total_citations"], start, end))
        return citations / total if total else None
    if metric == "avg_citation_position":
        positions = [r.value for r in rows if r.value > 0]
        return sum(positions) / len(positions) if positions else None
    return None


def family_metrics(family: str) -> list[str]:
    return [d.id for d in default_metric_definitions() if d.family == family]


def window_delta(
    store: ClientStore, family: str, metric: str,
    pre_start: str, pre_end: str, post_start: str, post_end: str,
) -> dict:
    if metric in ("indexed_pages", "crawl_errors", "canonical_valid_pct"):
        return {"pre": None, "post": None, "abs_delta": None, "rel_delta": None}
    pre = compute_metric(store, family, metric, pre_start, pre_end)
    post = compute_metric(store, family, metric, post_start, post_end)
    abs_delta = (post - pre) if (pre is not None and post is not None) else None
    rel_delta = (abs_delta / pre) if (abs_delta is not None and pre) else None
    return {
        "pre": pre,
        "post": post,
        "abs_delta": abs_delta,
        "rel_delta": rel_delta,
    }


def family_summary(
    store: ClientStore, family: str,
    pre_start: str, pre_end: str, post_start: str, post_end: str,
) -> dict:
    return {
        metric: window_delta(store, family, metric, pre_start, pre_end, post_start, post_end)
        for metric in family_metrics(family)
    }


def period_values(store: ClientStore, family: str, start: str, end: str) -> dict:
    return {
        metric: compute_metric(
            store,
            family,
            metric,
            None if metric in ("indexed_pages", "crawl_errors", "canonical_valid_pct") else start,
            None if metric in ("indexed_pages", "crawl_errors", "canonical_valid_pct") else end,
        )
        for metric in family_metrics(family)
    }


def all_families_summary(
    store: ClientStore, pre_start: str, pre_end: str, post_start: str, post_end: str
) -> dict:
    return {
        family: family_summary(store, family, pre_start, pre_end, post_start, post_end)
        for family in ("seo", "aeo", "geo", "analytics")
    }
