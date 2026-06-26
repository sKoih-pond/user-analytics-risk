"""
Load IEEE-CIS Fraud Detection into DuckDB — the two original Kaggle source tables.

The competition ships two files: train_transaction (the transaction grain) and
train_identity (device/identity attributes). We load each into its own raw table so the
dbt project has genuine per-source staging (stg_transactions, stg_identity), then expose a
joined view (raw.transactions_identity) for the Python feature pipeline, which needs the
full wide column set in one place (documented + anonymised V-columns). DuckDB reads the
CSVs natively (memory-efficient; no full pandas load).
"""
from db import get_con

RAW = "data/raw"


def main():
    con = get_con()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # Two source tables, one per Kaggle file (the dbt sources).
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.transactions AS
        SELECT * FROM read_csv_auto('{RAW}/train_transaction.csv', sample_size=-1)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.identity AS
        SELECT * FROM read_csv_auto('{RAW}/train_identity.csv', sample_size=-1)
    """)
    # Joined view for the Python pipeline (same shape the model has always seen).
    con.execute("""
        CREATE OR REPLACE VIEW raw.transactions_identity AS
        SELECT t.*, i.* EXCLUDE (TransactionID)
        FROM raw.transactions t
        LEFT JOIN raw.identity i USING (TransactionID)
    """)
    nt = con.execute("select count(*) from raw.transactions").fetchone()[0]
    ni = con.execute("select count(*) from raw.identity").fetchone()[0]
    ncols = len(con.execute("describe raw.transactions_identity").df())
    fraud = con.execute("select avg(isFraud) from raw.transactions").fetchone()[0]
    con.close()
    print(f"raw.transactions: {nt:,} rows | raw.identity: {ni:,} rows")
    print(f"raw.transactions_identity (view): {ncols} columns | fraud rate: {fraud:.4f}")


if __name__ == "__main__":
    main()
