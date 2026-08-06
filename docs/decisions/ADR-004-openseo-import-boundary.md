# ADR-004: OpenSEO/DataForSEO Import Boundary (Sanitized Local Files Only)

Status: accepted (2026-08-06)

## Context

The operator runs OpenSEO separately and wants its results combined with the
seo-ops dashboard. The product must not read, copy, print, or enter
credentials, must not modify the OpenSEO installation, and must preserve
client isolation and evidence integrity.

## Decision

- The only supported input is a **sanitized local result export** (JSON or
  CSV) placed on disk by the operator. There is no API call, no network
  access, and no reading of the OpenSEO installation.
- The adapter rejects any export whose JSON keys or CSV headers contain
  credential-looking tokens (`api_key`, `token`, `secret`, `password`,
  `authorization`, `credential`, `access_key`, `client_secret`).
- The import key is the **SHA-256 of the sanitized canonical export**
  (normalized rows only), recorded as `file_sha256` on the import batch.
  Re-importing identical content returns the existing batch (idempotent).
- Evidence captures only the sanitized canonical export, content-addressed
  under the client's `evidence/` directory, linked to the batch.
- Backlog generation is opt-in (`--backlog`) and derives opportunities only
  from SERP rows outside the top 10.
- Future API-based credential setup is a separate step that requires explicit
  operator approval; `config/openseo.env.example` names the variables with no
  values, and credentials never enter the repository.

## Consequences

- No credential material is ever read, copied, printed, stored, or entered by
  the product.
- Idempotency and client isolation reuse the existing import/store model
  (per-client SQLite, no cross-client queries).
- Metric definitions for the five normalized OpenSEO metrics were added to
  the existing seo family; all prior behavior and fixtures are unchanged.
