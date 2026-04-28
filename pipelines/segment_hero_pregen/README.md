# Segment Hero Pre-Generation

Two-step batch job that populates the UC Volume hero cache before Build Day.

## Step 1: Refresh the segment keys (DLT pipeline)

```bash
databricks pipelines create-pipeline --json-file pipeline_config.json --profile uswest
databricks pipelines start --pipeline-id <id> --profile uswest
```

Materializes `cme_outcomes_uswest.media_demo.segment_hero_keys` (~30 rows, filtered to segments with ≥3 customers).

## Step 2: Render heroes (notebook task)

Run `generate.py` as a Databricks notebook task. Reads the keys table, renders one hero per segment at `quality="medium"`, writes to the UC Volume. Budget: ~35 minutes, ~$3-5.

## Schedule

- **Before Build Day:** run once manually.
- **During Build Day:** scheduled nightly at 2am local.
