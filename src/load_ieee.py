"""
Load IEEE-CIS Fraud Detection into DuckDB `raw.transactions` — FULL column set.

Loads every column (so the explainable model can pick interpretable features and the
black-box comparison can use the opaque V-columns). DuckDB reads the CSVs natively
(memory-efficient; no full pandas load). train_transaction left-joined to train_identity.
"""
from db import get_con

RAW = "data/raw"


def main():
    con = get_con()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.transactions AS
        SELECT t.*, i.* EXCLUDE (TransactionID)
        FROM read_csv_auto('{RAW}/train_transaction.csv', sample_size=-1) t
        LEFT JOIN read_csv_auto('{RAW}/train_identity.csv', sample_size=-1) i
          USING (TransactionID)
    """)
    n, cols = con.execute("select count(*), count(*) from raw.transactions").fetchone()[0], \
        len(con.execute("describe raw.transactions").df())
    fraud = con.execute("select avg(isFraud) from raw.transactions").fetchone()[0]
    con.close()
    print(f"raw.transactions: {n:,} rows x {cols} columns")
    print(f"fraud rate: {fraud:.4f}")


if __name__ == "__main__":
    main()
