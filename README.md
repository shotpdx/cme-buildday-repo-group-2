# CME Build Day

Participant-facing contract and app workspace for the CME Build Day creative-generation workstream. The goal on Build Day is for every team to ship a working, personalized creative experience on top of the `cme_outcomes_uswest.media_demo` Customer 360.

This repo contains the shared data contract, track briefs, and a Databricks App implementation for the NBA workstream.

## What we're building

Three parallel tracks, all grounded in the same Customer 360:

**Sell-side — D2C home-screen hero.** A signed-in customer hits the streaming home page and the hero (image, tagline, CTA, subtitle) is personalized from their `(primary_segment, value_segment, top_genre_1)`. P95 under 500 ms, never 5xx, HyperFrames animation, graceful persona fallback on any upstream hiccup.

**Buy-side — Campaign Studio.** A marketing manager picks a target segment and, in under 30 seconds, sees a cross-format creative package (social square, vertical story, display banner, email header) stream in tile by tile via SSE. Per-tile regenerate + quality toggle, campaign-level approve, ZIP export, state persisted in Lakebase.

**Next Best Action (NBA) — Intelligent Decisioning.** The NBA engine is the intelligence and orchestration layer on top of the Customer 360. It consumes gold tables (churn predictions, LTV, content affinity, audience segments), applies rules-based decisioning logic, and outputs a prioritized action per customer routed to the right channel at the right time. Three NBA gold tables provide the foundation: an **Action Library** (~50 actions across 8 types — content, upsell, retention, re-engagement, win-back, loyalty, service, do-nothing), **Recommendations** (~10K scored and ranked action recommendations with explainability), and **Orchestration State** (~10K per-customer journey positions, frequency caps, channel fatigue, and delivery history). The engine operates as a maturity progression — rules-based triggers first, propensity models second, real-time signals third.

## The data contract

Everything participants can rely on — gold tables, silver support tables, enum vocabularies, grain, and the `_sync` Lakebase mirrors — is in [`build-day-data-dictionary.md`](build-day-data-dictionary.md). If it isn't documented there, treat it as undefined.

Key joins: all gold tables share `canonical_id`. The campaign funnel (`gold_media_campaign_engagement`) additionally keys on `campaign_id` and pitches a specific `content_id`. The NBA tables link to the action library via `recommended_action_id` → `action_id`, and to the asset library via `creative_template_id`.

## Environment

- **Catalog / schema:** `cme_outcomes_uswest.media_demo`
- **Lakebase mirrors:** same table names with `_sync` suffix
- **Volumes:** `/Volumes/cme_outcomes_uswest/media_demo/creatives/` for generated imagery

Anything not listed above (secret scopes, endpoint names, SP grants) is distributed per team on the morning of Build Day.

## Next Best Actions App

The app under `src/app` is now a FastAPI + React/Vite Databricks App. It presents a signal queue, invokes the Agent Bricks Supervisor for investigation, applies configurable guarded-autopilot policy, and records simulation-only activations for low-cost, low-risk actions.

Key resources:

- Supervisor endpoint: `mas-c4ed84f2-endpoint`
- Genie specialist: `01f14964737c1b408dcdb56061a52019`
- UC guardrail function: `cme_outcomes_uswest.media_demo.nba_policy_guardrail`
- SQL warehouse: `8d3ba577483125f2`

Local development:

```bash
USE_MOCK_BACKEND=true USE_MOCK_SUPERVISOR=true uvicorn app.app:app --app-dir src --reload --port 8000
cd src/app/ui && bun install && bun run dev
```

Production build:

```bash
cd src/app/ui && bun run build
pytest src/app/tests
databricks --profile cme-outcomes bundle validate
```
