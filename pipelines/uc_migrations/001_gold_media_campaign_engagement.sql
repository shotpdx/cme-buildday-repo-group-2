CREATE OR REPLACE TABLE cme_outcomes_uswest.media_demo.gold_media_campaign_engagement
COMMENT 'Gold-layer campaign engagement history. One row per (canonical_id, campaign_id) capturing the full funnel (sent -> delivered -> opened -> clicked -> offer_accepted -> converted). Pitches a specific show (content_id, show-level) tied to a content_category. Deterministically synthesized from gold_media_customer_360 + gold_media_audience_segments + content_catalog.'
AS
WITH campaigns AS (
  SELECT * FROM VALUES
    ('cmp_drama_newseason_2026q1',    'New Dramas This Season',        'launch',      'Drama',         'email',  'free_trial',      '30-day free premium trial',    CAST(0.00 AS DOUBLE), 'Your next obsession just dropped'),
    ('cmp_drama_midseason_push_2026', 'Mid-season Drama Push',         'retention',   'Drama',         'push',   'none',            '',                             CAST(0.00 AS DOUBLE), 'The drama continues tonight'),
    ('cmp_kids_family_promo_2026',    'Family Plan Promo',             'cross_sell',  'Kids',          'email',  'discount_pct',    '20% off family plan upgrade',  CAST(4.00 AS DOUBLE), 'Family movie nights, made easy'),
    ('cmp_kids_summer_launch_2026',   'Summer Kids Lineup',            'launch',      'Kids',          'in_app', 'content_unlock',  'Unlock 12 new kids shows',     CAST(0.00 AS DOUBLE), 'Summer just got 12 shows bigger'),
    ('cmp_sports_playoffs_2026',      'Playoff Coverage Starts Now',   'launch',      'Sports',        'email',  'free_trial',      '7-day playoff trial',          CAST(0.00 AS DOUBLE), 'The playoffs start tonight'),
    ('cmp_sports_weekly_digest_2026', 'Weekly Sports Digest',          'retention',   'Sports',        'push',   'none',            '',                             CAST(0.00 AS DOUBLE), 'This weeks must-watch games'),
    ('cmp_news_morning_brief_2026',   'Morning News Brief',            'retention',   'News',          'email',  'none',            '',                             CAST(0.00 AS DOUBLE), 'Your 5-minute morning briefing'),
    ('cmp_news_election_spec_2026',   'Election Night Live',           'launch',      'News',          'email',  'content_unlock',  'Live election coverage unlock',CAST(0.00 AS DOUBLE), 'Live election night coverage'),
    ('cmp_docu_goldenhour_2026',      'Golden Hour Documentary Series','launch',      'Documentary',   'email',  'free_trial',      '14-day documentary trial',     CAST(0.00 AS DOUBLE), 'Stories that matter'),
    ('cmp_winback_freemonth_2026q1',  'Come Back - One Month Free',    'winback',     'Entertainment', 'email',  'free_trial',      '1 free month',                 CAST(15.00 AS DOUBLE),'We miss you - a month on us'),
    ('cmp_winback_30off_2026q1',      'Come Back - 30% Off',           'winback',     'Entertainment', 'email',  'discount_pct',    '30% off for 3 months',         CAST(12.00 AS DOUBLE),'30% off - pick up where you left off'),
    ('cmp_upsell_premium_bundle_26',  'Premium Bundle Upgrade',        'upsell',      'Entertainment', 'email',  'bundle_upgrade',  'Upgrade to Premium + Extras',  CAST(25.00 AS DOUBLE),'Upgrade and save')
  AS t(campaign_id, campaign_name, campaign_type, content_category, channel, offer_type, offer_value_text, offer_value_usd, subject_line)
),
show_pool AS (
  SELECT genre AS content_category,
         collect_list(content_id) AS show_ids,
         collect_list(title)      AS show_titles
  FROM cme_outcomes_uswest.media_demo.content_catalog
  WHERE content_type IN ('show','sports_event')
  GROUP BY genre
),
base AS (
  SELECT
    c.canonical_id, c.email, c.first_name,
    c.days_since_last_engagement, c.has_subscription, c.current_subscription_tier,
    s.primary_segment, s.value_segment, s.top_genre_1,
    s.engagement_level, s.churn_risk_category
  FROM cme_outcomes_uswest.media_demo.gold_media_customer_360 c
  JOIN cme_outcomes_uswest.media_demo.gold_media_audience_segments s USING (canonical_id)
),
eligible AS (
  SELECT b.*, cm.*,
    pmod(abs(hash(b.canonical_id, cm.campaign_id, 'elig')), 100) AS r_elig
  FROM base b
  CROSS JOIN campaigns cm
),
filtered AS (
  SELECT * FROM eligible
  WHERE
    CASE
      WHEN campaign_type = 'winback' THEN value_segment IN ('At Risk','Churned') AND r_elig < 85
      WHEN campaign_type = 'upsell'  THEN has_subscription = false AND r_elig < 45
      WHEN content_category = top_genre_1 THEN r_elig < 70
      WHEN primary_segment = 'Digital Native'       AND content_category IN ('Kids','Drama')           THEN r_elig < 28
      WHEN primary_segment = 'Sports Enthusiast'    AND content_category IN ('Sports','Drama')         THEN r_elig < 32
      WHEN primary_segment = 'News Consumer'        AND content_category IN ('News','Documentary')     THEN r_elig < 38
      WHEN primary_segment = 'Entertainment Seeker' AND content_category IN ('Drama','Entertainment')  THEN r_elig < 32
      WHEN primary_segment = 'Casual Browser'       AND content_category = 'Entertainment'             THEN r_elig < 22
      ELSE r_elig < 8
    END
),
with_content AS (
  SELECT f.*,
    element_at(sp.show_ids,    1 + pmod(abs(hash(f.canonical_id, f.campaign_id, 'cid')), coalesce(size(sp.show_ids), 1)))    AS content_id,
    element_at(sp.show_titles, 1 + pmod(abs(hash(f.canonical_id, f.campaign_id, 'cid')), coalesce(size(sp.show_titles), 1))) AS content_title
  FROM filtered f
  LEFT JOIN show_pool sp ON sp.content_category = f.content_category
),
rng AS (
  SELECT *,
    pmod(abs(hash(canonical_id, campaign_id, 'd')),   100)   AS r_d,
    pmod(abs(hash(canonical_id, campaign_id, 'o')),   100)   AS r_o,
    pmod(abs(hash(canonical_id, campaign_id, 'k')),   100)   AS r_k,
    pmod(abs(hash(canonical_id, campaign_id, 'a')),   100)   AS r_a,
    pmod(abs(hash(canonical_id, campaign_id, 'v')),   100)   AS r_v,
    pmod(abs(hash(canonical_id, campaign_id, 'u')),   1000)  AS r_u,
    pmod(abs(hash(canonical_id, campaign_id, 'var')), 100)   AS r_variant,
    pmod(abs(hash(canonical_id, campaign_id, 'dev')), 100)   AS r_device,
    pmod(abs(hash(canonical_id, campaign_id, 'day')), 75)    AS send_day_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'sec')), 86400) AS send_sec_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'oh')),  43200) AS open_sec_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'kh')),  57600) AS click_sec_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'ah')),  75600) AS accept_sec_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'vh')), 172800) AS convert_sec_offset,
    pmod(abs(hash(canonical_id, campaign_id, 'rev')), 2400)  AS rev_jitter
  FROM with_content
),
stages AS (
  SELECT *,
    CAST(from_unixtime(unix_timestamp(TIMESTAMP '2026-02-01 00:00:00') + send_day_offset*86400 + send_sec_offset) AS TIMESTAMP) AS sent_at_ts,
    (channel IN ('push','in_app') OR r_d < 96)  AS v_delivered
  FROM rng
),
stages2 AS (
  SELECT *,
    v_delivered AND (
      CASE
        WHEN channel = 'push'          THEN r_o < (45 + CASE WHEN content_category = top_genre_1 THEN 15 ELSE 0 END)
        WHEN channel = 'in_app'        THEN r_o < (55 + CASE WHEN content_category = top_genre_1 THEN 15 ELSE 0 END)
        WHEN campaign_type = 'winback' THEN r_o < (18 + CASE WHEN value_segment = 'At Risk' THEN 6 ELSE 0 END)
        ELSE                                r_o < (28 + CASE WHEN content_category = top_genre_1 THEN 12 ELSE 0 END)
      END
    ) AS v_opened
  FROM stages
),
stages3 AS (
  SELECT *,
    v_opened AND (r_k < (28 + CASE WHEN content_category = top_genre_1 THEN 12 ELSE 0 END)) AS v_clicked
  FROM stages2
),
stages4 AS (
  SELECT *,
    v_clicked AND (offer_type != 'none') AND (r_a < 48) AS v_offer_accepted
  FROM stages3
),
stages5 AS (
  SELECT *,
    v_offer_accepted AND (r_v < 65) AS v_converted
  FROM stages4
)
SELECT
  concat('eng_', substr(md5(concat(canonical_id, '|', campaign_id)), 1, 16)) AS engagement_id,
  canonical_id,
  email,
  campaign_id,
  campaign_name,
  campaign_type,
  content_category,
  content_id,
  content_title,
  channel,
  CASE pmod(r_variant, 3) WHEN 0 THEN 'control' WHEN 1 THEN 'variant_a' ELSE 'variant_b' END AS variant,
  offer_type,
  offer_value_text,
  CAST(offer_value_usd AS DECIMAL(10,2)) AS offer_face_value_usd,
  subject_line,
  sent_at_ts AS sent_at,
  v_delivered AS delivered,
  CASE WHEN v_delivered THEN CAST(from_unixtime(unix_timestamp(sent_at_ts) + 90) AS TIMESTAMP) END AS delivered_at,
  v_opened AS opened,
  CASE WHEN v_opened THEN CAST(from_unixtime(unix_timestamp(sent_at_ts) + 120 + open_sec_offset) AS TIMESTAMP) END AS opened_at,
  v_clicked AS clicked,
  CASE WHEN v_clicked THEN CAST(from_unixtime(unix_timestamp(sent_at_ts) + 300 + open_sec_offset + click_sec_offset) AS TIMESTAMP) END AS clicked_at,
  v_offer_accepted AS offer_accepted,
  CASE WHEN v_offer_accepted THEN CAST(from_unixtime(unix_timestamp(sent_at_ts) + 600 + open_sec_offset + click_sec_offset + accept_sec_offset) AS TIMESTAMP) END AS offer_accepted_at,
  v_converted AS converted,
  CASE WHEN v_converted THEN CAST(from_unixtime(unix_timestamp(sent_at_ts) + 1200 + open_sec_offset + click_sec_offset + accept_sec_offset + convert_sec_offset) AS TIMESTAMP) END AS converted_at,
  CASE
    WHEN NOT v_converted                 THEN NULL
    WHEN campaign_type = 'winback'       THEN 'resubscribe'
    WHEN campaign_type = 'upsell'        THEN 'upgrade'
    WHEN offer_type    = 'free_trial'    THEN 'trial_start'
    WHEN offer_type    = 'content_unlock'THEN 'content_purchase'
    WHEN offer_type    = 'bundle_upgrade'THEN 'upgrade'
    ELSE                                      'content_purchase'
  END AS conversion_type,
  CAST(CASE WHEN v_converted THEN offer_value_usd + (rev_jitter / 100.0) ELSE 0.0 END AS DECIMAL(10,2)) AS revenue_generated_usd,
  (r_u < 20)                                                          AS unsubscribed,
  (channel NOT IN ('push','in_app') AND NOT v_delivered)              AS bounced,
  CASE pmod(r_device, 4) WHEN 0 THEN 'mobile' WHEN 1 THEN 'desktop' WHEN 2 THEN 'tv' ELSE 'tablet' END AS device_type,
  CAST(
      CASE WHEN v_delivered       THEN 10 ELSE 0 END
    + CASE WHEN v_opened          THEN 15 ELSE 0 END
    + CASE WHEN v_clicked         THEN 25 ELSE 0 END
    + CASE WHEN v_offer_accepted  THEN 25 ELSE 0 END
    + CASE WHEN v_converted       THEN 25 ELSE 0 END
  AS INT) AS engagement_score,
  DATE'2026-02-01' AS campaign_start_date,
  DATE'2026-04-30' AS campaign_end_date,
  current_timestamp() AS created_ts
FROM stages5
