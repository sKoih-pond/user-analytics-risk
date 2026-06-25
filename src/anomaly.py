"""
Risk / anti-fraud model on IEEE-CIS (real `isFraud` label).

Transaction-level supervised fraud classification — report PR-AUC + precision/recall
on the fraud class (fraud is rare; a missed fraud vs a false flag have different
costs — the operational framing from the IDS capstone). Then roll predictions up
to client risk.

Features: numeric (amount + C/D counts) + categoricals (card type/network, product
code, email domain, device type) via HistGBM's native categorical support.

Outputs:
  dbt_marts.txn_risk   (transaction_id, client_id, is_fraud, fraud_proba)
  dbt_marts.user_risk  (client_id, n_txn, max_proba, mean_proba, any_flagged)
"""
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, average_precision_score
from db import get_con, write_table

NUMERIC = ["amount", "c1", "c2", "c5", "c13", "c14", "d1", "d4", "d10", "d15"]
CATEGORICAL = ["card_network", "card_type", "product_cd", "p_emaildomain", "devicetype"]
FEATURES = NUMERIC + CATEGORICAL


def main():
    con = get_con()
    df = con.execute(
        "select transaction_id, client_id, is_fraud, "
        + ", ".join(FEATURES) + " from dbt_staging.stg_transactions"
    ).df()

    X = df[FEATURES].copy()
    for c in NUMERIC:
        X[c] = X[c].astype(float)
    for c in CATEGORICAL:
        X[c] = X[c].fillna("missing").astype("category")
    y = df["is_fraud"].astype(int)

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    clf = HistGradientBoostingClassifier(
        categorical_features="from_dtype", random_state=42, max_iter=200, learning_rate=0.1
    ).fit(Xtr, ytr)

    proba_te = clf.predict_proba(Xte)[:, 1]
    print(classification_report(yte, (proba_te >= 0.5).astype(int), digits=4))
    print("PR-AUC (fraud class):", round(average_precision_score(yte, proba_te), 4))

    df["fraud_proba"] = clf.predict_proba(X)[:, 1]
    write_table(con, df[["transaction_id", "client_id", "is_fraud", "fraud_proba"]],
                "dbt_marts", "txn_risk")

    user_risk = (df.groupby("client_id")
                   .agg(n_txn=("transaction_id", "count"),
                        max_proba=("fraud_proba", "max"),
                        mean_proba=("fraud_proba", "mean"),
                        any_flagged=("fraud_proba", lambda s: int((s >= 0.5).any())))
                   .reset_index())
    write_table(con, user_risk, "dbt_marts", "user_risk")
    con.close()
    print("wrote dbt_marts.txn_risk and dbt_marts.user_risk")


if __name__ == "__main__":
    main()
