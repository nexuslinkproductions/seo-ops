"""Acceptance D: scorecard artifacts per client."""

from __future__ import annotations

from ops.scorecard import generate_scorecard


def test_scorecard_generates_html_and_markdown(data_root, populated_store, client_a):
    card = generate_scorecard(
        populated_store,
        data_root / "clients" / client_a.id,
        "2026-07-01",
        "2026-07-31",
        highlights=["Clicks up"],
    )
    exports = data_root / "clients" / client_a.id / "exports"
    md = exports / "scorecard-2026-07-01_2026-07-31.md"
    html = exports / "scorecard-2026-07-01_2026-07-31.html"
    assert md.exists()
    assert html.exists()
    md_text = md.read_text(encoding="utf-8")
    html_text = html.read_text(encoding="utf-8")
    assert "`clicks` (seo)" in md_text  # metric definition referenced
    assert "Clicks up" in md_text
    assert card.export_path == str(html)
    assert html_text.startswith("<!doctype html>")
    assert "Metric definitions referenced" in html_text


def test_scorecard_lists_verified_changes(data_root, populated_store, client_a, tmp_path):
    from ops import changeflow, evidence as ev
    from ops.ingest import import_file
    from ops.models import MeasurementWindow
    from conftest import FIXTURES

    import_file(populated_store, "search_console", FIXTURES / "search-console.csv")
    change = changeflow.new_change(populated_store, "Title tag fix", "marcel")
    changeflow.approve(populated_store, change.id, "marcel")
    changeflow.deploy(populated_store, change.id)
    pre = tmp_path / "pre.txt"
    post = tmp_path / "post.txt"
    pre.write_text("pre", encoding="utf-8")
    post.write_text("post", encoding="utf-8")
    pre_item = ev.capture_evidence(populated_store, data_root / "clients" / client_a.id, "note", file_path=pre)
    post_item = ev.capture_evidence(populated_store, data_root / "clients" / client_a.id, "note", file_path=post)
    changeflow.verify(
        populated_store,
        change.id,
        [pre_item.id],
        [post_item.id],
        MeasurementWindow(
            pre_start="2026-06-01", pre_end="2026-06-30",
            post_start="2026-07-01", post_end="2026-07-31",
        ),
        "seo",
        "clicks",
    )
    card = generate_scorecard(
        populated_store,
        data_root / "clients" / client_a.id,
        "2026-08-01",
        "2026-08-31",
    )
    assert change.id in card.changes_in_period
