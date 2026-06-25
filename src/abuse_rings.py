"""
PHASE 2 — fraud-ring / shared-identifier detection (the JD's preferred line:
"bonus abuse, promotion abuse, fraudulent studio groups").

Clients that share a device (DeviceInfo) or email domain are linked in a graph;
dense communities are candidate rings. STUB to develop: score communities by size +
fraud_rate, validate against the real fraud label, frame for a non-technical reviewer.
"""
import pandas as pd
import networkx as nx
from db import get_con


def build_shared_identifier_graph(txns: pd.DataFrame) -> nx.Graph:
    g = nx.Graph()
    for key in ("deviceinfo", "p_emaildomain"):
        for val, grp in txns.dropna(subset=[key]).groupby(key):
            clients = grp["client_id"].unique()
            if len(clients) > 50:        # skip ubiquitous identifiers (e.g. gmail.com)
                continue
            for i in range(len(clients)):
                for j in range(i + 1, len(clients)):
                    g.add_edge(clients[i], clients[j], via=key)
    return g


def main():
    con = get_con()
    txns = con.execute(
        "select client_id, deviceinfo, p_emaildomain from dbt_staging.stg_transactions"
    ).df()
    con.close()
    g = build_shared_identifier_graph(txns)
    rings = [c for c in nx.connected_components(g) if len(c) >= 3]
    print(f"graph: {g.number_of_nodes()} clients, {g.number_of_edges()} links")
    print(f"candidate rings (>=3 linked clients): {len(rings)}")
    # TODO: score rings by joined fraud_rate; write dbt_marts.ring_flags; evaluate concentration.


if __name__ == "__main__":
    main()
