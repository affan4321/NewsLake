import { Reveal } from "./Reveal";

/*
 * The internal-tools counterpart to this site. Deliberately framed as "runs locally",
 * because it genuinely cannot be reached from the public internet: it talks to MinIO
 * and the Airflow API over Docker-internal hostnames.
 */
const PANELS = [
  {
    title: "Live pipeline view",
    body: "The Airflow DAG rendered as an animated flow diagram, polling task states every few seconds — plus a button to trigger a run and the next scheduled run time.",
  },
  {
    title: "Data Explorer",
    body: "A read-only browser for every storage layer: raw Bronze JSON straight out of object storage, Silver and Gold Parquet with full schemas, and both Postgres schemas.",
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
                separate Streamlit app that runs against the local Docker stack.
              </p>
              <p className="mt-4 text-base leading-relaxed text-muted">
                It is not deployed anywhere, and that is deliberate: it reaches MinIO and
                the Airflow API over Docker-internal hostnames that have no route from the
                public internet. Two audiences, two tools, one warehouse underneath.
              </p>
            </Reveal>

            <Reveal delay={0.12}>
              <div className="mt-8 inline-flex items-center gap-3 rounded-full border border-bone/15 px-5 py-3 font-mono text-[11px] tracking-[0.16em] text-muted uppercase">
                <span className="h-1.5 w-1.5 rounded-full bg-gold" />
                docker compose up streamlit
              </div>
            </Reveal>
          </div>

          <div className="space-y-4">
            {PANELS.map((panel, i) => (
              <Reveal key={panel.title} delay={0.1 + i * 0.08}>
                <div className="rounded-2xl border border-bone/10 bg-ink p-6 transition-colors duration-300 hover:border-signal/30">
                  <h3 className="text-base font-medium text-bone">{panel.title}</h3>
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
