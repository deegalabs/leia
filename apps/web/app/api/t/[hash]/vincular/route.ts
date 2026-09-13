import { bindTask, errorResponse, userFromRequest } from "@/lib/mock";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/vincular">) {
  const { hash } = await params;
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  try { return Response.json(bindTask(u, hash)); } catch (e) { return errorResponse(e); }
}
