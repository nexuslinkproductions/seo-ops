# AGENTS.md — seo-ops

These instructions govern any agent (human or AI) working in this repository.

## Identity and scope

- This repository is a **standalone** product workspace for a client-isolated
  SEO/AEO/GEO operations dashboard.
- It has **no dependency on, and no reuse of, any external repository,
  framework, governance file, skill set, or memory store**. In particular, do
  not read, invoke, cite, or reuse anything from YURI or adjacent systems.
- Work stays inside this repository. Do not create top-level folders outside
  the documented layout.

## Planning vs implementation

- The product plan is the set of documents under `docs/`. Treat them as the
  specification.
- Implementation is performed **only** per
  `docs/handoff/DEEPSEEK-BUILD-HANDOFF.md`, by the designated build task, after
  the plan is accepted. Do not begin production code from this planning
  baseline without that handoff being active.

## Hard rules

1. **Client isolation is non-negotiable.** No query, view, export, artifact,
   log line, or test fixture may mix data across clients. Any cross-client
   aggregate is out of scope for the MVP and requires an explicit, documented
   decision record first.
2. **No secrets in the repository.** Use environment variables or a local
   secrets store; commit nothing sensitive.
3. **No external service mutation from this repo** unless a task explicitly
   authorizes it. Read-only ingestion is the default posture.
4. **Evidence is immutable.** Once recorded, evidence items are not edited;
   corrections are appended as new evidence.
5. **Data stays local.** Client data lives under `data/` (gitignored) and is
   never uploaded, shared, or logged elsewhere.

## Documentation conventions

- Research notes: `docs/research/NN-topic.md`
- Architecture: `docs/architecture/`
- Decisions: `docs/decisions/ADR-NNN-title.md` (numbered, immutable once
  accepted; supersede with a new ADR rather than editing)
- Evidence produced by the product at runtime: `docs/evidence/` is reserved
  for the product's own schema/templates, not runtime output (runtime output
  lives under `data/`).

## Code conventions (when implementation begins)

- Python: type-annotated, `pydantic` for models, `pytest` for tests.
- Rust: single crate under `rust/ops-core`, `cargo test` for tests.
- C++ and C# are **excluded** per `docs/decisions/ADR-001-language-selection.md`.

## Git conventions

- Commit docs and code separately.
- Commit messages: `docs: ...`, `feat: ...`, `test: ...`, `chore: ...`.
- Never commit `data/`, `.env`, or any client-identifiable runtime artifact.
