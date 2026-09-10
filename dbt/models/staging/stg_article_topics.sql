select
    article_id,
    topic
from {{ source('raw', 'article_topics') }}
