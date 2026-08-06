"""Evidence capture, content addressing, and integrity verification.

Evidence files are stored under the client's `evidence/` directory named by
their SHA-256 digest and never modified. Corrections are new items. Integrity
verification runs through the Rust `ops-core` binary when present and falls
back to a pure-Python implementation otherwise.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .ids import new_id, utc_now
from .models import EvidenceItem, IntegrityReport
from .store import ClientStore


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def capture_evidence(
    store: ClientStore,
    client_dir: Path,
    kind: str,
    *,
    file_path: Optional[Path] = None,
    inline_text: Optional[str] = None,
    captured_by: str = "operator",
    source_description: Optional[str] = None,
    related_query: Optional[str] = None,
    related_url: Optional[str] = None,
    related_prompt_id: Optional[str] = None,
) -> EvidenceItem:
    if file_path is None and inline_text is None:
        raise ValueError("either file_path or inline_text is required")
    if file_path is not None:
        src = Path(file_path)
        if not src.is_file():
            raise ValueError(f"evidence file not found: {src}")
        digest, size = sha256_file(src)
        suffix = src.suffix or ""
        evidence_dir = client_dir / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        dest = evidence_dir / f"{digest}{suffix}"
        if not dest.exists():
            shutil.copyfile(src, dest)
        stored_path = str(dest)
    else:
        digest = sha256_text(inline_text or "")
        size = len((inline_text or "").encode("utf-8"))
        stored_path = None
    item = EvidenceItem(
        id=new_id(),
        captured_at=utc_now(),
        captured_by=captured_by,
        kind=kind,
        path=stored_path,
        inline_text=inline_text,
        sha256=digest,
        size_bytes=size,
        source_description=source_description,
        related_query=related_query,
        related_url=related_url,
        related_prompt_id=related_prompt_id,
    )
    return store.add_evidence(item)


def _manifest(store: ClientStore, evidence_dir: Path) -> tuple[list[dict], Path]:
    """Build the expected manifest and a temp manifest file for the Rust CLI."""
    entries = []
    for item in store.list_evidence():
        if not item.path or not item.sha256:
            continue
        rel = Path(item.path)
        try:
            rel = rel.relative_to(evidence_dir)
        except ValueError:
            continue
        entries.append({"path": str(rel), "sha256": item.sha256})
    fd, manifest_path = tempfile.mkstemp(suffix=".manifest")
    with os.fdopen(fd, "w") as fh:
        for entry in entries:
            fh.write(f"{entry['sha256']}  {entry['path']}\n")
    return entries, Path(manifest_path)


def find_rust_binary() -> Optional[Path]:
    env = os.environ.get("OPS_CORE_BIN")
    if env:
        candidate = Path(env)
        return candidate if candidate.is_file() else None
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / "rust/ops-core/target/release/ops-core",
        repo_root / "rust/ops-core/target/debug/ops-core",
        Path.cwd() / "target/release/ops-core",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    which = shutil.which("ops-core")
    return Path(which) if which else None


def verify_evidence_python(
    store: ClientStore, evidence_dir: Path
) -> IntegrityReport:
    evidence_dir = Path(evidence_dir)
    entries, _ = _manifest(store, evidence_dir)
    expected = {entry["path"]: entry["sha256"] for entry in entries}
    report = IntegrityReport(
        tool="python", subcommand="verify-evidence", checked=0, clean=True
    )
    seen: set[str] = set()
    if evidence_dir.exists():
        for path in sorted(evidence_dir.iterdir()):
            if not path.is_file():
                continue
            rel = path.name
            seen.add(rel)
            if rel not in expected:
                report.extra.append({"path": rel})
                report.clean = False
                continue
            actual, _ = sha256_file(path)
            if actual != expected[rel]:
                report.mismatches.append(
                    {"path": rel, "expected": expected[rel], "actual": actual}
                )
                report.clean = False
    for rel, digest in expected.items():
        if rel not in seen:
            report.missing.append({"path": rel, "expected": digest})
            report.clean = False
    report.checked = len(entries)
    return report


def verify_evidence(
    store: ClientStore, client_dir: Path, prefer_rust: bool = True
) -> IntegrityReport:
    evidence_dir = client_dir / "evidence"
    if not evidence_dir.exists():
        return IntegrityReport(
            tool="python", subcommand="verify-evidence", checked=0, clean=True
        )
    binary = find_rust_binary()
    if prefer_rust and binary is not None:
        _, manifest_path = _manifest(store, evidence_dir)
        try:
            proc = subprocess.run(
                [
                    str(binary),
                    "verify-evidence",
                    "--dir",
                    str(evidence_dir),
                    "--manifest",
                    str(manifest_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            payload = json.loads(proc.stdout or "{}")
            return IntegrityReport(**{**payload, "tool": "rust"})
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass
    return verify_evidence_python(store, evidence_dir)
