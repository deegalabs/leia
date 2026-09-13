import { errorResponse, register } from "@/lib/mock";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  try { return Response.json(register(body)); } catch (e) { return errorResponse(e); }
}
