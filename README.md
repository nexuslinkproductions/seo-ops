# seo-ops

Client-isolated SEO, AEO, GEO, analytics, evidence, and reporting operations product.

This repository is a **standalone planning and implementation workspace** for a
multi-client operations dashboard. It is completely independent of any other
system. All product knowledge lives in `docs/`; production code is added later
by a separate build task per `docs/handoff/DEEPSEEK-BUILD-HANDOFF.md`.

## Current state

- Phase: planning documentation complete; implementation not yet started.
- Source of truth: the documents under `docs/`.

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

## Repository rules

- Nothing under `data/` is committed; it holds per-client local stores.
- No secrets are committed. Ever.
- Implementation must follow the handoff document and the acceptance criteria.
