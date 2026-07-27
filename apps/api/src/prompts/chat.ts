// Chat prompt logic — kept separate from business logic.

import { AIChatInput } from "../ai/AIProvider";

export function buildChatMessages(input: AIChatInput) {
  const system = [
    "You are Cartana, a project specification copilot.",
    "Answer using ONLY the passages below. If the answer is not in the passages, say so.",
    "Cite passages inline as [n] and refer to filenames when relevant. Be concise.",
    "",
    "--- PASSAGES ---",
    input.passages
      .slice(0, 8)
      .map((p, i) => `[${i + 1}] (${p.filename}) ${p.text}`)
      .join("\n\n"),
  ].join("\n");

  const messages: { role: "system" | "user" | "assistant"; content: string }[] = [
    { role: "system", content: system },
  ];

  for (const m of input.history ?? []) {
    messages.push({ role: m.role, content: m.content });
  }
  messages.push({ role: "user", content: input.question });
  return messages;
}