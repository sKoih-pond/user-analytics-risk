"""
BLACK-BOX comparison — the explainable model PLUS the 339 anonymised V-columns.

Fair test: same features, same time-split as model_explainable.py, then ADD every V-column.
The PR-AUC gap is exactly what the un-explainable features buy on top of a strong,
fully-explainable model. The point is to MEASURE the trade-off, not to ship this.
"""
import re
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score
from db import get_con
from model_explainable import prepare, build_X, NUMERIC, CATEGORICAL


def main():
    con = get_con()
    df, _ = prepare(con)
    V = con.execute("SELECT transactionid tid, COLUMNS('^V[0-9]+$') FROM raw.transactions_identity").df()
    V.columns = ["tid"] + [c.lower() for c in V.columns[1:]]
    df = df.merge(V, on="tid", how="left")
    con.close()

    vcols = [c for c in df.columns if re.fullmatch(r"v\d+", c)]
    train = df.transactiondt <= df.transactiondt.quantile(0.70)
    X = build_X(df, NUMERIC + vcols, CATEGORICAL)
    y = df["y"].astype(int)
    Xtr, Xte, ytr, yte = X[train], X[~train], y[train], y[~train]
    print(f"black-box features: {X.shape[1]} (explainable + {len(vcols)} anonymised V-columns)")

    clf = HistGradientBoostingClassifier(categorical_features="from_dtype",
                                         max_iter=500, learning_rate=0.05, random_state=42).fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    print(f"\nPR-AUC  (black-box): {average_precision_score(yte, p):.4f}")
    print(f"ROC-AUC (black-box): {roc_auc_score(yte, p):.4f}")
    print("\noperating points:")
    print(f"  {'flag %':>7} {'precision':>9} {'recall':>7}")
    for q in [0.005, 0.01, 0.02, 0.05]:
        pred = (p >= np.quantile(p, 1 - q)).astype(int)
        print(f"  {q*100:6.1f}% {precision_score(yte,pred,zero_division=0):9.3f} {recall_score(yte,pred):7.3f}")


if __name__ == "__main__":
    main()
