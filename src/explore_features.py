"""
Feature EDA that informed the modelling strategy (reproducible — not asserted).
Prints fraud rates by the documented feature families so the strategy is evidence-led.
"""
from db import get_con


def main():
    con = get_con(); q = lambda s: con.execute(s).df()
    show = lambda t, s: (print(f"\n=== {t} ==="), print(q(s).to_string(index=False)))

    show("fraud rate by product line",
         "select ProductCD, count(*) n, round(avg(isFraud),4) fraud from raw.transactions_identity group by 1 order by fraud desc")
    show("card type / network",
         "select card6, count(*) n, round(avg(isFraud),4) fraud from raw.transactions_identity group by 1 order by fraud desc")
    show("identity record present?",
         "select (DeviceType is not null) has_identity, count(*) n, round(avg(isFraud),4) fraud from raw.transactions_identity group by 1")
    show("top email domains (n>2000)",
         "select P_emaildomain, count(*) n, round(avg(isFraud),4) fraud from raw.transactions_identity group by 1 having count(*)>2000 order by fraud desc limit 8")
    show("hour of day (riskiest)",
         "select cast(floor((TransactionDT%86400)/3600) as int) hr, count(*) n, round(avg(isFraud),4) fraud from raw.transactions_identity group by 1 order by fraud desc limit 5")
    show("association count C1 by fraud",
         "select isFraud, round(avg(C1),1) avg_c1, round(quantile_cont(C1,0.99),0) p99 from raw.transactions_identity group by 1")
    show("card1 is too coarse a customer (distinct account-birthdays per card1)",
         """with t as (select card1, floor(TransactionDT/86400)-D1 b from raw.transactions_identity where D1 is not null)
            select round(avg(c),2) avg_accounts_per_card1 from (select card1, count(distinct b) c from t group by card1)""")
    con.close()


if __name__ == "__main__":
    main()
