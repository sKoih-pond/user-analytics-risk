-- User-tagging system: one client maps to many tags across three families.
--   value:     vip / high / mid / low          (monetary, gated by frequency for vip)
--   lifecycle: active / dormant / new / one_off (recency + tenure)
--   risk:      confirmed_fraud / multi_identity / high_velocity / clean
-- Thresholds use NTILE(100) percentile ranks so the logic is adapter-portable (the Python
-- version in src/tagging.py used exact quantiles; the qualitative findings are unchanged).
with f as (
    select * from {{ ref('user_features') }}
),
pct as (
    select
        client_id,
        n_txn,
        recency_days,
        tenure_days,
        fraud_rate,
        n_devices,
        n_emails,
        ntile(100) over (order by monetary asc)              as monetary_pct,
        ntile(100) over (order by frequency asc)             as frequency_pct,
        ntile(100) over (order by coalesce(avg_c14, 0) asc)  as c14_pct
    from f
),
value_tags as (
    select
        client_id,
        cast('value' as varchar) as tag_family,
        case
            when monetary_pct >= 91 and frequency_pct >= 76 then 'vip'
            when monetary_pct >= 76 then 'high'
            when monetary_pct >= 51 then 'mid'
            else 'low'
        end as tag
    from pct
),
lifecycle_tags as (
    select
        client_id,
        cast('lifecycle' as varchar) as tag_family,
        case
            when n_txn <= 1 then 'one_off'
            when recency_days <= 30 then 'active'
            when recency_days <= 90 then 'dormant'
            when coalesce(tenure_days, 0) <= 30 then 'new'
            else 'dormant'
        end as tag
    from pct
),
risk_confirmed as (
    select client_id, cast('risk' as varchar) as tag_family, cast('confirmed_fraud' as varchar) as tag
    from pct where fraud_rate > 0
),
risk_multi as (
    select client_id, cast('risk' as varchar) as tag_family, cast('multi_identity' as varchar) as tag
    from pct where coalesce(n_devices, 0) >= 3 or coalesce(n_emails, 0) >= 3
),
risk_velocity as (
    select client_id, cast('risk' as varchar) as tag_family, cast('high_velocity' as varchar) as tag
    from pct where c14_pct >= 96
),
risk_any as (
    select client_id from risk_confirmed
    union select client_id from risk_multi
    union select client_id from risk_velocity
),
risk_clean as (
    select client_id, cast('risk' as varchar) as tag_family, cast('clean' as varchar) as tag
    from pct where client_id not in (select client_id from risk_any)
)
select * from value_tags
union all select * from lifecycle_tags
union all select * from risk_confirmed
union all select * from risk_multi
union all select * from risk_velocity
union all select * from risk_clean
