-- Singular test of the tagging logic: every client must carry exactly one value tag and
-- exactly one lifecycle tag (risk tags can be many). Catches a CASE branch that produces
-- duplicates or gaps. Passes when this query returns zero rows.
select
    client_id,
    tag_family,
    count(*) as n_tags
from {{ ref('user_tags') }}
where tag_family in ('value', 'lifecycle')
group by client_id, tag_family
having count(*) <> 1
