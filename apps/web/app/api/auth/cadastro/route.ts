/* Creating an account opens a session, under the same rule as entering: the token goes to the cookie. */
import { errorResponse, register } from "@/lib/mock";
import { callService, hasService } from "@/lib/server/service";
import { withSession } from "@/lib/server/session";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));

  if (hasService()) {
    const { status, data } = await callService(req, "/api/auth/cadastro", body);
    if (status >= 400 || typeof data.token !== "string") {
      return Response.json({ detail: data.detail ?? "não foi possível criar a conta" }, { status: status >= 400 ? status : 502 });
    }
    return withSession(Response.json({ usuario: data.usuario }), data.token);
  }

  try {
    const { token, usuario } = register(body);
    return withSession(Response.json({ usuario }), token);
  } catch (e) {
    return errorResponse(e);
  }
}
