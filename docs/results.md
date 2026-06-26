# Results — User Analytics & Risk

Real run on **IEEE-CIS Fraud Detection** (Kaggle). Warehouse: DuckDB and BigQuery · transforms: **dbt** (layered, tested, documented) · analytics: Python · BI: Metabase + Looker Studio. All numbers below are from the live pipeline.

## Data
- 590,540 transactions, **3.5% fraud** (20,663). Aggregated by dbt to **39,974 clients** (`card1 + addr1` proxy — IEEE-CIS has no explicit user id; documented approximation). Client-level base fraud rate **3.16%**.

## Segmentation — RFM in dbt (primary), KMeans as the ML alternative
The dashboard-facing segmentation is **RFM in SQL** (`user_segments`): each client scored 1-5 on Recency, Frequency and Monetary, then banded into named segments. It is deterministic, tested and runs on both warehouses.

| Segment | Clients | Avg spend | Avg txns | Fraud rate |
|---|---|---|---|---|
| Potential | 9,577 | $308 | 2.1 | **4.13%** |
| At Risk | 8,584 | $120 | 1.1 | 3.30% |
| Loyal | 8,319 | $811 | 5.0 | 3.00% |
| Champions | 9,008 | $7,633 | 57.1 | 2.73% |
| Hibernating | 4,486 | $55 | 1.0 | 1.98% |

The honest read: fraud concentrates in **Potential** (lower-spend, low-frequency, newer clients), while high-value **Champions** sit *below* the base rate. That fits this dataset's fraud type — mostly **first-transaction card fraud**, not abuse of established high-value accounts.

A **KMeans** clustering alternative (`src/segmentation.py` → `user_segments_kmeans`) surfaces what broad RFM bands dilute: a tiny **whale micro-cohort of 14 clients — ~$344k avg spend, ~4,017 avg txns, 6.6% fraud rate** (the highest), exactly the high-value/high-risk group a risk team prioritises.

![segments](charts/segments.png) ![fraud by segment](charts/fraud_by_segment.png)

## User-tagging system
Three families, built in dbt (`user_tags`, long format) — **value** (vip/high/mid/low), **lifecycle** (active/dormant/new/one_off), **risk** (confirmed_fraud/multi_identity/high_velocity/clean). One client carries exactly one value tag, one lifecycle tag, and one or more risk tags (a dbt singular test enforces this).

## Tag effectiveness — the honest finding
![tag effectiveness](charts/tag_effectiveness.png)

Against the **3.16%** client-level base rate:
- `confirmed_fraud` clients: **36.8%** fraud rate — but this tag is **derived from the label**, so it's partly circular; not a discovery.
- `multi_identity` (**3.17%**) and `high_velocity` (**2.74%**) sit **at or below** the base rate. So naive identity/velocity heuristics **do not** concentrate fraud here. That's the point: simple rules look plausible but don't earn trust — the supervised model has to.

## Fraud model — explainable vs black-box (see `docs/approach_and_decisions.md`)
Both on the **same time-based split** (train earlier 70%, test later 30% — no peeking at the future):

| Model | Features | PR-AUC | ROC-AUC |
|---|---|---|---|
| **Explainable (production)** | every **documented** feature + **rarity (frequency) encoding**, **amount-vs-card-group z-scores**, **drift-normalised time-deltas**, calendar/holiday, behavioural hour-distance, validated customer id | **0.540** | **0.913** |
| Black-box (comparison) | the same **+ all 339 anonymised V-columns** | 0.538 | 0.911 |

**The headline:** the 339 opaque features add **nothing** — the black-box (0.538 / 0.911) is **essentially identical to, in fact marginally below**, the explainable model (0.540 / 0.913). Explainability isn't a compromise here; with the right feature engineering it's the **better** model. At **ROC-AUC 0.913** it sits within ~0.01 of the domain expert's published **0.9245** (kyakovlev) — using *only documented features*. ![model comparison](charts/model_comparison.png)

- **Explainable feature engineering (adapted from the domain expert):** the biggest lifts came from **rarity encoding** (how often a card/email value appears — `card2_fq` and `card1_fq` are now top features), **amount-vs-card-group z-scores** (aggregated on *high-volume* card groups, not the thin reconstructed customer), and **drift-normalising the time-deltas** per month so they mean the same thing across the timeline. All explainable; none use the V-columns.
- **Customer-id, validated (the craft step most skip):** rebuilt the customer *explainably* via an "account birthday" (`transaction-day − D1`). Pressure-testing showed a *strict* key over-fragmented (222k customers, 2.65 txns each) while the *simple+chained* key gives **150k, 3.92 txns each, 94% label-coherent** — the correct entity.
- **Honest finding — right tool, wrong fraud type:** the per-customer *baseline* still didn't move the model, because this dataset is **first-transaction card fraud** (no personal "normal" to deviate from). The baseline is the right tool for a **repeat-user platform** (an exchange like Binance); here the lift comes from the **fat-group aggregations + rarity** above. Matching technique to fraud type is the judgement.
- **Time-based honesty:** a random split flatters fraud models by letting them see the future; all numbers above are forward-in-time.
- **Operating points** (set the alarm on cost): flag riskiest 1% → precision 0.87 / recall 0.25; 2% → 0.70 / 0.40; 5% → 0.41 / 0.60.
- **Top drivers** (all explainable): association counts (C1/C14/C9/C13), **card rarity** (`card2_fq`, `card1_fq`), email domain, card type.

## Limitations (interview-ready)
Client id is an approximation; baseline feature set by design; `confirmed_fraud` tag is label-derived. The value here is a **trustworthy, reproducible pipeline** (dbt-tested) with an evaluation that interrogates its own signals — not a leaderboard score.

> Reproducibility note: the analytics layer was rebuilt as a layered dbt project (sources → staging → intermediate → marts) and the raw load was split into the two original Kaggle source tables. The fraud model was re-run end-to-end afterwards and the results are unchanged (explainable PR-AUC 0.539 / ROC-AUC 0.913; black-box ROC-AUC 0.913 — explainable marginally ahead). The customer-id validation figures (222,452 vs 150,656 clients) reproduced exactly, confirming the data is identical.
