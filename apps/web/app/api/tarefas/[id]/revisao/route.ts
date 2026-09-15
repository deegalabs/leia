import { errorResponse, review, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

/* LeIA: lawyer review before release (docs/API-V3-CONTRACT.md). */
export async function GET(req: Request, { params }: RouteContext<"/api/tarefas/[id]/revisao">) {
  const up = await viaService(req);
  if (up) return up;
  const { id } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(review(u, Number(id))); } catch (e) { return errorResponse(e); }
}
