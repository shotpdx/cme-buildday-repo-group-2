# CME Build Day

Participant-facing contract for the CME Build Day creative-generation workstream. The goal on Build Day is for every team to ship a working, personalized creative experience on top of the `cme_outcomes_uswest.media_demo` Customer 360.

This repo is intentionally **docs only** — the shared data contract and the two tracks. No reference code, apps, or pipelines live here; teams bring their own implementations (LakeFoundry or hand-built).

## What we're building

Two parallel tracks, both grounded in the same Customer 360:

**Sell-side — D2C home-screen hero.** A signed-in customer hits the streaming home page and the hero (image, tagline, CTA, subtitle) is personalized from their `(primary_segment, value_segment, top_genre_1)`. P95 under 500 ms, never 5xx, HyperFrames animation, graceful persona fallback on any upstream hiccup.

**Buy-side — Campaign Studio.** A marketing manager picks a target segment and, in under 30 seconds, sees a cross-format creative package (social square, vertical story, display banner, email header) stream in tile by tile via SSE. Per-tile regenerate + quality toggle, campaign-level approve, ZIP export, state persisted in Lakebase.

## The data contract

Everything participants can rely on — gold tables, silver support tables, enum vocabularies, grain, and the `_sync` Lakebase mirrors — is in [`build-day-data-dictionary.md`](build-day-data-dictionary.md). If it isn't documented there, treat it as undefined.

Key joins: all gold tables share `canonical_id`. The campaign funnel (`gold_media_campaign_engagement`) additionally keys on `campaign_id` and pitches a specific `content_id`.

## Environment

- **Catalog / schema:** `cme_outcomes_uswest.media_demo`
- **Lakebase mirrors:** same table names with `_sync` suffix
- **Volumes:** `/Volumes/cme_outcomes_uswest/media_demo/creatives/` for generated imagery

Anything not listed above (secret scopes, endpoint names, SP grants) is distributed per team on the morning of Build Day.
