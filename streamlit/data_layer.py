"""Shared read access to every storage layer, for the Data Explorer pages.

Bronze/Silver/Gold live in MinIO (S3-compatible); raw/analytics live in Postgres.
Nothing here writes -- this is strictly a read-only inspection layer.
"""
import os

import boto3
import pandas as pd
from sqlalchemy import create_engine, text

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
# Optional (not required os.environ[...]): MinIO is local-only, so a cloud deployment of
# this app (Streamlit Community Cloud) won't have it configured or reachable. Missing
# credentials shouldn't crash the whole app on import -- only the Bronze/Silver/Gold
# Data Explorer tabs that actually need MinIO should fail, and only when used.
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "news-lakehouse")
MINIO_CONFIGURED = bool(MINIO_ROOT_USER and MINIO_ROOT_PASSWORD)
# MinIO and Airflow are only ever configured together, in the local docker-compose stack --
# a cloud deployment (Streamlit Community Cloud) never has either. So "is MinIO configured"
# doubles as "are we running locally", used to decide whether to attempt live
# MinIO/Airflow features at all versus showing a locked-feature message outright.
IS_LOCAL_ENV = MINIO_CONFIGURED

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "newslake")
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_SSLMODE = os.environ.get("POSTGRES_SSLMODE")  # unset for local postgres, "require" for Neon

S3_STORAGE_OPTIONS = {
    "key": MINIO_ROOT_USER,
    "secret": MINIO_ROOT_PASSWORD,
    "client_kwargs": {"endpoint_url": f"http://{MINIO_ENDPOINT}"},
}


def s3_client():
    if not MINIO_CONFIGURED:
        raise RuntimeError("MinIO isn't configured (MINIO_ROOT_USER/MINIO_ROOT_PASSWORD not set) -- Bronze/Silver/Gold aren't available in this deployment.")
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ROOT_USER,
        aws_secret_access_key=MINIO_ROOT_PASSWORD,
    )


def list_prefixes(prefix: str) -> list[str]:
    """One level of 'subfolders' under an S3 prefix (uses Delimiter='/' for drill-down UIs)."""
    resp = s3_client().list_objects_v2(Bucket=MINIO_BUCKET, Prefix=prefix, Delimiter="/")
    return [p["Prefix"] for p in resp.get("CommonPrefixes", [])]


def list_objects(prefix: str, max_keys: int = 200) -> list[dict]:
    resp = s3_client().list_objects_v2(Bucket=MINIO_BUCKET, Prefix=prefix, MaxKeys=max_keys)
    return resp.get("Contents", [])


def read_object_text(key: str) -> str:
    obj = s3_client().get_object(Bucket=MINIO_BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def read_parquet_table(prefix: str) -> pd.DataFrame:
    """Reads every Parquet file under an S3 prefix as one DataFrame (Silver/Gold tables)."""
    if not MINIO_CONFIGURED:
        raise RuntimeError("MinIO isn't configured (MINIO_ROOT_USER/MINIO_ROOT_PASSWORD not set) -- Bronze/Silver/Gold aren't available in this deployment.")
    return pd.read_parquet(f"s3://{MINIO_BUCKET}/{prefix}", storage_options=S3_STORAGE_OPTIONS)


def get_pg_engine():
    url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    if POSTGRES_SSLMODE:
        url += f"?sslmode={POSTGRES_SSLMODE}"
    return create_engine(url)


def list_pg_tables(schema: str) -> list[str]:
    sql = text("select table_name from information_schema.tables where table_schema = :schema order by table_name")
    with get_pg_engine().connect() as conn:
        return [row[0] for row in conn.execute(sql, {"schema": schema})]


def read_pg_table(schema: str, table: str, limit: int = 200) -> pd.DataFrame:
    with get_pg_engine().connect() as conn:
        return pd.read_sql(text(f'select * from "{schema}"."{table}" limit :limit'), conn, params={"limit": limit})


def pg_row_count(schema: str, table: str) -> int:
    with get_pg_engine().connect() as conn:
        return conn.execute(text(f'select count(*) from "{schema}"."{table}"')).scalar()
