/* Minimal inline markdown: **bold** and *italics*; everything else stays literal text (never HTML). */
export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean);
  return <>{parts.map((part, i) => part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part.startsWith("*") && part.length > 2 ? <em key={i}>{part.slice(1, -1)}</em> : part)}</>;
}

/* Titles from the service may start with an emoji; the app shows words only. */
export const cleanTitle = (s: string) => s.replace(/^[^\p{L}\p{N}]+/u, "").trim() || s;
