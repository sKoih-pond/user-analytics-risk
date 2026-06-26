# Looker Studio dashboard (free, permanent) on BigQuery

Looker Studio is free and connects straight to BigQuery, so this is the **permanent, live,
shareable** version of the risk dashboard. It pairs with the BigQuery warehouse and needs
no billing. Build it once the dbt marts exist on BigQuery (`dbt build --target bigquery`).

## Connect
1. Go to <https://lookerstudio.google.com> → **Create → Report**.
2. **Add data → BigQuery** → your sandbox project → dataset **`dbt_marts`** → table
   **`user_risk_profile`**. Add it. Repeat to also add **`user_segments`** and
   **`user_tags`** as data sources in the same report.
3. (Optional) For the tag-effectiveness and segment charts you can add a **Custom Query**
   data source instead, pasting the SQL below — it does the aggregation server-side.

## Charts (mirror the Metabase board and the PNGs in docs/charts/)

**1. Segment overview** — table on `user_risk_profile`
- Dimension: `segment`. Metrics: Record Count, AVG `monetary`, AVG `frequency`, AVG `fraud_rate`.

**2. Value / lifecycle / risk tag mix** — stacked bar on `user_tags`
- Dimension: `tag`. Breakdown dimension: `tag_family`. Metric: Record Count.

**3. Tag effectiveness (fraud rate by risk tag vs base rate)** — bar; Custom Query source:
```sql
SELECT t.tag, COUNT(*) AS clients, ROUND(AVG(c.fraud_rate), 4) AS avg_fraud_rate
FROM `PROJECT.dbt_marts.user_tags` t
JOIN `PROJECT.dbt_marts.user_features` c USING (client_id)
WHERE t.tag_family = 'risk'
GROUP BY t.tag ORDER BY avg_fraud_rate DESC;
-- base rate to annotate against:
-- SELECT ROUND(AVG(fraud_rate), 4) FROM `PROJECT.dbt_marts.user_features`;
```
- Bar of `avg_fraud_rate` by `tag`. Add a reference line at the base rate (~0.0316).

**4. Fraud rate by segment** — bar on `user_risk_profile`
- Dimension: `segment`. Metric: AVG `fraud_rate`. Sort descending.

**5. Risk flags scorecard** — scorecards on `user_risk_profile`
- SUM `is_confirmed_fraud`, SUM `is_multi_identity`, SUM `is_high_velocity`, Record Count.

## Share + record the link
- **Share → Manage access**. Keep it private unless Sylvester approves making it public
  (a public link counts as publishing — get his explicit OK first).
- Paste the report URL into `docs/results.md`, the README, and the dbt exposure
  (`models/exposures.yml`, `url:`).

> The PNGs in `docs/charts/` are the durable evidence and exist regardless of any live link.
