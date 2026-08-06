# SEO / AEO / GEO Optimization Workflow (v1)

Purpose: a repeatable, documented, approval-gated procedure for any client
site. A generic client site is the first case study; each run produces the
evidence and content needed for social proof.

## Operating principles

1. Never modify a site until there is a complete baseline and an approved
   plan.
2. Every change goes through the change log: proposal, approval, before
   evidence, deploy, after evidence, verify.
3. No credential values ever appear in chat, files, or memory.
4. Client data stays isolated per client (local dashboard is per-client
   stores; exports are sanitized before import).
5. Document decisions, results, and before/during/after comparisons as we go,
   not after the fact.
6. One approval gate at a time; nothing unattended or recurring without
   explicit approval.

## Toolchain

| Tool | Role |
|---|---|
| WordPress + Yoast + Elementor | Site content/technical implementation |
| OpenSEO (hosted) | Project dashboard: site audit, rankings, backlinks, Search Console integration, DataForSEO data |
| DataForSEO | Search data source behind OpenSEO |
| Google Search Console | Impressions/clicks/rankings ground truth (gate 1) |
| seo-ops local dashboard | Client-isolated metrics, evidence, change log, scorecards; consumes sanitized exports |
| TencentDB Agent Memory | Cross-project continuity (semantic recall + capture, cloud embeddings) |
| Codex router models | Delegated analysis/implementation lanes (DeepSeek, Kimi, Grok, Gemini, GPT-5.6 family) |
| agent-reach | Research router for live internet content: web/Exa search, Jina Reader, RSS, YouTube, Bilibili, V2EX, Twitter/X, Reddit, LinkedIn, XHS (per active backends) |

## Stages

### Stage 0 - Onboard
- Register client in seo-ops (`client-add`).
- Snapshot public site (homepage, sitemaps, robots, key templates).
- Confirm access: WordPress admin, OpenSEO project, DataForSEO, Search Console.
- Document environment facts in handoff state.
- Complete `CLIENT-INTAKE.md` and `ACCESS-INVENTORY.md`: goals, scope,
  budget, brand voice, personas, existing vendors, CMS access, and per-system
  owner (agency vs client) with recovery path and offboarding.
- Legal and privacy sign-off: DPA and consent before connecting Search
  Console or handling WooCommerce sales/customer data (GDPR/DSG).
- Staging and backup protocol: create a staging clone of the client site and
  run a full backup before any technical audit or integration work.
- Add GA4 and Google Business Profile to the access checklist.

### Stage 1 - Baseline (read-only, zero changes)
- Inventory: pages, products, sitemaps, robots.
- Homepage checks: title, H1, meta description, canonical, hreflang, OG,
  JSON-LD, images/alt, body copy.
- Record all findings as hypotheses until the audit confirms them.
- **Gate 1:** connect Search Console + run first OpenSEO audit (page cap +
  Lighthouse decision, credit confirmed first).

### Stage 2 - Measure
- Export Search Console / analytics / audit data.
- Sanitize exports locally per `SANITIZE-CHECKLIST.md` (mechanical grep for
  tokens, emails, API keys, auth headers before import).
- Import into seo-ops under the client; generate scorecard baseline.
- Pull sales data (WooCommerce best-sellers) for priority offerings.

### Stage 3 - Research
- Keyword and competitor research via OpenSEO/DataForSEO into backlog.
- Map keywords to buyer questions for AEO/GEO.
- Build the prioritized fix list (impact/effort scoring).
- Always use agent-reach for live research: run `agent-reach doctor --json`
  first, then use the active backends for the needed channels (web, video,
  social). Declare which platform/backend is in use before each sweep.
- For full-web sweeps, combine channels: Exa search + Jina Reader for pages,
  YouTube for video content, Twitter/X and Reddit for practitioner
  discussion, Bilibili/XHS for Chinese-language context, RSS for news.

### Stage 4 - Approve + implement (one change at a time)
- Each item: proposed change -> approval -> before evidence -> implement ->
  after evidence -> verify.
- Categories: technical, content, structured data, visibility/indexing.
- Keep changes small and reversible; verify each before moving on.
- Change-log contract per `CHANGE-LOG-TEMPLATE.md`: change, category,
  approver identity, approval timestamp, WordPress revision ID, before/after
  HTML hashes, schema validation status, evidence hashes, rollback pointer.
- Definition of done per category: e.g. a noindex change needs crawl evidence
  plus URL Inspection plus a wait window; a schema change needs Rich Results
  validation on all affected pages; hreflang needs reciprocity checks.
- Pre-deploy backup per change and a rollback protocol: regression threshold
  (max acceptable ranking/downtime drop), step-by-step reversion for
  database/content/code, and an incident record in `INCIDENT-ROLLBACK.md`.
- Record confounders with each change (algorithm updates, seasonality,
  downtime, promos) so deltas are not misattributed.

### Stage 5 - Measure + report
- Scheduled scorecard cadence (monthly recommended).
- Before/during/after comparison per metric family (SEO, AEO, GEO,
  analytics).

### Improvement quantification model

Every change is measured programmatically against a normalized before/after
delta, so results are calculated, not guessed:

1. **Before state:** capture the audit scorecard, GSC performance, Core Web
   Vitals, structured-data validity, and AEO/GEO probe baseline on a fixed
   date. Store as content-addressed evidence in seo-ops.
2. **One approved change at a time:** propose, approve, deploy, then
   re-capture with the same tools and the same measurement windows.
3. **Normalized delta per metric:** overall and per-category audit scores,
   issue counts by severity, indexed pages, impressions, clicks, CTR,
   position, CWV pass/fail, schema validity, citation rate, share of voice,
   and probe answer completeness (DE and EN separately).
4. **Attribute carefully:** deltas are exact; causation is inferred only from
   one-change-at-a-time plus 8-16 week trend windows. Never claim a single
   month proves a single change.
5. **Aggregate:** scorecard per period, change-log linkage to evidence, and
   a case-study summary that reports verified deltas only.

Model in one line: before_data (audit + probes + GSC) -> one approved change
-> after_data (same tools, same windows) -> normalized delta per metric ->
attributed in the change log -> aggregated into scorecard and case study.

### Stage 6 - Case study + social proof
- Turn verified results into posts for X, Threads, LinkedIn.
- Include baseline-to-result numbers, method, and screenshots/evidence.
- Reuse the same narrative structure for future clients.
- Gate all social content through `APPROVED-CLAIMS.md` before publishing:
  what may and may not be claimed, keeping within the honesty contract.

## Approvals and recurrence

- Define approver identity per client (owner vs client contact) and record
  the approval in the change log with timestamp.
- Standing monthly re-approval resolves the tension between "no recurring
  work without approval" and the mandated monthly scorecards/probes: the
  monthly cadence is approved once per client and re-confirmed at each
  report.
- Every gate has explicit acceptance criteria; instantiate from a reusable
  `GATE-TEMPLATE.md` (Gate 1 is the first instance).

## Required artifacts (this repo and per client)

- `CLIENT-INTAKE.md` - goals, scope, budget, brand voice, personas, access.
- `ACCESS-INVENTORY.md` - per-system owner, recovery path, offboarding.
- `GATE-TEMPLATE.md` - reusable approval package with acceptance criteria.
- `CHANGE-LOG-TEMPLATE.md` - immutable-style change entry schema.
- `SANITIZE-CHECKLIST.md` - mechanical export sanitization verification.
- `INCIDENT-ROLLBACK.md` - regression thresholds, restore steps, incident log.
- `APPROVED-CLAIMS.md` - allowed claims for reports and social content.
- `CLIENT-REPORT-TEMPLATE.md` - monthly non-technical client scorecard.
- `PROPOSAL-SOW.md` - deliverables, cadence, exclusions, pricing.
- `CASE-STUDY-TEMPLATE.md` - reusable case-study structure.

## Client boundary rule

Client-specific artifacts live under a client-prefixed path
(e.g. `clients/<client-id>/` or a per-client branch); the repo root keeps
only generic process, research, and template files. This repo stays the
generic service workspace; client specifics move to a client
subfolder as the service expands.

## Documentation artifacts (this repo)

- `HANDOFF-STATE.md` - live environment + gate status.
- `BASELINE-2026-08-06.md` - preserved before snapshot.
- `GATE-1-APPROVAL.md` - current approval package.
- `WORKFLOW.md` - this procedure (candidate skill source).
- `RESEARCH-DEEPSEEK-AI-SEO-AEO-GEO.md` - DeepSeek V4 Flash max-reasoning
  research brief on how practitioners run SEO/AEO/GEO with AI (read-only,
  `[VERIFY]` tags for time-sensitive facts).
- `RESEARCH-EXHAUSTIVE-SWEEP.md` - exhaustive v2 sweep (5,715 words, 65
  [PROVEN], 4 [VERIFY]): SEO/AEO/GEO 2026 state, deep competitive intel,
  validated unconventional plays, product graph framework, measurement,
  roadmap, social-proof strategy.
- `RESEARCH-VERIFICATION-2026-08-06.md` - live source verification status for
  the brief.
- Next: `CHANGE-LOG.md`, `DECISIONS.md`, `CASE-STUDY.md`, social content.

## Research-backed operating rules (from DeepSeek brief)

- AI answers overlap with classic ranking: indexability, clarity, entity
  identity, trustworthy content, and structured data feed both. Fix SEO
  basics first; AEO/GEO follow.
- AEO is mostly provable snippet mechanics plus repackaged SEO. Do not sell
  "guaranteed snippets" or "voice-search domination" as separate products.
- GEO evidence: quote-worthy content, statistics, citations, and fixed-prompt
  probes; never report probe data as official statistics.
- AI assists every stage, but humans own judgment, facts, E-E-A-T, and final
  output. Tool scores are heuristics, not Google signals.
- Measure with Search Console as ground truth, manual fixed-prompt AEO/GEO
  probes, and before/during/after evidence. SEO moves in 8-16 week cycles;
  never claim causation from a single month.
- First client-specific fixes follow the baseline: title/H1/meta + alt +
  noindex batch, product schema validation, then answer-shaped content around
  the top 3 sales-backed products.

## Next actions

1. User approves Gate 1 (Search Console + audit config).
2. Run audit in OpenSEO; import sanitized exports to seo-ops.
3. Pick the analytics lane model (DeepSeek V4 Flash max / Grok 4.5 / Kimi /
   other) before starting the analytical phase.
4. Turn this workflow into a reusable skill after the first client proves it.
