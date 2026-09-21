/* LeIA (E15): a cidadã confirma que o nome do convite é o dela e entra. Sem e-mail, sem senha e sem código:
   o link que ela recebeu já prova que é ela.

   O token sai da resposta e vai para o cookie `HttpOnly`, no mesmo molde do cadastro. Devolvê-lo no corpo o
   deixaria alcançável por JavaScript da página, e ele é a credencial de uma conta que ela não escolheu e
   nem sabe que tem. */
import { confirmName, errorResponse } from "@/lib/mock";
import { callService, hasService } from "@/lib/server/service";
import { withSession } from "@/lib/server/session";

export async function POST(req: Request, { params }: RouteContext<"/api/t/[hash]/confirm-name">) {
  const { hash } = await params;

  if (hasService()) {
    const { status, data } = await callService(req, `/api/t/${hash}/confirm-name`, {});
    if (status >= 400 || typeof data.token !== "string") {
      return Response.json({ detail: data.detail ?? "não foi possível confirmar agora" },
                           { status: status >= 400 ? status : 502 });
    }
    return withSession(Response.json({ usuario: data.usuario }), data.token);
  }

  try {
    const { token, usuario } = confirmName(hash);
    return withSession(Response.json({ usuario }), token);
  } catch (e) {
    return errorResponse(e);
  }
}
