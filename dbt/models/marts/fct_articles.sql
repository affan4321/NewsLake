select
    a.article_id,
    a.title,
    a.description,
    a.url,
    a.source_id,
    s.source_name,
    a.published_at,
    a.published_at::date as published_date,
    a.language,
    a.thumbnail_url
from {{ ref('stg_articles') }} a
left join {{ ref('stg_sources') }} s on a.source_id = s.source_id
