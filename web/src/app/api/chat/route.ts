import {
  convertToModelMessages,
  createUIMessageStreamResponse,
  stepCountIs,
  streamText,
  toUIMessageStream,
  type UIMessage,
} from "ai";
import { groq } from "@ai-sdk/groq";
import { CHAT_SYSTEM_PROMPT, queryMarts } from "@/lib/chat-tools";

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: groq("openai/gpt-oss-120b"),
    system: CHAT_SYSTEM_PROMPT,
    messages: await convertToModelMessages(messages),
    tools: { queryMarts },
    // Default is a single step (stop right after the tool call) — allow a few more
    // so the model can read the query result and actually answer in words.
    stopWhen: stepCountIs(5),
  });

  return createUIMessageStreamResponse({
    stream: toUIMessageStream({
      stream: result.stream,
      // Without this, a mid-stream error (Groq rate limit, timeout, etc.) just
      // drops the connection — the client sees the loading indicator vanish with
      // no message and no explanation. Turning it into an error part lets the UI
      // show something instead of going silent.
      onError: (error) => {
        console.error("Chat stream error:", error);
        return "Something went wrong answering that. Please try again.";
      },
    }),
  });
}
