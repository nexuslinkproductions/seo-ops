"""Acceptance C (evidence) and E (integrity)."""

from __future__ import annotations

import hashlib

import pytest

from ops import evidence as ev


def test_capture_stores_content_addressed_file(data_root, store, client_a, tmp_path):
    src = tmp_path / "before.png"
    src.write_bytes(b"before-screenshot-bytes")
    item = ev.capture_evidence(store, data_root / "clients" / client_a.id, "screenshot", file_path=src)
    expected = hashlib.sha256(b"before-screenshot-bytes").hexdigest()
    assert item.sha256 == expected
    stored = data_root / "clients" / client_a.id / "evidence" / f"{expected}.png"
    assert stored.exists()
    assert stored.read_bytes() == b"before-screenshot-bytes"


def test_evidence_is_immutable(data_root, store, client_a, tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("v1", encoding="utf-8")
    first = ev.capture_evidence(store, data_root / "clients" / client_a.id, "note", file_path=src)
    src.write_text("v2", encoding="utf-8")
    second = ev.capture_evidence(store, data_root / "clients" / client_a.id, "note", file_path=src)
    assert first.id != second.id
    assert first.sha256 != second.sha256
    assert "update_evidence" not in dir(store)
    # Original stored artifact is untouched and still matches its digest.
    stored = data_root / "clients" / client_a.id / "evidence" / f"{first.sha256}.txt"
    assert stored.read_text(encoding="utf-8") == "v1"


def test_inline_evidence_has_no_file(data_root, store, client_a):
    item = ev.capture_evidence(
        store, data_root / "clients" / client_a.id, "note", inline_text="hello"
    )
    assert item.path is None
    assert item.sha256 == ev.sha256_text("hello")


def _capture_pair(data_root, store, client_a, tmp_path):
    pre = tmp_path / "pre.txt"
    post = tmp_path / "post.txt"
    pre.write_text("pre evidence", encoding="utf-8")
    post.write_text("post evidence", encoding="utf-8")
    pre_item = ev.capture_evidence(store, data_root / "clients" / client_a.id, "note", file_path=pre)
    post_item = ev.capture_evidence(store, data_root / "clients" / client_a.id, "note", file_path=post)
    return pre_item, post_item


def test_verify_clean_tree(data_root, store, client_a, tmp_path):
    _capture_pair(data_root, store, client_a, tmp_path)
    report = ev.verify_evidence(
        store, data_root / "clients" / client_a.id, prefer_rust=False
    )
    assert report.clean is True
    assert report.tool == "python"
    assert report.checked == 2


def test_verify_flags_corrupted_file(data_root, store, client_a, tmp_path):
    pre_item, _ = _capture_pair(data_root, store, client_a, tmp_path)
    evidence_file = data_root / "clients" / client_a.id / "evidence" / f"{pre_item.sha256}.txt"
    evidence_file.write_bytes(b"tampered")
    report = ev.verify_evidence(
        store, data_root / "clients" / client_a.id, prefer_rust=False
    )
    assert report.clean is False
    assert any(m["path"].endswith(".txt") for m in report.mismatches)


def test_verify_flags_missing_file(data_root, store, client_a, tmp_path):
    pre_item, _ = _capture_pair(data_root, store, client_a, tmp_path)
    (data_root / "clients" / client_a.id / "evidence" / f"{pre_item.sha256}.txt").unlink()
    report = ev.verify_evidence(
        store, data_root / "clients" / client_a.id, prefer_rust=False
    )
    assert report.clean is False
    assert len(report.missing) == 1


def test_rust_binary_integration_if_built(data_root, store, client_a, tmp_path):
    binary = ev.find_rust_binary()
    if binary is None:
        pytest.skip("ops-core binary not built; python fallback covered elsewhere")
    pre_item, _ = _capture_pair(data_root, store, client_a, tmp_path)
    report = ev.verify_evidence(
        store, data_root / "clients" / client_a.id, prefer_rust=True
    )
    assert report.tool == "rust"
    assert report.clean is True
    (data_root / "clients" / client_a.id / "evidence" / f"{pre_item.sha256}.txt").write_bytes(b"x")
    report = ev.verify_evidence(
        store, data_root / "clients" / client_a.id, prefer_rust=True
    )
    assert report.clean is False
