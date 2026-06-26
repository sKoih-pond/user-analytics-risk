"""
Export the dbt marts to CSV for the Metabase CSV-upload path (Metabase Cloud cannot reach a
local DuckDB file). Writes to dashboards/exports/ (gitignored — regenerable). Run after
`dbt build`.
"""
import os
from db import get_con

OUT = "dashboards/exports"
os.makedirs(OUT, exist_ok=True)

EXPORTS = {
    "client_360": "select * from dbt_marts.user_risk_profile",
    "user_tags": "select * from dbt_marts.user_tags",
    "user_segments": "select * from dbt_marts.user_segments",
}


def main():
    con = get_con()
    for name, sql in EXPORTS.items():
        df = con.execute(sql).df()
        path = f"{OUT}/{name}.csv"
        df.to_csv(path, index=False)
        print(f"wrote {path}: {df.shape[0]:,} rows x {df.shape[1]} cols")
    con.close()


if __name__ == "__main__":
    main()
