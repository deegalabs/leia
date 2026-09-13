import { buildInferences, publicGate, storeTask } from "@/lib/mock";

/* Mock: the fixture's clauses become tagged items over the extracted text.
   LeIA: 409 while the pipeline runs or the lawyer reviews (docs/API-V3-CONTRACT.md). */
export async function GET(_req: Request, { params }: RouteContext<"/api/t/[hash]/inferencias">) {
  const { hash } = await params;
  const gate = publicGate(hash);
  if (gate) return gate;
  const t = storeTask(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  return Response.json(buildInferences(t));
}
