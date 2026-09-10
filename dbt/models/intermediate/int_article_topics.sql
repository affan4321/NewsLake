-- One row per (article, topic) mention, with source attached -- the grain mart_topic_trends aggregates from.
select
    t.article_id,
    t.topic,
    a.published_at,
    a.published_at::date as published_date,
    a.source_id,
    s.source_name
from {{ ref('stg_article_topics') }} t
inner join {{ ref('stg_articles') }} a on t.article_id = a.article_id
left join {{ ref('stg_sources') }} s on a.source_id = s.source_id
