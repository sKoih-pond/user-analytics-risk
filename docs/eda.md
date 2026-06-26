# EDA — the evidence behind the modelling choices

EDA here isn't decoration: every finding **justifies a specific modelling decision**. Two reproducible scripts produce it — `src/explore_features.py` (target-aware, alijs-style) and `src/eda_columns.py` (structural: NaN-grouping + redundancy, cdeotte-style). All from the loaded `raw.transactions` (590,540 rows × 434 columns).

## 1. Missingness has structure (and is itself a signal)
Grouping columns by **how many NaNs they have** (columns missing on the same rows share a source) yields **70 distinct missingness blocks**; the 339 V-columns fall into just **15 blocks**.
- **Identity record present in only 23.8% of rows — and where it's present, fraud is 8.0% vs 2.1% without.** Whether the identity block is missing is a strong signal.
- → *Decision:* a `has_identity` feature; and knowing column provenance (which blocks co-occur) before trusting them.

## 2. The 339 V-columns are highly redundant
Within the missingness blocks the V-columns are strongly correlated: **238 of 339 (70%) have a near-duplicate (|corr| > 0.9)**. Even a reduced set stays internally correlated.

![V block correlation](charts/v_block_corr.png)

- → *This is the EDA evidence for the model result:* the black-box (explainable + all 339 V) scored **0.538 vs the explainable 0.540** — i.e. the V-columns added nothing, *because there's barely any unique information in them.* The structural EDA and the model agree from two directions.

## 3. Time-deltas drift upward
The `D` columns are "days since…", so they **grow over time** — mean `D15` rises from **146 to 197** across the months.

![D drift](charts/d_drift.png)

- → *Decision:* **normalise the D columns per time-period** so a value means the same thing across the timeline (a forward-in-time test otherwise punishes the drift).

## 4. Column reference (groups, sparsity)
| Group | Cols | Mean NaN % |
|---|---|---|
| V (anonymised) | 339 | 43.0 |
| id (identity) | 38 | 84.8 |
| D (time-deltas) | 15 | 58.2 |
| C (counts) | 14 | **0.0** |
| base (amount, card, addr, email…) | 10 | 24.9 |
| M (match flags) | 9 | 49.9 |
| card | 6 | 0.5 |
| addr / dist | 4 | 43.9 |

- → *Decision:* the **C (counts)** group is fully populated and dominates importance; the **id** group is 85% empty (use sparingly). Sparsity guides how much to lean on each family.

## 5. Target-aware signals (`explore_features.py`)
Fraud rate by value: **ProductCD "C" 11.7%** vs "W" 2.0%; **credit 6.7%** vs debit 2.4%; **outlook/hotmail emails** 5–9% vs ~3% base; **~7am hour** 10.6% vs afternoon ~2.3%; association count **C1 averages 35 for fraud vs 13**; and **`card1` maps to ~11 different account-birthdays** (too coarse to be a customer).
- → *Decisions:* **rarity/frequency encoding** (rare values are risky), the **calendar/hour** features, the **association-count** features, and the **simpler+validated customer id**.

## Reproduce
```bash
python src/explore_features.py   # target-aware fraud-rate EDA
python src/eda_columns.py        # missingness blocks, V-redundancy, drift -> docs/charts/
```
Every chart and number above regenerates from the loaded data — no raw competition data committed.
