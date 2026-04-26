CREATE TABLE IF NOT EXISTS generated_campaigns (
    campaign_id TEXT PRIMARY KEY,
    segment_filter_json JSONB NOT NULL,
    assets_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL CHECK (status IN ('running', 'complete', 'approved', 'exported', 'failed')),
    created_by TEXT NOT NULL,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_generated_campaigns_status
    ON generated_campaigns (status, created_ts DESC);

CREATE INDEX IF NOT EXISTS idx_generated_campaigns_created_by
    ON generated_campaigns (created_by, created_ts DESC);
