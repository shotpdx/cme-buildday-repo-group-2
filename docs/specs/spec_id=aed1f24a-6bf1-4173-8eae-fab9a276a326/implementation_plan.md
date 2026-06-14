# Paramount+ High Churn Risk Customer Application — Implementation Plan

**Goal:** Build a Dash web application deployed as a Databricks App that identifies high-churn-risk Paramount+ customers, summarizes their behaviors, and dynamically suggests marketing actions using rule-based logic against existing gold tables.

**Architecture:** A Python Dash application with a SQL-warehouse-backed backend that queries `cme_outcomes_uswest.media_demo` gold tables (customer_360, churn_predictions, top_genres_per_user, content_affinity, nba_action_library, nba_recommendations). The backend module builds the high-risk customer dataset by joining and filtering these tables, computes segment-level behavior summaries, and applies three rule-based recommendation engines. The frontend provides a tabbed interface: a filterable/sortable customer list, a segment summary dashboard with key metrics and charts, and a recommendations panel. Deployed via Databricks Asset Bundles (DABs).

---

### Task 1: Backend Data Access Layer

**Depends On:** none

**Files:**
- Create: `src/app/backend.py`
- Create: `src/app/models.py`

**Requirements:**
- `models.py`: Define Pydantic models for `HighRiskCustomer`, `SegmentSummary`, and `ActionRecommendation`.
- `backend.py`: Implement a `Backend` class that connects to the SQL warehouse using `databricks.sdk.core.Config` and `databricks-sql-connector`.
- **High-risk customer identification query:** Join `gold_media_customer_360` c with `gold_media_churn_predictions` p on `canonical_id`, and LEFT JOIN `gold_media_top_genres_per_user` g on `c.canonical_id = g.canonical_id`. Filter using condition A OR B:
  - **Condition A:** `customer_tenure_days >= 180` AND `churn_risk_score >= 0.65`
  - **Condition B:** `churn_risk_category = 'High'` AND `days_since_last_engagement > 30`
- Return columns: `canonical_id, email, first_name, last_name, persona, churn_risk_score, churn_risk_category, days_since_last_engagement, total_watch_seconds, unique_content_viewed, customer_tenure_days, has_subscription, current_subscription_tier, top_genre_1, is_multi_platform`
- **Segment summary query:** For the high-risk segment, compute:
  - Churn risk category distribution (count per category)
  - Persona distribution (count per persona)
  - Average `total_watch_seconds`, `days_since_last_engagement`, `unique_content_viewed`
  - Subscription status breakdown (`has_subscription` true/false counts)
  - Top 5 content genres by frequency of `top_genre_1`
- **Rule-based recommendations:** Implement three rules evaluated against the segment summary:
  - **Rule 1 (Content Action):** If >75% of segment has `unique_content_viewed = 1` AND there is a dominant `top_genre_1` (most frequent genre), recommend: "Curate a personalized {genre} content discovery campaign"
  - **Rule 2 (Win-back Action):** If >75% of segment has `churn_risk_category = 'High'` AND average `days_since_last_engagement > 45`, recommend: "Launch a win-back campaign with exclusive offers"
  - **Rule 3 (Engagement Action):** Default/fallback -- recommend: "Deploy a multi-channel re-engagement campaign with personalized content recommendations"
- All queries use parameterized catalog/schema from environment variables `DATABRICKS_CATALOG` and `DATABRICKS_SCHEMA` (default: `cme_outcomes_uswest` / `media_demo`).
- The warehouse connection uses `DATABRICKS_WAREHOUSE_ID` from environment.
- Include a `USE_MOCK_BACKEND` toggle. When `true`, return hardcoded sample data so the app can run without a warehouse.

**Acceptance Criteria:**
- [ ] `Backend.get_high_risk_customers()` returns a list of `HighRiskCustomer` models
- [ ] `Backend.get_segment_summary()` returns a `SegmentSummary` model with all required aggregations
- [ ] `Backend.get_recommendations()` returns a list of `ActionRecommendation` models based on rule evaluation
- [ ] Mock backend returns realistic sample data when `USE_MOCK_BACKEND=true`
- [ ] All tests pass

**Skills:** `databricks-app-python`, `databricks-dbsql`

---

### Task 2: Dash Frontend Application

**Depends On:** 1

**Files:**
- Create: `src/app/app.py`
- Create: `src/app/requirements.txt`

**Requirements:**
- Build a Dash application using `dash-bootstrap-components` with a dark professional theme.
- **Layout:** Three tabs:
  1. **High-Risk Customers** -- A `dash_table.DataTable` showing all high-risk customers with columns: Name (first + last), Email, Persona, Churn Risk Score, Churn Risk Category, Days Since Last Engagement, Watch Hours, Content Viewed, Subscription Status. Sortable by all columns. Filterable by churn_risk_category and persona via dropdowns. Include a row count badge. Add a CSV export button.
  2. **Segment Summary** -- Cards showing key metrics (total high-risk customers, avg churn score, avg days since engagement, avg watch hours). Below, a row of charts: churn risk category pie chart, persona distribution bar chart, top genres bar chart, subscription status pie chart.
  3. **Recommendations** -- Display the rule-based recommendations as styled cards. Each card shows: rule name, condition status (met/not met), and the recommended action text. Highlight the active recommendation(s).
- App must listen on port 8080 and host 0.0.0.0.
- `requirements.txt` must include: `dash-bootstrap-components`, `databricks-sql-connector`, `databricks-sdk`, `pydantic`.
- Use the backend toggle pattern: read `USE_MOCK_BACKEND` env var.
- On app startup, load data once via callbacks (not blocking the server start).

**Acceptance Criteria:**
- [ ] App starts successfully with `python app.py` on port 8080
- [ ] All three tabs render with correct data from backend
- [ ] Customer table is sortable and filterable
- [ ] CSV export downloads the customer list
- [ ] Charts render correctly in the summary tab
- [ ] Recommendation cards display with correct rule evaluation
- [ ] App works in mock mode without a SQL warehouse connection
- [ ] All tests pass

**Skills:** `databricks-app-python`, `web-design-guidelines`

---

### Task 3: DAB Bundle and Deployment

**Depends On:** 1, 2

**Files:**
- Create: `databricks.yml`
- Create: `resources/churn_risk_app.app.yml`
- Create: `src/app/app.yaml`

**Requirements:**
- Create a minimal DAB bundle at the repo root with `databricks.yml`.
- Bundle name: `paramount-churn-risk-app`
- Include pattern: `resources/*.yml`
- Single `dev` target with `mode: development` and `default: true`. Do NOT set `workspace.host`.
- Create the app resource in `resources/churn_risk_app.app.yml`:
  - App name: `paramount-churn-risk-${bundle.target}`
  - Source code path: `../src/app`
- Create `src/app/app.yaml` with:
  - Command: `["python", "app.py"]`
  - Environment variables: `USE_MOCK_BACKEND=false`, `DATABRICKS_WAREHOUSE_ID=d24059778e957e41`, `DATABRICKS_CATALOG=cme_outcomes_uswest`, `DATABRICKS_SCHEMA=media_demo`
- Validate the bundle with `databricks bundle validate`
- Deploy with `databricks bundle deploy`
- Run with `databricks bundle run churn_risk_app`
- Verify the app starts and is accessible

**Acceptance Criteria:**
- [ ] `databricks bundle validate` passes with no errors
- [ ] `databricks bundle deploy` succeeds
- [ ] `databricks bundle run churn_risk_app` starts the app
- [ ] App is accessible and shows real data from Unity Catalog tables
- [ ] All files committed

**Skills:** `asset-bundles`, `databricks-app-python`
