# 01 - Sell-Side Brief: D2C Home-Screen Hero

## The brief

Build a D2C (direct-to-consumer) home-screen hero that personalizes per signed-in customer using the Customer 360 data in `cme_outcomes_uswest.media_demo`. When a customer lands on the home page, the hero image, tagline, CTA, and subtitle all adapt to who they are. The hero animates with HyperFrames and falls back cleanly if anything goes wrong.

## Success criteria

- **Hero image varies** by the `(primary_segment, value_segment, top_genre_1)` key derived from `customer_360_gold_sync`.
- **Copy varies per customer** — tagline, CTA, and subtitle all shift with segment.
- **P95 latency < 500 ms** on the hero endpoint (Lakebase-synced reads, UC Volume image cache).
- **Never returns 5xx** — any upstream failure (Azure OpenAI, cache miss, DB hiccup) falls back to the matching persona default image + copy.
- **HyperFrames animation** on the hero (intro reveal + subtle motion loop).

## Starting points

You can either:

1. **Fork the reference app** at `apps/d2c_home/` (FastAPI + Jinja + GSAP, hero images read from `/Volumes/cme_outcomes_uswest/media_demo/creatives/`). Iterate on copy, animation, fallback behavior.
2. **Rebuild from scratch using LakeFoundry**, invoking the `d2c-home-screen-pattern` skill. LakeFoundry will scaffold the app, wire the Lakebase query, cache images in the UC Volume, and add the HyperFrames hero. See `03-lakefoundry-quickstart.md`.

## Demo canonical IDs

Use these five representative IDs for end-to-end demos. They cover all personas and match the reference app's `DEMO_CANONICAL_IDS`:

- `demo-sports-01` — Sports Fan
- `demo-news-01` — News Junkie
- `demo-binge-01` — Entertainment Binge Watcher
- `demo-casual-01` — Casual Viewer
- `demo-cord-01` — Cord Cutter

## Data you will touch

- `customer_360_gold_sync` — customer profile (Lakebase, fast reads by `canonical_id`).
- `segment_hero_keys` — 141 rows keyed on `(primary_segment, value_segment, top_genre_1)`.
- `segment_hero_briefs` — 139 prewritten creative briefs matched to those keys.
- `/Volumes/cme_outcomes_uswest/media_demo/creatives/` — pre-generated and on-demand hero images.

See `04-data-dictionary.md` for full schemas.
