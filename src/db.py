"""DuckDB connection helper. File-based warehouse at <project_root>/platform.duckdb."""
import os
import duckdb

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "platform.duckdb"
)


def get_con():
    return duckdb.connect(DB_PATH)


def write_table(con, df, schema, table):
    """Replace schema.table with the contents of a pandas DataFrame."""
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {schema}.{table} AS SELECT * FROM _df")
    con.unregister("_df")
