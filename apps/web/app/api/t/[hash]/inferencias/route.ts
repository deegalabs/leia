import { buildInferences, inReview, isProcessing, storeTask } from "@/lib/mock";

/* Mock: the fixture's clauses become tagged items over the extracted text.
   LeIA: 409 while the lawyer reviews; while the pipeline runs, 200 with parcial: true and what exists so far
   (docs/API-V3-CONTRACT.md, "Preparação visível e tarefas do fluxo externo"). */
export async function GET(_req: Request, { params }: RouteContext<"/api/t/[hash]/inferencias">) {
  const { hash } = await params;
  const t = storeTask(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  if (inReview(t)) return Response.json({ detail: "Em revisão pelo advogado" }, { status: 409 });
  if (isProcessing(t)) return Response.json(buildInferences(t, true));
  if (t.status === "falhou") return Response.json({ detail: "a explicação não pôde ser preparada" }, { status: 409 });
  return Response.json(buildInferences(t));
}
