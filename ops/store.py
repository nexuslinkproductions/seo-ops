"""Per-client SQLite repository layer.

Isolation contract: every domain table lives inside one client's own
`client.db` and carries no `client_id` column. The store never opens more
than one client database per instance and exposes no cross-store query.
Evidence rows have no update path: evidence is immutable by construction.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .ids import new_id, utc_now
from .models import (
    AuditFinding,
    BacklogItem,
    ChangeEntry,
    EvidenceItem,
    ImportBatch,
    MetricDefinition,
    RawRow,
    Scorecard,
)

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS import_batches (
        id TEXT PRIMARY KEY,
        source_family TEXT NOT NULL,
        source_name TEXT NOT NULL,
        file_name TEXT,
        file_sha256 TEXT,
        imported_at TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        rule TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_rows (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL REFERENCES import_batches(id),
        row_sha256 TEXT NOT NULL,
        row_date TEXT,
        source TEXT NOT NULL,
        dimension_key TEXT,
        dimension_value TEXT,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        payload TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_raw_rows_date ON raw_rows(row_date)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_raw_rows_metric ON raw_rows(metric)
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_items (
        id TEXT PRIMARY KEY,
        captured_at TEXT NOT NULL,
        captured_by TEXT NOT NULL,
        kind TEXT NOT NULL,
        path TEXT,
        inline_text TEXT,
        sha256 TEXT,
        size_bytes INTEGER,
        source_description TEXT,
        related_query TEXT,
        related_url TEXT,
        related_prompt_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_findings (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        recommendation TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        evidence_ids TEXT NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS changes (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        scope_urls TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'proposed',
        proposed_by TEXT NOT NULL,
        approved_by TEXT,
        approved_at TEXT,
        deployed_at TEXT,
        verified_at TEXT,
        pre_evidence_ids TEXT NOT NULL DEFAULT '[]',
        post_evidence_ids TEXT NOT NULL DEFAULT '[]',
        measurement_window TEXT,
        result_summary TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scorecards (
        id TEXT PRIMARY KEY,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        metrics_snapshot TEXT NOT NULL,
        highlights TEXT NOT NULL DEFAULT '[]',
        changes_in_period TEXT NOT NULL DEFAULT '[]',
        export_path TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS backlog_items (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT NOT NULL,
        impact REAL NOT NULL,
        effort REAL NOT NULL,
        score REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        evidence_ids TEXT NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metric_definitions (
        id TEXT PRIMARY KEY,
        family TEXT NOT NULL,
        name TEXT NOT NULL,
        source TEXT NOT NULL,
        grain TEXT NOT NULL,
        formula TEXT NOT NULL,
        freshness TEXT NOT NULL DEFAULT 'period'
    )
    """,
]


class StoreError(Exception):
    """Raised for invalid store operations."""


class ClientStore:
    """One client's SQLite database. All reads/writes are single-store."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            for stmt in SCHEMA:
                con.execute(stmt)
            con.commit()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    # ---------- generic row helpers ----------

    @staticmethod
    def _j(value: Iterable) -> str:
        return json.dumps(list(value))

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        return dict(row)

    # ---------- imports ----------

    def batch_by_sha256(self, file_sha256: str) -> Optional[ImportBatch]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM import_batches WHERE file_sha256 = ?",
                (file_sha256,),
            ).fetchone()
        return ImportBatch(**self._row(row)) if row else None

    def add_batch_and_rows(
        self,
        source_family: str,
        source_name: str,
        file_name: Optional[str],
        file_sha256: Optional[str],
        rule: str,
        rows: Iterable[RawRow],
        batch_id: Optional[str] = None,
    ) -> ImportBatch:
        row_list = list(rows)
        batch = ImportBatch(
            id=batch_id or new_id(),
            source_family=source_family,
            source_name=source_name,
            file_name=file_name,
            file_sha256=file_sha256,
            imported_at=utc_now(),
            row_count=len(row_list),
            rule=rule,
        )
        with self._connect() as con:
            con.execute(
                """INSERT INTO import_batches
                   (id, source_family, source_name, file_name, file_sha256,
                    imported_at, row_count, rule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    batch.id,
                    batch.source_family,
                    batch.source_name,
                    batch.file_name,
                    batch.file_sha256,
                    batch.imported_at,
                    batch.row_count,
                    batch.rule,
                ),
            )
            con.executemany(
                """INSERT INTO raw_rows
                   (id, batch_id, row_sha256, row_date, source, dimension_key,
                    dimension_value, metric, value, payload)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        r.id,
                        r.batch_id,
                        r.row_sha256,
                        r.row_date,
                        r.source,
                        r.dimension_key,
                        r.dimension_value,
                        r.metric,
                        r.value,
                        r.payload,
                    )
                    for r in row_list
                ],
            )
            con.commit()
        return batch

    def list_batches(self) -> list[ImportBatch]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM import_batches ORDER BY imported_at DESC"
            ).fetchall()
        return [ImportBatch(**self._row(r)) for r in rows]

    def rows_for_metrics(
        self, metrics: Iterable[str], start: Optional[str] = None, end: Optional[str] = None
    ) -> list[RawRow]:
        metric_list = list(metrics)
        sql = "SELECT * FROM raw_rows WHERE metric IN ({})".format(
            ",".join("?" * len(metric_list))
        )
        params: list = list(metric_list)
        if start:
            sql += " AND row_date >= ?"
            params.append(start)
        if end:
            sql += " AND row_date <= ?"
            params.append(end)
        sql += " ORDER BY row_date"
        with self._connect() as con:
            rows = con.execute(sql, params).fetchall()
        return [RawRow(**self._row(r)) for r in rows]

    def row_count(self) -> int:
        with self._connect() as con:
            return con.execute("SELECT COUNT(*) FROM raw_rows").fetchone()[0]

    # ---------- evidence ----------

    def add_evidence(self, item: EvidenceItem) -> EvidenceItem:
        with self._connect() as con:
            con.execute(
                """INSERT INTO evidence_items
                   (id, captured_at, captured_by, kind, path, inline_text,
                    sha256, size_bytes, source_description, related_query,
                    related_url, related_prompt_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.id,
                    item.captured_at,
                    item.captured_by,
                    item.kind,
                    item.path,
                    item.inline_text,
                    item.sha256,
                    item.size_bytes,
                    item.source_description,
                    item.related_query,
                    item.related_url,
                    item.related_prompt_id,
                ),
            )
            con.commit()
        return item

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceItem]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM evidence_items WHERE id = ?", (evidence_id,)
            ).fetchone()
        return EvidenceItem(**self._row(row)) if row else None

    def list_evidence(self) -> list[EvidenceItem]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM evidence_items ORDER BY captured_at DESC"
            ).fetchall()
        return [EvidenceItem(**self._row(r)) for r in rows]

    def evidence_ids_exist(self, ids: Iterable[str]) -> bool:
        ids = list(ids)
        if not ids:
            return False
        with self._connect() as con:
            found = con.execute(
                "SELECT COUNT(*) FROM evidence_items WHERE id IN ({})".format(
                    ",".join("?" * len(ids))
                ),
                ids,
            ).fetchone()[0]
        return found == len(ids)

    # ---------- audits ----------

    def add_finding(self, finding: AuditFinding) -> AuditFinding:
        with self._connect() as con:
            con.execute(
                """INSERT INTO audit_findings
                   (id, created_at, category, severity, title, description,
                    recommendation, status, evidence_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    finding.id,
                    finding.created_at,
                    finding.category,
                    finding.severity,
                    finding.title,
                    finding.description,
                    finding.recommendation,
                    finding.status,
                    self._j(finding.evidence_ids),
                ),
            )
            con.commit()
        return finding

    def list_findings(self) -> list[AuditFinding]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM audit_findings ORDER BY created_at DESC"
            ).fetchall()
        findings = []
        for r in rows:
            d = self._row(r)
            d["evidence_ids"] = json.loads(d["evidence_ids"])
            findings.append(AuditFinding(**d))
        return findings

    def set_finding_status(self, finding_id: str, status: str) -> None:
        with self._connect() as con:
            cur = con.execute(
                "UPDATE audit_findings SET status = ? WHERE id = ?",
                (status, finding_id),
            )
            con.commit()
        if cur.rowcount == 0:
            raise StoreError(f"unknown finding: {finding_id}")

    # ---------- changes ----------

    def add_change(self, change: ChangeEntry) -> ChangeEntry:
        with self._connect() as con:
            con.execute(
                """INSERT INTO changes
                   (id, created_at, title, description, scope_urls, status,
                    proposed_by, approved_by, approved_at, deployed_at,
                    verified_at, pre_evidence_ids, post_evidence_ids,
                    measurement_window, result_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    change.id,
                    change.created_at,
                    change.title,
                    change.description,
                    self._j(change.scope_urls),
                    change.status,
                    change.proposed_by,
                    change.approved_by,
                    change.approved_at,
                    change.deployed_at,
                    change.verified_at,
                    self._j(change.pre_evidence_ids),
                    self._j(change.post_evidence_ids),
                    (
                        change.measurement_window.model_dump_json()
                        if change.measurement_window
                        else None
                    ),
                    change.result_summary.model_dump_json()
                    if change.result_summary
                    else None,
                ),
            )
            con.commit()
        return change

    def get_change(self, change_id: str) -> Optional[ChangeEntry]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM changes WHERE id = ?", (change_id,)
            ).fetchone()
        return self._change_from_row(row) if row else None

    @classmethod
    def _change_from_row(cls, row: sqlite3.Row) -> ChangeEntry:
        d = dict(row)
        d["scope_urls"] = json.loads(d["scope_urls"])
        d["pre_evidence_ids"] = json.loads(d["pre_evidence_ids"])
        d["post_evidence_ids"] = json.loads(d["post_evidence_ids"])
        d["measurement_window"] = (
            json.loads(d["measurement_window"]) if d["measurement_window"] else None
        )
        d["result_summary"] = (
            json.loads(d["result_summary"]) if d["result_summary"] else None
        )
        return ChangeEntry(**d)

    def list_changes(self) -> list[ChangeEntry]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM changes ORDER BY created_at DESC"
            ).fetchall()
        return [self._change_from_row(r) for r in rows]

    def update_change(self, change: ChangeEntry) -> ChangeEntry:
        with self._connect() as con:
            con.execute(
                """UPDATE changes SET
                     status = ?, approved_by = ?, approved_at = ?,
                     deployed_at = ?, verified_at = ?,
                     pre_evidence_ids = ?, post_evidence_ids = ?,
                     measurement_window = ?, result_summary = ?
                   WHERE id = ?""",
                (
                    change.status,
                    change.approved_by,
                    change.approved_at,
                    change.deployed_at,
                    change.verified_at,
                    self._j(change.pre_evidence_ids),
                    self._j(change.post_evidence_ids),
                    (
                        change.measurement_window.model_dump_json()
                        if change.measurement_window
                        else None
                    ),
                    change.result_summary.model_dump_json()
                    if change.result_summary
                    else None,
                    change.id,
                ),
            )
            con.commit()
        return change

    # ---------- scorecards ----------

    def add_scorecard(self, card: Scorecard) -> Scorecard:
        with self._connect() as con:
            con.execute(
                """INSERT INTO scorecards
                   (id, period_start, period_end, generated_at,
                    metrics_snapshot, highlights, changes_in_period, export_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    card.id,
                    card.period_start,
                    card.period_end,
                    card.generated_at,
                    json.dumps(card.metrics_snapshot),
                    self._j(card.highlights),
                    self._j(card.changes_in_period),
                    card.export_path,
                ),
            )
            con.commit()
        return card

    def list_scorecards(self) -> list[Scorecard]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM scorecards ORDER BY generated_at DESC"
            ).fetchall()
        cards = []
        for r in rows:
            d = self._row(r)
            d["metrics_snapshot"] = json.loads(d["metrics_snapshot"])
            d["highlights"] = json.loads(d["highlights"])
            d["changes_in_period"] = json.loads(d["changes_in_period"])
            cards.append(Scorecard(**d))
        return cards

    # ---------- backlog ----------

    def add_backlog_item(self, item: BacklogItem) -> BacklogItem:
        with self._connect() as con:
            con.execute(
                """INSERT INTO backlog_items
                   (id, created_at, title, description, category, impact,
                    effort, score, status, evidence_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.id,
                    item.created_at,
                    item.title,
                    item.description,
                    item.category,
                    item.impact,
                    item.effort,
                    item.score,
                    item.status,
                    self._j(item.evidence_ids),
                ),
            )
            con.commit()
        return item

    def list_backlog(self) -> list[BacklogItem]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM backlog_items ORDER BY score DESC, created_at DESC"
            ).fetchall()
        items = []
        for r in rows:
            d = self._row(r)
            d["evidence_ids"] = json.loads(d["evidence_ids"])
            items.append(BacklogItem(**d))
        return items

    # ---------- metric definitions ----------

    def seed_metric_definitions(self, definitions: Iterable[MetricDefinition]) -> None:
        with self._connect() as con:
            con.executemany(
                """INSERT OR IGNORE INTO metric_definitions
                   (id, family, name, source, grain, formula, freshness)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        d.id,
                        d.family,
                        d.name,
                        d.source,
                        d.grain,
                        d.formula,
                        d.freshness,
                    )
                    for d in definitions
                ],
            )
            con.commit()

    def list_metric_definitions(self) -> list[MetricDefinition]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM metric_definitions ORDER BY family, id"
            ).fetchall()
        return [MetricDefinition(**self._row(r)) for r in rows]

    def definition(self, metric_id: str) -> Optional[MetricDefinition]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM metric_definitions WHERE id = ?", (metric_id,)
            ).fetchone()
        return MetricDefinition(**self._row(row)) if row else None

    # ---------- schema introspection (isolation proof) ----------

    def tables(self) -> list[str]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        return [r[0] for r in rows]

    def columns(self, table: str) -> list[str]:
        with self._connect() as con:
            rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        return [r["name"] for r in rows]
