// Simple, transparent chunking strategy. ~700 chars per chunk with ~100
// char overlap. We deliberately keep this naive — smarter strategies
// (sentence-boundary aware, semantic, etc.) can replace this function
// without changing callers.

export interface ChunkPiece {
  position: number;
  text: string;
}

const CHUNK_SIZE = 700;
const CHUNK_OVERLAP = 100;

export function chunkText(input: string): ChunkPiece[] {
  const text = input.replace(/\r\n/g, "\n").trim();
  if (!text) return [];

  const pieces: ChunkPiece[] = [];
  let position = 0;
  let cursor = 0;

  while (cursor < text.length) {
    let end = Math.min(cursor + CHUNK_SIZE, text.length);

    // Prefer to break on a sentence or whitespace boundary near `end`.
    if (end < text.length) {
      const window = text.slice(cursor, end);
      const lastBreak = findLastBreak(window);
      if (lastBreak > CHUNK_SIZE * 0.5) {
        end = cursor + lastBreak;
      }
    }

    const piece = text.slice(cursor, end).trim();
    if (piece.length > 0) {
      pieces.push({ position, text: piece });
      position += 1;
    }

    if (end >= text.length) break;
    cursor = Math.max(end - CHUNK_OVERLAP, cursor + 1);
  }

  return pieces;
}

function findLastBreak(window: string): number {
  // Prefer paragraph > sentence > word boundary.
  const para = window.lastIndexOf("\n\n");
  if (para >= 0) return para + 2;
  const sentence = Math.max(
    window.lastIndexOf(". "),
    window.lastIndexOf("? "),
    window.lastIndexOf("! "),
    window.lastIndexOf(".\n")
  );
  if (sentence >= 0) return sentence + 2;
  const word = window.lastIndexOf(" ");
  if (word >= 0) return word + 1;
  return -1;
}