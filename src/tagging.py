"""
User-tagging system — reference Python implementation.

The canonical tagging is now the dbt model (models/marts/user_tags.sql), which the
dashboard and tests use. This script is kept as the readable reference for the same rules
and writes dbt_marts.user_tags_python so it never overwrites the dbt-owned table. The dbt
version uses NTILE(100) percentile ranks for portability; this one uses exact quantiles —
the tag distributions differ slightly but the families and qualitative findings match.

  value:     vip / high / mid / low        (monetary + frequency)
  lifecycle: active / dormant / one_off / new   (recency + tenure)
  risk:      confirmed_fraud / multi_identity / high_velocity / clean
"""
import pandas as pd
from db import get_con, write_table


def value_tag(r):
    if r.monetary >= r.m_p90 and r.frequency >= r.f_p75:
        return "vip"
    if r.monetary >= r.m_p75:
        return "high"
    if r.monetary >= r.m_p50:
        return "mid"
    return "low"


def lifecycle_tag(r):
    if r.n_txn <= 1:
        return "one_off"
    if r.recency_days <= 30:
        return "active"
    if r.recency_days <= 90:
        return "dormant"
    return "new" if (r.tenure_days or 0) <= 30 else "dormant"


def risk_tags(r):
    tags = []
    if (r.fraud_rate or 0) > 0:
        tags.append("confirmed_fraud")
    if (r.n_devices or 0) >= 3 or (r.n_emails or 0) >= 3:
        tags.append("multi_identity")          # shared/many identifiers — abuse-ring signal
    if (r.avg_c14 or 0) >= r.c14_p95:
        tags.append("high_velocity")
    return tags or ["clean"]


def main():
    con = get_con()
    df = con.execute("select * from dbt_marts.user_features").df()
    df["m_p50"], df["m_p75"], df["m_p90"] = (df.monetary.quantile(q) for q in (0.5, 0.75, 0.90))
    df["f_p75"] = df.frequency.quantile(0.75)
    df["c14_p95"] = df.avg_c14.fillna(0).quantile(0.95)

    rows = []
    for r in df.itertuples():
        rows.append((r.client_id, "value", value_tag(r)))
        rows.append((r.client_id, "lifecycle", lifecycle_tag(r)))
        for t in risk_tags(r):
            rows.append((r.client_id, "risk", t))

    out = pd.DataFrame(rows, columns=["client_id", "tag_family", "tag"])
    write_table(con, out, "dbt_marts", "user_tags_python")
    con.close()
    print(out.groupby(["tag_family", "tag"]).size())
    print("wrote dbt_marts.user_tags_python (canonical tagging is dbt-owned: user_tags)")


if __name__ == "__main__":
    main()
