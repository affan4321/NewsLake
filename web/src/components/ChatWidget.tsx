"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Chat from "./Chat";

function ChatBubbleIcon() {
  return (
    <svg className="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M8 10h8M8 14h5M21 12c0 4.418-4.03 8-9 8-1.06 0-2.078-.163-3.023-.463L3 21l1.532-4.596C3.564 15.166 3 13.634 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"
      />
    </svg>
  );
}

// Slow and deliberate. Opacity keyframes finish fading well before the scale keyframe
// finishes expanding (see the ring's transition below) — that gap is what makes each
// ring read as vanishing mid-flight instead of ballooning out to a visible edge.
const RING_DURATION = 3.2;

/*
 * Persistent bottom-right widget, present on every page. Collapsed state is a single
 * pill button (label + icon); it morphs into a plain close button once open via
 * Framer Motion's layout animation, and back again on close.
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

      <div className="relative">
        {showRings &&
          [0, RING_DURATION / 2].map((delay) => (
            <motion.span
              key={delay}
              aria-hidden
              className="border-signal/70 pointer-events-none absolute inset-0 rounded-full border-2"
              animate={{ scale: [1, 1.4], opacity: [0.5, 0.5, 0, 0] }}
              transition={{
                scale: { duration: RING_DURATION, repeat: Infinity, ease: "easeOut", delay },
                opacity: {
                  duration: RING_DURATION,
                  repeat: Infinity,
                  delay,
                  times: [0, 0.3, 0.6, 1],
                },
              }}
            />
          ))}

        <motion.button
          layout
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close chat" : "Open chat"}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          className={
            open
              ? "bg-medallion relative z-10 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full text-ink shadow-signal"
              : "bg-medallion relative z-10 flex cursor-pointer items-center gap-2.5 rounded-full py-3.5 pr-4 pl-5 text-ink shadow-signal"
          }
        >
          {open ? (
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeWidth={1.8} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <>
              <span className="text-sm font-semibold whitespace-nowrap">
                Chat to see live results
              </span>
              <ChatBubbleIcon />
            </>
          )}
        </motion.button>
      </div>
    </div>
  );
}
