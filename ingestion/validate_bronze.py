"""Airflow's validate_raw_data task: fail the pipeline if today's ingestion run wrote nothing.

Checks the whole day's bronze partition (not just the current hour) so it's robust to
whatever time the DAG actually ran at.
"""
import os
import sys
from datetime import datetime, timezone

import boto3
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ROOT_USER = os.environ["MINIO_ROOT_USER"]
MINIO_ROOT_PASSWORD = os.environ["MINIO_ROOT_PASSWORD"]
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "news-lakehouse")


def main():
    today = datetime.now(timezone.utc)
    prefix = f"bronze/source=freenewsapi/year={today:%Y}/month={today:%m}/day={today:%d}/"

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
    )
    response = s3.list_objects_v2(Bucket=MINIO_BUCKET, Prefix=prefix)
    count = response.get("KeyCount", 0)

    if count == 0:
        print(f"VALIDATION FAILED: no bronze objects found under {prefix}", file=sys.stderr)
        sys.exit(1)

    print(f"validated {count} bronze objects under {prefix}")


if __name__ == "__main__":
    main()
