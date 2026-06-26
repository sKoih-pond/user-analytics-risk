-- Transaction grain enriched with identity attributes. This is the single per-transaction
-- spine the marts aggregate from: transactions left-joined to the device / identity signals.
with t as (
    select * from {{ ref('stg_transactions') }}
),
i as (
    select * from {{ ref('stg_identity') }}
)
select
    t.transaction_id,
    t.client_id,
    t.is_fraud,
    t.event_ts,
    t.event_hour,
    t.amount,
    t.product_cd,
    t.card1,
    t.card2,
    t.card_network,
    t.card_type,
    t.addr1,
    t.p_emaildomain,
    t.r_emaildomain,
    t.c1, t.c2, t.c5, t.c13, t.c14,
    t.d1, t.d4, t.d10, t.d15,
    i.device_type,
    i.device_info,
    i.browser,
    (i.transaction_id is not null) as has_identity
from t
left join i using (transaction_id)
