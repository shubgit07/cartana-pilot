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
      <p className="text-sm leading-relaxed text-muted-foreground">
        Ask anything about the uploaded project material. Try a suggested question:
      </p>
      <div className="flex flex-wrap gap-2">
        {QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            aria-label={`Ask: ${q}`}
            className="rounded-full border border-border bg-surface px-3.5 py-1.5 text-xs text-muted-foreground shadow-soft transition-[background-color,border-color,color,box-shadow] duration-150 hover:border-border-strong hover:bg-primary-soft hover:text-primary-soft-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
