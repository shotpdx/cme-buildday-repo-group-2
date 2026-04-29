# Media Customer 360 — Data Dictionary

**Catalog:** `cme_outcomes_uswest` | **Schema:** `media_demo`

All gold tables join on `canonical_id` (the unified customer identifier from Hightouch identity resolution). Lakebase-synced copies have a `_sync` suffix with identical schemas.

---

## Gold Layer (Business-Ready)

### gold_media_customer_360
Unified customer profile combining demographics, engagement, and commerce. **The central table — start here.**

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** Unified customer ID |
| 1 | `email` | string | Normalized email |
| 2 | `first_name` | string | First name |
| 3 | `last_name` | string | Last name |
| 4 | `phone` | string | Normalized phone (digits only) |
| 5 | `zip_code` | string | ZIP code |
| 6 | `persona` | string | Behavioral persona: Sports Fan, News Junkie, Entertainment Binge Watcher, Casual Viewer, Cord Cutter |
| 7 | `customer_since` | timestamp | Account creation date |
| 8 | `total_events` | bigint | Total engagement events across all platforms |
| 9 | `platforms_used` | bigint | Count of distinct platforms (web, mobile, ott, linear_tv) |
| 10 | `unique_content_viewed` | bigint | Distinct content items consumed |
| 11 | `web_events` | bigint | Web platform event count |
| 12 | `mobile_events` | bigint | Mobile platform event count |
| 13 | `ott_events` | bigint | OTT/streaming event count |
| 14 | `linear_tv_events` | bigint | Linear TV event count |
| 15 | `total_watch_seconds` | bigint | Total viewing time in seconds |
| 16 | `last_engagement_ts` | timestamp | Most recent engagement |
| 17 | `first_engagement_ts` | timestamp | Earliest engagement |
| 18 | `total_transactions` | bigint | Commerce transaction count |
| 19 | `total_spend` | double | Lifetime spend ($) |
| 20 | `avg_transaction_value` | double | Average transaction amount ($) |
| 21 | `last_transaction_ts` | timestamp | Most recent transaction |
| 22 | `cancellations` | bigint | Number of subscription cancellations |
| 23 | `current_subscription_tier` | string | Active tier: basic, standard, premium, family (or null) |
| 24 | `days_since_last_engagement` | int | Recency metric |
| 25 | `customer_tenure_days` | int | Days since account creation |
| 26 | `avg_events_per_day` | double | Engagement frequency |
| 27 | `is_multi_platform` | boolean | Uses 2+ platforms |
| 28 | `has_subscription` | boolean | Has active subscription |
| 29 | `created_ts` | timestamp | Record creation timestamp |

**Rows:** ~10,000 | **Grain:** One row per customer | **Mirror:** `gold_media_customer_360_sync` on Lakebase

---

### gold_media_churn_predictions
Churn risk scores with explainable component factors.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** FK to customer_360 |
| 1 | `email` | string | Customer email |
| 2 | `churn_risk_score` | double | Overall risk score (0.0–1.0) |
| 3 | `churn_risk_category` | string | High (>=0.7), Medium (>=0.4), Low |
| 4 | `is_churned` | boolean | True if 45+ days inactive or cancelled |
| 5 | `inactivity_risk` | double | Component: days since last engagement (0–1) |
| 6 | `engagement_risk` | double | Component: low engagement frequency (0–1) |
| 7 | `platform_risk` | double | Component: single platform usage (0–1) |
| 8 | `subscription_risk` | double | Component: no subscription or past cancellations (0–1) |
| 9 | `days_since_last_engagement` | int | Raw recency value |
| 10 | `last_engagement_ts` | timestamp | Most recent activity |
| 11 | `scored_ts` | timestamp | When the score was computed |

**Rows:** ~10,000 | **Grain:** One row per customer | **Mirror:** `gold_media_churn_predictions_sync` on Lakebase

---

### gold_media_content_affinity
Per-customer, per-genre affinity scores based on consumption patterns.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK (composite).** FK to customer_360 |
| 1 | `content_genre` | string | **PK (composite).** Genre: Sports, News, Entertainment, Drama, Comedy, Documentary, Reality, Kids |
| 2 | `affinity_score` | double | Weighted affinity (0.0–1.0), factors: event share, watch time share, recency |
| 3 | `genre_events` | bigint | Number of events for this genre |
| 4 | `genre_watch_seconds` | bigint | Watch time for this genre (seconds) |
| 5 | `last_genre_engagement` | timestamp | Most recent engagement with this genre |
| 6 | `scored_ts` | timestamp | When the score was computed |

**Rows:** ~66,000 | **Grain:** One row per customer per genre | **Mirror:** `gold_media_content_affinity_sync` on Lakebase

---

### gold_media_top_genres_per_user
Pre-computed top 3 genre preferences per customer (pivoted from content_affinity).

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** FK to customer_360 |
| 1 | `top_genre_1` | string | Highest affinity genre |
| 2 | `top_genre_1_score` | double | Affinity score for top genre |
| 3 | `top_genre_2` | string | Second highest genre |
| 4 | `top_genre_2_score` | double | Score for second genre |
| 5 | `top_genre_3` | string | Third highest genre |
| 6 | `top_genre_3_score` | double | Score for third genre |
| 7 | `scored_ts` | timestamp | When the score was computed |

**Rows:** ~25,000 | **Grain:** One row per customer | **Mirror:** `gold_media_top_genres_per_user_sync` on Lakebase

---

### gold_media_customer_ltv
Lifetime Value scores with component breakdown.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** FK to customer_360 |
| 1 | `email` | string | Customer email |
| 2 | `ltv_score` | double | Composite LTV (unbounded, typically 0–500+) |
| 3 | `ltv_category` | string | High (>=200), Medium (>=100), Low |
| 4 | `subscription_value` | double | Annual subscription value + historical spend |
| 5 | `engagement_value` | double | Normalized engagement score (0–100) |
| 6 | `ad_revenue_potential` | double | Estimated ad revenue contribution |
| 7 | `subscription_annual_value` | int | Annual tier price: basic=120, standard=180, premium=240, family=300 |
| 8 | `total_spend` | double | Lifetime commerce spend ($) |
| 9 | `current_subscription_tier` | string | Active tier or null |
| 10 | `scored_ts` | timestamp | When the score was computed |

**Rows:** ~10,000 | **Grain:** One row per customer | **Mirror:** `gold_media_customer_ltv_sync` on Lakebase

---

### gold_media_audience_segments
Marketing-ready audience segments combining persona, engagement, churn, and LTV.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** FK to customer_360 |
| 1 | `email` | string | Customer email |
| 2 | `persona` | string | Behavioral persona |
| 3 | `primary_segment` | string | Sports Enthusiast, News Consumer, Entertainment Seeker, Casual Browser, Digital Native |
| 4 | `value_segment` | string | Premium Engaged, High Value, Conversion Target, At Risk, Churned, Standard |
| 5 | `content_segment` | string | "{top_genre} - {engagement_level}" combo |
| 6 | `engagement_level` | string | High (50+ events), Medium (20+), Low |
| 7 | `ltv_category` | string | High, Medium, Low |
| 8 | `churn_risk_category` | string | High, Medium, Low |
| 9 | `is_churned` | boolean | Churned flag |
| 10 | `has_subscription` | boolean | Active subscription flag |
| 11 | `is_multi_platform` | boolean | Uses 2+ platforms |
| 12 | `total_events` | bigint | Total engagement events |
| 13 | `platforms_used` | bigint | Platform count |
| 14 | `top_genre_1` | string | Favorite genre |
| 15 | `segmented_ts` | timestamp | When segmentation was computed |

**Rows:** ~10,000 | **Grain:** One row per customer | **Mirror:** `gold_media_audience_segments_sync` on Lakebase

---

### gold_media_campaign_engagement
Campaign funnel history with one row per `(canonical_id, campaign_id)`. Captures the full marketing funnel — **sent → delivered → opened → clicked → offer_accepted → converted** — with per-stage timestamps. Each row pitches a specific show (`content_id`) inside a genre (`content_category`), so participants can build segment-level creative and attribution analyses.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `engagement_id` | string | **PK.** Deterministic id of form `eng_<16-hex>` |
| 1 | `canonical_id` | string | **FK** → `customer_360.canonical_id` |
| 2 | `email` | string | Normalized email (denormalized for quick filtering) |
| 3 | `campaign_id` | string | Campaign code, e.g. `cmp_drama_newseason_2026q1` |
| 4 | `campaign_name` | string | Human-readable name |
| 5 | `campaign_type` | string | `launch`, `retention`, `cross_sell`, `winback`, `upsell` |
| 6 | `content_category` | string | Genre bucket: `Drama`, `Kids`, `Sports`, `News`, `Documentary`, `Entertainment` |
| 7 | `content_id` | string | Show/event being pitched (join to `content_catalog`) |
| 8 | `content_title` | string | Show title (denormalized from content_catalog) |
| 9 | `channel` | string | `email`, `push`, `in_app` |
| 10 | `variant` | string | A/B/C assignment: `control`, `variant_a`, `variant_b` |
| 11 | `offer_type` | string | `free_trial`, `discount_pct`, `content_unlock`, `bundle_upgrade`, `none` |
| 12 | `offer_value_text` | string | Human-readable offer (e.g. `20% off family plan upgrade`) |
| 13 | `offer_face_value_usd` | decimal(10,2) | Face value of the offer in USD |
| 14 | `subject_line` | string | Email/push subject line |
| 15 | `sent_at` | timestamp | Send time |
| 16 | `delivered` | boolean | Reached the inbox/device |
| 17 | `delivered_at` | timestamp | Delivery time (null if not delivered) |
| 18 | `opened` | boolean | Open event fired |
| 19 | `opened_at` | timestamp | Open time (null if not opened) |
| 20 | `clicked` | boolean | Click-through event |
| 21 | `clicked_at` | timestamp | Click time |
| 22 | `offer_accepted` | boolean | Offer redemption started |
| 23 | `offer_accepted_at` | timestamp | Accept time |
| 24 | `converted` | boolean | Conversion event (trial start, upgrade, purchase) |
| 25 | `converted_at` | timestamp | Conversion time |
| 26 | `conversion_type` | string | `trial_start`, `content_purchase`, `upgrade`, `resubscribe` (null if not converted) |
| 27 | `revenue_generated_usd` | decimal(10,2) | Revenue attributed to this engagement |
| 28 | `unsubscribed` | boolean | User unsubscribed in response |
| 29 | `bounced` | boolean | Bounced (email only) |
| 30 | `device_type` | string | `mobile`, `desktop`, `tv`, `tablet` |
| 31 | `engagement_score` | int | 0–100 additive score: delivered(10) + opened(15) + clicked(25) + accepted(25) + converted(25) |
| 32 | `campaign_start_date` | date | Campaign window start |
| 33 | `campaign_end_date` | date | Campaign window end |
| 34 | `created_ts` | timestamp | When this row was generated |

**Grain:** One row per `(canonical_id, campaign_id)` | **Mirror:** `gold_media_campaign_engagement_sync` on Lakebase

**Funnel semantics:** `delivered ⊇ opened ⊇ clicked ⊇ offer_accepted ⊇ converted`. `offer_accepted` is only possible when `offer_type != 'none'`. Campaign eligibility is pre-filtered by segment + value_segment + genre affinity, so every row is a realistic send, not a blanket blast.

---

## Buy Side Gold Layer (Paid Media & Creative Supply Chain)

The following tables extend the Customer 360 to support the **Buy Side** (brand/agency paid media) brief. They provide the seed data the Personalized Creative Activation Command Center needs as input — 3P enrichment, marketing briefs, media plans, concept history, and a base asset catalog. All reuse the same `canonical_id` backbone and existing enum vocabularies.

### gold_media_customer_enrichment
Third-party demographic, household, and intent signals layered onto 1P customer identities. Bridges the gap between knowing what customers *do* on the platform and who they are *outside* it — essential for brief translation, audience construction, and per-user creative personalization.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `canonical_id` | string | **PK.** FK to customer_360 |
| 1 | `age_bucket` | string | Age range: 18-24, 25-34, 35-44, 45-54, 55-64, 65+ |
| 2 | `gender` | string | Male, Female, Non-Binary, Unknown |
| 3 | `household_composition` | string | Single, Couple_No_Kids, Young_Family, Established_Family, Empty_Nest, Multi_Generational |
| 4 | `household_size` | int | Estimated household members (1–7) |
| 5 | `income_band` | string | Under_25K, 25K_50K, 50K_75K, 75K_100K, 100K_150K, 150K_Plus |
| 6 | `education_level` | string | High_School, Some_College, Bachelors, Graduate, Unknown |
| 7 | `home_ownership` | string | Owner, Renter, Unknown |
| 8 | `language_preference` | string | Primary language: English, Spanish, French, Mandarin, Other |
| 9 | `life_event_recent_move` | boolean | Moved in last 12 months |
| 10 | `life_event_new_parent` | boolean | New parent in last 12 months |
| 11 | `life_event_new_homeowner` | boolean | Became homeowner in last 12 months |
| 12 | `life_event_new_job` | boolean | Changed jobs in last 12 months |
| 13 | `intent_score_sports` | double | Category intent score for Sports (0.0–1.0) from 3P behavioral data |
| 14 | `intent_score_entertainment` | double | Category intent score for Entertainment (0.0–1.0) |
| 15 | `intent_score_news` | double | Category intent score for News (0.0–1.0) |
| 16 | `intent_score_family` | double | Category intent score for Family/Kids content (0.0–1.0) |
| 17 | `intent_score_premium_upgrade` | double | Propensity to upgrade subscription tier (0.0–1.0) |
| 18 | `ad_receptivity_score` | double | Modeled ad engagement propensity (0.0–1.0) |
| 19 | `enrichment_source` | string | Primary 3P provider: Acxiom, Experian, LiveRamp |
| 20 | `enrichment_confidence` | double | Match confidence (0.0–1.0) |
| 21 | `enrichment_refresh_ts` | timestamp | When 3P data was last refreshed |
| 22 | `created_ts` | timestamp | Record creation timestamp |

**Rows:** ~10,000 | **Grain:** One row per customer | **Mirror:** `gold_media_customer_enrichment_sync` on Lakebase

---

### gold_media_creative_briefs
Marketing brief repository — the entry point for the Buy Side workflow. Each brief captures an objective, audience description, message pillars, KPI targets, channel/format requirements, and budget. The application reads briefs, translates them into structured audiences and concepts, and drives the full creative pipeline downstream.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `brief_id` | string | **PK.** Unique brief identifier, e.g. `brief_sports_awareness_2026q2` |
| 1 | `brief_name` | string | Human-readable brief name |
| 2 | `brief_source` | string | `Brand`, `Agency`, `Internal_Marketing` |
| 3 | `brief_type` | string | `Brand`, `Performance`, `Hybrid`, `Retail_Media`, `Lifecycle` |
| 4 | `objective` | string | `Awareness`, `Consideration`, `Conversion`, `Loyalty`, `Reactivation` |
| 5 | `audience_description_text` | string | Free-text audience description from the submitter |
| 6 | `target_primary_segments` | string | Comma-separated from existing enum: Sports Enthusiast, News Consumer, etc. |
| 7 | `target_value_segments` | string | Comma-separated from existing enum: Premium Engaged, High Value, etc. |
| 8 | `target_content_genres` | string | Comma-separated from existing enum: Sports, Drama, etc. |
| 9 | `message_pillars` | string | JSON array of message pillars, e.g. `["Exclusive live access","Family bonding"]` |
| 10 | `mandatory_inclusions` | string | JSON array: elements that MUST appear in creative |
| 11 | `mandatory_exclusions` | string | JSON array: elements that must NOT appear |
| 12 | `kpi_targets` | string | JSON object: `{"ctr": 0.025, "roas": 4.0, "brand_lift_pct": 8.0}` |
| 13 | `channel_requirements` | string | JSON array of required channels: `["Display","CTV","Social"]` |
| 14 | `format_requirements` | string | JSON array of required formats: `["1920x1080","1080x1080","9x16"]` |
| 15 | `budget_usd` | double | Total brief budget in USD |
| 16 | `flight_start_date` | date | Campaign flight start |
| 17 | `flight_end_date` | date | Campaign flight end |
| 18 | `brand_name` | string | Advertiser brand name |
| 19 | `product_name` | string | Product or show being promoted |
| 20 | `brief_status` | string | `Draft`, `Translated`, `Approved`, `In_Production`, `Activated`, `Archived` |
| 21 | `submitted_by` | string | Submitter name/role |
| 22 | `submitted_ts` | timestamp | Brief submission timestamp |
| 23 | `updated_ts` | timestamp | Last update timestamp |
| 24 | `created_ts` | timestamp | Record creation timestamp |

**Rows:** ~20 | **Grain:** One row per brief | **Mirror:** `gold_media_creative_briefs_sync` on Lakebase

---

### gold_media_media_plan_line_items
Paid media plan structure defining where creatives will run — the DSP, deal type, placement format, platform specs, and budget/pacing for each line item. The existing `gold_media_campaign_engagement` covers CRM channels (email, push, in_app); this table fills the paid-media buying structure gap: programmatic DSPs, walled gardens, deal types, and format constraints.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `line_item_id` | string | **PK.** Unique line item ID, e.g. `li_sports_ctv_pg_001` |
| 1 | `insertion_order_id` | string | Parent insertion order, e.g. `io_sports_q2_001` |
| 2 | `campaign_id` | string | Parent campaign ID (may match campaign_engagement.campaign_id) |
| 3 | `brief_id` | string | **FK** → `creative_briefs.brief_id` |
| 4 | `line_item_name` | string | Human-readable name |
| 5 | `dsp_platform` | string | `The_Trade_Desk`, `DV360`, `Amazon_DSP`, `Meta`, `Google_Ads`, `TikTok`, `Innovid` |
| 6 | `exchange_inventory_source` | string | Exchange or inventory source, e.g. `OpenX`, `PubMatic`, `Direct` |
| 7 | `deal_id` | string | Deal identifier (null for Open market) |
| 8 | `deal_type` | string | `PG`, `PMP`, `Preferred`, `Open` |
| 9 | `placement_format` | string | `Display`, `Online_Video`, `CTV`, `Native`, `Social`, `Audio`, `Retail_Media` |
| 10 | `platform_spec_width` | int | Creative width in pixels (e.g. 1920, 1080, 300) |
| 11 | `platform_spec_height` | int | Creative height in pixels (e.g. 1080, 1920, 250) |
| 12 | `platform_spec_aspect_ratio` | string | Aspect ratio: `16:9`, `1:1`, `9:16`, `4:5`, `300x250` |
| 13 | `platform_spec_duration_max_sec` | int | Max creative duration in seconds (null for static) |
| 14 | `target_primary_segments` | string | Comma-separated target segments from existing enum |
| 15 | `target_content_genres` | string | Comma-separated target genres from existing enum |
| 16 | `target_geo` | string | Geographic targeting: `National`, `Regional`, or specific DMAs |
| 17 | `target_daypart` | string | `All_Day`, `Primetime`, `Morning`, `Late_Night` |
| 18 | `personalization_granularity` | string | `Segment`, `Micro_Cohort`, `One_to_One` |
| 19 | `budget_usd` | double | Line item budget in USD |
| 20 | `daily_pacing_usd` | double | Daily spend pace in USD |
| 21 | `frequency_cap` | int | Max impressions per user per day |
| 22 | `flight_start_date` | date | Line item flight start |
| 23 | `flight_end_date` | date | Line item flight end |
| 24 | `line_item_status` | string | `Draft`, `Booked`, `Live`, `Paused`, `Ended` |
| 25 | `created_ts` | timestamp | Record creation timestamp |

**Rows:** ~120 | **Grain:** One row per line item (Campaign → Insertion Order → Line Item) | **Mirror:** `gold_media_media_plan_line_items_sync` on Lakebase

---

### gold_media_creative_concepts
Historical/seed creative concept directions per brief and audience. While the application generates new concepts at runtime, it also needs a catalog of prior concepts to power the "prior-art matching" feature — pairing each new concept with historical creatives and playbooks that most resemble it. Seed data ensures the recommendation engine is functional on day one.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `concept_id` | string | **PK.** Unique concept ID, e.g. `cpt_sports_family_bonding_001` |
| 1 | `brief_id` | string | **FK** → `creative_briefs.brief_id` |
| 2 | `concept_name` | string | Short concept name, e.g. "Game Night Together" |
| 3 | `narrative_thesis` | string | 1–3 sentence narrative direction for the concept |
| 4 | `tone` | string | `Inspirational`, `Humorous`, `Urgent`, `Heartfelt`, `Edgy`, `Premium`, `Informational` |
| 5 | `visual_treatment` | string | `Bold_Graphic`, `Cinematic`, `UGC_Style`, `Minimalist`, `Action_Shot`, `Lifestyle`, `Data_Driven` |
| 6 | `message_pillars` | string | JSON array of message pillars this concept expresses |
| 7 | `target_primary_segment` | string | Primary audience segment from existing enum |
| 8 | `target_content_genre` | string | Primary content genre from existing enum |
| 9 | `target_value_segment` | string | Value segment from existing enum (nullable) |
| 10 | `prior_concept_performance_score` | double | Historical performance of similar concepts (0.0–1.0, null if first-of-kind) |
| 11 | `concept_to_brief_alignment_score` | double | Model-scored alignment between concept and brief intent (0.0–1.0) |
| 12 | `concept_status` | string | `Draft`, `Approved`, `Rejected`, `Archived` |
| 13 | `created_by` | string | Creator: `AI_Generated`, `Creative_Director`, `Agency` |
| 14 | `approved_by` | string | Approver name/role (null if not yet approved) |
| 15 | `created_ts` | timestamp | Concept creation timestamp |
| 16 | `updated_ts` | timestamp | Last update timestamp |

**Rows:** ~60 | **Grain:** One row per concept (multiple concepts per brief) | **Mirror:** `gold_media_creative_concepts_sync` on Lakebase

---

### gold_media_brand_asset_library
Governed catalog of approved base creative assets and DCO template components that the creative generation pipeline pulls from as source material. Without a populated asset library, the generation step has no base material to resize, reframe, or adapt.

| # | Column | Type | Description |
|---|--------|------|-------------|
| 0 | `asset_id` | string | **PK.** Unique asset ID, e.g. `ast_hero_sports_001` |
| 1 | `asset_name` | string | Human-readable asset name |
| 2 | `asset_type` | string | `Image`, `Video`, `Audio`, `DCO_Template` |
| 3 | `source_type` | string | `Studio_Master`, `In_House_Creative`, `Stock`, `Library_Asset`, `Template_Component` |
| 4 | `slot_type` | string | For DCO templates: `Hero`, `Headline`, `Subhead`, `CTA`, `Product_Slot`, `End_Card`, `Legal`. Null for non-template assets |
| 5 | `content_genre` | string | Primary genre from existing enum: Sports, News, Drama, etc. |
| 6 | `brand_name` | string | Associated brand |
| 7 | `product_name` | string | Associated product/show (nullable) |
| 8 | `format` | string | File format: `PNG`, `JPG`, `MP4`, `WAV`, `HTML5` |
| 9 | `width_px` | int | Asset width in pixels |
| 10 | `height_px` | int | Asset height in pixels |
| 11 | `aspect_ratio` | string | `16:9`, `1:1`, `9:16`, `4:5` |
| 12 | `duration_sec` | int | Duration in seconds (null for static images) |
| 13 | `storage_uri` | string | Path in Volumes: `/Volumes/cme_outcomes_uswest/media_demo/creatives/<asset_id>.<format>` |
| 14 | `content_tags` | string | JSON array of tags: `["sports","live_event","family","summer_2026"]` |
| 15 | `approved_channels` | string | JSON array: `["Web","App","CTV","Social","Email","Retail_Media"]` |
| 16 | `allow_ai_modification` | boolean | Whether the asset can be used as input for AI generation/editing |
| 17 | `rights_expiration_date` | date | When usage rights expire (null if perpetual) |
| 18 | `brand_guardrail_flags` | string | JSON array: `["no_competitor_adjacency","talent_approval_required"]` |
| 19 | `asset_status` | string | `Active`, `Expired`, `Archived` |
| 20 | `created_ts` | timestamp | Record creation timestamp |

**Rows:** ~200 | **Grain:** One row per asset or template component | **Mirror:** `gold_media_brand_asset_library_sync` on Lakebase

---

## Supporting Silver Tables

These are available if participants need event-level detail or the identity graph.

| Table | Grain | Rows | Key Columns |
|-------|-------|------|-------------|
| `silver_media_identity_graph` | canonical_id x identifier | ~2,600 | `canonical_id`, `identifier`, `identifier_type`, `confidence_score` |
| `silver_media_unified_engagement` | event | ~79,000 | `canonical_id`, `event_id`, `platform`, `event_type`, `content_id`, `event_ts`, `watch_duration_seconds` |
| `silver_media_users` | user | ~10,000 | `user_id`, `email_normalized`, `persona`, `zip_code` |
| `silver_media_content_catalog` | content | varies | `content_id`, `title`, `genre`, `category`, `sport` |
| `silver_media_commerce_transactions` | transaction | varies | `user_id`, `transaction_type`, `amount`, `subscription_tier` |

---

## Join Pattern

```
customer_360 (canonical_id)
  |--- churn_predictions (canonical_id)
  |--- customer_ltv (canonical_id)
  |--- audience_segments (canonical_id)
  |--- top_genres_per_user (canonical_id)
  |--- content_affinity (canonical_id, content_genre)
  |--- customer_enrichment (canonical_id)          ← Buy Side
  |--- campaign_engagement (canonical_id)

creative_briefs (brief_id)                         ← Buy Side
  |--- creative_concepts (brief_id)                ← Buy Side
  |--- media_plan_line_items (brief_id)            ← Buy Side

media_plan_line_items (campaign_id)
  |--- campaign_engagement (campaign_id)           ← cross-link

brand_asset_library (asset_id)                     ← Buy Side
  [standalone reference; queried by content_genre + format at generation time]
```

All customer-keyed gold tables join 1:1 on `canonical_id` except `content_affinity` (1:many, one row per genre) and `campaign_engagement` (1:many, one row per campaign). The Buy Side brief/concept/media-plan tables form a separate graph keyed on `brief_id`, linked to the customer graph via `campaign_id` on `media_plan_line_items`.

---

## Lakebase Access

All tables are synced to Lakebase (PostgreSQL) with a `_sync` suffix. Connect via the Lakebase project's PostgreSQL endpoint for low-latency app queries.

## Enum Values Reference

### Sell Side (Customer 360 & Engagement)

| Field | Values |
|-------|--------|
| `persona` | Sports Fan, News Junkie, Entertainment Binge Watcher, Casual Viewer, Cord Cutter |
| `primary_segment` | Sports Enthusiast, News Consumer, Entertainment Seeker, Casual Browser, Digital Native |
| `value_segment` | Premium Engaged, High Value, Conversion Target, At Risk, Churned, Standard |
| `engagement_level` | High, Medium, Low |
| `churn_risk_category` | High, Medium, Low |
| `ltv_category` | High, Medium, Low |
| `subscription_tier` | basic, standard, premium, family |
| `content_genre` | Sports, News, Entertainment, Drama, Comedy, Documentary, Reality, Kids |
| `platform` | web, mobile, ott, linear_tv |

### Buy Side (Enrichment, Briefs, Media Plans, Concepts, Assets)

> Fields in Buy Side tables marked "from existing enum" (e.g. `target_primary_segments`, `target_content_genres`, `content_genre`) reuse the Sell Side values above.

| Field | Values |
|-------|--------|
| `age_bucket` | 18-24, 25-34, 35-44, 45-54, 55-64, 65+ |
| `gender` | Male, Female, Non-Binary, Unknown |
| `household_composition` | Single, Couple_No_Kids, Young_Family, Established_Family, Empty_Nest, Multi_Generational |
| `income_band` | Under_25K, 25K_50K, 50K_75K, 75K_100K, 100K_150K, 150K_Plus |
| `education_level` | High_School, Some_College, Bachelors, Graduate, Unknown |
| `home_ownership` | Owner, Renter, Unknown |
| `enrichment_source` | Acxiom, Experian, LiveRamp |
| `brief_source` | Brand, Agency, Internal_Marketing |
| `brief_type` | Brand, Performance, Hybrid, Retail_Media, Lifecycle |
| `objective` | Awareness, Consideration, Conversion, Loyalty, Reactivation |
| `brief_status` | Draft, Translated, Approved, In_Production, Activated, Archived |
| `dsp_platform` | The_Trade_Desk, DV360, Amazon_DSP, Meta, Google_Ads, TikTok, Innovid |
| `deal_type` | PG, PMP, Preferred, Open |
| `placement_format` | Display, Online_Video, CTV, Native, Social, Audio, Retail_Media |
| `personalization_granularity` | Segment, Micro_Cohort, One_to_One |
| `line_item_status` | Draft, Booked, Live, Paused, Ended |
| `tone` | Inspirational, Humorous, Urgent, Heartfelt, Edgy, Premium, Informational |
| `visual_treatment` | Bold_Graphic, Cinematic, UGC_Style, Minimalist, Action_Shot, Lifestyle, Data_Driven |
| `concept_status` | Draft, Approved, Rejected, Archived |
| `asset_type` | Image, Video, Audio, DCO_Template |
| `source_type` | Studio_Master, In_House_Creative, Stock, Library_Asset, Template_Component |
| `slot_type` | Hero, Headline, Subhead, CTA, Product_Slot, End_Card, Legal |
| `asset_status` | Active, Expired, Archived |
