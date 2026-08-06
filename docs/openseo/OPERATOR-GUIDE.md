# OpenSEO Import — Operator Guide

Status: implemented (2026-08-06)

## What this is

The seo-ops dashboard can consume **sanitized local result exports** produced
by OpenSEO or DataForSEO-compatible tooling. The adapter maps keywords, SERP
positions, search volume, CPC, competition, and difficulty into the existing
per-client normalized metrics, evidence, and backlog model.

This boundary is deliberately **credential-free**:

- The adapter never reads, copies, prints, or stores credentials.
- It never reads or modifies the OpenSEO installation.
- It never makes network calls; it only reads one local file you provide.
- Exports that still contain credential-looking fields (`api_key`, `token`,
  `secret`, `password`, and similar) are rejected before anything is written.

## What you need before importing

1. A client in seo-ops: `python3 -m ops.cli client-add --name "Acme" --id acme`.
2. A local export file from OpenSEO/DataForSEO in **JSON or CSV**:
   - JSON: keyword/SERP result objects (DataForSEO `tasks.result` envelopes,
     top-level lists, or flat objects are all accepted).
   - CSV: columns such as `keyword`, `search volume`, `cpc`, `competition`,
     `difficulty`, `position`, `url`, `domain`.
3. Make sure the export is **sanitized**: remove any API keys, tokens,
   passwords, or authorization headers before saving the file. The adapter
   double-checks and refuses files that still contain such fields.

## Importing (CLI)

```bash
python3 -m ops.cli openseo-import \
  --client acme \
  --file ~/exports/acme-keywords.json
```

Optional flags:

- `--no-evidence`: do not capture the sanitized export as an evidence item.
- `--backlog`: derive backlog opportunities for SERP rows outside the top 10.
- `--backlog-max N`: cap the number of derived backlog items (default 25).
- `--by NAME`: operator name recorded on the evidence item.
- `--source openseo|dataforseo`: label only; the file format is detected.

## What happens on import

- Raw rows are appended to the client's own store under the `openseo` source
  family. No other client can see them (per-client store boundary).
- The sanitized export is captured as content-addressed evidence (SHA-256
  named file under `data/clients/<id>/evidence/`) unless `--no-evidence`.
- The import is idempotent: importing the same content twice returns the
  existing batch and adds nothing.
- With `--backlog`, opportunities for keywords ranking outside the top 10 are
  scored by impact/effort and added to the client backlog.

## Metric mapping

| Export field | Normalized metric (seo family) |
|---|---|
| search volume | `keyword_search_volume` |
| cpc | `keyword_cpc` |
| competition | `keyword_competition` |
| difficulty / KD | `keyword_difficulty` |
| position / rank | `serp_position` |

Metric definitions are stored per client and appear in scorecards. Scorecards
are regenerated on demand, so new imports are reflected the next time you run
`python3 -m ops.cli scorecard --client acme --start ... --end ...`.

## Credential setup is a separate, future step

Importing from local files needs **no credentials at all**. If a future phase
adds direct API access to OpenSEO/DataForSEO, that step will:

1. Be requested and approved explicitly by the operator (it is not part of
   file imports).
2. Use variables named in `config/openseo.env.example` — that file is a
   template only and contains no values.
3. Keep values in the local shell environment or OS keychain, never in this
   repository.
4. Remain read-only against the provider, matching the product's network and
   mutation boundaries.

Until that step is implemented and approved, the only supported input is the
sanitized local file described above.

## Troubleshooting

- "export rejected: ... contains credential-looking field": strip the named
  field from the file and save a new export.
- "no normalized rows produced": the file has no recognizable keyword/SERP
  columns or keys; check the export format.
- "unsupported export format": save the file as `.json` or `.csv`.
