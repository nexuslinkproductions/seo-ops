# seo-ops

Client-isolated SEO, AEO, GEO, analytics, evidence, and reporting operations
toolkit. A single operator can onboard clients, import sanitized search and
analytics exports, track approved changes with before/after evidence, and
generate scorecards, all on a loopback-only local dashboard.

This is the main repository for the SEO service: the dashboard code lives on
`main`, the reusable methodology on the `methodology` branch, and the
operational templates on the `operational-templates` branch.

## Branch layout

| Branch | Contents |
|---|---|
| `main` | Dashboard implementation (Python core + Rust ops-core) and this README |
| `methodology` | The repeatable, approval-gated SEO/AEO/GEO process (`WORKFLOW.md`) |
| `operational-templates` | Probe baseline, change log, sanitization, rollback, and approved-claims templates |

## Quickstart

```bash
git clone https://github.com/nexuslinkproductions/seo-ops.git
cd seo-ops
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest
python3 -m ops.cli --help
```

Start the dashboard (loopback only):

```bash
python3 -m ops.cli serve --port 8765
# open http://127.0.0.1:8765/
```

## How it works

1. Register a client: `python3 -m ops.cli client-add --name Acme --id acme`.
2. Import sanitized exports (JSON/CSV): Search Console, crawl results,
   analytics, GEO probes, or OpenSEO/DataForSEO keyword/SERP exports:
   `python3 -m ops.cli openseo-import --client acme --file path`.
3. Record audit findings, propose and approve changes, capture before/after
   evidence, and verify with measurement windows.
4. Generate scorecards per client and period.

Every client gets its own SQLite store under `data/clients/<id>/`; no query
path spans clients. Client data is never committed.

## Security boundaries

- Credential-free imports: the adapter rejects files containing credential-
  looking fields (`api_key`, `token`, `secret`, and similar).
- Loopback only: the dashboard binds to 127.0.0.1 and makes no outbound
  calls.
- No secrets in the repository, ever. `config/openseo.env.example` names
  variables only; values live in the operator's environment.
- Evidence is content-addressed (SHA-256) and verified on read.

See `docs/SECURITY-BOUNDARIES.md`, `docs/decisions/ADR-004-openseo-import-boundary.md`,
and `docs/openseo/OPERATOR-GUIDE.md` for details.

## Documentation map

- `docs/research/01-operational-requirements.md` - goals, non-goals, client
  isolation model, workflows.
- `docs/research/02-data-sources-and-metrics.md` - data sources and metric
  definitions for SEO, AEO, GEO.
- `docs/research/03-evidence-model.md` - before/after evidence and change log.
- `docs/architecture/OVERVIEW.md` - system architecture.
- `docs/ROADMAP.md`, `docs/ACCEPTANCE.md` - scope and acceptance criteria.
- `docs/evidence/BUILD-VERIFICATION.md` - implementation acceptance evidence.

The client-facing process and templates live on the `methodology` and
`operational-templates` branches.

## Repository rules

- Nothing under `data/` is committed; it holds per-client local stores.
- No secrets are committed. Ever.
- Client-specific artifacts stay out of `main`; they live in private
  per-client branches or private forks.
