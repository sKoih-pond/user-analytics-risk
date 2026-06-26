-- Client-360 risk mart: behavioural features + RFM segment + tagging signals in one row
-- per client. This is the analytics-ready view the BI dashboard reads (segment overview,
-- tag effectiveness, fraud-rate by segment / tag) and the target of the dbt exposure.
with f as (
    select * from {{ ref('user_features') }}
),
seg as (
    select client_id, segment, rfm_score from {{ ref('user_segments') }}
),
val as (
    select client_id, tag as value_tag
    from {{ ref('user_tags') }} where tag_family = 'value'
),
life as (
    select client_id, tag as lifecycle_tag
    from {{ ref('user_tags') }} where tag_family = 'lifecycle'
),
risk as (
    select
        client_id,
        max(case when tag = 'confirmed_fraud' then 1 else 0 end) as is_confirmed_fraud,
        max(case when tag = 'multi_identity'  then 1 else 0 end) as is_multi_identity,
        max(case when tag = 'high_velocity'   then 1 else 0 end) as is_high_velocity
    from {{ ref('user_tags') }} where tag_family = 'risk'
    group by client_id
)
select
    f.client_id,
    f.n_txn,
    f.frequency,
    f.monetary,
    f.avg_amount,
    f.max_amount,
    f.n_products,
    f.n_devices,
    f.n_emails,
    f.n_browsers,
    f.pct_identity,
    f.tenure_days,
    f.recency_days,
    f.n_fraud,
    f.fraud_rate,
    seg.segment,
    seg.rfm_score,
    val.value_tag,
    life.lifecycle_tag,
    coalesce(risk.is_confirmed_fraud, 0) as is_confirmed_fraud,
    coalesce(risk.is_multi_identity, 0)  as is_multi_identity,
    coalesce(risk.is_high_velocity, 0)   as is_high_velocity
from f
left join seg  on f.client_id = seg.client_id
left join val  on f.client_id = val.client_id
left join life on f.client_id = life.client_id
left join risk on f.client_id = risk.client_id
