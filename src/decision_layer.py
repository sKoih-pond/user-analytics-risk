"""
COST-SENSITIVE DECISION LAYER — turn fraud probabilities into a business decision.

A ROC-AUC is not a decision. What a risk team actually chooses is: which transactions to
block/review, given that a missed fraud costs the transaction AMOUNT and a review costs money.
This module reads the model's out-of-sample scores (dbt_marts.txn_risk) plus each transaction's
amount, and evaluates three policies on the later-30% time-holdout:

  1. naive threshold 0.5            — the default nobody should ship
  2. cost-optimal global threshold  — the single t* that minimises realised dollar cost
  3. amount-weighted EV policy      — block iff expected fraud loss (p x amount) > review cost;
                                      a per-transaction rule, no single threshold

It reports realised dollar cost + operating point (precision/recall/alert-rate) for each, a
sensitivity sweep over the review-cost assumption, writes docs/charts/cost_curve.png, and persists
the amount-weighted decisions to dbt_marts.txn_decision.

ASSUMPTIONS (module constants, clearly labelled — the numbers are illustrative, the METHOD is the
point): a missed fraud loses the transaction amount; a flagged transaction costs a flat review fee.
Evaluated out-of-time to match the model's time-based validation.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score
from db import get_con, write_table

# --- ASSUMPTIONS (illustrative dollar costs; the decision METHOD is what's being demonstrated) ---
C_REVIEW = 3.0            # $ cost of flagging one transaction (manual review + customer friction)
TIME_CUT_Q = 0.70        # same forward-in-time split the model trains on (model_explainable.py:120)
OUT = "docs/charts"
INK, BLOCK, ALLOW, MARK = "#2E2925", "#E45756", "#4C78A8", "#F58518"


def load_test_slice(con):
    """Model scores (out-of-sample for the later slice) joined to amount, restricted to the holdout."""
    df = con.execute("""
        SELECT r.transaction_id, r.is_fraud, r.fraud_proba,
               t.TransactionDT AS transactiondt, t.TransactionAmt AS amount
        FROM dbt_marts.txn_risk r
        JOIN raw.transactions t ON r.transaction_id = t.TransactionID
    """).df()
    cut = df.transactiondt.quantile(TIME_CUT_Q)      # identical cut to the model's train/test split
    test = df[df.transactiondt > cut].reset_index(drop=True)
    return test


def realised_cost(y, amount, block, c_review):
    """Blocked -> pay review; allowed fraud -> lose the amount. Lower is better."""
    return c_review * block.sum() + amount[(~block) & (y == 1)].sum()


def op_point(y, block):
    """precision / recall / alert-rate for a block decision."""
    if block.sum() == 0:
        return 0.0, 0.0, 0.0
    return (precision_score(y, block, zero_division=0), recall_score(y, block, zero_division=0), block.mean())


def summarise(name, y, amount, block, c_review):
    cost = realised_cost(y, amount, block, c_review)
    prec, rec, rate = op_point(y, block)
    print(f"  {name:<28} cost ${cost:>12,.0f}   alert {rate*100:5.2f}%   "
          f"precision {prec:5.3f}   recall {rec:5.3f}")
    return cost


def main():
    con = get_con()
    d = load_test_slice(con)
    y, p, amt = d.is_fraud.to_numpy(), d.fraud_proba.to_numpy(), d.amount.to_numpy()
    exposure = amt[y == 1].sum()                      # block-nothing worst case (total fraud $)
    print(f"holdout: {len(d):,} txns | fraud {y.mean()*100:.2f}% | fraud exposure ${exposure:,.0f}\n")

    # --- policy 1: naive 0.5 ---
    print(f"realised cost by policy (review = ${C_REVIEW:.0f}/flag):")
    summarise("block nothing", y, amt, np.zeros(len(y), bool), C_REVIEW)
    cost_naive = summarise("naive threshold 0.5", y, amt, p >= 0.5, C_REVIEW)

    # --- policy 2: cost-optimal global threshold ---
    ts = np.linspace(0.0, 1.0, 501)
    costs = np.array([realised_cost(y, amt, p >= t, C_REVIEW) for t in ts])
    t_star = ts[costs.argmin()]
    cost_opt = summarise(f"cost-optimal threshold t*={t_star:.3f}", y, amt, p >= t_star, C_REVIEW)

    # --- policy 3: amount-weighted expected-value ---
    block_ev = (p * amt) > C_REVIEW
    cost_ev = summarise("amount-weighted EV policy", y, amt, block_ev, C_REVIEW)

    save_naive = (cost_naive - cost_ev) / cost_naive * 100
    save_exp = (exposure - cost_ev) / exposure * 100
    print(f"\n  amount-weighted EV vs naive-0.5:  ${cost_naive - cost_ev:,.0f} saved ({save_naive:.1f}%)")
    print(f"  amount-weighted EV vs block-nothing: {save_exp:.1f}% of fraud exposure recovered")

    # --- sensitivity: the review-cost assumption is arguable, so show t* moves with it ---
    print("\nsensitivity to the review-cost assumption:")
    print(f"  {'review $':>8} {'optimal t*':>11} {'EV-policy cost':>16}")
    for c in [1.0, 3.0, 5.0, 10.0]:
        cc = np.array([realised_cost(y, amt, p >= t, c) for t in ts])
        print(f"  {c:8.0f} {ts[cc.argmin()]:11.3f} {realised_cost(y, amt, (p*amt) > c, c):16,.0f}")

    # --- chart: cost vs threshold, with the three operating points marked ---
    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(ts, costs, color=INK, lw=1.8, label="global threshold")
    ax.scatter([0.5], [realised_cost(y, amt, p >= 0.5, C_REVIEW)], color=ALLOW, zorder=5, label="naive 0.5")
    ax.scatter([t_star], [cost_opt], color=MARK, zorder=5, label=f"cost-optimal t*={t_star:.3f}")
    ax.axhline(cost_ev, color=BLOCK, ls="--", lw=1.5, label="amount-weighted EV policy")
    ax.set_xlabel("block threshold on fraud probability")
    ax.set_ylabel("realised cost on holdout ($)")
    ax.set_title(f"Decision on cost, not on 0.5  (review = ${C_REVIEW:.0f}/flag)")
    ax.legend(fontsize=8, frameon=False)
    ax.ticklabel_format(axis="y", style="plain")
    fig.tight_layout()
    fig.savefig(f"{OUT}/cost_curve.png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"\nwrote {OUT}/cost_curve.png")

    # --- persist the amount-weighted decisions (the recommended policy) ---
    d = d.assign(
        expected_fraud_loss=(p * amt),
        decision=np.where(block_ev, "block", "allow"),
        realised_cost=np.where(block_ev, C_REVIEW, np.where(y == 1, amt, 0.0)),
    )
    write_table(con, d[["transaction_id", "fraud_proba", "amount",
                        "expected_fraud_loss", "decision", "realised_cost"]],
                "dbt_marts", "txn_decision")
    # self-check (house style: the mart must be well-formed, or the run fails loudly)
    bad = con.execute("""select count(*) from dbt_marts.txn_decision
        where decision not in ('block','allow') or expected_fraud_loss < 0
           or realised_cost < 0 or amount is null""").fetchone()[0]
    assert bad == 0, f"txn_decision has {bad} malformed rows"
    con.close()
    print("wrote dbt_marts.txn_decision  (check: 0 malformed rows)")


if __name__ == "__main__":
    main()
