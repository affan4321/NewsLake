import type { Article } from "@/lib/db";
import SectionHeading from "./SectionHeading";
import { Reveal } from "./Reveal";
import Thumbnail from "./Thumbnail";

function timeAgo(iso: string) {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 60) return `${Math.max(mins, 1)}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function ArticlesSection({ articles }: { articles: Article[] }) {
  return (
    <section id="latest" className="mx-auto w-full max-w-stage px-5 py-24 md:px-10 md:py-32">
      <SectionHeading eyebrow="Straight from the warehouse" title="Latest articles">
        The most recent rows in <code className="font-mono text-silver">fct_articles</code>,
        queried live on page load. Titles link out to the original publisher.
      </SectionHeading>

      <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {articles.map((article, i) => (
          <Reveal key={article.articleId} delay={(i % 3) * 0.06}>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex h-full flex-col overflow-hidden rounded-2xl border border-bone/10 bg-ink-2 transition-all duration-300 hover:-translate-y-1 hover:border-signal/40 hover:shadow-lift"
            >
              <div className="relative aspect-[16/9] overflow-hidden bg-slate/40">
                <Thumbnail src={article.thumbnailUrl} />
                <div className="absolute inset-0 bg-gradient-to-t from-ink-2 via-transparent to-transparent" />
              </div>

              <div className="flex flex-1 flex-col p-5">
                <div className="flex items-center gap-3 font-mono text-[11px] text-muted">
                  <span className="truncate text-silver">{article.sourceName}</span>
                  <span className="text-bone/20">·</span>
                  <span className="shrink-0">{timeAgo(article.publishedAt)}</span>
                </div>

                <h3 className="mt-3 line-clamp-3 text-base leading-snug font-medium text-bone transition-colors duration-300 group-hover:text-signal">
                  {article.title}
                </h3>

                {article.description ? (
                  <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted">
                    {article.description}
                  </p>
                ) : null}
              </div>
            </a>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
