-- Typed transaction grain from IEEE-CIS. One row per transaction.
-- A "client" (user proxy) is approximated by card1 + addr1 — IEEE-CIS has no explicit
-- user id; this is the standard community approximation (documented as an assumption).
with t as (
    select * from {{ source('raw', 'transactions') }}
)
select
    transactionid                                                     as transaction_id,
    isfraud::int                                                      as is_fraud,
    -- TransactionDT is seconds from a reference date (~2017-12-01 per the Kaggle community).
    -- Approximate timestamp for recency/lifecycle; relative ordering is exact.
    (timestamp '2017-12-01' + to_seconds(transactiondt::bigint))      as event_ts,
    transactionamt::numeric                                           as amount,
    productcd                                                         as product_cd,
    card1,
    card4                                                             as card_network,
    card6                                                             as card_type,
    addr1,
    p_emaildomain,
    r_emaildomain,
    c1, c2, c5, c13, c14,
    d1, d4, d10, d15,
    devicetype,
    deviceinfo,
    id_31                                                             as browser,
    (card1::varchar || '-' || coalesce(addr1::varchar, 'NA'))         as client_id
from t
