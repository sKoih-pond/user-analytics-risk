# Metabase dashboard

Warehouse is **local DuckDB** (`platform.duckdb`). **Metabase Cloud cannot reach a local file**, so use one of these to get the data in:

## Path A — Upload the CSVs (simplest)
Exports are in `dashboards/exports/`: `client_360.csv` (features + segment + risk), `user_tags.csv`.
1. Metabase → gear ⚙ → **Admin settings → Settings → Uploads** → enable uploads (pick the upload database Metabase offers/your attached DB).
2. Home → **+ New → CSV upload** (or the Uploads page) → upload `client_360.csv` then `user_tags.csv`. Each becomes a table.
3. Build the dashboard (below).

## Path B — Hosted Postgres (live connection, most robust)
1. Create a free Postgres (e.g. neon.tech — instant, gives a connection string).
2. Load the marts into it (an agent can do this from the local DuckDB given the connection string).
3. Metabase → **Add database → PostgreSQL** → paste host/db/user/password → live dashboards on `client_360` + `user_tags`.

## Dashboard — ready-to-paste SQL (Native questions)
Make each one a **+ New → SQL query** on the uploads database, then pick the viz. Table names match the uploaded files (`client_360`, `user_tags`) — confirm exact names in Metabase's data browser and adjust if it prefixed them.

**1. Segments overview** (bar / table)
```sql
SELECT segment, count(*) AS clients, round(avg(monetary),2) AS avg_spend,
       round(avg(frequency),1) AS avg_txns, round(avg(fraud_rate),4) AS fraud_rate
FROM client_360 GROUP BY segment ORDER BY segment;
```
**2. Risk-tag distribution** (bar)
```sql
SELECT tag, count(*) AS clients FROM user_tags
WHERE tag_family='risk' GROUP BY tag ORDER BY clients DESC;
```
**3. Value & lifecycle mix** (bar, stacked by family)
```sql
SELECT tag_family, tag, count(*) AS clients FROM user_tags
WHERE tag_family IN ('value','lifecycle') GROUP BY 1,2 ORDER BY 1,3 DESC;
```
**4. Tag effectiveness — do risk tags concentrate fraud?** (bar; compare to base rate)
```sql
SELECT t.tag, count(*) AS clients, round(avg(c.fraud_rate),4) AS avg_fraud_rate
FROM user_tags t JOIN client_360 c USING(client_id)
WHERE t.tag_family='risk' GROUP BY t.tag ORDER BY avg_fraud_rate DESC;
-- overall base rate for comparison:
-- SELECT round(avg(fraud_rate),4) FROM client_360;
```
**5. Model risk — flagged clients + top risks** (number + table)
```sql
SELECT any_flagged, count(*) AS clients FROM client_360 GROUP BY any_flagged;
-- top-risk clients:
-- SELECT client_id, round(max_proba,3) max_proba, fraud_rate, n_txn, monetary
-- FROM client_360 ORDER BY max_proba DESC LIMIT 50;
```
Add all five to one dashboard → screenshot into `docs/` for the portfolio writeup.

## If you want the agent to build it for you
Metabase Cloud is internet-reachable, so with a **Metabase API key** (Admin → Settings → Authentication → API keys) the agent can create these questions + the dashboard via the REST API. Optional — the SQL above is enough to do it by hand.
