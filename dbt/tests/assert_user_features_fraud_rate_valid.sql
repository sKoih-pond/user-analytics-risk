-- Singular test: fraud_rate is a share, so it must lie in [0, 1] for every client.
-- The test passes when this query returns zero rows.
select
    client_id,
    fraud_rate
from {{ ref('user_features') }}
where fraud_rate < 0
   or fraud_rate > 1
   or fraud_rate is null
