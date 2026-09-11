import { Reveal } from "./Reveal";

const DASHBOARD_URL = "https://newslake.streamlit.app";

/*
 * The Streamlit app is public too, but two of its features stay local-only by design:
 * they talk to MinIO and the Airflow API over Docker-internal hostnames with no route
 * from the public internet, so the hosted version shows a locked state for these
 * specifically rather than an error. Keep the "Local only" tags accurate if that ever
 * changes (e.g. if the API gets tunnelled).
 */
const PANELS = [
  {
    title: "Live pipeline view",
    body: "The Airflow DAG as an animated flow diagram, polling task states every few seconds — plus a button to trigger a run and the next scheduled run time.",
    localOnly: true,
  },
  {
    title: "Data Explorer",
    body: "A read-only browser for every storage layer: raw Bronze JSON straight out of object storage, Silver and Gold Parquet with full schemas, and both Postgres schemas.",
    localOnly: true,
  },
];

export default function CockpitSection() {
  return (
    <section className="mx-auto w-full max-w-stage px-5 py-24 md:px-10 md:py-32">
      <div className="relative overflow-hidden rounded-3xl border border-bone/12 bg-ink-2 p-8 md:p-14">
        <div
          aria-hidden
          className="bg-medallion pointer-events-none absolute -top-32 -right-32 h-72 w-72 rounded-full opacity-10 blur-[90px]"
        />

        <div className="relative grid gap-12 lg:grid-cols-[1.1fr_1fr] lg:gap-20">
          <div>
            <Reveal>
              <p className="eyebrow">The other half</p>
              <h2 className="display mt-4 text-3xl md:text-5xl">
                There is a <span className="medallion-text">cockpit</span> behind this
              </h2>
              <p className="mt-5 text-base leading-relaxed text-muted">
                This site is the public face of the lake. The operational side — watching a
                run execute, poking at raw files, checking a Parquet schema — lives in a
                companion Streamlit dashboard, also public.
              </p>
              <p className="mt-4 text-base leading-relaxed text-muted">
                It mirrors the same warehouse data shown above, plus a full walkthrough of
                every pipeline stage. Two panels below stay local-only by design: they
                reach MinIO and the Airflow API over Docker-internal hostnames that have no
                route from the public internet.
              </p>
            </Reveal>

            <Reveal delay={0.12}>
              <a
                href={DASHBOARD_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-8 inline-flex items-center gap-2 rounded-xl border border-signal/30 bg-signal/[0.08] px-6 py-3.5 text-sm font-semibold tracking-[0.06em] text-signal transition-colors duration-300 hover:bg-signal/15"
              >
                Open the dashboard
                <span aria-hidden>↗</span>
              </a>
            </Reveal>
          </div>

          <div className="space-y-4">
            {PANELS.map((panel, i) => (
              <Reveal key={panel.title} delay={0.1 + i * 0.08}>
                <div className="rounded-2xl border border-bone/10 bg-ink p-6 transition-colors duration-300 hover:border-signal/30">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-base font-medium text-bone">{panel.title}</h3>
                    {panel.localOnly ? (
                      <span className="shrink-0 rounded-full border border-gold/30 px-2.5 py-1 font-mono text-[10px] tracking-[0.12em] text-gold uppercase">
                        Local only
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{panel.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
