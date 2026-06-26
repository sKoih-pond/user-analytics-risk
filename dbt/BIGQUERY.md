# Running this dbt project on BigQuery (free sandbox)

The same dbt project runs on two warehouses: DuckDB (default, local) and BigQuery. The
models are written to be adapter-portable (dbt cross-database macros + NTILE thresholds),
so nothing in `models/` changes between the two.

BigQuery here uses the **free sandbox**: no billing account, no card, ~10 GB storage and
1 TB query per month. We load only the columns the staging models need (all 590k rows, a
few tens of MB), so it stays comfortably inside the quota. **Never enable billing.** If a
step ever asks for a billing account, stop.

## One-time setup (Sylvester — needs your Google login)

1. **Create the sandbox.** Go to <https://console.cloud.google.com/bigquery>, sign in with
   a Google account, and accept the BigQuery sandbox. Note the **project id** it creates
   (something like `myproject-12345`). Do not attach billing.

2. **Authenticate the local tools** (one command, opens a browser):
   ```bash
   gcloud auth application-default login
   ```
   If you do not have `gcloud`: install the Google Cloud SDK
   (<https://cloud.google.com/sdk/docs/install>), or `brew install --cask google-cloud-sdk`.

3. **Install the BigQuery Python deps** (into the project venv):
   ```bash
   source .venv/bin/activate
   pip install -r requirements-bigquery.txt
   ```

## Run it

```bash
export BQ_PROJECT=<your-sandbox-project-id>     # e.g. myproject-12345
export BQ_LOCATION=US                            # optional, default US

# 1. Load the raw subset into a BigQuery `raw` dataset (reads from local DuckDB)
python src/load_bigquery.py

# 2. Build staging -> marts on BigQuery and run the tests
cd dbt && DBT_PROFILES_DIR=. dbt build --target bigquery

# 3. Docs (optional)
DBT_PROFILES_DIR=. dbt docs generate --target bigquery
```

A clean `dbt build --target bigquery` is the evidence the project runs on BigQuery. The
marts then back the Looker Studio dashboard (free, permanent) — see
`dashboards/looker_studio_setup.md`.

## Notes
- dbt writes to datasets `dbt_staging`, `dbt_intermediate`, `dbt_marts` (base dataset `dbt`
  + custom schema). Sandbox datasets/tables get a default 60-day expiry, which is fine.
- The Python ML model (`model_explainable.py`) stays on DuckDB; BigQuery only needs the
  dbt marts for the dashboard.
