# Approach & decisions (the interview script)

This project is a **risk decision-support tool**, so the goal is a model I can **trust and defend**, not a leaderboard score. Every choice below was made deliberately; this page is the reasoning behind each, in plain language.

> On AI: I used an AI assistant to scaffold and write code faster. The **analytical decisions** — what to include, how to validate, where to set the alarm, what to trust — are mine, and the reasoning is below. That's the difference between *using* a tool and *outsourcing the judgement*.

## Decision 1 — Explainable features only (no anonymised columns)
The dataset ships 339 anonymised "V" features (Vesta's secret engineered signals). I **excluded them** from the production model and used only signals with real fraud logic: transaction amount, **association counts** (how many addresses/devices are linked to a card), **days since prior activity**, **name/address match flags**, card type, product code, email domain, and an engineered **"how many accounts share this device/email"** signal.
- *Why:* if the model flags someone, I have to be able to say **why** — to the customer, a colleague, or a regulator. "Column V257 was high" is not an answer.
- *Trade-off, measured:* a black-box model using all 339 V-columns scored **PR-AUC 0.50** vs my explainable **0.47** — a **0.03** gain. I won't trade explainability for that. (See `model_blackbox.py`.)
- *Interviewer Q: "Why not use all the data?"* → the answer above.

## Decision 2 — Time-based validation (don't fool yourself)
Fraud data is time-ordered, so I trained on the **earlier 70%** and tested on the **later 30%** — the model never sees the future.
- *Why:* a random shuffle lets the model peek at future transactions and **inflates** the result. On a random split this model scored 0.62; tested honestly on later data it scores **0.47**. The 0.47 is the number I'd quote, because it's what you'd actually get in production.
- *Interviewer Q: "How do you know it'll hold up live?"* → I validated the way production runs: forward in time.

## Decision 3 — Set the alarm on cost, not on 0.5
Instead of a default cut-off, I report precision/recall at several **alert volumes** so the line can be set on the business cost of a **missed fraud** vs a **false accusation**:

| Flag the riskiest… | Precision | Recall |
|---|---|---|
| 0.5% | 0.91 | 0.13 |
| 1% | 0.84 | 0.24 |
| 2% | 0.66 | 0.38 |
| 5% | 0.37 | 0.53 |

- *Why:* a fraud team has finite review capacity and false accusations have real cost. The right threshold is a business choice, and I surface the trade-off rather than hide it behind 0.5.

## Decision 4 — Engineered a fraud-ring signal (judgement, not raw columns)
I created a "**how many accounts share this device / email domain**" feature — coordinated abuse rings share infrastructure.
- *Honest finding:* it was **not** a top driver at the transaction level. That's informative, not a failure — rings show up at the **account/graph level**, which is why ring detection is a separate piece (`abuse_rings.py`), not a single feature.

## Decision 5 — Test my own signals honestly
My rule-of-thumb risk tags (`multi_identity`, `high_velocity`) sit **at or below** the 3.5% base fraud rate — i.e. they **don't** concentrate fraud. I kept that finding *in* (see `docs/results.md`) rather than hide it: simple rules look plausible but don't earn trust, so the learned model has to.

## What actually drives the model (so I can defend any flag)
Top signals by permutation importance: **association counts (C1, C14, C2, C5, C13)**, product code, email domain, transaction amount, recency (D10, D4). All interpretable — a flagged account can be explained as e.g. *"this card is linked to an unusually high number of addresses/devices, with a risky product/email profile."*

## Limitations (I'd raise these myself)
- "Customer" is an approximation (`card1 + addr1`) — IEEE-CIS has no real user id.
- Single dataset, one time period; no concept drift handling yet.
- The model is a baseline by design — the value is a **trustworthy, reproducible, explainable** pipeline, not a leaderboard score.
