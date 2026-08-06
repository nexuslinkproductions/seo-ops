# ADR-001: Language Selection (Python + Rust; C++ and C# excluded)

Status: accepted (2026-08-06)

## Context

The product needs a data-centric application core plus one
performance/safety-relevant component (bulk evidence hashing, bulk CSV
validation). The mandate asked to evaluate whether C++ or C# have a real role
rather than adding them gratuitously. Environment: Python 3.14 and Rust 1.96
already available; single operator; local-first.

## Decision

- **Python** is the application core (models, storage, ingestion, metrics,
  scorecards, local dashboard, CLI).
- **Rust** is a single scoped crate (`rust/ops-core`) for bulk evidence
  integrity verification and bulk CSV validation, invoked as a JSON-emitting
  CLI subprocess.
- **C++ is excluded.**
- **C# is excluded.**

## Rationale

- Python maximizes development speed and correctness for structured-data
  workflows and has first-class SQLite support.
- Rust covers the performance class needed (parallel hashing, large-file
  validation) with memory safety and a single modern toolchain.
- C++ offers no capability Rust lacks here, while adding build complexity.
- C# targets ecosystems (Windows/.NET) irrelevant to this product and would
  add a third runtime for no gain.

## Consequences

- Two languages only; Rust stays small and stateless.
- Python retains a pure-Python fallback for every Rust duty, so the product
  functions without the Rust toolchain.
- Revisiting this decision requires a new ADR with measured evidence (e.g.,
  profiling data) showing an unmet need.
