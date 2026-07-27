"use client";

const QUESTIONS = [
  "What are the main requirements of this project?",
  "What deadlines are mentioned in the brief?",
  "What features does the dashboard module need?",
  "What are the acceptance criteria?",
];

export function SuggestedQuestions({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Ask anything about the uploaded project material. Try a suggested question:
      </p>
      <div className="flex flex-wrap gap-2">
        {QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            aria-label={`Ask: ${q}`}
            className="rounded-full border bg-background px-3 py-1 text-xs transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
