import { errorResponse, taskDetail, userFromRequest } from "@/lib/mock";

export async function GET(req: Request, { params }: RouteContext<"/api/tarefas/[id]">) {
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(taskDetail(u, Number(id))); } catch (e) { return errorResponse(e); }
}
