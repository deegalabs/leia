import { notFound } from "next/navigation";
import { DOCS, docBySlug } from "@/lib/docs";
import { renderDoc } from "@/lib/markdown";
import { DocsShell } from "@/components/DocsShell";

export const dynamicParams = false;
export function generateStaticParams() { return DOCS.map((d) => ({ slug: d.slug })); }
export async function generateMetadata({ params }: PageProps<"/docs/[slug]">) {
  const { slug } = await params; const d = docBySlug(slug);
  return { title: d ? `${d.title} · Documentação` : "Documentação" };
}

export default async function DocPage({ params }: PageProps<"/docs/[slug]">) {
  const { slug } = await params;
  const doc = docBySlug(slug);
  if (!doc) notFound();
  const { html, toc } = renderDoc(doc);
  return <DocsShell current={doc} html={html} toc={toc} />;
}
