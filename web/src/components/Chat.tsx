"use client";

import { useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";

const STARTERS = [
  "Which topics have the most articles?",
  "Who are the top 5 sources?",
  "How many articles are in the warehouse?",
];

export default function Chat({ onClose }: { onClose: () => void }) {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });

  const busy = status === "submitted" || status === "streaming";

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    sendMessage({ text: trimmed });
    setInput("");
  }

  return (
    <div className="flex h-[min(560px,75svh)] flex-col overflow-hidden rounded-2xl border border-bone/12 bg-ink-2 shadow-lift">
      <div className="flex items-center justify-between border-b border-bone/10 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="bg-medallion h-2 w-2 rounded-full" />
          <span className="font-mono text-xs tracking-[0.14em] text-bone uppercase">
            Ask NewsLake
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close chat"
          className="text-muted transition-colors hover:text-bone"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeWidth={1.8} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <div className="flex flex-wrap justify-center gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-bone/15 px-3 py-1.5 text-xs text-bone/80 transition-colors hover:border-signal/40 hover:text-signal"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "bg-medallion text-ink"
                    : "border border-bone/10 bg-ink text-bone"
                }`}
              >
                {message.parts.map((part, i) =>
                  part.type === "text" ? (
                    <span key={i} className="whitespace-pre-wrap">
                      {part.text}
                    </span>
                  ) : null,
                )}
              </div>
            </div>
          ))
        )}
        {busy ? (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border border-bone/10 bg-ink px-3.5 py-2.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" />
              <span
                className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal"
                style={{ animationDelay: "300ms" }}
              />
            </div>
          </div>
        ) : null}
        {!busy && error ? (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl border border-red-500/20 bg-red-500/10 px-3.5 py-2.5 text-sm leading-relaxed text-red-300">
              Something went wrong answering that. Mind trying again?
            </div>
          </div>
        ) : null}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className="flex items-center gap-2 border-t border-bone/10 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about topics, sources, or articles…"
          className="flex-1 rounded-xl border border-bone/15 bg-ink px-3.5 py-2.5 text-sm text-bone placeholder:text-muted focus:border-signal/40 focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="bg-medallion rounded-xl px-4 py-2.5 text-sm font-semibold text-ink transition-opacity disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
