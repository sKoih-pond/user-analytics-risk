"""
DEEP-LEARNING BENCHMARK — does a neural net beat well-engineered gradient boosting here?

Two PyTorch models, both evaluated on the SAME later-30% time-holdout as the explainable model
(reusing prepare()/build_X() so the comparison is apples-to-apples):

  1. Supervised MLP with ENTITY EMBEDDINGS — an embedding per categorical column concatenated with
     standardised numerics -> 2 hidden layers -> logit; BCE with pos_weight for the 3.5% imbalance.
  2. AUTOENCODER (unsupervised anomaly detection) — trained on LEGITIMATE transactions only; fraud
     scored by reconstruction error. A different paradigm to the supervised models.

The honest expectation on tabular data with strong hand-built features is that deep learning does NOT
beat HistGradientBoosting (explainable model: PR-AUC 0.540 / ROC-AUC 0.913). Whatever the result, this
reports it — a benchmark that either validates the simpler model or is beaten by it, not a claim.

Adds one dependency (torch). CPU is sufficient (~413k train rows, minutes).
"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score
from model_explainable import prepare, NUMERIC, CATEGORICAL
from db import get_con

SEED = 42
BATCH = 4096
MLP_EPOCHS = 8
AE_EPOCHS = 8
VAL_FRAC = 0.15          # last 15% of TRAIN (by time) held out for early stopping
torch.manual_seed(SEED)
np.random.seed(SEED)
DEV = torch.device("cpu")


def encode(df, train):
    """Fit-on-train encoders: standardised numerics + integer-coded categoricals (0 = unknown/missing)."""
    num = df[NUMERIC].astype(float).replace([np.inf, -np.inf], np.nan)
    med = num[train].median()
    num = num.fillna(med)
    mu, sd = num[train].mean(), num[train].std().replace(0, 1.0)
    Xn = ((num - mu) / sd).clip(-10, 10).to_numpy(np.float32)

    cat_mats, cards = [], []
    for c in CATEGORICAL:
        s = df[c].astype("string").fillna("missing")
        vocab = {v: i + 1 for i, v in enumerate(s[train].unique())}   # 0 reserved for unseen
        cat_mats.append(s.map(vocab).fillna(0).astype(np.int64).to_numpy())
        cards.append(len(vocab) + 1)
    Xc = np.stack(cat_mats, axis=1)
    return Xn, Xc, cards


class MLP(nn.Module):
    def __init__(self, n_num, cards):
        super().__init__()
        self.embs = nn.ModuleList([nn.Embedding(c, min(50, (c // 2) + 1)) for c in cards])
        emb_dim = sum(e.embedding_dim for e in self.embs)
        self.net = nn.Sequential(
            nn.Linear(n_num + emb_dim, 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 1),
        )

    def forward(self, xn, xc):
        e = [emb(xc[:, i]) for i, emb in enumerate(self.embs)]
        return self.net(torch.cat([xn] + e, dim=1)).squeeze(1)


class AE(nn.Module):
    def __init__(self, n):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(n, 64), nn.ReLU(), nn.Linear(64, 16), nn.ReLU())
        self.dec = nn.Sequential(nn.Linear(16, 64), nn.ReLU(), nn.Linear(64, n))

    def forward(self, x):
        return self.dec(self.enc(x))


def batches(n, shuffle=True):
    idx = np.random.permutation(n) if shuffle else np.arange(n)
    for i in range(0, n, BATCH):
        yield idx[i:i + BATCH]


def train_mlp(Xn, Xc, y, tr_idx, va_idx, pos_weight):
    m = MLP(Xn.shape[1], [int(c) for c in Xc.max(0) + 1]).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3, weight_decay=1e-5)
    lossf = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight))
    xn, xc, yt = torch.tensor(Xn), torch.tensor(Xc), torch.tensor(y.astype(np.float32))
    best, best_state, patience = -1, None, 0
    for ep in range(MLP_EPOCHS):
        m.train()
        for b in batches(len(tr_idx)):
            j = tr_idx[b]
            opt.zero_grad()
            lossf(m(xn[j], xc[j]), yt[j]).backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            pv = torch.sigmoid(m(xn[va_idx], xc[va_idx])).numpy()
        ap = average_precision_score(y[va_idx], pv)
        print(f"  MLP epoch {ep+1}/{MLP_EPOCHS}  val PR-AUC {ap:.4f}")
        if ap > best:
            best, best_state, patience = ap, {k: v.clone() for k, v in m.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 2:
                break
    m.load_state_dict(best_state)
    return m, xn, xc


def train_ae(Xn, tr_legit_idx, te_idx):
    m = AE(Xn.shape[1]).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    lossf = nn.MSELoss()
    x = torch.tensor(Xn)
    for ep in range(AE_EPOCHS):
        m.train()
        for b in batches(len(tr_legit_idx)):
            j = tr_legit_idx[b]
            opt.zero_grad()
            lossf(m(x[j]), x[j]).backward()
            opt.step()
    m.eval()
    with torch.no_grad():
        err = ((m(x[te_idx]) - x[te_idx]) ** 2).mean(1).numpy()   # reconstruction error = anomaly score
    return m, err


def main():
    con = get_con()
    df, train = prepare(con)
    con.close()
    y = df["y"].astype(int).to_numpy()
    Xn, Xc, cards = encode(df, train)
    print(f"encoded: {Xn.shape[1]} numeric + {len(cards)} categorical (embeddings) | "
          f"train {train.sum():,} test {(~train).sum():,}")

    idx = np.arange(len(df))
    tr_all, te_idx = idx[train.to_numpy()], idx[~train.to_numpy()]
    order = tr_all[np.argsort(df.transactiondt.to_numpy()[tr_all])]   # time-order the train rows
    n_val = int(len(order) * VAL_FRAC)
    tr_idx, va_idx = order[:-n_val], order[-n_val:]                   # earliest -> train, latest -> val
    pos_weight = (y[tr_idx] == 0).sum() / max((y[tr_idx] == 1).sum(), 1)

    print("\n[1] supervised MLP + entity embeddings")
    m, xn, xc = train_mlp(Xn, Xc, y, tr_idx, va_idx, pos_weight)
    with torch.no_grad():
        p_mlp = torch.sigmoid(m(xn[te_idx], xc[te_idx])).numpy()
    ap_mlp, roc_mlp = average_precision_score(y[te_idx], p_mlp), roc_auc_score(y[te_idx], p_mlp)

    print("\n[2] autoencoder (trained on legit only)")
    tr_legit = tr_all[y[tr_all] == 0]
    _, err = train_ae(Xn, tr_legit, te_idx)
    ap_ae, roc_ae = average_precision_score(y[te_idx], err), roc_auc_score(y[te_idx], err)

    print("\n=== benchmark on the same later-30% holdout ===")
    print(f"  {'model':<34} {'PR-AUC':>8} {'ROC-AUC':>8}")
    print(f"  {'HistGradientBoosting (explainable)':<34} {0.540:>8.3f} {0.913:>8.3f}   <- reference")
    print(f"  {'Deep MLP (embeddings)':<34} {ap_mlp:>8.3f} {roc_mlp:>8.3f}")
    print(f"  {'Autoencoder (anomaly)':<34} {ap_ae:>8.3f} {roc_ae:>8.3f}")
    verdict = "beats" if ap_mlp > 0.540 else "does not beat"
    print(f"\n  Finding: deep learning {verdict} well-engineered gradient boosting on this tabular problem.")


if __name__ == "__main__":
    main()
