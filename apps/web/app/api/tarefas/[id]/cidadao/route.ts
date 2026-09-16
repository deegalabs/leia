/* Desfaz o vínculo da cidadã com o documento: só quem enviou decide. */
import { errorResponse, unbindTask, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function DELETE(req: Request, { params }: RouteContext<"/api/tarefas/[id]/cidadao">) {
  const up = await viaService(req);
  if (up) return up;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const { id } = await params;
  try { return Response.json(unbindTask(u, Number(id))); } catch (e) { return errorResponse(e); }
}
