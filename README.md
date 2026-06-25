# User Analytics & Risk Platform

End-to-end analytics project on a real payments/e-commerce transaction base (**IEEE-CIS Fraud**): **profile users, segment them, tag them, and detect fraud/abuse.** Built to mirror a Data-Analyst (Risk) brief and to demonstrate the modern analyst stack (SQL + **dbt** + Python + **Metabase**).

Stack: **DuckDB** (file-based warehouse, no server) · **dbt** (transformations) · **Python** (pandas, scikit-learn) · **Metabase** (BI — optional, needs Docker/Java).

## Why this project
Maps almost line-by-line to the kind of work it showcases — user tagging systems, user profiling, customer segmentation, anomaly/fraud detection, behavioural analysis on large-scale data, in a fintech/internet-platform domain. See [`docs/jd_mapping.md`](docs/jd_mapping.md).

> Honesty: this is a **capability demonstration** (a built artifact), not claimed work experience. dbt/Metabase/Postgres go on the CV only once this is genuinely built and running.

## Phases
- **Phase 1 — core (also closes the dbt + Metabase skill gap):**
  transactions → dbt models (`staging` → user-level `marts`) → **RFM + KMeans segmentation** → **user-tagging system** (value / lifecycle / risk tags) → **anomaly/fraud model** (Isolation Forest, then a supervised classifier) → **Metabase** dashboard.
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
python src/anomaly.py                      # supervised fraud model (PR-AUC) -> txn_risk + user_risk

# 6. (Optional) BI: Metabase via Docker/Java connected to platform.duckdb (community DuckDB driver),
#    or Looker Studio on a CSV export. Spec in dashboards/metabase_setup.md. Charts also fine in notebooks/.
```

## Structure
```
src/         load_ieee.py, segmentation.py, tagging.py, anomaly.py, abuse_rings.py(P2), db.py
dbt/         dbt_project.yml, profiles.yml, models/{staging/stg_transactions, marts/user_features}, schema.yml
data/        raw/ (gitignored — IEEE-CIS CSVs) + README (dataset + download)
notebooks/   exploratory Jupyter work
dashboards/  metabase_setup.md (connection + dashboard spec)
docs/        jd_mapping.md, learning_path.md
```

## Data
**IEEE-CIS Fraud Detection** (Kaggle competition) — real `isFraud` labels + card/device/email identity features. Canonical grain: `raw.transactions`; aggregated to a `client_id` (card1 + addr1 proxy — IEEE-CIS has no explicit user id). See `data/README.md`.

## Results
Phase 1 **run on real IEEE-CIS data** (2026-06-25): 590,540 txns → dbt marts (tested) → segmentation + tagging + a supervised fraud model (**PR-AUC 0.617**, numeric + categoricals). See **[`docs/results.md`](docs/results.md)** + charts in `docs/charts/`. A Metabase dashboard was built via API as a demo; the **durable** artifacts are this repo + the PNG charts (Metabase trial is ephemeral — nothing should link to it).

## Status
Phase 1 done. Next: strengthen the fraud model (V-cols/categoricals/threshold), Phase 2 abuse rings, write-up screenshots. Tracks to Employment Task #7 and the Binance application.
