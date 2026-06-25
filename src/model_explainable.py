"""
EXPLAINABLE fraud model (centrepiece).

The line we draw: use EVERY feature whose meaning is documented — transaction amount,
all association COUNTS (C1-C14), all time-deltas (D1-D15), match flags (M1-M9),
distances, card/email/device/identity signals, hour-of-day — PLUS engineered,
explainable entity features: a sharper customer id, cross-account device/email sharing,
and a leak-free per-customer behavioural baseline (their own normal vs this transaction).
We EXCLUDE only the 339 fully-anonymised V-columns (you can't explain "V257").

Validation is TIME-BASED (train earlier, test later). Reports PR-AUC and ROC-AUC.
Importable: model_blackbox.py reuses prepare() and adds the V-columns for the comparison.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score
from db import get_con, write_table

C = [f"c{i}" for i in range(1, 15)]
D = [f"d{i}" for i in range(1, 16)]
M = [f"m{i}" for i in range(1, 10)]
NUMERIC = (["amount", "hr", "dist1", "dist2", "addr1", "addr2", "id_01", "id_02", "id_05", "id_06",
            "device_share", "email_share",
            "uid_prior_count", "time_since_prior", "uid_prior_mean_amt",
            "amount_z_individual", "amount_z_profile"] + C + D)
CATEGORICAL = (["card_network", "card_type", "product_cd", "p_emaildomain", "r_emaildomain",
                "devicetype", "has_identity", "new_device"] + M)

SELECT = """
    SELECT transactionid tid, isFraud y, transactiondt, transactionamt amount,
           card1, card2, card3, card5, addr1, addr2, dist1, dist2,
           card4 card_network, card6 card_type, productcd product_cd,
           p_emaildomain, r_emaildomain, devicetype, deviceinfo,
           id_01, id_02, id_05, id_06,
           c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,c11,c12,c13,c14,
           d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15,
           m1,m2,m3,m4,m5,m6,m7,m8,m9
    FROM raw.transactions
"""


def engineer(df):
    df.columns = df.columns.str.lower()
    day = np.floor(df.transactiondt / 86400)
    df["hr"] = np.floor((df.transactiondt % 86400) / 3600)
    df["account_birthday"] = day - df.d1
    df["has_identity"] = df.devicetype.notna()

    def s(x): return x.astype("Int64").astype(str)
    df["uid"] = (s(df.card1)+"_"+s(df.card2)+"_"+s(df.card3)+"_"+s(df.card5)
                 + "_"+s(df.addr1)+"_"+s(df.account_birthday.astype("Int64")))
    df["device_share"] = df.groupby("deviceinfo")["uid"].transform("nunique").where(df.deviceinfo.notna(), 1)
    df["email_share"] = df.groupby("p_emaildomain")["uid"].transform("nunique").where(df.p_emaildomain.notna(), 1)

    df = df.sort_values(["uid", "transactiondt"]).reset_index(drop=True)
    g = df.groupby("uid", sort=False)
    df["uid_prior_count"] = g.cumcount()
    csum = g.amount.cumsum() - df.amount
    df["uid_prior_mean_amt"] = (csum / df.uid_prior_count).where(df.uid_prior_count > 0)
    csq = g["amount"].transform(lambda x: (x**2).cumsum()) - df.amount**2
    std = np.sqrt(((csq / df.uid_prior_count) - df.uid_prior_mean_amt**2).clip(lower=0))
    df["amount_z_individual"] = ((df.amount - df.uid_prior_mean_amt) / std).where((df.uid_prior_count >= 2) & (std > 0))
    df["time_since_prior"] = g.transactiondt.diff()
    df["new_device"] = df.deviceinfo.notna() & ~df.duplicated(["uid", "deviceinfo"], keep="first")
    return df


def prepare(con):
    df = engineer(con.execute(SELECT).df())
    cut = df.transactiondt.quantile(0.70)
    train = df.transactiondt <= cut
    prof = df[train].groupby("product_cd")["amount"].agg(["mean", "std"])
    df["amount_z_profile"] = (df.amount - df.product_cd.map(prof["mean"])) / df.product_cd.map(prof["std"])
    return df, train


def build_X(df, cols_numeric, cols_categorical):
    X = df[cols_numeric + cols_categorical].copy()
    for c in cols_numeric:
        X[c] = X[c].astype(float)
    for c in cols_categorical:
        X[c] = X[c].astype("string").fillna("missing").astype("category")
    return X


def main():
    con = get_con()
    df, train = prepare(con)
    X, y = build_X(df, NUMERIC, CATEGORICAL), df["y"].astype(int)
    Xtr, Xte, ytr, yte = X[train], X[~train], y[train], y[~train]
    print(f"time-split: train {train.sum():,} | test {(~train).sum():,} | uids {df.uid.nunique():,} | features {X.shape[1]}")

    clf = HistGradientBoostingClassifier(categorical_features="from_dtype",
                                         max_iter=500, learning_rate=0.05, random_state=42).fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    print(f"\nPR-AUC  (explainable): {average_precision_score(yte, p):.4f}")
    print(f"ROC-AUC (explainable): {roc_auc_score(yte, p):.4f}")
    print("\noperating points:")
    print(f"  {'flag %':>7} {'precision':>9} {'recall':>7}")
    for q in [0.005, 0.01, 0.02, 0.05]:
        pred = (p >= np.quantile(p, 1 - q)).astype(int)
        print(f"  {q*100:6.1f}% {precision_score(yte,pred,zero_division=0):9.3f} {recall_score(yte,pred):7.3f}")

    print("\ntop features (permutation importance, 20k test sample):")
    samp = Xte.sample(min(20000, len(Xte)), random_state=42)
    imp = permutation_importance(clf, samp, yte.loc[samp.index], n_repeats=3, random_state=42, scoring="average_precision")
    for i in np.argsort(imp.importances_mean)[::-1][:12]:
        print(f"  {X.columns[i]:<20} {imp.importances_mean[i]:.4f}")

    df["fraud_proba"] = clf.predict_proba(X)[:, 1]
    write_table(con, df[["tid", "uid", "y", "fraud_proba"]].rename(columns={"tid": "transaction_id", "uid": "client_id", "y": "is_fraud"}),
                "dbt_marts", "txn_risk")
    ur = (df.groupby("uid").agg(n_txn=("tid", "count"), max_proba=("fraud_proba", "max"),
                                mean_proba=("fraud_proba", "mean"),
                                any_flagged=("fraud_proba", lambda s: int((s >= 0.5).any()))).reset_index().rename(columns={"uid": "client_id"}))
    write_table(con, ur, "dbt_marts", "user_risk")
    con.close()
    print("\nwrote dbt_marts.txn_risk / user_risk")


if __name__ == "__main__":
    main()
