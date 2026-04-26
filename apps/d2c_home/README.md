# D2C Home Screen Reference App

A FastAPI reference app for the CME Build Day sell-side demo. Serves a
personalized streaming-home-screen hero image + copy for a given customer
(`/hero/{canonical_id}`), backed by:

- **Lakebase** — audience segment rows synced from
  `cme_outcomes_uswest.media_demo.gold_media_audience_segments`.
- **UC Volume cache** — pre-rendered hero images keyed by a sha256 of the
  generation request (see `lakefoundry.creative.azure_openai_image.cache_key`).
  Populated by the batch pre-gen pipeline in Task 9.
- **Persona-default fallback** — if the cache misses, returns a static image
  from `static/persona_defaults/<persona_slug>.png`.

Task 11 layers HyperFrames motion + an HTML UI on top of this backend. Task 10
is the pure backend + tests.

## Run tests locally

```bash
cd apps/d2c_home
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest httpx
pytest tests/
```

Expected: `2 passed`.

The app uses `build_app(fetch_segment=..., image_client=..., fetch_copy=...)`
dependency injection, so the tests inject mocks for all I/O.

## Run locally (dev)

```bash
source .venv/bin/activate
export CREATIVES_VOLUME_ROOT=/tmp/heroes
export AZURE_OPENAI_ENDPOINT=https://lakefoundry-azure-openai.openai.azure.com/
export AZURE_OPENAI_KEY=...
export PGHOST=... PGDATABASE=... PGUSER=... PGPASSWORD=...
uvicorn main:app --reload
```

## Deploy to Databricks Apps

1. Upload this folder to the workspace (e.g. `/Workspace/Users/<me>/apps/d2c_home`).
2. Create a Databricks App pointing at that folder. The `app.yaml` declares
   the uvicorn command + env var wiring (Lakebase creds + Azure OpenAI key
   pulled from secrets).
3. Configure the referenced secrets in the app's secret scope:
   - `azure_openai_key_secret`
   - `lakebase_host`, `lakebase_database`, `lakebase_user`, `lakebase_password`
4. Ensure the app's service principal has `READ_VOLUME` on
   `/Volumes/cme_outcomes_uswest/media_demo/creatives/heroes`.

## Files

| File | Purpose |
|------|---------|
| `app.py` | `build_app()` factory + `/hero/{canonical_id}` route. DI-friendly. |
| `main.py` | Production entrypoint: wires real Lakebase + Azure OpenAI into `build_app()`. |
| `routes.py` | Placeholder — Task 11 may extract routes here. |
| `app.yaml` | Databricks Apps manifest. |
| `requirements.txt` | Python deps incl. editable install of `lakefoundry.creative`. |
| `tests/test_routes.py` | Two unit tests covering cached + persona-default paths. |
| `templates/index.html` | Placeholder — Task 11 populates. |
