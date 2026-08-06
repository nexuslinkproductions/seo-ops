# DeepSeek Build Handoff

Status: ready for build task (2026-08-06)

You are the implementation task (DeepSeek V4 Flash lane). Build the MVP of the
client-isolated SEO/AEO/GEO operations dashboard **exactly** per the documents
in this repository. Everything you need is in-repo; do not consult or reuse
any external repository, skill, or memory system.

## 1. Read first (in order)

1. `AGENTS.md` — repository rules (binding).
2. `docs/research/01-operational-requirements.md`
3. `docs/research/02-data-sources-and-metrics.md`
4. `docs/research/03-evidence-model.md`
5. `docs/research/04-technology-evaluation.md`
6. `docs/architecture/OVERVIEW.md`
7. `docs/decisions/ADR-001-language-selection.md`
8. `docs/SECURITY-BOUNDARIES.md`
9. `docs/ROADMAP.md` — build only the "MVP (Phase 1)" list, plus Phase 2 items
   11–12 if time allows (Python fallback paths are mandatory either way).
10. `docs/ACCEPTANCE.md` — your definition of done.

## 2. Build targets

- Python package `ops/` per `docs/architecture/OVERVIEW.md` section 1, using
  only the standard library plus `pydantic` and `pytest` (declare them in a
  `requirements.txt` or `pyproject.toml`).
- Rust crate `rust/ops-core/` with `verify-evidence` and `validate-csv`
  subcommands emitting JSON to stdout (Phase 2 scope; optional in first pass).
- Test fixtures under `tests/fixtures/` for each ingestion source and for the
  integrity test.

## 3. Non-negotiables

- Client isolation by store, per `docs/SECURITY-BOUNDARIES.md` section 1 and
  acceptance criteria A1–A3. Include the isolation test.
- Evidence immutability and SHA-256 content addressing.
- Change lifecycle gate: no `verified` status without pre/post evidence and a
  measurement window.
- Loopback-only server; no outbound network calls; no external service
  mutation.
- No secrets in the repo; `data/` is gitignored runtime data.
- Pure-Python fallback for every Rust duty.

## 4. Definition of done

- Every numbered criterion in `docs/ACCEPTANCE.md` verified by a command whose
  output you capture.
- `python3 -m pytest` passes (and `cargo test` if the crate is built).
- Record verification output in `docs/evidence/BUILD-VERIFICATION.md` (command
  + result summary per criterion).

## 5. Git protocol

- Commit code and docs separately: `feat: ...`, `test: ...`, `docs: ...`.
- Never commit `data/`, `.env`, or client-identifiable artifacts.

## 6. If something is underspecified

- Make the smallest reasonable decision consistent with the docs, and record
  it as a new ADR under `docs/decisions/` rather than silently diverging.
