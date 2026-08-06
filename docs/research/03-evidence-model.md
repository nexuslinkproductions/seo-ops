# Evidence, Before/After, Audit, and Change Log Model

Status: planning baseline (2026-08-06)

## 1. Principles

- **Evidence is immutable.** Items are hashed (SHA-256) at capture, stored
  under the client's store area, and never edited. Corrections are new items.
- **Every claim links to evidence.** Audit findings, deployed changes, and
  scorecard deltas reference evidence IDs.
- **Before/after pairs are first-class.** A change is not "evidenced" until it
  has at least one pre-change and one post-change evidence item, plus a
  measured window comparison.

## 2. Entities

### EvidenceItem
- `id`, `client_id`, `captured_at`, `captured_by`
- `kind`: screenshot | html_snapshot | serp_snapshot | llm_answer | export_file | note | measurement
- `path` (file under `data/clients/<id>/evidence/`) or `inline_text`
- `sha256`, `size_bytes`, `source_description`
- optional `related_query`, `related_url`, `related_prompt_id`

### AuditFinding
- `id`, `client_id`, `created_at`, `category` (technical | content | structured_data | entity_geo | analytics)
- `severity` (critical | high | medium | low), `title`, `description`, `recommendation`
- `evidence_ids[]`, `status` (open | accepted | dismissed | resolved)

### ChangeEntry (approved change log)
- `id`, `client_id`, `created_at`
- `title`, `description`, `scope_urls[]`
- `status`: proposed -> approved -> deployed -> verified (or rejected/reverted)
- `proposed_by`, `approved_by`, `approved_at`, `deployed_at`, `verified_at`
- `pre_evidence_ids[]`, `post_evidence_ids[]`
- `measurement_window`: pre_start, pre_end, post_start, post_end
- `result_summary` (filled at verification)

### Scorecard
- `id`, `client_id`, `period_start`, `period_end`, `generated_at`
- `metrics_snapshot` (JSON of computed metrics + deltas)
- `highlights[]` (text), `changes_in_period[]` (ChangeEntry refs)
- `export_path` (rendered artifact)

## 3. Before/after comparison rule

For a verified change:
1. Compute the relevant metric(s) over the pre window and the post window.
2. Record both values, the absolute and relative delta, and the evidence IDs
  on the ChangeEntry (`result_summary`).
3. Scorecards render verified changes with their deltas; unverified changes
  appear as "pending measurement".

## 4. Storage layout (per client)

```
data/clients/<client-id>/
  client.db            # SQLite store (metrics, entities)
  evidence/            # hashed evidence files, named <sha256>.<ext>
  exports/             # generated scorecards and reports
```

## 5. Integrity checks

- On read, evidence files can be re-hashed and compared to `sha256`.
- A periodic integrity command lists any evidence item whose file is missing
  or whose hash mismatches. (Candidate for the Rust component; see
  `docs/architecture/OVERVIEW.md`.)
