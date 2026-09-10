-- Singular test: fails if it returns any rows. Catches the "no negative counts"
-- invariant from the project's data-quality requirements.
select date, topic, article_count, unique_sources
from {{ ref('mart_topic_trends') }}
where article_count < 0 or unique_sources < 0
