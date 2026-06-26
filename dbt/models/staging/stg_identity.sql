-- Typed identity grain from IEEE-CIS train_identity. One row per transaction that carries
-- device / network attributes. Joined to stg_transactions in int_transactions_enriched.
with i as (
    select * from {{ source('raw', 'identity') }}
)
select
    transactionid                                                     as transaction_id,
    devicetype                                                        as device_type,
    deviceinfo                                                        as device_info,
    id_31                                                             as browser,
    id_01::double                                                     as id_01,
    id_02::double                                                     as id_02
from i
