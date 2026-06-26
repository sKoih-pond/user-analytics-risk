-- Typed transaction grain from IEEE-CIS train_transaction. One row per transaction.
-- Pure typing / renaming + transaction-only derivations (event_ts, hour, client_id).
-- Identity attributes are added later in int_transactions_enriched from stg_identity.
with t as (
    select * from {{ source('raw', 'transactions') }}
)
select
    transactionid                                                     as transaction_id,
    isfraud::int                                                      as is_fraud,
    transactiondt::bigint                                             as transaction_dt,
    -- TransactionDT is seconds from a reference date (~2017-12-01 per the Kaggle community).
    -- Approximate timestamp for recency / lifecycle; relative ordering is exact.
    {{ dbt.dateadd('second', 'transactiondt::bigint', "cast('2017-12-01' as timestamp)") }}
                                                                      as event_ts,
    floor(mod(transactiondt::bigint, 86400) / 3600)::int              as event_hour,
    transactionamt::double                                            as amount,
    productcd                                                         as product_cd,
    card1,
    card2,
    card4                                                             as card_network,
    card6                                                             as card_type,
    addr1,
    p_emaildomain,
    r_emaildomain,
    c1, c2, c5, c13, c14,
    d1, d4, d10, d15,
    -- A "client" (user proxy): card1 + addr1. IEEE-CIS has no explicit user id; this is the
    -- standard community approximation, documented as an assumption throughout the project.
    (card1::varchar || '-' || coalesce(addr1::varchar, 'NA'))         as client_id
from t
