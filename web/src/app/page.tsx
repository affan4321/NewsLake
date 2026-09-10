import {
  getKpis,
  getRecentArticles,
  getTopSources,
  getTopTopics,
} from "@/lib/db";
import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import KpiStrip from "@/components/KpiStrip";
import TopicsSection from "@/components/TopicsSection";
import SourcesSection from "@/components/SourcesSection";
import ArticlesSection from "@/components/ArticlesSection";
import PipelineSection from "@/components/PipelineSection";
import CockpitSection from "@/components/CockpitSection";
import Footer from "@/components/Footer";
import SectionHeading from "@/components/SectionHeading";

/*
 * Revalidate hourly. The pipeline only publishes once a day, so per-request queries
 * would be wasted work — but an hour is short enough that the page is never visibly
 * stale after a run lands.
 */
export const revalidate = 3600;

export default async function Home() {
  // One round trip instead of four sequential ones.
  const [kpis, topics, sources, articles] = await Promise.all([
    getKpis(),
    getTopTopics(12),
    getTopSources(10),
    getRecentArticles(12),
  ]);

  return (
    <>
      <Nav />
      <main className="flex-1">
        <Hero kpis={kpis} />

        <section id="overview" className="mx-auto w-full max-w-stage px-5 pb-8 md:px-10">
          <SectionHeading eyebrow="At a glance" title="What is in the lake">
            Counted straight from the warehouse at page build time — not a figure typed
            into the markup.
          </SectionHeading>
          <div className="mt-12">
            <KpiStrip kpis={kpis} />
          </div>
        </section>

        <TopicsSection topics={topics} />
        <SourcesSection sources={sources} totalSources={kpis.sources} />
        <ArticlesSection articles={articles} />
        <PipelineSection />
        <CockpitSection />
      </main>
      <Footer />
    </>
  );
}
