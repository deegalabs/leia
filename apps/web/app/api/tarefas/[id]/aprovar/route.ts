import { approve, errorResponse, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

/* LeIA: "pronta" -> "enviada"; the citizen link opens the explanation from here on. */
export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/aprovar">) {
  const up = await viaService(req);
  if (up) return up;
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(approve(u, Number(id))); } catch (e) { return errorResponse(e); }
}
