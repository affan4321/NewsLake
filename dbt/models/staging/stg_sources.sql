select
    source_id,
    source_name
from {{ source('raw', 'sources') }}
