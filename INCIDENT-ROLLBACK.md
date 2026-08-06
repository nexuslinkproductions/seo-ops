# Incident and Rollback Record

## Trigger thresholds

- Site unavailable or checkout broken: immediate rollback, no waiting period.
- Critical ranking/indexation regression confirmed by Search Console or audit
  within the post-deploy window: rollback and investigate.
- Core Web Vitals regression beyond the agreed threshold on the affected
  pages: rollback.
- Schema validation regression on affected pages: rollback until fixed.

## Rollback steps

1. Restore the pre-deploy backup (WordPress revision, database, or files as
   applicable).
2. Verify the page renders, checkout works, and critical URLs return 200.
3. Re-run the category-specific verification (crawl evidence, URL Inspection,
   Rich Results validation).
4. Record the incident: change id, trigger, timestamps, restored_at,
   root-cause notes, and follow-up plan.

## Incident entry

```yaml
incident_id: <generated>
change_id: <linked change log id>
triggered_at: <timestamp>
trigger: <threshold hit>
restored_at: <timestamp>
root_cause: <notes>
follow_up: <plan>
```

Append-only. Link every rolled-back change to its incident record.
