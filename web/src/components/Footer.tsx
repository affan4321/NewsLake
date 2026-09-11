import Logo from "./Logo";

const STACK = [
  "Python",
  "MinIO",
  "PySpark",
  "Airflow",
  "dbt",
  "Neon Postgres",
  "Next.js",
  "Streamlit",
];

export default function Footer() {
  return (
    <footer className="border-t border-bone/10 bg-ink">
      <div className="mx-auto w-full max-w-stage px-5 py-14 md:px-10">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <Logo className="h-6 w-6" />
              <span className="font-mono text-xs tracking-[0.18em] text-bone uppercase">
                NewsLake
              </span>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted">
              A news data lakehouse, built end to end — ingestion, transformation,
              orchestration, modelling, and serving.
            </p>
          </div>

          <div className="md:text-right">
            <p className="eyebrow">Built with</p>
            <ul className="mt-4 flex flex-wrap gap-2 md:justify-end">
              {STACK.map((item) => (
                <li
                  key={item}
                  className="rounded-full border border-bone/12 px-3 py-1.5 font-mono text-[11px] text-muted transition-colors duration-300 hover:border-bone/30 hover:text-bone"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-bone/10 pt-6 font-mono text-[11px] text-muted md:flex-row md:items-center md:justify-between">
          <span>Data refreshed daily by Airflow · served live from Neon</span>
          <a
            href="https://github.com/affan4321/NewsLake"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-bone"
          >
            github.com/affan4321/NewsLake
          </a>
        </div>
      </div>
    </footer>
  );
}
