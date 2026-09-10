import type { Kpis } from "@/lib/db";
import { Reveal } from "./Reveal";

function freshness(iso: string | null) {
  if (!iso) return "awaiting first run";
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
  if (hours < 1) return "updated minutes ago";
  if (hours < 24) return `updated ${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `updated ${days}d ago`;
}

export default function Hero({ kpis }: { kpis: Kpis }) {
  return (
    <section
      id="top"
      className="grain relative flex min-h-[92svh] items-center overflow-hidden px-5 pt-32 pb-20 md:px-10"
    >
      {/* Ambient glows in two medallion tones. Kept modest in radius — very large
          blurred boxes force browsers to allocate big offscreen buffers. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-56 left-1/3 h-[22rem] w-[22rem] rounded-full bg-bronze/10 blur-[70px] md:h-[40rem] md:w-[40rem] md:blur-[140px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -bottom-64 h-[18rem] w-[18rem] rounded-full bg-signal/10 blur-[70px] md:h-[32rem] md:w-[32rem] md:blur-[140px]"
      />

      <div className="mx-auto w-full max-w-stage">
        <Reveal>
          <div className="flex items-center gap-3">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-signal opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-signal" />
            </span>
            <span className="eyebrow">Live from Neon — {freshness(kpis.latestPublished)}</span>
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <h1 className="display mt-7 text-[16vw] leading-[0.9] md:text-[9.5vw]">
            News<span className="medallion-text">Lake</span>
          </h1>
        </Reveal>

        <Reveal delay={0.16}>
          <p className="mt-6 font-mono text-xs uppercase tracking-[0.2em] md:text-sm">
            <span className="text-bronze">Bronze</span>
            <span className="mx-3 text-muted">/</span>
            <span className="text-silver">Silver</span>
            <span className="mx-3 text-muted">/</span>
            <span className="text-gold">Gold</span>
          </p>
        </Reveal>

        <div className="mt-10 flex flex-col gap-8 border-t border-bone/12 pt-8 md:flex-row md:items-end md:justify-between">
          <Reveal delay={0.24}>
            <p className="max-w-xl text-base leading-relaxed text-muted md:text-lg">
              A news lakehouse that runs itself. Every day, Airflow pulls fresh articles
              into object storage, Spark cleans and aggregates them through three
              medallion layers, dbt models the result, and everything below is read live
              from the warehouse — no static exports.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="flex flex-wrap items-center gap-4">
              <a
                href="#overview"
                className="bg-medallion inline-flex items-center gap-2 rounded-full px-7 py-4 text-sm font-semibold tracking-[0.06em] text-ink shadow-signal transition-transform duration-300 hover:scale-[1.04]"
              >
                Explore the data
              </a>
              <a
                href="#pipeline"
                className="inline-flex items-center gap-2 rounded-full border border-bone/25 px-7 py-4 text-sm tracking-[0.06em] text-bone transition-colors hover:border-signal hover:text-signal"
              >
                How it works
              </a>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
