import SectionHeading from "./SectionHeading";
import { Reveal } from "./Reveal";

/*
 * The stages below describe what the pipeline actually does — not a generic medallion
 * explainer. If a Spark job or dbt model changes, update the matching `points` here.
 *
 * Class names are written out in full rather than composed at runtime: Tailwind scans
 * source text for literal class strings, so a template like `hover:${stage.ring}` would
 * never get generated into the stylesheet.
 */
const STAGES = [
  {
    layer: "Bronze",
    tone: "text-bronze",
    ring: "hover:border-bronze/40",
    glow: "bg-bronze",
    title: "Raw ingestion",
    body: "The article exactly as the API returned it, written to MinIO as JSON and partitioned by ingest time. Nothing is cleaned here — Bronze exists so any downstream bug can be replayed against the original response.",
    points: [
      "Python ingestion hits the listing endpoint, then enriches each article",
      "Rate-limited to stay inside the free API's daily budget",
      "Partitioned source / year / month / day / hour",
    ],
  },
  {
    layer: "Silver",
    tone: "text-silver",
    ring: "hover:border-silver/40",
    glow: "bg-silver",
    title: "Cleaned & validated",
    body: "PySpark flattens the nested JSON into a typed, article-grain table, drops rows that fail validation into a quarantine path, and deduplicates so a re-run can't double-count.",
    points: [
      "Rows missing an id, title, url or timestamp are quarantined, not silently dropped",
      "Stable source_id = ASCII slug + hash, so non-Latin publishers stay distinct",
      "Written as Snappy-compressed Parquet",
    ],
  },
  {
    layer: "Gold",
    tone: "text-gold",
    ring: "hover:border-gold/40",
    glow: "bg-gold",
    title: "Aggregated metrics",
    body: "Business-level rollups computed once, so the dashboard never pays for a full scan: daily article and source metrics, topic trends, and publishing activity.",
    points: [
      "Topics pre-exploded before counting distinct sources",
      "Four aggregate tables, each rewritten per run",
      "Independent quality checks gate the run before it proceeds",
    ],
  },
  {
    layer: "Warehouse",
    tone: "text-signal",
    ring: "hover:border-signal/40",
    glow: "bg-signal",
    title: "Postgres + dbt",
    body: "Spark lands article-grain data in a raw schema on Neon, then dbt builds staging, intermediate and mart models on top — with 22 tests that fail the run if the data is wrong.",
    points: [
      "Loader truncates rather than drops, so dependent dbt views survive",
      "unique / not_null / relationships / accepted_values tests",
      "The marts behind this page are the dbt output, read live",
    ],
  },
];

export default function PipelineSection() {
  return (
    <section
      id="pipeline"
      className="grain relative overflow-hidden border-t border-bone/10 bg-ink-2/50"
    >
      <div className="mx-auto w-full max-w-stage px-5 py-24 md:px-10 md:py-32">
        <SectionHeading eyebrow="How it works" title="Four layers, once a day">
          Airflow runs the whole chain on a schedule — fetch, validate, transform, check,
          aggregate, load, model, test. If any step fails its quality gate, the run stops
          there rather than publishing bad data.
        </SectionHeading>

        <div className="mt-14 grid gap-5 md:grid-cols-2">
          {STAGES.map((stage, i) => (
            <Reveal key={stage.layer} delay={i * 0.07}>
              <div
                className={`group relative h-full overflow-hidden rounded-2xl border border-bone/10 bg-ink p-7 transition-all duration-300 hover:-translate-y-1 ${stage.ring}`}
              >
                <div
                  aria-hidden
                  className={`pointer-events-none absolute -top-24 -right-24 h-48 w-48 rounded-full ${stage.glow} opacity-[0.07] blur-[60px] transition-opacity duration-500 group-hover:opacity-20`}
                />

                <div className="relative flex items-baseline gap-3">
                  <span className="font-mono text-[11px] text-muted tabular-nums">
                    0{i + 1}
                  </span>
                  <span
                    className={`font-mono text-[11px] tracking-[0.24em] uppercase ${stage.tone}`}
                  >
                    {stage.layer}
                  </span>
                </div>

                <h3 className="display relative mt-4 text-2xl text-bone">{stage.title}</h3>
                <p className="relative mt-3 text-sm leading-relaxed text-muted">
                  {stage.body}
                </p>

                <ul className="relative mt-5 space-y-2 border-t border-bone/10 pt-5">
                  {stage.points.map((point) => (
                    <li key={point} className="flex gap-3 text-sm leading-relaxed text-bone/75">
                      <span className={`mt-2 h-1 w-1 shrink-0 rounded-full ${stage.glow}`} />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
