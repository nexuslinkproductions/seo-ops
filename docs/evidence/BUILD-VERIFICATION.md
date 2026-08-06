# Build Verification — MVP (Phase 1 + Phase 2 core)

Status: verified (2026-08-06)

Toolchain: Python 3.14.6 (venv at `/private/tmp/seo-ops-venv`, pydantic
2.13.4, pytest 9.1.1), Rust 1.96.0.

## Primary commands

```text
$ python3 -m pytest
38 passed in 4.19s

$ cargo test
running 2 tests
test tests::csv_quoted_fields ... ok
test tests::sha256_known_vectors ... ok
test result: ok. 2 passed; 0 failed
```

## A. Isolation

| # | Criterion | Verification command | Result |
|---|---|---|---|
| A1 | Records of one client unreachable from another | `pytest tests/test_isolation.py::test_records_unreachable_across_clients` | passed |
| A2 | No domain table has a `client_id` column | `pytest tests/test_isolation.py::test_no_client_id_column_in_any_domain_table` | passed (schema introspection across all tables) |
| A3 | Scorecard export writes only under owning client dir | `pytest tests/test_isolation.py::test_scorecard_export_writes_only_under_own_client_dir` | passed |

Registry holds identity only: `test_no_cross_client_aggregate_view` asserts
`registry.db` contains exactly the `clients` table.

## B. Ingestion

| # | Criterion | Verification command | Result |
|---|---|---|---|
| B4 | All four fixture types ingest without error | `pytest tests/test_ingestion.py::test_each_fixture_ingests` (parametrized: search console, crawl, analytics, geo, aeo) | passed |
| B5 | Re-ingest does not duplicate raw rows | `pytest tests/test_ingestion.py::test_reingest_same_file_is_idempotent` | passed; rule recorded on every batch (`idempotent-file-sha256...`, ADR-002) |

CLI smoke (scratch root `/private/tmp/seo-ops-smoke`):
re-importing `search-console.csv` returned the existing batch id
`5eb8de37e430` with no new rows.

## C. Evidence and change flow

| # | Criterion | Verification command | Result |
|---|---|---|---|
| C6 | Evidence stored content-addressed with matching SHA-256 | `pytest tests/test_evidence.py::test_capture_stores_content_addressed_file` | passed |
| C7 | `verified` requires pre + post evidence and a defined window | `pytest tests/test_changeflow.py::test_verify_requires_pre_and_post_evidence`, `test_verify_requires_defined_window`, `test_cannot_verify_before_deploy` | passed |
| C8 | Before/after delta computed and stored | `pytest tests/test_changeflow.py::test_verify_stores_before_after_delta` | passed |

CLI smoke: `change-verify ... --metric clicks` produced
`clicks 15.0 -> 26.0 (abs 11.0, rel 0.7333)`.

## D. Metrics and scorecards

| # | Criterion | Verification command | Result |
|---|---|---|---|
| D9 | Every family has a computed metric with a period delta | `pytest tests/test_metrics.py::test_each_family_has_metric_with_delta` | passed |
| D10 | HTML + Markdown scorecard per client references metric definitions | `pytest tests/test_scorecard.py::test_scorecard_generates_html_and_markdown` | passed |

## E. Integrity

| # | Criterion | Verification command | Result |
|---|---|---|---|
| E11 | Clean tree reported clean; corrupted file flagged | `pytest tests/test_evidence.py::test_verify_clean_tree`, `test_verify_flags_corrupted_file`, `test_verify_flags_missing_file` | passed |
| E12 | Python fallback performs the same check without Rust | same tests with `prefer_rust=False`; plus `test_rust_binary_integration_if_built` with the built binary | passed |

CLI smoke (Rust path): `evidence-verify` reported
`integrity tool=rust clean=True checked=2 mismatches=0 missing=0`.
Dashboard evidence view renders `Integrity: CLEAN (2 items, tool rust)`.

## F. Dashboard

| # | Criterion | Verification command | Result |
|---|---|---|---|
| F13 | Loopback-only bind; seven views per client | `pytest tests/test_dashboard.py::test_binds_loopback_only`, `test_all_seven_views_serve` | passed |
| F14 | Every route requires client context; no global view | `pytest tests/test_dashboard.py::test_no_global_data_view` | passed |

Live smoke: `serve --port 8799` on 127.0.0.1; `/clients/smoke-client/overview`
returned 200, `/overview` returned 404, evidence view rendered the Rust
integrity report.

## G. Repository hygiene

| # | Criterion | Verification command | Result |
|---|---|---|---|
| G15 | `data/`, `.env`, secrets gitignored and absent from history | `pytest tests/test_hygiene.py::test_data_and_db_gitignored_and_absent_from_history` | passed (`git ls-files` contains no `data/` or `*.db`) |
| G16 | All docs listed in README exist | `pytest tests/test_hygiene.py::test_all_docs_exist` | passed |
| G17 | Test suite passes | `python3 -m pytest` + `cargo test` | passed |

## Notes

- No commits, pushes, or remotes were created for this build; the existing
  planning documentation commit (`80f4440`) is untouched.
- Crawl snapshot metrics are documented in ADR-003 (point-in-time; deltas
  render as `n/a`).
- Import idempotency and the Rust CLI contract are documented in ADR-002 and
  ADR-003 respectively.

## OpenSEO import boundary (2026-08-06)

Additional verification for the credential-free OpenSEO/DataForSEO adapter
(ADR-004):

```text
$ python3 -m pytest
45 passed, 2 skipped in 3.58s   # includes tests/test_openseo.py
```

- Mapping: JSON and CSV exports produce normalized `keyword_search_volume`,
  `keyword_cpc`, `keyword_competition`, `keyword_difficulty`, and
  `serp_position` rows (`tests/test_openseo.py`).
- Idempotency: re-import returns the existing batch with 0 new rows and no
  new evidence (`test_reimport_is_idempotent`; CLI smoke showed the same
  batch id on repeat import).
- Isolation: OpenSEO rows and evidence for client A are unreachable from
  client B (`test_isolated_across_clients`).
- Credential rejection: exports containing credential-looking fields are
  refused before any write (`test_rejects_credential_fields`), and the
  adapter ignores credential environment variables
  (`test_adapter_ignores_environment_credentials`).
- Evidence: only the sanitized canonical export is captured, content-
  addressed, and verified clean by `evidence-verify`.
