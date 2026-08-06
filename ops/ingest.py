"""File-first ingestion for SEO/AEO/GEO/analytics exports.

Imports are idempotent by content: the SHA-256 of the uploaded file is the
import key. Re-importing identical content returns the existing batch without
duplicating raw rows (documented rule, recorded on the batch row).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Callable, Optional

from .ids import new_id
from .models import ImportBatch, RawRow
from .store import ClientStore

IMPORT_RULE = "idempotent-file-sha256: identical content returns the existing batch"


class IngestError(Exception):
    """Raised for unreadable or unsupported import files."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _row_hash(
    payload: str, metric: str, row_date: Optional[str],
    dim_key: Optional[str], dim_value: Optional[str], value: float,
) -> str:
    canonical = json.dumps(
        [row_date, metric, dim_key, dim_value, value, payload], sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _as_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (ValueError, AttributeError):
        return None


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {
        "1", "true", "yes", "y", "owned", "valid", "present", "indexable",
    }


def _emit(
    rows: list[RawRow], batch_id: str, source: str, payload: dict,
    metric: str, value: float, row_date: Optional[str],
    dim_key: Optional[str] = None, dim_value: Optional[str] = None,
) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    rows.append(
        RawRow(
            id=new_id(),
            batch_id=batch_id,
            row_sha256=_row_hash(payload_json, metric, row_date, dim_key, dim_value, value),
            row_date=row_date,
            source=source,
            dimension_key=dim_key,
            dimension_value=dim_value,
            metric=metric,
            value=value,
            payload=payload_json,
        )
    )


def _read_csv_rows(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        raise IngestError(f"cannot read {path}: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise IngestError(f"no header row in {path}")
    return [dict(row) for row in reader]


def _parse_search_console(path: Path, batch_id: str) -> list[RawRow]:
    rows = []
    for raw in _read_csv_rows(path):
        row_date = raw.get("Date") or None
        payload = dict(raw)
        dim_key = next(
            (k for k in ("Query", "Page", "Country", "Device") if raw.get(k)),
            None,
        )
        dim_value = raw.get(dim_key) if dim_key else None
        for metric in ("clicks", "impressions", "position"):
            value = _as_float(raw.get(metric.capitalize()) or raw.get(metric.upper()))
            if value is not None:
                _emit(
                    rows, batch_id, "search_console", payload, metric, value,
                    row_date, dim_key, dim_value,
                )
    return rows


def _parse_crawl(path: Path, batch_id: str) -> list[RawRow]:
    rows = []
    for raw in _read_csv_rows(path):
        payload = dict(raw)
        address = raw.get("Address") or ""
        status = _as_float(raw.get("Status Code")) or 0.0
        indexable_text = (raw.get("Indexability") or "").lower()
        indexable = _as_bool(indexable_text) and "non-indexable" not in indexable_text
        canonical = (raw.get("Canonical Link Element 1") or "").strip()
        canonical_ok = 1.0 if (
            canonical and canonical.rstrip("/") == address.rstrip("/")
        ) else 0.0
        _emit(rows, batch_id, "crawl", payload, "crawl_pages", 1.0, None, "page", address)
        _emit(rows, batch_id, "crawl", payload, "crawl_indexable", 1.0 if indexable else 0.0, None, "page", address)
        _emit(rows, batch_id, "crawl", payload, "crawl_error", 1.0 if status >= 400 else 0.0, None, "page", address)
        _emit(rows, batch_id, "crawl", payload, "canonical_valid", canonical_ok, None, "page", address)
    return rows


def _parse_analytics(path: Path, batch_id: str) -> list[RawRow]:
    rows = []
    for raw in _read_csv_rows(path):
        payload = dict(raw)
        row_date = raw.get("Date") or None
        landing = raw.get("Landing page") or raw.get("Landing Page") or None
        for metric in ("sessions", "engaged_sessions", "conversions", "users"):
            for header in (metric, metric.replace("_", " "), metric.title()):
                value = _as_float(raw.get(header))
                if value is not None:
                    _emit(rows, batch_id, "analytics", payload, metric, value, row_date, "landing_page", landing)
                    break
    return rows


def _parse_geo(path: Path, batch_id: str) -> list[RawRow]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IngestError(f"invalid GEO JSON in {path}: {exc}") from exc
    rows = []
    for answer in data.get("answers", []):
        prompt_id = answer.get("prompt_id")
        engine = answer.get("engine", "")
        payload = dict(answer)
        payload["engine"] = engine
        cited = _as_bool(answer.get("client_cited"))
        mentioned = _as_bool(answer.get("brand_mentioned"))
        sources = answer.get("cited_sources") or []
        total_citations = float(len(sources))
        position = 0.0
        if cited:
            for src in sources:
                if str(src.get("url", "")):
                    position = float(src.get("position", 1))
                    break
        row_date = (answer.get("captured_at") or data.get("captured_at") or "")[:10] or None
        dim_key = "prompt_id"
        _emit(rows, batch_id, "geo_probe", payload, "geo_answer", 1.0, row_date, dim_key, prompt_id)
        _emit(rows, batch_id, "geo_probe", payload, "geo_citation", 1.0 if cited else 0.0, row_date, dim_key, prompt_id)
        _emit(rows, batch_id, "geo_probe", payload, "geo_mention", 1.0 if mentioned else 0.0, row_date, dim_key, prompt_id)
        _emit(rows, batch_id, "geo_probe", payload, "geo_citation_position", position, row_date, dim_key, prompt_id)
        _emit(rows, batch_id, "geo_probe", payload, "geo_total_citations", total_citations, row_date, dim_key, prompt_id)
    return rows


def _parse_aeo(path: Path, batch_id: str) -> list[RawRow]:
    rows = []
    if path.suffix.lower() == ".json":
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngestError(f"invalid AEO JSON in {path}: {exc}") from exc
        if isinstance(entries, dict):
            entries = entries.get("answers", [])
    else:
        entries = _read_csv_rows(path)
    for entry in entries:
        query = entry.get("query") or entry.get("Query")
        engine = entry.get("engine") or entry.get("Engine") or ""
        payload = dict(entry)
        row_date = (entry.get("captured_at") or entry.get("Date") or "")[:10] or None
        snippet = _as_bool(entry.get("featured_snippet_owned") or entry.get("featured_snippet"))
        paa = _as_bool(entry.get("paa_present") or entry.get("paa"))
        sd = _as_bool(entry.get("structured_data_valid") or entry.get("structured_data"))
        _emit(rows, batch_id, "aeo_audit", payload, "aeo_snippet_owned", 1.0 if snippet else 0.0, row_date, "query", query)
        _emit(rows, batch_id, "aeo_audit", payload, "aeo_paa", 1.0 if paa else 0.0, row_date, "query", query)
        _emit(rows, batch_id, "aeo_audit", payload, "aeo_sd_valid", 1.0 if sd else 0.0, row_date, "query", query)
    return rows


PARSERS: dict[str, Callable[[Path, str], list[RawRow]]] = {
    "search_console": _parse_search_console,
    "crawl": _parse_crawl,
    "analytics": _parse_analytics,
    "geo": _parse_geo,
    "aeo": _parse_aeo,
}

SOURCE_NAMES = {
    "search_console": "search_console",
    "crawl": "crawl",
    "analytics": "analytics",
    "geo": "geo_probe",
    "aeo": "aeo_audit",
}


def import_file(store: ClientStore, source: str, path: Path) -> ImportBatch:
    """Import one export file into the client's store (idempotent by content)."""
    if source not in PARSERS:
        raise IngestError(f"unsupported source: {source}")
    path = Path(path)
    if not path.is_file():
        raise IngestError(f"file not found: {path}")
    file_sha = _sha256_bytes(path.read_bytes())
    existing = store.batch_by_sha256(file_sha)
    if existing is not None:
        return existing
    batch_id = new_id()
    rows = PARSERS[source](path, batch_id)
    if not rows:
        raise IngestError(f"no normalized rows produced from {path.name}")
    return store.add_batch_and_rows(
        source_family=source,
        source_name=SOURCE_NAMES[source],
        file_name=path.name,
        file_sha256=file_sha,
        rule=IMPORT_RULE,
        rows=rows,
        batch_id=batch_id,
    )
