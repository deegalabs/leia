/* Who is signed in. A session the service no longer accepts is cleared here, so the browser does not keep
   showing a name for a session that is gone. */
import { meOf, userFromRequest } from "@/lib/mock";
import { getService, hasService } from "@/lib/server/service";
import { tokenFromRequest, withoutSession } from "@/lib/server/session";

const semSessao = () => Response.json({ detail: "não autenticado" }, { status: 401 });

export async function GET(req: Request) {
  if (!tokenFromRequest(req)) return semSessao();

  if (hasService()) {
    const { status, data } = await getService(req, "/api/auth/me");
    if (status === 401) return withoutSession(semSessao());
    if (status >= 400) return Response.json({ detail: data.detail ?? "erro" }, { status });
    return Response.json({ usuario: data.usuario });
  }

  const u = userFromRequest(req);
  if (!u) return withoutSession(semSessao());
  return Response.json(meOf(u));
}
