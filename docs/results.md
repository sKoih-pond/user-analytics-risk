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

## Fraud model — explainable vs black-box (see `docs/approach_and_decisions.md`)
Built two models on the **same time-based split** (train on earlier 70%, test on later 30% — no peeking at the future):

| Model | Features | PR-AUC (time-split) |
|---|---|---|
| **Explainable (production)** | interpretable only — amount, association counts, recency, match flags, card/email/device + engineered device/email-sharing | **0.470** |
| Black-box (comparison) | + all **339 anonymised V-columns** | 0.501 |

**The headline decision:** the 339 opaque features buy only **+0.03 PR-AUC**. Not worth losing the ability to explain a fraud decision — so the explainable model ships. ![model comparison](charts/model_comparison.png)

- **Honesty note:** on a *random* split this model scored 0.62; tested honestly **forward in time** it's **0.47**. The 0.47 is the real number. Random splitting inflates fraud results by letting the model see the future.
- **Operating points** (set the alarm on cost, not 0.5): flag the riskiest 1% → precision 0.84 / recall 0.24; 2% → 0.66 / 0.38; 5% → 0.37 / 0.53.
- **Top drivers** (all explainable): association counts (C1/C14/C2/C5/C13), product code, email domain, amount, recency.

## Limitations (interview-ready)
Client id is an approximation; baseline feature set by design; `confirmed_fraud` tag is label-derived. The value here is a **trustworthy, reproducible pipeline** (dbt-tested) with an evaluation that interrogates its own signals — not a leaderboard score.
