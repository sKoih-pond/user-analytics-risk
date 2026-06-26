-- Client-level (user-proxy) feature table: the spine for profiling, segmentation, tagging
-- and the user-level risk rollup. One row per client_id. Aggregated from the enriched
-- transaction grain. RFM building blocks (recency / frequency / monetary) are named here.
with t as (
    select * from {{ ref('int_transactions_enriched') }}
),
agg as (
    select
        client_id,
        count(*)                                  as n_txn,
        count(*)                                  as frequency,      -- RFM: F
        sum(amount)                               as total_amount,
        sum(amount)                               as monetary,       -- RFM: M
        avg(amount)                               as avg_amount,
        max(amount)                               as max_amount,
        count(distinct product_cd)               as n_products,
        count(distinct card_type)                as n_card_types,
        count(distinct p_emaildomain)            as n_emails,
        count(distinct device_info)              as n_devices,
        count(distinct browser)                  as n_browsers,
        avg(case when has_identity then 1 else 0 end) as pct_identity,
        min(event_ts)                            as first_ts,
        max(event_ts)                            as last_ts,
        sum(is_fraud)                            as n_fraud,
        avg(is_fraud)                            as fraud_rate,
        avg(c1)                                  as avg_c1,
        avg(c13)                                 as avg_c13,
        avg(c14)                                 as avg_c14
    from t
    group by client_id
)
select
    *,
    {{ dbt.datediff('first_ts', 'last_ts', 'day') }}                  as tenure_days,
    {{ dbt.datediff('last_ts', dbt.current_timestamp(), 'day') }}     as recency_days  -- RFM: R
from agg
