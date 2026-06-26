# User Analytics & Risk Platform

End-to-end analytics project on a real payments/e-commerce transaction base (**IEEE-CIS Fraud**): **profile users, segment them, tag them, and detect fraud/abuse.** Built to mirror a Data-Analyst (Risk) brief and to demonstrate the modern analyst stack (SQL + **dbt** + Python + **Metabase**).

Stack: **DuckDB** (file-based warehouse, no server) · **dbt** (transformations) · **Python** (pandas, scikit-learn) · **Metabase** (BI — optional, needs Docker/Java).

## Why this project
Maps almost line-by-line to the kind of work it showcases — user tagging systems, user profiling, customer segmentation, anomaly/fraud detection, behavioural analysis on large-scale data, in a fintech/internet-platform domain. See [`docs/jd_mapping.md`](docs/jd_mapping.md).

> Honesty: this is a **capability demonstration** (a built artifact), not claimed work experience. dbt/Metabase/Postgres go on the CV only once this is genuinely built and running.

## Phases
- **Phase 1 — core (also closes the dbt + Metabase skill gap):**
  transactions → dbt models (`staging` → user-level `marts`) → **RFM + KMeans segmentation** → **user-tagging system** (value / lifecycle / risk tags) → **explainable fraud model** (time-validated) + a **black-box comparison** → **Metabase** dashboard. Design rationale: **[`docs/approach_and_decisions.md`](docs/approach_and_decisions.md)**.
- **Phase 2 — differentiators:**
  **bonus/promo-abuse ring detection** (multi-account / graph community detection) + **cohort, retention & a mock A/B test**. Optionally re-run on **BigQuery** to claim it honestly.

## Quickstart
```bash
# 1. Python env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. No server needed — DuckDB is a local file (platform.duckdb). Metabase is optional/later.

# 3. Get the data: accept IEEE-CIS rules on Kaggle first, then download + load
export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token)
python -c "import kagglehub,glob,shutil; p=kagglehub.competition_download('ieee-fraud-detection'); [shutil.copy(f,'data/raw/') for f in glob.glob(p+'/train_*.csv')]"
python src/load_ieee.py                    # train_transaction(+identity) -> raw.transactions

# 4. Transform with dbt
cd dbt && DBT_PROFILES_DIR=. dbt build && cd ..   # staging + marts, runs tests

# 5. Analytics (Python)
python src/segmentation.py                 # RFM + KMeans -> user_segments
python src/tagging.py                      # value/lifecycle/risk tags -> user_tags
python src/model_explainable.py     # explainable model (time-split) -> txn_risk + user_risk
python src/model_blackbox.py        # black-box comparison (quantifies the trade-off)

# 6. (Optional) BI: Metabase via Docker/Java connected to platform.duckdb (community DuckDB driver),
#    or Looker Studio on a CSV export. Spec in dashboards/metabase_setup.md. Charts also fine in notebooks/.
```

## Structure
```
src/         load_ieee.py, explore_features.py, eda_columns.py, segmentation.py, tagging.py, model_explainable.py, model_blackbox.py, abuse_rings.py(P2), make_charts.py, db.py
dbt/         dbt_project.yml, profiles.yml, models/{staging/stg_transactions, marts/user_features}, schema.yml
data/        raw/ (gitignored — IEEE-CIS CSVs) + README (dataset + download)
notebooks/   exploratory Jupyter work
dashboards/  metabase_setup.md (connection + dashboard spec)
docs/        eda.md, approach_and_decisions.md, results.md, jd_mapping.md, learning_path.md, charts/
```

## Data
**IEEE-CIS Fraud Detection** (Kaggle competition) — real `isFraud` labels + card/device/email identity features. Canonical grain: `raw.transactions`; aggregated to a `client_id` (card1 + addr1 proxy — IEEE-CIS has no explicit user id). See `data/README.md`.

## Results
Phase 1 **run on real IEEE-CIS data** (2026-06-25): 590,540 txns → dbt marts (tested) → segmentation + tagging + an **explainable, time-validated fraud model**. Headline: the explainable model (only *documented* features + engineered customer-id/baseline) scores **PR-AUC 0.540 / ROC-AUC 0.913**; adding all 339 anonymised columns adds **nothing** (black-box 0.538/0.911 — essentially identical, marginally below) — so explainability is not a compromise here, it is the better model. Within ~0.01 ROC-AUC of the domain expert's published 0.9245, using only documented features. Full reasoning in **[`docs/approach_and_decisions.md`](docs/approach_and_decisions.md)**; numbers + charts in **[`docs/results.md`](docs/results.md)**. A Metabase dashboard was built as a demo; the **durable** artifacts are this repo + the PNG charts (the Metabase trial is ephemeral — nothing links to it).

## Status
Phase 1 done. Next (non-blocking): Phase 2 ring detection, a productionised alert threshold, cohort/A-B analysis. Tracks to Employment Task #7 and the Binance application.
