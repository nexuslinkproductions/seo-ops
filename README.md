# seo-ops

Client-isolated SEO, AEO, GEO, analytics, evidence, and reporting operations product.

This repository is a **standalone planning and implementation workspace** for a
multi-client operations dashboard. It is completely independent of any other
system. All product knowledge lives in `docs/`; production code is added later
by a separate build task per `docs/handoff/DEEPSEEK-BUILD-HANDOFF.md`.

## Current state

- Phase: MVP implemented (Python core + Rust ops-core); see
  `docs/evidence/BUILD-VERIFICATION.md` for acceptance evidence.
- Source of truth: the documents under `docs/`.

## Running locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 -m pytest
python3 -m ops.cli --help
```

All client data stays under `data/` (gitignored). The dashboard binds to
loopback only: `python3 -m ops.cli serve --port 8765`.

## OpenSEO / DataForSEO imports

The dashboard can consume sanitized local OpenSEO/DataForSEO result exports
(JSON/CSV) per client: `python3 -m ops.cli openseo-import --client <id> --file <path>`.
This boundary is credential-free; see
`docs/openseo/OPERATOR-GUIDE.md` and `config/openseo.env.example`.

## Documentation map

- `docs/research/01-operational-requirements.md` — goals, non-goals, client
  isolation model, workflows.
- `docs/research/02-data-sources-and-metrics.md` — required data sources and
  metric definitions for SEO, AEO, GEO.
- `docs/research/03-evidence-model.md` — before/after evidence, audit
  documentation, approved change log model.
- `docs/research/04-technology-evaluation.md` — Python/Rust roles and the
  C++/C# decision.
- `docs/architecture/OVERVIEW.md` — proposed system architecture.
- `docs/decisions/ADR-001-language-selection.md` — language decision record.
- `docs/SECURITY-BOUNDARIES.md` — security and privacy boundaries.
- `docs/ROADMAP.md` — MVP scope and phased roadmap.
- `docs/ACCEPTANCE.md` — acceptance criteria.
- `docs/handoff/DEEPSEEK-BUILD-HANDOFF.md` — self-contained build handoff.
- `docs/openseo/OPERATOR-GUIDE.md` — OpenSEO import operator guide.
- `docs/decisions/ADR-004-openseo-import-boundary.md` — OpenSEO boundary ADR.
- `config/openseo.env.example` — credential variable template (no values).

## Repository rules

- Nothing under `data/` is committed; it holds per-client local stores.
- No secrets are committed. Ever.
- Implementation must follow the handoff document and the acceptance criteria.
