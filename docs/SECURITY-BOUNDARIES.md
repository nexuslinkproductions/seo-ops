# Security and Privacy Boundaries

Status: planning baseline (2026-08-06)

## 1. Client isolation (hard boundary)

- Per-client SQLite stores; no cross-client tables or queries.
- No cross-client aggregates in MVP. Introducing any cross-client view
  requires a new ADR and explicit operator opt-in.
- Exports are written only inside the owning client's directory.
- Test suite must include an isolation proof (insert for client A, assert
  unreachable from client B's context).

## 2. Network posture

- Dashboard binds to loopback (127.0.0.1) only.
- MVP performs no outbound network calls; ingestion is file-based.
- Future API ingestion (later phase) must be read-only against provider APIs
  and store credentials outside the repo (environment or OS keychain).

## 3. Secrets

- No secrets in the repository; `.env` and key files are gitignored.
- The app never logs credential material.

## 4. External services

- The product never mutates external services (no CMS/WordPress writes). It
  documents changes; humans deploy them.
- Automated GEO probing, when added later, must comply with each provider's
  terms of service and rate limits.

## 5. Data protection

- All client data remains on the operator's machine under `data/`.
- Evidence files are content-addressed by SHA-256; the integrity command can
  detect tampering or corruption.
- Client data may contain personal data via analytics exports; the operator is
  responsible for lawful handling, retention, and deletion per client
  contract. Deleting a client removes its entire `data/clients/<id>/` tree.

## 6. Change governance

- Changes follow propose -> approve -> deploy -> verify. Approval is recorded
  with an approver name and timestamp; there is no implicit approval.
- Evidence is immutable; audit findings and scorecards reference evidence IDs
  rather than embedding mutable copies.
