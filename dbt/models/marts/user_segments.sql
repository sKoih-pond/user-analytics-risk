-- RFM segmentation in SQL: quintile-score each client on Recency, Frequency, Monetary,
-- then band the combined score into named segments. Deterministic and adapter-portable
-- (NTILE works on DuckDB and BigQuery), so it is the segmentation the dashboard relies on.
-- A KMeans clustering alternative lives in src/segmentation.py (writes user_segments_kmeans).
with f as (
    select * from {{ ref('user_features') }}
),
scored as (
    select
        client_id,
        recency_days,
        frequency,
        monetary,
        fraud_rate,
        -- most recent (smallest recency) scores 5; highest frequency / monetary score 5
        ntile(5) over (order by recency_days desc) as r,
        ntile(5) over (order by frequency asc)     as f,
        ntile(5) over (order by monetary asc)      as m
    from f
),
banded as (
    select
        *,
        (r + f + m) as rfm_score
    from scored
)
select
    client_id,
    r,
    f,
    m,
    rfm_score,
    case
        when rfm_score >= 13 then 'Champions'
        when rfm_score >= 10 then 'Loyal'
        when rfm_score >= 7  then 'Potential'
        when rfm_score >= 5  then 'At Risk'
        else 'Hibernating'
    end as segment
from banded
