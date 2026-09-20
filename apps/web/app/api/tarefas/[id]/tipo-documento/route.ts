import { errorResponse, setDocumentType, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

/* LeIA: the lawyer's answer about the species of the document, which is what chooses the vocabulary every
   extraction step uses to name the parties. It is an input to the next run, not a repair of this one. */
export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/tipo-documento">) {
  const up = await viaService(req);
  if (up) return up;
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const body = (await req.json().catch(() => ({}))) as { tipo?: string };
  try { return Response.json(setDocumentType(u, Number(id), String(body.tipo ?? ""))); } catch (e) { return errorResponse(e); }
}
