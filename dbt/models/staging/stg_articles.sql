select
    article_id,
    title,
    description,
    content,
    url,
    source_id,
    published_at,
    language,
    thumbnail_url,
    ingested_at
from {{ source('raw', 'articles') }}
