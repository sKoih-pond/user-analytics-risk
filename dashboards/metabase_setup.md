# Metabase dashboard

Metabase is the desired BI claim, but it is treated as **disposable**: Metabase Cloud
bills after its trial. So capture the **durable artifacts first** (PNG screenshots +
the exported dashboard definition), then it is safe to tear down. The permanent, free,
always-live dashboard is **Looker Studio on BigQuery** (see `looker_studio_setup.md`).

> COST GUARDRAIL: do not enter payment details. Capture exports before the trial ends, then
> tear down. Record the teardown deadline (see the README teardown reminder).

## Stand it up (pick one — all free to build)

**A. Local Docker (free, no billing, recommended if Docker is available).**
`docker compose up -d` (see `docker-compose.yml`) starts Postgres + Metabase on
<http://localhost:3000>. Load the marts into the Postgres (`platform` db) — e.g. export the
marts with `python src/export_marts.py` and copy the CSVs in, or point dbt at the Postgres.

**B. Local Metabase jar (free, no Docker).** Needs Java 21
(`brew install openjdk@21`). Download `metabase.jar` from <https://www.metabase.com/start/oss/>,
run `java -jar metabase.jar`, open <http://localhost:3000>. Connect via the community DuckDB
driver (drop the driver jar in `plugins/`) to read `platform.duckdb` directly, or upload the
CSVs from `src/export_marts.py`.

**C. Metabase Cloud trial (billable after the trial).** Sign up, then use the CSV-upload
path below (Cloud cannot reach a local file). Capture artifacts before the trial ends.

## Get the data in (Cloud / CSV path)
`python src/export_marts.py` writes `dashboards/exports/`: `client_360.csv`
(= `user_risk_profile`: features + segment + tags + risk flags), `user_tags.csv`,
`user_segments.csv`.
1. Metabase → ⚙ Admin → Settings → **Uploads** → enable.
2. **+ New → CSV upload** → upload `client_360.csv`, `user_tags.csv`, `user_segments.csv`.

## Dashboard — ready-to-paste SQL (Native questions)
Table names match the uploaded files (`client_360`, `user_tags`); confirm exact names in the
data browser and adjust if Metabase prefixed them.

**1. Segment overview** (table)
```sql
SELECT segment, count(*) AS clients, round(avg(monetary),2) AS avg_spend,
       round(avg(frequency),1) AS avg_txns, round(avg(fraud_rate),4) AS fraud_rate
FROM client_360 GROUP BY segment ORDER BY fraud_rate DESC;
```
**2. Value / lifecycle / risk tag mix** (bar, stacked by family)
```sql
SELECT tag_family, tag, count(*) AS clients FROM user_tags
GROUP BY 1,2 ORDER BY 1,3 DESC;
```
**3. Tag effectiveness — do risk tags concentrate fraud?** (bar vs base rate)
```sql
SELECT t.tag, count(*) AS clients, round(avg(c.fraud_rate),4) AS avg_fraud_rate
FROM user_tags t JOIN client_360 c USING(client_id)
WHERE t.tag_family='risk' GROUP BY t.tag ORDER BY avg_fraud_rate DESC;
-- base rate to compare against: SELECT round(avg(fraud_rate),4) FROM client_360;  (~0.0316)
```
**4. Fraud rate by segment** (bar)
```sql
SELECT segment, round(avg(fraud_rate),4) AS avg_fraud_rate
FROM client_360 GROUP BY segment ORDER BY avg_fraud_rate DESC;
```
**5. Risk flags** (scorecards)
```sql
SELECT sum(is_confirmed_fraud) AS confirmed_fraud, sum(is_multi_identity) AS multi_identity,
       sum(is_high_velocity) AS high_velocity, count(*) AS clients FROM client_360;
```
Add all five to one dashboard.

## Capture durable artifacts BEFORE teardown (these ARE the portfolio evidence)
1. **Screenshots** of each card + the full board → `docs/charts/` and `dashboards/exports/`.
2. **Export the dashboard definition** so it survives teardown:
   - OSS serialization: `java -jar metabase.jar export dashboards/exports/metabase` (or the
     Admin → Settings serialization), commit the YAML.
   - Or via the API: `GET /api/dashboard/:id` → save the JSON to
     `dashboards/exports/metabase_dashboard.json` and commit it.
3. Only then tear down (`docker compose down -v`, or stop the jar / cancel the Cloud trial).

> The matplotlib PNGs in `docs/charts/` (from `src/make_charts.py`) already mirror these
> tiles and are committed, so the visual evidence exists regardless of any live instance.

## Agent-built option
Metabase's REST API can create these questions + the dashboard. With a running instance and
an API key (Admin → Settings → Authentication → API keys), an agent can build it, screenshot
it (browser MCP), and export the JSON in one pass.
