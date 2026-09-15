import { errorResponse, taskDetail, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function GET(req: Request, { params }: RouteContext<"/api/tarefas/[id]">) {
  const up = await viaService(req);
  if (up) return up;
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(taskDetail(u, Number(id))); } catch (e) { return errorResponse(e); }
}
