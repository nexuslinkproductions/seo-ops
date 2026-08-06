"""Sales-prioritization backlog with impact/effort scoring."""

from __future__ import annotations

from typing import Optional

from .ids import new_id, utc_now
from .models import BacklogItem
from .store import ClientStore


def score(impact: float, effort: float) -> float:
    if effort <= 0:
        raise ValueError("effort must be > 0")
    return round(impact * 100 / effort, 1)


def add_item(
    store: ClientStore,
    title: str,
    impact: float,
    effort: float,
    category: str = "content",
    description: Optional[str] = None,
    evidence_ids: Optional[list[str]] = None,
) -> BacklogItem:
    item = BacklogItem(
        id=new_id(),
        created_at=utc_now(),
        title=title,
        description=description,
        category=category,
        impact=impact,
        effort=effort,
        score=score(impact, effort),
        evidence_ids=evidence_ids or [],
    )
    return store.add_backlog_item(item)


def list_items(store: ClientStore) -> list[BacklogItem]:
    return store.list_backlog()
