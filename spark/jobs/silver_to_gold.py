"""Silver -> Gold: daily analytical aggregates.

Reads silver/articles/ and writes four small aggregate tables to gold/. Unlike the
partitioned Silver Parquet, Gold tables stay unpartitioned single files -- daily-grain
aggregates are tiny even over years of history, so partitioning would just create
small-file overhead for no benefit.

entity_trends (from the original proposal) is deferred -- it needs NER extraction from
article text, which is a separate NLP step not yet built.
"""
from pyspark.sql import SparkSession, functions as F

SILVER_ARTICLES_PATH = "s3a://news-lakehouse/silver/articles/"
GOLD_DAILY_ARTICLE_METRICS_PATH = "s3a://news-lakehouse/gold/daily_article_metrics/"
GOLD_DAILY_SOURCE_METRICS_PATH = "s3a://news-lakehouse/gold/daily_source_metrics/"
GOLD_TOPIC_TRENDS_PATH = "s3a://news-lakehouse/gold/topic_trends/"
GOLD_ARTICLE_ACTIVITY_PATH = "s3a://news-lakehouse/gold/article_activity/"


def write_gold(df, path):
    df.coalesce(1).write.mode("overwrite").option("compression", "snappy").parquet(path)


def main():
    spark = SparkSession.builder.appName("newslake-silver-to-gold").getOrCreate()

    articles = spark.read.parquet(SILVER_ARTICLES_PATH).withColumn("date", F.to_date("published_at"))
    articles.cache()
    print(f"silver/articles rows read: {articles.count()}")

    daily_topic_counts = (
        articles.select("date", F.explode_outer("topics").alias("topic"))
        .groupBy("date")
        .agg(F.countDistinct("topic").alias("distinct_topic_count"))
    )
    daily_article_metrics = (
        articles.groupBy("date")
        .agg(
            F.count("article_id").alias("article_count"),
            F.countDistinct("source_id").alias("distinct_source_count"),
        )
        .join(daily_topic_counts, on="date", how="left")
    )
    write_gold(daily_article_metrics, GOLD_DAILY_ARTICLE_METRICS_PATH)
    print(f"gold/daily_article_metrics rows: {daily_article_metrics.count()}")

    daily_source_metrics = articles.groupBy("date", "source_id", "source_name").agg(
        F.count("article_id").alias("article_count")
    )
    write_gold(daily_source_metrics, GOLD_DAILY_SOURCE_METRICS_PATH)
    print(f"gold/daily_source_metrics rows: {daily_source_metrics.count()}")

    topic_trends = (
        articles.withColumn("topic", F.explode("topics"))
        .groupBy("date", "topic")
        .agg(
            F.count("article_id").alias("article_count"),
            F.countDistinct("source_id").alias("unique_sources"),
        )
    )
    write_gold(topic_trends, GOLD_TOPIC_TRENDS_PATH)
    print(f"gold/topic_trends rows: {topic_trends.count()}")

    article_activity = (
        articles.withColumn("hour", F.hour("published_at"))
        .groupBy("date", "hour")
        .agg(F.count("article_id").alias("article_count"))
    )
    write_gold(article_activity, GOLD_ARTICLE_ACTIVITY_PATH)
    print(f"gold/article_activity rows: {article_activity.count()}")

    spark.stop()


if __name__ == "__main__":
    main()
