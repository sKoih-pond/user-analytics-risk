"""
EXPLAINABLE fraud model (the centrepiece).

Deliberate, defensible decisions (this is the interview script):
  * Features you can explain the fraud logic for — amount, association COUNTS (C*),
    days-since-prior-activity (D*), name/address MATCH flags (M*), card type/network,
    product code, email domain, device type, PLUS an engineered "how many accounts
    share this device / email" signal (a fraud-ring tell). NO anonymised V-columns.
  * TIME-BASED validation: train on earlier transactions, test on later ones — no
    peeking at the future (a random split inflates results and hides production drift).
  * Operational THRESHOLD: report precision/recall at several alert volumes, not just 0.5,
    so the alarm line can be set on the cost of a missed fraud vs a false accusation.
  * Explainability: permutation importance (what drives the score) + worked examples.

Writes dbt_marts.txn_risk / dbt_marts.user_risk (scored with this, the production model).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, precision_score, recall_score
from db import get_con, write_table

NUMERIC = ["amount", "c1", "c2", "c5", "c13", "c14", "d1", "d4", "d10", "d15",
           "device_share", "email_share"]
CATEGORICAL = ["card_network", "card_type", "product_cd", "p_emaildomain", "devicetype",
               "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9"]


def load(con):
    df = con.execute("""
        SELECT transactionid AS tid, isFraud AS y, transactiondt AS dt,
               transactionamt AS amount, card1, addr1,
               card4 AS card_network, card6 AS card_type, productcd AS product_cd,
               p_emaildomain, devicetype, deviceinfo,
               c1,c2,c5,c13,c14, d1,d4,d10,d15, m1,m2,m3,m4,m5,m6,m7,m8,m9
        FROM raw.transactions
    """).df()
    df.columns = df.columns.str.lower()   # DuckDB keeps original case for unaliased cols
    df["client_id"] = df.card1.astype("Int64").astype(str) + "-" + df.addr1.astype("Int64").astype(str)
    # engineered fraud-ring signals: distinct accounts sharing a device / email domain
    df["device_share"] = df.groupby("deviceinfo")["client_id"].transform("nunique").where(df.deviceinfo.notna(), 1)
    df["email_share"] = df.groupby("p_emaildomain")["client_id"].transform("nunique").where(df.p_emaildomain.notna(), 1)
    return df


def make_X(df):
    X = df[NUMERIC + CATEGORICAL].copy()
    for c in NUMERIC:
        X[c] = X[c].astype(float)
    for c in CATEGORICAL:
        X[c] = X[c].astype("string").fillna("missing").astype("category")
    return X


def main():
    con = get_con()
    df = load(con).sort_values("dt").reset_index(drop=True)   # TIME ORDER
    X, y = make_X(df), df["y"].astype(int).values

    cut = int(len(df) * 0.70)                                  # earlier 70% train, later 30% test
    Xtr, Xte, ytr, yte = X.iloc[:cut], X.iloc[cut:], y[:cut], y[cut:]
    print(f"time-split: train {len(Xtr):,} (fraud {ytr.mean():.3%})  |  test {len(Xte):,} (fraud {yte.mean():.3%})")

    clf = HistGradientBoostingClassifier(categorical_features="from_dtype",
                                         max_iter=300, learning_rate=0.08, random_state=42).fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    print(f"\nPR-AUC (explainable): {average_precision_score(yte, p):.4f}")

    print("\noperating points (set the alarm line on cost):")
    print(f"  {'flag %':>7} {'threshold':>9} {'precision':>9} {'recall':>7}")
    for q in [0.005, 0.01, 0.02, 0.05]:
        thr = np.quantile(p, 1 - q)
        pred = (p >= thr).astype(int)
        print(f"  {q*100:6.1f}% {thr:9.3f} {precision_score(yte,pred,zero_division=0):9.3f} {recall_score(yte,pred):7.3f}")

    print("\ntop features (permutation importance on 20k test sample):")
    samp = Xte.sample(min(20000, len(Xte)), random_state=42)
    imp = permutation_importance(clf, samp, yte[samp.index - cut], n_repeats=3,
                                 random_state=42, scoring="average_precision")
    for i in np.argsort(imp.importances_mean)[::-1][:10]:
        print(f"  {X.columns[i]:<16} {imp.importances_mean[i]:.4f}")

    # score everyone -> marts (this is the production model)
    df["fraud_proba"] = clf.predict_proba(X)[:, 1]
    write_table(con, df[["tid", "client_id", "y", "fraud_proba"]].rename(columns={"tid": "transaction_id", "y": "is_fraud"}),
                "dbt_marts", "txn_risk")
    ur = (df.groupby("client_id").agg(n_txn=("tid", "count"), max_proba=("fraud_proba", "max"),
                                      mean_proba=("fraud_proba", "mean"),
                                      any_flagged=("fraud_proba", lambda s: int((s >= 0.5).any()))).reset_index())
    write_table(con, ur, "dbt_marts", "user_risk")
    con.close()
    print("\nwrote dbt_marts.txn_risk / user_risk")


if __name__ == "__main__":
    main()
