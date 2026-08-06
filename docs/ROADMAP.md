# MVP Scope and Phased Roadmap

Status: planning baseline (2026-08-06)

## MVP (Phase 1) — must-have

1. Client registry + per-client SQLite stores.
2. CSV/JSON ingestion for Search Console-style performance exports, crawl
   exports, analytics exports, and GEO probe JSON.
3. Evidence capture with SHA-256 hashing and linkage.
4. Change log lifecycle with before/after evidence requirement at verify time.
5. Metric computation for SEO, AEO, GEO, analytics families with
   period-over-period deltas.
6. Local dashboard (loopback, server-rendered): overview, trends, evidence,
   audits, changes, scorecards, backlog.
7. Scorecard artifact generation (HTML + Markdown export) per client.
8. Sales-prioritization backlog with impact/effort scoring.
9. Pure-Python evidence verification path.
10. Pytest suite including the client-isolation proof.

## Phase 2 — performance and integrity

11. Rust `ops-core verify-evidence` (parallel hashing) + Python fallback.
12. Rust `ops-core validate-csv` for large exports.
13. Integrity dashboard panel surfacing mismatch reports.

## Phase 3 — live ingestion

14. Search Console API ingestion (read-only) behind the normalized schema.
15. GA4 Data API ingestion (read-only).
16. Scheduled ingestion runs.

## Phase 4 — GEO automation

17. Provider-compliant automated GEO probing for the fixed prompt set.
18. Answer-diff detection over time per prompt.

## Phase 5 — hardening (only if demanded)

19. Multi-user access: requires ADR, authentication, and re-validation of the
    isolation model.
20. Optional hosted client portal for scorecard delivery.

## Explicitly out of scope (all phases, unless re-ADR'd)

- Cross-client benchmarking views.
- Automated website mutation.
- Billing/CRM.
