import { decodeToken } from "@/lib/registry";
import { verifyRecord } from "@/lib/mock";

export async function GET(_req: Request, { params }: RouteContext<"/api/verify/[attempt]">) {
  const { attempt } = await params;
  const record = decodeToken(attempt);
  if (!record) return Response.json({ detail: "comprovante não encontrado" }, { status: 404 });
  return Response.json(verifyRecord(record));
}
