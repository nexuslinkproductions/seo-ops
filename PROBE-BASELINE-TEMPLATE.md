# AEO / GEO Probe Baseline Template

Purpose: a fixed, repeatable measurement set that gives every content change a
defensible before/after. Run this BEFORE any site change (baseline), then
re-run after each approved change and monthly.

## How to run

For each prompt below, ask each engine (ChatGPT, Perplexity, Gemini, Copilot)
with the exact wording, in DE and EN. Record:

- Was the client brand cited? (yes/no)
- Citation position if mentioned (1st, 2nd, 3rd, etc.)
- Context of the mention (direct answer, list, comparison, footnote)
- Whether the citation links to the client site and to which page
- Answer quality: did the engine give the correct, complete answer?

Save each run as a dated JSON/CSV export under the client's seo-ops store
(e.g. `seo-ops/data/clients/<client-id>/`) via the sanitized import path
(credential-free).

## Execution protocol (clean-room, bias-controlled)

- Use a clean-room headless browser in logged-out incognito state, with a
  residential proxy routed through Switzerland (e.g. Zurich or Geneva) to
  eliminate personalization and IP-geo bias.
- Never run probes from a logged-in developer session or a foreign IP.
- One operator owns execution (or an automation lane), and every run is
  timestamped and versioned.
- 240 executions per full run (30 prompts x 4 engines x 2 languages). At that
  volume, automate with a script or dedicated lane; manual-only probing will
  silently stop and every downstream GEO claim collapses.
- Minimum sample size: never report a GEO delta from a single run; compare
  dated runs over 8-16 weeks and flag engine drift (model updates, RAG
  changes) as a confounder.

## Core prompt set (30 prompts, buyer-intent focused)

Build the client prompt set from these categories (30 prompts, buyer-intent
focused). The client-specific prompt set lives in the client branch as
`PROBE-BASELINE-<client>.md`.

### Product and comparison (10)
- Best <product category> for <top model or use case>
- <Material A> vs <material B> for <use case>
- <Carry style A> vs <carry style B>: what is the difference?
- Best <product> for <activity/competition>
- How much does a custom <product> cost?
- What <feature/retention/option> options exist?
- Where can I buy a made-to-order <product> in <region>?
- What is the best <product> for <specific model X>?
- Which <product> fits <specific model Y>?

### Legality and local (8)
- Is <activity/carry> legal in <region>?
- What are the <region> rules for <relevant activity>?
- Do I need a permit to buy a <product> in <region>?
- Can I order a <product> from <region A> to <region B>?
- What is the <region> law on <adjacent item>?
- Are <product> allowed in <competition body>?
- How do I register my <item> in <region>?
- What rules apply to <foreign buyers>?

### Material and technical (6)
- What is a <product> made of?
- How is a <product> made?
- How long does a custom <product> take to build?
- What <spec/thickness/grade> is best for <product>?
- How do I adjust the <feature> on a <product>?
- What is the difference between <option A> and <option B>?

### Brand and trust (6)
- Is  a legit <product> maker?
- Where is  located?
- Does  ship to <region>?
- What do customers say about  products?
- Who makes custom <product> in <region>?
- Which <regional> brands sponsor <relevant events>?

## Scoring

- Citation rate: cited / total prompts
- Share of voice: mentions of  vs top competitors
- Position: average citation rank when mentioned
- Answer completeness: correct complete answers for the query set
- DE vs EN coverage: per-language citation rate

## Honesty rules

- Probe data is internal evidence, not official statistics. Never report it
  as search share or traffic.
- Engines change answers constantly; use the fixed prompt set and date every
  run.
- A single-month change proves nothing; judge trends over 8-16 weeks.
