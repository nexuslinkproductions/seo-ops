# Change Log Entry Template

Each approved change gets one entry, immutable in style (append-only).

## Entry schema

```yaml
change_id: <generated id>
title: <what changed>
category: technical | content | structured_data | visibility | analytics
client: <client id>
status: proposed | approved | deployed | verified | rolled_back

proposed_by: <operator>
proposed_at: <timestamp>
approved_by: <owner or client contact>
approved_at: <timestamp>
approval_note: <optional>

wordpress_revision_id: <revision id if WordPress change>
before_html_sha256: <hash of before state>
after_html_sha256: <hash of after state>
schema_validation_status: pending | passed | failed
evidence_before: <evidence ids>
evidence_after: <evidence ids>

measurement_window:
  pre_start: <date>
  pre_end: <date>
  post_start: <date>
  post_end: <date>

verification:
  definition_of_done: <category-specific checklist result>
  confounders: <algorithm updates, seasonality, downtime, promos>
  result_summary: <normalized delta per metric>

rollback:
  trigger: <regression threshold>
  restored_at: <timestamp if rolled back>
  incident_record: <link to INCIDENT-ROLLBACK.md entry>
```

## Rules

- Append-only. Never edit a prior entry.
- Attach before and after evidence (content-addressed) before marking
  verified.
- Record confounders on every entry; never attribute a delta without them.
- A rollback is a first-class status with its own incident record.
