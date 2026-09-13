/* Minimal inline markdown: **bold** and *italics*; everything else stays literal text (never HTML). */
export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean);
  return <>{parts.map((part, i) => part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part.startsWith("*") && part.length > 2 ? <em key={i}>{part.slice(1, -1)}</em> : part)}</>;
}

/* Paragraphs and simple lists from the markdown explanation; inline marks via <Inline>. Shared by the citizen
   journey and the lawyer review so both read the same text the same way. */
export function Paragraphs({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return <>{blocks.map((b, i) => {
    const lines = b.split("\n");
    if (lines.length > 1 && lines.every((l) => /^\s*([-*]|\d+[.)])\s+/.test(l))) {
      return <ul key={i} className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{lines.map((l, j) => <li key={j}><Inline text={l.replace(/^\s*([-*]|\d+[.)])\s+/, "")} /></li>)}</ul>;
    }
    return <p key={i} className="mb-3 last:mb-0"><Inline text={b.replace(/^[-*]\s+/gm, "")} /></p>;
  })}</>;
}

/* Titles from the service may start with an emoji; the app shows words only. */
export const cleanTitle = (s: string) => s.replace(/^[^\p{L}\p{N}]+/u, "").trim() || s;
