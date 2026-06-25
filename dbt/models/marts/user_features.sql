-- Client-level (user-proxy) feature table: spine for profiling, segmentation,
-- tagging and the user-level risk rollup. One row per client_id.
with t as (
    select * from {{ ref('stg_transactions') }}
)
select
    client_id,
    count(*)                                              as n_txn,
    count(*)                                              as frequency,          -- RFM
    sum(amount)                                           as total_amount,
    sum(amount)                                           as monetary,           -- RFM
    avg(amount)                                           as avg_amount,
    max(amount)                                           as max_amount,
    count(distinct product_cd)                            as n_products,
    count(distinct card_type)                             as n_card_types,
    count(distinct p_emaildomain)                         as n_emails,
    count(distinct deviceinfo)                            as n_devices,
    min(event_ts)                                         as first_ts,
    max(event_ts)                                         as last_ts,
    date_diff('day', min(event_ts), max(event_ts))        as tenure_days,
    date_diff('day', max(event_ts), current_timestamp)    as recency_days,       -- RFM
    sum(is_fraud)                                         as n_fraud,
    avg(is_fraud)                                         as fraud_rate,
    avg(c1)  as avg_c1,
    avg(c13) as avg_c13,
    avg(c14) as avg_c14
from t
group by client_id
