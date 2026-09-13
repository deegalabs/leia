import { readFileSync } from "node:fs";
import { join } from "node:path";
import { marked } from "marked";

/* Server-side markdown for the documentation pages. The content is the team's own repository docs. */
export function renderDoc(file: string): string {
  const md = readFileSync(join(process.cwd(), "content", "docs", file), "utf8");
  marked.setOptions({ gfm: true, breaks: false });
  return marked.parse(md) as string;
}
