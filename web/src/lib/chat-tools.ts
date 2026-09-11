import { tool } from "ai";
import { z } from "zod";
import { neon } from "@neondatabase/serverless";

/*
 * The chatbot's only tool: run a read-only SQL query against the `analytics` schema.
 *
 * Defense in depth, in order:
 *   1. This code rejects anything that isn't a single, plain SELECT before it's sent.
 *   2. Even if that check were bypassed, `chatbot_reader` (see the role created for this
 *      feature) has SELECT-only grants scoped to the `analytics` schema — no `raw`, no
 *      writes, no DDL. The database enforces this independently of the code below.
 *   3. `chatbot_reader` has a server-side statement_timeout, so a runaway query can't
 *      hang the connection.
 *
 * (1) exists to fail fast with a clear message instead of a generic Postgres permission
 * error — (2) is what actually makes this safe.
 */

const BLOCKED_KEYWORDS =
  /\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|execute|call|vacuum|into|pg_sleep|pg_read_file|pg_terminate_backend)\b/i;

function validateSelectOnly(sql: string): string | null {
  const trimmed = sql.trim().replace(/;+\s*$/, "");
  if (!/^select\b/i.test(trimmed)) {
    return "Only SELECT queries are allowed.";
  }
  if (trimmed.includes(";")) {
    return "Only a single statement is allowed.";
  }
  if (BLOCKED_KEYWORDS.test(trimmed)) {
    return "Query contains a disallowed keyword.";
  }
  return null;
}

function clampLimit(sql: string): string {
  return /\blimit\s+\d+/i.test(sql) ? sql : `${sql} LIMIT 200`;
}

// Trend/aggregate tables never carry huge text; fct_articles does (title/description/
// content) — truncate any long string cell so one wide row can't blow the context budget.
function truncateWideFields<T extends Record<string, unknown>>(rows: T[]): T[] {
  return rows.map((row) => {
    const copy = { ...row };
    for (const key in copy) {
      const value = copy[key];
      if (typeof value === "string" && value.length > 300) {
        copy[key] = (value.slice(0, 300) + "…") as T[Extract<keyof T, string>];
      }
    }
    return copy;
  });
}

export const queryMarts = tool({
  description:
    "Run a read-only SQL SELECT against the analytics schema (Postgres/Neon) to answer questions about NewsLake's article, topic, and source data. Only SELECT statements are permitted.",
  inputSchema: z.object({
    sql: z
      .string()
      .describe(
        "A single, read-only PostgreSQL SELECT statement against tables in the analytics schema (no schema prefix needed).",
      ),
  }),
  execute: async ({ sql }) => {
    const error = validateSelectOnly(sql);
    if (error) {
      return { error };
    }

    const url = process.env.CHATBOT_DATABASE_URL;
    if (!url) {
      return { error: "Chat database is not configured." };
    }

    try {
      const client = neon(url);
      const rows = await client.query(clampLimit(sql));
      return { rows: truncateWideFields(rows as Record<string, unknown>[]) };
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Query failed." };
    }
  },
});

export const CHAT_SYSTEM_PROMPT = `You are the NewsLake data assistant. You answer questions about the news articles, topics, and sources tracked by the NewsLake pipeline by querying its Postgres warehouse — never from prior knowledge, and never by guessing numbers.

You have one tool, queryMarts, which runs a single read-only SELECT against these tables in the "analytics" schema (query them unqualified, e.g. "fct_articles", not "analytics.fct_articles" — the search_path already points there):

- fct_articles(article_id, title, description, content, url, source_id, source_name, published_at, published_date, language, thumbnail_url)
  One row per article. "content" and "description" are long — only select them if the user actually needs the article text; otherwise select title/source_name/published_at/url.
- mart_topic_trends(date, topic, article_count, unique_sources)
  One row per (date, topic). A single article can count toward several topics.
- mart_source_activity(date, source_id, source_name, article_count)
  One row per (date, source).

Notes on the data:
- The pipeline has been running for a short time, so most queries will span very few distinct "date"/"published_date" values — don't assume a long history exists. If a trend question can't be answered because there's only one day of data, say so plainly instead of fabricating a trend.
- Topic and source names are free text from the source API — use ILIKE for matching rather than exact equality.
- Always answer using the actual rows returned by queryMarts. If a query returns nothing, say so instead of inventing an answer.
- Call queryMarts at most once per question. Don't re-run the same or a near-identical query a second time — use the result you already have.

How to talk:
- Write like a knowledgeable person chatting with someone, not a report generator. Full, natural sentences — contractions are fine, a little personality is fine.
- Never expose the SQL you ran, table/column names, or phrases like "querying the warehouse" — just answer the question the way a person who already knows the numbers would.
- Don't lead every answer with a bare number in bold or a rigid "X: Y" list format — weave the numbers into a sentence instead.
- Plain text only, no markdown at all (no **bold**, no "- " bullet lists, no headers) — the chat window can't render it, so it would show up as literal asterisks and dashes.
- Keep it brief — a couple of sentences is usually enough — but brief doesn't mean clipped or robotic.`;
