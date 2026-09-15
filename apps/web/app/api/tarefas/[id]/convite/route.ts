/* The invite that governs a document link: issued and cancelled by whoever sent the document. */
import { errorResponse, issueInvite, revokeInvite, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

const semSessao = () => Response.json({ detail: "não autenticado" }, { status: 401 });

export async function POST(req: Request, { params }: RouteContext<"/api/tarefas/[id]/convite">) {
  const up = await viaService(req);
  if (up) return up;
  const u = userFromRequest(req);
  if (!u) return semSessao();
  const { id } = await params;
  const body = await req.json().catch(() => ({}));
  try { return Response.json(issueInvite(u, Number(id), body)); } catch (e) { return errorResponse(e); }
}

export async function DELETE(req: Request, { params }: RouteContext<"/api/tarefas/[id]/convite">) {
  const up = await viaService(req);
  if (up) return up;
  const u = userFromRequest(req);
  if (!u) return semSessao();
  const { id } = await params;
  try { return Response.json(revokeInvite(u, Number(id))); } catch (e) { return errorResponse(e); }
}
