"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Chat from "./Chat";

function ChatBubbleIcon() {
  return (
    <svg className="h-6 w-6 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M8 10h8M8 14h5M21 12c0 4.418-4.03 8-9 8-1.06 0-2.078-.163-3.023-.463L3 21l1.532-4.596C3.564 15.166 3 13.634 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"
      />
    </svg>
  );
}

const RING_DURATION = 4;
const RING_COUNT = 2;
/** How far each ring travels outward from every edge of the pill, in px. */
const RING_SPREAD = 64;
const RING_DELAYS = Array.from(
  { length: RING_COUNT },
  (_, i) => (i * RING_DURATION) / RING_COUNT,
);

/*
 * Ring timing. Position and opacity share ONE keyframe set on ONE `times` timeline:
 * split across per-property transitions they drift out of phase under
 * `repeat: Infinity`. Opacity starts and ends at 0 so the loop restart is invisible —
 * a non-zero first frame is what made a ring pop into existence each cycle.
 */
const RING_TIMES = [0, 0.12, 0.5, 1];
/**
 * Rings grow by pushing all four insets outward by equal PIXEL amounts, not by
 * `scale`. The pill is far wider than it is tall, so scaling it uniformly adds
 * proportionally more width than height and reads as a sideways stretch. Equal pixel
 * offsets keep the halo hugging the pill evenly the whole way around.
 *
 * Offsets are proportional to RING_TIMES so that, with `ease: "linear"`, travel is
 * genuinely constant-speed — no easeOut burst that makes a ring appear already-large.
 */
const RING_INSET = RING_TIMES.map((t) => -RING_SPREAD * t);

const SWAP = {
  initial: { opacity: 0, scale: 0.8 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.8 },
  transition: { duration: 0.15, ease: [0.22, 1, 0.36, 1] as const },
};

/*
 * Persistent bottom-right widget, present on every page. The launcher and the close
 * button are two separate elements that fade/scale in and out rather than one element
 * morphing between shapes — a width morph from a wide pill to a small circle reads as
 * a squash rather than a state change.
 *
 * The wrapper holds `min-h-14` so it keeps the launcher's height even while no button
 * is mounted mid-swap; without it the column collapses and the open panel jumps down.
 */
export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const reduceMotion = useReducedMotion();
  const showRings = !open && !reduceMotion;

  return (
    <div className="fixed right-5 bottom-5 z-50 flex flex-col items-end gap-3">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="w-[min(380px,calc(100vw-2.5rem))] origin-bottom-right"
          >
            <Chat onClose={() => setOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sizes itself to the launcher, so `inset-0` rings and the glow start exactly at
          the pill's outline. Both sit behind the button, which is lifted to z-10. */}
      <div className="relative flex min-h-14 items-center justify-end">
        {!open && (
          <div
            aria-hidden
            className="bg-signal/30 pointer-events-none absolute -inset-1 rounded-full blur-xl"
          />
        )}

        {showRings &&
          RING_DELAYS.map((delay) => (
            <motion.span
              key={delay}
              aria-hidden
              className="border-signal/60 pointer-events-none absolute rounded-full border-2"
              animate={{
                top: RING_INSET,
                right: RING_INSET,
                bottom: RING_INSET,
                left: RING_INSET,
                opacity: [0, 0.55, 0.3, 0],
              }}
              transition={{
                duration: RING_DURATION,
                repeat: Infinity,
                ease: "linear",
                delay,
                times: RING_TIMES,
              }}
            />
          ))}

        <AnimatePresence initial={false} mode="popLayout">
          {open ? (
            <motion.button
              key="close"
              {...SWAP}
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.94 }}
              className="bg-medallion relative z-10 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full text-ink shadow-signal"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeWidth={1.8} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </motion.button>
          ) : (
            <motion.button
              key="open"
              {...SWAP}
              onClick={() => setOpen(true)}
              aria-label="Open chat"
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              className="bg-medallion relative z-10 flex cursor-pointer items-center gap-3 rounded-full py-4 pr-5 pl-6 text-ink shadow-signal"
            >
              <span className="text-base font-semibold whitespace-nowrap">
                Chat to see live results
              </span>
              <ChatBubbleIcon />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
