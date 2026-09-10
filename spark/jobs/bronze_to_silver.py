"""Bronze -> Silver: flatten, validate, dedupe, and write Parquet.

Reads every bronze JSON object under bronze/source=freenewsapi/, keeps one row per
article_id (latest ingested_at wins), and splits records into:
  - silver/articles/   (Parquet, partitioned by year/month/day of published_at)
  - silver/sources/    (Parquet, small dimension table, not partitioned)
  - quarantine/silver_validation/  (JSON, rows failing required-field checks)

This does a full recompute of Silver from all of Bronze every run (no incremental
merge yet) -- that's Stage 7 scope once a watermark exists to bound the Bronze read.
"""
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.window import Window

BRONZE_PATH = "s3a://news-lakehouse/bronze/source=freenewsapi/"
SILVER_ARTICLES_PATH = "s3a://news-lakehouse/silver/articles/"
SILVER_SOURCES_PATH = "s3a://news-lakehouse/silver/sources/"
QUARANTINE_PATH = "s3a://news-lakehouse/quarantine/silver_validation/"

REQUIRED_FIELDS = ["article_id", "title", "url", "published_at"]


def flatten(raw_df):
    return raw_df.select(
        F.col("article.uuid").alias("article_id"),
        F.trim(F.col("article.title")).alias("title"),
        F.col("article.incipit").alias("description"),
        F.col("article.body").alias("content"),
        F.col("article.original_url").alias("url"),
        F.col("article.authors").alias("authors"),
        F.trim(F.col("article.publisher")).alias("source_name"),
        F.lower(F.regexp_replace(F.trim(F.col("article.publisher")), "[^a-zA-Z0-9]+", "_")).alias("source_id"),
        F.to_timestamp(F.col("article.published_at")).alias("published_at"),
        F.col("article.languages").getItem(0).alias("language"),
        F.col("article.topics").alias("topics"),
        F.col("article.thumbnail").alias("thumbnail_url"),
        F.to_timestamp(F.col("_ingestion.ingested_at")).alias("ingested_at"),
        F.col("_ingestion.run_id").alias("run_id"),
    )


def split_valid_invalid(df):
    missing = [F.when(F.col(f).isNull(), F.lit(f)) for f in REQUIRED_FIELDS]
    reasons = F.array_except(F.array(*missing), F.array(F.lit(None).cast("string")))
    with_reasons = df.withColumn("_quarantine_reason", reasons)
    valid = with_reasons.where(F.size("_quarantine_reason") == 0).drop("_quarantine_reason")
    invalid = with_reasons.where(F.size("_quarantine_reason") > 0)
    return valid, invalid


def dedupe_latest(df):
    window = Window.partitionBy("article_id").orderBy(F.col("ingested_at").desc())
    return (
        df.withColumn("_rn", F.row_number().over(window))
        .where(F.col("_rn") == 1)
        .drop("_rn")
    )


def main():
    spark = SparkSession.builder.appName("newslake-bronze-to-silver").getOrCreate()

    raw_df = spark.read.option("recursiveFileLookup", "true").json(BRONZE_PATH)
    print(f"bronze rows read: {raw_df.count()}")

    flat_df = flatten(raw_df)
    valid_df, invalid_df = split_valid_invalid(flat_df)
    deduped_df = dedupe_latest(valid_df)

    articles_df = (
        deduped_df
        .withColumn("year", F.date_format("published_at", "yyyy"))
        .withColumn("month", F.date_format("published_at", "MM"))
        .withColumn("day", F.date_format("published_at", "dd"))
    )

    (
        articles_df.coalesce(4)
        .write.mode("overwrite")
        .partitionBy("year", "month", "day")
        .option("compression", "snappy")
        .parquet(SILVER_ARTICLES_PATH)
    )
    print(f"silver/articles rows written: {articles_df.count()}")

    sources_df = deduped_df.select("source_id", "source_name").distinct()
    sources_df.coalesce(1).write.mode("overwrite").option("compression", "snappy").parquet(SILVER_SOURCES_PATH)
    print(f"silver/sources rows written: {sources_df.count()}")

    invalid_count = invalid_df.count()
    if invalid_count > 0:
        invalid_df.coalesce(1).write.mode("append").json(QUARANTINE_PATH)
    print(f"quarantined rows: {invalid_count}")

    spark.stop()


if __name__ == "__main__":
    main()
