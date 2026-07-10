# Approach & decisions (the interview script)

This project is a **risk decision-support tool**, so the goal is a model I can **trust and defend**, not a leaderboard score. Every choice below was made deliberately; this page is the reasoning behind each, in plain language.

> On AI: I used an AI assistant to scaffold and write code faster. The **analytical decisions** — what to include, how to validate, where to set the alarm, what to trust — are mine, and the reasoning is below. That's the difference between *using* a tool and *outsourcing the judgement*.

## Decision 1 — Explainable features only (no anonymised columns)
The dataset ships 339 anonymised "V" features (Vesta's secret engineered signals). I **excluded only those** and used **every feature whose meaning is documented**: amount, all **association counts** (C1–C14), all **time-deltas** (D1–D15), **match flags** (M1–M9), distances, card type/network, product code, emails, device/identity, hour — plus explainable engineered features: a validated customer id, **rarity (frequency) encoding** of cards/addresses/emails, **amount-vs-card-group z-scores**, **drift-normalised time-deltas**, calendar/holiday, and behavioural distances.
- *Why:* if the model flags someone, I have to say **why** — to the customer, a colleague, or a regulator. "Column V257 was high" is not an answer. "This card value is rare, the amount is unusual for this card group, on a never-seen device" is.
- *Result:* the explainable model reaches **PR-AUC 0.540 / ROC-AUC 0.913** (time-validated) — within ~0.01 ROC-AUC of the domain expert's published 0.9245, using *only documented features*.
- *Trade-off, measured:* adding all 339 V-columns on top adds **nothing measurable** (black-box 0.538/0.911 vs explainable 0.540/0.913 — marginally *below*). Explainability isn't a compromise here; with the right FE it's the better model. (See `model_blackbox.py`.)
- *Interviewer Q: "Why not use all the data?"* → measured the gain; it's tiny; not worth losing the ability to explain a decision.

## Decision 2 — Time-based validation (don't fool yourself)
Fraud data is time-ordered, so I trained on the **earlier 70%** and tested on the **later 30%** — the model never sees the future.
- *Why:* a random shuffle lets the model peek at future transactions and **inflates** the result. Every number I quote is forward-in-time — the explainable model: **PR-AUC 0.540 / ROC-AUC 0.913**. That's what you'd actually get in production, not a flattering offline figure.
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

## Decision 4 — Entity resolution, validated; and knowing when a technique fits
The V-columns are mostly **aggregations over entities** (card/email/device), so I rebuilt that signal explainably rather than use the black box. The "account birthday" trick (`transaction-day − D1`, constant per real card-account) is the key — I later confirmed it's the same anchor the competition's UID expert (kyakovlev) used.

**I pressure-tested my own customer id** (the step beginners skip). My first key was *strict* — card components + billing region + birthday — on the instinct that "more fields = more precise". But matching on **all** of them **fragments** real customers whenever a field is blank or noisy. Validating it proved the point:

| Customer key | Customers | Avg history | Label-purity* |
|---|---|---|---|
| Strict (many fields) | 222,452 | 2.65 txns | 96.7% |
| **Simple + chained** (`card1 + birthday`, strays rescued via "days since last purchase") | **150,656** | **3.92 txns** | 94.4% |

\*share of multi-transaction customers that are all-fraud or all-honest — the "did I merge two different people?" check.

So the simpler key (plus timeline-chaining) gives **32% fewer, ~50% longer, still 94%-coherent** customer histories — the correct entity. **The id change alone didn't move the model** (~0.52 either way at that point); the later lift to **0.540 / 0.913** came from explainable *feature engineering* (rarity + card-group aggregations), not the id. The per-customer baseline features still don't rank.

- *The real insight:* the baseline/deviation idea catches **account-takeover** — an account behaving unlike itself. This dataset's fraud is mostly **first-transaction card fraud** (a stolen card used once), so there's no personal "normal" to deviate from, however well you reconstruct the customer. The baseline is the **right tool for a repeat-user platform** (an exchange like Binance), and genuinely the wrong lever here. Matching the technique to the fraud type is the judgement — and *"I validated my own grouping and found it over-fragmented, then learned the technique doesn't fit this fraud type"* is a stronger interview answer than a number.

## Decision 5 — Test my own signals honestly
My rule-of-thumb risk tags (`multi_identity`, `high_velocity`) sit **at or below** the 3.5% base fraud rate — i.e. they **don't** concentrate fraud. I kept that finding *in* (see `docs/results.md`) rather than hide it: simple rules look plausible but don't earn trust, so the learned model has to.

## Decision 6 — A layered dbt project, and SQL vs Python for each job
I split the work by what each tool is good at. The deterministic, rule-based transforms live in **dbt** as a layered project: two raw sources (transaction and identity) into typed **staging**, a single enriched **intermediate** transaction spine, then the **marts** (per-client features, RFM segmentation, the tagging system, and a client-360 risk profile). The ML lives in Python, where it belongs.
- *Why layered:* each step is small, named and testable. The tests are the point. Not just `not_null`/`unique` on keys, but **relationships** between layers, **accepted_values** on every tag and segment, and two singular tests that encode business rules (a fraud rate must sit in [0,1]; every client gets exactly one value tag and one lifecycle tag). If a CASE branch ever drifts, a test fails rather than a dashboard quietly lying.
- *Segmentation in SQL, not Python:* I made the dashboard segmentation **RFM in dbt** because it is deterministic, documented and re-runs identically on any warehouse. KMeans stays as a Python alternative (`user_segments_kmeans`) because it earns its place: it surfaces a tiny ultra-whale cohort that the broad RFM bands dilute. Right tool per job, not one tool for everything.
- *Portable on purpose:* the same models run on **DuckDB** (free local iteration) and **BigQuery** (free sandbox) by using dbt's cross-database macros and NTILE-based thresholds instead of warehouse-specific functions. One project, two warehouses, no forked SQL.

## Decision 7 — From a cost *framing* to a cost *decision* (implemented)
Decision 3 argued the threshold should be set on business cost; `src/decision_layer.py` now does it. Using each transaction's **amount** (a missed fraud loses the amount; a flag costs a flat review fee), on the same later-30% holdout:

| Policy | Realised cost | Recall | Alert rate |
|---|---|---|---|
| Naive threshold 0.5 | $708k | 0.36 | 1.6% |
| Cost-optimal single threshold (t*≈0.018) | $255k | 0.87 | 25% |
| **Amount-weighted EV policy** (block iff `p×amount > review`) | **$190k** | 0.76 | 19% |

- *Result:* the expected-value policy is **73% cheaper than naive-0.5** and recovers **80% of the $967k fraud exposure**. It blocks higher-value transactions (avg **$354 vs $85**) because it decides on *expected dollars at risk*, not probability alone — so it beats **any** global threshold (see `docs/charts/cost_curve.png`).
- *Why it matters:* this is the difference between a model and a **decision**. Two transactions with the same probability but different amounts are not the same risk.
- *Honesty:* the dollar costs are labelled **assumptions**; a sensitivity sweep shows the optimal threshold moves predictably with the review cost. The method, not the exact $, is the point.
- *Interviewer Q: "How would you deploy this?"* → score, then block on expected value under a review-capacity constraint; recalibrate the costs to the business.

## Decision 8 — Deep learning as a benchmark (and why boosting still wins)
I added two PyTorch models (`src/model_deep.py`): a **supervised MLP with entity embeddings**, and an **autoencoder** anomaly detector trained on legitimate transactions only. Same features, same time-split.
- *Result on the holdout:* MLP **PR-AUC 0.316 / ROC-AUC 0.853**; autoencoder **0.057 / 0.641** — both **below** the explainable HistGradientBoosting (**0.540 / 0.913**).
- *Why:* on tabular data with strong hand-engineered features, gradient boosting is the known strong baseline; a generic MLP must *learn* the interactions boosting exploits natively, and the autoencoder's "unlike normal" premise fits repeat-user account-takeover, not this dataset's first-transaction card fraud (same point as Decision 4).
- *The honest finding:* deep learning **did not beat** well-engineered boosting here — which is exactly why the production model stays HGB. Knowing when *not* to reach for a neural net is the judgement.
- *Caveat I'd raise myself:* the MLP was still improving at 8 epochs; more tuning would close some gap but not overtake 0.540 — and it would remain the less explainable choice.
- *Interviewer Q: "Did you try deep learning?"* → yes, benchmarked both an MLP and an autoencoder; documented that they underperform boosting on this problem, and why.

## What actually drives the model (so I can defend any flag)
Top signals by permutation importance: **association counts (C1, C14, C9, C13)**, **card rarity** (`card2_fq`, `card1_fq`), **email domain**, **card type**. All interpretable — a flag reads as e.g. *"this card is linked to an unusually high number of addresses, with a risky email domain and an odd billing distance."*

## Limitations (I'd raise these myself)
- "Customer" is a constructed id (card components + region + account-birthday) — IEEE-CIS has no ground-truth user id, so it's a validated heuristic.
- Single dataset, one time period; no concept-drift handling yet.
- PR-AUC 0.540 is solid for forward-in-time validation on a curated feature set, not a leaderboard-tuned figure — the value is a **trustworthy, reproducible, explainable** pipeline whose performance I can stand behind.
