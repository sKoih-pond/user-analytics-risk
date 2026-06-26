# Learning path (build-by-doing)

Order to work through the project; each step is a real, CV-able skill.

1. **Stack up** — `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
2. **Data** — accept the IEEE-CIS rules, download + `python src/load_ieee.py` (see `data/README.md`). Inspect `raw.transactions` / `raw.identity`; understand the card1+addr1 client proxy and the fraud label.
3. **dbt** — free *dbt Fundamentals* course (~half a day). Then `cd dbt && DBT_PROFILES_DIR=. dbt build` and `dbt docs generate && dbt docs serve`. Read the lineage: sources → staging → intermediate → marts, plus the tests and the exposure.
4. **Segmentation** — RFM is dbt-owned (`user_segments`); the KMeans alternative is `python src/segmentation.py` (tune `K`, name clusters from centroids).
5. **Tagging** — dbt-owned (`user_tags`); justify each threshold; review risk-tag precision vs the base fraud rate. `src/tagging.py` is the readable reference.
6. **Risk model** — `python src/model_explainable.py` then `src/model_blackbox.py`; read the PR-AUC + precision/recall; pick a threshold from the trade-off (capstone discipline).
7. **Charts** — `python src/make_charts.py` regenerates the PNG dashboard tiles in `docs/charts/`.
8. **BigQuery (free sandbox)** — one-time auth in `dbt/BIGQUERY.md`, then `python src/load_bigquery.py` and `dbt build --target bigquery`. Same project, cloud warehouse, zero cost.
9. **BI dashboards** — Looker Studio on BigQuery (free, permanent): `dashboards/looker_studio_setup.md`. Metabase (Docker / local jar / Cloud trial): `dashboards/metabase_setup.md` — capture screenshots + the exported definition before any teardown.
10. **Phase 2** — `src/abuse_rings.py` (community detection + ring scoring); cohort/retention + a mock A/B test.
11. **Write up** — README results + a dashboard screenshot; then add the honest CV lines (dbt, BigQuery, Metabase, Looker Studio) to the Data domain CV.

Keep it honest: only add a tool to the CV once you've genuinely used it here.
