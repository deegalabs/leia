import { meOf, userFromRequest } from "@/lib/mock";

export async function GET(req: Request) {
  const u = userFromRequest(req);
  if (!u) return Response.json({ detail: "não autenticado" }, { status: 401 });
  return Response.json(meOf(u));
}
