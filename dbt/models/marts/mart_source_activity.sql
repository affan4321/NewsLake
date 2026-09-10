select
    published_date as date,
    source_id,
    source_name,
    count(*) as article_count
from {{ ref('fct_articles') }}
group by 1, 2, 3
