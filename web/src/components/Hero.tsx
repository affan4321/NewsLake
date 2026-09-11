import type { Kpis } from "@/lib/db";
import Globe from "./Globe";
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
      {/* The globe sits behind everything, faded out near the top (where the headline
          sits) via a mask so it never fights text contrast, and faded into the page
          background at the bottom so it doesn't hard-cut into the next section. */}
      <div
        className="absolute inset-0"
        style={{
          maskImage: "linear-gradient(to bottom, transparent, black 30%, black 78%, transparent)",
          WebkitMaskImage:
            "linear-gradient(to bottom, transparent, black 30%, black 78%, transparent)",
        }}
      >
        <Globe />
      </div>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-ink to-transparent"
      />

      <div className="pointer-events-none relative mx-auto w-full max-w-stage">
        <Reveal>
          <div className="inline-flex items-center gap-2.5 rounded-full border border-signal/25 bg-signal/[0.06] py-1.5 pr-4 pl-3">
            {/* A little signal-strength meter instead of a plain pulsing dot. */}
            <span className="flex h-2.5 items-end gap-[3px]">
              <span
                className="w-[3px] animate-pulse rounded-full bg-signal"
                style={{ height: "40%", animationDelay: "0ms" }}
              />
              <span
                className="w-[3px] animate-pulse rounded-full bg-signal"
                style={{ height: "100%", animationDelay: "180ms" }}
              />
              <span
                className="w-[3px] animate-pulse rounded-full bg-signal"
                style={{ height: "65%", animationDelay: "360ms" }}
              />
            </span>
            <span className="eyebrow !text-signal">Live</span>
            <span className="h-3 w-px bg-bone/15" />
            <span className="eyebrow">from Neon · {freshness(kpis.latestPublished)}</span>
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
            <div className="pointer-events-auto flex flex-wrap items-center gap-4">
              <a
                href="#overview"
                className="bg-medallion inline-flex items-center gap-2 rounded-xl px-7 py-4 text-sm font-semibold tracking-[0.06em] text-ink shadow-signal transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-lift"
              >
                Explore the data
              </a>
              <a
                href="#pipeline"
                className="inline-flex items-center gap-2 rounded-xl border border-bone/25 px-7 py-4 text-sm tracking-[0.06em] text-bone transition-colors hover:border-signal hover:text-signal"
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
