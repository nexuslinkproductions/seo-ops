# ADR-002: Import Idempotency and Normalized Row Schema

Status: accepted (2026-08-06)

## Context

The plan (research 02, acceptance B5) requires that re-ingesting an export
file not duplicate raw rows, either via an idempotent import key or an
explicitly recorded rule for new import batches.

## Decision

- The SHA-256 digest of the uploaded file is the import key. Importing
  identical content returns the existing `import_batches` row and inserts
  nothing; the applied rule is recorded on every batch.
- New content always produces a new import batch with a new id and a new
  `file_sha256`.
- Normalized rows follow the common grain `(row_date, source, dimension_key,
  dimension_value, metric, value)` plus a full `payload` JSON so derived
  metrics can be recomputed later.
- CSV sources map to metrics: search console (`clicks`, `impressions`,
  `ctr`, `position`), crawl (`crawl_pages`, `crawl_indexable`,
  `crawl_error`, `canonical_valid`), analytics (`sessions`,
  `engaged_sessions`, `conversions`, `conversion_rate`, `users`), AEO
  (`aeo_snippet_owned`, `aeo_paa`, `aeo_sd_valid`), GEO (`geo_answer`,
  `geo_citation`, `geo_mention`, `geo_citation_position`,
  `geo_total_citations`).

## Consequences

- Raw rows are append-only; corrections are new files/batches.
- Crawl exports have no per-row date; their rows carry no `row_date` and are
  treated as point-in-time snapshots (see ADR-003).

