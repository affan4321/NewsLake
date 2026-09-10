"""Silver -> Postgres raw schema: lands article-grain data for dbt to build on.

Writes scalar columns only -- `topics` gets exploded into a separate article_topics
bridge table instead of written as a native Postgres array, to sidestep JDBC array-type
mapping issues entirely. `authors` is dropped here: no dashboard section needs it, so it
stays lake-only (still in silver/articles for anyone who wants it later).

Full overwrite each run, same as bronze_to_silver/silver_to_gold -- no incremental merge
until Stage 7.
"""
import os

from pyspark.sql import SparkSession, functions as F

SILVER_ARTICLES_PATH = "s3a://news-lakehouse/silver/articles/"
SILVER_SOURCES_PATH = "s3a://news-lakehouse/silver/sources/"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "newslake")
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_SSLMODE = os.environ.get("POSTGRES_SSLMODE")  # unset for local postgres, "require" for Neon
JDBC_URL = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
if POSTGRES_SSLMODE:
    JDBC_URL += f"?sslmode={POSTGRES_SSLMODE}"


def write_table(df, table_name):
    (
        df.write.format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", table_name)
        .option("user", POSTGRES_USER)
        .option("password", POSTGRES_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        # truncate (not drop+recreate): dbt's staging views select from these tables,
        # and a DROP TABLE fails once anything depends on it. TRUNCATE keeps the table
        # object intact so those views survive a reload. Only safe because our schema
        # is stable across runs -- if columns ever change, this needs a real migration.
        .option("truncate", "true")
        .mode("overwrite")
        .save()
    )
    print(f"wrote {df.count()} rows to {table_name}")


def main():
    spark = SparkSession.builder.appName("newslake-load-to-postgres").getOrCreate()

    silver_articles = spark.read.parquet(SILVER_ARTICLES_PATH)
    silver_sources = spark.read.parquet(SILVER_SOURCES_PATH)

    articles = silver_articles.select(
        "article_id", "title", "description", "content", "url",
        "source_id", "source_name", "published_at", "language",
        "thumbnail_url", "ingested_at", "run_id",
    )
    write_table(articles, "raw.articles")

    write_table(silver_sources, "raw.sources")

    article_topics = (
        silver_articles.select("article_id", F.explode("topics").alias("topic"))
    )
    write_table(article_topics, "raw.article_topics")

    spark.stop()


if __name__ == "__main__":
    main()
