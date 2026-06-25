"""
BLACK-BOX comparison model — the deliberate counterpoint to model_explainable.py.

Uses every numeric column INCLUDING the 339 anonymised V-features (Vesta's secret
engineered signals). Same TIME-BASED split, same metric. The point is NOT to ship this
— it's to MEASURE the performance you give up by refusing features you can't explain.
You can't tell an interviewer why "V257" flagged an account; you can for the explainable
model. This script quantifies that trade-off honestly.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_score, recall_score
from db import get_con


def main():
    con = get_con()
    # all numeric V / C / D columns + amount, ordered by time
    df = con.execute("""
        SELECT isFraud AS y, transactiondt AS dt, transactionamt AS amount,
               COLUMNS('^[VCD][0-9]+$')
        FROM raw.transactions
    """).df()
    con.close()
    df = df.sort_values("dt").reset_index(drop=True)
    feats = [c for c in df.columns if c not in ("y", "dt")]
    X = df[feats].astype("float32")
    y = df["y"].astype(int).values
    print(f"black-box features: {len(feats)} (incl. {sum(c.upper().startswith('V') for c in feats)} anonymised V-columns)")

    cut = int(len(df) * 0.70)
    Xtr, Xte, ytr, yte = X.iloc[:cut], X.iloc[cut:], y[:cut], y[cut:]
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, random_state=42).fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    print(f"\nPR-AUC (black-box): {average_precision_score(yte, p):.4f}")
    print("\noperating points:")
    print(f"  {'flag %':>7} {'precision':>9} {'recall':>7}")
    for q in [0.005, 0.01, 0.02, 0.05]:
        pred = (p >= np.quantile(p, 1 - q)).astype(int)
        print(f"  {q*100:6.1f}% {precision_score(yte,pred,zero_division=0):9.3f} {recall_score(yte,pred):7.3f}")


if __name__ == "__main__":
    main()
