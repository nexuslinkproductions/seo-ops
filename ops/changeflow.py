"""Change lifecycle: proposed -> approved -> deployed -> verified.

Verification is gated: at least one pre and one post evidence item plus a
defined measurement window are required, and the before/after metric delta is
computed and stored on the change.
"""

from __future__ import annotations

from typing import Optional

from .ids import new_id, utc_now
from .metrics import compute_metric
from .models import ChangeEntry, MeasurementWindow, ResultSummary
from .store import ClientStore


class ChangeFlowError(Exception):
    """Raised for invalid lifecycle transitions."""


def _require(store: ClientStore, change_id: str) -> ChangeEntry:
    change = store.get_change(change_id)
    if change is None:
        raise ChangeFlowError(f"unknown change: {change_id}")
    return change


def _transition(change: ChangeEntry, expected: set[str], target: str) -> None:
    if change.status not in expected:
        raise ChangeFlowError(
            f"cannot move change {change.id} from {change.status} to {target}"
        )


def new_change(
    store: ClientStore,
    title: str,
    proposed_by: str,
    description: Optional[str] = None,
    scope_urls: Optional[list[str]] = None,
) -> ChangeEntry:
    change = ChangeEntry(
        id=new_id(),
        created_at=utc_now(),
        title=title,
        description=description,
        scope_urls=scope_urls or [],
        status="proposed",
        proposed_by=proposed_by,
    )
    return store.add_change(change)


def approve(store: ClientStore, change_id: str, approved_by: str) -> ChangeEntry:
    change = _require(store, change_id)
    _transition(change, {"proposed"}, "approved")
    change.status = "approved"
    change.approved_by = approved_by
    change.approved_at = utc_now()
    return store.update_change(change)


def deploy(store: ClientStore, change_id: str) -> ChangeEntry:
    change = _require(store, change_id)
    _transition(change, {"approved"}, "deployed")
    change.status = "deployed"
    change.deployed_at = utc_now()
    return store.update_change(change)


def reject(store: ClientStore, change_id: str) -> ChangeEntry:
    change = _require(store, change_id)
    _transition(change, {"proposed", "approved"}, "rejected")
    change.status = "rejected"
    return store.update_change(change)


def revert(store: ClientStore, change_id: str) -> ChangeEntry:
    change = _require(store, change_id)
    _transition(change, {"deployed", "verified"}, "reverted")
    change.status = "reverted"
    return store.update_change(change)


def verify(
    store: ClientStore,
    change_id: str,
    pre_evidence_ids: list[str],
    post_evidence_ids: list[str],
    window: MeasurementWindow,
    family: str,
    metric: str,
) -> ChangeEntry:
    change = _require(store, change_id)
    _transition(change, {"deployed"}, "verified")
    if not pre_evidence_ids or not post_evidence_ids:
        raise ChangeFlowError(
            "verification requires at least one pre and one post evidence item"
        )
    if not store.evidence_ids_exist(pre_evidence_ids + post_evidence_ids):
        raise ChangeFlowError("one or more referenced evidence items do not exist")
    if not (window.pre_start and window.pre_end and window.post_start and window.post_end):
        raise ChangeFlowError("verification requires a defined measurement window")
    if window.pre_end > window.post_start:
        raise ChangeFlowError("measurement windows must not overlap")
    pre = compute_metric(store, family, metric, window.pre_start, window.pre_end)
    post = compute_metric(store, family, metric, window.post_start, window.post_end)
    if pre is None or post is None:
        raise ChangeFlowError("no metric data available in one or both windows")
    abs_delta = post - pre
    rel_delta = abs_delta / pre if pre else None
    change.status = "verified"
    change.verified_at = utc_now()
    change.pre_evidence_ids = pre_evidence_ids
    change.post_evidence_ids = post_evidence_ids
    change.measurement_window = window
    change.result_summary = ResultSummary(
        family=family,
        metric=metric,
        pre_value=pre,
        post_value=post,
        abs_delta=abs_delta,
        rel_delta=rel_delta,
    )
    return store.update_change(change)
