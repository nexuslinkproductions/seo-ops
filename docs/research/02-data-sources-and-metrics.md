# Data Sources and Metrics

Status: planning baseline (2026-08-06)

## 1. Data sources (ingestion)

| Family | Source | MVP input mode | Notes |
|---|---|---|---|
| SEO | Google Search Console (performance export) | CSV export file or API (later) | clicks, impressions, CTR, position by query/page/date |
| SEO | Crawl data (Screaming Frog / Sitebulb export) | CSV export file | status codes, titles, meta, canonicals, indexability |
| Analytics | GA4 export (or Plausible/Matomo CSV) | CSV export file | sessions, conversions, landing pages, engagement |
| AEO | Manual/assisted snippet audit | structured JSON/CSV | featured snippet ownership per tracked query, PAA presence |
| GEO | LLM answer probes | structured JSON | fixed prompt set run against ChatGPT/Perplexity/Gemini; record cited sources and mentions |
| Evidence | Screenshots, HTML snapshots, documents | files | hashed, timestamped, linked to changes |
| Changes | Operator change log entries | app records | proposed/approved/deployed lifecycle |

Design notes:

- All ingestion is **file-first**: manual exports are first-class inputs, so
  the product works without network access or API credentials.
- API-based ingestion (Search Console API, GA4 Data API) is a later phase and
  must reuse the same normalized schema.
- GEO probes in MVP are operator-run (the operator queries each engine and
  records results) or imported from a probe tool's JSON export; automated
  probing is a later phase and must respect each provider's terms.

## 2. Normalized metric model

Common grain: `(client, date, source, dimension..., metric, value)`.

### SEO metrics
- Clicks, impressions, CTR, average position (by date, query, page, device, country).
- Indexed pages count, crawl errors count, pages with valid canonicals (%).
- Core Web Vitals pass rate (from crawl/lab export, optional in MVP).

### AEO metrics
- Tracked queries with owned featured snippet (count and %).
- PAA presence count per tracked query set.
- Structured data coverage: % of key templates with valid schema markup.

### GEO metrics
- Citation rate: % of prompt-set answers that cite any client property.
- Citation position: rank of client citation among cited sources (1st, 2nd...).
- Mention rate: % of answers mentioning the brand (cited or not).
- Share of answer: client citations / total citations across prompt set.
- Engine breakdown: metrics per engine (ChatGPT, Perplexity, Gemini, Copilot).

### Analytics metrics
- Organic sessions, organic conversions, conversion rate.
- Engagement: engaged sessions, average engagement time.
- Landing-page level organic performance.

### Derived scorecard metrics
- Period-over-period deltas for each metric family.
- Before/after comparisons tied to deployed changes (see evidence model).

## 3. Metric governance

- Every metric has a definition entry: name, source, grain, formula,
  freshness expectation.
- Scorecards cite metric definitions so clients see consistent terminology.
- Raw ingestion rows are preserved (append-only) so derived metrics can be
  recomputed if definitions change.
