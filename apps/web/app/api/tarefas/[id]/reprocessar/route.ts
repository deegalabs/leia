/* Refaz a explicação de um documento que não chegou ao fim: só quem enviou. */
import { errorResponse, retryTask, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/reprocessar">) {
  const up = await viaService(req);
  if (up) return up;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const { id } = await params;
  try { return Response.json(retryTask(u, Number(id))); } catch (e) { return errorResponse(e); }
}
