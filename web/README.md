# NewsLake — web

The public-facing site for [NewsLake](../README.md), a news data lakehouse. Next.js 16 (App
Router) + React 19 + Tailwind 4 + `motion`, server-rendered straight from the `analytics` schema
in Neon Postgres — no separate API layer, no static exports. See the [root README](../README.md)
for how that data gets there (MinIO → Spark → Airflow → dbt → Neon).

## Setup

```bash
cp .env.example .env.local   # fill in DATABASE_URL, CHATBOT_DATABASE_URL, GROQ_API_KEY, REVALIDATE_SECRET
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Env vars (`.env.local`, gitignored):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon connection string the page reads from (direct endpoint, not `-pooler`) |
| `CHATBOT_DATABASE_URL` | Read-only, `analytics`-schema-only connection used by the chat SQL tool |
| `GROQ_API_KEY` | Free key from [console.groq.com](https://console.groq.com), powers the chatbot |
| `REVALIDATE_SECRET` | Shared secret checked by `api/revalidate` — must match root `.env`'s value |

## Structure

```
src/
  app/
    page.tsx          entry point — fetches KPIs/topics/sources/articles, renders sections
    layout.tsx         fonts, metadata, mounts the global <ChatWidget />
    api/chat/route.ts        streaming chat endpoint (see below)
    api/revalidate/route.ts  called by the pipeline's DAG after a run, forces the homepage
                             cache to refresh instead of waiting up to an hour
    globals.css         design tokens: colors, .eyebrow/.display utilities, animations
  components/
    Hero, KpiStrip, TopicsSection, SourcesSection, ArticlesSection,
    PipelineSection, CockpitSection, Footer, Nav      page sections
    Globe                                              canvas globe in the hero (drag on desktop,
                                                        auto-tumbles on mobile — no drag gesture there,
                                                        it fights page scroll)
    ChatWidget, Chat                                   floating chat launcher + panel
  lib/
    db.ts          server-side data layer — one function per section, reads analytics.*
    chat-tools.ts  the chatbot's SQL tool + its system prompt
```

Page data fetching happens once per request in `page.tsx` (`Promise.all` of four `lib/db.ts`
calls) and is passed down as props — no client-side fetching for page content. `revalidate =
3600` in `page.tsx`: the pipeline only publishes once a day, so hourly is plenty fresh without
hitting Postgres on every visit. `app/api/revalidate/route.ts` is the escape hatch for that
cache — the Airflow DAG's last task calls it after a successful run so the homepage doesn't
have to wait out the hour on a manual/off-schedule run. See the root README's
[Web app](../README.md#web-app-public-site) section for the full wiring.

## The chatbot

The floating chat widget (bottom-right, every page) answers questions about the data by having
an LLM **write and run SQL directly** — not RAG. There's no vector search or document retrieval
here; the "knowledge" is a schema description in a system prompt, and the model generates a query
the same way it would generate any other code.

- `app/api/chat/route.ts` — a Next.js route calling `streamText()` from the
  [Vercel AI SDK](https://ai-sdk.dev), passing it one tool (`queryMarts`) and Groq's
  `openai/gpt-oss-120b` as the model. The SDK's default is to stop right after a tool call, so
  `stopWhen: stepCountIs(5)` is set explicitly to let the model read the query result and answer
  in words as a second step.
- `lib/chat-tools.ts` — `queryMarts` (the tool itself: takes a SQL string, runs it against Neon,
  returns rows) and `CHAT_SYSTEM_PROMPT` (the model's entire knowledge of the schema, plus static
  "about NewsLake" context so it can answer project questions without a query at all).
- `components/Chat.tsx` / `ChatWidget.tsx` — the UI, using `useChat` from `@ai-sdk/react` to
  stream the response in token-by-token.

**Guardrails** (three independent layers, so no single one has to be perfect):
1. Code rejects anything that isn't a single `SELECT` before it's sent anywhere.
2. The connection uses a dedicated `chatbot_reader` Postgres role, `SELECT`-only on the
   `analytics` schema — no `raw`, no writes, enforced by the database itself. See the root
   README's [Web app](../README.md#web-app-public-site) section for the exact SQL to recreate it.
3. That role has an 8-second `statement_timeout`.

**A gotcha, if you touch `chat-tools.ts`:** Postgres `timestamp` columns come back from the Neon
driver as native JS `Date` objects. Fine for the browser (`JSON.stringify` handles it), but the AI
SDK also replays a tool's raw return value into the model's *next* turn as a structured value —
and `Date` isn't valid there, which fails silently with no error reaching the user. The tool
round-trips its result through `JSON.parse(JSON.stringify(rows))` specifically to avoid this.

## Learn more

- [Next.js docs](https://nextjs.org/docs)
- [Vercel AI SDK docs](https://ai-sdk.dev/docs)
- [Groq](https://groq.com) — free-tier inference the chatbot runs on
