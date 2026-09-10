"""Fetch articles from freenewsapi.io and land them as raw JSON in the MinIO bronze layer.

Two calls per article: /v1/news lists recent article UUIDs (lightweight), then /v1/details
fetches the full payload (body, authors, topics, url) per UUID -- the listing alone doesn't
carry enough fields to build the Silver schema.

Bronze layout: s3://<bucket>/bronze/source=freenewsapi/year=YYYY/month=MM/day=DD/hour=HH/<article_id>.json
Each object is the untouched /v1/details payload plus an `_ingestion` metadata block
(run_id, ingested_at, source) -- no cleaning or reshaping happens here.
"""
import json
import math
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import boto3
import requests
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.environ["NEWS_API_KEY"]
NEWS_API_BASE_URL = os.environ.get("NEWS_API_BASE_URL", "https://api.freenewsapi.io/v1")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "news-lakehouse")

# freenewsapi.io returns 10 articles/page regardless of the page_size we request.
LISTING_PAGE_SIZE = 10
MAX_ARTICLES_PER_RUN = int(os.environ.get("MAX_ARTICLES_PER_RUN", "300"))
MIN_REQUEST_INTERVAL = 0.55   # API allows 2 req/sec; stay under with margin


class RateLimitedSession:
    """Wraps requests.Session and enforces the API's 2 req/sec limit between calls."""

    def __init__(self, api_key: str):
        self._session = requests.Session()
        self._session.headers.update({"x-api-key": api_key})
        self._last_request_at = 0.0

    def get(self, url: str, params: dict) -> dict:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        response = self._session.get(url, params=params, timeout=30)
        self._last_request_at = time.monotonic()

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 2))
            time.sleep(retry_after)
            return self.get(url, params)

        response.raise_for_status()
        return response.json()


def fetch_article_uuids(session: RateLimitedSession, limit: int) -> list[str]:
    """Paginate /v1/news until we have `limit` article UUIDs or the API runs out."""
    url = f"{NEWS_API_BASE_URL}/news"
    uuids = []
    cursor = None
    max_pages = math.ceil(limit / LISTING_PAGE_SIZE)

    for page_num in range(1, max_pages + 1):
        params = {"language": "en"}
        if cursor:
            params["cursor"] = cursor  # NB: request param is `cursor`, not `next_cursor` (that's the response field)

        payload = session.get(url, params)
        page_articles = payload.get("data") or []
        if not page_articles:
            break

        uuids.extend(a["uuid"] for a in page_articles)
        print(f"  listing page {page_num}: +{len(page_articles)} uuids (total {len(uuids)})")

        meta = payload.get("meta", {})
        cursor = meta.get("next_cursor")
        if not meta.get("has_more") or not cursor:
            break

    return uuids[:limit]


def fetch_article_details(session: RateLimitedSession, article_uuid: str) -> dict:
    url = f"{NEWS_API_BASE_URL}/details"
    payload = session.get(url, {"uuid": article_uuid})
    return payload["data"]


def write_bronze(s3, run_id: str, ingested_at: datetime, article: dict) -> str:
    partition = (
        f"bronze/source=freenewsapi/"
        f"year={ingested_at:%Y}/month={ingested_at:%m}/day={ingested_at:%d}/hour={ingested_at:%H}"
    )
    record = {
        "article": article,
        "_ingestion": {
            "run_id": run_id,
            "ingested_at": ingested_at.isoformat(),
            "source": "freenewsapi",
        },
    }
    key = f"{partition}/{article['uuid']}.json"
    s3.put_object(
        Bucket=MINIO_BUCKET,
        Key=key,
        Body=json.dumps(record).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def main():
    run_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc)
    session = RateLimitedSession(NEWS_API_KEY)

    print(f"[{run_id}] listing up to {MAX_ARTICLES_PER_RUN} articles from {NEWS_API_BASE_URL}/news")
    article_uuids = fetch_article_uuids(session, MAX_ARTICLES_PER_RUN)
    print(f"[{run_id}] found {len(article_uuids)} articles, fetching details for each")

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
    )

    written = 0
    for i, article_uuid in enumerate(article_uuids, start=1):
        article = fetch_article_details(session, article_uuid)
        write_bronze(s3, run_id, ingested_at, article)
        written += 1
        if i % 25 == 0 or i == len(article_uuids):
            print(f"  details {i}/{len(article_uuids)} written")

    total_requests = len(article_uuids) + math.ceil(len(article_uuids) / LISTING_PAGE_SIZE)
    print(f"[{run_id}] wrote {written} objects to s3://{MINIO_BUCKET}/bronze/source=freenewsapi/...")
    print(f"[{run_id}] used ~{total_requests} of today's 5000-request quota")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"API request failed: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
