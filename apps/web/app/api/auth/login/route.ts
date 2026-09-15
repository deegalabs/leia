/* Entering is where the service token first exists for this browser. It goes into the session cookie and
   never into the response body, so no script on the page can read it. */
import { errorResponse, login } from "@/lib/mock";
import { callService, hasService } from "@/lib/server/service";
import { withSession } from "@/lib/server/session";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));

  if (hasService()) {
    const { status, data } = await callService(req, "/api/auth/login", body);
    if (status !== 200 || typeof data.token !== "string") {
      return Response.json({ detail: data.detail ?? "não foi possível entrar" }, { status: status === 200 ? 502 : status });
    }
    return withSession(Response.json({ usuario: data.usuario }), data.token);
  }

  try {
    const { token, usuario } = login(body);
    return withSession(Response.json({ usuario }), token);
  } catch (e) {
    return errorResponse(e);
  }
}
