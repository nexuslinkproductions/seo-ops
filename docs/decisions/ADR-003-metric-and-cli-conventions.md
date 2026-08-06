# ADR-003: Metric Computation, Delta Conventions, and CLI Contracts

Status: accepted (2026-08-06)

## Context

The plan defines metric families and before/after deltas but leaves formulas,
window semantics, backlog scoring, and the Rust CLI manifest format
underspecified for the build task.

## Decision

- All metric values are computed on demand from raw rows; definitions live in
  `ops/metrics.py` and are seeded into each client store so scorecards can
  reference them.
- Deltas are computed over explicit windows: `abs_delta = post - pre` and
  `rel_delta = abs_delta / pre` (or `null` when `pre` is zero/absent).
- Crawl metrics are point-in-time snapshots: they are computed over all rows
  when no window is given and show `n/a` for windowed deltas.
- Backlog score = `impact * 100 / effort` with impact/effort on a 1-5 scale.
- The Rust CLI emits JSON on stdout and owns no business rules:
  - `verify-evidence --dir <dir> [--manifest <file>]` where the manifest is a
    plain-text file with lines `<sha256>  <relative-path>` (two spaces,
    sha256sum-style). Output reports `checked`, `clean`, `mismatches`,
    `missing`, `extra`.
  - `validate-csv <file> [--required col1,col2]` reports row/column counts
    and required-column presence.
- Python falls back to a pure-Python implementation when the binary is
  absent; the fallback produces the same report shape.

## Consequences

- Scorecard deltas are deterministic and reproducible from raw rows.
- No cross-client computation exists; every call resolves one client store.

