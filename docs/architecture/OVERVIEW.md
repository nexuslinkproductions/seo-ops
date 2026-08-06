# Architecture Overview

Status: proposed (2026-08-06)

## 1. Shape

Local-first, single-operator, multi-client application:

- **Python package `ops/`** — application core.
- **Rust crate `rust/ops-core/`** — evidence integrity and bulk validation CLI.
- **Per-client SQLite stores** under `data/clients/<client-id>/`.
- **Local web dashboard** served by Python (loopback only) with server-rendered
  HTML; plus exportable scorecard artifacts.

```
seo-ops/
  ops/                  # Python package
    __init__.py
    models.py           # pydantic domain models
    store.py            # per-client SQLite repository layer
    clients.py          # client registry + store resolution
    ingest.py           # CSV/JSON importers -> normalized rows
    metrics.py          # metric computation + before/after deltas
    evidence.py         # evidence capture, hashing, linkage
    changeflow.py       # change lifecycle (propose/approve/deploy/verify)
    scorecard.py        # scorecard computation + rendering
    backlog.py          # sales-prioritization backlog (impact/effort)
    serve.py            # local HTTP app server (loopback)
    cli.py              # operator CLI entry points
    templates/          # dashboard HTML templates
    static/             # CSS/JS assets
  rust/ops-core/        # Rust crate
    Cargo.toml
    src/main.rs         # `ops-core verify-evidence`, `ops-core validate-csv`
  tests/                # pytest suite
  docs/                 # this documentation set
  data/                 # gitignored runtime data (per-client stores)
```

## 2. Client isolation mechanism

- A **client registry** (one small SQLite DB at `data/registry.db`, containing
  only client IDs, names, and store paths — no metrics) maps client IDs to
  store directories.
- All domain data lives in the client's own `client.db`. Domain tables carry
  no `client_id` column because the store itself *is* the boundary.
- `store.py` exposes `open_client_store(client_id)`; there is no API that
  opens multiple client stores in one call, and no SQL ever spans stores.
- The web layer requires a client selection; every route is
  `/clients/<client_id>/...` and resolves exactly one store.

## 3. Data flow

1. **Ingest:** operator drops an export file; `ingest.py` parses, validates
  (optionally via `ops-core validate-csv` for large files), and appends
  normalized rows to the client's store. Raw rows are append-only.
2. **Evidence:** `evidence.py` copies a file into the client's `evidence/`
  directory named by SHA-256, records metadata in the store.
3. **Change flow:** `changeflow.py` enforces the lifecycle
  proposed -> approved -> deployed -> verified, requiring pre/post evidence
  before verification.
4. **Metrics/scorecards:** `metrics.py` computes from raw rows on demand;
  `scorecard.py` renders a period artifact into `exports/`.
5. **Integrity:** `ops-core verify-evidence` walks a client's evidence tree,
  re-hashes files, and emits a JSON mismatch report; Python surfaces it in the
  dashboard.

## 4. Rust boundary

- Communication: subprocess with JSON on stdout; exit codes for status.
- Rust holds no domain state and no business rules.
- If Rust is unavailable, Python falls back to a pure-Python (slower)
  verification path so the product never hard-depends on the toolchain.

## 5. Dashboard (MVP)

Server-rendered pages per client:

- Overview: metric-family summary cards with period deltas.
- Trends: time-series tables/simple charts per metric family.
- Evidence: list with hashes, kinds, and linked changes.
- Audits: findings by severity/status.
- Changes: the approved change log with before/after deltas.
- Scorecards: generated artifacts and one-click regeneration.
- Backlog: opportunity list scored by impact/effort for sales prioritization.

No JavaScript framework in MVP; progressive enhancement only.

## 6. Evolution path

- API ingestion (Search Console, GA4) behind the same normalized schema.
- Automated GEO probing with provider-compliant tooling.
- Optional multi-user access would require a new ADR covering authentication
  and re-validating the isolation model.
