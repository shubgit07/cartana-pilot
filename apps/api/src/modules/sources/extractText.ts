// Text extraction — pure function over Buffer + kind.
// Phase 1 supports PDF + plain text. Image/screenshot ingestion is a
// future expansion (plan §17.2).

import pdfParse from "pdf-parse";
import { logger } from "../../lib/logger";

export async function extractText(buffer: Buffer, kind: "pdf" | "text"): Promise<string> {
  if (kind === "text") {
    return buffer.toString("utf8");
  }
  if (kind === "pdf") {
    try {
      const res = await pdfParse(buffer);
      return res.text || "";
    } catch (err) {
      logger.error("PDF parse failed", { err: String(err) });
      throw err;
    }
  }
  throw new Error(`Unsupported source kind: ${kind}`);
}