import { logout, userFromRequest } from "@/lib/mock";

export async function POST(req: Request) {
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  return Response.json(logout(u));
}
