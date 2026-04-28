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

**Rows:** ~10,000 | **Grain:** One row per customer

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

**Rows:** ~10,000 | **Grain:** One row per customer

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

**Rows:** ~66,000 | **Grain:** One row per customer per genre

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

**Rows:** ~25,000 | **Grain:** One row per customer

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

**Rows:** ~10,000 | **Grain:** One row per customer

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

**Rows:** ~10,000 | **Grain:** One row per customer

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
```

All gold tables join 1:1 on `canonical_id` except `content_affinity` which is 1:many (one row per genre).

---

## Lakebase Access

All tables are synced to Lakebase (PostgreSQL) with a `_sync` suffix. Connect via the Lakebase project's PostgreSQL endpoint for low-latency app queries.

## Enum Values Reference

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
