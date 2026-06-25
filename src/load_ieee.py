"""
Load IEEE-CIS Fraud Detection into DuckDB `raw.transactions`.

Expects the competition files in data/raw/ :
    train_transaction.csv   (label + transaction features)
    train_identity.csv      (device / browser features; optional, left-joined)
"""
import os
import pandas as pd
from db import get_con, write_table

RAW = "data/raw"

# Curated columns (the full set has 400+ V-columns; we keep a defensible analyst subset).
TXN_COLS = ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
            "card1", "card4", "card6", "addr1", "P_emaildomain", "R_emaildomain",
            "C1", "C2", "C5", "C13", "C14", "D1", "D4", "D10", "D15"]
ID_COLS = ["TransactionID", "DeviceType", "DeviceInfo", "id_30", "id_31", "id_33"]


def main():
    txn = pd.read_csv(f"{RAW}/train_transaction.csv", usecols=TXN_COLS)
    id_path = f"{RAW}/train_identity.csv"
    if os.path.exists(id_path):
        idn = pd.read_csv(id_path, usecols=ID_COLS)
        df = txn.merge(idn, on="TransactionID", how="left")
    else:
        print("note: train_identity.csv not found — loading without device/identity features")
        df = txn

    df.columns = [c.lower() for c in df.columns]   # dbt models expect lowercase

    con = get_con()
    write_table(con, df, "raw", "transactions")
    n, fraud = len(df), int(df["isfraud"].sum())
    con.close()
    print(f"raw.transactions: {n:,} rows x {df.shape[1]} cols")
    print(f"fraud rate: {fraud / n:.4f}  ({fraud:,} fraud)")


if __name__ == "__main__":
    main()
