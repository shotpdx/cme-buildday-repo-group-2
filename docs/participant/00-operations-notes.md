# 00 - Operations Notes

Operational prerequisites and environment checks for the CME Build Day creative-generation workstream. Update this file as each item is confirmed.

## UC Volume status

Target path: `dbfs:/Volumes/cme_outcomes_uswest/media_demo/creatives/`

Profile used for check: `uswest` (workspace `https://dbc-fa80cb73-9755.cloud.databricks.com`).

Current status as of Task 1 scaffolding:

- `databricks fs ls dbfs:/Volumes/cme_outcomes_uswest/media_demo/creatives/ --profile uswest` returns
  `Error: no such directory: /Volumes/cme_outcomes_uswest/media_demo/creatives`.
- `databricks catalogs get cme_outcomes_uswest --profile uswest` returns
  `Error: Catalog 'cme_outcomes_uswest' is not accessible in current workspace`.
- The catalog does not appear in `databricks catalogs list --profile uswest`. The related online catalog
  `lakefoundry_db_cme-outcomes` is present but is not the Unity Catalog catalog needed here.

Action required before Task 2 runs end-to-end:

1. Create (or request creation of) the catalog `cme_outcomes_uswest` in the `uswest` workspace, or confirm the correct catalog name if it differs.
2. Create schema `cme_outcomes_uswest.media_demo`.
3. Create volume: `databricks volumes create cme_outcomes_uswest media_demo creatives MANAGED --profile uswest`.
4. Re-run the `databricks fs ls` check above and confirm the volume is listable (empty result is expected).

This task (Task 1) intentionally did not auto-create the catalog because the plan's remediation only covered creating the volume under an existing catalog. Flag this during standup so the owner of the `uswest` workspace can provision the catalog/schema.

## Azure OpenAI quota verification checklist

Model: `gpt-image-2` (Azure OpenAI). Verify the following before Build Day.

Headroom target: 6 teams x approximately 50 images = approximately 300 images total, with comfortable bursts from parallel participants.

Items to verify via the Azure portal (Azure OpenAI resource -> Model deployments -> gpt-image-2) or the Azure CLI:

- [ ] **TPM (tokens per minute) limit** on the `gpt-image-2` deployment. Capture the current cap and confirm it supports concurrent image prompts for 6 teams.
- [ ] **RPM (requests per minute) limit** on the deployment. Rule of thumb: target at least ~60 RPM to give each team ~10 RPM headroom; raise if batch pre-gen (Task 9) uses higher parallelism.
- [ ] **Deployment region** matches the region used by the Databricks App / SDP pipelines (latency, data residency).
- [ ] **Content filter policy** assigned to the deployment is one we expect (default vs custom).
- [ ] **API version** currently pinned matches what the `azure-openai-image` skill / helper library will use (Task 3).

Azure CLI commands to capture the numbers for the record (run from a workstation authenticated to the Azure subscription):

```bash
# List the Azure OpenAI accounts visible to your account
az cognitiveservices account list --query "[?kind=='OpenAI'].{name:name, group:resourceGroup, region:location}" -o table

# Inspect deployments on the specific account (replace <account> and <rg>)
az cognitiveservices account deployment list \
  --name <account> \
  --resource-group <rg> \
  -o table

# Show full config (including sku capacity == TPM in thousands) for gpt-image-2
az cognitiveservices account deployment show \
  --name <account> \
  --resource-group <rg> \
  --deployment-name gpt-image-2
```

If quota is tight (below ~60 RPM / below expected TPM for a single image prompt x 6 teams x burst factor), **file an Azure quota increase at least 1-2 business days before Build Day** — that is the typical turnaround. Note the case ID and target values here once filed.

## Change log

- 2026-04-26: File created during Task 1 (scaffold). UC volume `cme_outcomes_uswest/media_demo/creatives` does not yet exist; catalog itself not accessible in `uswest` workspace. Azure quota not yet verified.
