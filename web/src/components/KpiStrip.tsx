import type { Kpis } from "@/lib/db";
import Counter from "./Counter";
import { Reveal } from "./Reveal";

export default function KpiStrip({ kpis }: { kpis: Kpis }) {
  const items = [
    { label: "Articles", value: kpis.articles, hint: "rows in fct_articles", accent: "text-bone" },
    { label: "Sources", value: kpis.sources, hint: "distinct publishers", accent: "text-silver" },
    { label: "Topics", value: kpis.topics, hint: "tracked categories", accent: "text-gold" },
    {
      label: kpis.days === 1 ? "Day of history" : "Days of history",
      value: kpis.days,
      hint: "grows once per run",
      accent: "text-bronze",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-bone/12 bg-bone/12 lg:grid-cols-4">
      {items.map((item, i) => (
        <Reveal key={item.label} delay={i * 0.06} className="bg-ink-2">
          <div className="group h-full px-6 py-8 transition-colors duration-300 hover:bg-slate/40">
            <p className="eyebrow">{item.label}</p>
            <p className={`display mt-3 text-4xl md:text-5xl ${item.accent}`}>
              <Counter to={item.value} />
            </p>
            <p className="mt-2 font-mono text-[11px] text-muted">{item.hint}</p>
          </div>
        </Reveal>
      ))}
    </div>
  );
}
