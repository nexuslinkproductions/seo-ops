"""OpenSEO / DataForSEO file-import adapter (credential-free boundary).

This adapter accepts sanitized, local result exports (JSON or CSV) and maps
them into the existing per-client normalized metric, evidence, and backlog
model. It never reads, copies, prints, or stores credentials, never touches
the OpenSEO installation, and never makes network calls. Exports that contain
credential-looking fields are rejected before anything is written.

Import key: SHA-256 of the sanitized canonical export (ADR-004). Re-importing
identical content returns the existing batch without duplicating raw rows.
Evidence captures only the sanitized canonical export, content-addressed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from .backlog import add_item as backlog_add
from .evidence import capture_evidence as capture_evidence_item
from .ids import new_id
from .ingest import _emit, _row_hash, IngestError
from .models import ImportBatch, RawRow
from .store import ClientStore

IMPORT_RULE = (
    "idempotent-sanitized-content: canonical SHA-256 is the import key "
    "(ADR-004)"
)

# Fields that indicate an export still contains credential material. Any
# match (case-insensitive, on JSON keys or CSV headers) rejects the import.
FORBIDDEN_TOKENS = {
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
    "credential",
    "access_key",
    "client_secret",
}

# Metric ids used by this adapter; they are defined in ops/metrics.py under
# the seo family and stored in raw_rows under the same names.
METRIC_KEYWORD_VOLUME = "keyword_search_volume"
METRIC_KEYWORD_CPC = "keyword_cpc"
METRIC_KEYWORD_COMPETITION = "keyword_competition"
METRIC_KEYWORD_DIFFICULTY = "keyword_difficulty"
METRIC_SERP_POSITION = "serp_position"

_NUMBER_KEYS = {
    "searchvolume": "volume",
    "volume": "volume",
    "cpc": "cpc",
    "competition": "competition",
    "keyworddifficulty": "difficulty",
    "difficulty": "difficulty",
    "kd": "difficulty",
}
_TEXT_KEYS = {
    "keyword": "keyword",
    "key": "keyword",
    "query": "keyword",
    "url": "url",
    "domain": "domain",
    "position": "position",
    "rank": "position",
    "rankabsolute": "position",
}


def _normalize_header(header: str) -> str:
    return "".join(ch for ch in header.strip().lower() if ch.isalnum())


def _as_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check_forbidden(keys: list[str], context: str) -> None:
    normalized = [_normalize_header(k) for k in keys]
    for key in normalized:
        for token in FORBIDDEN_TOKENS:
            if token in key:
                raise IngestError(
                    f"export rejected: {context} contains credential-looking "
                    f"field ({token}). Strip credentials from the export "
                    "before importing."
                )


def _iter_json_keys(value) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        keys.extend(value.keys())
        for v in value.values():
            keys.extend(_iter_json_keys(v))
    elif isinstance(value, list):
        for v in value:
            keys.extend(_iter_json_keys(v))
    return keys


def _iter_json_entries(value) -> list[dict]:
    """Flatten DataForSEO-style envelopes into a list of result dicts."""
    if isinstance(value, list):
        out: list[dict] = []
        for item in value:
            out.extend(_iter_json_entries(item))
        return out
    if not isinstance(value, dict):
        return []
    if "result" in value and isinstance(value["result"], list):
        out = []
        for item in value["result"]:
            out.extend(_iter_json_entries(item))
        return out
    if "tasks" in value and isinstance(value["tasks"], list):
        out = []
        for task in value["tasks"]:
            out.extend(_iter_json_entries(task))
        return out
    return [value]


def _keyword_data(entry: dict) -> dict:
    kd = entry.get("keyword_data")
    return kd if isinstance(kd, dict) else entry


def _parse_json(path: Path, batch_id: str, captured_at: Optional[str]) -> list[RawRow]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IngestError(f"invalid OpenSEO JSON export in {path.name}: {exc}") from exc
    _check_forbidden(_iter_json_keys(data), path.name)
    rows: list[RawRow] = []
    for entry in _iter_json_entries(data):
        kd = _keyword_data(entry)
        keyword = (
            kd.get("keyword")
            or entry.get("key")
            or entry.get("query")
        )
        if not keyword:
            continue
        ki = kd.get("keyword_info") if isinstance(kd.get("keyword_info"), dict) else kd
        volume = _as_float(ki.get("search_volume"))
        cpc = _as_float(ki.get("cpc"))
        competition = _as_float(ki.get("competition"))
        kp = kd.get("keyword_properties") if isinstance(kd.get("keyword_properties"), dict) else {}
        difficulty = _as_float(
            kp.get("keyword_difficulty")
            or kd.get("keyword_difficulty")
            or kd.get("difficulty")
            or entry.get("keyword_difficulty")
        )
        row_date = (
            (entry.get("last_updated_time") or entry.get("captured_at") or captured_at or "")
        )[:10] or None
        payload = {"keyword": keyword, "engine": "openseo"}
        if volume is not None:
            payload["search_volume"] = volume
            _emit(
                rows, batch_id, "openseo", payload, METRIC_KEYWORD_VOLUME,
                volume, row_date, "keyword", keyword,
            )
        if cpc is not None:
            payload["cpc"] = cpc
            _emit(
                rows, batch_id, "openseo", payload, METRIC_KEYWORD_CPC,
                cpc, row_date, "keyword", keyword,
            )
        if competition is not None:
            payload["competition"] = competition
            _emit(
                rows, batch_id, "openseo", payload, METRIC_KEYWORD_COMPETITION,
                competition, row_date, "keyword", keyword,
            )
        if difficulty is not None:
            payload["difficulty"] = difficulty
            _emit(
                rows, batch_id, "openseo", payload, METRIC_KEYWORD_DIFFICULTY,
                difficulty, row_date, "keyword", keyword,
            )
        serp_items = entry.get("items")
        if not isinstance(serp_items, list):
            serp_item = entry.get("serp_item")
            serp_items = [serp_item] if isinstance(serp_item, dict) else []
            if entry.get("rank_absolute") is not None:
                serp_items.append(entry)
        for item in serp_items:
            position = _as_float(
                item.get("rank_absolute")
                or item.get("rank")
                or item.get("position")
            )
            if position is None:
                continue
            url = item.get("url")
            domain = item.get("domain")
            serp_payload = {
                "keyword": keyword,
                "url": url or "",
                "domain": domain or "",
                "engine": "openseo",
            }
            _emit(
                rows, batch_id, "openseo", serp_payload, METRIC_SERP_POSITION,
                position, row_date, "url", url or keyword,
            )
    return rows


def _parse_csv(path: Path, batch_id: str, captured_at: Optional[str]) -> list[RawRow]:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        raise IngestError(f"cannot read {path.name}: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise IngestError(f"no header row in {path.name}")
    _check_forbidden(list(reader.fieldnames), path.name)
    rows: list[RawRow] = []
    for raw in reader:
        mapped: dict[str, str] = {}
        for header, value in raw.items():
            target = _TEXT_KEYS.get(_normalize_header(header))
            if target and value not in (None, ""):
                mapped[target] = value
            number = _NUMBER_KEYS.get(_normalize_header(header))
            if number and value not in (None, ""):
                mapped[number] = value
        keyword = mapped.get("keyword")
        if not keyword:
            continue
        payload = {"keyword": keyword, "engine": "openseo"}
        row_date = (mapped.get("date") or captured_at or "")[:10] or None
        volume = _as_float(mapped.get("volume"))
        cpc = _as_float(mapped.get("cpc"))
        competition = _as_float(mapped.get("competition"))
        difficulty = _as_float(mapped.get("difficulty"))
        position = _as_float(mapped.get("position"))
        if volume is not None:
            payload["search_volume"] = volume
            _emit(rows, batch_id, "openseo", payload, METRIC_KEYWORD_VOLUME, volume, row_date, "keyword", keyword)
        if cpc is not None:
            payload["cpc"] = cpc
            _emit(rows, batch_id, "openseo", payload, METRIC_KEYWORD_CPC, cpc, row_date, "keyword", keyword)
        if competition is not None:
            payload["competition"] = competition
            _emit(rows, batch_id, "openseo", payload, METRIC_KEYWORD_COMPETITION, competition, row_date, "keyword", keyword)
        if difficulty is not None:
            payload["difficulty"] = difficulty
            _emit(rows, batch_id, "openseo", payload, METRIC_KEYWORD_DIFFICULTY, difficulty, row_date, "keyword", keyword)
        if position is not None:
            serp_payload = {
                "keyword": keyword,
                "url": mapped.get("url", ""),
                "domain": mapped.get("domain", ""),
                "engine": "openseo",
            }
            _emit(rows, batch_id, "openseo", serp_payload, METRIC_SERP_POSITION, position, row_date, "url", mapped.get("url") or keyword)
    return rows


def _parse_export(path: Path, batch_id: str) -> list[RawRow]:
    suffix = path.suffix.lower()
    captured_at = None
    if suffix == ".json":
        return _parse_json(path, batch_id, captured_at)
    if suffix == ".csv":
        return _parse_csv(path, batch_id, captured_at)
    raise IngestError(
        f"unsupported export format for {path.name}: expected .json or .csv"
    )


def _canonical(rows: list[RawRow]) -> tuple[bytes, str]:
    canonical = {
        "source": "openseo",
        "rows": [
            {
                "row_date": r.row_date,
                "metric": r.metric,
                "value": r.value,
                "dimension_key": r.dimension_key,
                "dimension_value": r.dimension_value,
                "payload": json.loads(r.payload),
            }
            for r in rows
        ],
    }
    raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return raw, hashlib.sha256(raw).hexdigest()


def _derive_backlog(store: ClientStore, rows: list[RawRow], max_items: int) -> list:
    best: dict[str, dict] = {}
    volume_by_keyword: dict[str, float] = {}
    for row in rows:
        payload = json.loads(row.payload)
        keyword = payload.get("keyword") or row.dimension_value
        if not keyword:
            continue
        if row.metric == METRIC_SERP_POSITION:
            current = best.get(keyword)
            if current is None or row.value < current["position"]:
                best[keyword] = {"position": row.value, "payload": payload}
        elif row.metric == METRIC_KEYWORD_VOLUME:
            volume_by_keyword[keyword] = row.value
    items = []
    candidates = [
        (keyword, info)
        for keyword, info in best.items()
        if info["position"] > 10
    ]
    candidates.sort(
        key=lambda pair: (
            volume_by_keyword.get(pair[0], 0.0) / pair[1]["position"],
            pair[0],
        ),
        reverse=True,
    )
    for keyword, info in candidates[:max_items]:
        volume = volume_by_keyword.get(keyword, 0.0)
        impact = min(5.0, max(1.0, volume / 1000.0)) if volume else 2.0
        item = backlog_add(
            store,
            title=f"Improve ranking for '{keyword}' (outside top 10)",
            impact=round(impact, 1),
            effort=3.0,
            category="seo",
            description=(
                f"OpenSEO SERP position {info['position']} for '{keyword}'; "
                "verify title, content, and internal links before changing the site."
            ),
        )
        items.append(item)
    return items


def import_openseo_export(
    store: ClientStore,
    client_dir: Path,
    path: Path,
    *,
    capture_evidence: bool = True,
    build_backlog: bool = False,
    backlog_max: int = 25,
    captured_by: str = "operator",
    source_description: str = "OpenSEO/DataForSEO local export (sanitized)",
) -> dict:
    """Import one sanitized OpenSEO/DataForSEO export into a client store."""
    path = Path(path)
    if not path.is_file():
        raise IngestError(f"file not found: {path}")
    batch_id = new_id()
    rows = _parse_export(path, batch_id)
    if not rows:
        raise IngestError(f"no normalized rows produced from {path.name}")
    canonical_bytes, canonical_sha = _canonical(rows)
    existing = store.batch_by_sha256(canonical_sha)
    if existing is not None:
        return {
            "batch": existing,
            "evidence": [],
            "new_rows": 0,
            "idempotent": True,
            "backlog": [],
        }
    for row in rows:
        row.batch_id = batch_id
    batch = store.add_batch_and_rows(
        source_family="openseo",
        source_name="openseo",
        file_name=path.name,
        file_sha256=canonical_sha,
        rule=IMPORT_RULE,
        rows=rows,
        batch_id=batch_id,
    )
    evidence_ids: list[str] = []
    if capture_evidence:
        fd, tmp_path = tempfile.mkstemp(prefix="openseo-sanitized-", suffix=".json")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(canonical_bytes)
            item = capture_evidence_item(
                store,
                client_dir,
                "export_file",
                file_path=Path(tmp_path),
                captured_by=captured_by,
                source_description=source_description,
            )
            evidence_ids.append(item.id)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    backlog_items: list = []
    if build_backlog:
        backlog_items = _derive_backlog(store, rows, backlog_max)
    return {
        "batch": batch,
        "evidence": evidence_ids,
        "new_rows": len(rows),
        "idempotent": False,
        "backlog": backlog_items,
    }
