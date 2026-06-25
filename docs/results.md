# Results — User Analytics & Risk

Real run on **IEEE-CIS Fraud Detection** (Kaggle). Warehouse: DuckDB · transforms: dbt (tested) · analytics: Python · BI: Metabase. All numbers below are from the live pipeline.

## Data
- 590,540 transactions, **3.5% fraud** (20,663). Aggregated to **39,974 clients** (`card1 + addr1` proxy — IEEE-CIS has no explicit user id; documented approximation).

## Segmentation (RFM + KMeans, 5 segments)
A small **whale** cohort stands out: segment 3 = 17 clients, **~$338k avg spend, 3,755 avg txns, 5.9% fraud rate** (the highest) — exactly the high-value/high-risk group a risk team prioritises.

![segments](charts/segments.png) ![fraud by segment](charts/fraud_by_segment.png)

## User-tagging system
Three families — **value** (vip/high/mid/low), **lifecycle** (active/dormant/new/one_off), **risk** (confirmed_fraud/multi_identity/high_velocity/clean).

## Tag effectiveness — the honest finding
![tag effectiveness](charts/tag_effectiveness.png)

- `confirmed_fraud` clients: **36.7%** fraud rate — but this tag is **derived from the label**, so it's partly circular; not a discovery.
- `multi_identity` (**3.2%**) and `high_velocity` (**2.8%**) sit **at or below** the 3.5% base rate. So naive identity/velocity heuristics **do not** concentrate fraud here. That's the point: simple rules look plausible but don't earn trust — the supervised model has to.

## Fraud model (HistGradientBoosting, transaction-level)
- **PR-AUC 0.617** (vs 0.035 random baseline); precision **0.875** / recall **0.383** on fraud at the default 0.5 threshold; **1,754** clients flagged.
- Features: numeric (amount + C/D counts) **+ categoricals** (card type/network, product code, email domain, device type) via HistGBM's native categorical support — adding the categoricals lifted PR-AUC from a numeric-only **0.524** to **0.617**.
- **Honest baseline:** still uses a curated subset, not IEEE-CIS's full 400+ V-columns. Kaggle leaders reached ~0.93 AUC with the full V-columns + heavy engineering. Discipline carried from the IDS capstone: report **PR-AUC + the precision/recall trade-off on the rare class**, not headline accuracy.
- **Next gains:** load the V/identity columns, threshold tuning off the precision/recall curve, time-based validation split.

## Limitations (interview-ready)
Client id is an approximation; baseline feature set by design; `confirmed_fraud` tag is label-derived. The value here is a **trustworthy, reproducible pipeline** (dbt-tested) with an evaluation that interrogates its own signals — not a leaderboard score.
