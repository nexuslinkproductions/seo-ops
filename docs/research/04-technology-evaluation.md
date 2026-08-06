# Technology Evaluation

Status: planning baseline (2026-08-06)

## 1. Requirements driving the choice

- Local-first desktop-style tool; no server farm.
- Heavy on structured data: ingestion normalization, metric computation,
  scorecard rendering.
- File integrity and hashing at moderate scale (thousands of evidence files).
- Small team; maintainability beats raw performance.

## 2. Python — primary language (adopt)

Role: application core.

- Data model and validation: `pydantic`.
- Storage: `sqlite3` (stdlib) via a thin repository layer; per-client DB files.
- Ingestion: CSV/JSON parsers, normalization into the metric model.
- Metrics: pure functions computing scorecard and before/after deltas.
- Serving/UI: stdlib `http.server`-based local app server rendering HTML
  templates for the dashboard (no external dependency required for MVP; a
  micro-framework may be introduced later by ADR if justified).
- CLI: `argparse`/`typer`-style commands for ingest, evidence check,
  scorecard generation.

Why: fastest correct development for data-centric CRUD + analytics; excellent
SQLite integration; the operator environment already has Python 3.14.

## 3. Rust — supporting component (adopt, scoped)

Role: `rust/ops-core` crate, invoked as a CLI subprocess by Python.

Justified duties (performance- or safety-relevant):
- Bulk evidence integrity: parallel SHA-256 hashing of large evidence trees
  with a manifest report.
- Bulk CSV row validation/normalization for very large exports (if Python
  profiling shows a bottleneck).

Boundary: Rust owns no business rules. It receives file paths and validation
specs, returns structured JSON to stdout. Python orchestrates.

Why Rust and not more Python: measurable throughput on multi-GB evidence
trees, memory safety for long-running batch jobs, and the operator already has
a Rust toolchain. Kept deliberately small to avoid two-language complexity
spread.

## 4. C++ — not justified (exclude)

- No use case here requires its niche (no native UI, no embedded constraints,
  no existing C++ codebase).
- Rust covers the same performance class with better safety and a single
  modern toolchain. Adding C++ would only add build complexity.

## 5. C# — not justified (exclude)

- Its strengths (Windows desktop, .NET enterprise ecosystem, Unity) do not
  match this product.
- Would introduce a third runtime, a second package ecosystem, and
  cross-platform friction for zero capability gain over Python + Rust.

## 6. Decision summary

Python (core) + Rust (scoped performance/integrity component). C++ and C#
excluded as gratuitous. Recorded formally in
`docs/decisions/ADR-001-language-selection.md`.
