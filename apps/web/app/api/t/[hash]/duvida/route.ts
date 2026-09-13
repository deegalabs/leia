import { errorResponse, sendDoubt } from "@/lib/mock";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/duvida">) {
  const { hash } = await params;
  const body = await req.json().catch(() => ({}));
  try { return Response.json(sendDoubt(hash, String(body?.texto ?? ""), body?.contexto)); } catch (e) { return errorResponse(e); }
}
