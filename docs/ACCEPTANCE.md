# Acceptance Criteria

Status: planning baseline (2026-08-06)

The MVP is accepted when all of the following hold, verified by commands run
in the repo:

## A. Isolation

1. An automated test creates two clients, inserts distinct records for each,
   and asserts each record is unreachable from the other client's context.
2. No domain table contains a `client_id` column; isolation is by store.
3. Scorecard export for client A writes only under client A's directory.

## B. Ingestion

4. Sample Search Console-style CSV, crawl CSV, analytics CSV, and GEO probe
   JSON fixtures each ingest without error and produce normalized rows.
5. Re-ingesting the same file does not duplicate raw rows (idempotent import
   key) or is explicitly recorded as a new import batch with a documented
   rule.

## C. Evidence and change flow

6. Capturing an evidence file stores it content-addressed and records a
   matching SHA-256 in the store.
7. A change cannot transition to `verified` without at least one pre and one
   post evidence item and a defined measurement window.
8. Verification computes and stores a before/after metric delta.

## D. Metrics and scorecards

9. Each metric family (SEO, AEO, GEO, analytics) has at least one computed
   metric with a period-over-period delta on the dashboard.
10. A scorecard artifact (HTML and Markdown) generates per client and
    references its metric definitions.

## E. Integrity

11. The evidence verification command reports a clean tree as clean and flags
    a deliberately corrupted file as a mismatch (test with fixture).
12. When the Rust binary is absent, the Python fallback performs the same
    check.

## F. Dashboard

13. The local server binds to loopback only and serves the seven MVP views
    per client.
14. Every route requires a client context; there is no global data view.

## G. Repository hygiene

15. `data/`, `.env`, and secrets are gitignored and absent from history.
16. All docs listed in `README.md` exist and are internally consistent.
17. Test suite passes: `python3 -m pytest` (and `cargo test` when the Rust
    crate exists).
