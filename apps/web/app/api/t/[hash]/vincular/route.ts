import { bindTask, errorResponse, publicGate, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/vincular">) {
  const up = await viaService(req);
  if (up) return up;
  const { hash } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  const gate = publicGate(hash, u, true);
  if (gate) return gate;
  try { return Response.json(bindTask(u, hash)); } catch (e) { return errorResponse(e); }
}
