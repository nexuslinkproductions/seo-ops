"""Acceptance C: change lifecycle gate and before/after deltas."""

from __future__ import annotations

import pytest

from ops import changeflow, evidence as ev
from ops.models import MeasurementWindow
from ops.ingest import import_file

from conftest import FIXTURES


def _deployed_change(store):
    change = changeflow.new_change(store, "Rewrite homepage H1", "marcel")
    changeflow.approve(store, change.id, "marcel")
    return changeflow.deploy(store, change.id)


def _evidence_pair(data_root, store, client_a, tmp_path):
    pre = tmp_path / "pre.png"
    post = tmp_path / "post.png"
    pre.write_bytes(b"pre")
    post.write_bytes(b"post")
    pre_item = ev.capture_evidence(store, data_root / "clients" / client_a.id, "screenshot", file_path=pre)
    post_item = ev.capture_evidence(store, data_root / "clients" / client_a.id, "screenshot", file_path=post)
    return pre_item, post_item


def test_verify_requires_pre_and_post_evidence(data_root, store, client_a, tmp_path):
    import_file(store, "search_console", FIXTURES / "search-console.csv")
    change = _deployed_change(store)
    window = MeasurementWindow(
        pre_start="2026-06-01", pre_end="2026-06-30",
        post_start="2026-07-01", post_end="2026-07-31",
    )
    with pytest.raises(changeflow.ChangeFlowError):
        changeflow.verify(store, change.id, [], [], window, "seo", "clicks")
    pre_item, post_item = _evidence_pair(data_root, store, client_a, tmp_path)
    with pytest.raises(changeflow.ChangeFlowError):
        changeflow.verify(store, change.id, [pre_item.id], [], window, "seo", "clicks")
    # Fake evidence id must also be rejected
    with pytest.raises(changeflow.ChangeFlowError):
        changeflow.verify(store, change.id, ["missing"], [post_item.id], window, "seo", "clicks")
    verified = changeflow.verify(
        store, change.id, [pre_item.id], [post_item.id], window, "seo", "clicks"
    )
    assert verified.status == "verified"


def test_verify_requires_defined_window(data_root, store, client_a, tmp_path):
    change = _deployed_change(store)
    pre_item, post_item = _evidence_pair(data_root, store, client_a, tmp_path)
    empty = MeasurementWindow(
        pre_start="", pre_end="", post_start="", post_end=""
    )
    with pytest.raises(changeflow.ChangeFlowError):
        changeflow.verify(store, change.id, [pre_item.id], [post_item.id], empty, "seo", "clicks")


def test_cannot_verify_before_deploy(data_root, store, client_a, tmp_path):
    import_file(store, "search_console", FIXTURES / "search-console.csv")
    change = changeflow.new_change(store, "Meta description pass", "marcel")
    changeflow.approve(store, change.id, "marcel")
    pre_item, post_item = _evidence_pair(data_root, store, client_a, tmp_path)
    window = MeasurementWindow(
        pre_start="2026-06-01", pre_end="2026-06-30",
        post_start="2026-07-01", post_end="2026-07-31",
    )
    with pytest.raises(changeflow.ChangeFlowError):
        changeflow.verify(store, change.id, [pre_item.id], [post_item.id], window, "seo", "clicks")


def test_verify_stores_before_after_delta(data_root, store, client_a, tmp_path):
    import_file(store, "search_console", FIXTURES / "search-console.csv")
    change = _deployed_change(store)
    pre_item, post_item = _evidence_pair(data_root, store, client_a, tmp_path)
    window = MeasurementWindow(
        pre_start="2026-06-01", pre_end="2026-06-30",
        post_start="2026-07-01", post_end="2026-07-31",
    )
    verified = changeflow.verify(
        store, change.id, [pre_item.id], [post_item.id],
        window, "seo", "clicks",
    )
    assert verified.status == "verified"
    assert verified.verified_at is not None
    summary = verified.result_summary
    assert summary.pre_value == 15
    assert summary.post_value == 26
    assert summary.abs_delta == 11
    assert summary.rel_delta == pytest.approx(11 / 15)
