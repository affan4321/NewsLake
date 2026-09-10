/*
 * Read-only query layer over the Neon-hosted `analytics` schema — the same marts dbt
 * builds at the end of the pipeline. Everything here runs server-side only (the Neon
 * driver is imported into server components / route handlers, never shipped to the
 * browser), so DATABASE_URL is never exposed.
 *
 * Note on the shape of the data: the pipeline currently has a single day of history,
 * so anything time-series-shaped is written to degrade gracefully — one day renders as
 * a single point, and the same query gets richer on its own as days accumulate. Don't
 * "fix" that by hardcoding a date range.
 */
import { neon } from "@neondatabase/serverless";

function client() {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error(
      "DATABASE_URL is not set. Copy the Neon connection string into web/.env.local (see .env.example).",
    );
  }
  return neon(url);
}

export type Kpis = {
  articles: number;
  sources: number;
  topics: number;
  days: number;
  latestPublished: string | null;
};

export async function getKpis(): Promise<Kpis> {
  const sql = client();
  const [row] = await sql`
    select
      count(*)::int                        as articles,
      count(distinct source_id)::int       as sources,
      count(distinct published_date)::int  as days,
      max(published_at)                    as latest_published
    from analytics.fct_articles
  `;
  const [t] = await sql`
    select count(distinct topic)::int as topics from analytics.mart_topic_trends
  `;
  return {
    articles: row.articles,
    sources: row.sources,
    topics: t.topics,
    days: row.days,
    latestPublished: row.latest_published
      ? new Date(row.latest_published).toISOString()
      : null,
  };
}

export type Topic = { topic: string; articleCount: number; uniqueSources: number };

/** Topics ranked by volume, aggregated across every day the pipeline has seen. */
export async function getTopTopics(limit = 12): Promise<Topic[]> {
  const sql = client();
  const rows = await sql`
    select
      topic,
      sum(article_count)::int   as article_count,
      max(unique_sources)::int  as unique_sources
    from analytics.mart_topic_trends
    group by topic
    order by article_count desc
    limit ${limit}
  `;
  return rows.map((r) => ({
    topic: r.topic,
    articleCount: r.article_count,
    uniqueSources: r.unique_sources,
  }));
}

export type Source = { sourceId: string; sourceName: string; articleCount: number };

export async function getTopSources(limit = 10): Promise<Source[]> {
  const sql = client();
  const rows = await sql`
    select
      source_id,
      max(source_name)         as source_name,
      sum(article_count)::int  as article_count
    from analytics.mart_source_activity
    group by source_id
    order by article_count desc
    limit ${limit}
  `;
  return rows.map((r) => ({
    sourceId: r.source_id,
    sourceName: r.source_name,
    articleCount: r.article_count,
  }));
}

export type Article = {
  articleId: string;
  title: string;
  description: string | null;
  url: string;
  sourceName: string;
  publishedAt: string;
  thumbnailUrl: string | null;
};

export async function getRecentArticles(limit = 12): Promise<Article[]> {
  const sql = client();
  const rows = await sql`
    select article_id, title, description, url, source_name, published_at, thumbnail_url
    from analytics.fct_articles
    order by published_at desc
    limit ${limit}
  `;
  return rows.map((r) => ({
    articleId: r.article_id,
    title: r.title,
    description: r.description,
    url: r.url,
    sourceName: r.source_name,
    publishedAt: new Date(r.published_at).toISOString(),
    thumbnailUrl: r.thumbnail_url,
  }));
}

export type DailyVolume = { date: string; articles: number; sources: number };

/**
 * Per-day article volume. Reads as a single point today and becomes a real trend line
 * once the daily Airflow run has accumulated more days — no code change needed.
 */
export async function getDailyVolume(): Promise<DailyVolume[]> {
  const sql = client();
  const rows = await sql`
    select
      published_date::text            as date,
      count(*)::int                   as articles,
      count(distinct source_id)::int  as sources
    from analytics.fct_articles
    group by published_date
    order by published_date
  `;
  return rows.map((r) => ({
    date: r.date,
    articles: r.articles,
    sources: r.sources,
  }));
}
