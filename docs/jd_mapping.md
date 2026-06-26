# JD → Project mapping (Binance Data Analyst, Risk)

How this project demonstrates each requirement. **Capability shown by a built artifact — not claimed years of experience.**

| JD item | Where it's demonstrated |
|---|---|
| Build & maintain a **user tagging system** | dbt `marts/user_tags.sql` (value / lifecycle / risk families); `src/tagging.py` is the reference impl |
| Develop **user profiles** from large-scale data | dbt `marts/user_features.sql` (one row per user, behavioural features) |
| **Data mining, feature engineering, EDA** | `user_features` features + `docs/eda.md` |
| **Customer / user segmentation** | dbt `marts/user_segments.sql` (RFM) + `src/segmentation.py` (KMeans alternative) |
| **Identify patterns, anomalies** in user behaviour | `src/model_explainable.py` (explainable gradient-boosted classifier, time-validated) → `marts.txn_risk` / `user_risk` |
| **Risk control / anti-fraud** | the whole risk track; promo/withdrawal-ratio signals; PR-AUC eval |
| Monitor / evaluate **tag effectiveness** | precision of risk tags vs `is_abuser`; dashboard tiles |
| Python, SQL, **Power BI / Tableau**-class BI | Python + SQL + dbt + **Looker Studio** dashboard on BigQuery |
| ML applied to user data (advantage) | classifier + Isolation Forest |
| **Bonus / promo abuse, fraudulent studio groups** (preferred) | `src/abuse_rings.py` (Phase 2: shared-device/IP graph → ring detection) |
| **A/B testing, user lifecycle** (preferred) | Phase 2: cohort/retention + mock experiment |
| **Large-scale behavioural datasets** (preferred) | event-level data aggregated to users; scales on Postgres/BigQuery |
| **Internet platform / fintech** domain (preferred) | crypto-exchange-style event model (deposits/trades/withdrawals/promos) |

## Honest talking points (interview)
- "I built a user-tagging + risk-scoring pipeline on exchange-style behavioural data — profiling, segmentation, and an anti-fraud model, with the tag effectiveness measured against known abuse rings."
- Carry over the **capstone discipline**: lead on the precision/recall trade-off (a missed abuser vs a false flag), not headline accuracy.
- Gaps it does NOT close: actual years in a risk team, and crypto-specific abuse typologies — be straight about both.
