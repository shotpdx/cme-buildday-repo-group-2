# 02 - Buy-Side Brief: Campaign Studio

## The brief

Build a campaign preview tool that lets a marketing manager describe a target segment and see a full cross-format creative package — social, story, display, email header — in under 30 seconds. Tiles stream in as they finish so the user never stares at a blank screen. Every generation is persisted so it can be regenerated, approved, and exported as a ZIP.

## Success criteria

- **One segment filter produces four cross-format tiles:** `social_square` (1024x1024), `vertical_story` (1024x1792), `display_banner` (1792x1024), `email_header` (1792x1024).
- **SSE fan-out** — tiles stream in as each one finishes, not after all four complete.
- **Per-tile regenerate** with a low / medium quality toggle.
- **Campaign-level approve + export-to-zip** (zips all four approved tiles + the brief).
- **State persists to Lakebase** in `media_demo.generated_campaigns` so refresh-safe and auditable.

## Starting points

You can either:

1. **Fork the reference app** at `apps/campaign_studio/` (FastAPI + SSE backend, React UI, Lakebase persistence via the `Store` class). Iterate on the brief synthesis prompt, quality toggle, UX polish, export format.
2. **Rebuild from scratch using LakeFoundry**, invoking the `campaign-studio-pattern` skill. LakeFoundry will scaffold the FastAPI + SSE backend, the React frontend, the Lakebase migration, and the four-format fan-out loop. See `03-lakefoundry-quickstart.md`.

## Demo segment filters

Any `persona` from `gold_media_customer_360` works as a segment filter. For quick demos, drive off the same five personas the sell-side app uses: Sports Fan, News Junkie, Entertainment Binge Watcher, Casual Viewer, Cord Cutter.

## Data you will touch

- `gold_media_customer_360` / `customer_360_gold_sync` — customer segmentation.
- `segment_hero_briefs` — reusable brief text per segment.
- `media_demo.generated_campaigns` — Lakebase table where campaigns + tile status + approval state live.
- `/Volumes/cme_outcomes_uswest/media_demo/creatives/` — per-tile generated images.

See `04-data-dictionary.md` for full schemas.
