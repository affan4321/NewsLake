select
    published_date as date,
    topic,
    count(distinct article_id) as article_count,
    count(distinct source_id) as unique_sources
from {{ ref('int_article_topics') }}
group by 1, 2
