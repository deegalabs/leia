/* LeIA (E15): "esse nome não é o meu". Registra e não faz mais nada.

   Não devolve sessão nenhuma, ao contrário da confirmação: aqui não nasce conta, porque não há nome para
   afirmar. Quem tocou continua lendo tudo e continua podendo perguntar; o que ela perde é o comprovante.

   A falha aqui é engolida de propósito. O aviso é útil para quem enviou, mas não é o que a pessoa veio
   fazer, e uma tarja vermelha por causa dele assustaria por um problema que não é dela e que não a impede
   de nada. */
import { denyName, errorResponse } from "@/lib/mock";
import { callService, hasService } from "@/lib/server/service";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/deny-name">) {
  const { hash } = await params;

  if (hasService()) {
    const { status, data } = await callService(req, `/api/t/${hash}/deny-name`, {});
    if (status >= 400) {
      return Response.json({ detail: data.detail ?? "não foi possível registrar agora" }, { status });
    }
    return Response.json({ ok: true });
  }

  try {
    return Response.json(denyName(hash));
  } catch (e) {
    return errorResponse(e);
  }
}
