# Export Sanitization Checklist

Run before ANY export is imported into seo-ops. This is the one step where a
mistake leaks client data or credentials into the dashboard.

## Mechanical verification (run every time)

```bash
# After saving the export, grep for credential and PII patterns.
grep -rinE "api[_-]?key|token|secret|password|authorization|credential|client[_-]?secret|access[_-]?key|sk-[A-Za-z0-9]|nvapi-|bearer" EXPORT_FILE
grep -rinE "@[a-z0-9._-]+\.[a-z]{2,}" EXPORT_FILE   # email addresses
```

Any hit must be removed before import. Do not proceed until both greps are
clean.

## Field-level strip list

- API keys, tokens, secrets, passwords, authorization headers
- `access_key`, `client_secret`, `refresh_token`, `id_token`
- Email addresses, phone numbers, full names of end customers
- Payment or shipping data
- Any raw cookie or session material

## Import gate

- The seo-ops adapter already rejects credential-looking fields as a
  double-check. Treat that as the last line of defense, not the only one.
- After import, verify the evidence item's SHA-256 matches the sanitized file
  you intended to import.
- Never keep the raw (unsanitized) export in the repo or dashboard data
  directory.
