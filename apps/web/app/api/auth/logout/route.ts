/* Leaving drops the cookie no matter what the service answers: a session the browser cannot present is over. */
import { logout, userFromRequest } from "@/lib/mock";
import { callService, hasService } from "@/lib/server/service";
import { tokenFromRequest, withoutSession } from "@/lib/server/session";

export async function POST(req: Request) {
  if (hasService()) {
    if (tokenFromRequest(req)) await callService(req, "/api/auth/logout", {}).catch(() => null);
    return withoutSession(Response.json({ ok: true }));
  }

  const u = userFromRequest(req);
  if (u) logout(u);
  return withoutSession(Response.json({ ok: true }));
}
