import { errorResponse, sendDoubt } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/duvida">) {
  const up = await viaService(req);
  if (up) return up;
  const { hash } = await params;
  const body = await req.json().catch(() => ({}));
  try { return Response.json(sendDoubt(hash, String(body?.texto ?? ""), body?.contexto)); } catch (e) { return errorResponse(e); }
}
