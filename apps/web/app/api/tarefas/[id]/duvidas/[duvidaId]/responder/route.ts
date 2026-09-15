import { answerDoubt, errorResponse, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/duvidas/[duvidaId]/responder">) {
  const up = await viaService(req);
  if (up) return up;
  const { id, duvidaId } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  try { return Response.json(answerDoubt(u, Number(id), Number(duvidaId), String(body?.resposta ?? ""))); } catch (e) { return errorResponse(e); }
}
