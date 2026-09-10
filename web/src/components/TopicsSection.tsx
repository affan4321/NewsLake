"use client";

import { motion } from "motion/react";
import type { Topic } from "@/lib/db";
import SectionHeading from "./SectionHeading";

/*
 * The bars are driven by the parent row's variants rather than each having its own
 * `whileInView`. That is not a style preference — a bar starts at scaleX(0), which gives
 * it a zero-width bounding box, and IntersectionObserver never reports a zero-area
 * element as intersecting. Self-observing bars therefore deadlock: they can't grow
 * because they aren't visible, and aren't visible because they haven't grown.
 * Inheriting from the parent (which has a normal box) sidesteps that entirely.
 */
const ROW = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

export default function TopicsSection({ topics }: { topics: Topic[] }) {
  const max = Math.max(...topics.map((t) => t.articleCount), 1);

  return (
    <section id="topics" className="mx-auto w-full max-w-stage px-5 py-24 md:px-10 md:py-32">
      <SectionHeading eyebrow="What the world is talking about" title="Topics by volume">
        Every article carries one or more topic tags. Spark explodes those into a bridge
        table so a single article can count toward several topics at once — these are the
        busiest, ranked across all history.
      </SectionHeading>

      <div className="mt-14 space-y-3">
        {topics.map((topic, i) => {
          const ratio = topic.articleCount / max;
          const bar = {
            hidden: { scaleX: 0 },
            visible: { scaleX: ratio },
          };

          return (
            <motion.div
              key={topic.topic}
              variants={ROW}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
              className="group relative overflow-hidden rounded-xl border border-bone/10 bg-ink-2 px-5 py-4 transition-colors duration-300 hover:border-bone/25"
            >
              {/* Soft gradient body of the bar. */}
              <motion.div
                aria-hidden
                variants={bar}
                transition={{ duration: 0.9, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
                style={{ transformOrigin: "left" }}
                className="bg-medallion absolute inset-y-0 left-0 w-full opacity-25 transition-opacity duration-300 group-hover:opacity-40"
              />
              {/* Bright leading edge, so a short bar still reads as a bar. */}
              <motion.div
                aria-hidden
                variants={bar}
                transition={{ duration: 0.9, delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}
                style={{ transformOrigin: "left" }}
                className="bg-medallion absolute inset-y-0 left-0 w-full [mask-image:linear-gradient(to_right,transparent_calc(100%-2px),black_calc(100%-2px))]"
              />

              <div className="relative flex items-center justify-between gap-4">
                <div className="flex min-w-0 items-center gap-4">
                  <span className="font-mono text-[11px] text-muted tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="truncate text-sm font-medium text-bone md:text-base">
                    {topic.topic}
                  </span>
                </div>
                <div className="flex shrink-0 items-baseline gap-4">
                  <span className="font-mono text-[11px] text-muted">
                    {topic.uniqueSources} sources
                  </span>
                  <span className="display text-lg text-bone tabular-nums md:text-xl">
                    {topic.articleCount.toLocaleString()}
                  </span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
