"""Airflow's silver_quality_checks task: fail the pipeline if Silver looks wrong.

Independent of bronze_to_silver's own logic -- re-verifies the invariants that job is
supposed to guarantee (no duplicate article_id, no nulls in required fields) rather than
just trusting it, plus a sanity check on how much data is landing in quarantine.
"""
import sys

from pyspark.sql import SparkSession, functions as F

SILVER_ARTICLES_PATH = "s3a://news-lakehouse/silver/articles/"
QUARANTINE_PATH = "s3a://news-lakehouse/quarantine/silver_validation/"
REQUIRED_FIELDS = ["article_id", "title", "url", "published_at"]
MAX_QUARANTINE_RATIO = 0.2


def fail(message: str):
    print(f"QUALITY CHECK FAILED: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    spark = SparkSession.builder.appName("newslake-silver-quality-checks").getOrCreate()

    articles = spark.read.parquet(SILVER_ARTICLES_PATH)
    article_count = articles.count()
    print(f"silver/articles row count: {article_count}")
    if article_count == 0:
        fail("silver/articles is empty")

    for field in REQUIRED_FIELDS:
        null_count = articles.where(F.col(field).isNull()).count()
        if null_count > 0:
            fail(f"{null_count} rows have a null {field}")

    duplicate_count = (
        articles.groupBy("article_id").count().where(F.col("count") > 1).count()
    )
    if duplicate_count > 0:
        fail(f"{duplicate_count} duplicate article_id values in silver/articles")

    try:
        quarantine_count = spark.read.json(QUARANTINE_PATH).count()
    except Exception:
        quarantine_count = 0  # no quarantine data written yet is fine
    total = article_count + quarantine_count
    quarantine_ratio = quarantine_count / total if total else 0
    print(f"quarantine ratio: {quarantine_ratio:.2%} ({quarantine_count}/{total})")
    if quarantine_ratio > MAX_QUARANTINE_RATIO:
        fail(f"quarantine ratio {quarantine_ratio:.2%} exceeds {MAX_QUARANTINE_RATIO:.0%} threshold")

    print("all quality checks passed")
    spark.stop()


if __name__ == "__main__":
    main()
