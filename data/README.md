# Data

**Primary dataset: IEEE-CIS Fraud Detection** (Kaggle competition `ieee-fraud-detection`, Vesta). Real `isFraud` labels + rich card/device/email features — the best fit for a Data-Analyst (Risk) brief.

## Download (after accepting the competition rules)
1. Accept rules once: https://www.kaggle.com/competitions/ieee-fraud-detection/rules → "I Understand and Accept".
2. Token is at `~/.kaggle/access_token` (KGAT). Then:
```bash
source .venv/bin/activate             # project venv (has kagglehub)
export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token)
python -c "import kagglehub,glob,shutil; p=kagglehub.competition_download('ieee-fraud-detection'); [shutil.copy(f,'data/raw/') for f in glob.glob(p+'/train_*.csv')]"
python src/load_ieee.py               # -> DuckDB raw.transactions + raw.identity (+ joined view)
```
We use `train_transaction.csv` (+ `train_identity.csv`); `test_*` not needed (unlabelled).

## Canonical schema (what dbt expects)
Two source tables loaded by `src/load_ieee.py` into the local DuckDB file (`platform.duckdb`):
`raw.transactions` (train_transaction) and `raw.identity` (train_identity), plus a joined view
`raw.transactions_identity` for the Python feature pipeline. dbt staging (`stg_transactions`,
`stg_identity`) types each source; `stg_transactions` derives `event_ts` (TransactionDT ≈ from
2017-12-01) and `client_id` = `card1 + addr1` (user proxy — IEEE-CIS has no explicit user id;
documented assumption); `int_transactions_enriched` joins them and the marts aggregate per client.

Files go in `data/raw/` (gitignored). Respect the competition licence — don't commit raw data.

## Alternatives (if re-pointing later)
| Dataset | Strength | Risk label |
|---|---|---|
| eCommerce behavior, multi-category store (REES46) | best behavioural profiling/segmentation/lifecycle | none |
| PaySim mobile-money | fintech + fraud, aggregate per account | synthetic |
| Online Retail II (UCI) | RFM / CLV / cohorts | none |
