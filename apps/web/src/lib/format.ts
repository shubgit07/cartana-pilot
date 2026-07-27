// Locale-aware formatting helpers (server-render safe — fixed locale).
// We pin to en-US for the dev MVP so SSR/CSR markup matches; widen later
// when the source `Accept-Language` work lands.

const LOCALE = "en-US";

const dateFmt = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium" });
const dateTimeFmt = new Intl.DateTimeFormat(LOCALE, {
  dateStyle: "medium",
  timeStyle: "short",
});
const numFmt = new Intl.NumberFormat(LOCALE);

export function formatDate(input: string | Date | null | undefined): string {
  if (input == null) return "";
  const d = typeof input === "string" ? new Date(input) : input;
  if (Number.isNaN(d.getTime())) return "";
  return dateFmt.format(d);
}

export function formatDateTime(input: string | Date | null | undefined): string {
  if (input == null) return "";
  const d = typeof input === "string" ? new Date(input) : input;
  if (Number.isNaN(d.getTime())) return "";
  return dateTimeFmt.format(d);
}

export function formatCount(n: number, singular: string, plural?: string): string {
  const word = n === 1 ? singular : plural ?? `${singular}s`;
  return `${numFmt.format(n)} ${word}`;
}

export function formatScore(n: number): string {
  return n.toFixed(2);
}
