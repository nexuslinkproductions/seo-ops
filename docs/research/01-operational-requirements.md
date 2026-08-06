# Operational Requirements

Status: planning baseline (2026-08-06)

## 1. Product purpose

A single-operator, multi-client operations product for an SEO/AEO/GEO
consultancy. It supports **sales-backed prioritization**, **search and traffic
metrics**, **before/after evidence**, **audit documentation**, **approved
change logs**, and **client-ready scorecards** — with strict client isolation.

## 2. Definitions

- **SEO (Search Engine Optimization):** visibility in classic search engines
  (Google, Bing). Signals: rankings, impressions, clicks, CTR, crawl/index
  health.
- **AEO (Answer Engine Optimization):** presence in featured snippets, People
  Also Ask, knowledge panels, and voice-assistant answers. Signals: snippet
  ownership, structured-data coverage, answer accuracy.
- **GEO (Generative Engine Optimization):** citation/mention inside
  LLM-generated answers (ChatGPT, Perplexity, Gemini, Copilot). Signals:
  citation frequency, citation position, source attribution, sentiment of
  mention, answer share across a fixed prompt set.

## 3. Goals

1. Provide one dashboard foundation where each client has an isolated view of:
   - search performance (SEO), answer presence (AEO), generative citations
     (GEO), and traffic/analytics.
2. Support before/after evidence capture so every delivered change can be
   shown with dated proof.
3. Maintain an approved change log per client: what changed, who approved,
   when, linked evidence.
4. Generate client-ready scorecards (periodic summaries) from stored data.
5. Enable sales-backed prioritization: a backlog of opportunities with
   estimated impact, effort, and status, per client.

## 4. Non-goals (MVP)

- No multi-user authentication, roles, or permissions (single operator).
- No cross-client aggregation or benchmarking views.
- No automated site mutation (no pushing changes to CMS/WordPress; the product
  documents and measures, humans change sites).
- No real-time crawling at scale; ingestion is periodic and file/API based.
- No billing, invoicing, or CRM features.
- No public/client-facing hosted portal in MVP; scorecards are exported
  artifacts (HTML/PDF/Markdown).

## 5. Users and workflows

Primary user: the consultant/operator.

Core workflows:

1. **Onboard client:** create client, register domains/properties, define a
   GEO prompt set (fixed list of buyer-relevant questions).
2. **Ingest data:** import Search Console exports, analytics exports, crawl
   results, and GEO probe results on a schedule.
3. **Audit:** record an audit finding (technical, content, structured data,
   entity/GEO) with severity and recommendation.
4. **Change management:** log a proposed change; mark approved; attach
   pre-change evidence; after deployment attach post-change evidence.
5. **Measure:** view trends per metric family; compare before/after windows.
6. **Scorecard:** generate a periodic scorecard artifact per client.
7. **Prioritize:** maintain a per-client opportunity backlog scored by
   impact/effort for sales conversations.

## 6. Client data isolation model

- Each client has a **dedicated logical store** (per-client SQLite database
  file under `data/clients/<client-id>/client.db`).
- The application opens exactly one client store per request context; there is
  no shared table containing multiple clients' rows. Client A's data cannot
  appear in Client B's queries because there is no query path that spans
  stores.
- Exports and scorecards are written under `data/clients/<client-id>/exports/`.
- Tests must include an isolation test proving that records inserted for one
  client are unreachable from another client's context.

## 7. Operational constraints

- Runs locally on the operator's machine; no network exposure required for MVP.
- Python 3.14 and Rust 1.96 toolchains are available; no new installs needed.
- Network access may be restricted in some environments; the design must not
  require network for core functionality (ingestion accepts manual file
  exports as first-class input).
