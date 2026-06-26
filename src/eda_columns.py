"""
Structural EDA — the evidence behind the modelling choices.
Adapted from two IEEE-CIS references: alijs1 (per-column reference) and
cdeotte (NaN-grouping of the V/ID columns). Reproducible; reads raw.transactions_identity;
saves charts to docs/charts/. Findings written up in docs/eda.md.
"""
import os
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from db import get_con

OUT = "docs/charts"
os.makedirs(OUT, exist_ok=True)
con = get_con()
df = con.execute("select * from raw.transactions_identity").df()
df.columns = df.columns.str.lower()
N = len(df)
print(f"rows={N:,}  columns={df.shape[1]}")

# ---- 1. Missingness blocks (Deotte): columns missing on the same rows share a source ----
nan_count = df.isna().sum()
blocks = {}
for c in df.columns:
    blocks.setdefault(int(nan_count[c]), []).append(c)
v_blocks = sum(1 for k, v in blocks.items() if any(c.startswith("v") for c in v))
print(f"\n[missingness] {len(blocks)} distinct NaN-count blocks; V-columns fall into {v_blocks} blocks "
      f"(same NaN count = same source/timeframe)")
has_id = df["devicetype"].notna()
print(f"[missingness] identity record present in {has_id.mean()*100:.1f}% of rows | "
      f"fraud {df.loc[has_id,'isfraud'].mean():.3f} vs {df.loc[~has_id,'isfraud'].mean():.3f} without "
      f"-> whether the identity block is missing is itself a signal")

# ---- 2. V-column redundancy ----
vcols = [c for c in df.columns if re.fullmatch(r"v\d+", c)]
samp = df[vcols].sample(min(50000, N), random_state=42)
corr = samp.corr().abs()
np.fill_diagonal(corr.values, 0.0)
twin = (corr.max() > 0.9).sum()
print(f"\n[V-redundancy] {len(vcols)} V-columns; {twin} ({twin/len(vcols)*100:.0f}%) have a |corr|>0.9 twin "
      f"-> highly redundant, little unique signal (why the black box added nothing)")
block = [f"v{i}" for i in range(1, 12)]
m = df[block].sample(min(50000, N), random_state=1).corr()
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(m.values, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(block))); ax.set_xticklabels(block, rotation=90)
ax.set_yticks(range(len(block))); ax.set_yticklabels(block)
plt.colorbar(im, fraction=0.046); ax.set_title("V1–V11: a highly-correlated (redundant) block")
fig.tight_layout(); fig.savefig(f"{OUT}/v_block_corr.png", dpi=120); plt.close(fig)

# ---- 3. Drift: time-deltas grow over time (why we normalise per period) ----
df["mth"] = (np.floor(df.transactiondt / 86400) // 30).astype(int)
drift = df.groupby("mth")["d15"].mean()
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(drift.index, drift.values, marker="o", color="#F58518")
ax.set_title("Time-deltas (D15) drift upward over time"); ax.set_xlabel("month index"); ax.set_ylabel("mean D15")
fig.tight_layout(); fig.savefig(f"{OUT}/d_drift.png", dpi=120); plt.close(fig)
print(f"\n[drift] mean D15 rises from {drift.iloc[0]:.0f} to {drift.iloc[-1]:.0f} across months "
      f"-> raw D means different things over time; normalise per period")

# ---- 4. Column reference (alijs-style), summarised by group ----
def grp(c):
    if re.fullmatch(r"c\d+", c): return "C (counts)"
    if re.fullmatch(r"d\d+", c): return "D (time-deltas)"
    if re.fullmatch(r"m\d+", c): return "M (match flags)"
    if re.fullmatch(r"v\d+", c): return "V (anonymised)"
    if c.startswith("id_"): return "id (identity)"
    if c.startswith("card"): return "card"
    if c.startswith(("addr", "dist")): return "addr/dist"
    return "base"
ref = pd.DataFrame({"col": df.columns})
ref["group"] = ref.col.map(grp)
ref["nan_pct"] = ref.col.map(lambda c: df[c].isna().mean() * 100)
summary = ref.groupby("group").agg(cols=("col", "size"), mean_nan_pct=("nan_pct", "mean")).round(1)
print("\n=== column groups (count + mean NaN%) ===")
print(summary.sort_values("cols", ascending=False).to_string())

con.close()
print("\nsaved charts: v_block_corr.png, d_drift.png")
