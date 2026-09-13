import { publicTaskFor } from "@/lib/mock";

export async function GET(_req: Request, { params }: RouteContext<"/api/t/[hash]">) {
  const { hash } = await params;
  /* LeIA: v3 adds advogado, tem_advogado, cidadao_vinculado, duvidas_enviadas and the stored last attempt;
     the visible preparation adds etapas (14 steps), the full eventos and sem_perguntas (external flow) */
  const t = publicTaskFor(hash);
  if (!t) return Response.json({ detail: "não encontrado" }, { status: 404 });
  return Response.json(t);
}
