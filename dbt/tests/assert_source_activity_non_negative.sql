-- Singular test: fails if it returns any rows.
select date, source_id, article_count
from {{ ref('mart_source_activity') }}
where article_count < 0
