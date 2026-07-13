"""
MLflow experiment tracking + model registry over the four fraud models + the cost-decision metric.

One command reproduces the whole tracked experiment: each model is trained on the SAME time-split as
the rest of the project, logged as a run (params, metrics, the model artifact, and the comparison/cost
charts) under the 'fraud-detection' experiment, and the explainable model is registered as the champion.

Local SQLite backend so tracking AND the model registry work with no server. Inspect with:
    mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
import os
import re
import subprocess
import warnings

import numpy as np
import torch
import mlflow
import mlflow.sklearn
import mlflow.pytorch
from mlflow.tracking import MlflowClient
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score

from db import get_con
from model_explainable import prepare, build_X, NUMERIC, CATEGORICAL
import model_deep as md
import decision_layer as dl

warnings.filterwarnings("ignore")
TRACKING = "sqlite:///mlflow.db"
EXPERIMENT = "fraud-detection"
CHAMPION = "fraud-explainable-hgb"
CHARTS = ["docs/charts/model_comparison.png", "docs/charts/cost_curve.png"]
HGB = dict(categorical_features="from_dtype", max_iter=500, learning_rate=0.05, random_state=42)


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def op_metrics(y, score, q=0.01):
    """PR-AUC, ROC-AUC + precision/recall at a business-relevant top-q% alert rate."""
    pred = (score >= np.quantile(score, 1 - q)).astype(int)
    return {"pr_auc": float(average_precision_score(y, score)),
            "roc_auc": float(roc_auc_score(y, score)),
            "precision_at_1pct": float(precision_score(y, pred, zero_division=0)),
            "recall_at_1pct": float(recall_score(y, pred))}


TAGS = {"dataset": "IEEE-CIS", "split": "time-based-70pct", "git_commit": git_sha()}


def log_charts():
    for c in CHARTS:
        if os.path.exists(c):
            mlflow.log_artifact(c, "charts")


def main():
    mlflow.set_tracking_uri(TRACKING)
    mlflow.set_experiment(EXPERIMENT)

    con = get_con()
    df, train = prepare(con)
    y = df["y"].astype(int)
    yte = y[~train].to_numpy()
    amt_te = df.loc[~train, "amount"].to_numpy()

    # ---- 1. explainable HGB (champion) ----
    X = build_X(df, NUMERIC, CATEGORICAL)
    with mlflow.start_run(run_name="explainable-hgb"):
        clf = HistGradientBoostingClassifier(**HGB).fit(X[train], y[train])
        p = clf.predict_proba(X[~train])[:, 1]
        mlflow.log_params({"model": "HistGradientBoosting", **HGB, "n_features": X.shape[1],
                           "n_train": int(train.sum()), "n_test": int((~train).sum())})
        mlflow.log_metrics(op_metrics(yte, p))
        # champion business value, from the cost-decision layer
        ts = np.linspace(0, 1, 501)
        cost_naive = dl.realised_cost(yte, amt_te, p >= 0.5, dl.C_REVIEW)
        cost_opt = min(dl.realised_cost(yte, amt_te, p >= t, dl.C_REVIEW) for t in ts)
        cost_ev = dl.realised_cost(yte, amt_te, (p * amt_te) > dl.C_REVIEW, dl.C_REVIEW)
        exposure = amt_te[yte == 1].sum()
        mlflow.log_metrics({"cost_naive": float(cost_naive), "cost_optimal": float(cost_opt),
                            "cost_ev": float(cost_ev),
                            "pct_saved_vs_naive": float((cost_naive - cost_ev) / cost_naive * 100),
                            "exposure_recovered_pct": float((exposure - cost_ev) / exposure * 100)})
        mlflow.set_tags(TAGS)
        log_charts()
        mlflow.sklearn.log_model(clf, "model", registered_model_name=CHAMPION)
        print(f"explainable-hgb   pr_auc {op_metrics(yte, p)['pr_auc']:.3f}  (champion)")

    # ---- 2. black-box HGB (+339 anonymised V-columns) ----
    V = con.execute("SELECT transactionid tid, COLUMNS('^V[0-9]+$') FROM raw.transactions_identity").df()
    V.columns = ["tid"] + [c.lower() for c in V.columns[1:]]
    dfb = df.merge(V, on="tid", how="left")
    con.close()
    vcols = [c for c in dfb.columns if re.fullmatch(r"v\d+", c)]
    trb = (dfb.transactiondt <= dfb.transactiondt.quantile(0.70)).to_numpy()
    Xb, yb = build_X(dfb, NUMERIC + vcols, CATEGORICAL), dfb["y"].astype(int).to_numpy()
    with mlflow.start_run(run_name="blackbox-hgb"):
        clf = HistGradientBoostingClassifier(**HGB).fit(Xb[trb], yb[trb])
        pb = clf.predict_proba(Xb[~trb])[:, 1]
        mlflow.log_params({"model": "HistGradientBoosting", **HGB, "n_features": Xb.shape[1],
                           "extra": f"+{len(vcols)} anonymised V-columns"})
        mlflow.log_metrics(op_metrics(yb[~trb], pb))
        mlflow.set_tags(TAGS)
        mlflow.sklearn.log_model(clf, "model")
        print(f"blackbox-hgb      pr_auc {op_metrics(yb[~trb], pb)['pr_auc']:.3f}")

    # ---- 3 & 4. deep models (reuse model_deep, same encoding + split) ----
    np.random.seed(md.SEED)
    torch.manual_seed(md.SEED)
    yv = y.to_numpy()
    Xn, Xc, cards = md.encode(df, train)
    idx = np.arange(len(df))
    tr_all, te_idx = idx[train.to_numpy()], idx[~train.to_numpy()]
    order = tr_all[np.argsort(df.transactiondt.to_numpy()[tr_all])]
    n_val = int(len(order) * md.VAL_FRAC)
    tr_idx, va_idx = order[:-n_val], order[-n_val:]
    pos_weight = (yv[tr_idx] == 0).sum() / max((yv[tr_idx] == 1).sum(), 1)

    with mlflow.start_run(run_name="deep-mlp"):
        m, xn, xc = md.train_mlp(Xn, Xc, yv, tr_idx, va_idx, pos_weight)
        with torch.no_grad():
            p_mlp = torch.sigmoid(m(xn[te_idx], xc[te_idx])).numpy()
        mlflow.log_params({"model": "MLP+embeddings (PyTorch)", "epochs": md.MLP_EPOCHS,
                           "batch": md.BATCH, "n_numeric": Xn.shape[1], "n_categorical": len(cards)})
        mlflow.log_metrics(op_metrics(yv[te_idx], p_mlp))
        mlflow.set_tags(TAGS)
        mlflow.pytorch.log_model(m, "model")
        print(f"deep-mlp          pr_auc {op_metrics(yv[te_idx], p_mlp)['pr_auc']:.3f}")

    with mlflow.start_run(run_name="autoencoder"):
        tr_legit = tr_all[yv[tr_all] == 0]
        ae, err = md.train_ae(Xn, tr_legit, te_idx)
        mlflow.log_params({"model": "Autoencoder (PyTorch)", "epochs": md.AE_EPOCHS,
                           "batch": md.BATCH, "n_numeric": Xn.shape[1], "trained_on": "legit-only"})
        mlflow.log_metrics(op_metrics(yv[te_idx], err))
        mlflow.set_tags(TAGS)
        mlflow.pytorch.log_model(ae, "model")
        print(f"autoencoder       pr_auc {op_metrics(yv[te_idx], err)['pr_auc']:.3f}")

    # ---- register champion + alias ----
    client = MlflowClient()
    latest = max(int(mv.version) for mv in client.search_model_versions(f"name='{CHAMPION}'"))
    client.set_registered_model_alias(CHAMPION, "champion", latest)
    print(f"\nregistered '{CHAMPION}' v{latest} + alias @champion")
    print(f"inspect: mlflow ui --backend-store-uri {TRACKING}")


if __name__ == "__main__":
    main()
