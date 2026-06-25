# Approach & decisions (the interview script)

This project is a **risk decision-support tool**, so the goal is a model I can **trust and defend**, not a leaderboard score. Every choice below was made deliberately; this page is the reasoning behind each, in plain language.

> On AI: I used an AI assistant to scaffold and write code faster. The **analytical decisions** — what to include, how to validate, where to set the alarm, what to trust — are mine, and the reasoning is below. That's the difference between *using* a tool and *outsourcing the judgement*.

## Decision 1 — Explainable features only (no anonymised columns)
The dataset ships 339 anonymised "V" features (Vesta's secret engineered signals). I **excluded only those** and used **every feature whose meaning is documented**: amount, all **association counts** (C1–C14), all **time-deltas** (D1–D15), **name/address match flags** (M1–M9), distances, card type/network, product code, buyer/recipient email, device/identity signals, hour-of-day — plus engineered explainable features (sharper customer id, cross-account sharing, per-customer baseline).
- *Why:* if the model flags someone, I have to say **why** — to the customer, a colleague, or a regulator. "Column V257 was high" is not an answer. "This card is linked to an unusual number of addresses, at an odd hour, on a never-seen device" is.
- *Trade-off, measured:* adding all 339 V-columns on top of this model lifts PR-AUC by only **+0.013** (0.538 vs **0.525**) and ROC-AUC by **0.000** (both 0.901). Explainability is effectively **free** here, so I ship the model I can defend. (See `model_blackbox.py`.)
- *Interviewer Q: "Why not use all the data?"* → measured the gain; it's 0.013; not worth losing the ability to explain a decision.

## Decision 2 — Time-based validation (don't fool yourself)
Fraud data is time-ordered, so I trained on the **earlier 70%** and tested on the **later 30%** — the model never sees the future.
- *Why:* a random shuffle lets the model peek at future transactions and **inflates** the result. Every number I quote is forward-in-time — the explainable model: **PR-AUC 0.525 / ROC-AUC 0.901**. That's what you'd actually get in production, not a flattering offline figure.
- *Interviewer Q: "How do you know it'll hold up live?"* → I validated the way production runs: forward in time.

## Decision 3 — Set the alarm on cost, not on 0.5
Instead of a default cut-off, I report precision/recall at several **alert volumes** so the line can be set on the business cost of a **missed fraud** vs a **false accusation**:

| Flag the riskiest… | Precision | Recall |
|---|---|---|
| 0.5% | 0.93 | 0.13 |
| 1% | 0.87 | 0.25 |
| 2% | 0.69 | 0.40 |
| 5% | 0.40 | 0.58 |

- *Why:* a fraud team has finite review capacity and false accusations have real cost. The right threshold is a business choice, and I surface the trade-off rather than hide it behind 0.5.

## Decision 4 — Entity resolution + a per-customer baseline (judgement, not raw columns)
The V-columns are mostly **aggregations over entities** (card/email/device). So instead of using the black box, I rebuilt that signal explainably:
- **Sharper customer id:** `card1` alone is far too coarse (it maps to ~11 different accounts). I combined the card components + billing region + an **"account birthday"** (`transaction-day − D1`, which is constant per real account) into a stable customer id.
- **Leak-free per-customer baseline:** for each transaction I compute the customer's *normal* from their **earlier** transactions only (amount mean/std, count, time-since-last, is-this-device-new), then how far this transaction **deviates** — both a model feature and an explainable alert rule.
- **Profile fallback:** for brand-new customers (no history) I fall back to the norm for their product/segment.
- *Honest finding:* on **this** dataset the per-customer baseline barely moved the score — ~222k customers over 590k transactions means most appear once or twice, so there's little personal history to deviate from. It's the **right** approach for a **repeat-user platform** (an exchange like Binance has ongoing accounts); on one-shot card data the signal lives in the association counts. Knowing *when* a technique fits is part of the judgement.

## Decision 5 — Test my own signals honestly
My rule-of-thumb risk tags (`multi_identity`, `high_velocity`) sit **at or below** the 3.5% base fraud rate — i.e. they **don't** concentrate fraud. I kept that finding *in* (see `docs/results.md`) rather than hide it: simple rules look plausible but don't earn trust, so the learned model has to.

## What actually drives the model (so I can defend any flag)
Top signals by permutation importance: **association counts (C1, C14, C13, C9)**, buyer/recipient **email domains**, **distances**, **time-deltas**, **billing region**. All interpretable — a flag reads as e.g. *"this card is linked to an unusually high number of addresses, with a risky email domain and an odd billing distance."*

## Limitations (I'd raise these myself)
- "Customer" is a constructed id (card components + region + account-birthday) — IEEE-CIS has no ground-truth user id, so it's a validated heuristic.
- Single dataset, one time period; no concept-drift handling yet.
- PR-AUC 0.525 is solid for forward-in-time validation on a curated feature set, not a leaderboard-tuned figure — the value is a **trustworthy, reproducible, explainable** pipeline whose performance I can stand behind.
