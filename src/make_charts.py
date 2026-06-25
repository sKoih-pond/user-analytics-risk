"""
Render the dashboard charts as static PNGs into docs/charts/ — a PERMANENT portfolio
artifact, independent of the (ephemeral) Metabase Cloud trial. Reads the dbt marts.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from db import get_con

OUT = "docs/charts"
os.makedirs(OUT, exist_ok=True)
con = get_con()


def save(fig, name):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}", dpi=120, bbox_inches="tight"); plt.close(fig)
    print("wrote", f"{OUT}/{name}")


# 1. Clients per segment
df = con.execute("select segment, count(*) c from dbt_marts.user_segments group by segment order by segment").df()
fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(df.segment.astype(str), df.c, color="#4C78A8")
ax.set_title("Clients per segment"); ax.set_xlabel("segment"); ax.set_ylabel("clients"); save(fig, "segments.png")

# 2. Risk-tag distribution
df = con.execute("select tag, count(*) c from dbt_marts.user_tags where tag_family='risk' group by tag order by c desc").df()
fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(df.tag, df.c, color="#E45756")
ax.set_title("Risk-tag distribution"); ax.set_ylabel("clients"); plt.xticks(rotation=20, ha="right"); save(fig, "risk_tags.png")

# 3. Tag effectiveness: fraud rate by risk tag vs base rate
base = con.execute("select avg(fraud_rate) from dbt_marts.user_features").fetchone()[0]
df = con.execute("""
  select t.tag, round(avg(c.fraud_rate),4) afr
  from dbt_marts.user_tags t join dbt_marts.user_features c using(client_id)
  where t.tag_family='risk' group by t.tag order by afr desc""").df()
fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(df.tag, df.afr, color="#F58518")
ax.axhline(base, ls="--", color="grey", label=f"base rate {base:.3f}")
ax.set_title("Fraud rate by risk tag"); ax.set_ylabel("avg fraud_rate"); ax.legend()
plt.xticks(rotation=20, ha="right"); save(fig, "tag_effectiveness.png")

# 4. Fraud rate by segment
df = con.execute("""
  select s.segment, round(avg(f.fraud_rate),4) afr
  from dbt_marts.user_segments s join dbt_marts.user_features f using(client_id)
  group by s.segment order by s.segment""").df()
fig, ax = plt.subplots(figsize=(6, 4)); ax.bar(df.segment.astype(str), df.afr, color="#72B7B2")
ax.set_title("Fraud rate by segment"); ax.set_xlabel("segment"); ax.set_ylabel("avg fraud_rate"); save(fig, "fraud_by_segment.png")

con.close()
print("done")
