"""Acceptance G: repository hygiene."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_data_and_db_gitignored_and_absent_from_history():
    if not (REPO / ".gitignore").is_file():
        pytest.skip("no .gitignore in this checkout")
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "data/" in gitignore
    assert "*.db" in gitignore
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True
    ).stdout.splitlines()
    assert not any(p.startswith("data/") for p in tracked)
    assert not any(p.endswith(".db") for p in tracked)


def test_all_docs_exist():
    expected = [
        "README.md",
        "AGENTS.md",
        "docs/architecture/OVERVIEW.md",
        "docs/research/01-operational-requirements.md",
        "docs/research/02-data-sources-and-metrics.md",
        "docs/research/03-evidence-model.md",
        "docs/research/04-technology-evaluation.md",
        "docs/decisions/ADR-001-language-selection.md",
        "docs/SECURITY-BOUNDARIES.md",
        "docs/ROADMAP.md",
        "docs/ACCEPTANCE.md",
        "docs/handoff/DEEPSEEK-BUILD-HANDOFF.md",
    ]
    missing = [p for p in expected if not (REPO / p).is_file()]
    assert missing == []


def test_no_secrets_marker_files():
    for path in (REPO / ".env",):
        assert not path.exists()
