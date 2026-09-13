import { approve, errorResponse, userFromRequest } from "@/lib/mock";

/* LeIA: "pronta" -> "enviada"; the citizen link opens the explanation from here on. */
export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/aprovar">) {
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(approve(u, Number(id))); } catch (e) { return errorResponse(e); }
}
