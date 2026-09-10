import type { Source } from "@/lib/db";
import SectionHeading from "./SectionHeading";
import { Reveal } from "./Reveal";

export default function SourcesSection({
  sources,
  totalSources,
}: {
  sources: Source[];
  totalSources: number;
}) {
  return (
    <section
      id="sources"
      className="grain relative overflow-hidden border-y border-bone/10 bg-ink-2/50"
    >
      <div className="mx-auto w-full max-w-stage px-5 py-24 md:px-10 md:py-32">
        <SectionHeading eyebrow="Who is publishing" title="Most active sources">
          {totalSources.toLocaleString()} distinct publishers have appeared in the lake so
          far. Each gets a stable <code className="font-mono text-silver">source_id</code>{" "}
          derived from its name plus a hash — so publishers writing in non-Latin scripts
          stay distinct instead of collapsing together.
        </SectionHeading>

        <div className="mt-14 grid gap-3 md:grid-cols-2">
          {sources.map((source, i) => (
            <Reveal key={source.sourceId} delay={i * 0.04}>
              <div className="group flex items-center justify-between gap-4 rounded-xl border border-bone/10 bg-ink px-5 py-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-silver/40">
                <div className="flex min-w-0 items-center gap-4">
                  <span className="display w-8 shrink-0 text-lg text-muted transition-colors duration-300 group-hover:text-silver tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-bone md:text-base">
                      {source.sourceName}
                    </p>
                    <p className="truncate font-mono text-[11px] text-muted">
                      {source.sourceId}
                    </p>
                  </div>
                </div>
                <span className="display shrink-0 text-xl text-silver tabular-nums">
                  {source.articleCount.toLocaleString()}
                </span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
