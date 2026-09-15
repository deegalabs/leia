/* Public verification of a receipt. The service answers this one under /verify, not /api. */
import { verifyRecord } from "@/lib/mock";
import { decodeToken } from "@/lib/registry";
import { viaService } from "@/lib/server/service";

export async function GET(req: Request, { params }: RouteContext<"/api/verify/[attempt]">) {
  const { attempt } = await params;
  const up = await viaService(req, `/verify/${encodeURIComponent(attempt)}?format=json`);
  if (up) return up;
  const record = decodeToken(attempt);
  if (!record) return Response.json({ detail: "comprovante não encontrado" }, { status: 404 });
  return Response.json(verifyRecord(record));
}
