"""
Customer segmentation on the dbt user_features mart.
RFM scoring + KMeans clusters -> writes dbt_marts.user_segments.

Run after `dbt build`. TODO: tune k (elbow/silhouette), name clusters from centroids.
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
    write_table(con, out, "dbt_marts", "user_segments")
    con.close()
    print(out["segment"].value_counts().sort_index())
    print("wrote dbt_marts.user_segments")


if __name__ == "__main__":
    main()
