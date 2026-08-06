"""Client registry and store resolution.

The registry holds only identity data (id, name, domains, prompt set) in a
single `registry.db`. All domain data lives in the client's own store. There
is no cross-client query surface.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

from .ids import utc_now
from .models import ClientInfo
from .store import ClientStore


class ClientError(Exception):
    """Raised for registry/store resolution problems."""


def default_data_root() -> Path:
    env = os.environ.get("SEO_OPS_DATA_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "data"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "client"


def ensure_registry(data_root: Path) -> Path:
    data_root = Path(data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    registry_path = data_root / "registry.db"
    with sqlite3.connect(registry_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                domains TEXT NOT NULL DEFAULT '[]',
                geo_prompts TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        con.commit()
    return registry_path


def _unique_client_id(con: sqlite3.Connection, name: str) -> str:
    base = _slugify(name)
    candidate = base
    suffix = 2
    while con.execute("SELECT 1 FROM clients WHERE id = ?", (candidate,)).fetchone():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def create_client(
    data_root: Path,
    name: str,
    domains: list[str] | None = None,
    geo_prompts: list[str] | None = None,
    explicit_id: str | None = None,
) -> ClientInfo:
    registry_path = ensure_registry(data_root)
    with sqlite3.connect(registry_path) as con:
        client_id = (
            re.sub(r"[^a-z0-9-]", "", explicit_id).strip("-")
            if explicit_id
            else _unique_client_id(con, name)
        )
        if con.execute("SELECT 1 FROM clients WHERE id = ?", (client_id,)).fetchone():
            raise ClientError(f"client already exists: {client_id}")
        info = ClientInfo(
            id=client_id,
            name=name,
            created_at=utc_now(),
            domains=domains or [],
            geo_prompts=geo_prompts or [],
        )
        con.execute(
            """INSERT INTO clients (id, name, created_at, domains, geo_prompts)
               VALUES (?, ?, ?, ?, ?)""",
            (
                info.id,
                info.name,
                info.created_at,
                json.dumps(info.domains),
                json.dumps(info.geo_prompts),
            ),
        )
        con.commit()
    store = ClientStore(client_dir(data_root, client_id) / "client.db")
    from .metrics import default_metric_definitions

    store.seed_metric_definitions(default_metric_definitions())
    return info


def client_dir(data_root: Path, client_id: str) -> Path:
    return Path(data_root) / "clients" / client_id


def get_client(data_root: Path, client_id: str) -> ClientInfo:
    registry_path = ensure_registry(data_root)
    with sqlite3.connect(registry_path) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if not row:
        raise ClientError(f"unknown client: {client_id}")
    d = dict(row)
    d["domains"] = json.loads(d["domains"])
    d["geo_prompts"] = json.loads(d["geo_prompts"])
    return ClientInfo(**d)


def list_clients(data_root: Path) -> list[ClientInfo]:
    registry_path = ensure_registry(data_root)
    with sqlite3.connect(registry_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM clients ORDER BY name").fetchall()
    clients = []
    for r in rows:
        d = dict(r)
        d["domains"] = json.loads(d["domains"])
        d["geo_prompts"] = json.loads(d["geo_prompts"])
        clients.append(ClientInfo(**d))
    return clients


def open_client_store(data_root: Path, client_id: str) -> ClientStore:
    get_client(data_root, client_id)  # raises if unknown
    return ClientStore(client_dir(data_root, client_id) / "client.db")
