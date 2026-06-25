# Learning path (build-by-doing)

Order to work through the scaffold; each step is a real, CV-able skill.

1. **Stack up** — `pip install -r requirements.txt`; `docker compose up -d` (Postgres + Metabase).
2. **Data** — accept the IEEE-CIS rules, download + `python src/load_ieee.py` (see `data/README.md`). Inspect `raw.transactions`; understand the card1+addr1 client proxy and the fraud label.
3. **dbt fundamentals** — free *dbt Fundamentals* course (~half a day). Then `DBT_PROFILES_DIR=. dbt build` and read `dbt docs generate && dbt docs serve`. Understand sources → staging → marts + tests.
4. **Segmentation** — `python src/segmentation.py`; tune `K` (elbow/silhouette), name clusters from centroids.
5. **Tagging** — `python src/tagging.py`; justify each threshold; review risk-tag precision vs `is_abuser`.
6. **Risk model** — `python src/anomaly.py`; read the PR-AUC + precision/recall; pick a threshold from the trade-off (capstone discipline).
7. **Metabase** — build the dashboard (`dashboards/metabase_setup.md`); screenshot it.
8. **Phase 2** — `src/abuse_rings.py` (community detection + ring scoring); cohort/retention + a mock A/B test.
9. **(Optional) BigQuery** — re-point dbt at a BigQuery sandbox; load GA4 sample → claim BigQuery honestly.
10. **Write up** — short README results section + dashboard screenshot; then add the honest CV lines (dbt, Metabase, [BigQuery]) to the Data domain CV.

Keep it honest: only add a tool to the CV once you've genuinely used it here.
