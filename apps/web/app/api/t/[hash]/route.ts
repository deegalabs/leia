import { inviteGate, publicTaskFor, storeTask, userFromRequest } from "@/lib/mock";
import { viaService } from "@/lib/server/service";

export async function GET(req: Request, { params }: RouteContext<"/api/t/[hash]">) {
  const up = await viaService(req);
  if (up) return up;
  const { hash } = await params;
  /* LeIA: v3 adds advogado, tem_advogado, cidadao_vinculado, duvidas_enviadas and the stored last attempt;
     the visible preparation adds etapas (14 steps), the full eventos and sem_perguntas (external flow) */
  const stored = storeTask(hash);
  if (stored) {
    const gate = inviteGate(stored, userFromRequest(req));
    if (gate) return gate;
  }
  const t = publicTaskFor(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  return Response.json(t);
}
