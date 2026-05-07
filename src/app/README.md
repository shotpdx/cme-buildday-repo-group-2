# CME Next Best Actions Engine

Agent-driven decisioning engine for high-churn-risk customer retention.

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend development)

### Backend

```bash
cd src/app
pip install -r requirements.txt
python app.py
```

The backend runs on `http://localhost:8080` by default. Set `PORT=8081` if 8080 is in use:

```bash
PORT=8081 python app.py
```

By default, the app uses mock data (`USE_MOCK_BACKEND=true`). To connect to real Databricks tables:

```bash
USE_MOCK_BACKEND=false USE_MOCK_SUPERVISOR=false DATABRICKS_WAREHOUSE_ID=<id> python app.py
```

### Frontend

```bash
cd src/app/ui
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api` requests to the backend at `http://127.0.0.1:8081`.

### Deploy to Databricks Apps

1. Build the frontend:
   ```bash
   cd src/app/ui && npm run build
   ```

2. Upload to workspace:
   ```bash
   databricks workspace import-dir src/app /Workspace/Users/<you>/paramount-churn-risk-dev --profile cme-outcomes --overwrite
   ```
   Only upload the files needed: `app.py`, `backend.py`, `models.py`, `__init__.py`, `requirements.txt`, `app.yaml`, and `ui/dist/`.

3. Deploy:
   ```bash
   databricks apps deploy paramount-churn-risk-dev --source-code-path /Workspace/Users/<you>/paramount-churn-risk-dev --profile cme-outcomes
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Backend port |
| `USE_MOCK_BACKEND` | `true` | Use mock data instead of Databricks SQL |
| `USE_MOCK_SUPERVISOR` | `true` | Use simulated agent instead of real MAS endpoint |
| `DATABRICKS_WAREHOUSE_ID` | — | SQL warehouse ID (required when mock is off) |
| `DATABRICKS_CATALOG` | `cme_outcomes_uswest` | Unity Catalog name |
| `DATABRICKS_SCHEMA` | `media_demo` | Schema name |
| `NBA_SUPERVISOR_ENDPOINT` | `mas-c4ed84f2-endpoint` | Model serving endpoint for agent |
