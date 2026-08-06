# AGENTS.md - seo-ops

Instructions for any AI agent (Codex, Claude, Gemini, Kimi, DeepSeek, etc.)
operating this repository. Read this file first. Stay inside this repo.

Public repo: https://github.com/nexuslinkproductions/seo-ops

## 0. Quick start (every session)

1. Confirm cwd is this repo root.
2. Identify the current git branch (`main`, `methodology`, `operational-templates`,
   or a private client/working branch).
3. Activate the local venv and verify the CLI:

```bash
. .venv/bin/activate
python3 -m ops.cli --help
python3 -m pytest
```

4. Never invent credentials, never open outbound network from this app, never
   mutate a client site from this repo.
5. If the task is client work, require an explicit `--client <id>` and keep all
   artifacts under that client.

## 1. Identity and scope

seo-ops is a standalone, client-isolated SEO / AEO / GEO operations toolkit:

- Python package `ops/` (dashboard + CLI + stores)
- Rust crate `rust/ops-core/` (evidence integrity + CSV validation helpers)
- Loopback-only local dashboard
- Credential-free local-file imports
- Content-addressed evidence (SHA-256)

This repo has **no dependency on YURI or any external governance/memory system**.
Do not read, cite, invoke, or reuse adjacent repos for this work.

Out of scope unless a new ADR says otherwise:

- Cross-client aggregates / benchmarks
- Automated CMS/WordPress mutation from this repo
- Multi-user auth / hosted portal
- Billing / CRM
- Secret storage in git

## 2. Roles and decision boundaries

| Role | May do | Must not do |
|---|---|---|
| **Human operator / owner** | Approve gates, approve site changes, approve publishes, authorize commits/pushes, authorize any external mutation | Hand credentials into chat or into repo files |
| **Agent (any model)** | Read docs, run local CLI/tests, propose audits/backlog/changes, sanitize+import exports, capture evidence, generate scorecards, draft case studies behind the claims gate | Deploy to live sites, publish social posts, send email, push/merge/PR, store secrets, mix clients, edit existing evidence |
| **Independent reviewer** | Check claims against `APPROVED-CLAIMS.md`, verify evidence integrity, re-run tests | Approve its own authored claims |

### Stop and ask a human when

- Any live-site change would be made (WordPress, DNS, Search Console settings)
- Credentials / API keys / OAuth / cookies are requested or discovered
- An export fails sanitization and the fix is unclear
- A change needs approval (`change-approve`) or Gate 1 / monthly cadence approval
- Rollback threshold is hit or site/checkout is broken
- Publishing reports/social posts (must pass claims gate)
- Cross-client views or any ADR-changing decision is proposed
- Commit / push / PR / merge is requested without explicit owner authorization
- Networked API ingestion (Phase 3+) is requested; file import is the only supported path today

Default posture: **read, measure, document, propose**. Humans deploy.

## 3. Branch layout and git workflow

### Canonical branches

| Branch | Owns | Agent focus |
|---|---|---|
| `main` | Dashboard implementation (`ops/`, `rust/`, `tests/`, docs) | Code, CLI, tests, architecture |
| `methodology` | Process: `WORKFLOW.md` | Lifecycle stages 0-6, gates, research rules |
| `operational-templates` | Templates: probe baseline, change log, sanitize, rollback, approved claims | Operational checklists and schemas |

These three branches are public and generic. They must not contain client-
identifiable runtime data.

### Working branches

| Branch type | Purpose | Rules |
|---|---|---|
| `feat/*`, `fix/*`, `docs/*` | Implementation / docs work against `main` | Keep commits scoped; docs and code commits separate |
| Private `client/<id>` branch or private fork | Client intake, probe set, change log copies, case study drafts | Never merge client PII/secrets into public branches |
| Local-only data | Runtime stores under `data/` | Gitignored; never commit |

### Propagation

1. Implement tooling fixes on a working branch → PR/merge to `main`.
2. Process changes → update `WORKFLOW.md` on `methodology`, then sync README
   pointers if needed.
3. Template changes → update files on `operational-templates`.
4. Do **not** use `git add .`. Stage explicit paths only.
5. Commit only when the human explicitly authorizes it.
6. Never force-push. Never commit `data/`, `.env`, `*.db`, or client exports.

Commit prefixes: `docs:`, `feat:`, `test:`, `chore:`, `fix:`.

## 4. Hard safety rules

1. **Client isolation:** one store per client under `data/clients/<id>/`.
   No query, view, export, log line, fixture, or scorecard may span clients.
2. **No secrets in repo or chat.** Use env vars / OS keychain outside git.
   `config/openseo.env.example` names variables only.
3. **Loopback only.** Dashboard binds `127.0.0.1`. No outbound calls from MVP.
4. **No external mutation from this repo.** Humans change sites; this tool
   records propose → approve → deploy → verify.
5. **Evidence is immutable.** Never edit an evidence file or row; append a new
   evidence item for corrections.
6. **Sanitize before import.** Run `SANITIZE-CHECKLIST.md` greps; adapter
   rejection is a backup, not the only gate.
7. **Data stays local.** Runtime data under `data/` is never uploaded, shared,
   or logged elsewhere.
8. **Claims gate.** Reports and social drafts must pass `APPROVED-CLAIMS.md`
   via an independent reviewer.
9. **Rollback thresholds.** Immediate rollback on outage/checkout break;
   ranking/indexation/CWV/schema regressions follow `INCIDENT-ROLLBACK.md`.
10. **One approval gate at a time.** No unattended recurring work without
    standing monthly approval recorded for that client.

## 5. Repository map

```text
seo-ops/
  AGENTS.md                 # this manual
  README.md
  WORKFLOW.md               # on methodology branch
  APPROVED-CLAIMS.md        # on operational-templates
  CHANGE-LOG-TEMPLATE.md
  INCIDENT-ROLLBACK.md
  PROBE-BASELINE-TEMPLATE.md
  SANITIZE-CHECKLIST.md
  config/openseo.env.example
  docs/
    ACCEPTANCE.md
    SECURITY-BOUNDARIES.md
    ROADMAP.md
    architecture/OVERVIEW.md
    decisions/ADR-00N-*.md
    evidence/BUILD-VERIFICATION.md
    openseo/OPERATOR-GUIDE.md
    research/
    handoff/                # historical build handoff; MVP is already built
  ops/                      # Python application
  rust/ops-core/            # Rust integrity helpers
  tests/                    # pytest + fixtures
  data/                     # gitignored runtime (registry + per-client stores)
```

Runtime layout (never commit):

```text
data/
  registry.db
  clients/<client-id>/
    client.db
    evidence/          # SHA-256 named files
    exports/           # scorecards, etc.
```

Override root with `SEO_OPS_DATA_ROOT` or `--data-root` when needed.

## 6. CLI surface (source of truth)

Entry point:

```bash
python3 -m ops.cli <command> ...
```

| Command | Purpose | Required args |
|---|---|---|
| `client-add` | Register client + seed metric defs | `--name`, optional `--id --domain --prompt` |
| `client-list` | List registry clients | none |
| `ingest` | Import Search Console / crawl / analytics / geo / aeo | `--client --source --file` |
| `openseo-import` | Import sanitized OpenSEO/DataForSEO JSON/CSV | `--client --file` |
| `evidence-add` | Capture evidence file or inline note | `--client --kind` + `--file` or `--inline-text` |
| `evidence-verify` | Re-hash evidence tree; report mismatches | `--client` (`--rust` preferred) |
| `audit-add` | Record audit finding | `--client --category --severity --title` |
| `backlog-add` | Add impact/effort opportunity | `--client --title --impact --effort` |
| `change-new` | Propose change | `--client --title` |
| `change-approve` | Human approval recorded | `--client --change-id` (`--by`) |
| `change-deploy` | Mark deployed (after human deploy) | `--client --change-id` |
| `change-verify` | Require pre/post evidence + windows + metric | see below |
| `scorecard` | Generate HTML + Markdown scorecard | `--client --start --end` |
| `serve` | Loopback dashboard | optional `--port` (default local) |

`change-verify` required window/evidence args:

```bash
python3 -m ops.cli change-verify \
  --client <id> \
  --change-id <id> \
  --pre-evidence <id> \
  --post-evidence <id> \
  --pre-start YYYY-MM-DD --pre-end YYYY-MM-DD \
  --post-start YYYY-MM-DD --post-end YYYY-MM-DD \
  --family <seo|aeo|geo|analytics> \
  --metric <metric_id>
```

### Enumerations agents must respect

| Field | Allowed values |
|---|---|
| ingest `--source` | `search_console`, `crawl`, `analytics`, `geo`, `aeo` |
| evidence `--kind` | `screenshot`, `html_snapshot`, `serp_snapshot`, `llm_answer`, `export_file`, `note`, `measurement` |
| audit `--category` | `technical`, `content`, `structured_data`, `entity_geo`, `analytics` |
| audit `--severity` | `critical`, `high`, `medium`, `low` |
| metric `--family` | `seo`, `aeo`, `geo`, `analytics` |
| change statuses | `proposed` → `approved` → `deployed` → `verified` (also `rejected`, `reverted`) |

### Common metric ids

- SEO: `clicks`, `impressions`, `ctr`, `avg_position`, `indexed_pages`,
  `crawl_errors`, `canonical_valid_pct`, `keyword_search_volume`,
  `keyword_cpc`, `keyword_competition`, `keyword_difficulty`, `serp_position`
- AEO: `snippet_owned_pct`, `paa_presence`, `structured_data_coverage_pct`
- GEO: `citation_rate`, `mention_rate`, `share_of_answer`, `avg_citation_position`
- Analytics: `sessions`, `conversions`, `conversion_rate`, `engaged_sessions`

Deltas: `abs_delta = post - pre`; `rel_delta = abs_delta / pre` (null if pre is 0).
Crawl metrics are point-in-time; windowed deltas may be `n/a` (ADR-003).

## 7. Process lifecycle → commands and artifacts

Map every client engagement to `WORKFLOW.md` stages. Use templates from
`operational-templates`. Record durable results in the client store via CLI.

### Stage 0 - Onboard

```bash
python3 -m ops.cli client-add --name "Acme" --id acme --domain acme.example --prompt "..."
python3 -m ops.cli client-list
```

Artifacts (client branch / private path, not public `main`):

- `CLIENT-INTAKE.md`, `ACCESS-INVENTORY.md`
- Legal/privacy sign-off before Search Console / customer data
- Staging clone + full backup before technical work

**Human gate:** access confirmation, DPA/consent, staging/backup ready.

### Stage 1 - Baseline (read-only, zero site changes)

- Public snapshots: homepage, sitemap, robots, key templates
- Hypotheses only until audit confirms
- **Gate 1 (human):** Search Console connect + first OpenSEO audit config
  (page cap, Lighthouse decision, credits confirmed)

### Stage 2 - Measure (sanitize → import → baseline scorecard)

```bash
# Mechanical sanitize (required)
grep -rinE "api[_-]?key|token|secret|password|authorization|credential|client[_-]?secret|access[_-]?key|sk-[A-Za-z0-9]|nvapi-|bearer" EXPORT_FILE
grep -rinE "@[a-z0-9._-]+\.[a-z]{2,}" EXPORT_FILE

python3 -m ops.cli ingest --client acme --source search_console --file ./clean/gsc.csv
python3 -m ops.cli ingest --client acme --source crawl --file ./clean/crawl.csv
python3 -m ops.cli ingest --client acme --source analytics --file ./clean/analytics.csv
python3 -m ops.cli ingest --client acme --source geo --file ./clean/geo.json
python3 -m ops.cli ingest --client acme --source aeo --file ./clean/aeo.json

python3 -m ops.cli openseo-import --client acme --file ./clean/keywords.json --backlog --by operator

python3 -m ops.cli evidence-verify --client acme --rust
python3 -m ops.cli scorecard --client acme --start 2026-07-01 --end 2026-07-31
```

Rules:

- Never import until both greps are clean.
- Never keep unsanitized exports under `data/` or in git.
- Re-import of identical content is idempotent (ADR-002 / ADR-004).

### Stage 3 - Research → audit + backlog

```bash
python3 -m ops.cli audit-add \
  --client acme --category technical --severity high \
  --title "Missing product schema on PDP" \
  --recommendation "Add Product JSON-LD and validate"

python3 -m ops.cli backlog-add \
  --client acme --title "Answer page for top product Q" \
  --impact 5 --effort 2 --category content
```

Backlog score = `impact * 100 / effort` (impact/effort 1-5).

Research may use external tools **outside** this app, but do not paste secrets
into the repo. Prefer sanitized notes and evidence captures.

### Stage 4 - One change at a time

Lifecycle enforced by `ops/changeflow.py`:

`proposed → approved → deployed → verified`
(or `rejected` / `reverted`)

```bash
# 1) Propose
python3 -m ops.cli change-new --client acme --title "Add Product schema on /product/x" --proposed-by agent

# 2) Capture BEFORE evidence (while still pre-deploy)
python3 -m ops.cli evidence-add --client acme --kind html_snapshot --file ./before.html --by agent

# 3) HUMAN approves + deploys on the real site (backup first)
python3 -m ops.cli change-approve --client acme --change-id <id> --by owner
# ... human deploys ...
python3 -m ops.cli change-deploy --client acme --change-id <id>

# 4) Capture AFTER evidence
python3 -m ops.cli evidence-add --client acme --kind html_snapshot --file ./after.html --by agent

# 5) Verify with non-overlapping windows
python3 -m ops.cli change-verify \
  --client acme --change-id <id> \
  --pre-evidence <pre_id> --post-evidence <post_id> \
  --pre-start 2026-06-01 --pre-end 2026-06-28 \
  --post-start 2026-07-01 --post-end 2026-07-28 \
  --family seo --metric clicks
```

Also append a human-readable entry using `CHANGE-LOG-TEMPLATE.md` on the
client branch (revision id, HTML hashes, schema status, confounders, rollback
pointer). CLI status and template entry must agree.

**Rollback:** follow `INCIDENT-ROLLBACK.md`, restore backup, re-verify, append
incident record, mark change reverted in process notes.

### Stage 5 - Measure + report

```bash
python3 -m ops.cli scorecard --client acme --start 2026-08-01 --end 2026-08-31 --highlight "schema rollout"
python3 -m ops.cli serve --port 8765
# open http://127.0.0.1:8765/clients/acme/overview
```

Dashboard views (all require client context): overview, trends, evidence,
audits, changes, scorecards, backlog.

Cadence: monthly scorecards/probes only with standing monthly approval.

### Stage 6 - Case study / social proof

- Use verified deltas only; attribute carefully; note confounders.
- Run every draft through `APPROVED-CLAIMS.md` with an independent reviewer.
- Never claim guarantees, single-month causation, or probe data as official
  statistics.

### Improvement quantification model (mandatory)

1. Before state captured as evidence (scorecard, GSC, CWV, schema, probes)
2. Exactly one approved change
3. After state with the same tools and windows
4. Normalized deltas per metric
5. Attribution only with one-change-at-a-time + 8-16 week trends
6. Aggregate into scorecard + case study

## 8. Definition of done by change category

| Category | Done means |
|---|---|
| **technical** (crawl/index/noindex/canonical) | Pre/post crawl evidence + URL Inspection notes + wait window recorded; `change-verify` succeeded; confounders noted |
| **content** | Pre/post HTML or screenshot evidence; target query/metric window set; no unverified ranking claims |
| **structured_data** | Rich Results / schema validation passed on all affected URLs; `schema_validation_status=passed` in change log |
| **visibility / hreflang** | Reciprocity checks recorded; crawl/index evidence attached |
| **AEO** | Snippet/PAA/structured-data metrics updated; evidence kind `serp_snapshot` or measurement export attached |
| **GEO** | Probe run uses fixed prompt set; dated DE+EN results imported; honesty labels applied; no single-run delta claims |
| **analytics** | Sanitized analytics import; metric family `analytics`; windows non-overlapping |
| **scorecard task** | HTML + Markdown written under client exports; integrity clean |
| **code change in this repo** | Targeted tests pass; isolation/hygiene still green; no secrets/`data/` staged |
| **publish task** | Independent claims-gate PASS; human authorization to post |

Verification cannot mark `verified` without: at least one pre evidence id, one
post evidence id, fully defined non-overlapping windows, and computable metric
data in both windows.

## 9. Verification checklist (run before claiming done)

```bash
# Tooling health
. .venv/bin/activate
python3 -m pytest
(cd rust/ops-core && cargo test)

# Client integrity
python3 -m ops.cli evidence-verify --client <id> --rust

# Isolation / acceptance regressions (always relevant)
python3 -m pytest tests/test_isolation.py tests/test_hygiene.py tests/test_evidence.py tests/test_changeflow.py

# Optional live dashboard smoke
python3 -m ops.cli serve --port 8765
# confirm bind is 127.0.0.1 and /overview (no client) is not a global data view
```

Acceptance themes live in `docs/ACCEPTANCE.md` and the verified command matrix
in `docs/evidence/BUILD-VERIFICATION.md`. Prefer re-running commands over
trusting old narrative status.

## 10. Quality bar for agent tasks

A task is done only when all of the following are true:

1. **Correct branch / path:** code on `main` line, process edits on
   `methodology`, template edits on `operational-templates`, client artifacts
   on private client branch/path.
2. **Single-client context** whenever data is touched.
3. **Safety gates held:** sanitize, no secrets, no external mutation, no
   evidence edits.
4. **Commands actually run** (or explicitly blocked with reason); paste key
   outputs in the handoff.
5. **Tests relevant to the change are green.**
6. **Artifacts linked:** evidence ids, change ids, scorecard paths, template
   entries.
7. **Human gates called out** instead of silently skipped.
8. **No speculative claims** beyond measured deltas and approved language.

## 11. Coding conventions (when changing this repo)

- Python ≥3.11, type-annotated, pydantic models in `ops/models.py`
- Tests with pytest under `tests/`; fixtures under `tests/fixtures/`
- Rust only in `rust/ops-core` for integrity/CSV helpers; no business rules
- C++ / C# excluded (ADR-001)
- Docs: research `docs/research/NN-topic.md`; ADRs append-only numbered files
- `docs/evidence/` holds product schemas/verification docs, not runtime output
- Historical note: `docs/handoff/DEEPSEEK-BUILD-HANDOFF.md` was the build
  packet; MVP is implemented. Do not treat the repo as "planning only."

## 12. OpenSEO / DataForSEO boundary (ADR-004)

Supported today: **sanitized local JSON/CSV only**.

Not supported without a new explicit approval + implementation:

- Reading OpenSEO install files
- Using env credentials inside the adapter
- Network calls to providers

If an export contains credential-looking fields, strip them and save a new
file. Do not ask the model to "just ignore" those fields in-place inside
`data/`.

## 13. Incident / STOP protocol

On "STOP immediately" or production incident:

1. Stop all edits, deploys, posts, commits, pushes, PRs.
2. Report exactly what changed and what did not.
3. If a site change was already deployed, follow `INCIDENT-ROLLBACK.md`.
4. Preserve evidence; append incident records; do not rewrite history.

## 14. Handoff format (agent → human or next agent)

Use this structure at task end:

```text
BRANCH: <name>
CLIENT: <id or n/a>
GOAL: <one sentence>
DONE:
- ...
COMMANDS RUN:
- ...
ARTIFACTS:
- evidence:... change:... scorecard:... files:...
GATES WAITING ON HUMAN:
- ...
RISKS / NON-GOALS TOUCHED:
- ...
NEXT:
- ...
```

## 15. Reference index

| Need | Open |
|---|---|
| Process stages | `WORKFLOW.md` (methodology) |
| Security boundaries | `docs/SECURITY-BOUNDARIES.md` |
| Acceptance criteria | `docs/ACCEPTANCE.md` |
| Verified command matrix | `docs/evidence/BUILD-VERIFICATION.md` |
| Architecture | `docs/architecture/OVERVIEW.md` |
| Metric/CLI contracts | `docs/decisions/ADR-003-metric-and-cli-conventions.md` |
| Import idempotency | `docs/decisions/ADR-002-import-idempotency.md` |
| OpenSEO boundary | `docs/decisions/ADR-004-openseo-import-boundary.md` + `docs/openseo/OPERATOR-GUIDE.md` |
| Sanitize gate | `SANITIZE-CHECKLIST.md` |
| Change log schema | `CHANGE-LOG-TEMPLATE.md` |
| Rollback | `INCIDENT-ROLLBACK.md` |
| Claims gate | `APPROVED-CLAIMS.md` |
| Probe baseline | `PROBE-BASELINE-TEMPLATE.md` |
| Roadmap / non-goals | `docs/ROADMAP.md` |
