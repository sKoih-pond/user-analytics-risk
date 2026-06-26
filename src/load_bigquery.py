"""
Load the IEEE-CIS raw tables into a BigQuery FREE SANDBOX dataset so the dbt project can
run against BigQuery (staging -> marts), exactly as it does on DuckDB.

We load only the columns the dbt staging models use (a few dozen), all 590k rows. That is
a few tens of MB, far inside the sandbox's ~10 GB storage / 1 TB query monthly quota. The
heavy anonymised V-columns and the Python ML model stay on DuckDB; BigQuery is purely the
warehouse for dbt + the Looker Studio dashboard.

Prerequisites (one-time, Sylvester's to do — see dbt/BIGQUERY.md):
  1. Create the free BigQuery sandbox (no billing account, no card).
  2. gcloud auth application-default login
  3. export BQ_PROJECT=<your-sandbox-project-id>   (optional: BQ_LOCATION, default US)
Then:  python src/load_bigquery.py    &&    cd dbt && dbt build --target bigquery
"""
import os
import sys
from db import get_con

TXN_COLS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card4", "card6", "addr1", "P_emaildomain", "R_emaildomain",
    "C1", "C2", "C5", "C13", "C14", "D1", "D4", "D10", "D15",
]
ID_COLS = ["TransactionID", "DeviceType", "DeviceInfo", "id_31", "id_01", "id_02"]


def fetch(con, table, cols):
    select = ", ".join(f'"{c}" as {c.lower()}' for c in cols)
    return con.execute(f"select {select} from raw.{table}").df()


def main():
    project = os.environ.get("BQ_PROJECT")
    if not project:
        sys.exit("Set BQ_PROJECT to your BigQuery sandbox project id first (see dbt/BIGQUERY.md).")
    location = os.environ.get("BQ_LOCATION", "US")

    try:
        from google.cloud import bigquery
    except ImportError:
        sys.exit("pip install -r requirements-bigquery.txt  (google-cloud-bigquery + dbt-bigquery)")

    con = get_con()
    txn = fetch(con, "transactions", TXN_COLS)
    ident = fetch(con, "identity", ID_COLS)
    con.close()
    print(f"read from DuckDB: transactions {txn.shape}, identity {ident.shape}")

    client = bigquery.Client(project=project, location=location)
    ds_id = f"{project}.raw"
    ds = bigquery.Dataset(ds_id)
    ds.location = location
    client.create_dataset(ds, exists_ok=True)
    print(f"dataset ready: {ds_id} ({location})")

    cfg = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    for name, df in [("transactions", txn), ("identity", ident)]:
        tbl = f"{ds_id}.{name}"
        client.load_table_from_dataframe(df, tbl, job_config=cfg).result()
        n = client.get_table(tbl).num_rows
        print(f"loaded {tbl}: {n:,} rows")
    print("\nraw loaded to BigQuery. Now: cd dbt && DBT_PROFILES_DIR=. "
          "BQ_PROJECT=%s dbt build --target bigquery" % project)


if __name__ == "__main__":
    main()
