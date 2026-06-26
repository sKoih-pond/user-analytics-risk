"""
KMeans segmentation alternative on the dbt user_features mart -> writes
dbt_marts.user_segments_kmeans.

The canonical, dashboard-facing segmentation is the deterministic RFM model in
dbt (models/marts/user_segments.sql). This script is the ML alternative: it adds RFM
scores then clusters on standardised behavioural features with KMeans, which surfaces a
tiny ultra-whale micro-cohort that broad RFM bands dilute. Run after `dbt build`.
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from db import get_con, write_table

FEATURES = ["recency_days", "frequency", "monetary", "avg_amount", "n_devices", "n_emails"]
K = 5


def rfm_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["R"] = pd.qcut(df["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    df["F"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["M"] = pd.qcut(df["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["rfm_score"] = df["R"] + df["F"] + df["M"]
    return df


def main():
    con = get_con()
    df = con.execute("select * from dbt_marts.user_features").df()
    df = rfm_scores(df)

    X = StandardScaler().fit_transform(df[FEATURES].fillna(0))
    df["segment"] = KMeans(n_clusters=K, random_state=42, n_init=10).fit_predict(X)

    out = df[["client_id", "R", "F", "M", "rfm_score", "segment"]]
    write_table(con, out, "dbt_marts", "user_segments_kmeans")
    con.close()
    print(out["segment"].value_counts().sort_index())
    print("wrote dbt_marts.user_segments_kmeans (RFM segmentation is dbt-owned: user_segments)")


if __name__ == "__main__":
    main()
